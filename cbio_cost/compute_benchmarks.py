"""Compute benchmark evidence for the WGS reference workflow (spec 011 §4-§9, §27).

Raw measured/published figures are recorded as named ``Decimal`` constants;
every derived value used elsewhere in the Compute model is computed here from
those raw figures via the same formula the spec documents, rather than being
re-hardcoded as a second, untraceable number. Each figure is paired with an
:class:`~cbio_cost.evidence.Evidence` record so its classification, source and
exact value travel with it into the UI and exports.

Do not add a "universal BWA-MEM2 performance" figure here — every benchmark in
this module describes one specific measured/published execution and must stay
labelled as such (spec 011 §4).
"""

from __future__ import annotations

from decimal import Decimal

from cbio_cost.evidence import Evidence

SECONDS_PER_HOUR = Decimal(3600)
KIB_PER_GIB = Decimal(1024 * 1024)
KIB_PER_MIB = Decimal(1024)

# ---------------------------------------------------------------------------
# BWA-MEM2 + sort — NA12878, measured CBIO/Ilifu benchmark (spec 011 §4)
# ---------------------------------------------------------------------------

BWA_SAMPLE = "NA12878"
BWA_REFERENCE = "Homo_sapiens_assembly38.fasta (GATK hg38)"
BWA_CPU_MODEL = "Intel Xeon Gold 6142 @ 2.60 GHz, 2 sockets x 16 physical cores = 32 physical cores"
BWA_COMMAND = (
    "bwa-mem2 mem -t 32 ... | samtools sort --reference Homo_sapiens_assembly38.fasta "
    "--threads 32 -o NA12878.cram"
)
BWA_BENCHMARK_DATE = "2026-09-17"

BWA_FASTQ_R1_GB = Decimal(48)
BWA_FASTQ_R2_GB = Decimal(49)
BWA_FASTQ_TOTAL_GB = Decimal(97)
BWA_CRAM_OUTPUT_GB = Decimal(57)
BWA_CRAI_OUTPUT_MB = Decimal("2.5")

BWA_ALLOCATED_CPU = 32

# GNU time statistics, measured (spec 011 §4)
BWA_ELAPSED_SECONDS = Decimal(4 * 3600 + 56 * 60 + 42)  # 4:56:42
BWA_USER_CPU_SECONDS = Decimal("239688.20")
BWA_SYSTEM_CPU_SECONDS = Decimal("5558.03")
BWA_MAX_RSS_KB = Decimal("122379120")

# Derived values (spec 011 §4 "Derived values") — computed from the raw
# measurements above, not re-hardcoded.
BWA_WALL_TIME_HOURS = BWA_ELAPSED_SECONDS / SECONDS_PER_HOUR
BWA_CPU_CORE_HOURS = (BWA_USER_CPU_SECONDS + BWA_SYSTEM_CPU_SECONDS) / SECONDS_PER_HOUR
BWA_EFFECTIVE_AVG_CORES = BWA_CPU_CORE_HOURS / BWA_WALL_TIME_HOURS
BWA_PEAK_RAM_GIB = BWA_MAX_RSS_KB / KIB_PER_GIB

BWA_RUNTIME_EVIDENCE = Evidence(
    classification="measured",
    source=f"{BWA_SAMPLE} BWA-MEM2 + samtools sort benchmark",
    date=BWA_BENCHMARK_DATE,
    value=f"{BWA_WALL_TIME_HOURS} h/sample",
    notes=(
        f"{BWA_CPU_MODEL}. hg38 ({BWA_REFERENCE}). Elapsed wall time 4:56:42 "
        f"({BWA_ELAPSED_SECONDS}s) / 3600 = {BWA_WALL_TIME_HOURS} h. One measured "
        "single-sample execution — not universal BWA-MEM2 performance."
    ),
)

BWA_CPU_EVIDENCE = Evidence(
    classification="measured",
    source=f"{BWA_SAMPLE} BWA-MEM2 benchmark execution configuration (-t 32)",
    date=BWA_BENCHMARK_DATE,
    value=f"{BWA_ALLOCATED_CPU} CPU",
    notes=f"Effective average CPU utilisation measured at {BWA_EFFECTIVE_AVG_CORES:.2f} cores (1377%).",
)

