# 012c — Project Flow and State Closure

## Objective

Complete the remaining project-state, Transfer persistence and guided-flow issues identified during the deployed review after 012a.

This is a **small correctness and UX closure iteration**.

Do not redesign the project-state architecture.

The deployed application already demonstrates that the core architecture is substantially working:

- Storage configuration persists across page navigation;
- Compute configuration persists across page navigation;
- project identity remains consistent;
- upstream project changes invalidate dependent downstream results;
- module-specific changes do not unnecessarily invalidate unrelated modules;
- Project Summary no longer silently combines stale results;
- the previous Transfer missing-key crash is fixed;
- Summary financial structure now distinguishes included and excluded costs.

The remaining issues are:

1. Transfer widget configuration is not fully persistent.
2. Transfer status can disagree with Transfer result validity.
3. Summary incorrectly describes configured projects as the minimum/default project.
4. Guided workflow/status UI is incomplete.
5. The implemented Summary route is `/project-summary`, not `/summary`; tests/docs should reflect reality.

The purpose of 012c is to close these issues without expanding functionality.

---

# 1. Preserve the Existing Architecture

Preserve the canonical project-state architecture introduced in 012a.

The application remains:

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

Continue to treat:

> Streamlit widgets as views onto project state, not as project state itself.

Do not revert to widget-key-driven application state.

---

# 2. Preserve Confirmed Working Behaviour

Do not regress the following behaviour verified in the deployed application.

## Storage persistence

A configured project such as:

```text
Project name
Example WGS Project

Samples
500

Retention
5 years
```

must survive navigation through all pages and back to Storage.

This includes all Storage configuration such as:

- project name;
- sample count;
- retention;
- dataset assumptions;
- transfer contingency;
- engineering assumptions;
- USD/ZAR planning rate;
- VAT;
- lifecycle configuration.

---

# 3. Preserve Compute Persistence

The reviewed Compute configuration:

```text
Alignment workers
7

DeepVariant workers
13

Scratch
333 GiB/worker
```

survived navigation and reproduced:

```text
Sequential-stage planning estimate
419.04 h

Alignment peak
2,331 GiB

DeepVariant / overall peak
4,329 GiB
```

for the reviewed 500-sample project.

Preserve this behaviour.

Do not change Compute calculation logic.

---

# 4. Preserve Dependency Invalidation

The deployed application correctly handled:

```text
Samples
500 → 1000
```

by:

- recalculating Storage;
- marking Compute as Needs review;
- marking Transfer as Needs review;
- removing old downstream results from Summary.

Preserve this.

The application also correctly handled a Compute-only change without invalidating Storage.

Preserve this dependency behaviour.

---

# 5. Transfer Persistence Is the Primary Correctness Fix

The remaining major state defect is Transfer configuration persistence.

Observed configuration:

```text
Dataset
FASTQ

Throughput mode
Measured throughput

Measured throughput
777 Mbps
```

initially produced:

```text
Transfer volume
48.83 TB

Estimated duration
153.5 h

AWS ingress
US$0
```

After navigating away from Transfer and returning:

```text
Throughput mode
Measured throughput
```

was preserved, but:

```text
Measured throughput
777 → 0.00
```

The page then reported:

```text
Invalid input:
Measured throughput must be greater than zero.
```

This must be fixed.

---

# 6. Transfer Configuration Must Be Canonical

All Transfer configuration must live in the durable Transfer configuration model.

Do not persist only the currently observed problematic throughput value.

Audit and persist all Transfer inputs, including where applicable:

```text
dataset selection
custom dataset name
custom dataset size
custom dataset unit

source endpoint
custom source name
source location

destination endpoint
custom destination name
destination location

throughput mode

measured throughput

known link capacity
link-capacity unit
planning efficiency

transfer method

RTT

any other user-editable Transfer assumptions
```

The exact current field set should be taken from the implementation.

Do not add new Transfer features.

---

# 7. Transfer Widgets Must Rehydrate From Canonical State

When Transfer is rendered, each widget must initialise from the canonical Transfer configuration.

Conceptually:

