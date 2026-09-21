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
    HpcExecutionInfo,
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
    """CRAM indexing — measured, lightweight, explicitly included stage
    (spec 011a §8-§9)."""
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
        included_in_total=True,
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


def working_storage_result(
    scratch_per_worker_gib: Decimal,
    alignment_concurrency: int,
    deepvariant_concurrency: int,
) -> WorkingStorageResult:
    """Stage-specific working storage (spec 011a §12).

    The same per-worker scratch assumption is used for both stages, but each
    stage's peak scratch is driven by its own concurrency setting. Under the
    sequential-stage execution model, peak workflow scratch is the max of
    the two stage peaks, not their sum, unless the stages are explicitly
    modelled as running concurrently.
    """
    if scratch_per_worker_gib < 0:
        raise ValueError("scratch_per_worker_gib cannot be negative")
    if alignment_concurrency <= 0:
        raise ValueError("alignment_concurrency must be positive")
    if deepvariant_concurrency <= 0:
        raise ValueError("deepvariant_concurrency must be positive")

    alignment_peak_gib = scratch_per_worker_gib * Decimal(alignment_concurrency)
    deepvariant_peak_gib = scratch_per_worker_gib * Decimal(deepvariant_concurrency)

    return WorkingStorageResult(
        scratch_per_worker_gib=scratch_per_worker_gib,
        alignment_concurrency=alignment_concurrency,
        deepvariant_concurrency=deepvariant_concurrency,
        alignment_peak_gib=alignment_peak_gib,
        deepvariant_peak_gib=deepvariant_peak_gib,
        peak_simultaneous_gib=max(alignment_peak_gib, deepvariant_peak_gib),
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
# HPC execution environment (spec 011a §18)
# ---------------------------------------------------------------------------


def hpc_execution_info() -> HpcExecutionInfo:
    return HpcExecutionInfo(
        status=bm.HPC_STATUS,
        alignment_runtime_evidence=bm.BWA_RUNTIME_EVIDENCE,
        deepvariant_runtime_evidence=bm.DEEPVARIANT_RUNTIME_EVIDENCE,
        glnexus_status=bm.GLNEXUS_STATUS,
        monetary_cost_status=bm.HPC_MONETARY_COST_STATUS,
        working_storage_status=bm.HPC_WORKING_STORAGE_STATUS,
        scheduling_status=bm.HPC_SCHEDULING_STATUS,
    )


# ---------------------------------------------------------------------------
# Orchestration (spec 011 §10, §18)
# ---------------------------------------------------------------------------

LIMITATIONS: list[str] = [
    "The BWA-MEM2 benchmark is one measured NA12878 execution on Ilifu hardware.",
    "The 160 GiB alignment RAM allocation is a planning assumption; measured peak was "
    "approximately 116.7 GiB.",
    "Performance varies by sample, reference, software version, CPU architecture, "
    "storage and configuration.",
    "AWS performance cannot be inferred exactly from Ilifu core counts.",
    "DeepVariant numbers are published benchmarks from a different cloud/platform.",
    "GLnexus is not yet quantitatively modelled.",
    "Current elapsed time assumes sequential cohort-wide stages.",
    "Workflow pipelining is not currently modelled.",
    "Queue delay, retries, startup and staging overhead are not currently modelled.",
    "Working-storage defaults are planning assumptions until measured.",
    "AWS compute pricing is not yet implemented.",
    "HPC monetary cost is not currently modelled.",
    "Accuracy varies by dataset, truth set and pipeline configuration.",
    "Cost estimates are infrastructure planning estimates, not procurement quotations.",
]

UNMODELLED_OVERHEAD = (
    "Workflow overhead — scheduler delay, instance startup, retries, staging delay, "
    "orchestration overhead, interruptions and contention — is not currently modelled."
)


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
    # CRAM indexing shares the alignment stage's concurrency setting — it is
    # a downstream step on the same worker, not an independently scheduled
    # stage (spec 011a §8-§9).
    cram_index = concurrency_result(
        cram_index_stage.name,
        num_samples,
        config.alignment_concurrency,
        bm.CRAM_INDEX_WALL_TIME_HOURS,
        bm.CRAM_INDEX_RUNTIME_EVIDENCE,
        "benchmark",
    )
    deepvariant = _stage_concurrency(
        deepvariant_stage.name,
        num_samples,
        config.deepvariant_concurrency,
        bm.DEEPVARIANT_RUNTIME_HOURS,
        bm.DEEPVARIANT_RUNTIME_EVIDENCE,
        config.deepvariant_runtime_override_hours,
    )

    # V1 design decision (spec 011 §18): treat the per-sample stages as fully
    # sequential across the whole cohort — a defensible worst-case, not a
    # pipelined estimate. Only GLnexus (no approved benchmark) is excluded
    # from this total; CRAM indexing is measured and included (spec 011a §9).
    known_modelled_elapsed_hours = (
        alignment.idealised_elapsed_hours
        + cram_index.idealised_elapsed_hours
        + deepvariant.idealised_elapsed_hours
    )

    working_storage = working_storage_result(
        config.scratch_gib_per_worker,
        config.alignment_concurrency,
        config.deepvariant_concurrency,
    )

    return ComputeResult(
        stages=[alignment_stage, cram_index_stage, deepvariant_stage, glnexus_stage],
        alignment=alignment,
        cram_index=cram_index,
        deepvariant=deepvariant,
        glnexus=glnexus_stage,
        working_storage=working_storage,
        known_modelled_elapsed_hours=known_modelled_elapsed_hours,
        excluded_stages=["GLnexus (cohort joint calling)"],
        unmodelled_overhead=UNMODELLED_OVERHEAD,
        aws=aws_execution_info(),
        hpc=hpc_execution_info(),
        sentieon=sentieon_info(num_samples, usd_zar),
        limitations=list(LIMITATIONS),
    )
