# 011a — Compute Refinement and Execution Model Cleanup

## Objective

Refine the Compute implementation introduced in specification 011 before moving on to the Transfer module.

This is primarily a **clarification, usability and architecture refinement**.

Do not substantially expand cloud costing or introduce new speculative benchmarks in this iteration.

The main goals are:

1. stop loading the application with the 500-sample example as though it were the user's project;
2. clarify measured values versus planning assumptions;
3. correct CRAM-index runtime/resource treatment;
4. improve working-storage/concurrency logic;
5. separate **workflow** from **execution environment**;
6. make HPC a first-class execution option alongside AWS;
7. clearly separate future Sentieon and DRAGEN/ICA alternatives;
8. remove internal specification references from the user-facing application;
9. improve wording around what is and is not currently modelled;
10. prepare for future workflow accuracy/performance evidence;
11. address the session-state issue when entering `/compute` directly;
12. retain GLnexus as an explicit but currently unmodelled cohort stage.

The guiding principle remains:

> A technically informed user should be able to understand what was measured, what was published, what was assumed, what is currently calculated, and what remains unknown.

Prefer an incomplete but defensible result over a precise-looking unsupported estimate.

---

# 1. Preserve Existing Architecture

Retain:

```text
Storage
Compute
Transfer
Project Summary
```

Keep the current:

- `st.navigation + st.Page` architecture;
- native top navigation;
- simplified CBIO header;
- GRO styling;
- Storage calculation model;
- Storage pricing;
- WGS30x model;
- Custom Project model;
- evidence/provenance architecture introduced in 011.

Do not revisit branding or navigation placement.

---

# 2. Remove the 500-Sample Example as the Default Project

The application currently opens with the example profile:

```text
Example WGS Project
WGS 30×
500 samples
5-year retention
```

This should not appear to be the user's project by default.

The 500 × 30× project is useful for demonstrations and regression testing, but it must be treated as an **example profile**, not the initial application state.

## Preferred behaviour

Start with either:

### Option A — minimum valid project

For example:

```text
Project type     WGS 30×
Samples          1
Retention        1 year
```

or similarly conservative minimum valid values.

This is preferred if blank state introduces unnecessary complexity.

### Option B — explicit unconfigured project

For example:

> Configure your project to begin.

Use this only if it fits cleanly with the existing shared project/session architecture.

Do not create unnecessary session-state complexity purely to achieve blank inputs.

## Example project

Provide a clear optional action such as:

```text
Load example: 500 × 30× WGS
```

or equivalent.

The existing 500-sample regression test must remain unchanged.

The example should remain available for:

- demonstrations;
- screenshots;
- testing;
- validation;
- reproducing documented calculations.

But it must not silently become the user's project.

---

# 3. Shared Project State Across Pages

Inspect the current session/project-state implementation.

During deployed testing, opening `/compute` directly could show:

> WGS 30x project required

even though Storage visually appeared to have WGS selected.

Navigating:

```text
Storage → Compute
```

within the same session correctly populated Compute.

This is confusing.

The application should have one coherent project state shared by:

```text
Storage
Compute
Transfer
Project Summary
```

Direct navigation to `/compute` should not produce a contradictory state.

If the project genuinely has not been configured, say so clearly.

For example:

> Configure a project in Storage before calculating Compute requirements.

Do not simultaneously render what looks like a configured WGS project while claiming no WGS project exists.

Avoid introducing database persistence or user accounts.

This remains session-level application state.

---

# 4. Workflow and Execution Environment Are Different Concepts

The current Compute page partially mixes:

- the biological/computational workflow;
- where the workflow executes.

Separate these concepts explicitly.

## Workflow

Example:

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

This describes **what processing occurs**.

## Execution environment

This describes **where/how it runs**.

The initial architecture should recognise:

```text
Ilifu / HPC
AWS
```

Future alternatives:

```text
Sentieon on HPC
DRAGEN / Illumina ICA
```

Do not treat Sentieon as though it were simply another AWS cost item.

Do not treat AWS as though it defines the workflow itself.

---

# 5. Execution Environment Section

Introduce a clearly labelled section such as:

## Execution environment

