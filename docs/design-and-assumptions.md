# CBIO Genomics Infrastructure Cost Planner
## Design, Assumptions and Decision Record

This is the living source of truth for why the planner behaves as it
does: its purpose and architecture, what is actually implemented today,
what is planned but not built, the evidence behind important numbers, and
open questions. It is not a changelog and does not record implementation
minutiae that belong in source comments, the README or Git history.

See [`README.md`](../README.md) for setup/run instructions and
[`docs/assumptions.md`](assumptions.md) for the original V1 simplifications
list (storage/transfer only). Where that older document's description of
internal mechanics has been superseded by later changes, this document is
authoritative — see the note in [Storage](#storage-implemented) below.

---

## 1. Purpose

The planner is a technical planning tool for **estimating and comparing
genomics infrastructure requirements and costs**. It is deliberately
explainable and deterministic: every figure is produced by plain
arithmetic over editable assumptions, with a full calculation-detail trace
available in the UI — never an opaque or AI-generated cost figure.

It is **not** an AWS billing system, does not call any cloud provider API,
and does not perform privacy, ethics, security or procurement compliance
assessment.

### Planned broader architecture

    Storage
       ↓
    Compute
       ↓
    Transfer
       ↓
    Project Summary

These are logical planning domains, not necessarily sequential execution
stages. The long-term intent is for all modules to operate over one shared
project/dataset model so the planner produces one coherent project
infrastructure estimate.

**Status: Storage is Implemented. The Storage / Compute / Transfer /
Project Summary application navigation and module shell are Implemented
(`app.py`, `views/`) — Compute and Transfer calculations themselves, and a
full cross-module Project Summary rollup, remain Planned.** Everything
under [§10](#10-compute-planned) onward in this document describes
planned design direction, not current behaviour, unless explicitly marked
otherwise.

---

## 2. Status terminology

Used consistently throughout this document:

- **Implemented** — currently available in the application.
- **Planned** — agreed design direction but not yet implemented.
- **Under investigation** — requires further research, benchmarking,
  validation, pricing information, or a design decision.
- **Out of scope** — deliberately not part of the current development
  scope.

Planned or Under investigation functionality is never described as if it
already exists.

## 3. Evidence classifications

Numerical assumptions, benchmarks and commercial inputs are classified by
provenance:

- **Measured** — measured by CBIO/UCT or the project team on actual
  infrastructure, or using an explicitly documented test.
- **Published benchmark** — reported by a software developer, cloud
  provider, peer-reviewed paper, technical report or other external
  source. Source and version/date recorded where possible.
- **Planning assumption** — a reasonable modelling value used for
  infrastructure planning, not presented as measured or authoritative.
- **Local commercial assumption** — a price or commercial term available
  locally to UCT/CBIO that may not represent public or generally
  available pricing.

---

## 4. Current project model (Implemented)

Both project modes reduce to one internal representation before reaching
a single calculation engine (`cbio_cost/calculator.py`,
`cbio_cost/storage.py`, `cbio_cost/transfer.py`): a `ProjectInputs` (name,
mode, retention, transfer contingency, headroom) plus a `list[Dataset]`,
each with `size_gb`, `retrieval_fraction`, `read_passes`, `active_months`
and `archive_class`. WGS 30x is conceptually a predefined *template* over
this model, not a separate calculation engine — see `cbio_cost/models.py`.

A thin cross-module wrapper, `cbio_cost/project.py` (`Project`,
`ProjectMetadata`), holds this project identity plus the Storage module's
computed `CostEstimate`, shared via session state so other modules (today,
Project Summary) can read it without redefining or recomputing it. It
performs no calculation of its own — see [§4 of spec
010](../requests/010-application-architecture.md).

### WGS 30x template

A predefined planning profile for approximately 30x whole-genome
sequencing. The user specifies the number of samples and retention
period; advanced planning assumptions (editable, collapsed by default)
determine estimated dataset sizes and movement behaviour. Sequencing
depth is **not** exposed as an input used to derive file sizes — the
profile's per-sample volumes already represent 30x and are not scaled
again.

Current WGS 30x planning defaults (`config/project-profiles.yaml`):

| Data type | Planning value | Evidence class |
|---|---:|---|
| FASTQ | 100 GB/sample | Planning assumption |
| CRAM | 40 GB/sample | Planning assumption |
| gVCF/QC/indexes | 10 GB/sample | Planning assumption |

These are planning assumptions, not guarantees. The built-in 500-sample
demo profile represents approximately:

- FASTQ: 50,000 GB
- CRAM: 20,000 GB
- gVCF/QC/indexes: 5,000 GB
- total durable data before headroom: 75,000 GB

Other current WGS template defaults (`config/project-profiles.yaml`,
`default_profile`): 20% storage headroom, 1 month active (S3 Standard)
period before archive transition, 20% transfer contingency, FASTQ read
once (`fastq_passes: 1`), 10% of CRAMs retrieved once
(`cram_retrieval_percent: 10`, `cram_retrieval_passes: 1`), gVCF read
twice (`gvcf_passes: 2`), and all three file types archived to Glacier
Flexible Retrieval. These are used to generate the WGS template's three
datasets (FASTQ, CRAM, gVCF) via `cbio_cost.config.build_wgs_datasets`.

### Custom Project

A generic dataset model for projects that do not fit the WGS template
(`app.py` Custom Project mode). A user defines one or more datasets (start
at one, add up to 20, remove any but the first), each independently
configurable:

- dataset name (free text, not constrained to genomics file types);
- total dataset size (GB or TB; **total** size, not per-sample);
- retrieval percentage (0-100%, fraction of the dataset read per pass);
- read passes (how many times the retrieval fraction is read);
- active storage period (months in S3 Standard before archive);
- archive class (one of the four storage classes below).

Retention period is currently **project-level only** (one value shared by
all datasets in a project) — a per-dataset retention override was
considered but deliberately deferred in favour of simplicity (spec
006 §13). Storage headroom is currently a WGS-template-only concept;
Custom Project datasets are costed at their entered size with no headroom
uplift (headroom is silent/zero in Custom Project mode).

---

## 5. Storage modelling (Implemented)

Storage/transfer is the only currently-implemented cost domain. Source:
`cbio_cost/storage.py`, `cbio_cost/transfer.py`, `cbio_cost/operations.py`,
`cbio_cost/calculator.py`, `config/aws-pricing.yaml`.

### Active S3 storage

Each dataset's size (plus WGS-template headroom, where applicable) is
priced against a tiered S3 Standard USD/GB-month schedule for its own
`active_months`, independently per dataset, then summed across datasets.

> **Note on a design change post-006:** the original V1 engine (documented
> in `docs/assumptions.md`) tiered *one combined envelope* across all file
> types for a single project-wide active period. Request 006 (Custom
> Project) made active-storage duration a **per-dataset** input, which is
> only meaningful if each dataset's active storage is tiered and costed
> independently and then summed (spec 006 §17) — this is the current,
> correct description of `cbio_cost/storage.py`. For the WGS 500x30x demo
> this changes the active-storage dollar total slightly versus the
> pre-006 engine (durable volume and egress GB figures are unaffected and
> match the pre-006 numbers exactly).

### Archive storage and lifecycle

S3 Lifecycle transitions normally change an object's storage class while
the object remains under the same bucket/key namespace — data does not
need to move to a separate bucket. After its active period, each
dataset's remaining retention months are priced against its own archive
class's tiered schedule. If a dataset's `active_months` exceeds the
project's total retention, no archive period applies (clamped to zero,
not an error).

**S3-Standard-only datasets** (`archive_class: s3_standard`) are a special
case (spec 006 §14): no lifecycle transition is modelled — the dataset is
priced at the S3 Standard rate for the *entire* retention period, not just
`active_months`, and no archive-cost line or minimum-duration warning is
shown for it.

Supported storage classes (`STORAGE_CLASS_KEYS` in `cbio_cost/models.py`,
priced in `config/aws-pricing.yaml`): S3 Standard, Glacier Instant
Retrieval, Glacier Flexible Retrieval, Glacier Deep Archive. Each carries
a minimum-storage-duration warning threshold, a requires-restore flag, and
human-readable retrieval characteristics shown in the UI's "Calculation
details" expander.

### Retrieval / read-pass model and data-transfer (egress)

For every dataset: `base workflow egress = size_gb × retrieval_fraction ×
read_passes`. Per-dataset base egress values sum to a project total, which
is then scaled by the project's `transfer_contingency` fraction to give
planned egress, priced against a tiered AWS internet-egress USD/GB
schedule (minus a configurable one-time free allowance — not a recurring
monthly allowance, since this tool estimates project-lifetime cost rather
than simulating a month-by-month bill). AWS ingress (data moving *into*
S3) is modelled as free, consistent with current AWS pricing; only egress
(S3 → Ilifu) is charged.

### S3/API/lifecycle request costs

Estimated from total project volume and total planned egress using an
assumed average object size of 5 GB (`AVG_OBJECT_SIZE_GB` in
`cbio_cost/storage.py`), not from actual file counts (this tool does not
track individual files). This is a coarse, project-level planning
approximation — modelled once per project, not per dataset, since it is
already an approximation rather than a real per-object charge.

### Engineering/support

Onboarding, ongoing operations (scaled by `retention_years`) and closeout
hours, all at one hourly rate, computed once per project — **not**
multiplied by the number of datasets (spec 006 §18). Current defaults:
8 onboarding hours, 12 operations hours/year, 4 closeout hours, at an
illustrative R1,000/hour. The UI explicitly labels this rate: *"Planning
assumption only — not an approved UCT/CBIO institutional rate."*

### Sensitivity scenarios

A Low / Expected / High comparison table, computed generically for both
modes from the shared dataset model (spec 006 §19):

- **WGS 30x** — Low/Expected/High are fixed, named overlays from
  `config/project-profiles.yaml` (`scenarios`), applied to the *current*
  (possibly user-edited) sample count/volumes so the table reflects live
  inputs, varying only movement behaviour:

  | Scenario | FASTQ passes | CRAM retrieval % | CRAM passes | gVCF passes | Contingency |
  |---|---:|---:|---:|---:|---:|
  | Low movement | 1 | 5% | 1 | 1 | 10% |
  | Expected | 1 | 10% | 1 | 2 | 20% |
  | High movement | 2 | 25% | 1 | 3 | 40% |

- **Custom Project** — has no FASTQ/CRAM/gVCF concept to scale, so Low/High
  are generic multipliers on the live dataset list's `read_passes` and on
  `transfer_contingency` (0.5x / 1x / 2x), since a per-file-type overlay
  like the WGS one cannot be generalised to arbitrary datasets. These do
  not reproduce the WGS scenario numbers and are not intended to — they
  demonstrate the same qualitative point (movement behaviour materially
  affects total cost) for arbitrary datasets.

### Currency and VAT

USD → ZAR conversion and VAT are applied to AWS-sourced costs
(storage + requests + archive + egress) only. Engineering/staff cost is
shown as a plain ZAR figure — VAT is not applied to internal staff time.
Defaults (`config/aws-pricing.yaml`): 16.05 USD/ZAR (as of 2026-09-14,
explicitly a placeholder), 15% VAT.

### Exports

CSV, JSON and Markdown exports (`cbio_cost/export.py`) all include: the
project mode label (`"WGS 30x"` or `"Custom Project"`), the full dataset
list (name, size, retrieval %, passes, active months, archive class), the
cost-component breakdown, and pricing/assumption provenance (see §6
below). Compute is explicitly listed as "Not included" in every export.

### Decimal arithmetic

All calculations use Python's `Decimal` type end-to-end (never `float`),
to avoid floating-point rounding artifacts in financial figures. Rounding
only happens at display/formatting time; percentages/fractions are stored
internally as `Decimal` fractions in `[0, 1]`.

---

## 6. Pricing provenance (Implemented)

Current values in `config/aws-pricing.yaml`, verified against the
repository at the time of writing this document:

- Provider: **AWS**
- Region: **Africa (Cape Town)**
- Region code: **`af-south-1`**
- Pricing source: **https://aws.amazon.com/s3/pricing/**
- Pricing last verified: **2026-08-31**

These match the values given in spec 009 §7 exactly — no discrepancy
found. However, every individual price in `config/aws-pricing.yaml` (S3
Standard/Glacier tiers, egress tiers, request costs) is explicitly marked
`pricing_last_verified: "UNVERIFIED"` with a `source` note describing it
as an approximate placeholder — **the file-level `pricing_last_verified`
date above describes when the pricing *structure* was last reviewed, not
that every individual rate has been reconciled against a live AWS
account or invoice.** Published AWS pricing (rate schedules) is kept
structurally distinct from configurable planning assumptions (volumes,
movement, engineering hours) throughout the codebase and in every export.

The engineering/support hourly rate is explicitly described in the UI and
exports as *"Planning assumption only — not an approved UCT/CBIO
institutional rate."*

---

## 7. Data volume reference guide (Implemented)

`data_volume_guide.py` provides rough, informational planning ranges for
common genomics data types, shown in a collapsed "Data volume reference
guide" expander visible from both project modes (spec 007, extended by
spec 008). It is documentation only — never used to derive or scale a
calculated value, and it must not be imported by anything under
`cbio_cost/` (the calculation engine).

