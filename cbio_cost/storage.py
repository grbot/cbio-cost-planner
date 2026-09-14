"""Data volume and S3/Glacier storage cost calculations (spec §4, §7, §8, §9)."""

from __future__ import annotations

from decimal import Decimal

from cbio_cost.models import (
    ArchiveClassResult,
    FileTypeVolumeAssumption,
    PriceTier,
    PricingConfig,
    ProjectInputs,
    StorageAssumptions,
    StorageCostResult,
    TraceLine,
    VolumeResult,
)

MONTHS_PER_YEAR = Decimal(12)
AVG_OBJECT_SIZE_GB = Decimal(5)  # planning assumption for request-count estimation
APPROX_DAYS_PER_MONTH = Decimal("30.4")


def tiered_cost(quantity_gb: Decimal, tiers: list[PriceTier]) -> Decimal:
    """Price ``quantity_gb`` against a cumulative tiered USD/GB(-month) schedule.

    Each tier's ``up_to_gb`` is a cumulative ceiling; the final tier must be
    unbounded (``up_to_gb is None``).
    """
    if quantity_gb < 0:
        raise ValueError("quantity_gb cannot be negative")
    cost = Decimal(0)
    remaining = quantity_gb
    prev_ceiling = Decimal(0)
    for tier in tiers:
        if remaining <= 0:
            break
        tier_capacity = (tier.up_to_gb - prev_ceiling) if tier.up_to_gb is not None else remaining
        amount_in_tier = min(remaining, tier_capacity)
        cost += amount_in_tier * tier.usd_per_gb
        remaining -= amount_in_tier
        if tier.up_to_gb is not None:
            prev_ceiling = tier.up_to_gb
    return cost


def calculate_data_volume(
    inputs: ProjectInputs,
    volumes: dict[str, FileTypeVolumeAssumption],
    storage: StorageAssumptions,
) -> VolumeResult:
    """Compute per-file-type and total durable data volume, plus the
    provisioned planning envelope after headroom (spec §4). Never rounds."""
    per_file_type_gb: dict[str, Decimal] = {}
    trace: list[TraceLine] = []
    for name, assumption in volumes.items():
        volume_gb = Decimal(inputs.num_samples) * assumption.gb_per_sample
        per_file_type_gb[name] = volume_gb
        trace.append(
            TraceLine(
                label=f"{name} volume",
                detail=f"{inputs.num_samples} x {assumption.gb_per_sample} GB = {volume_gb} GB",
            )
        )

    raw_total_gb = sum(per_file_type_gb.values(), Decimal(0))
    trace.append(
        TraceLine(
            label="Raw durable volume",
            detail=" + ".join(f"{v} GB" for v in per_file_type_gb.values()) + f" = {raw_total_gb} GB",
        )
    )

    envelope_gb = raw_total_gb * (Decimal(1) + storage.headroom_fraction)
    trace.append(
        TraceLine(
            label="Provisioned envelope",
            detail=(
                f"{raw_total_gb} GB x (1 + {storage.headroom_fraction * 100}%) = {envelope_gb} GB"
            ),
        )
    )

    return VolumeResult(
        per_file_type_gb=per_file_type_gb,
        raw_total_gb=raw_total_gb,
        envelope_gb=envelope_gb,
        trace=trace,
    )


def active_storage_cost(envelope_gb: Decimal, active_months: Decimal, pricing: PricingConfig) -> Decimal:
    """Tiered S3 Standard cost for the active-processing period (spec §7)."""
    s3_standard = pricing.storage_classes["s3_standard"]
    monthly_cost = tiered_cost(envelope_gb, s3_standard.tiers)
    return monthly_cost * active_months


def request_cost(raw_total_gb: Decimal, planned_egress_gb: Decimal, pricing: PricingConfig) -> Decimal:
    """Estimate S3 PUT/GET/lifecycle-transition request costs (spec §1, §6).

    Individual object counts aren't tracked by this planning tool, so request
    counts are estimated from volume using an assumed average object size.
    This is a coarse planning approximation, not a billing-accurate count.
    """
    put_requests = raw_total_gb / AVG_OBJECT_SIZE_GB
    get_requests = planned_egress_gb / AVG_OBJECT_SIZE_GB
    lifecycle_requests = raw_total_gb / AVG_OBJECT_SIZE_GB

    req = pricing.requests
    return (
        (put_requests / Decimal(1000)) * req.put_usd_per_1000
        + (get_requests / Decimal(1000)) * req.get_usd_per_1000
        + (lifecycle_requests / Decimal(1000)) * req.lifecycle_transition_usd_per_1000
    )


