"""Endpoint-to-endpoint data-movement calculation engine (spec 012).

Framework-independent (no Streamlit import), matching ``cbio_cost``
convention — ``views/transfer.py`` only reads widgets, calls into this
module, and renders.

Deliberately named ``transfer_plan``, not ``transfer`` — ``cbio_cost/
transfer.py`` already exists and is Storage's own AWS-egress-cost engine
(spec 006 §6-§8, used by ``cbio_cost/calculator.py``), a different concern
from this module's endpoint-to-endpoint movement planning (spec 012 §17).
Neither module imports from the other; the only thing they share is the
same underlying AWS egress pricing config (reused here via
``cbio_cost.storage.tiered_cost``, never a second pricing source).
"""

from __future__ import annotations

from decimal import Decimal

from cbio_cost.evidence import Evidence
from cbio_cost.models import PricingConfig
from cbio_cost.project import Project
from cbio_cost.storage import tiered_cost
from cbio_cost.transfer_plan_models import (
    UNKNOWN_THROUGHPUT_SCENARIOS_MBPS,
    BdpResult,
    Endpoint,
    ProviderCostResult,
    ThroughputResult,
    TransferPlan,
    TransferPlanResult,
    TransferScenario,
)
from cbio_cost.units import gb_to_tb

# ---------------------------------------------------------------------------
# Units (spec 012 §10-§11): network throughput uses decimal units
# (1 Mbps = 1,000,000 bits/second); dataset size stays on the project's
# existing binary-GB/TB convention (cbio_cost.units). These are
# deliberately different unit systems and must not be mixed silently.
# ---------------------------------------------------------------------------

BYTES_PER_GB = Decimal(1024) ** 3
BITS_PER_BYTE = Decimal(8)
BITS_PER_SECOND_PER_MBPS = Decimal(10**6)

SECONDS_PER_HOUR = Decimal(3600)
HOURS_PER_DAY = Decimal(24)


def transfer_duration_seconds(size_gb: Decimal, throughput_mbps: Decimal) -> Decimal:
    """``seconds = size_GB x 1024^3 x 8 / (throughput_Mbps x 10^6)`` (spec 012 §11)."""
    if size_gb <= 0:
        raise ValueError("size_gb must be positive")
    if throughput_mbps <= 0:
        raise ValueError("throughput_mbps must be positive")
    return (size_gb * BYTES_PER_GB * BITS_PER_BYTE) / (throughput_mbps * BITS_PER_SECOND_PER_MBPS)


