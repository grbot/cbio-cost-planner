"""Typed data structures for the Transfer domain model (spec 012 §3-§9, §13).

Mirrors the ``cbio_cost/compute_models.py`` convention (plain dataclasses,
Decimal fractions/quantities, no Streamlit import). Kept in its own module,
distinct from the pre-existing ``cbio_cost/transfer.py`` — that module is
Storage's own AWS-egress-cost engine (spec 006 §6-§8), unrelated to this
endpoint-to-endpoint data-movement planner; see ``cbio_cost/transfer_plan.py``
for why the two are named differently and never import from each other.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from cbio_cost.evidence import Evidence

ENDPOINT_TYPES: dict[str, str] = {
    "institutional": "Institutional / local storage",
    "ilifu": "Ilifu / HPC",
    "aws_s3": "AWS S3",
    "ica": "Illumina ICA",
    "other_object_storage": "Other object storage",
    "custom": "Custom endpoint",
}

TRANSFER_METHODS: list[str] = [
    "Not yet selected",
    "Globus",
    "AWS CLI / S3 multipart",
    "rclone",
    "Institutional DTN",
    "Illumina ICA transfer",
    "Other",
]

THROUGHPUT_MODES: dict[str, str] = {
    "measured": "Measured throughput",
    "known_capacity": "Known link capacity",
    "unknown": "Unknown throughput",
}

UNKNOWN_THROUGHPUT_SCENARIOS_MBPS: list[Decimal] = [
    Decimal(100),
    Decimal(500),
    Decimal(1000),
    Decimal(5000),
    Decimal(10000),
]

DEFAULT_EFFICIENCY_PERCENT = Decimal(70)


@dataclass
class Endpoint:
    """One transfer endpoint (spec 012 §4-§5). ``label`` is the resolved
    display name — the custom name when ``type == "custom"``, otherwise
    ``ENDPOINT_TYPES[type]``. ``location`` is purely descriptive (spec 012
    §20) and must never be used to infer bandwidth."""

    type: str
    label: str
    location: str = ""

    def __post_init__(self) -> None:
        if self.type not in ENDPOINT_TYPES:
            raise ValueError(f"Unknown endpoint type '{self.type}'")
        if self.type == "custom" and not self.label.strip():
            raise ValueError("Custom endpoint name cannot be blank")


@dataclass
class ThroughputResult:
    """The throughput basis actually used in the duration calculation
    (spec 012 §9, §27) — always traceable to one of the three modes."""

    mode: str  # "measured" | "known_capacity" | "unknown"
    effective_mbps: Decimal | None
    evidence: Evidence | None
    measured_mbps: Decimal | None = None
    measured_note: str = ""
    link_capacity_mbps: Decimal | None = None
    efficiency_fraction: Decimal | None = None


@dataclass
class ProviderCostResult:
    """Provider transfer-cost status (spec 012 §18-§19) — ``cost_usd`` is
    ``None``, never ``Decimal(0)``, whenever cost applicability has not been
    verified for this endpoint pair."""

    status: str  # "calculated" | "not_calculated"
    cost_usd: Decimal | None
    basis: str
    evidence: Evidence | None = None


@dataclass
class BdpResult:
    """Bandwidth-delay product (spec 012 §21) — informational only, never
    additional project storage and never fed back into the duration
    calculation (spec 012 §22)."""

    rtt_ms: Decimal
    bdp_bytes: Decimal
    bdp_mb: Decimal


@dataclass
class TransferPlan:
    """User-editable Transfer planning configuration (spec 012 §3, §24-§27, §35)."""

    dataset_name: str
    size_gb: Decimal
    source: Endpoint
    destination: Endpoint
    throughput_mode: str
    transfer_method: str
    measured_mbps: Decimal | None = None
    measured_note: str = ""
    link_capacity_mbps: Decimal | None = None
    efficiency_percent: Decimal | None = None
    rtt_ms: Decimal | None = None

    def __post_init__(self) -> None:
        if self.size_gb <= 0:
            raise ValueError("Dataset size must be greater than zero")
        if self.throughput_mode not in THROUGHPUT_MODES:
            raise ValueError(f"Unknown throughput mode '{self.throughput_mode}'")
        if self.throughput_mode == "measured":
            if self.measured_mbps is None or self.measured_mbps <= 0:
                raise ValueError("Measured throughput must be greater than zero")
        if self.throughput_mode == "known_capacity":
            if self.link_capacity_mbps is None or self.link_capacity_mbps <= 0:
                raise ValueError("Link capacity must be greater than zero")
            if self.efficiency_percent is None or not (Decimal(0) < self.efficiency_percent <= Decimal(100)):
                raise ValueError("Planning efficiency must be greater than 0% and at most 100%")
        if self.rtt_ms is not None and self.rtt_ms < 0:
            raise ValueError("Round-trip time cannot be negative")


@dataclass
class TransferScenario:
    """One row of the unknown-throughput planning-scenario table (spec 012 §9, §28)."""

    label: str
    throughput_mbps: Decimal
    duration_seconds: Decimal
    duration_hours: Decimal
    duration_days: Decimal


@dataclass
class TransferPlanResult:
    """Full Transfer planning result for one configured plan (spec 012 §15, §31)."""

    plan: TransferPlan
    size_tb: Decimal
    throughput: ThroughputResult
    duration_seconds: Decimal | None
    duration_hours: Decimal | None
    duration_days: Decimal | None
    scenarios: list[TransferScenario]
    provider_cost: ProviderCostResult
    bdp: BdpResult | None
    limitations: list[str] = field(default_factory=list)
