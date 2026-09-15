# 009 — Add Initial Design, Assumptions and Decision Documentation

## Objective

Create the initial living design and assumptions document for the
CBIO Genomics Infrastructure Cost Planner.

This task is documentation only.

Do not change application behaviour, calculations, pricing logic,
configuration values, UI, styling, tests, or existing project defaults
unless a trivial documentation link in the README is appropriate.

The purpose of this task is to establish a durable source of truth for:

- the purpose and architecture of the planner;
- implemented functionality;
- planned functionality;
- modelling assumptions;
- evidence and provenance;
- important design decisions;
- benchmarks;
- known limitations;
- open research questions.

Future implementation instructions will maintain this document as the
project evolves.

---

# 1. Create the documentation file

Create:

    docs/design-and-assumptions.md

Use the title:

# CBIO Genomics Infrastructure Cost Planner
## Design, Assumptions and Decision Record

The document should be concise enough to remain useful, but detailed
enough that a developer or technical reviewer can understand why the
planner behaves as it does without needing access to previous ChatGPT,
Claude, Codex, or other AI conversations.

Do not write the document as a changelog.

Do not document implementation minutiae that belong in source-code
comments or the README.

---

# 2. Establish status terminology

The document must clearly distinguish between functionality that exists
and functionality that is being designed.

Use the following status terminology consistently:

- **Implemented** — currently available in the application.
- **Planned** — agreed design direction but not yet implemented.
- **Under investigation** — requires further research, benchmarking,
  validation, pricing information, or a design decision.
- **Out of scope** — deliberately not part of the current development
  scope.

Never describe Planned or Under investigation functionality as if it
already exists in the application.

---

# 3. Establish evidence classifications

Important numerical assumptions, benchmarks and commercial inputs must
be classified by provenance.

Use these evidence classes:

### Measured

Measured by CBIO/UCT or the project team on actual infrastructure or
using an explicitly documented test.

Examples include future Ilifu or AWS benchmarks.

### Published benchmark

A value reported by a software developer, cloud provider, peer-reviewed
paper, technical report, or other external source.

Record the source and relevant version/date where possible.

### Planning assumption

A reasonable modelling value used for infrastructure planning but not
presented as a measured or authoritative value.

### Local commercial assumption

A price or commercial term available locally to UCT/CBIO that may not
represent public or generally available pricing.

The document should make these classifications visible wherever they
materially affect calculations or architectural recommendations.

---

# 4. Document the purpose of the planner

Describe the planner as a technical planning tool for estimating and
comparing genomics infrastructure requirements and costs.

The current implemented functionality is primarily focused on storage.

The planned broader architecture is:

    Storage
       ↓
    Compute
       ↓
    Transfer
       ↓
    Project Summary

These are logical planning domains rather than necessarily sequential
execution stages.

The long-term intent is for all modules to operate over a shared project
and dataset model so that the planner can produce a coherent project
infrastructure estimate.

The application should remain explainable and deterministic rather than
producing opaque infrastructure recommendations.

---

# 5. Document the current project model

Document the distinction between:

## WGS 30× template

A predefined planning profile for approximately 30× whole-genome
sequencing.

The user primarily specifies the number of samples while advanced
planning assumptions determine estimated dataset sizes and behaviour.

Do not derive file sizes dynamically from sequencing depth.

The current planning defaults include approximately:

| Data type | Planning value |
|---|---:|
| FASTQ | 100 GB/sample |
| CRAM | 40 GB/sample |
| gVCF/QC/indexes | 10 GB/sample |

These values are planning assumptions, not guarantees.

The current 500-sample example therefore represents approximately:

- FASTQ: 50,000 GB
- CRAM: 20,000 GB
- gVCF/QC/indexes: 5,000 GB
- total durable data before additional headroom: 75,000 GB

Document the existing operational/headroom assumptions from the current
application/configuration rather than inventing new values.

## Custom Project

Document the generic dataset model introduced for projects that do not
fit the WGS template.

A custom dataset can describe characteristics such as:

- dataset name;
- total dataset size;
- unit;
- retrieval percentage;
- read passes;
- active storage period;
- archive class;
- retention period where currently supported.

Make clear that Custom Project dataset size represents total dataset
size, not per-sample size.

The WGS profile should conceptually be regarded as a predefined template
over the same general project/dataset model rather than an entirely
separate calculation engine.

---

# 6. Document current storage modelling

Document the currently implemented storage model by inspecting the
application and configuration files.

Do not rely only on this instruction where the repository provides a
more precise description of current behaviour.

Cover:

- active S3 storage;
- archive storage;
- lifecycle behaviour;
- retrieval/read assumptions;
- data-transfer assumptions that are currently part of the storage
  calculator;
- engineering/support assumptions;
- sensitivity scenarios;
- currency conversion;
- VAT handling;
- pricing provenance;
- exports;
- Custom Project behaviour.

Explain that S3 lifecycle transitions normally change an object's
storage class while the object remains under the same bucket/key
namespace.

Document the supported storage classes actually implemented by the
application.

Do not introduce new storage calculations.

---

# 7. Document current pricing provenance

Inspect the pricing configuration and record the actual current values
and metadata used by the application.

The current intended AWS pricing basis is:

- Provider: AWS
- Region: Africa (Cape Town)
- Region code: af-south-1
- Pricing source:
  https://aws.amazon.com/s3/pricing/
- Pricing last verified: 2026-08-31

Verify these against the repository configuration.

If the repository differs, document the actual implemented state and
explicitly note the discrepancy rather than silently changing either
the application or configuration.

Published AWS pricing must remain distinguishable from configurable
planning assumptions.

The existing engineering/support rate should be explicitly described as
an illustrative planning rate rather than an approved institutional
charge unless the repository already provides more precise wording.

---

# 8. Document the data-volume reference guide

Document that the application provides rough planning guidance for
common genomics data types.

The guide is informational only.

It must not be interpreted as a sequencing-depth-to-file-size
calculator.

Record the currently implemented guide values from the application,
including the existing 4×, 12× and 30× WGS guidance and other assay/data
types where present.

State that measured project volumes should be preferred whenever they
are available.

Actual data sizes vary according to factors including:

- sequencing platform;
- coverage;
- read length;
- compression;
- reference;
- variant caller;
- assay;
- pipeline;
- representation.

---

# 9. Document data governance principles

Document the existing governance guidance.

The calculator estimates infrastructure requirements and cost. It does
not determine whether sensitive research data may legally,
institutionally, ethically, or contractually be stored in a particular
cloud or object-storage environment.

Relevant considerations include:

- participant consent;
- ethics approvals;
- data-access agreements;
- institutional policy;
- storage jurisdiction/location;
- identity and access controls;
- encryption;
- audit logging;
- retention and deletion;
- data-transfer requirements.

A cost estimate does not constitute approval to store project data in
AWS.

The planner should not require or encourage users to enter participant-
level data, phenotype data, variants, credentials, AWS keys, or other
sensitive project information merely to obtain an infrastructure
estimate.

---

# 10. Document the planned Compute model

Mark this entire section clearly as **Planned** unless repository
inspection shows that some component has already been implemented.

Compute should be separated conceptually from durable Storage costing.

The Compute module should eventually model:

- processing stages;
- CPU;
- RAM;
- runtime;
- temporary/working storage;
- concurrency;
- wall-clock completion time;
- infrastructure cost;
- software/licensing cost;
- execution architecture.

It should support scenarios such as:

- Cost-efficient
- Balanced
- Fast

Do not assume that a faster scenario necessarily costs proportionally
more or less.

Calculate such differences from infrastructure use once implemented.

Parallelism can alter:

- wall-clock duration;
- simultaneous scratch requirements;
- instance selection;
- utilisation;
- Spot/on-demand exposure;
- storage lifetime;
- price/performance.

---

# 11. Document the planned open-source 30× WGS compute reference

The current design direction for the default open-source reference
workflow is:

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

This is a planning/design decision and should not be described as
implemented.

GATK may be considered later as an alternative workflow but is not
currently intended to be the primary default reference workflow.