BWA_CPU_UTILISATION_EVIDENCE = Evidence(
    classification="measured",
    source=f"{BWA_SAMPLE} BWA-MEM2 benchmark GNU time statistics",
    date=BWA_BENCHMARK_DATE,
    value=f"{BWA_CPU_CORE_HOURS:.1f} core-hours/sample",
    notes=(
        f"(user {BWA_USER_CPU_SECONDS}s + system {BWA_SYSTEM_CPU_SECONDS}s) / 3600 = "
        f"{BWA_CPU_CORE_HOURS:.2f} core-hours. Not {BWA_ALLOCATED_CPU} x wall time — allocated "
        "CPU and measured CPU consumption are separate figures."
    ),
)

BWA_MEASURED_RAM_EVIDENCE = Evidence(
    classification="measured",
    source=f"{BWA_SAMPLE} BWA-MEM2 benchmark, max resident set size",
    date=BWA_BENCHMARK_DATE,
    value=f"{BWA_PEAK_RAM_GIB:.1f} GiB",
    notes=f"{BWA_MAX_RSS_KB:.0f} KB / (1024x1024) = {BWA_PEAK_RAM_GIB:.4f} GiB peak RSS.",
)

ALIGNMENT_PLANNING_RAM_GIB = Decimal(160)

ALIGNMENT_PLANNING_RAM_EVIDENCE = Evidence(
    classification="planning_assumption",
    source="Operational headroom over measured NA12878 peak RSS",
    date=BWA_BENCHMARK_DATE,
    value=f"{ALIGNMENT_PLANNING_RAM_GIB} GiB",
    notes=(
        f"Planning allocation, not a measured requirement. Measured peak: "
        f"{BWA_PEAK_RAM_GIB:.1f} GiB in the CBIO/Ilifu {BWA_SAMPLE} benchmark."
    ),
)

# ---------------------------------------------------------------------------
# CRAM index — measured CBIO/Ilifu benchmark (spec 011 §5)
# ---------------------------------------------------------------------------

CRAM_INDEX_COMMAND = "samtools index -@32 NA12878.cram"
CRAM_INDEX_ELAPSED_SECONDS = Decimal(15 * 60) + Decimal("8.66")  # 15:08.66
CRAM_INDEX_USER_SECONDS = Decimal("170.09")
CRAM_INDEX_SYSTEM_SECONDS = Decimal("60.18")
CRAM_INDEX_MAX_RSS_KB = Decimal("28928")

CRAM_INDEX_WALL_TIME_HOURS = CRAM_INDEX_ELAPSED_SECONDS / SECONDS_PER_HOUR
CRAM_INDEX_PEAK_RAM_MIB = CRAM_INDEX_MAX_RSS_KB / KIB_PER_MIB

CRAM_INDEX_RESOURCE_NOTE = "Lightweight / shared worker"

CRAM_INDEX_RUNTIME_EVIDENCE = Evidence(
    classification="measured",
    source=f"{BWA_SAMPLE} samtools index benchmark",
    date=BWA_BENCHMARK_DATE,
    value=f"{CRAM_INDEX_WALL_TIME_HOURS * 60:.1f} min/sample",
    notes=(
        f"Elapsed 15:08.66 ({CRAM_INDEX_ELAPSED_SECONDS}s) / 3600 = "
        f"{CRAM_INDEX_WALL_TIME_HOURS:.4f} h. Measured and lightweight despite "
        "requesting 32 threads — does not require a dedicated 32-core worker."
    ),
)

# ---------------------------------------------------------------------------
# DeepVariant v1.10 — published benchmark (spec 011 §8)
# ---------------------------------------------------------------------------

DEEPVARIANT_VERSION = "DeepVariant v1.10"
DEEPVARIANT_SOURCE_URL = "https://github.com/google/deepvariant/blob/r1.10/docs/metrics.md"
DEEPVARIANT_ENVIRONMENT = "GCP n2-standard-96 (96 vCPU / 384 GiB RAM, CPU-only), WGS sample HG003, mean of 5 runs"

