# 012a — Project State, Guided Flow and Summary Integrity

## Objective

Correct the application-wide project-state and Project Summary problems discovered during the deployed end-to-end review after Transfer 012.

This is a **correctness and architecture iteration**, not a new feature expansion.

The deployed calculators themselves produced correct results when their state was coherent. The critical problem is that page-specific Streamlit widget state is currently being treated as persistent application state.

When users navigate between:

```text
Storage
Compute
Transfer
Project Summary
```

widget-associated values can disappear when their widgets are no longer rendered.

This causes:

- Storage inputs to reset;
- Compute inputs to reset;
- Transfer to crash on a missing session-state key;
- Project Summary to combine results produced from different project configurations;
- apparently authoritative results to be displayed even though their dependencies have changed.

The central architectural rule for this iteration is:

> Streamlit widgets are views onto project state. They are not the project state.

The application must maintain one durable session-level project model independently of page widget lifecycle.

The user should be able to move freely between Storage, Compute, Transfer and Project Summary without losing configuration or silently mixing results from different project states.

---

# 1. Preserve Existing Functional Models

Do not redesign the existing Storage, Compute or Transfer calculation models unless required to fix state handling.

Preserve:

## Storage

- WGS 30× and Custom Project modes;
- lifecycle/storage calculations;
- AWS pricing;
- transfer/egress planning assumption;
- engineering calculation;
- data-volume guidance;
- governance wording;
- exports.

## Compute

- workflow versus execution-environment distinction;
- BWA-MEM2;
- CRAM indexing;
- DeepVariant;
- GLnexus excluded/pending;
- configured versus effective concurrency;
- sequential-stage planning estimate;
- stage-specific scratch;
- Ilifu/HPC;
- AWS architecture;
- Sentieon/DRAGEN alternatives;
- evidence classifications;
- exports.

## Transfer

- endpoint model;
- WGS dataset presets;
- custom datasets;
- measured throughput;
- known-capacity + efficiency;
- unknown-throughput scenarios;
- transfer methods;
- RTT/BDP;
- provider-cost status;
- exports.

Do not introduce deeper Compute functionality in this iteration.

---

# 2. Reproduced Defects

The following deployed behaviour was observed and must be treated as regression cases.

A project was configured as:

```text
Project
Example WGS Project

Type
WGS 30×

Samples
500

Retention
5 years
```

Compute was configured as:

```text
Alignment workers
7

DeepVariant workers
13

Scratch
333 GiB/worker
```

Transfer was configured as:

```text
Dataset
FASTQ

Throughput mode
Measured

Measured throughput
777 Mbps
```

Before entering Project Summary the valid results were approximately:

## Storage

```text
Durable data
73.2 TB

Provisioned envelope
87.9 TB

Planned workflow egress
72.7 TB

Current included total
R693,613
```

## Compute

```text
Sequential-stage planning estimate
419.04 h

Alignment peak scratch
2,331 GiB

DeepVariant peak scratch
4,329 GiB

Peak simultaneous working storage
4,329 GiB
```

## Transfer

```text
FASTQ
48.83 TB

Measured throughput
777 Mbps

Estimated duration
153.5 h

Provider transfer charge
US$0 AWS ingress
```

The first Project Summary reproduced these values correctly.

After navigating:

```text
Project Summary → Storage
```

Storage widget values reset.

Observed resets included:

```text
Project name              blank
Samples                   1
Retention                 0.10 years
Transfer contingency      0%
Engineering hours/rate    zero
USD/ZAR                   0.01
VAT                       0%
```

The page then produced:

```text
Invalid input:
FASTQ: dataset size must be greater than zero
```

while another part of the application still identified the project as a 500-sample project.

This proves that project identity/configuration and page widget state are currently split.

---

# 3. Compute State-Loss Regression

The same project also lost Compute configuration after page navigation.

Observed reset:

```text
Alignment workers
7 → 1

DeepVariant workers
13 → 1

Scratch
333 GiB → 0 GiB
```

This caused the previously valid result:

```text
419.04 h
4,329 GiB peak scratch
```

to become approximately:

```text
3,173.42 h
0 GiB peak scratch
```

while the page header continued to describe the project as:

```text
500 × 30× WGS
```

This must not occur.

---

# 4. Transfer Missing-Key Crash