The workflow should be modelled by stages rather than assigning one
undifferentiated "compute hours per genome" number.

For example:

### Alignment stage

Per-sample parallel work:

    FASTQ → BWA-MEM2 → sort/compress → CRAM → CRAI

Resource characteristics to model include:

- CPU;
- RAM;
- runtime;
- working storage;
- I/O behaviour.

### Variant-calling stage

Per-sample parallel work:

    CRAM → DeepVariant → gVCF

This stage may use a different instance/resource profile from alignment.

### Cohort stage

Cohort-level work:

    gVCFs → GLnexus → joint callset

Do not model GLnexus simply as another identical per-sample job.

Its memory, compute, storage and runtime requirements should eventually
be benchmarked for representative cohort sizes.

---

# 12. Record the planned BWA-MEM2 benchmark

Record that a CBIO/Ilifu benchmark is planned.

A recent workflow used by Scott provides the reference form of the
test:

    bwa-mem2 mem -t 20 \
      -R '@RG\tID:AGS0834\tSM:AGS0834\tPL:AGS0834' \
      t2t/chm13v2.0.fa \
      AGS0834_1.fq.gz AGS0834_2.fq.gz \
    | samtools sort \
      --reference t2t/chm13v2.0.fa \
      --threads 20 \
      -o AGS0834.cram -

    samtools index -@10 AGS0834.cram

Do not invent a runtime for this benchmark.

Status:

**Under investigation — CBIO/Ilifu benchmark planned.**

The benchmark should ideally capture:

- FASTQ R1/R2 sizes;
- approximate sequencing depth;
- reference;
- CPU model;
- allocated CPU count;
- allocated RAM;
- wall-clock time;
- peak RAM;
- source filesystem/storage;
- temporary/working storage;
- peak temporary disk usage if practical;
- resulting CRAM size;
- indexing time if measured separately.

Where practical, `/usr/bin/time -v` can be used to capture process
resource information.

The purpose of this benchmark is to establish a local observed reference
point that can later be compared with an AWS execution environment.

---

# 13. Record the DeepVariant benchmark evidence

Document the currently identified DeepVariant published benchmark as a
**Published benchmark**, not a CBIO measurement.

At the time of this design work, DeepVariant v1.10 documentation reports
a 30× WGS CPU benchmark on a 96-vCPU / 384-GiB reference machine of
approximately:

- make_examples: 46m 15s
- call_variants: 15m 58s
- postprocess: 6m 45s
- total: approximately 1h 8m 58s

Source:

https://github.com/google/deepvariant/blob/r1.10/docs/metrics.md

Also record that DeepVariant explicitly notes that the benchmark
configuration is intended for benchmark consistency and is not
necessarily the fastest or cheapest configuration.

Do not translate this runtime directly into an AWS cost until an
appropriate AWS reference configuration and pricing model have been
selected.

The DeepVariant documentation/reference data also provides useful
support for a roughly 40 GB 30× CRAM planning value, but keep the
project's 40 GB/sample value classified as a planning assumption unless
we have measured it locally.

Where relevant, record the DeepVariant version associated with the
benchmark.

---

# 14. Document intermediate/working compute storage

This is an important planned part of Compute.

Do not treat durable project storage as the only storage requirement.

Distinguish:

### Durable storage

Long-lived project inputs and released outputs.

Modelled primarily in the Storage module.

### Compute working storage

Temporary/intermediate storage required while jobs execute.

Examples may include:

- compressed FASTQs being processed;
- alignment/sorting temporary files;
- BAM/CRAM intermediates;
- DeepVariant working files;
- workflow work directories;
- container temporary data;
- cohort-calling temporary files.

Model this eventually by processing stage and concurrency.

A useful conceptual relationship is:

    simultaneous working storage
      ≈ scratch required per worker × concurrent workers

However, storage cost must account for both provisioned capacity and
lifetime.

A fast scenario with high concurrency may require substantially more
simultaneous scratch capacity but hold it for less time.

Therefore do not assume that scratch cost scales directly with maximum
capacity.

