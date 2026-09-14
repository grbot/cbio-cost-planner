"""Top-level orchestration: build a full cost estimate and scenario comparisons.

This is the only module the Streamlit UI should call into for calculations
(spec §2, §19: no calculation logic duplicated between UI and backend).
"""

from __future__ import annotations

import math
from decimal import Decimal

from cbio_cost.models import (
    CostEstimate,
    CostLineItem,
    CurrencyAssumptions,
    EngineeringAssumptions,
    FileTypeVolumeAssumption,
    MovementAssumptions,
    PricingConfig,
    ProjectInputs,
    StorageAssumptions,
)
from cbio_cost.operations import build_operations_cost_result
from cbio_cost.storage import build_storage_cost_result, calculate_data_volume
from cbio_cost.transfer import build_transfer_result
from cbio_cost.units import gb_to_tb


def _usd_to_zar_inc_vat(amount_usd: Decimal, currency: CurrencyAssumptions) -> Decimal:
    return amount_usd * currency.usd_zar * (Decimal(1) + currency.vat_fraction)


def build_estimate(
    inputs: ProjectInputs,
    volumes: dict[str, FileTypeVolumeAssumption],
    storage: StorageAssumptions,
    movement: MovementAssumptions,
    engineering: EngineeringAssumptions,
    pricing: PricingConfig,
    currency: CurrencyAssumptions,
) -> CostEstimate:
    """Compute a complete cost estimate for one set of inputs/assumptions."""
    volume = calculate_data_volume(inputs, volumes, storage)
    transfer = build_transfer_result(volume.per_file_type_gb, movement, pricing)
    storage_cost = build_storage_cost_result(
        inputs,
        volumes,
        volume.per_file_type_gb,
        volume.raw_total_gb,
        volume.envelope_gb,
        transfer.planned_egress_gb,
        storage,
        pricing,
    )
    operations_cost = build_operations_cost_result(inputs, engineering)

    total_aws_usd = (
        storage_cost.active_storage_cost_usd
        + storage_cost.request_cost_usd
        + storage_cost.archive_total_cost_usd
        + transfer.egress_cost_usd
    )
    total_aws_zar_ex_vat = total_aws_usd * currency.usd_zar
    total_aws_zar_inc_vat = total_aws_zar_ex_vat * (Decimal(1) + currency.vat_fraction)
    total_engineering_zar = operations_cost.total_zar
    grand_total_zar = total_aws_zar_inc_vat + total_engineering_zar

    line_items = [
        CostLineItem(
            "Project onboarding", operations_cost.onboarding_cost_zar, "Engineering (ZAR)"
        ),
        CostLineItem(
            "Active S3 storage",
            _usd_to_zar_inc_vat(storage_cost.active_storage_cost_usd, currency),
            "AWS (USD to ZAR, incl. VAT)",
        ),
        CostLineItem(
            "S3/API/lifecycle requests",
            _usd_to_zar_inc_vat(storage_cost.request_cost_usd, currency),
            "AWS (USD to ZAR, incl. VAT)",
        ),
        CostLineItem(
            "AWS to Ilifu transfer",
            _usd_to_zar_inc_vat(transfer.egress_cost_usd, currency),
            "AWS (USD to ZAR, incl. VAT)",
        ),
        CostLineItem(
            "Archive storage",
            _usd_to_zar_inc_vat(storage_cost.archive_total_cost_usd, currency),
            "AWS (USD to ZAR, incl. VAT)",
        ),
        CostLineItem(
            "Operational management", operations_cost.operations_cost_zar, "Engineering (ZAR)"
        ),
        CostLineItem("Project closeout", operations_cost.closeout_cost_zar, "Engineering (ZAR)"),
        CostLineItem("Total project infrastructure cost", grand_total_zar, ""),
    ]

    return CostEstimate(
        inputs=inputs,
        volume=volume,
        transfer=transfer,
        storage=storage_cost,
        operations=operations_cost,
        currency=currency,
        total_aws_usd=total_aws_usd,
        total_aws_zar_ex_vat=total_aws_zar_ex_vat,
        total_aws_zar_inc_vat=total_aws_zar_inc_vat,
        total_engineering_zar=total_engineering_zar,
        grand_total_zar=grand_total_zar,
        line_items=line_items,
    )


def build_scenarios(
    inputs: ProjectInputs,
    volumes: dict[str, FileTypeVolumeAssumption],
    storage: StorageAssumptions,
    engineering: EngineeringAssumptions,
    pricing: PricingConfig,
    currency: CurrencyAssumptions,
    scenario_movements: dict[str, MovementAssumptions],
) -> dict[str, CostEstimate]:
    """Build one :class:`CostEstimate` per named scenario (spec §13)."""
    return {
        name: build_estimate(inputs, volumes, storage, movement, engineering, pricing, currency)
        for name, movement in scenario_movements.items()
    }


def explain_result(estimate: CostEstimate) -> str:
    """Deterministic plain-English summary of an estimate (spec §15).

    Generated entirely from computed values via string formatting — no LLM.
    """
    inputs = estimate.inputs
    raw_tb = gb_to_tb(estimate.volume.raw_total_gb)
    envelope_tb = gb_to_tb(estimate.volume.envelope_gb)
    egress_tb = gb_to_tb(estimate.transfer.planned_egress_gb)
    rounded_envelope_tb = Decimal(math.ceil(envelope_tb / 10) * 10)

    return (
        f"This {inputs.num_samples}-sample {inputs.project_type} project is estimated to "
        f"generate approximately {raw_tb:.1f} TB of durable genomic data. With operational "
        f"headroom, a {envelope_tb:.1f} TB storage envelope is appropriate, which may be "
        f"rounded operationally to a {rounded_envelope_tb:.0f} TB project allocation. The "
        f"expected AWS-to-Ilifu data movement is approximately {egress_tb:.1f} TB under the "
        "selected workflow assumptions. Because AWS internet egress is charged while ingress "
        "is generally free, transfer behaviour is an important component of the total project "
        "cost."
    )
