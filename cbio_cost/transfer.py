"""Data movement (egress) volume and AWS transfer cost calculations (spec §5, §6;
spec 006 §6-§8: egress is computed per dataset from its own retrieval
fraction and read-pass count, then summed and contingency-adjusted at the
project level)."""

from __future__ import annotations

from decimal import Decimal

from cbio_cost.models import Dataset, DatasetEgressDetail, PricingConfig, TraceLine, TransferResult
from cbio_cost.storage import tiered_cost


def dataset_base_egress_gb(dataset: Dataset) -> Decimal:
    """AWS S3 -> Ilifu base workflow egress for one dataset (spec 006 §8).

    base workflow egress = dataset size x retrieval fraction x read passes
    """
    return dataset.size_gb * dataset.retrieval_fraction * dataset.read_passes


def apply_contingency(base_egress_gb: Decimal, contingency_fraction: Decimal) -> Decimal:
    """Apply the transfer contingency to base egress (spec §5)."""
    return base_egress_gb * (Decimal(1) + contingency_fraction)


def tiered_egress_cost(quantity_gb: Decimal, pricing: PricingConfig) -> Decimal:
    """Tiered AWS egress cost after the configurable free allowance (spec §6).

    The free allowance is treated as a single planning-level deduction from
    total planned egress (not a recurring monthly allowance), consistent
    with this tool being a project-lifetime planning estimate rather than a
    month-by-month billing simulation.
    """
    billable_gb = quantity_gb - pricing.egress.free_allowance_gb_per_month
    if billable_gb < 0:
        billable_gb = Decimal(0)
    return tiered_cost(billable_gb, pricing.egress.tiers)


def build_transfer_result(
    datasets: list[Dataset],
    transfer_contingency: Decimal,
    pricing: PricingConfig,
) -> TransferResult:
    """Assemble the full data-movement/egress result (spec §5, §6; spec 006 §8)."""
    details: list[DatasetEgressDetail] = []
    trace: list[TraceLine] = []
    for dataset in datasets:
        egress_gb = dataset_base_egress_gb(dataset)
        details.append(DatasetEgressDetail(name=dataset.name, base_egress_gb=egress_gb))
        trace.append(
            TraceLine(
                label=f"{dataset.name} base workflow egress",
                detail=(
                    f"{dataset.size_gb} GB x {dataset.retrieval_fraction * 100}% retrieval x "
                    f"{dataset.read_passes} pass(es) = {egress_gb} GB"
                ),
            )
        )

    base_egress_gb = sum((d.base_egress_gb for d in details), Decimal(0))
    planned_egress_gb = apply_contingency(base_egress_gb, transfer_contingency)
    egress_cost_usd = tiered_egress_cost(planned_egress_gb, pricing)

    trace.append(
        TraceLine(
            label="Total base workflow egress",
            detail=" + ".join(f"{d.base_egress_gb} GB" for d in details) + f" = {base_egress_gb} GB",
        )
    )
    trace.append(
        TraceLine(
            label="Planned egress (with contingency)",
            detail=(
                f"{base_egress_gb} GB x (1 + {transfer_contingency * 100}%) = {planned_egress_gb} GB"
            ),
        )
    )
    trace.append(
        TraceLine(
            label="AWS egress cost",
            detail=(
                f"{planned_egress_gb} GB, less {pricing.egress.free_allowance_gb_per_month} GB "
                f"free allowance, tiered @ af-south-1 egress rates = ${egress_cost_usd}"
            ),
        )
    )

    return TransferResult(
        datasets=details,
        base_egress_gb=base_egress_gb,
        planned_egress_gb=planned_egress_gb,
        egress_cost_usd=egress_cost_usd,
        trace=trace,
    )