Potential AWS implementations may include EBS, instance-local NVMe,
shared filesystems, or other appropriate temporary storage.

The final implementation should calculate working-storage cost according
to the selected architecture rather than applying one generic scratch
price.

Current scratch requirements are:

**Under investigation — benchmark required.**

---

# 15. Document Sentieon as a planned commercial option

Sentieon should be considered a commercial accelerated alternative in
the future Compute module.

Record the current UCT planning licence rate as:

    US$1.50 per genome

Classify this as:

**Local commercial assumption**

Describe it as a current UCT planning value that must be confirmed for
actual project budgeting.

Do not present it as public Sentieon list pricing.

For example, at this assumption:

    500 genomes × US$1.50 = US$750 licence cost

The software licence must be itemised separately from:

- compute infrastructure;
- temporary storage;
- data transfer;
- durable storage.

Do not imply that US$1.50/genome represents the total cost of running a
Sentieon workflow.

Sentieon runtime/performance assumptions remain:

**Under investigation**

until appropriate local or published benchmarks are selected.

---

# 16. Document ICA / DRAGEN / iGG as a planned alternative

Record Illumina Connected Analytics / DRAGEN as another potential
execution strategy.

Keep this marked as **Under investigation** until current pricing,
runtime, licensing and workflow behaviour are sufficiently validated for
implementation.

The architecture may conceptually include:

    FASTQ
      ↓
    ICA / DRAGEN
      ↓
    per-sample gVCF
      ↓
    optional DRAGEN iterative gVCF genotyper (iGG)
      ↓
    cohort callset

Do not silently combine iGG pricing into individual DRAGEN processing.

Record current published pricing information only where it has been
verified and include source/date.

Relevant current reference:

https://help.ica.illumina.com/reference/r-pricing

Also note that Illumina commercial platform/pricing models may evolve,
so pricing should eventually be configuration-driven and version/date
stamped rather than embedded as permanent constants.

Do not implement ICA costing as part of this documentation task.

---

# 17. Document execution architecture principles

Record the current design principle that the planner should not assume
Slurm is always the preferred execution environment.

For highly parallel per-sample genomics processing on AWS, architectures
such as:

    Nextflow
      +
    AWS Batch
      +
    containerised workers
      +
    object storage
      +
    appropriate temporary working storage

may be suitable.

Slurm remains a valid architecture for workloads or environments where
an HPC scheduler is appropriate.

The eventual planner should recommend an execution architecture based on
workload characteristics rather than always selecting one scheduler.

This remains **Planned**.

---

# 18. Document planned completion-time scenarios

The Compute model should eventually support both resource/cost estimates
and expected elapsed completion time.

Important concepts:

### Total compute consumption

For example:

    jobs × runtime × resources

### Concurrency

Number of jobs executing simultaneously.

### Estimated wall-clock completion

Approximately dependent on:

    number of jobs
    ÷ concurrency
    × runtime per job

with additional workflow/stage constraints.

The eventual tool may support:

- Cost-efficient
- Balanced
- Fast

and/or a user-selected target completion time.

For example:

    Target completion: 7 days

could be used to estimate the concurrency required.

Do not assume that the compute cost is identical between scenarios.
Instance price/performance, scaling efficiency, storage lifetime,
provisioning, Spot availability and other factors may cause differences.

---

# 19. Document the planned Transfer model

Mark this section as **Planned**.

The conceptual model is:

    Endpoints
       ↓
    Dataset
       ↓
    Network
       ↓
    Transfer method
       ↓
    Duration + cost + practical recommendation

Potential endpoints include:

- institutional/local HPC;
- Ilifu;
- AWS S3;
- Illumina ICA;
- other object storage;
- custom endpoint.

Potential transfer methods include:

- S3 multipart transfer;
- AWS CLI;
- rclone;
- Globus;
- institutional DTN;
- ICA transfer mechanism;
- other/custom method.

Do not assume that transfer method automatically changes pricing unless
the selected endpoint/service actually has a relevant charge.

---

# 20. Document bandwidth modelling principles

The planner should not infer sustained network bandwidth merely from two
geographic locations.

