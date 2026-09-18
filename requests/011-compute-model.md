# 011 — Compute Model and Initial WGS Compute Planner

## Objective

Implement the first functional **Compute** module of the CBIO Genomics Infrastructure Cost Planner.

The Compute module should estimate the resources, runtime, working storage, execution configuration and eventual cost required to process a genomics project.

For this first implementation, focus on the existing **30× WGS project profile** and the initial open-source workflow:

```text
FASTQ
  ↓
BWA-MEM2 alignment
  ↓
sorted CRAM + CRAI
  ↓
DeepVariant
  ↓
per-sample gVCF
  ↓
GLnexus cohort joint calling
```

The implementation must be deterministic and transparent.

Do **not** use AI/LLM-generated estimates.

Most importantly:

> Every significant calculated output must be traceable to its input, formula, benchmark, evidence source and planning assumption.

Measured observations must never silently become universal defaults.

---

# 1. Preserve Existing Application Architecture

Retain the current top-level application architecture:

```text
Storage
Compute
Transfer
Project Summary
```

Do not change:

- Storage calculations
- Storage pricing
- WGS30x storage profile
- Custom Project storage mode
- Transfer placeholder
- existing navigation architecture
- existing GRO visual styling
- CBIO / Genomics Infrastructure Cost Planner header
- current Streamlit `st.navigation + st.Page` architecture

This task primarily implements the Compute page.

Do not revisit branding or navigation.

---

# 2. Evidence Model

Introduce an explicit evidence/provenance model for compute assumptions.

Every important benchmark or assumption should belong to one of four evidence classes.

## 2.1 Measured — CBIO/Ilifu

Measurements obtained directly from CBIO/Ilifu workloads.

Example:

NA12878 BWA-MEM2 benchmark described below.

## 2.2 Published benchmark

Measurements published by a software vendor/project, academic publication or other documented external source.

Example:

DeepVariant official benchmark.

## 2.3 Planning assumption

A value selected for infrastructure planning where no direct measurement exists or where safety/headroom is intentionally applied.

Examples:

- RAM headroom
- scratch allocation
- worker concurrency
- runtime scaling
- cloud performance equivalence
- utilisation efficiency

## 2.4 Local commercial assumption

Locally supplied commercial or institutional figures.

Examples:

- Sentieon UCT licence estimate
- CBIO engineering rate

Evidence classification should be represented in the internal model rather than only rendered as explanatory text.

---

# 3. Evidence Record

Where practical, use a structured record such as:

```python
Evidence(
    classification="measured",
    label="Measured — CBIO/Ilifu",
    source="NA12878 BWA-MEM2 benchmark",
    date="2026-09-17",
    value=...,
    notes=...
)
```

The exact Python implementation may differ if a better design fits the existing repository.

The important requirement is that assumptions and benchmarks remain traceable.

---

# 4. Measured BWA-MEM2 Benchmark

Add the following benchmark to the project's documented compute evidence.

## Benchmark

Classification:

**Measured — CBIO/Ilifu**

Sample:

NA12878

Input:

- R1 FASTQ: approximately 48 GB
- R2 FASTQ: approximately 49 GB
- total compressed FASTQ: approximately 97 GB

Reference:

`Homo_sapiens_assembly38.fasta`

GATK hg38 reference.

CPU:

- Intel Xeon Gold 6142 @ 2.60 GHz
- 2 sockets
- 16 physical cores/socket
- 32 physical cores total
- 1 hardware thread/core

Alignment:

```bash
bwa-mem2 mem -t 32 ...
```

piped directly to:

```bash
samtools sort \
  --reference Homo_sapiens_assembly38.fasta \
  --threads 32 \
  -o NA12878.cram
```

Measured GNU time statistics:

- elapsed wall time: 4:56:42
- user CPU time: 239688.20 seconds
- system CPU time: 5558.03 seconds
- average CPU utilisation: 1377%
- maximum resident set size: 122379120 KB
- swaps: 0
- exit status: 0

Derived values:

