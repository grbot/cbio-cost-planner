"""Compute-stage/concurrency/working-storage calculation engine (spec 011).

Framework-independent (no Streamlit import), matching ``cbio_cost``
convention — ``views/compute.py`` only reads widgets, calls into this module,
and renders (spec 011 §10: "Do not hard-code the entire implementation
directly into Streamlit UI code").

Deterministic and transparent throughout: every stage carries its
:class:`~cbio_cost.evidence.Evidence`, and the WGS 30x reference workflow is
the only workflow modelled in V1 (spec 011 objective).
"""

from __future__ import annotations

import math
from decimal import Decimal

from cbio_cost import compute_benchmarks as bm
from cbio_cost.compute_models import (
    AwsExecutionInfo,
    ComputeConfig,
    ComputeResult,
    ComputeStage,
    ConcurrencyResult,
    SentieonInfo,
    WorkingStorageResult,
)
from cbio_cost.evidence import Evidence

# ---------------------------------------------------------------------------
# Workflow stages (spec 011 §6, §10)
# ---------------------------------------------------------------------------


def build_alignment_stage() -> ComputeStage:
    """BWA-MEM2 + sort planning profile (spec 011 §6)."""
    return ComputeStage(
        name="BWA-MEM2 + sort",
        workflow_stage="Alignment",
        scope="per_sample",
        cpu=bm.BWA_ALLOCATED_CPU,
        memory_gib=bm.ALIGNMENT_PLANNING_RAM_GIB,
        runtime_hours=bm.BWA_WALL_TIME_HOURS,
        working_storage_gib=None,
        accelerator=None,
        software="bwa-mem2 + samtools sort",
        status="Implemented",
        evidence={
            "cpu": bm.BWA_CPU_EVIDENCE,
            "memory": bm.ALIGNMENT_PLANNING_RAM_EVIDENCE,
            "measured_peak_memory": bm.BWA_MEASURED_RAM_EVIDENCE,
            "runtime": bm.BWA_RUNTIME_EVIDENCE,
            "cpu_utilisation": bm.BWA_CPU_UTILISATION_EVIDENCE,
        },
        included_in_total=True,
    )


def build_cram_index_stage() -> ComputeStage:
    """CRAM indexing — lightweight downstream operation (spec 011 §5)."""
    return ComputeStage(
        name="CRAM index",
        workflow_stage="Alignment",
        scope="per_sample",
        cpu=None,
        memory_gib=None,
        runtime_hours=bm.CRAM_INDEX_WALL_TIME_HOURS,
        working_storage_gib=None,
        accelerator=None,
        software="samtools index",
        status="Implemented",
        evidence={"runtime": bm.CRAM_INDEX_RUNTIME_EVIDENCE},
        included_in_total=False,
    )


def build_deepvariant_stage() -> ComputeStage:
    """DeepVariant v1.10 published benchmark (spec 011 §8)."""
    return ComputeStage(
        name="DeepVariant",
        workflow_stage="Variant calling",
        scope="per_sample",
        cpu=96,
        memory_gib=Decimal(384),
        runtime_hours=bm.DEEPVARIANT_RUNTIME_HOURS,
        working_storage_gib=None,
        accelerator=None,
        software=bm.DEEPVARIANT_VERSION,
        status="Implemented",
        evidence={"runtime": bm.DEEPVARIANT_RUNTIME_EVIDENCE},
        included_in_total=True,
    )


def build_glnexus_stage() -> ComputeStage:
    """GLnexus cohort joint calling — no approved planning benchmark (spec 011 §9)."""
    return ComputeStage(
        name="GLnexus",
        workflow_stage="Cohort joint calling",
        scope="cohort",
        cpu=None,
        memory_gib=None,
        runtime_hours=None,
        working_storage_gib=None,
        accelerator=None,
        software="GLnexus",
        status=bm.GLNEXUS_STATUS,
        evidence={},
        included_in_total=False,
    )


# ---------------------------------------------------------------------------
# Concurrency model (spec 011 §14)
# ---------------------------------------------------------------------------


def concurrency_result(
    stage_name: str,
    samples: int,
    concurrency: int,
    runtime_per_unit_hours: Decimal,
    runtime_evidence: Evidence,
    runtime_basis: str,
) -> ConcurrencyResult:
    """Idealised planning waves/elapsed-time for one per-sample stage.

    ``waves = ceil(samples / concurrency)``; elapsed time is idealised and
    excludes queue delay, instance startup, retries, staging, interruptions,
    contention and workflow overhead (spec 011 §14).
    """
    if samples <= 0:
        raise ValueError("samples must be positive")
    if concurrency <= 0:
        raise ValueError("concurrency must be positive")
    if runtime_per_unit_hours < 0:
        raise ValueError("runtime_per_unit_hours cannot be negative")

    waves = math.ceil(Decimal(samples) / Decimal(concurrency))
    worker_hours = Decimal(samples) * runtime_per_unit_hours
    idealised_elapsed_hours = Decimal(waves) * runtime_per_unit_hours

    return ConcurrencyResult(
        stage_name=stage_name,
        samples=samples,
        concurrency=concurrency,
        runtime_per_unit_hours=runtime_per_unit_hours,
        waves=waves,
        worker_hours=worker_hours,
        idealised_elapsed_hours=idealised_elapsed_hours,
        runtime_evidence=runtime_evidence,
        runtime_basis=runtime_basis,
    )