```text
canonical Transfer config
        ↓
Transfer widgets
        ↓
user edit
        ↓
validation
        ↓
canonical Transfer config
```

If Streamlit removes a widget-associated session key while the page is not rendered, returning to Transfer must recreate the widget from canonical configuration.

It must not recreate it from:

```text
0
minimum
blank
first option
```

unless that genuinely is the canonical value.

---

# 8. Transfer Round-Trip Regression

The following must work exactly.

Configure:

```text
WGS 30×
500 samples
5 years
```

Transfer:

```text
Dataset
FASTQ

Throughput mode
Measured throughput

Measured throughput
777 Mbps
```

Navigate:

```text
Transfer
→ Project Summary
→ Storage
→ Compute
→ Transfer
```

Expected on return:

```text
Dataset
FASTQ

Throughput mode
Measured throughput

Measured throughput
777 Mbps
```

and the Transfer result must again be approximately:

```text
Volume
48.83 TB

Estimated duration
153.5 h

Provider charge
US$0
```

Use exact calculation-layer values in automated tests.

---

# 9. Audit All Transfer Modes

Do not test only Measured throughput.

Perform round-trip persistence tests for:

## Measured throughput

For example:

```text
777 Mbps
```

## Known link capacity

Use distinctive values such as:

```text
Link capacity
2.5 Gbps

Planning efficiency
63%
```

Verify both survive page navigation.

## Unknown throughput

Verify that the selected throughput mode survives navigation and scenario behaviour remains unchanged.

---

# 10. Audit Optional Transfer Fields

Where supported, populate distinctive values for:

```text
source
destination
source location
destination location
transfer method
RTT
```

Navigate away and back.

Every field must survive.

Do not allow optional fields to reset simply because their widgets were not rendered on another page.

---

# 11. Transfer Status Must Reflect Current Validity

The deployed review observed a contradiction:

```text
Transfer result
missing / invalid
```

while progress still displayed:

```text
Transfer
Complete
```

This must not occur.

A module may be labelled:

```text
Complete
```

only if it has a valid result for its current configuration and current project dependencies.

---

# 12. Transfer Status Rules

At minimum:

### Not configured

Use when Transfer has not yet been configured.

### Complete

Use only when:

- Transfer configuration is valid;
- Transfer calculation succeeded;
- result corresponds to current project dependencies.

### Needs review

Use when:

- upstream dependencies changed;
- previous Transfer configuration remains available;
- result is stale or requires recalculation/review.

### Invalid

May be used internally or visibly where appropriate when current Transfer inputs fail validation.

Do not display:

```text
Complete
```

for an invalid or missing current result.

---

# 13. Status Must Be Derived From Canonical State

Do not treat:

```text
user previously visited Transfer
```

or:

```text
Transfer was once successfully calculated
```

as equivalent to:

```text
Transfer is currently Complete
```

Status must reflect current configuration/result validity.

---

# 14. Fix Default-Project Detection

The deployed Summary incorrectly displayed wording equivalent to:

```text
Showing the minimum default project
```

and:

```text
This project has not been configured yet
```

even after the user had configured valid:

```text
500-sample
```

and:

```text
1000-sample
```

projects.

Fix this.

---

# 15. Explicit Project Configuration State

Do not infer whether the project is configured solely by checking whether values differ from defaults.

A valid user-configured project may legitimately use default values.

Prefer explicit project state such as:

```text
project_configured = True
```

or an equivalent lifecycle/status mechanism.

Set it when the user has intentionally established a valid project configuration.

Exact implementation is flexible.

---

# 16. Default Project Behaviour

A genuinely fresh session may begin with the existing minimum planning project.

For example:

```text
WGS 30×
1 sample
```

That is acceptable.

But distinguish:

```text
minimum initial/default state
```

from:

```text
user-configured project that happens to contain the same values
```

Do not call a configured project unconfigured simply because its values match defaults.

---

# 17. Summary Default-State Wording

In a fresh session, Summary may say something like:

```text
Project setup has not been completed yet.

Start with Storage to configure the project.
```

or equivalent.