- wall time ≈ 4.945 hours/sample
- effective average CPU utilisation ≈ 13.77 cores
- CPU consumption ≈ 68.1 core-hours/sample
- peak RAM ≈ 116.7 GiB

Output:

- CRAM ≈ 57 GB
- CRAI ≈ 2.5 MB

Do not describe this as universal BWA-MEM2 performance.

The UI/documentation must identify it as one measured CBIO/Ilifu benchmark.

---

# 5. CRAM Index Benchmark

Classification:

**Measured — CBIO/Ilifu**

Command:

```bash
samtools index -@32 NA12878.cram
```

Measured:

- wall time: 15:08.66
- user time: 170.09 s
- system time: 60.18 s
- average CPU utilisation: 25%
- maximum resident set size: 28,928 KB
- exit status: 0

Treat CRAM indexing as a lightweight downstream operation.

Do not model it as requiring a dedicated 32-core worker merely because `-@32` was specified.

---

# 6. Alignment Planning Profile

Create an initial planning profile derived from the measured benchmark.

Suggested initial planning resources:

- requested CPU: 32
- requested RAM: 160 GiB
- baseline runtime: 4.945 h/sample

Important:

32 CPU is based on the measured execution configuration.

160 GiB RAM is **not measured**.

It is a:

**Planning assumption**

derived from the measured peak RAM of approximately 116.7 GiB plus operational headroom.

The UI must make this distinction visible.

Do not say:

> BWA-MEM2 requires 160 GiB.

Instead say something equivalent to:

> Planning allocation: 160 GiB  
> Measured peak: 116.7 GiB in the CBIO/Ilifu NA12878 benchmark.

---

# 7. Existing WGS Storage Assumptions

Do not change the existing WGS30x storage defaults in this task.

Existing planning defaults include approximately:

- FASTQ: 100 GB/sample
- CRAM: 40 GB/sample
- gVCF/QC: 10 GB/sample

The measured NA12878 values should be documented alongside these:

- measured FASTQ: ~97 GB
- measured CRAM: ~57 GB

This does **not** justify changing the generic CRAM default from 40 GB based on one sample.

Clearly distinguish:

Planning assumption:

```text
40 GB CRAM/sample
```

from:

Measured:

```text
57 GB NA12878 CRAM
```

---

# 8. DeepVariant Benchmark

Add an initial DeepVariant benchmark based on the official DeepVariant v1.10 runtime documentation.

Classification:

**Published benchmark**

Source:

Google DeepVariant v1.10 runtime metrics.

Benchmark environment:

- GCP `n2-standard-96`
- 96 vCPU
- 384 GiB RAM
- CPU-only
- WGS sample HG003

Reported WGS runtime:

- make_examples: 46m15s
- call_variants: 15m58s
- postprocess_variants: 6m45s
- total: 1h08m58s

The benchmark was averaged over five runs.

The DeepVariant documentation explicitly states that this configuration is selected for reproducibility/consistency and is **not necessarily the fastest or cheapest configuration**.

The planner must preserve this qualification.

Do not claim that an AWS instance will reproduce this runtime.

Any mapping from this GCP benchmark to AWS is a:

**Planning assumption**

until benchmarked.

---

# 9. GLnexus

Represent GLnexus as the cohort-level joint-calling stage.

Do not invent a runtime or AWS cost for GLnexus in this task.

Until a suitable benchmark is selected:

Runtime:

**Under investigation**

Evidence status:

**No approved planning benchmark**

The Compute page may show the stage and clearly indicate that it is not yet included in runtime/cost totals.

This is preferable to presenting an unsupported estimate.

---

# 10. Compute Stage Model

Create a reusable internal compute-stage model.

Conceptually:

```text
ComputeStage
    name
    workflow_stage
    scope
        per_sample
        cohort
    cpu
    memory_gib
    runtime_hours
    working_storage_gib
    accelerator
    software
    evidence
    included_in_total
```

Do not hard-code the entire implementation directly into Streamlit UI code.

Separate calculation/model logic from rendering.

This should allow later addition of:

