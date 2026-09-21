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

**Status: Storage, Compute (WGS 30x scope) and Transfer are Implemented.**
The Storage / Compute / Transfer / Project Summary application navigation
and module shell are Implemented (`app.py`, `views/`); Project Summary
shows what each module has actually computed (§9) rather than a fully
combined cross-module total. See §10 and §11 for exactly what is/isn't
implemented within Compute and Transfer respectively — several items
within each (e.g. AWS compute/transfer pricing verification, GLnexus,
Sentieon/ICA costing, transfer staging storage) remain Planned or Under
investigation.

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
- **Planning scenario** (spec 012) — one of several illustrative
  throughput/duration figures shown when no measured or known-capacity
  value exists; never presented as expected or measured.
- **Published/provider pricing** (spec 012) — a cloud/network provider's
  published tariff (e.g. AWS egress), distinct from Published benchmark
  (software/hardware performance) above.

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

### Application startup state (spec 011a)

The application no longer opens with the 500-sample demo profile loaded as
though it were the user's project. On first load it seeds a conservative
**minimum-valid WGS 30x project** — 1 sample, 1-year retention, empty
project name — using the same config-driven planning defaults (volumes,
movement, engineering, currency) as the demo profile
(`views/storage._minimum_valid_state()`). The full 500×30×/5-year example
remains available via the explicit "Load 500 x 30x WGS / 5-year demo
profile" button (`views/storage._default_state()` /
`_load_demo_profile()`), used for demonstrations, screenshots and
reproducing the documented regression figures below — it is never the
application's silent starting state.

A shared project bootstrap (`views/storage.ensure_project_state()`) runs
once, before `st.navigation` dispatches to whichever page the user opens
first (`app.py`). This guarantees `st.session_state["project"]` always
holds a coherent project — Storage, Compute, Transfer and Project Summary
share one project state regardless of navigation entry point. Previously,
opening a non-Storage page directly in a fresh session could show a
contradictory "no project configured" message, because `st.navigation` only
executes the render function of the page actually displayed and Storage's
own session-state seeding never ran.

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
remains on the Storage page itself. Since spec 011, Project Summary also
shows a Compute section (workflow, sequential-stage planning estimate,
configured/effective worker concurrency, working storage, evidence status)
once the Compute page has been visited in the session — Compute cost itself
is shown as **"not yet calculated"**, never `$0`, because AWS compute
pricing remains unverified (§10.8). Since spec 012, Project Summary
similarly shows a Transfer section (dataset, source → destination, volume,
throughput basis, estimated duration or planning scenarios, method,
provider-cost status) once the Transfer page has been visited — its figures
are never folded into Storage's `grand_total_zar` or any other combined
total (§11), matching how Compute cost is handled. **A single combined
figure across all three modules remains intentionally not built** until
cost ownership across Storage/Compute/Transfer is made fully explicit.

---

## 10. Compute (Partially implemented)

**Spec 011 implements a first functional Compute module**, scoped to the WGS
30x project profile and the open-source reference workflow below: workflow
stages, CPU/RAM (as measured + planning-allocation pairs), runtime,
concurrency, idealised elapsed time, temporary/working storage, an initial
AWS execution-architecture recommendation, and Evidence-classified
provenance on every significant figure (`cbio_cost/evidence.py`,
`cbio_cost/compute_models.py`, `cbio_cost/compute.py`,
`cbio_cost/compute_benchmarks.py`). AWS compute pricing, GLnexus, Sentieon
runtime, ICA/DRAGEN, Custom Project compute support, and Cost-efficient /
Balanced / Fast scenarios remain **Planned** or **Under investigation** — see
each subsection below.

**Spec 011a refines this module** before Transfer (012) is started: the
Compute page now separates **workflow** (what processing occurs, §10.1)
from **execution environment** (where/how it runs — Ilifu/HPC and AWS,
§10.8) as distinct concepts; CRAM indexing is corrected from an
internally-contradictory "excluded as workflow overhead" treatment to an
explicitly included, measured stage (§10.2); working storage became
stage-specific (§10.5); the runtime total is relabelled a **sequential-stage
planning estimate** with an explicit pipelining caveat (§10.9); Sentieon and
DRAGEN/ICA are presented as alternative execution options, not part of the
active workflow; and internal specification references (`spec 011 §n`) were
removed from user-facing Compute page text — this document may continue to
reference them.

