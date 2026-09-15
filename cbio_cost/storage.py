"""Data volume and S3/Glacier storage cost calculations (spec §4, §7, §8, §9;
spec 006 §13-§17: every calculation runs per-dataset off the generic
``Dataset`` model, then sums across datasets — the same code path for WGS
30x and Custom Project)."""

from __future__ import annotations

from decimal import Decimal

from cbio_cost.models import (
    Dataset,
    DatasetStorageResult,
    DatasetVolumeDetail,
    PriceTier,
    PricingConfig,
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


def calculate_data_volume(datasets: list[Dataset], headroom_fraction: Decimal) -> VolumeResult:
    """Compute per-dataset and total durable data volume, plus the
    provisioned planning envelope after headroom (spec §4; spec 006 §5, §15).
    Never rounds."""
    details: list[DatasetVolumeDetail] = []
    trace: list[TraceLine] = []
    for dataset in datasets:
        envelope_gb = dataset.size_gb * (Decimal(1) + headroom_fraction)
        details.append(DatasetVolumeDetail(name=dataset.name, size_gb=dataset.size_gb, envelope_gb=envelope_gb))
        trace.append(
            TraceLine(
                label=f"{dataset.name} size",
                detail=f"{dataset.size_gb} GB",
            )
        )

    raw_total_gb = sum((d.size_gb for d in details), Decimal(0))
    trace.append(
        TraceLine(
            label="Total durable project volume",
            detail=" + ".join(f"{d.size_gb} GB" for d in details) + f" = {raw_total_gb} GB",
        )
    )

    envelope_gb = raw_total_gb * (Decimal(1) + headroom_fraction)
    trace.append(
        TraceLine(
            label="Provisioned envelope",
            detail=f"{raw_total_gb} GB x (1 + {headroom_fraction * 100}%) = {envelope_gb} GB",
        )
    )

    return VolumeResult(
        datasets=details,
        raw_total_gb=raw_total_gb,
        envelope_gb=envelope_gb,
        trace=trace,
    )


def request_cost(raw_total_gb: Decimal, planned_egress_gb: Decimal, pricing: PricingConfig) -> Decimal:
    """Estimate S3 PUT/GET/lifecycle-transition request costs (spec §1, §6).

    Individual object counts aren't tracked by this planning tool, so request
    counts are estimated from total project volume using an assumed average
    object size. This is a coarse planning approximation, not a
    billing-accurate count, and is modelled once across the whole project
    rather than per dataset.
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


def _dataset_storage_result(
    dataset: Dataset,
    headroom_fraction: Decimal,
    retention_months: Decimal,
    pricing: PricingConfig,
) -> tuple[DatasetStorageResult, TraceLine]:
    envelope_gb = dataset.size_gb * (Decimal(1) + headroom_fraction)
    s3_standard = pricing.storage_classes["s3_standard"]
    s3_monthly_cost = tiered_cost(envelope_gb, s3_standard.tiers)

    if dataset.archive_class == "s3_standard":
        # S3-Standard-only dataset: no lifecycle transition, so it simply
        # stays in S3 Standard for the whole retention period (spec 006 §14).
        active_cost = s3_monthly_cost * retention_months
        result = DatasetStorageResult(
            name=dataset.name,
            archive_class=dataset.archive_class,
            active_storage_cost_usd=active_cost,
            months_in_archive=Decimal(0),
            archive_monthly_cost_usd=Decimal(0),
            archive_total_cost_usd=Decimal(0),
            minimum_duration_warning=None,
            retrieval_characteristics=s3_standard.retrieval_characteristics,
            requires_restore=False,
        )
        trace = TraceLine(
            label=f"{dataset.name} storage (S3 Standard, full retention)",
            detail=(
                f"{envelope_gb} GB tiered @ S3 Standard rates x {retention_months} month(s) "
                f"= ${active_cost}"
            ),
        )
        return result, trace

    active_months = min(dataset.active_months, retention_months)
    active_cost = s3_monthly_cost * active_months
    months_in_archive = retention_months - active_months
    if months_in_archive < 0:
        months_in_archive = Decimal(0)

    storage_class = pricing.storage_classes[dataset.archive_class]
    archive_monthly_cost = tiered_cost(envelope_gb, storage_class.tiers)
    archive_total_cost = archive_monthly_cost * months_in_archive

    warning: str | None = None
    archived_days = months_in_archive * APPROX_DAYS_PER_MONTH
    if 0 < archived_days < storage_class.minimum_storage_duration_days:
        warning = (
            f"{dataset.name} is planned to remain in {storage_class.label} for only "
            f"~{archived_days:.0f} days, below its "
            f"{storage_class.minimum_storage_duration_days}-day minimum storage "
            "duration; early deletion/transition fees may apply."
        )

    result = DatasetStorageResult(
        name=dataset.name,
        archive_class=dataset.archive_class,
        active_storage_cost_usd=active_cost,
        months_in_archive=months_in_archive,
        archive_monthly_cost_usd=archive_monthly_cost,
        archive_total_cost_usd=archive_total_cost,
        minimum_duration_warning=warning,
        retrieval_characteristics=storage_class.retrieval_characteristics,
        requires_restore=storage_class.requires_restore,
    )
    trace = TraceLine(
        label=f"{dataset.name} storage ({storage_class.label})",
        detail=(
            f"Active: {envelope_gb} GB tiered @ S3 Standard rates x {active_months} month(s) "
            f"= ${active_cost}; Archive: ${archive_monthly_cost}/month x {months_in_archive} "
            f"months = ${archive_total_cost}"
        ),
    )
    return result, trace


def build_storage_cost_result(
    datasets: list[Dataset],
    raw_total_gb: Decimal,
    planned_egress_gb: Decimal,
    headroom_fraction: Decimal,
    retention_years: Decimal,
    pricing: PricingConfig,
) -> StorageCostResult:
    """Assemble the full storage-cost result: active + archive storage
    calculated independently per dataset then summed, plus one project-level
    request-cost estimate (spec 006 §17)."""
    retention_months = retention_years * MONTHS_PER_YEAR

    results: list[DatasetStorageResult] = []
    trace: list[TraceLine] = []
    for dataset in datasets:
        result, dataset_trace = _dataset_storage_result(dataset, headroom_fraction, retention_months, pricing)
        results.append(result)
        trace.append(dataset_trace)

    req_cost = request_cost(raw_total_gb, planned_egress_gb, pricing)
    trace.append(
        TraceLine(
            label="S3/API/lifecycle requests",
            detail=(
                f"Estimated from volume at {AVG_OBJECT_SIZE_GB} GB/object avg object size "
                f"= ${req_cost}"
            ),
        )
    )

    active_total = sum((r.active_storage_cost_usd for r in results), Decimal(0))
    archive_monthly_total = sum((r.archive_monthly_cost_usd for r in results), Decimal(0))
    archive_annual_total = archive_monthly_total * MONTHS_PER_YEAR
    archive_total = sum((r.archive_total_cost_usd for r in results), Decimal(0))

    return StorageCostResult(
        datasets=results,
        active_storage_cost_usd=active_total,
        request_cost_usd=req_cost,
        archive_monthly_cost_usd=archive_monthly_total,
        archive_annual_cost_usd=archive_annual_total,
        archive_total_cost_usd=archive_total,
        trace=trace,
    )