Currently implemented entries:

| Data / format | Rough planning size |
|---|---:|
| 4x WGS FASTQ | ~12-20 GB/sample |
| 4x WGS CRAM | ~5-8 GB/sample |
| 12x WGS FASTQ | ~35-50 GB/sample |
| 12x WGS CRAM | ~12-20 GB/sample |
| 30x WGS FASTQ | ~80-120 GB/sample |
| 30x WGS BAM | ~80-120 GB/sample |
| 30x WGS CRAM | ~30-50 GB/sample |
| 30x WGS gVCF | ~5-10 GB/sample |
| 30x WGS QC + indexes | ~1-5 GB/sample |
| WES FASTQ | ~8-15 GB/sample |
| WES BAM/CRAM | ~5-10 GB/sample |
| RNA-seq FASTQ | ~5-15 GB/sample |
| RNA-seq BAM | ~5-20 GB/sample |
| Genotyping array | <1 GB/sample |
| Joint VCF/BCF | Project-level (no per-sample estimate given) |

All entries are classified as **Planning assumption** (rough,
human-curated ranges, not measured or published-benchmark values). The
guide explicitly states these are planning estimates only and that
measured project volumes should be preferred whenever available. It is
**not** a sequencing-depth-to-file-size calculator: 4x/12x/30x entries are
independent curated rows, not one value scaled by a depth multiplier —
gVCF size in particular does not necessarily scale linearly with coverage
(depends on variant caller, reference-block representation, sequencing
quality, callable regions, pipeline configuration), so no 4x/12x gVCF
estimate is given. Actual sizes vary with sequencing platform, coverage,
read length, compression, reference, variant caller, assay, pipeline and
representation.