Physical distance can inform expected latency, but it does not reliably
determine achievable throughput.

Routing, institutional networking, peering, firewall behaviour,
congestion, DTNs, TCP tuning and endpoint performance all matter.

The planned Transfer module should support three bandwidth modes:

### Measured throughput

Preferred where an actual source-to-destination transfer measurement is
available.

### Known link capacity

Use known network capacity together with a configurable planning
efficiency.

### Unknown bandwidth

Do not invent a bandwidth value.

Instead show useful scenarios such as:

- 100 Mbps;
- 500 Mbps;
- 1 Gbps;
- 5 Gbps;
- 10 Gbps.

The project convention should continue to distinguish storage units from
network-rate units correctly.

Where the existing calculator uses:

    1 TB = 1024 GB

preserve that convention.

Network Mbps/Gbps should follow normal decimal network-rate definitions.

---

# 21. Document latency/RTT principles

Round-trip latency should be an optional secondary network
characteristic.

Bandwidth remains the primary input for transfer-duration estimation.

Latency influences whether the available bandwidth can actually be
utilised, particularly over high-bandwidth long-distance TCP paths.

If RTT is supplied, the future planner may calculate the
bandwidth-delay product (BDP):

    BDP = bandwidth × RTT

This can support recommendations concerning:

- TCP window requirements;
- parallel streams;
- multipart transfer;
- Globus;
- DTNs;
- resumable transfers.

Do not initially apply an arbitrary latency penalty directly to the
transfer-duration formula.

Instead:

    dataset size + planning throughput
        → estimated duration

and:

    bandwidth + RTT + transfer method
        → transfer feasibility/advice

If RTT is unknown, it should remain optional.

---

# 22. Distinguish transfer staging storage

Record that temporary transfer/staging storage is conceptually distinct
from both durable storage and compute working storage.

The project therefore recognises three broad storage contexts:

| Storage context | Primary module |
|---|---|
| Durable project storage | Storage |
| Compute working/intermediate storage | Compute |
| Transfer staging/validation storage | Transfer |

Avoid double-counting the same physical storage resource if a future
architecture intentionally reuses it for multiple purposes.

---

# 23. Create an assumptions/evidence table

Include a concise table of important assumptions and evidence.

At minimum include entries conceptually equivalent to:

| Item | Current value/status | Evidence class | Notes |
|---|---:|---|---|
| 30× WGS FASTQ | ~100 GB/sample | Planning assumption | Current WGS profile |
| 30× WGS CRAM | ~40 GB/sample | Planning assumption | Supported by external examples; local measurement pending |
| 30× WGS gVCF/QC/indexes | ~10 GB/sample | Planning assumption | Generic planning value |
| BWA-MEM2 runtime | TBD | Measured | Ilifu benchmark planned |
| BWA-MEM2 scratch | TBD | Measured | Ilifu benchmark planned |
| DeepVariant CPU runtime | ~1h09/sample on reference configuration | Published benchmark | DeepVariant v1.10 |
| GLnexus cohort resources | TBD | — | Research/benchmark required |
| Sentieon licence | US$1.50/genome | Local commercial assumption | Current UCT planning rate |
| Sentieon runtime | TBD | — | Research/benchmark required |
| AWS S3 pricing | Config-driven | Published pricing | af-south-1 |
| ICA/DRAGEN pricing | Under investigation | Published/commercial | Verify before implementation |
| Transfer bandwidth | User measurement/link/scenario | Planning input | Do not infer from geography |
| Compute working storage | TBD | Measured/planning | Benchmark required |

Use actual implemented/configured values where they differ from this
summary.

---

# 24. Add an initial decision record

Create a dated decision log in the document.

Use the current date of this instruction where appropriate:

    2026-09-15

Record important decisions already made, including:

### Project structure

The planner is evolving toward:

    Storage → Compute → Transfer → Project Summary

### Shared modelling

WGS templates and Custom Project should ultimately use a common
underlying dataset/project model.

### WGS depth

Do not expose sequencing depth as a normal input for the fixed WGS 30×
profile merely to derive file sizes.

