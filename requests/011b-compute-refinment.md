# 011b — Compute Correctness and Closure

## Objective

Complete the final correctness and presentation work identified during the read-only review of the deployed Compute page after specification 011a.

This is a **small closure iteration** before beginning specification 012 Transfer.

The primary goals are:

1. correct effective-concurrency and working-storage calculations for small projects;
2. distinguish configured worker capacity from workers that can actually be active;
3. improve the responsive workflow diagram;
4. tighten AWS resource-model wording;
5. add traceable links to the workflow-accuracy evidence section where defensible sources already exist;
6. provide a small, honest Compute summary on Project Summary;
7. preserve all successful 011a behaviour.

Do not expand Compute into the deeper costing and comparison work reserved for a later iteration.

The guiding rule is:

> Capacity settings may exceed the number of samples, but calculations and labels must not imply that more sample workers are active than the project can use.

---

# 1. Preserve the 011a Architecture and Behaviour

Retain the current application structure:

```text
Storage
Compute
Transfer
Project Summary
```

Preserve:

- the minimum valid initial project state;
- direct `/compute` behaviour;
- shared session-level project state;
- the workflow versus execution-environment separation;
- Ilifu/HPC and AWS representation;
- the open-source BWA-MEM2 → DeepVariant workflow;
- Sentieon and DRAGEN/ICA as excluded alternatives;
- measured, published, planning and local-commercial evidence classes;
- explicit inclusion of CRAM-index runtime;
- sequential-stage runtime wording;
- GLnexus as visible but quantitatively unmodelled;
- working storage as temporary compute capacity, separate from durable Storage;
- user-editable concurrency, scratch and runtime assumptions;
- CSV, JSON and Markdown exports.

Do not reintroduce:

- the 500-sample example as the default project;
- internal specification references in user-facing text;
- unsupported AWS prices;
- unsupported HPC monetary costs;
- unsupported GLnexus figures;
- claims that planning allocations were measured requirements.

---

# 2. Correct Effective Concurrency

The deployed page allows configured concurrency to exceed the number of samples.

For example:

```text
samples                         1
configured alignment workers   10
configured DeepVariant workers 10
```

Only one per-sample task can actually run at once.

For every per-sample stage, calculate:

```text
effective_concurrency = min(sample_count, configured_concurrency)
```

Assume `sample_count >= 1` and `configured_concurrency >= 1` under the current minimum-valid-project model.

Examples:

| Samples | Configured workers | Effective concurrency |
|---:|---:|---:|
| 1 | 10 | 1 |
| 5 | 10 | 5 |
| 10 | 10 | 10 |
| 500 | 10 | 10 |
| 500 | 50 | 50 |

Do not silently rewrite the user's configured setting. A user may intentionally be describing available capacity.

Instead, retain both values in the calculation/result model:

```text
configured_concurrency
effective_concurrency
```

Use **effective concurrency** in calculations that depend on the number of simultaneously active sample workers.

---

# 3. Runtime Calculation

For each per-sample stage:

```text
effective_concurrency = min(samples, configured_concurrency)

waves = ceil(samples / effective_concurrency)

idealised_stage_elapsed = waves × runtime_per_sample

worker_hours = samples × runtime_per_sample
```

Using configured concurrency directly in the denominator happens to produce the same one-wave result when workers exceed samples, but the displayed concurrency must still reflect reality.

## Runtime UI

Replace an ambiguous field such as:

```text
Concurrency
10
```

with either:

```text
Active workers
1 of 10 configured
```

or two clearly labelled fields:

```text
Configured workers    10
Effective concurrency 1
```

Prefer the compact first form if space is limited.

Apply this separately to:

- alignment;
- CRAM indexing, which shares the alignment worker pool;
- DeepVariant.

Continue to describe the overall result as a:

> Sequential-stage planning estimate

Continue to state that pipelining and workflow overhead are not modelled.

---

# 4. Correct Stage-Specific Working Storage

The deployed minimum project currently shows:

```text
1 sample
10 configured workers
250 GiB scratch/worker
2,500 GiB stage peak
```

This overstates simultaneously required scratch for a one-sample project.

Calculate stage peaks using **effective concurrency**:

```text
alignment_effective_concurrency =
min(samples, configured_alignment_workers)

alignment_peak_scratch =
scratch_per_worker × alignment_effective_concurrency
```

and:

```text
deepvariant_effective_concurrency =
min(samples, configured_deepvariant_workers)

deepvariant_peak_scratch =
scratch_per_worker × deepvariant_effective_concurrency
```

Under the current sequential-stage model:

```text
peak_simultaneous_working_storage =
max(alignment_peak_scratch, deepvariant_peak_scratch)
```

Do not sum the two stage peaks unless the model is later changed to execute those stages concurrently.

## Required examples

### One-sample default project