- Sentieon
- GATK
- DRAGEN / ICA
- custom workflows
- GPU workflows
- alternative clouds
- local HPC

without rewriting the page.

---

# 11. Separate Allocated Resources from Utilisation

The model must distinguish:

## Allocated resources

Example:

32 CPU allocated.

## Measured utilisation

Example:

13.77 effective average CPU cores used.

Do not calculate measured CPU consumption as:

```text
32 × wall time
```

For the measured BWA benchmark:

CPU consumption should remain approximately:

```text
68.1 core-hours/sample
```

This distinction should be visible in benchmark details.

---

# 12. Working / Intermediate Storage

Compute must introduce working storage explicitly.

This is different from durable Storage-module capacity.

Architecture:

```text
Storage module
    durable inputs
    durable outputs
    archive

Compute module
    temporary working storage
    sort temporary files
    workflow working directories
    intermediate files
    container/cache space

Transfer module
    transfer staging
```

Do not add temporary compute storage to the durable storage estimate.

---

# 13. Initial Working Storage Model

For V1, implement working storage conservatively as a configurable planning assumption.

At minimum support:

```text
scratch per worker
×
concurrent workers
=
simultaneous working storage
```

Example:

```text
250 GiB scratch/worker
×
20 workers
=
5,000 GiB simultaneous working storage
```

The default scratch-per-worker value must be labelled:

**Planning assumption**

until measured.

Do not imply that it is a measured BWA requirement.

Allow the user to edit it.

Later benchmarks can replace/refine this assumption.

---

# 14. Concurrency Model

The user should be able to specify worker concurrency.

For a per-sample stage:

```text
waves = ceil(samples / concurrent_workers)

stage_elapsed_time =
waves × runtime_per_sample
```

Also calculate:

```text
worker_hours =
samples × runtime_per_sample
```

These are different concepts.

Example using the measured alignment benchmark:

```text
500 samples

runtime:
4.945 h/sample

worker-hours:
~2472.5 worker-hours
```

If concurrency = 10:

```text
waves = 50

idealised elapsed time:
~247.25 h
≈ 10.3 days
```

If concurrency = 50:

```text
waves = 10

elapsed:
~49.45 h
≈ 2.06 days
```

Clearly label elapsed time as an idealised planning estimate.

It does not include:

- queue delay
- instance startup
- retries
- data staging
- interruptions
- contention
- workflow overhead
- cohort-level stages

unless those are explicitly modelled.

---

# 15. Initial Compute UI

The Compute page should become functional rather than remain a placeholder.

Suggested hierarchy:

## 01 Compute Planning

Short introduction.

Example:

> Estimate compute resources, working storage and processing time for the current project. Results combine measured benchmarks, published benchmarks and explicit planning assumptions.

### Project

Show inherited project information:

- project type
- sample count
- WGS profile

For current WGS mode:

```text
500 × 30× WGS
```

or equivalent based on Storage project state.

Do not duplicate all Storage controls unnecessarily.

### Workflow

Show:

```text
FASTQ
  ↓
BWA-MEM2
  ↓
CRAM
  ↓
DeepVariant
  ↓
gVCF
  ↓
GLnexus
  ↓
cohort VCF
```

Use restrained GRO styling.

Do not create an elaborate diagram if simple cards/arrows are clearer.

---

# 16. Workflow Stage Cards/Table

Show each stage with:

- stage
- scope
- CPU
- RAM
- runtime
- evidence
- status

For example:

| Stage | Scope | Resources | Runtime | Evidence |
|---|---|---|---|---|
| BWA-MEM2 + sort | per sample | 32 CPU / 160 GiB planning | 4.95 h | Measured — CBIO/Ilifu |
| CRAM index | per sample | lightweight | ~15 min measured | Measured — CBIO/Ilifu |
| DeepVariant | per sample | 96 vCPU / 384 GiB benchmark environment | 1h09 | Published benchmark |
| GLnexus | cohort | Under investigation | Not included | Benchmark pending |

Make clear where a resource value is a planning allocation rather than a measured requirement.

---

# 17. Compute Configuration

Initially expose editable controls for:

- concurrent alignment workers
- concurrent DeepVariant workers
- scratch GiB per worker
- optional runtime overrides

Runtime overrides should be clearly identified as user-supplied planning assumptions.

Do not silently overwrite benchmark evidence.

If the user overrides a benchmark:

display something like:

```text
Runtime used in calculation:
3.5 h/sample

Basis:
User override

Reference benchmark:
4.945 h/sample — Measured CBIO/Ilifu
```

---

# 18. Runtime Summary

Show at least:

### Alignment

- runtime/sample
- worker-hours
- concurrency
- idealised elapsed time

### DeepVariant

- benchmark runtime/sample
- worker-hours
- concurrency
- idealised elapsed time

### Cohort calling

- Under investigation / excluded

### Overall

Do not simply add stage elapsed times if workflow dependencies or incomplete stages make the result misleading.

For V1, it is acceptable to show:

**Estimated per-sample processing stages**

and:

**Known modelled elapsed time**

with a warning that GLnexus and workflow overhead are excluded.

---

# 19. Working Storage Summary

Show:

```text
Scratch / worker
Concurrent workers
Peak simultaneous scratch
```

Keep this separate from durable project storage.

Explain briefly:

> Working storage is temporary compute capacity and is not included in the durable Storage estimate.

---

# 20. AWS Execution Architecture

Introduce AWS as the first cloud execution target, but do not overstate precision.

Initial architecture recommendation:

```text
Amazon S3
    ↓
AWS Batch
    ↓
EC2 worker instances
    ↓
temporary working storage
    ↓
workflow outputs
    ↓
Amazon S3
```

Workflow orchestration may later use Nextflow.

AWS Batch itself does not add a separate service charge; users pay for the underlying resources it provisions.

Do not assume Slurm is required.

For embarrassingly parallel per-sample genomics stages, AWS Batch + EC2 is a valid initial architecture to investigate.

---

# 21. AWS Region

Use:

**Africa (Cape Town)**

Region code:

`af-south-1`

This keeps compute near the project's currently modelled AWS storage.

Do not silently move workloads to another region because it appears cheaper.

Cross-region transfer and governance implications would need separate modelling.

---

# 22. AWS Instance Selection

Do not hard-code a single instance as universally optimal.

The current AWS Cape Town region supports several relevant families, including compute- and memory-optimised families.

The model should eventually choose instances based on stage requirements.

For V1:

- represent AWS instance mapping as a planning recommendation
- preserve CPU/RAM requirements independently from the chosen instance
- keep instance type configurable
- store pricing separately from workflow benchmarks

Do not assume that 32 AWS vCPUs have the same performance as 32 physical Xeon Gold 6142 cores on Ilifu.

Any runtime translation is a planning assumption until benchmarked.

---

# 23. AWS Pricing

If current verified EC2 pricing is not available in the repository/configuration, do not invent it.

The Compute page may initially distinguish:

```text
Resource model     Implemented
Runtime model      Implemented
Working storage    Implemented
AWS architecture   Implemented
AWS price          Pending verified regional pricing
```

However, structure the calculation code so that verified EC2 pricing can be added without redesigning the Compute model.

Pricing metadata should eventually include:

```text
provider
region
instance type
purchase model
USD/hour
source
date verified
```

Support later:

- On-Demand
- Spot

but do not use an assumed Spot discount.

---

# 24. AWS Batch

Document:

AWS Batch itself has no additional service charge.

Underlying resources such as EC2 and storage are billed normally.

This should not be represented as a zero-cost compute environment.

Instead:

```text
AWS Batch orchestration fee: $0
EC2: priced separately
working storage: priced separately
data transfer: Transfer module
durable S3: Storage module
```

---

# 25. Spot vs On-Demand

Do not make Spot the default purely because it may be cheaper.

Long genomics jobs may be interrupted.

For V1:

On-Demand:

**baseline planning mode**

Spot:

**future/optional optimisation**

Later Spot modelling should consider:

- interruption tolerance
- retries
- checkpointing
- workflow resilience
- price variability