---

## 8. Data governance principles (Implemented)

The calculator estimates infrastructure requirements and cost. It does
**not** determine whether sensitive research data may legally,
institutionally, ethically or contractually be stored in a particular
cloud/object-storage environment. A visible, non-alarming callout ("Sensitive
data and governance", spec 008) is shown below the mode selector in both
project modes, stating this and naming the relevant considerations:
participant consent, ethics approvals, data-access agreements,
institutional policy, storage jurisdiction/location, access controls,
encryption, audit logging, retention/deletion, and data-transfer
requirements.

**A cost estimate does not constitute approval to store project data in
AWS.** The same statement is included in the Markdown export's
pricing/assumptions notes.

The planner does not require or encourage entering participant-level
data, phenotype data, variants, credentials, AWS keys or other sensitive
project information to obtain an infrastructure estimate — only
infrastructure-planning inputs (dataset sizes, retention, movement
assumptions) are collected.

---

## 9. Project Summary (status)

**Status: PARTIALLY AVAILABLE.** A dedicated Project Summary page
(`views/summary.py`) now exists in the navigation. It renders only from
the shared `Project`/`CostEstimate` populated by the Storage module in
this session — project type, sample count, retention, durable data
volume, per-dataset storage lifecycle (archive class), storage-related
cost, engineering cost, and the relevant headroom/contingency/currency
assumptions — and never fabricates a Compute or Transfer figure. Because
Streamlit only reruns the page currently being viewed, these figures
reflect Storage's last-computed values in the session rather than
recalculating live; the page says so explicitly. Before Storage has been
visited in a session, it shows a plain "visit Storage" notice instead of
inventing data.

The detailed Cost Summary panel (dataset totals, cost breakdown,
sensitivity table, plain-English explanation, calculation-detail trace)
remains on the Storage page itself. **A full cross-module rollup that also
incorporates Compute and Transfer results is Planned**, pending those
modules below.

---

## 10. Compute (Planned)

**Nothing in this section is implemented.** Compute is conceptually
separated from durable Storage costing and should eventually model:
processing stages, CPU, RAM, runtime, temporary/working storage,
concurrency, wall-clock completion time, infrastructure cost,
software/licensing cost, and execution architecture.

It should support scenarios such as **Cost-efficient**, **Balanced** and
**Fast** — without assuming a faster scenario necessarily costs
proportionally more or less; such differences should be calculated from
actual infrastructure use once implemented. Parallelism can alter
wall-clock duration, simultaneous scratch requirements, instance
selection, utilisation, Spot/on-demand exposure, storage lifetime and
price/performance.

### 10.1 Open-source 30x WGS reference workflow (Planned)

Current design direction for the default open-source reference workflow:

    FASTQ
      ↓
    BWA-MEM2
      ↓
    sorted CRAM + CRAI
      ↓
    DeepVariant
      ↓
    per-sample gVCF
      ↓
    GLnexus
      ↓
    cohort callset

GATK may be considered later as an alternative but is not currently
intended as the primary default. The workflow is modelled by **stages**
rather than one undifferentiated "compute hours per genome" number:

- **Alignment stage** (per-sample, parallel): FASTQ → BWA-MEM2 →
  sort/compress → CRAM → CRAI. Resource characteristics to model: CPU,
  RAM, runtime, working storage, I/O behaviour.
- **Variant-calling stage** (per-sample, parallel): CRAM → DeepVariant →
  gVCF. May use a different instance/resource profile from alignment.
- **Cohort stage** (cohort-level): gVCFs → GLnexus → joint callset. Not
  modelled as another identical per-sample job — memory, compute, storage
  and runtime should eventually be benchmarked for representative cohort
  sizes.

### 10.2 BWA-MEM2 benchmark — Under investigation

**Status: Under investigation — CBIO/Ilifu benchmark planned.** No
BWA-MEM2 runtime has been measured or invented for this document. A
recent workflow used by Scott provides the reference form of the planned
test:

```text
bwa-mem2 mem -t 20 \
  -R '@RG\tID:AGS0834\tSM:AGS0834\tPL:AGS0834' \
  t2t/chm13v2.0.fa \
  AGS0834_1.fq.gz AGS0834_2.fq.gz \
| samtools sort \
  --reference t2t/chm13v2.0.fa \
  --threads 20 \
  -o AGS0834.cram -

samtools index -@10 AGS0834.cram
```

The benchmark should ideally capture: FASTQ R1/R2 sizes, approximate
sequencing depth, reference, CPU model, allocated CPU count, allocated
RAM, wall-clock time, peak RAM, source filesystem/storage,
temporary/working storage, peak temporary disk usage (if practical),
resulting CRAM size, and indexing time (if measured separately). Where
practical, `/usr/bin/time -v` can capture process resource information.
Purpose: establish a local observed reference point comparable later with
an AWS execution environment.

### 10.3 DeepVariant benchmark — Published benchmark

DeepVariant v1.10 documentation reports a 30x WGS CPU benchmark on a
96-vCPU / 384-GiB reference machine of approximately:

- make_examples: 46m 15s
- call_variants: 15m 58s
- postprocess: 6m 45s
- **total: approximately 1h 8m 58s**

Source: https://github.com/google/deepvariant/blob/r1.10/docs/metrics.md
(version: DeepVariant r1.10). DeepVariant's own documentation notes this
configuration is intended for benchmark consistency, not necessarily the
fastest or cheapest configuration. This runtime is **not** translated
into an AWS cost until an appropriate AWS reference configuration and
pricing model have been selected.

This benchmark also provides useful external support for a roughly 40 GB
30x CRAM planning value, but the project's 40 GB/sample WGS default stays
classified as a **Planning assumption** (not Measured) unless/until
measured locally.

### 10.4 GLnexus cohort resources — Under investigation

No benchmark exists yet. Required: research/benchmark GLnexus for
representative cohort sizes (e.g. ~500 WGS samples).

### 10.5 Intermediate/working compute storage — Under investigation

Durable project storage (modelled in §5 above) is not the only storage
requirement. Compute working storage is temporary/intermediate storage
needed while jobs execute — e.g. compressed FASTQs being processed,
alignment/sorting temporaries, BAM/CRAM intermediates, DeepVariant working
files, workflow work directories, container temporary data, cohort-calling
temporaries. This should eventually be modelled by processing stage and
concurrency:

    simultaneous working storage ≈ scratch required per worker × concurrent workers

Storage cost must account for both provisioned capacity *and* lifetime —
a fast, high-concurrency scenario may need substantially more simultaneous
scratch but hold it for less time, so scratch cost does not scale directly
with maximum capacity. Potential AWS implementations include EBS,
instance-local NVMe, or shared filesystems; the final implementation
should calculate working-storage cost per the selected architecture
rather than one generic scratch price. **Current scratch requirements:
Under investigation — benchmark required.**

### 10.6 Sentieon — Planned, Local commercial assumption

A commercial accelerated alternative for the future Compute module.
Current UCT planning licence rate:

    US$1.50 per genome

Classified as **Local commercial assumption** — a current UCT planning
value that must be confirmed for actual project budgeting, not public
Sentieon list pricing. Example: 500 genomes × US$1.50 = US$750 licence
cost. The software licence must be itemised separately from compute
infrastructure, temporary storage, data transfer and durable storage;
US$1.50/genome does not represent the total cost of running a Sentieon
workflow. Sentieon runtime/performance remains **Under investigation**
until appropriate local or published benchmarks are selected.

### 10.7 ICA / DRAGEN / iGG — Under investigation

Illumina Connected Analytics / DRAGEN is another potential execution
strategy, kept **Under investigation** until current pricing, runtime,
licensing and workflow behaviour are sufficiently validated for
implementation. Conceptual architecture:

    FASTQ
      ↓
    ICA / DRAGEN
      ↓
    per-sample gVCF
      ↓
    optional DRAGEN iterative gVCF genotyper (iGG)
      ↓
    cohort callset

iGG pricing must not be silently combined into individual DRAGEN
processing. Reference: https://help.ica.illumina.com/reference/r-pricing
— no pricing figure is recorded here as verified; Illumina commercial
pricing models may evolve, so this should eventually be
configuration-driven and version/date-stamped rather than a permanent
constant. ICA costing is **not** implemented as part of this document.

### 10.8 Execution architecture — Planned

The planner should not assume Slurm is always the preferred execution
environment. For highly parallel per-sample genomics processing on AWS,
an architecture such as Nextflow + AWS Batch + containerised workers +
object storage + appropriate temporary working storage may be suitable.
Slurm remains valid where an HPC scheduler is appropriate. The eventual
planner should recommend an execution architecture based on workload
characteristics rather than always selecting one scheduler.

### 10.9 Completion-time scenarios — Planned

The Compute model should eventually support both resource/cost estimates
and expected elapsed completion time:

- **Total compute consumption**, e.g. `jobs × runtime × resources`
- **Concurrency** — number of jobs executing simultaneously
- **Estimated wall-clock completion** — approximately
  `number of jobs ÷ concurrency × runtime per job`, with additional
  workflow/stage constraints

The eventual tool may support Cost-efficient / Balanced / Fast scenarios
and/or a user-selected target completion time (e.g. "Target completion:
7 days") to estimate required concurrency. Compute cost is not assumed
identical between scenarios — instance price/performance, scaling
efficiency, storage lifetime, provisioning, Spot availability and other
factors may cause differences.

---

## 11. Transfer (Planned)

**Nothing in this section is implemented** beyond the current
storage-module egress cost described in §5 (which only prices AWS
internet egress volume/cost — it does not model transfer duration,
method, or endpoint choice). Conceptual model:

    Endpoints → Dataset → Network → Transfer method → Duration + cost + practical recommendation

Potential endpoints: institutional/local HPC, Ilifu, AWS S3, Illumina
ICA, other object storage, custom endpoint. Potential transfer methods:
S3 multipart transfer, AWS CLI, rclone, Globus, institutional DTN, ICA
transfer mechanism, other/custom. Transfer method does not automatically
change pricing unless the selected endpoint/service actually has a
relevant charge.

### 11.1 Bandwidth modelling principles — Planned

The planner must not infer sustained network bandwidth merely from two
geographic locations. Physical distance can inform expected latency but
does not reliably determine achievable throughput — routing,
institutional networking, peering, firewall behaviour, congestion, DTNs,
TCP tuning and endpoint performance all matter. The planned Transfer
module should support three bandwidth modes:

- **Measured throughput** — preferred, where an actual source-to-
  destination transfer measurement is available.
- **Known link capacity** — known network capacity with a configurable
  planning efficiency.
- **Unknown bandwidth** — do not invent a value; instead show scenarios
  such as 100 Mbps, 500 Mbps, 1 Gbps, 5 Gbps, 10 Gbps.

The project's `1 TB = 1024 GB` storage-unit convention is preserved
throughout; network Mbps/Gbps follow normal decimal network-rate
definitions (these are deliberately different unit systems).

### 11.2 Latency/RTT principles — Planned

Round-trip latency is an optional secondary characteristic. Bandwidth
remains the primary input for transfer-duration estimation; latency
influences whether available bandwidth can actually be utilised,
particularly over high-bandwidth long-distance TCP paths. If RTT is
supplied, a future planner may calculate the bandwidth-delay product
(`BDP = bandwidth × RTT`) to support recommendations on TCP window
requirements, parallel streams, multipart transfer, Globus, DTNs and
resumable transfers. No arbitrary latency penalty is applied directly to
the transfer-duration formula:

    dataset size + planning throughput → estimated duration
    bandwidth + RTT + transfer method → transfer feasibility/advice

RTT remains optional if unknown.

### 11.3 Transfer staging storage — Planned

Temporary transfer/staging storage is conceptually distinct from both
durable storage and compute working storage:

| Storage context | Primary module |
|---|---|
| Durable project storage | Storage |
| Compute working/intermediate storage | Compute |
| Transfer staging/validation storage | Transfer |

A future architecture must avoid double-counting the same physical
storage resource if it is intentionally reused for multiple purposes.

---

## 12. Assumptions and evidence table

| Item | Current value/status | Evidence class | Notes |
|---|---:|---|---|
| 30x WGS FASTQ | 100 GB/sample | Planning assumption | Current WGS template default (`config/project-profiles.yaml`) |
| 30x WGS CRAM | 40 GB/sample | Planning assumption | Supported by DeepVariant docs' ~40 GB reference; local measurement pending |
| 30x WGS gVCF/QC/indexes | 10 GB/sample | Planning assumption | Generic planning value; does not scale linearly with depth |
| Data volume reference guide (4x/12x/30x/WES/RNA-seq/array) | See §7 | Planning assumption | Informational only; never feeds a calculation |
| BWA-MEM2 runtime | TBD | Measured (pending) | Ilifu benchmark planned, §10.2 |
| BWA-MEM2 scratch | TBD | Measured (pending) | Ilifu benchmark planned, §10.2 |
| DeepVariant CPU runtime | ~1h09/sample on 96-vCPU/384-GiB reference config | Published benchmark | DeepVariant v1.10, §10.3 |
| GLnexus cohort resources | TBD | — | Research/benchmark required, §10.4 |
| Compute working storage | TBD | Measured/planning (pending) | Benchmark required, §10.5 |
| Sentieon licence | US$1.50/genome | Local commercial assumption | Current UCT planning rate, §10.6 |
| Sentieon runtime | TBD | — | Research/benchmark required, §10.6 |
| AWS S3/egress/request pricing | Config-driven (`config/aws-pricing.yaml`) | Published pricing (per-rate: UNVERIFIED) | af-south-1; see §6 |
| USD/ZAR exchange rate | 16.05 (as of 2026-09-14) | Planning assumption | Placeholder; confirm against approved UCT/CBIO source |
| VAT | 15% | Planning assumption | Applied to AWS costs only |
| Engineering hourly rate | R1,000/hour | Planning assumption | Explicitly not an approved institutional rate |
| ICA/DRAGEN pricing | Under investigation | Published/commercial (pending) | Verify before implementation, §10.7 |
| Transfer bandwidth | Not yet implemented | Planning input (future) | Must not be inferred from geography, §11.1 |

---

## 13. Decision record

Dated: 2026-09-15.

| Decision | Rationale |
|---|---|
| **Project structure**: evolve toward Storage → Compute → Transfer → Project Summary | Separates genuinely distinct cost domains while keeping a path to one coherent project estimate |
| **Shared modelling**: WGS templates and Custom Project use one common dataset/project model | Avoids a second, divergent calculation engine (spec 006 §3); WGS is a template, not a special case |
| **WGS depth**: do not expose sequencing depth as a normal input for the fixed WGS 30x profile to derive file sizes | The 30x profile's per-sample volumes already represent 30x; deriving sizes from depth would double-count and add false precision (spec 006 §2) |
| **File-size guidance**: provide rough reference ranges rather than deriving file size from coverage | Genomic file size is not a clean function of coverage alone (caller, pipeline, compression, reference all matter); a guide avoids implying false precision while still helping users pick Custom Project sizes (spec 007/009) |
| **Compute reference workflow**: BWA-MEM2 + DeepVariant + GLnexus as the initial planned open-source 30x WGS reference; GATK kept as a future alternative | Reflects current CBIO/Ilifu practice and available published benchmark evidence (DeepVariant) |
| **Compute scenarios**: model different completion strategies (Cost-efficient/Balanced/Fast), not only a single "cheapest" run | Real infrastructure choices trade cost against wall-clock time; a single number hides that trade-off |
| **Working storage**: intermediate/working storage is part of Compute costing | Easy to forget scratch/temporary storage entirely; it has real cost and must be modelled by stage/concurrency, not ignored |
| **Scheduler architecture**: do not assume Slurm is always the correct cloud execution model | AWS-native architectures (Batch, Nextflow) may suit highly parallel per-sample genomics workloads better than an HPC scheduler |
| **Transfer bandwidth**: do not infer sustained bandwidth from geography | Achievable throughput depends on routing, peering, congestion and endpoint performance, not distance; prefer measured throughput, known link capacity, or explicit scenarios |
| **Latency**: treat RTT as a feasibility/performance characteristic, not an arbitrary duration penalty | Bandwidth is the primary duration driver; latency affects whether that bandwidth is actually achievable, which is a different (BDP/TCP-tuning) concern |
| **Evidence**: distinguish Measured, Published benchmark, Planning assumption and Local commercial assumption throughout | Prevents a rough planning number from being mistaken for a measured or authoritative one when budgeting real projects |

---

## 14. Open research backlog

### Compute

- Run BWA-MEM2 FASTQ → CRAM benchmark on Ilifu; measure wall time, CPU and
  RAM; measure/estimate peak working storage; record resulting CRAM size.
- Select representative AWS Cape Town instance types; verify current
  af-south-1 compute pricing.
- Determine suitable temporary storage architecture and pricing.
- Compare Ilifu measurement with AWS execution.
- Validate DeepVariant AWS resource configuration.
- Research/benchmark GLnexus for approximately 500 WGS samples.
- Investigate Spot versus On-Demand economics.
- Investigate Sentieon runtime/performance using appropriate evidence;
  validate the UCT Sentieon commercial assumption before real budgeting.
- Research ICA/DRAGEN runtime and current iCredit/commercial model;
  research iGG separately from per-sample DRAGEN processing.

### Transfer

- Define transfer endpoint model and transfer-method recommendations.
- Establish practical throughput measurement guidance.
- Determine how cloud egress pricing should be applied by endpoint.
- Determine whether transfer staging storage should be explicitly costed.
- Consider RTT/BDP advisory logic.
- Test representative institutional/Ilifu → AWS transfer paths when
  possible.

### Storage

- Continue validating real WGS file-size assumptions against measured
  CBIO projects.
- Consider whether workflow-specific gVCF assumptions should eventually
  replace the generic gVCF planning value.
- Continue validating lifecycle assumptions against real project access
  patterns.

Open research items are not to be turned into application assumptions
until they have been evaluated.

---

## 15. Known limitations

- Cost estimates are planning estimates, not quotations.
- Published cloud prices change and may no longer match
  `config/aws-pricing.yaml` at the time of use.
- Local commercial pricing (e.g. Sentieon) may not apply to every project.
- Genomics data volumes vary substantially by platform, pipeline and
  assay; the reference guide gives rough ranges, not predictions.
- Runtime depends strongly on hardware, I/O, software version and
  workflow configuration.
- Network throughput cannot be predicted reliably from geography alone.
- Compute, Transfer and a cross-module Project Summary are not yet
  implemented.
- Sensitive-data governance remains project/institution specific; the
  planner does not perform that assessment.
- The planner does not constitute infrastructure, security, ethics,
  procurement or compliance approval.

---

## 16. Source references

- AWS S3 pricing: https://aws.amazon.com/s3/pricing/
- AWS S3 storage lifecycle guidance:
  https://docs.aws.amazon.com/whitepapers/latest/genomics-data-transfer-analytics-and-machine-learning/appendix-f-optimizing-storage-cost-and-data-lifecycle-management.html
- AWS archived-object guidance:
  https://docs.aws.amazon.com/AmazonS3/latest/userguide/archived-objects.html
- DeepVariant metrics: https://github.com/google/deepvariant/blob/r1.10/docs/metrics.md
- DeepVariant details: https://github.com/google/deepvariant/blob/r1.10/docs/deepvariant-details.md
- BWA-MEM2: https://github.com/bwa-mem2/bwa-mem2
- GLnexus: https://github.com/dnanexus-rnd/GLnexus
- Illumina ICA pricing: https://help.ica.illumina.com/reference/r-pricing

No publication dates, prices or benchmark results are recorded here
beyond what has been verified above. For volatile information such as
cloud/commercial pricing, a verification date is recorded where known
(see §6).

---

## Maintaining this document

After implementing a material application change, review this document.
Update it when the change introduces or modifies: architecture, modelling
assumptions, benchmark values, pricing inputs or provenance, design
decisions, evidence status, known limitations, or open research
questions.

Do **not** update this document merely because code changed. Do not use
it as a commit log or task history. Do not duplicate implementation
details that belong in the README, source code, configuration, tests, or
Git history.

When new evidence replaces a planning assumption:

1. update the value if appropriate;
2. update its evidence classification;
3. record its source/version/date;
4. preserve enough decision context to explain why the model changed.

When a Planned item becomes Implemented, update its status. When an open
research question is resolved, remove it from the active backlog and, if
materially important, record the resulting decision or assumption in
§13.