Use explicit planning volumes and provide reference guidance instead.

### File-size guidance

Provide rough reference ranges rather than pretending that genomic file
size can be precisely derived from coverage.

### Compute reference workflow

Use BWA-MEM2 + DeepVariant + GLnexus as the initial planned open-source
30× WGS reference workflow.

Keep GATK as a potential future alternative.

### Compute scenarios

Model different completion strategies rather than only a single
"cheapest" run.

### Working storage

Intermediate/working storage is part of Compute costing and must not be
forgotten.

### Scheduler architecture

Do not assume Slurm is always the correct cloud execution model.

### Transfer bandwidth

Do not infer sustained bandwidth from geography.

Prefer measured throughput, known link capacity, or explicit scenarios.

### Latency

Treat RTT as a transfer feasibility/performance characteristic rather
than applying an arbitrary latency penalty to calculated duration.

### Evidence

Clearly distinguish local measurements, published benchmarks, planning
assumptions and local commercial assumptions.

Provide a short rationale for each decision.

---

# 25. Add an open research backlog

Create a clearly labelled section for unresolved work.

At minimum include:

## Compute

- Run BWA-MEM2 FASTQ → CRAM benchmark on Ilifu.
- Measure wall time.
- Record CPU and RAM.
- Measure/estimate peak working storage.
- Record resulting CRAM size.
- Select representative AWS Cape Town instance types.
- Verify current af-south-1 compute pricing.
- Determine suitable temporary storage architecture and pricing.
- Compare Ilifu measurement with AWS execution.
- Validate DeepVariant AWS resource configuration.
- Research/benchmark GLnexus for approximately 500 WGS samples.
- Investigate Spot versus On-Demand economics.
- Investigate Sentieon runtime/performance using appropriate evidence.
- Validate UCT Sentieon commercial assumption before real budgeting.
- Research ICA/DRAGEN runtime and current iCredit/commercial model.
- Research iGG separately from per-sample DRAGEN processing.

## Transfer

- Define transfer endpoint model.
- Define transfer-method recommendations.
- Establish practical throughput measurement guidance.
- Determine how cloud egress pricing should be applied by endpoint.
- Determine whether transfer staging storage should be explicitly
  costed.
- Consider RTT/BDP advisory logic.
- Test representative institutional/Ilifu → AWS transfer paths when
  possible.

## Storage

- Continue validating real WGS file-size assumptions against measured
  CBIO projects.
- Consider whether workflow-specific gVCF assumptions should eventually
  replace the generic gVCF planning value.
- Continue validating lifecycle assumptions against real project access
  patterns.

Do not turn open research items into application assumptions until they
have been evaluated.

---

# 26. Document explicit current limitations

Include a section explaining important limitations.

Examples:

- cost estimates are planning estimates, not quotations;
- published cloud prices change;
- local commercial pricing may not apply to every project;
- genomics data volumes vary;
- runtime depends strongly on hardware, I/O, software version and
  workflow configuration;
- network throughput cannot be predicted reliably from geography;
- current Compute and Transfer designs are not yet implemented;
- sensitive-data governance remains project/institution specific;
- the planner does not constitute infrastructure, security, ethics,
  procurement or compliance approval.

---

# 27. Preserve source references

Where a numerical value comes from a published external source, include
a reference.

Current useful references include:

AWS S3 pricing:

    https://aws.amazon.com/s3/pricing/

AWS S3 storage lifecycle guidance:

    https://docs.aws.amazon.com/whitepapers/latest/genomics-data-transfer-analytics-and-machine-learning/appendix-f-optimizing-storage-cost-and-data-lifecycle-management.html

AWS archived-object guidance:

    https://docs.aws.amazon.com/AmazonS3/latest/userguide/archived-objects.html

DeepVariant metrics:

    https://github.com/google/deepvariant/blob/r1.10/docs/metrics.md

DeepVariant details:

    https://github.com/google/deepvariant/blob/r1.10/docs/deepvariant-details.md

BWA-MEM2:

    https://github.com/bwa-mem2/bwa-mem2