Once the project has been configured, remove this message.

For a configured 500-sample project, Summary must not display any wording suggesting:

```text
minimum default project
```

or:

```text
project has not been configured
```

---

# 18. Guided Workflow

Complete the guided workflow originally intended in 012a.

The recommended project sequence is:

```text
1 Storage
    ↓
2 Compute
    ↓
3 Transfer
    ↓
4 Project Summary
```

This remains guidance, not a locked wizard.

---

# 19. Free Navigation Must Remain

Preserve the existing top navigation:

```text
Storage
Compute
Transfer
Project Summary
```

Users may jump directly between pages.

Do not disable pages.

Do not require users to click Next before another page becomes available.

The planner is an engineering tool, not a questionnaire.

---

# 20. Per-Page Progress Treatment

Add a compact progress/status treatment on the main project pages.

For example:

```text
Storage       Complete
Compute       Complete
Transfer      Needs review
Summary       Not ready
```

or a restrained equivalent.

The exact visual implementation is flexible.

Requirements:

- use text labels;
- keep it compact;
- use existing GRO styling;
- do not rely only on colour;
- do not create a large wizard component;
- do not duplicate the native navigation unnecessarily.

---

# 21. Page-Level Continue Actions

Add a simple forward action where appropriate.

At the end of Storage:

```text
Continue to Compute →
```

At the end of Compute:

```text
Continue to Transfer →
```

At the end of Transfer:

```text
Review Project Summary →
```

These are convenience actions.

They must not be required for state persistence.

Using top navigation must behave identically.

---

# 22. Summary Status

Project Summary should provide a compact view of module readiness.

For example:

```text
Storage       Complete
Compute       Complete
Transfer      Complete
```

If an upstream change invalidates downstream modules:

```text
Storage       Complete
Compute       Needs review
Transfer      Needs review
```

Summary must then clearly indicate that the overall project estimate is partial.

---

# 23. Summary Financial Structure

Preserve the corrected financial Summary.

For the reviewed 500-sample example, this included approximately:

```text
Storage lifecycle             R442,264
Planned workflow egress       R179,349
Engineering                    R72,000
                              ─────────
Current included total        R693,613
```

Do not change the underlying Storage calculations.

Use exact calculated values.

---

# 24. Preserve Transfer Cost Separation

The explicit Transfer plan remains separate from the Storage workflow-egress assumption.

For the reviewed example:

```text
Institutional/local storage
→ AWS S3
```

was AWS ingress and showed:

```text
Provider charge
US$0
```

This must remain separately identified.

Do not double-count it in:

```text
Current included total
```

unless future cost ownership is explicitly redesigned.

That redesign is out of scope for 012c.

---

# 25. Summary Route

The implemented Streamlit route is:

```text
/project-summary
```

not:

```text
/summary
```

Treat `/project-summary` as canonical.

Do not redesign routing solely to support `/summary`.

Update:

- tests;
- documentation;
- internal references;

to use:

```text
/project-summary
```

where a route is required.

---

# 26. Direct Project Summary Entry

Opening:

```text
/project-summary
```

in a fresh session must not crash.

The current deployed behaviour of opening a valid minimum project is acceptable provided the UI clearly identifies that project setup has not yet been completed.

Once the project is configured, that default-state wording must disappear.

---

# 27. Preserve 500-Sample Regression

Retain the existing end-to-end regression.

Project:

```text
WGS 30×
500 samples
5 years
```

Storage approximately:

```text
Durable data
73.2 TB

Provisioned envelope
87.9 TB

Workflow egress
72.7 TB

Current included total
R693,613
```

Compute:

```text
Alignment workers
7

DeepVariant workers
13

Scratch
333 GiB/worker

Sequential estimate
419.04 h

Alignment peak
2,331 GiB

DeepVariant / overall peak
4,329 GiB
```

Transfer:

```text
FASTQ
48.83 TB

Measured throughput
777 Mbps

Estimated duration
153.5 h

AWS ingress
US$0
```

Use exact internal values in tests.

Do not hard-code rounded UI values into business logic.

---