For this iteration, show at least:

### Ilifu / HPC

Status:

**Available planning reference**

Basis:

- measured BWA-MEM2 benchmark;
- institutional HPC execution;
- no direct infrastructure charge currently modelled.

Make clear:

> No HPC monetary cost is currently calculated. Resource and runtime planning can still be shown.

Do not imply HPC is free in an economic sense.

Simply state that institutional HPC charging/cost allocation is not currently modelled.

### AWS

Status:

**Architecture model implemented; pricing pending**

Architecture:

```text
Amazon S3
    ↓
AWS Batch
    ↓
EC2 workers
    ↓
temporary working storage
    ↓
outputs
    ↓
Amazon S3
```

Region:

```text
Africa (Cape Town)
af-south-1
```

Do not yet present unsupported EC2 cost estimates.

### Sentieon on HPC

Status:

**Planned**

Known local commercial assumption:

```text
US$1.50 / genome
```

Clearly label this as:

**software licence only**

and:

**Local commercial assumption**

Do not include it in the selected open-source workflow total.

### DRAGEN / Illumina ICA

Status:

**Planned**

Do not calculate costs in 011a.

---

# 6. Do Not Yet Build a Full Execution Comparison Engine

The architecture should prepare for a future comparison such as:

| Execution option | Workflow | Evidence | Cost | Completion time |
|---|---|---|---:|---:|
| Ilifu / HPC | BWA-MEM2 + DeepVariant | measured + published | not modelled | estimated |
| AWS | BWA-MEM2 + DeepVariant | planning model | pending | estimated |
| HPC + Sentieon | Sentieon | local commercial | future | future |
| ICA | DRAGEN | vendor evidence | future | future |

Do **not** fabricate the missing cells.

This table does not need to be implemented yet unless it naturally fits the existing UI.

The important requirement in 011a is that the internal architecture and user-facing terminology distinguish these options correctly.

---

# 7. BWA-MEM2 Evidence Clarification

The current workflow-stage row effectively shows:

```text
BWA-MEM2 + sort
32 CPU / 160 GiB
4.94 h
Measured — CBIO/Ilifu
```

This can incorrectly imply that all displayed resource values were measured.

They were not.

Measured:

```text
CPU allocation        32 physical cores
wall time             4:56:42
CPU utilisation       ~13.77 cores average
CPU consumption       ~68.1 core-hours
peak RAM              ~116.7 GiB
FASTQ input           ~97 GB
CRAM output           ~57 GB
```

Planning assumption:

```text
RAM allocation        160 GiB
```

The UI must make this distinction clear.

For example:

```text
BWA-MEM2 + sort

Planning allocation
32 CPU
160 GiB RAM

Measured benchmark
4.945 h/sample
116.7 GiB peak RAM

Evidence
Measured — CBIO/Ilifu
Planning RAM headroom — Planning assumption
```

Do not simply attach one evidence label to a mixture of measured and assumed values.

---

# 8. CRAM Indexing

The current stage displays approximately:

```text
CRAM index
per sample
resources not modelled
0.25 h
Measured — CBIO/Ilifu
Implemented
```

This wording should be improved.

We did measure the resource behaviour.

Measured CBIO/Ilifu benchmark:

```text
samtools index -@32 NA12878.cram

wall time           15:08.66
user CPU            170.09 s
system CPU           60.18 s
average CPU          25%
peak RAM             28,928 KB
exit                 0
```

The result demonstrates that CRAM indexing was lightweight in this benchmark despite requesting 32 threads.

Use wording such as:

```text
Planning resources:
Lightweight / shared worker

Runtime:
~0.25 h/sample

Evidence:
Measured — CBIO/Ilifu
```

Do not imply that a dedicated 32-core worker is required.

---

# 9. Include CRAM Index Runtime Properly

The deployed application currently:

- displays approximately 0.25 h/sample;
- excludes it from the runtime total;
- says it is folded into workflow overhead;
- while also stating that workflow overhead is excluded.

This is internally contradictory.

Correct it.

Because CRAM indexing has an actual measured runtime, it should either:

### Preferred

be included explicitly as a modelled stage;

or

### Alternative

