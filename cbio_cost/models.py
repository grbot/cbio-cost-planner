"""Typed data structures shared across the cost-calculation engine.

Convention: every percentage/fraction field (headroom, contingency, VAT,
retrieval fraction, ...) is stored as a ``Decimal`` fraction in the range
``[0, 1]`` (e.g. 20% is ``Decimal("0.20")``), not as 0-100. UI code is
responsible for converting user-facing percent inputs into this form.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

FILE_TYPES: tuple[str, ...] = ("FASTQ", "CRAM", "gVCF")

STORAGE_CLASS_KEYS: tuple[str, ...] = (
    "s3_standard",
    "glacier_instant",
    "glacier_flexible",
    "glacier_deep_archive",
)


@dataclass
class ProjectInputs:
    """Top-level project description (spec §3)."""

    project_name: str
    project_type: str
    num_samples: int
    depth_label: str
    retention_years: Decimal

    def __post_init__(self) -> None:
        if self.num_samples <= 0:
            raise ValueError("num_samples must be a positive integer")
        if self.retention_years <= 0:
            raise ValueError("retention_years must be positive")


@dataclass
class FileTypeVolumeAssumption:
    """Per-file-type data volume and archive destination (spec §4, §8)."""

    name: str
    gb_per_sample: Decimal
    archive_class: str

    def __post_init__(self) -> None:
        if self.gb_per_sample < 0:
            raise ValueError(f"{self.name}: gb_per_sample cannot be negative")
        if self.archive_class not in STORAGE_CLASS_KEYS:
            raise ValueError(f"{self.name}: unknown archive_class '{self.archive_class}'")


@dataclass
class StorageAssumptions:
    """Storage envelope and active-period assumptions (spec §4, §7)."""

    headroom_fraction: Decimal
    active_months: Decimal

    def __post_init__(self) -> None:
        if not (Decimal(0) <= self.headroom_fraction):
            raise ValueError("headroom_fraction cannot be negative")
        if self.active_months < 0:
            raise ValueError("active_months cannot be negative")


@dataclass
class MovementAssumptions:
    """Data-movement (egress-driving) assumptions (spec §5)."""

    fastq_passes: Decimal
    cram_retrieval_fraction: Decimal
    cram_retrieval_passes: Decimal
    gvcf_passes: Decimal
    transfer_contingency: Decimal

    def __post_init__(self) -> None:
        for label, value in (
            ("fastq_passes", self.fastq_passes),
            ("cram_retrieval_passes", self.cram_retrieval_passes),
            ("gvcf_passes", self.gvcf_passes),
        ):
            if value < 0:
                raise ValueError(f"{label} cannot be negative")
        if not (Decimal(0) <= self.cram_retrieval_fraction <= Decimal(1)):
            raise ValueError("cram_retrieval_fraction must be between 0 and 1")
        if self.transfer_contingency < 0:
            raise ValueError("transfer_contingency cannot be negative")


@dataclass
class EngineeringAssumptions:
    """Infrastructure engineering effort/rate assumptions (spec §10)."""

    onboarding_hours: Decimal
    operations_hours_per_year: Decimal
    closeout_hours: Decimal
    hourly_rate_zar: Decimal

    def __post_init__(self) -> None:
        for label, value in (
            ("onboarding_hours", self.onboarding_hours),
            ("operations_hours_per_year", self.operations_hours_per_year),
            ("closeout_hours", self.closeout_hours),
            ("hourly_rate_zar", self.hourly_rate_zar),
        ):
            if value < 0:
                raise ValueError(f"{label} cannot be negative")


@dataclass
class CurrencyAssumptions:
    """Exchange rate and VAT assumptions (spec §12)."""

    usd_zar: Decimal
    vat_fraction: Decimal

    def __post_init__(self) -> None:
        if self.usd_zar <= 0:
            raise ValueError("usd_zar must be positive")
        if self.vat_fraction < 0:
            raise ValueError("vat_fraction cannot be negative")


@dataclass
class PriceTier:
    """One tier of a tiered USD-per-GB(-month) price schedule.

    ``up_to_gb`` is the cumulative usage ceiling for this tier, or ``None``
    for the final, unbounded tier.
    """

    up_to_gb: Decimal | None
    usd_per_gb: Decimal


@dataclass
class StorageClassPricing:
    key: str
    label: str
    tiers: list[PriceTier]
    minimum_storage_duration_days: int
    retrieval_usd_per_gb: Decimal
    requires_restore: bool
    retrieval_characteristics: str
    pricing_last_verified: str
    source: str


@dataclass
class RequestPricing:
    put_usd_per_1000: Decimal
    get_usd_per_1000: Decimal
    lifecycle_transition_usd_per_1000: Decimal
    pricing_last_verified: str
    source: str


@dataclass
class EgressPricing:
    tiers: list[PriceTier]
    free_allowance_gb_per_month: Decimal
    pricing_last_verified: str
    source: str


@dataclass
class PricingConfig:
    region: str
    storage_classes: dict[str, StorageClassPricing]
    egress: EgressPricing
    requests: RequestPricing


@dataclass
class TraceLine:
    """One human-readable calculation-detail line for the audit expander."""

    label: str
    detail: str


@dataclass
class VolumeResult:
    per_file_type_gb: dict[str, Decimal]
    raw_total_gb: Decimal
    envelope_gb: Decimal
    trace: list[TraceLine] = field(default_factory=list)


@dataclass
class TransferResult:
    per_file_type_egress_gb: dict[str, Decimal]
    base_egress_gb: Decimal
    planned_egress_gb: Decimal
    egress_cost_usd: Decimal
    trace: list[TraceLine] = field(default_factory=list)


@dataclass
class ArchiveClassResult:
    file_type: str
    storage_class: str
    monthly_cost_usd: Decimal
    months_in_archive: Decimal
    total_cost_usd: Decimal
    minimum_duration_warning: str | None
    retrieval_characteristics: str
    requires_restore: bool


@dataclass
class StorageCostResult:
    active_storage_cost_usd: Decimal
    request_cost_usd: Decimal
    archive_results: list[ArchiveClassResult]
    archive_monthly_cost_usd: Decimal
    archive_annual_cost_usd: Decimal
    archive_total_cost_usd: Decimal
    trace: list[TraceLine] = field(default_factory=list)


@dataclass
class OperationsCostResult:
    onboarding_cost_zar: Decimal
    operations_cost_zar: Decimal
    closeout_cost_zar: Decimal
    total_zar: Decimal
    trace: list[TraceLine] = field(default_factory=list)


@dataclass
class CostLineItem:
    label: str
    amount_zar: Decimal
    note: str = ""


@dataclass
class CostEstimate:
    inputs: ProjectInputs
    volume: VolumeResult
    transfer: TransferResult
    storage: StorageCostResult
    operations: OperationsCostResult
    currency: CurrencyAssumptions

    total_aws_usd: Decimal
    total_aws_zar_ex_vat: Decimal
    total_aws_zar_inc_vat: Decimal
    total_engineering_zar: Decimal
    grand_total_zar: Decimal

    line_items: list[CostLineItem] = field(default_factory=list)
    explanation: str = ""