# 28. Preserve 1000-Sample Invalidation Behaviour

Test:

```text
Samples
500 → 1000
```

Expected immediately after the upstream change:

```text
Storage
Complete/current

Compute
Needs review

Transfer
Needs review
```

Old 500-sample Compute and Transfer figures must not remain displayed as current.

---

# 29. Revisit Compute

When Compute is revisited after the sample-count change:

```text
Alignment workers
7

DeepVariant workers
13

Scratch
333 GiB
```

must remain configured.

Compute should recalculate for the 1000-sample project.

The deployed review observed approximately:

```text
831.74 h
```

Preserve the existing calculation logic.

---

# 30. Revisit Transfer

When Transfer is revisited after the sample-count change:

```text
FASTQ
Measured throughput
777 Mbps
```

must remain configured.

The Transfer result should recalculate using the new project data volume.

Do not require the user to re-enter:

```text
777 Mbps
```

simply because the upstream project changed.

---

# 31. Module-Specific Changes

Preserve dependency isolation.

## Compute-only change

Changing:

```text
alignment workers
7 → 8
```

must affect Compute/Summary as appropriate.

It must not invalidate Storage.

It must not erase Transfer configuration.

## Transfer-only change

Changing:

```text
777 Mbps → 888 Mbps
```

must affect Transfer/Summary.

It must not invalidate Storage.

It must not invalidate Compute.

---

# 32. Transfer Validation Must Not Destroy Configuration

If a Transfer field temporarily becomes invalid:

```text
Measured throughput
0
```

show validation feedback.

Do not erase unrelated Transfer configuration.

If the user restores a valid value, the calculation should recover normally.

Do not mark Transfer Complete while the current input remains invalid.

---

# 33. Exports

Ensure Transfer exports use canonical Transfer configuration.

Test:

```text
Transfer
→ Project Summary
→ Storage
→ Compute
→ Transfer
→ Export
```

The exported configuration must still contain the originally configured values.

For the regression case, this includes:

```text
dataset = FASTQ
throughput_mode = measured
measured_throughput_mbps = 777
```

plus the current endpoint/method/RTT fields where configured.

---

# 34. Tests

Add or update tests covering the remaining defects.

At minimum:

## Transfer measured-throughput persistence

```text
777 Mbps
```

survives page round-trip.

## Transfer known-capacity persistence

Distinctive capacity and efficiency survive page round-trip.

## Transfer optional-field persistence

Endpoints, locations, method and RTT survive.

## Transfer validity/status

Valid current result:

```text
Complete
```

Invalid current result:

```text
not Complete
```

Stale upstream dependency:

```text
Needs review
```

## Project configured state

Fresh project:

```text
not configured
```

After valid project setup:

```text
configured
```

Configured 500-sample project must not show default-project messaging.

## Dependency tests

Preserve existing 500→1000 invalidation behaviour.

## Full navigation

```text
Storage
→ Compute
→ Transfer
→ Project Summary
→ Storage
→ Compute
→ Transfer
→ Project Summary
```

must preserve all valid module configuration.

---

# 35. Full Distinctive-Value Transfer Regression

Use a Transfer configuration containing distinctive values for as many fields as currently supported.

For example:

```text
Dataset
FASTQ

Source
Institutional / local storage

Source location
Cape Town

Destination
AWS S3

Destination location
Cape Town AWS region

Throughput mode
Measured

Measured throughput
777 Mbps

Transfer method
Globus

RTT
37 ms
```

Use only options actually supported by the application.

Navigate through every page and back.

Verify every configured value survives.

This test is specifically intended to catch hidden transient-widget state beyond the known throughput defect.

---

# 36. Visual Acceptance

At desktop and narrow widths verify:

- progress/status treatment does not overflow;
- native top navigation remains usable;
- Continue actions remain readable;
- no duplicate giant navigation interface appears;
- Project Summary remains readable;
- no new layout regression occurs.

Test approximately:

```text
1440 px
1024 px
390 px
```

where practical.

---

# 37. Documentation

Update:

```text
docs/design-and-assumptions.md
```

only where necessary to reflect the completed behaviour.