GLnexus:

    https://github.com/dnanexus-rnd/GLnexus

Illumina ICA pricing:

    https://help.ica.illumina.com/reference/r-pricing

Do not invent publication dates, prices or benchmark results that have
not been verified.

For volatile information such as cloud/commercial pricing, record a
verification date where known.

---

# 28. README link

If appropriate, add a small documentation link to the existing README,
for example:

    ## Design documentation

    See `docs/design-and-assumptions.md` for architecture decisions,
    planning assumptions, benchmark provenance and open research
    questions.

Do not otherwise rewrite or restructure the README as part of this task.

---

# 29. Establish the permanent documentation-maintenance rule

Add a short section near the end of `docs/design-and-assumptions.md`
called:

## Maintaining this document

It should establish the following rule for future development:

After implementing a material application change, review this document.

Update it when the change introduces or modifies:

- architecture;
- modelling assumptions;
- benchmark values;
- pricing inputs or provenance;
- design decisions;
- evidence status;
- known limitations;
- open research questions.

Do not update the document merely because code changed.

Do not use it as a commit log or task history.

Do not duplicate implementation details that belong in the README,
source code, configuration, tests, or Git history.

When new evidence replaces a planning assumption:

1. update the value if appropriate;
2. update its evidence classification;
3. record its source/version/date;
4. preserve enough decision context to explain why the model changed.

When a Planned item becomes Implemented, update its status.

When an open research question is resolved, remove it from the active
backlog and, if materially important, record the resulting decision or
assumption.

---

# 30. Requirement for future instruction files

From the next implementation instruction onward, each material
instruction should contain a documentation requirement equivalent to:

> ## Documentation requirement
>
> After implementing this change, review
> `docs/design-and-assumptions.md`.
>
> Update it only if this change materially changes architecture,
> modelling assumptions, benchmarks, pricing/provenance, design
> decisions, evidence status, known limitations, or open research
> questions.
>
> Preserve the distinction between Implemented, Planned, Under
> investigation and Out of scope.
>
> Preserve evidence classifications:
> Measured, Published benchmark, Planning assumption and Local
> commercial assumption.
>
> Do not modify the document merely to record that this task occurred.

This requirement applies to future substantial feature/model changes.

Minor styling fixes, typo corrections and implementation-only refactors
do not require a documentation update unless they change the meaning of
the planner.

---

# 31. Repository inspection requirement

Before writing the document:

1. inspect the current repository;
2. inspect the current pricing/configuration files;
3. inspect existing instruction files where useful;
4. inspect current implemented WGS and Custom Project behaviour;
5. inspect existing data-volume and governance guidance;
6. distinguish current implementation from the planned architecture in
   this instruction.

Where this instruction conflicts with actual current implementation:

- do not silently rewrite history;
- document the implemented behaviour accurately;
- note a meaningful discrepancy where necessary;
- do not change calculations as part of this task.

The documentation should describe the repository that actually exists,
while also recording the agreed planned direction.

---

# 32. Validation

Before completing the task:

- confirm `docs/design-and-assumptions.md` exists;
- confirm Implemented and Planned functionality are clearly
  distinguished;
- confirm no BWA-MEM2 runtime has been invented;
- confirm the DeepVariant benchmark is labelled Published benchmark;
- confirm the Sentieon US$1.50/genome value is labelled Local commercial
  assumption;
- confirm working/intermediate compute storage is documented;
- confirm Compute scenarios are documented as Planned;
- confirm Transfer bandwidth is not inferred from geography;
- confirm latency is not directly used as an arbitrary transfer-time
  penalty;
- confirm the research backlog exists;
- confirm the decision record exists;
- confirm pricing/source provenance is present;
- confirm future documentation-maintenance rules are present;
- confirm no application calculations or behaviour were changed.

Report:

1. files created;
2. files modified;
3. major documentation sections added;
4. any discrepancies found between repository implementation and the
   assumptions supplied in this instruction;
5. any claims or values deliberately left as TBD because evidence is
   still required.

Do not implement Compute, Transfer, Project Summary, new pricing logic,
or new calculator functionality as part of 009.