def _stage_concurrency(
    stage_name: str,
    samples: int,
    concurrency: int,
    benchmark_hours: Decimal,
    benchmark_evidence: Evidence,
    override_hours: Decimal | None,
) -> ConcurrencyResult:
    if override_hours is not None:
        return concurrency_result(
            stage_name, samples, concurrency, override_hours, benchmark_evidence, "user_override"
        )
    return concurrency_result(
        stage_name, samples, concurrency, benchmark_hours, benchmark_evidence, "benchmark"
    )


# ---------------------------------------------------------------------------
# Working storage (spec 011 §12-§13)
# ---------------------------------------------------------------------------


def working_storage_result(scratch_per_worker_gib: Decimal, concurrent_workers: int) -> WorkingStorageResult:
    """``simultaneous working storage = scratch per worker x concurrent workers``
    (spec 011 §13)."""
    if scratch_per_worker_gib < 0:
        raise ValueError("scratch_per_worker_gib cannot be negative")
    if concurrent_workers <= 0:
        raise ValueError("concurrent_workers must be positive")

    return WorkingStorageResult(
        scratch_per_worker_gib=scratch_per_worker_gib,
        concurrent_workers=concurrent_workers,
        peak_simultaneous_gib=scratch_per_worker_gib * Decimal(concurrent_workers),
        evidence=bm.SCRATCH_EVIDENCE,
    )


# ---------------------------------------------------------------------------
# Sentieon (spec 011 §27)
# ---------------------------------------------------------------------------


def sentieon_info(num_samples: int, usd_zar: Decimal) -> SentieonInfo:
    total_usd = Decimal(num_samples) * bm.SENTIEON_USD_PER_GENOME
    return SentieonInfo(
        usd_per_genome=bm.SENTIEON_USD_PER_GENOME,
        num_samples=num_samples,
        total_usd=total_usd,
        total_zar=total_usd * usd_zar,
        evidence=bm.SENTIEON_EVIDENCE,
        status="Planned / not included in current workflow",
    )


# ---------------------------------------------------------------------------
# AWS execution architecture (spec 011 §20-§26)
# ---------------------------------------------------------------------------


def aws_execution_info() -> AwsExecutionInfo:
    return AwsExecutionInfo(
        region_code=bm.AWS_REGION_CODE,
        region_name=bm.AWS_REGION_NAME,
        architecture_steps=list(bm.AWS_ARCHITECTURE_STEPS),
        batch_orchestration_fee_usd=Decimal(0),
        purchase_model="On-Demand",
        pricing_status=bm.AWS_PRICING_STATUS,
        ec2_pricing=None,
    )


# ---------------------------------------------------------------------------
# Orchestration (spec 011 §10, §18)
# ---------------------------------------------------------------------------

LIMITATIONS: list[str] = [
    "The BWA-MEM2 benchmark is one measured NA12878 execution on Ilifu hardware.",
    "Performance varies by sample, reference, software version, CPU architecture, "
    "storage and configuration.",
    "AWS performance cannot be inferred exactly from Ilifu core counts.",
    "DeepVariant numbers are published benchmarks from a different cloud/platform.",
    "GLnexus is not yet included in total runtime.",
    "Workflow overhead, failures, retries and queue delays are not yet modelled.",
    "Working-storage defaults are planning assumptions until measured.",
    "Cost estimates are infrastructure planning estimates, not procurement quotations.",
]


def build_compute_result(num_samples: int, config: ComputeConfig, usd_zar: Decimal) -> ComputeResult:
    """Build the full Compute planning result for the current project's
    sample count and configuration."""
    alignment_stage = build_alignment_stage()
    cram_index_stage = build_cram_index_stage()
    deepvariant_stage = build_deepvariant_stage()
    glnexus_stage = build_glnexus_stage()

    alignment = _stage_concurrency(
        alignment_stage.name,
        num_samples,
        config.alignment_concurrency,
        bm.BWA_WALL_TIME_HOURS,
        bm.BWA_RUNTIME_EVIDENCE,
        config.alignment_runtime_override_hours,
    )
    deepvariant = _stage_concurrency(
        deepvariant_stage.name,
        num_samples,
        config.deepvariant_concurrency,
        bm.DEEPVARIANT_RUNTIME_HOURS,
        bm.DEEPVARIANT_RUNTIME_EVIDENCE,
        config.deepvariant_runtime_override_hours,
    )

    # V1 design decision (spec 011 §18): treat the two per-sample stages as
    # fully sequential across the whole cohort — a defensible worst-case, not
    # a pipelined estimate. CRAM indexing (lightweight) and GLnexus (no
    # approved benchmark) are excluded from this total.
    known_modelled_elapsed_hours = alignment.idealised_elapsed_hours + deepvariant.idealised_elapsed_hours

    working_storage = working_storage_result(
        config.scratch_gib_per_worker,
        max(config.alignment_concurrency, config.deepvariant_concurrency),
    )

    return ComputeResult(
        stages=[alignment_stage, cram_index_stage, deepvariant_stage, glnexus_stage],
        alignment=alignment,
        deepvariant=deepvariant,
        glnexus=glnexus_stage,
        working_storage=working_storage,
        known_modelled_elapsed_hours=known_modelled_elapsed_hours,
        excluded_stages=["GLnexus (cohort joint calling)", "CRAM index (folded into workflow overhead)"],
        aws=aws_execution_info(),
        sentieon=sentieon_info(num_samples, usd_zar),
        limitations=list(LIMITATIONS),
    )