def archive_storage_cost(
    inputs: ProjectInputs,
    volumes: dict[str, FileTypeVolumeAssumption],
    per_file_type_gb: dict[str, Decimal],
    storage: StorageAssumptions,
    pricing: PricingConfig,
) -> tuple[list[ArchiveClassResult], Decimal, Decimal, Decimal]:
    """Per-file-type archive storage cost over the retention period (spec §8, §9).

    Returns (per-file-type results, aggregate monthly cost, aggregate annual
    cost, aggregate total cost over the archived portion of the retention
    period).
    """
    retention_months = inputs.retention_years * MONTHS_PER_YEAR
    months_in_archive = retention_months - storage.active_months
    if months_in_archive < 0:
        months_in_archive = Decimal(0)

    results: list[ArchiveClassResult] = []
    for name, assumption in volumes.items():
        storage_class = pricing.storage_classes[assumption.archive_class]
        volume_gb = per_file_type_gb[name]
        monthly_cost = tiered_cost(volume_gb, storage_class.tiers)
        total_cost = monthly_cost * months_in_archive

        warning: str | None = None
        archived_days = months_in_archive * APPROX_DAYS_PER_MONTH
        if 0 < archived_days < storage_class.minimum_storage_duration_days:
            warning = (
                f"{name} is planned to remain in {storage_class.label} for only "
                f"~{archived_days:.0f} days, below its "
                f"{storage_class.minimum_storage_duration_days}-day minimum storage "
                "duration; early deletion/transition fees may apply."
            )

        results.append(
            ArchiveClassResult(
                file_type=name,
                storage_class=assumption.archive_class,
                monthly_cost_usd=monthly_cost,
                months_in_archive=months_in_archive,
                total_cost_usd=total_cost,
                minimum_duration_warning=warning,
                retrieval_characteristics=storage_class.retrieval_characteristics,
                requires_restore=storage_class.requires_restore,
            )
        )

    aggregate_monthly = sum((r.monthly_cost_usd for r in results), Decimal(0))
    aggregate_annual = aggregate_monthly * MONTHS_PER_YEAR
    aggregate_total = sum((r.total_cost_usd for r in results), Decimal(0))
    return results, aggregate_monthly, aggregate_annual, aggregate_total


def build_storage_cost_result(
    inputs: ProjectInputs,
    volumes: dict[str, FileTypeVolumeAssumption],
    per_file_type_gb: dict[str, Decimal],
    raw_total_gb: Decimal,
    envelope_gb: Decimal,
    planned_egress_gb: Decimal,
    storage: StorageAssumptions,
    pricing: PricingConfig,
) -> StorageCostResult:
    """Assemble the full storage-cost result (active + archive + requests)."""
    active_cost = active_storage_cost(envelope_gb, storage.active_months, pricing)
    req_cost = request_cost(raw_total_gb, planned_egress_gb, pricing)
    archive_results, archive_monthly, archive_annual, archive_total = archive_storage_cost(
        inputs, volumes, per_file_type_gb, storage, pricing
    )

    trace = [
        TraceLine(
            label="Active S3 Standard storage",
            detail=(
                f"{envelope_gb} GB tiered @ S3 Standard rates x {storage.active_months} "
                f"month(s) = ${active_cost}"
            ),
        ),
        TraceLine(
            label="S3/API/lifecycle requests",
            detail=(
                f"Estimated from volume at {AVG_OBJECT_SIZE_GB} GB/object avg object size "
                f"= ${req_cost}"
            ),
        ),
    ]
    for r in archive_results:
        trace.append(
            TraceLine(
                label=f"{r.file_type} archive ({r.storage_class})",
                detail=(
                    f"${r.monthly_cost_usd}/month x {r.months_in_archive} months = "
                    f"${r.total_cost_usd}"
                ),
            )
        )

    return StorageCostResult(
        active_storage_cost_usd=active_cost,
        request_cost_usd=req_cost,
        archive_results=archive_results,
        archive_monthly_cost_usd=archive_monthly,
        archive_annual_cost_usd=archive_annual,
        archive_total_cost_usd=archive_total,
        trace=trace,
    )
