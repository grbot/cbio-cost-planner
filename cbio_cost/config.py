"""Load and validate YAML configuration into typed objects.

Keeping this separate from ``models.py`` means the YAML shape (and any
future support for JSON/TOML) can change without touching the dataclasses
used by the calculation engine.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from cbio_cost.models import (
    STORAGE_CLASS_KEYS,
    CurrencyAssumptions,
    EgressPricing,
    EngineeringAssumptions,
    FileTypeVolumeAssumption,
    MovementAssumptions,
    PriceTier,
    PricingConfig,
    ProjectInputs,
    RequestPricing,
    StorageAssumptions,
    StorageClassPricing,
)


def _dec(value: Any) -> Decimal:
    """Convert a YAML-parsed scalar (int/float/str) to Decimal safely."""
    return Decimal(str(value))


def _percent_to_fraction(value: Any) -> Decimal:
    fraction = _dec(value) / Decimal(100)
    if not (Decimal(0) <= fraction):
        raise ValueError(f"Percentage value {value!r} cannot be negative")
    return fraction


def _parse_tiers(raw_tiers: list[dict[str, Any]], rate_key: str) -> list[PriceTier]:
    if not raw_tiers:
        raise ValueError("A price schedule must have at least one tier")
    tiers: list[PriceTier] = []
    for raw in raw_tiers:
        up_to_gb = raw.get("up_to_gb")
        tiers.append(
            PriceTier(
                up_to_gb=None if up_to_gb is None else _dec(up_to_gb),
                usd_per_gb=_dec(raw[rate_key]),
            )
        )
    if tiers[-1].up_to_gb is not None:
        raise ValueError("The final tier in a price schedule must be unbounded (up_to_gb: null)")
    for tier in tiers:
        if tier.usd_per_gb < 0:
            raise ValueError("Tier prices cannot be negative")
    return tiers


def load_pricing(path: str | Path) -> PricingConfig:
    """Parse ``config/aws-pricing.yaml`` into a :class:`PricingConfig`."""
    raw = yaml.safe_load(Path(path).read_text())["aws"]

    storage_classes: dict[str, StorageClassPricing] = {}
    for key, block in raw["storage_classes"].items():
        if key not in STORAGE_CLASS_KEYS:
            raise ValueError(f"Unknown storage class key in pricing config: {key}")
        storage_classes[key] = StorageClassPricing(
            key=key,
            label=block["label"],
            tiers=_parse_tiers(block["tiers"], "usd_per_gb_month"),
            minimum_storage_duration_days=int(block["minimum_storage_duration_days"]),
            retrieval_usd_per_gb=_dec(block["retrieval_usd_per_gb"]),
            requires_restore=bool(block["requires_restore"]),
            retrieval_characteristics=str(block["retrieval_characteristics"]).strip(),
            pricing_last_verified=str(block["pricing_last_verified"]),
            source=str(block["source"]),
        )

    egress_block = raw["egress"]
    egress = EgressPricing(
        tiers=_parse_tiers(egress_block["tiers"], "usd_per_gb"),
        free_allowance_gb_per_month=_dec(egress_block["free_allowance_gb_per_month"]),
        pricing_last_verified=str(egress_block["pricing_last_verified"]),
        source=str(egress_block["source"]),
    )
    if egress.free_allowance_gb_per_month < 0:
        raise ValueError("free_allowance_gb_per_month cannot be negative")

    requests_block = raw["requests"]
    requests = RequestPricing(
        put_usd_per_1000=_dec(requests_block["put_usd_per_1000"]),
        get_usd_per_1000=_dec(requests_block["get_usd_per_1000"]),
        lifecycle_transition_usd_per_1000=_dec(requests_block["lifecycle_transition_usd_per_1000"]),
        pricing_last_verified=str(requests_block["pricing_last_verified"]),
        source=str(requests_block["source"]),
    )
    for label, value in (
        ("put_usd_per_1000", requests.put_usd_per_1000),
        ("get_usd_per_1000", requests.get_usd_per_1000),
        ("lifecycle_transition_usd_per_1000", requests.lifecycle_transition_usd_per_1000),
    ):
        if value < 0:
            raise ValueError(f"{label} cannot be negative")

    return PricingConfig(
        region=str(raw["region"]),
        storage_classes=storage_classes,
        egress=egress,
        requests=requests,
    )


def load_currency_defaults(path: str | Path) -> CurrencyAssumptions:
    """Read the default USD/ZAR exchange rate and VAT rate from the pricing config."""
    raw = yaml.safe_load(Path(path).read_text())["aws"]
    return CurrencyAssumptions(
        usd_zar=_dec(raw["exchange_rate"]["usd_zar"]),
        vat_fraction=_percent_to_fraction(raw["vat_percent"]),
    )


class ProjectProfile:
    """A fully-specified set of inputs/assumptions loaded from profiles YAML."""

    def __init__(
        self,
        project: ProjectInputs,
        volumes: dict[str, FileTypeVolumeAssumption],
        storage: StorageAssumptions,
        movement: MovementAssumptions,
        engineering: EngineeringAssumptions,
    ) -> None:
        self.project = project
        self.volumes = volumes
        self.storage = storage
        self.movement = movement
        self.engineering = engineering


def _parse_volumes(raw_volumes: dict[str, dict[str, Any]]) -> dict[str, FileTypeVolumeAssumption]:
    volumes: dict[str, FileTypeVolumeAssumption] = {}
    for name, block in raw_volumes.items():
        volumes[name] = FileTypeVolumeAssumption(
            name=name,
            gb_per_sample=_dec(block["gb_per_sample"]),
            archive_class=str(block["archive_class"]),
        )
    return volumes


def _parse_movement(block: dict[str, Any]) -> MovementAssumptions:
    return MovementAssumptions(
        fastq_passes=_dec(block["fastq_passes"]),
        cram_retrieval_fraction=_percent_to_fraction(block["cram_retrieval_percent"]),
        cram_retrieval_passes=_dec(block["cram_retrieval_passes"]),
        gvcf_passes=_dec(block["gvcf_passes"]),
        transfer_contingency=_percent_to_fraction(block["transfer_contingency_percent"]),
    )


def load_profiles(path: str | Path) -> tuple[ProjectProfile, dict[str, MovementAssumptions]]:
    """Parse ``config/project-profiles.yaml``.

    Returns the default project profile plus a mapping of scenario name ->
    movement-assumption overlay for the sensitivity-analysis comparison.
    """
    raw = yaml.safe_load(Path(path).read_text())
    default_block = raw["default_profile"]

    project = ProjectInputs(
        project_name=str(default_block["project"]["project_name"]),
        project_type=str(default_block["project"]["project_type"]),
        num_samples=int(default_block["project"]["num_samples"]),
        depth_label=str(default_block["project"]["depth_label"]),
        retention_years=_dec(default_block["project"]["retention_years"]),
    )
    volumes = _parse_volumes(default_block["volumes"])
    storage = StorageAssumptions(
        headroom_fraction=_percent_to_fraction(default_block["storage"]["headroom_percent"]),
        active_months=_dec(default_block["storage"]["active_months"]),
    )
    movement = _parse_movement(default_block["movement"])
    engineering = EngineeringAssumptions(
        onboarding_hours=_dec(default_block["engineering"]["onboarding_hours"]),
        operations_hours_per_year=_dec(default_block["engineering"]["operations_hours_per_year"]),
        closeout_hours=_dec(default_block["engineering"]["closeout_hours"]),
        hourly_rate_zar=_dec(default_block["engineering"]["hourly_rate_zar"]),
    )
    profile = ProjectProfile(project, volumes, storage, movement, engineering)

    scenarios = {name: _parse_movement(block) for name, block in raw["scenarios"].items()}

    return profile, scenarios