Document:

- Transfer configuration persistence;
- canonical Transfer config;
- module status semantics;
- explicit configured-project state;
- guided but non-locking workflow;
- `/project-summary` as the implemented Summary route.

Do not turn the document into a changelog.

---

# 38. Explicitly Out of Scope

Do not implement:

- new Storage calculations;
- new Compute calculations;
- AWS EC2 pricing;
- AWS instance mapping;
- HPC monetary costing;
- Sentieon runtime benchmarking;
- DRAGEN/ICA costing;
- GLnexus benchmarking;
- new DeepVariant benchmarks;
- measured Compute scratch;
- pipelined workflow scheduling;
- transfer automation;
- Globus API integration;
- actual S3 transfer execution;
- database persistence;
- saved projects across browser sessions;
- user accounts;
- multi-user collaboration;
- AI/LLM recommendations;
- new Transfer pricing models;
- multi-leg Transfer workflows.

---

# 39. Acceptance Criteria

012c is complete when:

1. Measured Transfer throughput persists across page navigation.
2. All other Transfer configuration fields also persist.
3. Transfer no longer falls back to `0.00` after navigation.
4. Transfer status cannot say Complete when its current result is invalid or missing.
5. Stale Transfer results show Needs review.
6. Configured projects no longer display minimum/default-project warnings.
7. Fresh projects still clearly indicate that setup is incomplete.
8. Storage persistence remains correct.
9. Compute persistence remains correct.
10. 500→1000 dependency invalidation remains correct.
11. Compute-only changes do not invalidate Storage.
12. Transfer-only changes do not invalidate Storage or Compute.
13. Project Summary financial structure remains correct.
14. Explicit Transfer cost remains separate from the current included total.
15. Guided Storage → Compute → Transfer → Project Summary flow is visible.
16. Free top navigation remains available.
17. Continue actions work.
18. `/project-summary` works directly.
19. No page crashes.
20. Full automated test suite passes.

---

# 40. Deployment Completion Gate

After deployment, perform a fresh read-only review.

Configure:

```text
Project
Example WGS Project

WGS 30×
500 samples
5 years
```

Configure Compute:

```text
Alignment workers
7

DeepVariant workers
13

Scratch
333 GiB/worker
```

Configure Transfer:

```text
FASTQ
Measured throughput
777 Mbps
```

Then navigate:

```text
Storage
→ Compute
→ Transfer
→ Project Summary
→ Storage
→ Compute
→ Transfer
→ Project Summary
```

Verify:

```text
Storage configuration unchanged
Compute = 7 / 13 / 333
Transfer = FASTQ / measured / 777 Mbps
```

Verify the same results remain current.

Then:

```text
500 → 1000 samples
```

Verify:

```text
Storage       Complete
Compute       Needs review
Transfer      Needs review
```

Revisit Compute and confirm:

```text
7 / 13 / 333
```

are retained.

Revisit Transfer and confirm:

```text
FASTQ
Measured
777 Mbps
```

are retained.

Then change only:

```text
Alignment workers
7 → 8
```

and verify Storage remains current.

Then change only:

```text
Transfer throughput
777 → 888 Mbps
```

and verify Storage and Compute remain current.

Finally verify:

- configured/default-project messaging;
- module statuses;
- Continue actions;
- Project Summary finances;
- Transfer export;
- responsive layout;
- direct `/project-summary`;
- full automated tests.

Only then mark the entire:

```text
012 Transfer
012a Project State
012c Closure
```

phase complete.

---

# 41. Completion Report

After implementation report:

1. files modified;
2. root cause of Transfer throughput reset;
3. canonical Transfer configuration changes;
4. Transfer widget rehydration approach;
5. other Transfer fields audited;
6. status-validity changes;
7. configured-project state implementation;
8. guided-flow UI implementation;
9. Continue navigation;
10. Summary/default messaging changes;
11. route/documentation updates;
12. regression tests added;
13. 500-sample regression result;
14. 500→1000 invalidation result;
15. full navigation persistence result;
16. automated test results;
17. functionality deliberately deferred.