be clearly excluded with a defensible reason.

Prefer explicit inclusion.

Do not call measured CRAM-index runtime “workflow overhead.”

Workflow overhead should instead mean things such as:

- scheduler delay;
- instance startup;
- retries;
- staging delay;
- orchestration overhead;
- interruptions;
- contention.

---

# 10. Runtime Model and Sequential Assumption

The current application calculates:

```text
Alignment elapsed
+
DeepVariant elapsed
=
Known modelled elapsed
```

For the 500-sample / concurrency-10 example:

```text
247.25 h
+
57.47 h
=
304.72 h
```

This assumes cohort-wide stages execute sequentially.

That is a useful conservative planning model, but it is not the only possible workflow execution model.

A real workflow may pipeline samples:

```text
Sample 1 alignment → DeepVariant
while
Sample 2 alignment continues
```

Do not implement a sophisticated pipeline scheduler in 011a.

Instead rename or qualify the result.

For example:

> **Sequential-stage planning estimate**

or:

> **Known modelled elapsed time — assumes cohort-wide stages execute sequentially**

Explain:

> Workflow pipelining may reduce elapsed time. Pipelining is not currently modelled.

This is preferable to presenting 304.72 h as though it were a predicted completion time.

---

# 11. Worker-Hours vs Elapsed Time

Continue to distinguish:

```text
worker-hours
```

from:

```text
idealised elapsed time
```

For example:

```text
500 × 4.945 h
=
2,472.5 alignment worker-hours
```

Concurrency changes elapsed time but does not automatically change the underlying worker-hours.

Do not describe worker-hours as CPU-hours.

For the BWA benchmark:

```text
measured CPU consumption
≈ 68.1 core-hours/sample
```

is a separate measurement from:

```text
worker runtime
≈ 4.945 h/sample
```

Preserve this distinction.

---

# 12. Working Storage / Scratch Concurrency

The deployed application currently shows:

```text
250 GiB scratch / worker
10 concurrent workers
2,500 GiB peak scratch
```

But the page exposes separate concurrency settings for:

- alignment workers;
- DeepVariant workers.

The UI does not explain which concurrency value drives the scratch calculation.

Correct this ambiguity.

## V1 preferred model

Working storage should be stage-specific where practical.

Conceptually:

```text
alignment scratch / worker
×
alignment concurrency
=
alignment peak scratch
```

and:

```text
DeepVariant scratch / worker
×
DeepVariant concurrency
=
DeepVariant peak scratch
```

If the same 250 GiB planning assumption is temporarily used for both stages, say so explicitly.

For sequential-stage execution:

```text
peak workflow scratch
=
max(
    alignment peak scratch,
    DeepVariant peak scratch
)
```

Do not add them unless the model explicitly allows both stages to run concurrently.

If pipelining is introduced later, simultaneous scratch requirements can be reconsidered.

---

# 13. Scratch Evidence

The current:

```text
250 GiB / worker
```

remains:

**Planning assumption**

No CBIO measurement currently supports it.

Keep it editable.

Show something like:

```text
Scratch per worker
250 GiB

Evidence
Planning assumption

Measured benchmark
Not yet available
```

Do not associate it with the measured BWA benchmark.

---

# 14. GLnexus

Keep GLnexus in the workflow.

It is biologically/computationally important because the workflow does not end with independent gVCFs.

Continue to show:

```text
GLnexus
cohort stage
Under investigation
```

Do not invent:

- CPU requirement;
- RAM requirement;
- runtime;
- worker count;
- AWS cost.

Make the workflow diagram visually distinguish modelled and unmodelled stages if this can be done simply.

For example:

```text
FASTQ
  ↓
BWA-MEM2        modelled
  ↓
CRAM
  ↓
DeepVariant     modelled
  ↓
gVCF
  ↓
GLnexus         benchmark pending
  ↓
cohort VCF
```

Do not allow GLnexus to disappear merely because it is not yet quantified.

We will return to GLnexus after the initial Transfer module unless suitable benchmark evidence is added earlier.

---

# 15. Sentieon Placement

The current Sentieon section appears within the Compute page even though the selected workflow is open source.