Do not assume a fixed Spot discount.

---

# 26. EBS / Working Storage

Prepare the model for temporary AWS working storage.

Likely initial technology:

**EBS gp3**

but keep the internal working-storage abstraction generic.

The model should eventually support:

- capacity
- lifetime
- IOPS
- throughput
- price

For V1, if verified `af-south-1` pricing is not available in configuration, show the capacity requirement but do not invent a cost.

Important:

EBS working storage is temporary compute infrastructure.

It must not be added to S3 durable storage capacity.

---

# 27. Sentieon

Prepare the compute architecture for a future Sentieon workflow alternative.

Known local figure:

**$1.50 per genome**

Classification:

**Local commercial assumption**

For 500 genomes:

```text
500 × $1.50 = $750
```

At the planner's existing illustrative FX rate of R16.05/USD:

```text
R12,037.50
```

This represents software licensing only.

It does not include:

- compute
- storage
- transfer
- engineering

Do not implement Sentieon runtime claims without a benchmark.

It is acceptable for Sentieon to remain:

**Planned / not included in current workflow**

in 011.

---

# 28. DRAGEN / Illumina ICA

Do not implement ICA/DRAGEN costing in this task.

Prepare the architecture so a later workflow option can represent:

```text
FASTQ
  ↓
ICA / DRAGEN
  ↓
CRAM
  ↓
gVCF
```

This is a future execution-provider/workflow alternative.

Mark:

**Planned**

Do not mix ICA iCredits into AWS EC2 compute totals.

---

# 29. Cost-efficient / Balanced / Fast

Do not yet present these as authoritative presets unless their resource and pricing behaviour is explicitly defined.

The underlying Compute model should nevertheless support later scenarios such as:

- Cost-efficient
- Balanced
- Fast

These will primarily vary:

- concurrency
- instance selection
- purchase model
- scratch capacity
- expected completion time

Do not assume that higher concurrency necessarily changes total compute cost linearly.

---

# 30. Calculation Basis / Evidence & Assumptions UI

Add a collapsed section near the Compute results:

**Calculation basis & evidence**

This should show concise provenance.

Example:

### Alignment runtime

4.945 h/sample

**Measured — CBIO/Ilifu**

NA12878, hg38, BWA-MEM2, 32-core Xeon Gold 6142 node.

### Alignment RAM

Measured peak:

116.7 GiB

Planning allocation:

160 GiB

**160 GiB is a Planning assumption.**

### DeepVariant

1h08m58s/sample

**Published benchmark**

DeepVariant v1.10, HG003, CPU-only, 96 vCPU / 384 GiB, mean of five runs.

### Scratch

250 GiB/worker

**Planning assumption**

No CBIO measured benchmark yet.

This section should make it easy for a technically informed user to challenge or replace assumptions.

---

# 31. Documentation

Update:

`docs/design-and-assumptions.md`

Document:

- Compute architecture
- WGS workflow
- evidence model
- NA12878 benchmark
- exact benchmark commands
- hardware
- input/output sizes
- measured runtime
- measured CPU utilisation
- measured RAM
- CRAM indexing benchmark
- limitations of single-sample benchmarking
- DeepVariant published benchmark
- GLnexus benchmark status
- working storage model
- concurrency formulas
- AWS Batch architecture
- AWS pricing status
- Sentieon local commercial assumption
- ICA/DRAGEN planned status

Use the existing status vocabulary:

- Implemented
- Planned
- Under investigation
- Out of scope

Use evidence classes:

- Measured
- Published benchmark
- Planning assumption
- Local commercial assumption

Do not turn the design document into a changelog.

---

# 32. Tests

Add deterministic tests for the compute model.

At minimum test:

## BWA benchmark calculations

Given:

```text
runtime = 4.945 h
samples = 500
```

approximately:

```text
worker-hours = 2472.5
```

## Concurrency

500 samples  
10 workers

```text
waves = 50
elapsed ≈ 247.25 h
```

500 samples  
50 workers

```text
waves = 10
elapsed ≈ 49.45 h
```