The following navigation sequence reproduced a Streamlit crash:

```text
Transfer
→
Project Summary
→
Transfer
```

The traceback showed direct access similar to:

```python
st.session_state["transfer_dataset_choice"]
```

when that widget-associated key no longer existed.

No page may assume that a Streamlit widget key is permanent application state.

Fix all similar patterns, not only this one line.

Audit Storage, Compute and Transfer for direct reliance on transient widget keys.

---

# 5. Mixed-Era Project Summary

The most serious correctness issue is that Project Summary can combine results from different project configurations.

Observed example:

```text
Storage
old valid 500-sample result

Compute
new reset 1-worker / 0-scratch result

Transfer
old 777 Mbps result
```

Project Summary therefore displayed internally incompatible results simultaneously.

This must never be presented as a coherent project estimate.

The Summary must know whether each module result was calculated from the current project/configuration state.

---

# 6. Canonical Project State

Introduce or formalise one durable session-level project model.

Conceptually:

```text
ProjectState
│
├── project
│   ├── name
│   ├── project_type
│   ├── sample_count
│   ├── retention_years
│   ├── currency
│   ├── vat
│   └── shared dataset assumptions
│
├── storage
│   ├── config
│   ├── result
│   └── status
│
├── compute
│   ├── config
│   ├── result
│   └── status
│
├── transfer
│   ├── config
│   ├── result
│   └── status
│
└── revision / dependency metadata
```

Exact Python structure is flexible.

Possible implementations include:

- dataclasses;
- typed dictionaries;
- Pydantic models if already appropriate;
- existing domain models extended cleanly.

Do not introduce a database.

Do not introduce user accounts.

The scope remains one Streamlit session.

---

# 7. Widgets Are Not Canonical State

Do not use page widget keys as the only stored value for project configuration.

For example, avoid architecture equivalent to:

```python
samples = st.number_input(
    "Samples",
    key="storage_samples"
)
```

where:

```text
storage_samples
```

is then treated as the persistent project value.

Instead, conceptually:

```text
ProjectState
    ↓
widget initial value
    ↓
user edits widget
    ↓
validated value
    ↓
ProjectState updated
```

If Streamlit removes the widget key because another page renders, the canonical project configuration must remain intact.

---

# 8. Widget Initialisation

When a page renders, initialise widgets from the canonical configuration.

Conceptually:

```python
if widget_key not in st.session_state:
    st.session_state[widget_key] = project_state.storage.config.some_value
```

or use another robust Streamlit-compatible pattern.

Do not initialise missing widget keys from arbitrary minimum values when a canonical project value already exists.

Minimum defaults should be used only when creating a genuinely new project/configuration.

---

# 9. Separate Shared Project Inputs From Module Inputs

Clearly identify inputs that belong to the overall project.

Examples:

```text
Project name
Project type
Sample count
Retention
USD/ZAR planning rate
VAT
```

and inputs that belong specifically to modules.

### Storage-specific

Examples:

```text
dataset sizes
headroom
archive class
active-storage period
transfer contingency
engineering assumptions
```

### Compute-specific

Examples:

```text
alignment concurrency
DeepVariant concurrency
scratch/worker
runtime overrides
execution environment
```

### Transfer-specific

Examples:

```text
dataset selection
source
destination
throughput mode
throughput
efficiency
transfer method
RTT
```

Do not create competing copies of shared project values in multiple modules.

---

# 10. One Project Identity

The application must never simultaneously display:

```text
Project header:
500 samples
```

while a page's underlying calculation uses:

```text
1 sample
```

Shared project identity must come from one canonical source.

If sample count changes, all modules must see the same new sample count.

---

# 11. Project Revision

Introduce a lightweight project revision or equivalent dependency mechanism.

For example:

```text
project_revision = 12
```

When a material upstream project input changes:

```text
project_revision += 1
```

Each module result records the revision/dependency state from which it was calculated.

Conceptually:

```text
StorageResult
calculated_for_revision = 12
```

This exact mechanism is not mandatory if a cleaner dependency-hash approach is used.

The requirement is:

> The application must be able to determine whether a stored result is valid for the current configuration.

---

# 12. Dependency-Aware Result Validity

Not every change invalidates every module.

Design dependencies explicitly.

For example:

## Sample count changes