DEEPVARIANT_MAKE_EXAMPLES_SECONDS = Decimal(46 * 60 + 15)
DEEPVARIANT_CALL_VARIANTS_SECONDS = Decimal(15 * 60 + 58)
DEEPVARIANT_POSTPROCESS_SECONDS = Decimal(6 * 60 + 45)
DEEPVARIANT_TOTAL_SECONDS = (
    DEEPVARIANT_MAKE_EXAMPLES_SECONDS + DEEPVARIANT_CALL_VARIANTS_SECONDS + DEEPVARIANT_POSTPROCESS_SECONDS
)
DEEPVARIANT_RUNTIME_HOURS = DEEPVARIANT_TOTAL_SECONDS / SECONDS_PER_HOUR

DEEPVARIANT_RUNTIME_EVIDENCE = Evidence(
    classification="published_benchmark",
    source=f"{DEEPVARIANT_VERSION} runtime metrics ({DEEPVARIANT_SOURCE_URL})",
    date="r1.10 documentation",
    value=f"{DEEPVARIANT_RUNTIME_HOURS:.4f} h/sample",
    notes=(
        f"{DEEPVARIANT_ENVIRONMENT}. make_examples 46m15s + call_variants 15m58s + "
        f"postprocess_variants 6m45s = {DEEPVARIANT_TOTAL_SECONDS:.0f}s. DeepVariant's own "
        "documentation states this configuration is chosen for reproducibility/consistency, "
        "not necessarily the fastest or cheapest — this runtime is not a claim that an AWS "
        "instance will reproduce it."
    ),
)

# ---------------------------------------------------------------------------
# GLnexus — no approved planning benchmark (spec 011 §9)
# ---------------------------------------------------------------------------

GLNEXUS_STATUS = "Under investigation"
GLNEXUS_EVIDENCE_NOTE = "No approved planning benchmark"

# ---------------------------------------------------------------------------
# Working storage — planning assumption (spec 011 §13)
# ---------------------------------------------------------------------------

DEFAULT_SCRATCH_GIB_PER_WORKER = Decimal(250)

SCRATCH_EVIDENCE = Evidence(
    classification="planning_assumption",
    source="Conservative initial planning value; no CBIO measured scratch benchmark yet",
    date=BWA_BENCHMARK_DATE,
    value=f"{DEFAULT_SCRATCH_GIB_PER_WORKER} GiB/worker",
    notes=(
        "Editable planning assumption, not a measured BWA-MEM2 requirement. The same "
        "per-worker figure is currently used for both alignment and DeepVariant workers."
    ),
)

# ---------------------------------------------------------------------------
# Sentieon — local commercial assumption (spec 011 §27)
# ---------------------------------------------------------------------------

SENTIEON_USD_PER_GENOME = Decimal("1.50")

SENTIEON_EVIDENCE = Evidence(
    classification="local_commercial_assumption",
    source="UCT Sentieon licence planning rate",
    date="Unconfirmed — see docs/design-and-assumptions.md",
    value=f"US${SENTIEON_USD_PER_GENOME}/genome",
    notes=(
        "Software licensing only; does not include compute, storage, transfer or "
        "engineering. Sentieon runtime is not implemented without a benchmark."
    ),
)

# ---------------------------------------------------------------------------
# AWS execution architecture (spec 011 §20-§26)
# ---------------------------------------------------------------------------

AWS_REGION_CODE = "af-south-1"
AWS_REGION_NAME = "Africa (Cape Town)"
AWS_ARCHITECTURE_STEPS = [
    "Amazon S3",
    "AWS Batch",
    "EC2 worker instances",
    "Working storage",
    "Workflow outputs",
    "Amazon S3",
]
AWS_PRICING_STATUS = "Pending verified regional pricing"

# ---------------------------------------------------------------------------
# Execution environment — Ilifu/HPC and future alternatives (spec 011a §5, §18)
# ---------------------------------------------------------------------------

HPC_STATUS = "Available planning reference"
HPC_MONETARY_COST_STATUS = "Not currently modelled"
HPC_WORKING_STORAGE_STATUS = "Planning model available"
HPC_SCHEDULING_STATUS = "Not currently modelled"

DRAGEN_ICA_STATUS = "Planned"