Use the exact stored benchmark runtime rather than rounded display values where possible.

## Scratch

250 GiB/worker  
20 workers

```text
5000 GiB
```

## Evidence

Verify that measured and planning values remain separately classified.

For example:

measured peak RAM:

**Measured — CBIO/Ilifu**

planning RAM:

**Planning assumption**

## Existing regression

All existing Storage tests must continue to pass.

The known 500 × 30× storage/transfer regression must remain unchanged:

```text
FASTQ       50,000 GB
CRAM        20,000 GB
gVCF/QC      5,000 GB
durable     75,000 GB

expected reads before contingency:
62,000 GB

with 20% transfer contingency:
74,400 GB

74,400 / 1024 =
72.65625 TB
```

Compute implementation must not alter these figures.

---

# 33. Exports

Extend project export data to include the Compute configuration and results where practical.

Include:

- workflow
- sample count
- compute stages
- runtime assumptions
- concurrency
- worker-hours
- idealised elapsed time
- scratch assumptions
- evidence classifications
- benchmark references
- excluded/unmodelled stages

Do not export unsupported costs as zero.

Use:

`null`, `not modelled`, or equivalent structured state.

---

# 34. Project Summary

Update Project Summary conservatively.

Add a Compute section when Compute has been configured.

Show:

- workflow
- known modelled runtime
- concurrency
- working storage requirement
- evidence status

If AWS compute pricing remains pending, show:

**Compute cost — not yet calculated**

rather than `$0`.

GLnexus should similarly be identified as excluded/pending.

Do not yet combine incomplete Compute figures into a misleading grand total.

---

# 35. UI Style

Use the existing GRO visual language.

Keep:

- navy
- teal
- dark blue-grey
- white/light backgrounds
- Aptos/Aptos Display where currently used
- restrained cards
- technical/document-like presentation

Avoid:

- colourful cloud-provider marketing styling
- excessive cards
- traffic-light colours
- decorative icons
- unnecessary charts

Prefer tables and concise metrics where they communicate the model more clearly.

---

# 36. Explicit Limitations

The UI and documentation should clearly communicate that:

1. The BWA-MEM2 benchmark is one measured NA12878 execution on Ilifu hardware.
2. Performance varies by sample, reference, software version, CPU architecture, storage and configuration.
3. AWS performance cannot be inferred exactly from Ilifu core counts.
4. DeepVariant numbers are published benchmarks from a different cloud/platform.
5. GLnexus is not yet included in total runtime.
6. Workflow overhead, failures, retries and queue delays are not yet modelled.
7. Working-storage defaults are planning assumptions until measured.
8. Cost estimates are infrastructure planning estimates, not procurement quotations.

---

# 37. Do Not Implement

Do not implement in 011:

- AI recommendations
- LLM integration
- Transfer page functionality
- detailed network modelling
- GLnexus invented benchmarks
- Sentieon runtime estimates
- ICA/DRAGEN costing
- Slurm deployment
- actual AWS provisioning
- Terraform
- AWS API calls
- live cloud execution
- workflow execution
- genomic data uploads
- participant/sample metadata
- compliance certification
- arbitrary Custom Compute workflow builder

These belong in later iterations.

---

# 38. Implementation Principle

The most important principle of this task is:

> A technically informed user must be able to understand how the planner arrived at a number and decide whether the underlying benchmark or assumption is appropriate for their project.

Prefer an incomplete but defensible calculation over a precise-looking unsupported estimate.

The Compute module should make uncertainty visible rather than hiding it.

---

# 39. Completion Report

After implementation:

1. list files created/modified;
2. describe the Compute model implemented;
3. list benchmarks and assumptions added;
4. identify which numbers are measured, published, planning assumptions or local commercial assumptions;
5. report tests run and results;
6. report any assumptions made during implementation;
7. list functionality deliberately left pending;
8. confirm that existing Storage calculations/regression tests remain unchanged;
9. confirm that `docs/design-and-assumptions.md` was reviewed and updated;
10. do not claim AWS pricing is implemented unless the prices and regional source metadata are actually verified.