Potentially invalidates:

```text
Storage
Compute
Transfer
Summary
```

## WGS file-size assumptions change

Potentially invalidates:

```text
Storage
Transfer
possibly Compute working assumptions where dependent
Summary
```

## Alignment worker count changes

Invalidates:

```text
Compute
Summary
```

but should not invalidate Storage.

## Transfer throughput changes

Invalidates:

```text
Transfer
Summary
```

but should not invalidate Storage or Compute.

## USD/ZAR changes

Invalidates financial results that use that exchange rate.

Do not simply invalidate everything on every widget change unless this is required as an initial conservative implementation.

A conservative broad invalidation model is acceptable initially if it is correct and clearly documented.

---

# 13. Module Status

Give each major module a state such as:

```text
Not configured
Complete
Needs review
Stale
Invalid
```

Exact labels may be simplified.

Recommended user-facing set:

```text
Not configured
Complete
Needs review
```

Use `Invalid` only where validation has failed.

Internally, more detailed states may exist.

---

# 14. Guided Flow

Introduce a guided project flow:

```text
1 Storage
    ↓
2 Compute
    ↓
3 Transfer
    ↓
4 Project Summary
```

This is guidance, not a rigid wizard.

Users must retain the ability to click the existing top navigation and move directly between modules.

Do not disable free navigation.

---

# 15. Save and Continue

Where appropriate, provide an action such as:

```text
Save and continue →
```

or:

```text
Continue to Compute →
```

At the end of Storage.

Similarly:

```text
Continue to Transfer →
```

at the end of Compute.

And:

```text
Review Project Summary →
```

at the end of Transfer.

The exact navigation implementation should follow supported Streamlit behaviour.

Do not create fragile custom routing.

---

# 16. Guided Progress Indicator

Provide a compact project-progress indicator where useful.

For example:

```text
1 Storage      Complete
2 Compute      Complete
3 Transfer     Needs review
4 Summary      Not ready
```

Keep this restrained.

Do not create a large wizard interface.

Do not use traffic-light colour semantics as the only status indicator.

Text labels must communicate state.

---

# 17. Upstream Changes and Downstream Review

If a user completes:

```text
500 samples
```

through all modules and later changes:

```text
500 → 1000 samples
```

the application must not continue presenting old 500-sample Compute and Transfer results as current.

Depending on implementation, either:

### Recalculate automatically

where the calculation is deterministic and all required configuration remains valid;

or:

### Mark downstream results

```text
Needs review
```

until the user revisits/recalculates them.

Prefer automatic recalculation only where it is clearly safe.

Do not silently reinterpret user choices.

---

# 18. Preserve Module Configuration When Stale

A stale result does not mean the user's configuration should be erased.

Example:

```text
Alignment workers
7

DeepVariant workers
13

Scratch
333 GiB
```

If sample count changes from 500 to 1000, preserve those settings.

Then recalculate or mark the Compute result as needing review.

Do not reset:

```text
7 → 1
13 → 1
333 → 0
```

---

# 19. Summary Must Use One Coherent Project State

Project Summary must never combine module results produced from incompatible project configurations.

Before displaying a result as current, verify its dependency/revision validity.

If a result is stale, display something such as:

```text
Compute
Needs review

Project inputs changed after this Compute estimate was calculated.
Review Compute before treating this result as current.
```

Do not silently show the stale number as authoritative.

---

# 20. Summary Readiness

Project Summary should distinguish between:

```text
Current
Needs review
Not configured
```

for Storage, Compute and Transfer.

At minimum, an authoritative project summary requires a valid current Storage result.

If Compute or Transfer is not configured, Summary may still display partial information, but clearly identify the missing sections.

Do not pretend a partial summary is complete.

---

# 21. Direct Summary Entry

Opening:

```text
/summary
```

directly in a fresh session must not present a normal-looking calculated project as though the user configured it.

Prefer wording such as:

```text
Project setup is not complete.

Start with Storage to configure the project.
```

If minimum defaults are intentionally used, say so explicitly.

Do not call default-derived values:

```text
last-computed
```

unless they were actually computed through a configured project workflow.

---

# 22. Project Summary Financial Completeness

The deployed internally consistent 500-sample example produced:

```text
Storage lifecycle             R442,264
Planned workflow egress       R179,349
Engineering                    R72,000
                              ─────────
Current included total        R693,613
```

Project Summary currently shows:

```text
Storage-related cost
R442,264

Engineering
R72,000
```

but does not prominently include:

```text
Planned workflow egress
R179,349
```

or:

```text
Current included total
R693,613
```

Correct this.

---

# 23. Summary Cost Structure

Present the financial section approximately as:

```text
Current included costs

Storage lifecycle             R442,264
Planned workflow egress       R179,349
Engineering                    R72,000
                              ─────────
Current included total        R693,613
```

Then separately:

```text
Not yet included

Compute infrastructure        Pending
Explicit transfer-plan cost   see Transfer
GLnexus                       Pending where relevant
```

Use actual calculated values.

Do not hard-code the example figures.

---

# 24. Distinguish Storage Workflow Egress From Transfer Plan

The existing Storage model contains a planned workflow-egress assumption.

The Transfer module models an explicit endpoint-to-endpoint transfer.

These may represent different movements.

For the reviewed example:

### Storage workflow egress

```text
Planned workflow reads
72.7 TB

Cost
R179,349
```

### Explicit Transfer plan

```text
Institutional/local storage
→
AWS S3

FASTQ
48.83 TB

AWS ingress charge
US$0
```

These are not the same transfer.

Do not replace one with the other.

Do not automatically add both to the same total unless cost ownership and duplication have been resolved.

---

# 25. Summary Cost Labelling

Use language such as:

```text
Current included total
```

rather than:

```text
Total project cost
```

while major cost categories remain unmodelled.

Explain what is included.

For example:

> Current included total covers modelled Storage lifecycle cost, planned workflow egress and engineering. Compute infrastructure and other pending components are not yet included.

This distinction is important.

---

# 26. Transfer Cost in Summary

If Transfer has a provider charge:

- show it in the Transfer section;
- explain whether it is included in the current project total.

For 012a, do not automatically merge explicit Transfer-plan charges into the existing Storage total unless deduplication is certain.

Prefer:

```text
Explicit transfer plan

Provider charge
US$0

Included in project total
No — shown separately
```

or equivalent.

This can be refined later when transfer-cost ownership moves out of Storage.

---

# 27. Compute Summary

Preserve the existing valid Compute summary.

For the reviewed example it should retain values such as:

```text
Alignment
7 active of 7 configured

DeepVariant
13 active of 13 configured

Sequential-stage planning estimate
419.04 h

Peak working storage
4,329 GiB
```

provided those results remain current for the project configuration.

If stale, do not display them as current without a warning.

---

# 28. Transfer Summary

Preserve valid Transfer summary values.

For the reviewed example:

```text
FASTQ
48.83 TB

Measured throughput
777 Mbps

Estimated duration
153.5 h

Provider charge
US$0
```

provided the result remains current.

If the project sample count or dataset definition changes, mark/recalculate appropriately.

---

# 29. Safe Session-State Access

Audit the application for direct indexing such as:

```python
st.session_state["some_widget_key"]
```

where the key may disappear when the widget is not rendered.

Use safe access/initialisation patterns.

Examples include:

```python
st.session_state.get(...)
```

with canonical-state fallback, or explicit widget initialisation.

Do not hide programming errors by blindly defaulting every missing key.

The fallback must come from the canonical configuration where one exists.

---

# 30. Avoid Incorrect Minimum Fallbacks

Do not use values such as:

```text
1 sample
0.10-year retention
0% contingency
0 engineering rate
0.01 USD/ZAR
0% VAT
0 GiB scratch
```

as fallback values for an already configured project.

Those are initial/minimum defaults only.

Once a user has configured a value, the canonical project model must preserve it.

---

# 31. Validation State

Invalid user input should not destroy the last valid configuration/result.

For example, if a user temporarily enters an invalid custom dataset size:

- show validation feedback;
- do not replace the entire project state with invalid zero values;
- preserve the last valid result where appropriate;
- mark it as needing review if necessary.

Avoid cascading invalid state across unrelated modules.

---

# 32. Project Reset

If the application already has a project reset mechanism, ensure it resets:

```text
canonical project state
module configs
module results
module statuses
widget state
```

coherently.

If no reset mechanism exists, do not add a large new feature solely for this iteration.

Do not confuse navigation with reset.