This can make Sentieon look like part of the active workflow.

Move/reframe it as an:

**Alternative workflow / execution option**

For example:

```text
Alternative execution options

Sentieon on HPC
Planned

Local licence assumption:
US$1.50/genome

Not included in current workflow or totals.
```

The existing calculation:

```text
500 genomes × US$1.50
=
US$750
```

may remain visible as an illustrative licence calculation if useful.

At:

```text
16.05 ZAR/USD
```

this gives:

```text
R12,037.50
```

But make clear that this is:

- licence only;
- not compute;
- not storage;
- not transfer;
- not engineering;
- not included in current project total.

---

# 16. AWS Batch Wording

Retain the factual architecture:

```text
AWS Batch orchestration fee: $0
```

but reduce its visual prominence.

The important future cost components are:

```text
EC2 worker compute
working storage
durable S3 storage
data transfer
software/licensing where applicable
```

Use wording such as:

> AWS Batch does not add a separate service charge. The EC2 and storage resources used by the workflow remain billable.

Keep:

```text
On-Demand
```

as the baseline purchase model.

Keep:

```text
Spot
```

as:

**future / optional optimisation**

Do not assume a fixed Spot discount.

Do not yet implement detailed AWS pricing in 011a.

---

# 17. AWS Pricing Status

Continue to display:

```text
AWS pricing
Pending verified regional pricing
```

until actual:

```text
af-south-1
```

pricing is verified and stored with provenance.

Future pricing metadata should include:

```text
provider
region
instance type
purchase model
USD/hour
source
date verified
```

Do not invent AWS prices to complete the UI.

---

# 18. HPC as a First-Class Option

Ilifu/HPC should not appear only as the source of the BWA benchmark.

Make it conceptually clear that:

```text
Ilifu / institutional HPC
```

is itself an execution environment.

Current state:

### Runtime evidence

Partially available.

BWA-MEM2:

**Measured — CBIO/Ilifu**

DeepVariant:

**Published benchmark only**

GLnexus:

**Under investigation**

### Monetary cost

**Not currently modelled**

### Working storage

Planning model available.

### Scheduling

Not currently modelled.

Do not invent:

- Ilifu CPU-hour rates;
- queue times;
- fair-share performance;
- internal institutional charges.

---

# 19. Remove Internal Specification References From User UI

Remove user-facing references such as:

```text
spec 011
spec 011 §13
§13
```

or similar implementation references.

These are useful during development but should not appear in the finished planner interface.

Replace them with user-oriented provenance.

For example:

Instead of:

```text
Scratch assumption (spec 011 §13)
```

use:

```text
Scratch assumption
Planning assumption
```

or:

```text
Why this value?
```

Internal design documentation may continue to reference numbered specifications where useful.

The normal user should not need to understand the implementation history.

---

# 20. Accuracy / Performance Evidence

Prepare the Compute model/UI for future workflow accuracy evidence.

Do **not** create a simplistic ranking such as:

```text
DeepVariant   99.9%
GATK          99.6%
DRAGEN        99.8%
```

unless all values come from a genuinely comparable benchmark.

Accuracy depends on:

- truth set;
- sample;
- sequencing technology;
- coverage;
- reference;
- confident regions;
- software version;
- pipeline configuration;
- SNP vs INDEL evaluation;
- evaluation methodology.

---

# 21. BWA-MEM2 Is Not a Variant Caller

Do not present BWA-MEM2 as though it has an independent variant-calling F1 score.

BWA-MEM2 is an aligner.

Accuracy evidence should compare complete or appropriately defined workflows, for example:

```text
BWA-MEM2 → DeepVariant
BWA-MEM2 → GATK HaplotypeCaller
DRAGEN pipeline
Sentieon pipeline
```

Where possible, comparisons should use:

- the same GIAB truth sample;
- the same truth-set version;
- the same confident regions;
- the same sequencing technology;
- the same coverage;
- the same evaluation methodology.

---

# 22. Accuracy Evidence Sources

Prepare for links/references to reputable benchmark sources.

Useful evidence categories include:

### Genome in a Bottle / hap.py

Preferred basis for truth-set evaluation where applicable.

### DeepVariant published metrics