```text
samples                         1
configured alignment workers   10
configured DeepVariant workers 10
scratch/worker                  250 GiB
```

Expected:

```text
alignment effective concurrency   1
DeepVariant effective concurrency 1
alignment peak                    250 GiB
DeepVariant peak                  250 GiB
workflow peak                     250 GiB
```

### Unequal stage settings

```text
samples                         20
configured alignment workers   2
configured DeepVariant workers 3
scratch/worker                  250 GiB
```

Expected:

```text
alignment peak    500 GiB
DeepVariant peak  750 GiB
workflow peak     750 GiB
```

### Capacity exceeds a small project

```text
samples                         2
configured alignment workers   10
configured DeepVariant workers 20
scratch/worker                  250 GiB
```

Expected:

```text
alignment peak    500 GiB
DeepVariant peak  500 GiB
workflow peak     500 GiB
```

## Working-storage UI

Continue to show:

- scratch per worker;
- alignment peak;
- DeepVariant peak;
- peak simultaneous working storage;
- the sequential-stage `max(...)` explanation.

Add concise effective-worker context to the stage peaks, for example:

```text
Alignment peak
250 GiB
1 active worker from 10 configured
```

The interface must still state that the shared scratch-per-worker value is a planning assumption, not a measured BWA-MEM2 or DeepVariant requirement.

---

# 5. CRAM Index Consistency

Preserve the 011a CRAM-index treatment:

```text
scope       per sample
resources   lightweight / shared worker
runtime     approximately 0.252 h/sample
evidence    Measured — CBIO/Ilifu
```

The CRAM-index stage must:

- remain included in the sequential-stage runtime total;
- share the alignment stage's configured and effective concurrency;
- remain a separate measured runtime contribution;
- not be called workflow overhead;
- not imply that it requires a dedicated 32-core worker.

Do not alter the measured benchmark value in this iteration.

---

# 6. Responsive Workflow Diagram

At the reviewed desktop viewport, `cohort VCF` wraps onto a second line and appears visually detached from GLnexus and its arrow.

Make the workflow readable at common desktop and tablet widths.

Preferred behaviour:

- keep the entire workflow on one line when sufficient width exists;
- when wrapping is required, wrap deliberately as meaningful rows rather than allowing only the final output card to drop below;
- retain visible directional continuity;
- avoid horizontal page overflow;
- preserve a sensible reading order for screen readers and narrow displays.

Acceptable implementations include:

- a responsive grid with explicit breakpoints;
- a horizontally scrollable workflow strip on narrow widths;
- a deliberate two-row layout with a clear continuation indicator.

Do not create a large or decorative workflow graphic. Keep the restrained GRO visual style.

Test at approximately:

```text
1280 × 720
1024 × 768
mobile/narrow width
```

---

# 7. Tighten AWS Status Wording

The AWS status table currently says:

```text
Resource model    Implemented
Runtime model     Implemented
```

This may imply that EC2 instance selection and AWS-specific performance modelling are complete.

Use more precise wording, for example:

| Component | Status |
|---|---|
| Workflow resource requirements | Implemented |
| Sequential runtime planning model | Implemented |
| Working-storage planning model | Implemented |
| AWS execution architecture | Implemented |
| EC2 instance mapping | Pending |
| AWS regional pricing | Pending verified `af-south-1` pricing |

Continue to warn that Ilifu and GCP benchmark performance cannot be assumed to reproduce exactly on AWS.

Do not select EC2 instance types or calculate AWS costs in 011b.

---

# 8. Workflow Accuracy Evidence and Links

Retain the careful 011a wording that:

- accuracy depends on sample, technology, coverage, truth set, reference and configuration;
- evidence categories are not scores;
- workflows are not ranked;
- no unsupported cross-study F1 comparison is made.

Where a defensible primary source has already been selected, make the evidence category link to that source.

Prefer primary sources such as:

- Genome in a Bottle/NIST;
- precisionFDA challenge material;
- official DeepVariant documentation or publications;
- official peer-reviewed or vendor methodology for Sentieon and DRAGEN.

Do not add a link merely to make every row clickable.

If an appropriate source has not been selected, show:

```text
Source selection pending
```

or retain the unlinked evidence category.

Do not copy marketing performance claims into the planner as though they were controlled comparisons.

The existing DeepVariant performance link should remain in the calculation/evidence details.

External evidence links should open normally and have descriptive link text rather than displaying a long raw URL where practical.

---

# 9. Project Summary Integration

The deployed Project Summary currently says:

> Visit the Compute page to configure and calculate Compute figures for this project. No compute cost or resource figures are shown here yet.

Replace this with a small Compute summary when valid Compute results exist in the current session.

At minimum show:

- selected workflow;
- sequential-stage planning estimate;
- configured alignment and DeepVariant workers;
- effective alignment and DeepVariant concurrency;
- peak simultaneous working storage;
- GLnexus excluded/pending status;
- compute cost status: not yet calculated;
- AWS regional pricing status: pending.