Moving between pages must never reset the project.

---

# 33. Exports

Exports should use canonical configuration/result state rather than transient widget keys.

Ensure exports remain stable after navigating away from and back to a module.

For example:

```text
Storage → Summary → Storage → export
```

must export the same configured Storage project unless the user changed it.

Likewise for Compute and Transfer.

---

# 34. Round-Trip Navigation Tests

Add regression coverage for page round trips.

At minimum test the logical state transitions corresponding to:

```text
Storage
→ Compute
→ Transfer
→ Summary
→ Storage
```

and verify that all configured values remain unchanged.

Then:

```text
Storage
→ Compute
→ Transfer
→ Summary
→ Compute
```

and:

```text
Storage
→ Compute
→ Transfer
→ Summary
→ Transfer
```

No module configuration may disappear.

---

# 35. 500-Sample End-to-End Regression

Create an end-to-end state regression based on the reviewed example.

Project:

```text
WGS 30×
500 samples
5 years
```

Compute:

```text
alignment workers
7

DeepVariant workers
13

scratch
333 GiB/worker
```

Transfer:

```text
FASTQ
measured throughput
777 Mbps
```

Verify the expected approximate outputs from the calculation layer:

## Storage

```text
durable data
73.2 TB

provisioned envelope
87.9 TB

planned workflow egress
72.7 TB
```

Use exact internal values in tests rather than rounded display values.

## Compute

```text
sequential estimate
~419.04 h

alignment peak
2331 GiB

DeepVariant peak
4329 GiB

overall peak
4329 GiB
```

## Transfer

```text
volume
48.828125 TB

throughput
777 Mbps

duration
~153.5 h
```

## Summary

Must reproduce the current values from all three modules from the same project revision.

---

# 36. Financial Regression

For the current 500-sample example under the current pricing/assumptions, verify approximately:

```text
Storage lifecycle
R442,264

Planned workflow egress
R179,349

Engineering
R72,000

Current included total
R693,613
```

Use exact underlying calculations in automated tests.

Do not hard-code rounded UI values as business logic.

---

# 37. Dependency Invalidation Tests

Test at least:

### Sample count

```text
500 → 1000
```

Storage/Compute/Transfer/Summary must no longer present the old 500-sample results as current.

### Compute concurrency

```text
7 → 20
```

Compute/Summary update or become Needs review.

Storage remains current.

### Transfer throughput

```text
777 → 500 Mbps
```

Transfer/Summary update or become Needs review.

Storage and Compute remain current.

### Currency

Changing USD/ZAR must invalidate/recalculate financial outputs that depend on it.

---

# 38. Direct Page Entry Tests

Test fresh-session entry to:

```text
/storage
/compute
/transfer
/summary
```

No page should crash.

No page should create contradictory project identities.

No page should silently replace a previously configured canonical value merely because its widget key is absent.

---

# 39. Full Navigation Regression

After all modules are configured, repeatedly navigate:

```text
Storage
Compute
Transfer
Summary
Storage
Transfer
Compute
Summary
```

Configuration and current results must remain stable.

This is a critical acceptance test.

---

# 40. Guided Flow Without Lock-In

The application should communicate the recommended sequence:

```text
Storage → Compute → Transfer → Summary
```

but advanced users must still be able to navigate directly.

The flow should feel like:

> a guided engineering planner

rather than:

> a rigid questionnaire.

---

# 41. Visual Treatment

Keep the existing GRO visual style.

Progress/status treatment should be:

- compact;
- technical;
- restrained;
- text-readable;
- consistent with existing section hierarchy.

Avoid:

- oversized stepper graphics;
- decorative icons;
- traffic-light-only statuses;
- modal-heavy workflows.

---

# 42. Documentation

Update:

```text
docs/design-and-assumptions.md
```

with:

- canonical project-state architecture;
- distinction between widget state and project state;
- shared versus module-specific inputs;
- module configuration/result separation;
- dependency validity;
- stale/needs-review behaviour;
- guided workflow;
- Summary readiness;
- financial-summary semantics;
- distinction between workflow egress and explicit Transfer plan;
- navigation persistence guarantees.

Do not turn the design document into a changelog.

---

# 43. Explicitly Out of Scope

Do not implement:

- database persistence;
- user accounts;
- saved projects across sessions;
- cloud project storage;
- browser local-storage persistence unless already part of the architecture;
- collaboration/multi-user editing;
- AWS EC2 pricing;
- AWS instance selection;
- deeper HPC costing;
- Sentieon benchmarking;
- DRAGEN/ICA costing;
- GLnexus benchmarking;
- new DeepVariant benchmarks;
- measured scratch benchmarking;
- workflow pipelining;
- transfer automation;
- Globus integration;
- actual genomic-data movement;
- AI/LLM recommendations.

These remain later work.

---

# 44. Acceptance Criteria

012a is complete when all of the following are true.

## Persistence

1. Storage inputs survive navigation to every other page and back.
2. Compute inputs survive navigation to every other page and back.
3. Transfer inputs survive navigation to every other page and back.
4. Project identity remains consistent across pages.
5. Missing Streamlit widget keys do not cause crashes.

## Summary integrity

6. Summary never silently combines results from incompatible project states.
7. Stale results are marked Needs review or recalculated safely.
8. Direct Summary entry does not imply that an unconfigured default project is authoritative.
9. Partial summaries clearly identify missing modules.

## Financial summary

10. Storage lifecycle cost is shown.
11. Planned workflow egress is shown.
12. Engineering is shown.
13. Current included total is shown.
14. Explicit Transfer-plan costs remain separately identified unless safe deduplication is established.
15. Compute infrastructure cost remains explicitly pending.

## Guided flow

16. The recommended sequence is visible:

```text
Storage → Compute → Transfer → Summary
```

17. Users retain free navigation.
18. Upstream changes correctly invalidate or recalculate dependent downstream results.

## Regression

19. The 500-sample end-to-end example remains internally consistent.
20. Storage calculations remain unchanged.
21. Compute calculations remain unchanged.
22. Transfer calculations remain unchanged.
23. Existing module tests pass.
24. New state/navigation tests pass.

---

# 45. Deployment Completion Gate

After implementation and deployment, perform a fresh read-only end-to-end review.

Configure:

```text
WGS 30×
500 samples
5 years
```

Then configure:

```text
Compute

Alignment workers
7

DeepVariant workers
13

Scratch
333 GiB
```

Then:

```text
Transfer

FASTQ
Measured throughput
777 Mbps
```

Record Storage, Compute and Transfer results.

Navigate:

```text
Storage
→ Compute
→ Transfer
→ Summary
→ Storage
→ Compute
→ Transfer
→ Summary
```

Verify:

- no input changes;
- no result changes;
- no crashes;
- no mixed-era results.

Then change:

```text
Samples
500 → 1000
```

Verify that dependent results are recalculated or clearly marked:

```text
Needs review
```

and that no old 500-sample result remains presented as current.

Then change only Compute concurrency and verify Storage remains current.

Then change only Transfer throughput and verify Storage and Compute remain current.

Inspect Summary after each change.

Finally:

- verify exports after round-trip navigation;
- verify direct `/summary` behaviour in a fresh session;
- run the complete automated test suite;
- confirm `docs/design-and-assumptions.md` reflects the implemented state architecture.

Only after these checks pass should 012a be considered complete.

---

# 46. Implementation Principle

The application now has multiple calculators, but the user is configuring **one project**.

Therefore the architecture should be:

```text
                 Project
                    │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
     Storage      Compute     Transfer
        │           │           │
        └───────────┼───────────┘
                    ▼
              Project Summary
```

not:

```text
Storage widgets
Compute widgets
Transfer widgets
      ↓
loosely combined Summary
```

A user should be able to think:

> I am editing my project.

not:

> I am filling in four unrelated forms.

That distinction should guide the implementation.

---

# 47. Completion Report

After implementation report:

1. files created/modified;
2. canonical project-state architecture;
3. how widget state is now separated from project state;
4. shared versus module-specific configuration;
5. result validity/stale mechanism;
6. dependency invalidation rules;
7. guided-flow implementation;
8. direct-page behaviour;
9. Transfer crash fix;
10. Summary integrity changes;
11. financial-summary changes;
12. export persistence;
13. navigation regression tests;
14. 500-sample regression results;
15. dependency-invalidation tests;
16. full automated test results;
17. documentation changes;
18. assumptions made;
19. functionality deliberately deferred.