Four distinct planning questions run through Storage, Compute and (later)
Transfer: what data must be stored (Storage), what processing must be
performed (**workflow**), where/how that processing runs (**execution
environment**), and how data moves between locations (Transfer). These
remain distinct even where they interact, so the Compute page renders them
as separate sections rather than one merged view.

It should eventually support scenarios such as **Cost-efficient**,
**Balanced** and **Fast** — without assuming a faster scenario necessarily
costs proportionally more or less; such differences should be calculated
from actual infrastructure use once implemented. Parallelism can alter
wall-clock duration, simultaneous scratch requirements, instance
selection, utilisation, Spot/on-demand exposure, storage lifetime and
price/performance.

### 10.1 Open-source 30x WGS reference workflow (Implemented)

**Workflow** describes what processing occurs, independently of where it
runs — kept as a distinct concept from **execution environment** (§10.8),
which describes where/how the workflow executes (spec 011a §4). The
workflow diagram on the Compute page annotates each processing stage as
"modelled" or "benchmark pending" rather than leaving unquantified stages
(GLnexus) unlabelled.

Implemented as the Compute page's workflow (`views/compute.py`), scoped to
the WGS 30x project profile only — Custom Project compute modelling remains
**Planned**. Reference workflow:

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

### 10.2 BWA-MEM2 + CRAM index benchmark — Measured (Implemented)

**Status: Implemented.** Measured on CBIO/Ilifu, 2026-09-17
(`cbio_cost/compute_benchmarks.py`). This is **one measured single-sample
execution**, not universal BWA-MEM2 performance — the planner always labels
it as such (spec 011 §4).

Sample: NA12878. Input: R1 FASTQ ≈48 GB, R2 FASTQ ≈49 GB, total compressed
FASTQ ≈97 GB. Reference: `Homo_sapiens_assembly38.fasta` (GATK hg38). CPU:
Intel Xeon Gold 6142 @ 2.60 GHz, 2 sockets × 16 physical cores = 32 physical
cores, 1 hardware thread/core.

```bash
bwa-mem2 mem -t 32 ... \
| samtools sort \
  --reference Homo_sapiens_assembly38.fasta \
  --threads 32 \
  -o NA12878.cram
```

Measured GNU time statistics: elapsed wall time 4:56:42; user CPU time
239688.20s; system CPU time 5558.03s; average CPU utilisation 1377%;
maximum resident set size 122,379,120 KB; swaps 0; exit status 0.

Derived values (computed from the figures above, not re-hardcoded — see
`BWA_WALL_TIME_HOURS`/`BWA_CPU_CORE_HOURS`/`BWA_PEAK_RAM_GIB` in
`cbio_cost/compute_benchmarks.py`): wall time = 17802s / 3600 = **4.945
h/sample**; CPU consumption = (239688.20 + 5558.03)s / 3600 ≈ **68.1
core-hours/sample** (effective average ≈13.77 cores — *not*
`32 × wall time`, see spec 011 §11); peak RAM = 122,379,120 KB / (1024×1024)
≈ **116.7 GiB**.

Output: CRAM ≈57 GB, CRAI ≈2.5 MB.

