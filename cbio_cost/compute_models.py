"""Typed data structures for the Compute domain model (spec 011 §10).

Mirrors the ``cbio_cost/models.py`` convention (plain dataclasses, Decimal
fractions/quantities, no Streamlit import) but is kept in its own module
because Compute is a separate, newer domain from Storage/Transfer. This
separation is deliberate (spec 011 §10): later workflow options (Sentieon,
GATK, DRAGEN/ICA, custom workflows, GPU workflows, alternative clouds, local
HPC) should be addable without rewriting Storage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from cbio_cost.evidence import Evidence


@dataclass
class ComputeStage:
    """One workflow-processing stage (spec 011 §10)."""

    name: str
    workflow_stage: str
    scope: str  # "per_sample" | "cohort"
    cpu: int | None
    memory_gib: Decimal | None
    runtime_hours: Decimal | None
    working_storage_gib: Decimal | None
    accelerator: str | None
    software: str
    status: str
    evidence: dict[str, Evidence] = field(default_factory=dict)
    included_in_total: bool = False


@dataclass
class ConcurrencyResult:
    """Idealised planning elapsed-time/worker-hours for one per-sample stage
    (spec 011 §14). ``configured_concurrency`` is the user's raw setting;
    ``effective_concurrency`` is capped at the sample count, since only one
    per-sample task can actually be active per sample (spec 011b §2)."""

    stage_name: str
    samples: int
    configured_concurrency: int
    effective_concurrency: int
    runtime_per_unit_hours: Decimal
    waves: int
    worker_hours: Decimal
    idealised_elapsed_hours: Decimal
    runtime_evidence: Evidence
    runtime_basis: str  # "benchmark" | "user_override"


@dataclass
class WorkingStorageResult:
    """Simultaneous working/scratch storage requirement (spec 011 §13; stage-
    specific peak logic refined in spec 011a §12; peaks driven by effective,
    not configured, concurrency since spec 011b §4)."""

    scratch_per_worker_gib: Decimal
    alignment_configured_concurrency: int
    alignment_effective_concurrency: int
    deepvariant_configured_concurrency: int
    deepvariant_effective_concurrency: int
    alignment_peak_gib: Decimal
    deepvariant_peak_gib: Decimal
    peak_simultaneous_gib: Decimal
    evidence: Evidence


@dataclass
class EC2InstancePricing:
    """Verified EC2 pricing metadata (spec 011 §23) — reserved extension
    point. Not populated in V1: no verified af-south-1 EC2 pricing exists in
    this repository, and the spec explicitly forbids inventing it."""

    provider: str
    region: str
    instance_type: str
    purchase_model: str
    usd_per_hour: Decimal
    source: str
    date_verified: str


@dataclass
class AwsExecutionInfo:
    """Initial AWS execution-architecture recommendation (spec 011 §20-§26)."""

    region_code: str
    region_name: str
    architecture_steps: list[str]
    batch_orchestration_fee_usd: Decimal
    purchase_model: str
    pricing_status: str
    ec2_pricing: EC2InstancePricing | None = None


@dataclass
class HpcExecutionInfo:
    """Ilifu/institutional HPC as an execution environment in its own right,
    not merely the source of the BWA-MEM2 benchmark (spec 011a §18)."""

    status: str
    alignment_runtime_evidence: Evidence
    deepvariant_runtime_evidence: Evidence
    glnexus_status: str
    monetary_cost_status: str
    working_storage_status: str
    scheduling_status: str


@dataclass
class SentieonInfo:
    """Sentieon licensing figure — excluded from current workflow totals
    (spec 011 §27)."""

    usd_per_genome: Decimal
    num_samples: int
    total_usd: Decimal
    total_zar: Decimal
    evidence: Evidence
    status: str


@dataclass
class ComputeConfig:
    """User-editable Compute planning configuration (spec 011 §17)."""

    alignment_concurrency: int
    deepvariant_concurrency: int
    scratch_gib_per_worker: Decimal
    alignment_runtime_override_hours: Decimal | None = None
    deepvariant_runtime_override_hours: Decimal | None = None

    def __post_init__(self) -> None:
        if self.alignment_concurrency <= 0:
            raise ValueError("alignment_concurrency must be positive")
        if self.deepvariant_concurrency <= 0:
            raise ValueError("deepvariant_concurrency must be positive")
        if self.scratch_gib_per_worker < 0:
            raise ValueError("scratch_gib_per_worker cannot be negative")


@dataclass
class ComputeResult:
    """Full Compute planning result for one project (spec 011 §10, §18-§19;
    CRAM-index inclusion and HPC execution info added in spec 011a)."""

    stages: list[ComputeStage]
    alignment: ConcurrencyResult
    cram_index: ConcurrencyResult
    deepvariant: ConcurrencyResult
    glnexus: ComputeStage
    working_storage: WorkingStorageResult
    known_modelled_elapsed_hours: Decimal
    excluded_stages: list[str]
    unmodelled_overhead: str
    aws: AwsExecutionInfo
    hpc: HpcExecutionInfo
    sentieon: SentieonInfo
    limitations: list[str]