def duration_breakdown(seconds: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    """(hours, days) derived from seconds — kept at full internal precision;
    rounding only happens at display time (spec 012 §11, §29)."""
    hours = seconds / SECONDS_PER_HOUR
    days = hours / HOURS_PER_DAY
    return seconds, hours, days


def bandwidth_delay_product_bytes(throughput_mbps: Decimal, rtt_ms: Decimal) -> Decimal:
    """``BDP_bytes = throughput_bits_per_second x RTT_seconds / 8`` (spec 012 §21).

    Pure decimal-network-unit arithmetic — never mixed with the binary
    GB/TB dataset-size convention.
    """
    if throughput_mbps <= 0:
        raise ValueError("throughput_mbps must be positive")
    if rtt_ms < 0:
        raise ValueError("rtt_ms cannot be negative")
    throughput_bps = throughput_mbps * BITS_PER_SECOND_PER_MBPS
    rtt_seconds = rtt_ms / Decimal(1000)
    return (throughput_bps * rtt_seconds) / BITS_PER_BYTE


# ---------------------------------------------------------------------------
# Dataset presets (spec 012 §6-§7) — derived from the shared Project, never
# recomputed from per-sample rates, so WGS and Custom Project modes share
# one source of truth and Storage headroom is never silently added.
# ---------------------------------------------------------------------------


def dataset_presets(project: Project) -> dict[str, Decimal]:
    presets = {dataset.name: dataset.size_gb for dataset in project.datasets}
    if project.datasets:
        presets["All durable project data"] = sum((d.size_gb for d in project.datasets), Decimal(0))
    return presets


# ---------------------------------------------------------------------------
# Throughput (spec 012 §9, §23, §27)
# ---------------------------------------------------------------------------


def throughput_result(
    mode: str,
    measured_mbps: Decimal | None,
    measured_note: str,
    link_capacity_mbps: Decimal | None,
    efficiency_percent: Decimal | None,
) -> ThroughputResult:
    if mode == "measured":
        evidence = Evidence(
            classification="measured_throughput",
            source=measured_note or "User-supplied measured transfer throughput",
            date="",
            value=f"{measured_mbps} Mbps",
            notes="Do not treat a speed-test result as equivalent to sustained bulk-transfer throughput.",
        )
        return ThroughputResult(
            mode=mode,
            effective_mbps=measured_mbps,
            evidence=evidence,
            measured_mbps=measured_mbps,
            measured_note=measured_note,
        )
    if mode == "known_capacity":
        efficiency_fraction = efficiency_percent / Decimal(100)
        effective_mbps = link_capacity_mbps * efficiency_fraction
        evidence = Evidence(
            classification="planning_assumption",
            source="Known link capacity with a configurable planning-efficiency assumption",
            date="",
            value=f"{effective_mbps} Mbps",
            notes=(
                f"{link_capacity_mbps} Mbps link x {efficiency_percent}% planning efficiency. "
                "Applications rarely sustain theoretical line rate; do not assume 100% efficiency."
            ),
        )
        return ThroughputResult(
            mode=mode,
            effective_mbps=effective_mbps,
            evidence=evidence,
            link_capacity_mbps=link_capacity_mbps,
            efficiency_fraction=efficiency_fraction,
        )
    # "unknown" — no single throughput; the scenario table carries the numbers.
    return ThroughputResult(mode=mode, effective_mbps=None, evidence=None)


def _throughput_label(mbps: Decimal) -> str:
    if mbps >= 1000:
        return f"{mbps / Decimal(1000):g} Gbps"
    return f"{mbps:g} Mbps"


def unknown_throughput_scenarios(size_gb: Decimal) -> list[TransferScenario]:
    scenarios = []
    for mbps in UNKNOWN_THROUGHPUT_SCENARIOS_MBPS:
        seconds = transfer_duration_seconds(size_gb, mbps)
        _, hours, days = duration_breakdown(seconds)
        scenarios.append(
            TransferScenario(
                label=_throughput_label(mbps),
                throughput_mbps=mbps,
                duration_seconds=seconds,
                duration_hours=hours,
                duration_days=days,
            )
        )
    return scenarios


# ---------------------------------------------------------------------------
# Provider transfer cost (spec 012 §18-§19) — reuses the existing verified
# AWS egress pricing config via cbio_cost.storage.tiered_cost; never a
# second pricing source, never an invented ingress charge.
# ---------------------------------------------------------------------------


def provider_cost(source: Endpoint, destination: Endpoint, planned_gb: Decimal, pricing: PricingConfig) -> ProviderCostResult:
    if source.type == "aws_s3" and destination.type != "aws_s3":
        billable_gb = max(planned_gb - pricing.egress.free_allowance_gb_per_month, Decimal(0))
        cost_usd = tiered_cost(billable_gb, pricing.egress.tiers)
        evidence = Evidence(
            classification="provider_pricing",
            source=pricing.pricing_source,
            date=pricing.pricing_last_verified,
            value=f"${cost_usd}",
            notes=(
                f"AWS internet egress ({pricing.region_name}, `{pricing.region}`), reusing the "
                "same pricing configuration Storage uses. Not every AWS transfer necessarily uses "
                "public-internet egress (e.g. Direct Connect, inter-region) — those are not modelled."
            ),
        )
        return ProviderCostResult(
            status="calculated",
            cost_usd=cost_usd,
            basis=f"AWS internet egress, {pricing.region_name}",
            evidence=evidence,
        )
    if destination.type == "aws_s3" and source.type != "aws_s3":
        evidence = Evidence(
            classification="provider_pricing",
            source="AWS S3 does not charge for internet data transfer in",
            date=pricing.pricing_last_verified,
            value="$0",
            notes="AWS ingress is not charged. This does not cover S3 request/API costs, which are priced separately on Storage.",
        )
        return ProviderCostResult(status="calculated", cost_usd=Decimal(0), basis="AWS ingress (not charged)", evidence=evidence)
    return ProviderCostResult(
        status="not_calculated",
        cost_usd=None,
        basis="No verified provider transfer pricing for this endpoint pair.",
    )


# ---------------------------------------------------------------------------
# Explicit limitations (spec 012 §36)
# ---------------------------------------------------------------------------

LIMITATIONS: list[str] = [
    "Transfer duration assumes sustained effective throughput.",
    "Real throughput may vary over time.",
    "Link capacity is not equivalent to application throughput.",
    "Protocol overhead is represented only through the planning-efficiency assumption where applicable.",
    "RTT does not directly determine throughput in this model.",
    "BDP is informational and does not change the duration calculation.",
    "Provider transfer charges are not fully modelled.",
    "Institutional network bottlenecks are not automatically known.",
    "Transfer-method selection does not automatically alter throughput.",
    "The planner does not move genomic data itself.",
]


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def build_transfer_plan_result(plan: TransferPlan, pricing: PricingConfig) -> TransferPlanResult:
    """Build the full Transfer planning result for one configured plan."""
    throughput = throughput_result(
        plan.throughput_mode,
        plan.measured_mbps,
        plan.measured_note,
        plan.link_capacity_mbps,
        plan.efficiency_percent,
    )

    duration_seconds = duration_hours = duration_days = None
    scenarios: list[TransferScenario] = []
    if plan.throughput_mode == "unknown":
        scenarios = unknown_throughput_scenarios(plan.size_gb)
    else:
        duration_seconds = transfer_duration_seconds(plan.size_gb, throughput.effective_mbps)
        _, duration_hours, duration_days = duration_breakdown(duration_seconds)

    bdp = None
    if plan.rtt_ms is not None and throughput.effective_mbps is not None:
        bdp_bytes = bandwidth_delay_product_bytes(throughput.effective_mbps, plan.rtt_ms)
        bdp = BdpResult(rtt_ms=plan.rtt_ms, bdp_bytes=bdp_bytes, bdp_mb=bdp_bytes / Decimal(10**6))

    return TransferPlanResult(
        plan=plan,
        size_tb=gb_to_tb(plan.size_gb),
        throughput=throughput,
        duration_seconds=duration_seconds,
        duration_hours=duration_hours,
        duration_days=duration_days,
        scenarios=scenarios,
        provider_cost=provider_cost(plan.source, plan.destination, plan.size_gb, pricing),
        bdp=bdp,
        limitations=list(LIMITATIONS),
    )