**Alignment planning profile** (Compute page "Workflow stages"): requested
CPU = 32 (**Measured** — the benchmark's own execution configuration);
requested RAM = **160 GiB**, classified **Planning assumption** — derived
from the measured peak of 116.7 GiB plus operational headroom, and always
shown alongside the measured figure, never merged into it (spec 011 §6).

**CRAM indexing** (`samtools index -@32 NA12878.cram`, measured): wall time
15:08.66; user 170.09s; system 60.18s; average CPU utilisation 25%; max RSS
28,928 KB. Treated as a lightweight downstream operation — not modelled as
requiring a dedicated 32-core worker. It shares the alignment stage's
concurrency setting (a downstream step on the same worker, not an
independently scheduled stage) and is **explicitly included** in the
Compute page's runtime total (spec 011a §8-§9) — an earlier revision
excluded it under an internally-contradictory "workflow overhead" label,
even though the underlying figure is measured, not unmodelled overhead.
Workflow overhead now means only queue delay, instance startup, retries,
staging delay, orchestration overhead, interruptions and contention — none
of which are currently modelled — and is stated separately from GLnexus,
the total's one genuinely excluded stage.

### 10.3 DeepVariant benchmark — Published benchmark (Implemented)

DeepVariant v1.10 documentation reports a 30x WGS CPU benchmark on a
96-vCPU / 384-GiB reference machine (GCP `n2-standard-96`, CPU-only, WGS
sample HG003, mean of 5 runs) of approximately:

- make_examples: 46m 15s
- call_variants: 15m 58s
- postprocess: 6m 45s
- **total: approximately 1h 8m 58s** (4138s / 3600 ≈1.1494 h/sample)

Source: https://github.com/google/deepvariant/blob/r1.10/docs/metrics.md
(version: DeepVariant r1.10). DeepVariant's own documentation notes this
configuration is intended for benchmark consistency, not necessarily the
fastest or cheapest configuration. This runtime is used as a **planning
input** on the Compute page but is **not** translated into an AWS cost
until an appropriate AWS reference configuration and pricing model have
been selected — the planner does not claim an AWS instance will reproduce
this GCP runtime (spec 011 §8).

This benchmark also provides useful external support for a roughly 40 GB
30x CRAM planning value, but the project's 40 GB/sample WGS default stays
classified as a **Planning assumption** (not Measured) unless/until
measured locally.

### 10.4 GLnexus cohort resources — Under investigation

No benchmark exists yet. The Compute page shows GLnexus as the cohort
joint-calling stage but explicitly excludes it from runtime/cost totals
("No approved planning benchmark") rather than inventing a figure (spec 011
§9). Required: research/benchmark GLnexus for representative cohort sizes
(e.g. ~500 WGS samples).

### 10.5 Working compute storage — Implemented (initial planning-assumption model)

Durable project storage (modelled in §5 above) is not the only storage
requirement. Compute working storage is temporary/intermediate storage
needed while jobs execute — e.g. compressed FASTQs being processed,
alignment/sorting temporaries, BAM/CRAM intermediates, DeepVariant working
files, workflow work directories, container temporary data, cohort-calling
temporaries. Implemented for V1 as a configurable planning assumption
(`cbio_cost.compute.working_storage_result`), **stage-specific since spec
011a §12**:

    alignment peak scratch    = scratch per worker x alignment concurrency
    DeepVariant peak scratch  = scratch per worker x DeepVariant concurrency
    peak workflow scratch     = max(alignment peak, DeepVariant peak)

Default scratch/worker = 250 GiB, classified **Planning assumption** — not
a measured BWA-MEM2 requirement, editable on the Compute page. The same
per-worker figure is currently used for both stages, but each stage's peak
is driven by its own concurrency setting; the two stage peaks are combined
with `max(...)`, not summed, reflecting the V1 sequential-stage execution
model (§10.9) — the two stages are not modelled as running concurrently, so
their scratch requirements do not stack. Storage cost must eventually
account for both provisioned capacity *and*
lifetime — a fast, high-concurrency scenario may need substantially more
simultaneous scratch but hold it for less time, so scratch cost does not
scale directly with maximum capacity. Potential AWS implementations include
EBS gp3, instance-local NVMe, or shared filesystems; the final
implementation should calculate working-storage cost per the selected
architecture rather than one generic scratch price. **No CBIO measured
scratch benchmark yet** — the 250 GiB default remains Under investigation
for refinement.

### 10.6 Sentieon — Planned, Local commercial assumption

A commercial accelerated alternative for the future Compute module. Since
spec 011a, presented under the Compute page's **"Alternative execution
options"** section (alongside ICA/DRAGEN, §10.7) rather than inside the
active open-source workflow, to avoid implying it is part of the selected
pipeline — the underlying licence-cost calculation is unchanged and remains
excluded from totals. Current UCT planning licence rate:

    US$1.50 per genome

Classified as **Local commercial assumption** — a current UCT planning
value that must be confirmed for actual project budgeting, not public
Sentieon list pricing. Example: 500 genomes × US$1.50 = US$750 licence cost
(R12,037.50 at the planner's illustrative R16.05/USD rate). The software
licence must be itemised separately from compute infrastructure, temporary
storage, data transfer and engineering; US$1.50/genome does not represent
the total cost of running a Sentieon workflow. Sentieon remains **Planned /
not included in current workflow** — runtime/performance remains **Under
investigation** until appropriate local or published benchmarks are
selected.

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

### 10.8 Execution environment — Ilifu/HPC and AWS (Implemented), pricing Planned

**Execution environment** describes where/how the workflow (§10.1) runs —
kept distinct from the workflow itself (spec 011a §4-§5). The Compute page
represents two current options and two planned alternatives:

- **Ilifu / institutional HPC** — status **"Available planning
  reference"**. This is not merely the source of the BWA-MEM2 benchmark; it
  is itself a first-class execution environment (spec 011a §18). Runtime
  evidence is partially available (BWA-MEM2: Measured — CBIO/Ilifu;
  DeepVariant: Published benchmark only; GLnexus: Under investigation).
  Working storage has a planning model available (§10.5). Monetary cost and
  scheduling (queue times, fair-share performance, internal institutional
  charging) are **not currently modelled** — the Compute page states this
  explicitly rather than implying HPC execution is free.
- **AWS** — status **"Architecture model implemented; pricing pending"**,
  detailed below.
- **Sentieon on HPC** — **Planned** (§10.6).
- **DRAGEN / Illumina ICA** — **Planned** (§10.7).

A full execution-option comparison engine (cost/evidence/completion-time
across all four) is intentionally **not** built yet (spec 011a §6) — only
the underlying architecture and terminology need to distinguish these
options correctly for V1.

The planner does not assume Slurm is always the preferred execution
environment. For V1 (spec 011 §20), the Compute page documents an initial
AWS architecture recommendation for the embarrassingly-parallel per-sample
stages:

    Amazon S3 -> AWS Batch -> EC2 worker instances -> working storage
      -> workflow outputs -> Amazon S3

Region: **Africa (Cape Town)**, `af-south-1` — kept near the project's
already-modelled AWS storage; cross-region transfer/governance implications
are not modelled. AWS Batch itself has no additional service charge; EC2,
working storage and data transfer are priced separately (`cbio_cost.compute
.aws_execution_info`). Purchase model baseline for V1: **On-Demand**; Spot
is a future/optional optimisation, no fixed discount is assumed (spec 011
§25). Instance selection is represented only as a planning-level
architecture recommendation, not a per-stage instance-type mapping — CPU/RAM
requirements are kept independent of any specific instance choice
(`EC2InstancePricing` exists in `cbio_cost/compute_models.py` as a reserved,
unpopulated extension point). **AWS compute price: Pending verified regional
pricing** — no `af-south-1` EC2 rate is invented; the Compute page shows this
status explicitly rather than a `$0` or estimated figure. Workflow
orchestration may later use Nextflow. Slurm remains valid where an HPC
scheduler is appropriate; the planner does not always select one scheduler.

### 10.9 Completion-time scenarios — Partially implemented

Implemented for V1 (`cbio_cost.compute.concurrency_result`, spec 011 §14):

- **Worker-hours** — `samples × runtime per sample`
- **Concurrency** — user-configurable, separately for alignment and
  DeepVariant (CRAM indexing shares alignment's concurrency)
- **Idealised elapsed time** — `waves × runtime per sample`, where
  `waves = ceil(samples / concurrency)`

The Compute page's **"Sequential-stage planning estimate"** (renamed from
"known modelled elapsed time" in spec 011a §10, to avoid it reading as an
unconditional completion prediction) sums the alignment, CRAM index and
DeepVariant idealised elapsed times, treating these per-sample stages as
fully sequential across the whole cohort — a defensible worst-case, not a
pipelined estimate. It excludes only GLnexus (no approved benchmark) and
workflow overhead (queue delay, instance startup, retries, staging,
interruptions, contention — none currently modelled), both stated
separately and clearly labelled (spec 011 §18; spec 011a §9-§11; decision
record §13). A real workflow may pipeline samples (e.g. sample 2's
alignment proceeding while sample 1 moves to DeepVariant); pipelining is
**not currently modelled**, and the Compute page states this explicitly —
pipelining would only ever reduce, not increase, elapsed time relative to
this estimate.

**Still Planned**: Cost-efficient / Balanced / Fast scenario presets, and a
user-selected target completion time used to derive required concurrency.
Compute cost is not assumed identical between such scenarios — instance
price/performance, scaling efficiency, storage lifetime, provisioning, Spot
availability and other factors may cause differences.

### 10.10 Workflow accuracy evidence — Planned (principles only, spec 011a §20-§23)

The Compute page shows a small **"Workflow accuracy evidence"** information
section — principles only, not a scoring or ranking system. Variant-calling
accuracy depends on the truth set, sample, sequencing technology, coverage,
reference, confident regions, software version, pipeline configuration and
evaluation methodology, so a single number (e.g. "DeepVariant 99.9%") is
misleading without stating all of these. BWA-MEM2 is an aligner, not a
variant caller, and is never presented with an independent accuracy score —
accuracy evidence always attaches to a complete or appropriately defined
workflow (e.g. "BWA-MEM2 → DeepVariant", "DRAGEN pipeline"). Useful evidence
categories: **Genome in a Bottle (GIAB) / hap.py** (preferred basis for
truth-set evaluation), **DeepVariant's own published precision/recall/F1
metrics**, **precisionFDA challenges** (independent benchmark context), and
vendor benchmarks (must be labelled as vendor-published, not independent
evidence). The Compute page does not assign a winner, rank workflows, or mix
incompatible F1 scores into one comparison table. A controlled accuracy
comparison across workflows may be added later once an appropriate common
benchmark is identified.

---

## 11. Transfer (Implemented)

**Spec 012 implements the first functional Transfer module** —
endpoint-to-endpoint data-movement planning, distinct from (and never
double-counted with) the Storage module's own AWS-egress-cost assumption
described in §5. Conceptual model, implemented in `cbio_cost/transfer_plan.py`
/ `cbio_cost/transfer_plan_models.py`:

    Endpoints → Dataset → Network → Transfer method → Duration + cost

**Storage's existing egress assumption vs. the Transfer module** — these
answer different questions and are deliberately kept separate:

| | Existing Storage egress model (`cbio_cost/transfer.py`) | Transfer module (`cbio_cost/transfer_plan.py`) |
|---|---|---|
| Question answered | How much AWS-to-Ilifu workflow egress does the selected retrieval/passes behaviour imply, and what does it cost? | How long will moving a specific dataset between two named endpoints take, and what provider cost applies? |
| Scope | One fixed direction (S3 → Ilifu workflow reads), folded into the Storage cost total | Any endpoint pair, explicit direction, one plan at a time |
| Cost ownership | Included in Storage's `grand_total_zar` | Never folded into any total (Project Summary shows it separately) |

Neither module imports from the other; they share only the same underlying
AWS egress pricing configuration (`config/aws-pricing.yaml`), reused by the
Transfer module via `cbio_cost.storage.tiered_cost` rather than a second
pricing source. Migrating Storage's egress assumption *into* Transfer is a
possible future direction but was explicitly not done in spec 012.

Endpoint types (`ENDPOINT_TYPES`): institutional/local storage, Ilifu/HPC,
AWS S3, Illumina ICA, other object storage, custom (user-named). Transfer
methods (`TRANSFER_METHODS`, descriptive only in V1 — selecting one does
not change the calculated throughput): Globus, AWS CLI/S3 multipart,
rclone, institutional DTN, ICA transfer mechanism, other, not yet selected.

Dataset volume is derived directly from the shared `Project.datasets` list
that Storage already computed (`cbio_cost.transfer_plan.dataset_presets`) —
the raw per-dataset size, not the headroom-inflated provisioned envelope —
so WGS and Custom Project modes share one source of truth with no
duplicated per-sample-volume logic, and Storage headroom is never silently
added to a transfer estimate.

### 11.1 Bandwidth modelling principles (Implemented)

The planner does not infer sustained network bandwidth merely from two
geographic locations. Physical distance can inform expected latency but
does not reliably determine achievable throughput — routing,
institutional networking, peering, firewall behaviour, congestion, DTNs,
TCP tuning and endpoint performance all matter. The Transfer module
supports three throughput modes (`cbio_cost.transfer_plan.throughput_result`):

- **Measured throughput** — preferred, where an actual source-to-
  destination transfer measurement is available. Classified **Measured**,
  never conflated with a speed-test result.
- **Known link capacity** — known network capacity with a configurable
  planning-efficiency assumption (default 70%, editable, always classified
  **Planning assumption** — 100% efficiency is never assumed silently).
- **Unknown bandwidth** — no value is invented; a planning-scenario table
  shows estimated duration at 100 Mbps, 500 Mbps, 1 Gbps, 5 Gbps and 10
  Gbps, each classified **Planning scenario**. No throughput in that table
  is recommended.

The transfer-time formula (`cbio_cost.transfer_plan.transfer_duration_seconds`):

    seconds = size_GB × 1024³ × 8 / (throughput_Mbps × 10⁶)

The project's `1 TB = 1024 GB` storage-unit convention (`cbio_cost.units`)
is preserved for dataset size throughout; network Mbps/Gbps follow normal
decimal network-rate definitions (`1 Mbps = 1,000,000 bits/second`) — these
are deliberately different unit systems and are never mixed silently.

**Implementation note on the worked example in spec 012 §12**: 1 TB at
1000 Mbps gives ≈2.44 h via the formula above, matching the spec text
exactly. The same formula at 700 Mbps (1000 Mbps × 70% efficiency) gives
≈3.49 h — the spec text's "≈3.41 h" for that case does not match its own
formula (duration scales as 1/throughput: 2.44h × 1000/700 ≈ 3.49h). The
implementation and its tests (`tests/test_transfer_plan.py`) derive both
figures from the formula rather than hard-coding either number, per the
spec's own instruction to do so.

### 11.2 Latency/RTT principles (Implemented)

Round-trip latency is an optional, secondary, advanced field. Bandwidth
remains the primary input for transfer-duration estimation; latency
influences whether available bandwidth can actually be utilised,
particularly over high-bandwidth long-distance TCP paths. If RTT is
supplied, the planner calculates the bandwidth-delay product
(`cbio_cost.transfer_plan.bandwidth_delay_product_bytes`):

    BDP_bytes = throughput_bits_per_second × RTT_seconds / 8

For example, 10 Gbps at 180 ms RTT gives exactly 225,000,000 bytes (225
MB) of data in flight — pure decimal-network-unit arithmetic, no binary
GB/TB conversion involved. BDP is presented as informational only: **not
additional project storage**, and it never feeds back into the duration
calculation:

    dataset size + planning throughput → estimated duration   (unaffected by RTT)
    bandwidth + RTT → bandwidth-delay product                  (informational only)

RTT remains optional if unknown; no arbitrary latency penalty is applied.

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
| BWA-MEM2 + sort runtime (NA12878) | 4.945 h/sample | Measured — CBIO/Ilifu | 32-core Xeon Gold 6142, hg38, §10.2 |
| BWA-MEM2 CPU consumption (NA12878) | ≈68.1 core-hours/sample | Measured — CBIO/Ilifu | (user+sys CPU time)/3600, not 32×wall time, §10.2 |
| BWA-MEM2 peak RAM (NA12878) | ≈116.7 GiB | Measured — CBIO/Ilifu | Max RSS, §10.2 |
| Alignment planning RAM allocation | 160 GiB | Planning assumption | Headroom over measured peak, §10.2 |
| CRAM index runtime (NA12878) | ≈15.1 min/sample | Measured — CBIO/Ilifu | `samtools index -@32`, lightweight, shares alignment concurrency, included in runtime total, §10.2 |
| Scratch/worker (working storage) | 250 GiB/worker | Planning assumption | Editable; same figure used for both stages; peak = max(alignment peak, DeepVariant peak), §10.5 |
| DeepVariant CPU runtime | ~1h09/sample on 96-vCPU/384-GiB reference config | Published benchmark | DeepVariant v1.10, §10.3 |
| GLnexus cohort resources | TBD | — | Research/benchmark required, §10.4 |
| Sentieon licence | US$1.50/genome (500 genomes = US$750 / R12,037.50) | Local commercial assumption | Current UCT planning rate, §10.6 |
| Sentieon runtime | TBD | — | Research/benchmark required, §10.6 |
| AWS S3/egress/request pricing | Config-driven (`config/aws-pricing.yaml`) | Published pricing (per-rate: UNVERIFIED) | af-south-1; see §6 |
| AWS compute (EC2) pricing | Pending verified regional pricing | — | Not invented; region af-south-1 recommended, §10.8 |
| USD/ZAR exchange rate | 16.05 (as of 2026-09-14) | Planning assumption | Placeholder; confirm against approved UCT/CBIO source |
| VAT | 15% | Planning assumption | Applied to AWS costs only |
| Engineering hourly rate | R1,000/hour | Planning assumption | Explicitly not an approved institutional rate |
| ICA/DRAGEN pricing | Under investigation | Published/commercial (pending) | Verify before implementation, §10.7 |
| Transfer default planning efficiency | 70% | Planning assumption | Editable; applications rarely sustain theoretical line rate, §11.1 |
| Transfer unknown-throughput scenarios | 100/500/1000/5000/10000 Mbps | Planning scenario | None recommended; shown when throughput is not known, §11.1 |
| AWS egress pricing reused for Transfer provider cost | Config-driven (`config/aws-pricing.yaml`), same as Storage | Published/provider pricing (per-rate: UNVERIFIED) | AWS S3 → non-AWS only; AWS ingress modelled as $0; all other endpoint pairs "Not currently calculated", §11 |

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
| **Compute V1 scope** (spec 011): support only the WGS 30x project profile; Custom Project shows a guard message rather than a Compute result | The reference workflow, benchmark and sample-count assumptions are WGS-30x-specific; extending to arbitrary Custom Project datasets needs separate design |
| **Compute "Sequential-stage planning estimate"** (spec 011a, renamed from "known modelled elapsed time"): sum the alignment, CRAM index and DeepVariant idealised elapsed times as if fully sequential across the whole cohort | A true pipelined estimate is workflow-overhead/scheduling modelling that spec 011/011a explicitly defer; a labelled worst-case sum is defensible and transparent in the meantime, and the label now avoids reading as an unconditional completion prediction |
| **CRAM indexing included, GLnexus excluded, from Compute totals** (spec 011a, corrects spec 011) | CRAM indexing is measured and lightweight but is a real, measured contribution to elapsed time — excluding it under a "workflow overhead" label was internally contradictory, since workflow overhead is separately defined as unmodelled scheduling/staging effects; GLnexus still has no approved benchmark, so it remains excluded |
| **Working storage is stage-specific** (spec 011a §12): `max(alignment peak, DeepVariant peak)`, each driven by its own concurrency, not a single shared-concurrency figure | The Compute page exposes two independent concurrency controls; a single `concurrent_workers = max(...)` scratch figure obscured which control actually drove the number shown |
| **Workflow and execution environment are separate Compute page sections** (spec 011a §4-§5, §18): Ilifu/HPC is a first-class execution option, not merely the benchmark source | Conflating "what processing occurs" with "where it runs" made Sentieon/AWS read as workflow alternatives rather than execution-environment alternatives, and understated Ilifu/HPC as a real (if unpriced) execution option |
| **Application starts with a minimum-valid project, not the 500-sample example** (spec 011a §2-§3) | The 500×30×/5-year demo silently presented as the user's real project on first load; a minimum-valid WGS project (1 sample, 1 year) plus an explicit "Load demo profile" action avoids that, and also gives every page a valid project to bootstrap from regardless of navigation entry point |
| **No per-stage AWS instance-type mapping in Compute V1** | No verified af-south-1 EC2 pricing exists in the repository; CPU/RAM requirements are kept independent of any specific instance choice until pricing is confirmed (spec 011 §22-§23) |
| **Transfer's engine module is named `cbio_cost/transfer_plan.py`, not `cbio_cost/transfer.py`** (spec 012) | `cbio_cost/transfer.py` already existed as Storage's own AWS-egress-cost engine (spec 006 §6-§8), used by `cbio_cost/calculator.py`; reusing that name for the new endpoint-to-endpoint movement planner would have shadowed a load-bearing module. The two never import from each other |
| **Transfer provider cost reuses `cbio_cost.storage.tiered_cost` and `config/aws-pricing.yaml`'s egress tiers directly, not a new pricing source** (spec 012 §18) | Only AWS S3 → non-AWS (tiered egress) and non-AWS → AWS S3 ($0 ingress) are calculated; every other endpoint pair shows "Not currently calculated" rather than an invented figure |
| **Transfer §12 worked-example discrepancy resolved by deriving from the formula, not hard-coding either figure** (spec 012) | The spec text's 700 Mbps example ("≈3.41 h") doesn't match its own §11 formula (≈3.49 h); §12 itself instructs deriving values rather than hard-coding, so the implementation and tests compute from the formula and document the discrepancy rather than picking one number to trust |

---

## 14. Open research backlog

### Compute

- Select representative AWS Cape Town instance types; verify current
  af-south-1 compute (EC2) and working-storage (EBS) pricing.
- Determine suitable temporary storage architecture and pricing.
- Compare the measured Ilifu NA12878 benchmark with an AWS execution of the
  same workflow.
- Validate DeepVariant AWS resource configuration.
- Research/benchmark GLnexus for approximately 500 WGS samples.
- Benchmark scratch/working-storage requirements to replace the 250
  GiB/worker planning default.
- Investigate Spot versus On-Demand economics.
- Investigate Sentieon runtime/performance using appropriate evidence;
  validate the UCT Sentieon commercial assumption before real budgeting.
- Research ICA/DRAGEN runtime and current iCredit/commercial model;
  research iGG separately from per-sample DRAGEN processing.
- Extend Compute modelling to Custom Project mode.
- Design and implement Cost-efficient / Balanced / Fast scenario presets.
- Model workflow pipelining (overlapping alignment/DeepVariant across
  samples) as an alternative to the sequential-stage planning estimate.
- Identify a common benchmark suitable for a controlled workflow accuracy
  comparison (§10.10) once one exists.
- Research Ilifu/HPC cost allocation/charging so the execution environment
  comparison (§10.8) can eventually include an HPC monetary cost figure.

### Transfer

- Establish practical throughput measurement guidance and gather measured
  institutional/Ilifu ↔ AWS transfer figures to replace planning scenarios.
- Determine whether transfer staging storage should be explicitly costed
  (§11.3 remains Planned).
- Verify current af-south-1 AWS egress pricing (shared with Storage,
  currently UNVERIFIED placeholder rates).
- Extend provider-cost modelling to endpoint pairs beyond AWS S3 (e.g.
  Illumina ICA iCredits, institutional DTN charges where applicable).
- Consider a migration of Storage's existing AWS-egress workflow assumption
  into the Transfer module once cost ownership/deduplication is explicit
  (spec 012 §17 — explicitly deferred, not done in 012).
- Consider supporting multiple transfer legs in one plan (spec 012 §30 —
  the model doesn't prevent this, but the V1 UI supports one at a time).
- Design Cost-efficient/Balanced/Fast-style transfer-method recommendations
  once method-specific throughput evidence exists (spec 012 §13).

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
- Compute is implemented only for the WGS 30x profile's open-source
  reference workflow (§10); GLnexus, AWS compute pricing, Sentieon/ICA
  runtime and Custom Project compute remain unimplemented within it.
- Transfer (§11) provider cost is calculated only for AWS S3 ↔ non-AWS
  endpoint pairs; every other pair shows "Not currently calculated," and
  transfer-method selection does not change the calculated throughput.
- The BWA-MEM2 benchmark behind Compute's alignment stage is one measured
  NA12878 execution on Ilifu hardware — not universal BWA-MEM2 performance,
  and AWS performance cannot be inferred exactly from Ilifu core counts.
- Compute's "Sequential-stage planning estimate" excludes GLnexus and
  workflow overhead (queue delay, instance startup, retries, staging,
  interruptions, contention); it assumes stages execute sequentially across
  the cohort and does not model pipelining — see §10.9.
- Compute's Ilifu/HPC execution environment has no monetary cost currently
  modelled — this states that HPC cost allocation is unmodelled, not that
  HPC execution is free — see §10.8.
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