DeepVariant publishes precision/recall/F1 benchmark results together with runtime metrics.

### precisionFDA challenges

Useful independent benchmark context for comparing variant-calling pipelines.

### Vendor benchmarks

May be included, but clearly label them as vendor-published evidence.

Do not present vendor benchmarks as independent evidence.

---

# 23. Initial Accuracy UI

Do not build a large accuracy-comparison system in 011a.

A small information section is sufficient.

For example:

## Workflow accuracy evidence

> Variant-calling accuracy depends on the sample, sequencing technology, coverage, truth set, reference and software configuration. Where possible, workflows should be evaluated against an appropriate Genome in a Bottle truth set using a consistent evaluation methodology.

Then optionally expose references such as:

```text
DeepVariant
Published GIAB / hap.py accuracy metrics

GATK
GIAB / precisionFDA benchmark evidence

DRAGEN
GIAB / precisionFDA benchmark evidence

Sentieon
GIAB / precisionFDA benchmark evidence
```

Do not assign a winner.

Do not rank workflows.

Do not mix incompatible F1 scores into one comparison table.

A controlled accuracy comparison can be added later when we identify an appropriate common benchmark.

---

# 24. Storage Wording About Compute

Review wording in Storage that currently implies:

> Compute is not yet included.

Compute resource/runtime planning is now implemented.

What is not yet implemented is **complete compute costing**.

Update wording accordingly.

Prefer:

> Compute runtime and resource planning are available. Compute infrastructure cost is not yet included in the project total.

or equivalent.

Do not imply that the entire Compute module remains a placeholder.

---

# 25. Project Summary

Update Project Summary to reflect the refined terminology.

It should distinguish:

### Workflow

Example:

```text
BWA-MEM2 → DeepVariant → GLnexus
```

with GLnexus identified as unmodelled where appropriate.

### Execution environment

Example:

```text
Ilifu / HPC
```

or:

```text
AWS
```

depending on current selection/model state.

### Runtime

Use:

```text
Sequential-stage planning estimate
```

rather than presenting the current elapsed value as an unconditional completion prediction.

### Working storage

Show the correct stage-specific or peak scratch model.

### Cost

If unavailable:

```text
Compute infrastructure cost
Not yet calculated
```

Do not use zero.

### Evidence

Summarise:

- measured;
- published;
- planning assumptions;
- excluded/unmodelled stages.

---

# 26. Export

Update Compute export fields to match the refined model.

Where practical include:

```text
workflow
execution_environment
sample_count
alignment_runtime
alignment_runtime_evidence
alignment_measured_peak_ram
alignment_planning_ram
alignment_concurrency
deepvariant_runtime
deepvariant_runtime_evidence
deepvariant_concurrency
cram_index_runtime
cram_index_evidence
scratch_per_worker
scratch_evidence
peak_working_storage
elapsed_time_model
glnexus_status
compute_cost_status
```

Do not expose internal specification numbers as meaningful provenance.

Use human-readable evidence classifications instead.

---

# 27. Documentation

Update:

```text
docs/design-and-assumptions.md
```

to reflect the refined architecture.

Document the distinction between:

```text
workflow
execution environment
benchmark
planning assumption
pricing
```

Document the current execution options:

```text
Ilifu / HPC
AWS
Sentieon on HPC — planned
DRAGEN / ICA — planned
```

Document:

- CRAM-index treatment;
- stage-specific scratch logic;
- sequential-stage elapsed-time assumption;
- future pipelining consideration;
- GLnexus status;
- accuracy evidence principles;
- removal of specification references from user-facing UI;
- minimum/empty project startup behaviour.

Do not turn the document into a chronological changelog.

---

# 28. Tests

Add/update deterministic tests.

## Initial project state

Verify that the application does not silently initialise to:

```text
500 samples
5 years
```

unless the example profile is explicitly loaded.

## Example profile

Verify that loading:

```text
500 × 30× WGS
```

still produces the established regression values.

## BWA evidence

Verify:

```text
measured peak RAM
=
Measured — CBIO/Ilifu
```

and:

```text
160 GiB planning RAM
=
Planning assumption
```

These must remain distinct.

