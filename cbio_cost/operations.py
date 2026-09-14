"""Infrastructure engineering effort costing (spec §10)."""

from __future__ import annotations

from decimal import Decimal

from cbio_cost.models import EngineeringAssumptions, OperationsCostResult, ProjectInputs, TraceLine


def onboarding_cost(engineering: EngineeringAssumptions) -> Decimal:
    return engineering.onboarding_hours * engineering.hourly_rate_zar


def operations_cost(engineering: EngineeringAssumptions, retention_years: Decimal) -> Decimal:
    """Ongoing operations cost over the full project lifetime."""
    return engineering.operations_hours_per_year * retention_years * engineering.hourly_rate_zar


def closeout_cost(engineering: EngineeringAssumptions) -> Decimal:
    return engineering.closeout_hours * engineering.hourly_rate_zar


def build_operations_cost_result(
    inputs: ProjectInputs, engineering: EngineeringAssumptions
) -> OperationsCostResult:
    onboarding = onboarding_cost(engineering)
    operations = operations_cost(engineering, inputs.retention_years)
    closeout = closeout_cost(engineering)
    total = onboarding + operations + closeout

    trace = [
        TraceLine(
            label="Onboarding",
            detail=(
                f"{engineering.onboarding_hours} hours x R{engineering.hourly_rate_zar}/hour = "
                f"R{onboarding}"
            ),
        ),
        TraceLine(
            label="Ongoing operations",
            detail=(
                f"{engineering.operations_hours_per_year} hours/year x {inputs.retention_years} "
                f"years x R{engineering.hourly_rate_zar}/hour = R{operations}"
            ),
        ),
        TraceLine(
            label="Closeout",
            detail=(
                f"{engineering.closeout_hours} hours x R{engineering.hourly_rate_zar}/hour = "
                f"R{closeout}"
            ),
        ),
    ]

    return OperationsCostResult(
        onboarding_cost_zar=onboarding,
        operations_cost_zar=operations,
        closeout_cost_zar=closeout,
        total_zar=total,
        trace=trace,
    )
