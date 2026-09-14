"""Data movement (egress) volume and AWS transfer cost calculations (spec §5, §6)."""

from __future__ import annotations

from decimal import Decimal

from cbio_cost.models import MovementAssumptions, PricingConfig, TraceLine, TransferResult
from cbio_cost.storage import tiered_cost


def fastq_egress(fastq_volume_gb: Decimal, fastq_passes: Decimal) -> Decimal:
    """AWS S3 -> Ilifu egress for FASTQ primary processing."""
    return fastq_volume_gb * fastq_passes


def cram_egress(cram_volume_gb: Decimal, retrieval_fraction: Decimal, retrieval_passes: Decimal) -> Decimal:
    """AWS S3 -> Ilifu egress for the subset of CRAMs that are retrieved."""
    return cram_volume_gb * retrieval_fraction * retrieval_passes


def gvcf_egress(gvcf_volume_gb: Decimal, passes: Decimal) -> Decimal:
    """AWS S3 -> Ilifu egress for gVCF joint-calling retrieval passes."""
    return gvcf_volume_gb * passes


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
    per_file_type_gb: dict[str, Decimal],
    movement: MovementAssumptions,
    pricing: PricingConfig,
) -> TransferResult:
    """Assemble the full data-movement/egress result (spec §5, §6)."""
    fastq_gb = per_file_type_gb.get("FASTQ", Decimal(0))
    cram_gb = per_file_type_gb.get("CRAM", Decimal(0))
    gvcf_gb = per_file_type_gb.get("gVCF", Decimal(0))

    fastq_e = fastq_egress(fastq_gb, movement.fastq_passes)
    cram_e = cram_egress(cram_gb, movement.cram_retrieval_fraction, movement.cram_retrieval_passes)
    gvcf_e = gvcf_egress(gvcf_gb, movement.gvcf_passes)

    per_file_type_egress_gb = {"FASTQ": fastq_e, "CRAM": cram_e, "gVCF": gvcf_e}
    base_egress_gb = fastq_e + cram_e + gvcf_e
    planned_egress_gb = apply_contingency(base_egress_gb, movement.transfer_contingency)
    egress_cost_usd = tiered_egress_cost(planned_egress_gb, pricing)

    trace = [
        TraceLine(
            label="FASTQ egress",
            detail=f"{fastq_gb} GB x {movement.fastq_passes} pass(es) = {fastq_e} GB",
        ),
        TraceLine(
            label="CRAM egress",
            detail=(
                f"{cram_gb} GB x {movement.cram_retrieval_fraction * 100}% retrieval x "
                f"{movement.cram_retrieval_passes} pass(es) = {cram_e} GB"
            ),
        ),
        TraceLine(
            label="gVCF egress",
            detail=f"{gvcf_gb} GB x {movement.gvcf_passes} pass(es) = {gvcf_e} GB",
        ),
        TraceLine(
            label="Base egress",
            detail=f"{fastq_e} + {cram_e} + {gvcf_e} GB = {base_egress_gb} GB",
        ),
        TraceLine(
            label="Planned egress (with contingency)",
            detail=(
                f"{base_egress_gb} GB x (1 + {movement.transfer_contingency * 100}%) = "
                f"{planned_egress_gb} GB"
            ),
        ),
        TraceLine(
            label="AWS egress cost",
            detail=(
                f"{planned_egress_gb} GB, less {pricing.egress.free_allowance_gb_per_month} GB "
                f"free allowance, tiered @ af-south-1 egress rates = ${egress_cost_usd}"
            ),
        ),
    ]

    return TransferResult(
        per_file_type_egress_gb=per_file_type_egress_gb,
        base_egress_gb=base_egress_gb,
        planned_egress_gb=planned_egress_gb,
        egress_cost_usd=egress_cost_usd,
        trace=trace,
    )