## CRAM index

Verify the measured runtime is represented correctly.

If included in runtime calculations, test the exact inclusion logic.

## Scratch

If:

```text
alignment concurrency = 10
alignment scratch = 250 GiB
```

then:

```text
alignment peak scratch = 2500 GiB
```

If:

```text
DeepVariant concurrency = 20
DeepVariant scratch = 250 GiB
```

then:

```text
DeepVariant peak scratch = 5000 GiB
```

For sequential-stage execution:

```text
peak workflow scratch
=
max(2500, 5000)
=
5000 GiB
```

Do not sum to 7500 GiB unless stages are explicitly modelled as concurrent.

## Runtime

Preserve deterministic worker-hour calculations.

Make clear whether CRAM indexing is included.

## Existing Storage regression

The established 500 × 30× regression must remain unchanged:

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

---

# 29. Explicit Limitations

Retain and refine limitations.

At minimum communicate:

1. BWA-MEM2 performance is based on one measured NA12878 run on Ilifu.
2. The 160 GiB alignment RAM allocation is a planning assumption; measured peak was approximately 116.7 GiB.
3. DeepVariant runtime is a published benchmark from a different compute environment.
4. AWS performance cannot be inferred directly from Ilifu core counts.
5. GLnexus is not yet quantitatively modelled.
6. Current elapsed time assumes sequential cohort-wide stages.
7. Workflow pipelining is not currently modelled.
8. Queue delay, retries, startup and staging overhead are not currently modelled.
9. Scratch requirements remain planning assumptions.
10. AWS compute pricing is not yet implemented.
11. HPC monetary cost is not currently modelled.
12. Accuracy varies by dataset, truth set and pipeline configuration.

---

# 30. Do Not Implement in 011a

Do not implement:

- detailed AWS EC2 pricing;
- live AWS pricing APIs;
- Spot pricing estimates;
- AWS provisioning;
- Terraform;
- Slurm deployment;
- HPC accounting rates;
- GLnexus invented runtime;
- GLnexus invented resource requirements;
- workflow pipelining scheduler;
- Sentieon runtime estimates;
- Sentieon compute cost;
- DRAGEN/ICA costing;
- arbitrary Custom Compute workflow builder;
- AI recommendations;
- LLM integration;
- Transfer functionality;
- a workflow accuracy ranking;
- unsupported F1 comparisons.

These belong in later iterations.

---

# 31. Next Development Sequence

After this refinement, the intended sequence is approximately:

```text
011   Initial Compute model                    DONE
011a  Compute refinement                       CURRENT

012   Transfer model

013   Compute costing and alternatives
      - verified AWS Cape Town pricing
      - AWS instance mapping
      - working-storage pricing
      - HPC execution model refinement
      - Sentieon alternative
      - GLnexus benchmark if available
      - DRAGEN / ICA alternative
      - controlled accuracy/performance evidence
```

Do not implement 012 or 013 as part of this task.

---

# 32. Implementation Principle

The planner should increasingly answer four separate questions:

```text
1. What data do I need to store?
       Storage

2. What processing do I need to perform?
       Workflow

3. Where/how should that processing run?
       Execution environment

4. How does the data move between locations?
       Transfer
```

These concepts should remain distinct even when they interact.

The eventual Project Summary can then combine them into one infrastructure plan.

---

# 33. Completion Report

After implementation:

1. list files created/modified;
2. describe the initial-project-state change;
3. describe how shared project/session state was handled;
4. describe the workflow vs execution-environment separation;
5. describe the CRAM-index correction;
6. describe the revised runtime wording/calculation;
7. describe the stage-specific scratch model;
8. describe how HPC and AWS are now represented;
9. describe how Sentieon and DRAGEN/ICA are separated as future alternatives;
10. confirm internal specification references were removed from user-facing UI;
11. describe any accuracy-evidence UI added;
12. report tests run and results;
13. confirm existing Storage calculations remain unchanged;
14. confirm the 500 × 30× regression remains unchanged;
15. confirm `docs/design-and-assumptions.md` was reviewed and updated;
16. list functionality deliberately left for 012/013;
17. report any assumptions made during implementation.