Example:

```text
Compute

Workflow
BWA-MEM2 + CRAM index + DeepVariant
GLnexus shown but excluded pending benchmark

Sequential-stage planning estimate
6.35 h

Worker capacity
Alignment: 1 active of 10 configured
DeepVariant: 1 active of 10 configured

Peak working storage
250 GiB

Compute cost
Not yet calculated — AWS regional pricing pending
```

If Compute has not yet produced valid session results, retain a clear prompt to visit Compute.

Do not invent a monetary total.

Do not add temporary working storage to durable Storage totals.

---

# 10. Sentieon Currency Context

Keep Sentieon outside the selected open-source workflow and outside all current runtime and cost totals.

Retain:

```text
US$1.50/genome
software licensing only
Local commercial assumption
```

When displaying the converted rand value, show the exchange-rate basis nearby or through concise help text, for example:

```text
Converted using the project's current USD/ZAR planning rate.
```

Do not change the rate source or broader currency model in 011b.

---

# 11. Exports

Update Compute exports so that they do not repeat the concurrency ambiguity.

Where concurrency is exported, include separate fields for:

```text
configured_alignment_workers
effective_alignment_concurrency
configured_deepvariant_workers
effective_deepvariant_concurrency
```

Include the corrected stage-specific scratch peaks and peak simultaneous working storage.

Preserve evidence classifications and exclusions.

Do not include GLnexus in runtime or cost totals.

---

# 12. Tests

Add or update deterministic tests for the calculation layer.

At minimum cover:

1. one sample with ten configured workers;
2. samples equal configured workers;
3. samples greater than configured workers;
4. unequal alignment and DeepVariant concurrency;
5. both configured concurrency values greater than sample count;
6. CRAM indexing sharing alignment concurrency;
7. peak workflow scratch using `max(...)`, not the sum;
8. worker-hours remaining independent of concurrency;
9. sequential elapsed including CRAM-index runtime;
10. GLnexus remaining excluded;
11. Project Summary receiving corrected effective concurrency and scratch values;
12. exports containing both configured and effective concurrency.

Retain the existing 500-sample regression coverage.

For the existing 500-sample, concurrency-10 scenario, the scratch result should remain unchanged if the scratch assumption is unchanged because:

```text
min(500, 10) = 10
```

---

# 13. Explicitly Out of Scope

Do not implement any of the following in 011b:

- verified EC2 pricing;
- EC2 instance-type selection;
- EBS pricing;
- Spot discounts;
- a full Ilifu/HPC monetary-cost model;
- Sentieon runtime/resource benchmarking;
- DRAGEN/ICA costing;
- a new DeepVariant benchmark;
- a GLnexus benchmark;
- measured per-stage scratch values;
- pipelined workflow scheduling;
- scheduler/startup/retry modelling;
- a workflow comparison engine;
- new accuracy scores or cross-workflow rankings;
- database persistence or user accounts;
- Transfer implementation.

These remain later Compute work after Transfer 012 unless separately specified.

---

# 14. Acceptance Criteria

Specification 011b is complete when:

1. direct `/compute` still opens successfully in the minimum project state;
2. a one-sample project with ten configured workers displays one effective worker per per-sample stage;
3. the same project with 250 GiB scratch/worker shows 250 GiB, not 2,500 GiB, as each stage peak and overall sequential peak;
4. unequal alignment and DeepVariant concurrency produces correct independent stage peaks;
5. configured worker capacity is preserved and visibly distinguished from effective concurrency;
6. CRAM indexing remains included and internally consistent;
7. worker-hours, waves and sequential elapsed remain correct;
8. the workflow diagram remains visually connected at the tested widths;
9. AWS wording does not imply EC2 mapping or pricing is complete;
10. accuracy evidence remains cautious and gains only defensible source links;
11. Project Summary shows the corrected Compute resource/runtime summary when available;
12. exports expose configured and effective concurrency separately;
13. no user-facing specification references appear;
14. no unsupported prices, benchmarks or performance claims are introduced;
15. the existing 500-sample regression scenario remains valid;
16. Storage calculations and durable-capacity totals are unchanged;
17. automated tests pass;
18. the deployed page passes a final read-only visual and functional review.

---

# 15. Completion Gate Before Transfer 012

After implementation and deployment:

1. open `/compute` directly in a fresh session;
2. verify the one-sample default calculation;
3. test unequal stage concurrency;
4. test a project where both worker settings exceed sample count;
5. confirm the corrected results in Project Summary and exports;
6. inspect the workflow at desktop, tablet and narrow widths;
7. verify evidence links and all exclusion wording;
8. confirm no Storage values changed;
9. run the full test suite;
10. perform a final read-only deployed review.

Once these checks pass, mark Compute 011b complete and proceed to specification 012 Transfer.
