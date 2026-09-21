# 013a — Project Setup and State Closure

## Objective

Complete the canonical project-state work introduced in 013 and make the application UI reflect that architecture clearly.

013 successfully fixed the fundamental project persistence problem:

```text
Load 500 × 30× WGS / 5-year demo
→ Compute
→ Storage
```

now retains the configured project.

The full:

```text
Storage
→ Compute
→ Transfer
→ Project Summary
→ Storage
```

round trip also retains the project identity, sample count, retention period, Storage assumptions and Storage results.

This is a major improvement and the 013 architecture should be preserved.

However, three areas remain before the project-state foundation can be formally closed:

1. some Transfer configuration still does not survive navigation;
2. module `Complete` status is currently too easy to obtain simply by visiting a page;
3. project-level controls are still presented as though they belong to Storage.

013a addresses only those issues and adds one explicit project-level action:

```text
New project
```

This is a closure iteration.

Do not redesign the calculation engines or introduce new infrastructure-planning functionality.

---

# 1. Preserve the 013 Architecture

013 established the central rule:

> There is exactly one canonical source of truth for the current project.

Continue using the canonical `ProjectState` architecture implemented in 013.

Do not introduce another parallel state mechanism.

The conceptual architecture remains:

```text
                       PROJECT
                          │
                    ProjectState
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
       Storage         Compute         Transfer
          │               │               │
          └───────────────┼───────────────┘
                          ▼
                    Project Summary
```

Widgets remain views onto canonical state.

Pages do not own the project.

---

# 2. Do Not Reopen the 013 Refactor

013a is not another state architecture rewrite.

The following now works and must remain working:

- project identity persistence;
- 500-sample demo persistence;
- Storage persistence;
- Storage calculation persistence;
- Compute project identity;
- full page navigation without losing the project;
- canonical project-state approach;
- existing Storage calculations;
- existing Compute calculations;
- existing Transfer calculations;
- existing Summary financial structure.

Fix remaining defects within the 013 architecture.

---

# 3. Confirm the Remaining Transfer Defect

The fresh deployed review after 013 reproduced:

```text
Transfer
Measured throughput = 777 Mbps
Note = distinctive value

→ Project Summary
→ Transfer
```

Observed:

```text
Measured throughput = 0.00 Mbps
Note = blank
```

while:

```text
Throughput mode = Measured
```

remained selected.

This means some Transfer fields are still not fully participating in the canonical-state architecture.

This must be fixed.

---

# 4. Audit Every Transfer Input

Do not patch only:

```text
777 Mbps
note
```

Audit every editable Transfer field.

For each actual field in the current implementation identify:

| Field | Widget key | Canonical field | Hydration source | Update path | Conditional? | Tested? |
|---|---|---|---|---|---|---|
| Dataset | | | | | | |
| Custom dataset size | | | | | | |
| Source endpoint | | | | | | |
| Source location | | | | | | |
| Destination endpoint | | | | | | |
| Destination location | | | | | | |
| Throughput mode | | | | | | |
| Measured throughput | | | | | | |
| Link capacity | | | | | | |
| Efficiency | | | | | | |
| Transfer method | | | | | | |
| RTT enabled | | | | | | |
| RTT | | | | | | |
| Note | | | | | | |

Use the actual current fields.

Do not invent fields merely to match this table.

---

# 5. Transfer Canonical-State Rule

Every Transfer business value must live in canonical state.

For example, conceptually:

```text
ProjectState.config.transfer.measured_throughput_mbps = 777
```

not only:

```text
st.session_state["transfer_measured_throughput"] = 777
```

The Streamlit widget key may disappear.

The canonical value must not.

---

# 6. Transfer Hydration

When Transfer is rendered:

```text
canonical TransferConfig
        ↓
hydrate missing widget keys
        ↓
render widgets
```

Example:

```text
canonical measured throughput
777
```

Widget key has disappeared because another page was visited.

Expected when returning:

```text
Measured throughput
777
```

not:

```text
0.00
```

---

# 7. Transfer Note Persistence

The note is project configuration.

It must survive navigation.

Test:

```text
Note
013a persistence test

→ Storage
→ Compute
→ Project Summary
→ Transfer
```

Expected:

```text
013a persistence test
```

---

# 8. Transfer Location Persistence

Test both:

```text
Source location
Cape Town test source

Destination location
AWS Cape Town test destination
```

Navigate away and back.

Both must remain exactly.

---

# 9. RTT Persistence

Test:

```text
RTT enabled
True

RTT
137 ms
```

Navigate through all pages.

Expected:

```text
137 ms
```

must remain.

---

# 10. Conditional Transfer Persistence

Conditional UI must not erase canonical values.

Test:

```text
Throughput mode
Measured

Measured throughput
777 Mbps
```

Then:

```text
Measured
→ Unknown
→ Measured
```

Expected:

```text
777 Mbps
```

Likewise:

```text
RTT enabled
True

RTT
137 ms
```

Then:

```text
True
→ False
→ True
```

Expected:

```text
137 ms
```

Retain inactive values in canonical configuration unless the user explicitly resets them.

---

# 11. Transfer Round-Trip Gate

Configure distinctive Transfer values:

```text
Dataset
FASTQ

Measured throughput
777 Mbps

Transfer method
Globus

RTT enabled
True

RTT
137 ms

Source location
Cape Town test source

Destination location
AWS Cape Town test destination

Note
013a persistence test
```

Then navigate:

```text
Transfer
→ Project Summary
→ Storage
→ Compute
→ Transfer
```

Every configured field must remain exactly.

If any configured Transfer field resets:

```text
013a FAIL
```

---

# 12. Status Semantics Need Tightening

The fresh deployed review also observed that simply visiting Compute and Transfer could cause them to become:

```text
Complete
```

even though Transfer still had:

- unknown throughput;
- no meaningful transfer mechanism selected;
- blank locations;
- no committed Transfer planning configuration.

This makes `Complete` more confident than the actual state warrants.

A page visit must not itself mean:

```text
Complete
```

---

# 13. Status Is Derived, Not Page-Driven

Preserve the 013 principle:

```text
canonical configuration
+
configuration validity
+
current result
+
dependency revisions
=
module status
```

Do not use:

```text
page visited
```

as a proxy for completion.

---

# 14. Status Definitions

Continue using:

```text
Not configured
Complete
Needs review
Invalid
```

with stricter semantics.

## Not configured

The user has not yet established enough intentional configuration for the module to count as a completed planning step.

## Complete

The module has:

- intentional configuration;
- valid configuration;
- a valid current result;
- dependencies matching current project state.

## Needs review

The module retains intentional configuration but its result is stale because an upstream dependency changed.

## Invalid

The user has intentionally configured the module but its current configuration cannot produce a valid result.

---

# 15. Page Visit Must Not Configure a Module

This is mandatory.

Fresh project:

```text
Compute
Not configured

Transfer
Not configured
```

Simply navigating:

```text
Storage
→ Compute
→ Transfer
```

must not automatically produce:

```text
Compute
Complete

Transfer
Complete
```

unless the module genuinely has sufficient intentional configuration and a valid current result according to the application's intended defaults.

---

# 16. Transfer Completion Requirements

Review what is genuinely required for a useful Transfer estimate.

At minimum, `Complete` should require:

- a selected/known dataset volume;
- meaningful source and destination endpoints;
- a usable throughput planning basis;
- a valid effective throughput;
- a valid calculated duration.

Do not require optional descriptive fields merely to satisfy status.

For example, locations may remain optional if the model does not require them.

RTT may remain optional.

A note is optional.

But:

```text
Measured throughput mode
0 Mbps
```

cannot be Complete.

Likewise an unknown-throughput scenario should only be Complete if the application intentionally treats the scenario table itself as a completed Transfer estimate.

Make this distinction explicit in code/tests.

---

# 17. Transfer Method Semantics

Determine whether Transfer method is:

```text
required configuration
```

or:

```text
optional descriptive metadata
```

based on the current intended model.

Do not arbitrarily require it merely to make status stricter.

Document the decision.

If no method is selected and method is optional:

```text
Complete
```

may still be valid if the transfer estimate itself is valid.

If method is intended to be required for a completed plan, enforce that consistently.

---

# 18. Compute Completion Semantics

Review Compute similarly.

Do not mark Compute Complete merely because its page was visited.

However, Compute already has meaningful default benchmark/resource assumptions.

Therefore it may be reasonable for Compute to become Complete once a configured WGS project exists and the current Compute model can calculate a valid estimate.

The decision should be based on:

```text
intentional project configuration
+
valid Compute configuration/result
```

not:

```text
user opened Compute
```

---

# 19. Project Setup Is Not Storage

The UI should now reflect the canonical architecture.

Currently controls such as:

```text
Load 500 × 30× WGS / 5-year demo profile
WGS 30×
Custom Project
```

are presented within Storage.

These are not fundamentally Storage settings.

They establish the project itself.

Move project-level controls out of the Storage-specific section.

---

# 20. Project Setup Area

Introduce a compact project-level setup/identity area beneath:

```text
CBIO
Genomics Infrastructure Cost Planner
```

and above the module-specific content.

Conceptually:

```text
CBIO
Genomics Infrastructure Cost Planner

PROJECT
Example WGS Project
WGS 30×  ·  500 samples  ·  5 years

[ New project ]

────────────────────────────────────────

Storage
Estimate durable storage, lifecycle and storage-related costs
```

Exact layout may be adapted to the existing visual system.

Keep it restrained and consistent with GRO styling.

---

# 21. Do Not Add a Fifth Navigation Page

Do not change:

```text
Storage
Compute
Transfer
Project Summary
```

into:

```text
Project
Storage
Compute
Transfer
Project Summary
```

for 013a.

Project setup should sit above the module workflow.

The existing top navigation remains focused on the four planning views.

---

# 22. Project Setup Ownership

The project-level area owns:

- project name;
- project type/mode;
- WGS 30× versus Custom Project;
- project-level sample count where appropriate;
- project-level retention where appropriate;
- Load Example;
- New project.

Be careful with existing fields.

Only move fields that are genuinely project-level.

Do not move Storage-specific assumptions into the Project area.

---

# 23. WGS 30× and Custom Project

Move the current:

```text
WGS 30×
Custom Project
```

selection out of the Storage section and into Project setup.

This choice defines the project/data model used by the application.

Conceptually:

```text
Project type

[ WGS 30× ]   [ Custom Project ]
```

Do not change the underlying WGS or Custom Project calculation models.

This is a UI/ownership change.

---

# 24. WGS Project-Level Inputs

For:

```text
WGS 30×
```

the Project area may contain the genuinely shared project inputs such as:

```text
Project name
Number of samples
Retention period
```

where these are already canonical shared inputs.

Do not duplicate them in Storage after moving them.

---

# 25. Custom Project

For:

```text
Custom Project
```

keep the existing generic dataset model.

Move only the project-type selection and genuinely project-level identity controls.

Dataset-specific Storage configuration may remain in Storage if it belongs there.

Do not redesign Custom Project in this iteration.

---

# 26. Load Example Is a Project Action

Move:

```text
Load 500 × 30× WGS / 5-year demo profile
```

into the Project area.

It should continue to atomically load canonical project configuration as established in 013.

It must not become a Storage-only operation.

---

# 27. Example Profile Behaviour

Loading the example should result in:

```text
Project name
Example WGS Project

Project type
WGS 30×

Samples
500

Retention
5 years
```

plus the existing example assumptions already defined by the profile.

Do not change the profile values in 013a.

---

# 28. Compact Configured Project View

Once a project is configured, avoid using excessive vertical space.

A configured project can be summarised compactly, for example:

```text
PROJECT

Example WGS Project
WGS 30×  ·  500 samples  ·  5 years                    New project
```

Use the current GRO visual language.

Do not create a large dashboard card.

---

# 29. Editing the Project

The user must still be able to edit project-level configuration.

Choose a simple interaction consistent with the current UI.

Possible approaches include:

- keep the compact project fields directly editable;
- use an Edit project expander;
- show the project setup controls compactly.

Do not introduce modal-heavy or complicated UI merely for editing.

Prefer the simplest approach that works reliably in Streamlit.

---

# 30. Project Area Across Pages

The project identity should be visible consistently on:

- Storage;
- Compute;
- Transfer;
- Project Summary.

However, do not duplicate separate project-state widgets independently on every page.

Use a shared rendering/helper function backed by canonical ProjectState.

The displayed project identity should always come from the same canonical state.

---

# 31. Avoid Excessive Vertical Repetition

On Compute, Transfer and Summary, the project area may be more compact than on Storage/project setup.

For example:

```text
PROJECT
Example WGS Project  ·  WGS 30×  ·  500 samples  ·  5 years
```

The exact implementation is flexible.

The goal is orientation, not another large section on every page.

---

# 32. New Project Action

Add:

```text
New project
```

as an explicit project-level action.

Use:

```text
New project
```

not:

```text
Clear
Clear project
Reset everything
```

This better communicates the user's intention.

---

# 33. New Project Placement

Place `New project` within the Project area.

Do not place it:

- beside Streamlit Fork/GitHub controls;
- in the native navigation bar;
- independently in unrelated module controls;
- inside Compute;
- inside Transfer.

It belongs to the project.

---

# 34. New Project Visual Treatment

Use a secondary/outline treatment in the normal Project view.

It should be available but not visually dominant.

Example:

```text
Load 500 × 30× WGS / 5-year demo profile     New project
```

when project setup actions are expanded.

On narrow screens, stack appropriately.

Preserve responsive behaviour.

---

# 35. New Project Confirmation

Because this action destroys the current in-session project configuration, require confirmation.

Use wording close to:

```text
Start a new project?

This will clear the current Storage, Compute and Transfer configuration
and all calculated results. This cannot be undone.
```

Actions:

```text
Cancel

Start new project
```

Use destructive styling for the final confirmation action where supported and consistent with the current design.

---

# 36. New Project Must Be Atomic

Do not clear individual widgets.

Do not clear:

```text
Storage
then Compute
then Transfer
```

piecemeal.

The action should conceptually perform:

```text
new_state = create_default_project()

st.session_state["project_state"] = new_state
```

plus only whatever UI-key cleanup/rerun is required by Streamlit.

Canonical state replacement is the authoritative reset.

---

# 37. New Project Must Clear Results

After confirmation, clear:

- Storage calculated result;
- Compute calculated result;
- Transfer calculated result;
- Summary-derived current project values;
- revision/dependency metadata belonging to the previous project.

Do not allow old results to reappear.

---

# 38. New Project Must Clear Configuration

Reset canonical:

- project configuration;
- Storage configuration;
- Compute configuration;
- Transfer configuration;

to genuine initial/default state.

Do not preserve values from the previous project unless they are global application defaults by design.

---

# 39. New Project Configured State

After reset:

```text
configured = False
```

or the equivalent canonical state.

The application should behave as a fresh session.

Expected statuses:

```text
Storage
Not configured

Compute
Not configured

Transfer
Not configured
```

subject to the exact existing Storage setup semantics.

Do not show the new default 1-sample state as a fully configured project.

---

# 40. New Project Returns to Storage

After successful reset:

```text
→ Storage
```

This is the natural starting point for configuring the new project.

Do not leave the user on Project Summary looking at an empty/default project.

---

# 41. New Project Confirmation Message

After reset, a short confirmation is useful:

```text
New project started.
```

Keep it brief.

Do not add a persistent alert.

---

# 42. Cancel Behaviour

Selecting:

```text
Cancel
```

must leave canonical ProjectState completely unchanged.

Test this.

---

# 43. New Project Must Not Leave Ghost Widget State

This is important after the 013 refactor.

Example:

```text
old project:
500 samples
777 Mbps
137 ms
7 / 13 / 333
```

Then:

```text
New project
→ confirm
```

Navigate through all pages.

None of these old values may reappear because stale Streamlit widget keys survived.

If necessary, remove/re-key relevant UI-only widget state as part of the atomic new-project transition.

Canonical ProjectState remains the source of truth.

---

# 44. New Project Regression Test

Configure:

```text
500-sample demo

Compute:
7 / 13 / 333

Transfer:
FASTQ
777 Mbps
137 ms
distinctive locations
distinctive note
Globus
```

Then:

```text
New project
→ confirm
```

Expected:

```text
project configured = False

Storage
Not configured

Compute
Not configured

Transfer
Not configured
```

Navigate:

```text
Storage
→ Compute
→ Transfer
→ Project Summary
→ Storage
```

No old project values may reappear.

---

# 45. Load Example After New Project

Test:

```text
configured project
→ New project
→ Load 500-sample example
```

Expected:

```text
Example WGS Project
WGS 30×
500 samples
5 years
```

with normal example calculations.

This verifies that reset and profile loading are clean inverse project transitions.

---

# 46. New Project After Example

Also test:

```text
Fresh session
→ Load example
→ New project
```

Expected:

```text
fresh unconfigured state
```

No demo values remain.

---

# 47. Preserve Guided Workflow

Continue to show the guided module flow:

```text
Storage
→ Compute
→ Transfer
→ Project Summary
```

and existing module status/progress information.

Project setup sits above this workflow.

Do not turn the application into a locked wizard.

Free top navigation remains available.

---

# 48. Project Setup and Guided Flow

The conceptual hierarchy should now be:

```text
PROJECT
   │
   ▼
Storage
   │
   ▼
Compute
   │
   ▼
Transfer
   │
   ▼
Project Summary
```

But Project is not a fifth page.

It is the shared context for the four planning views.

---

# 49. Storage Page After This Change

Storage should now begin with Storage-specific content.

It should no longer appear to own:

```text
WGS 30× / Custom Project
Load Example
New Project
```

Those belong above it.

Storage should focus on:

- durable datasets;
- file-size assumptions;
- provisioned envelope/headroom;
- active storage;
- archive lifecycle;
- storage-related workflow egress assumptions;
- engineering/pricing assumptions currently assigned to Storage;
- Storage results.

---

# 50. Compute Page

Do not change Compute functionality.

It should simply receive project context from canonical ProjectState.

Preserve:

- 7/13/333 persistence;
- benchmark assumptions;
- CRAM indexing;
- DeepVariant;
- scratch calculations;
- current runtime model.

---

# 51. Transfer Page

Apart from completing canonical state persistence and status semantics, do not change Transfer functionality.

Preserve:

- dataset selection;
- source/destination model;
- measured/link/unknown throughput modes;
- duration calculations;
- RTT/BDP;
- methods;
- provider-cost behaviour.

---

# 52. Project Summary

Do not change the established Summary financial structure.

Continue showing current values such as:

```text
Storage lifecycle

Planned workflow egress

Engineering

Current included total
```

and keep:

```text
explicit Transfer provider charge
```

separate.

Project Summary should also use the shared project identity area rather than maintaining its own independent project identity.

---

# 53. Preserve Known 500-Sample Regression

The example project should continue to produce approximately:

## Storage

```text
Durable
73.2 TB

Provisioned
87.9 TB

Workflow egress
72.7 TB

Current included total
R693,613
```

## Compute

with:

```text
7 alignment workers
13 DeepVariant workers
333 GiB scratch/worker
```

approximately:

```text
419.04 h

2,331 GiB alignment peak

4,329 GiB overall peak
```

## Transfer

FASTQ at:

```text
777 Mbps
```

approximately:

```text
48.83 TB
153.5 h
```

Use exact internal values.

Do not hard-code these rounded regression numbers.

---

# 54. Preserve 1000-Sample Regression

After:

```text
500 → 1000
```

continue to expect approximately:

```text
146.5 TB durable

175.8 TB provisioned

145.3 TB workflow egress

R1,289,918 current included total
```

and Compute with retained:

```text
7 / 13 / 333
```

approximately:

```text
831.74 h
```

Do not change calculation models in 013a.

---

# 55. Preserve Immediate Dependency Invalidation

013 intended:

```text
500 → 1000
```

to immediately produce:

```text
Storage
Complete

Compute
Needs review

Transfer
Needs review
```

without requiring page visits.

Verify this remains true after the 013a changes.

If the deployed 013 implementation still fails this test, fix it as part of state closure.

Do not defer it.

---

# 56. Status Consistency Across Pages

The same canonical status must appear in:

- Project area/progress indicator;
- Storage;
- Compute;
- Transfer;
- Project Summary.

Do not calculate status independently in each view.

---

# 57. No New Calculation Features

Do not add:

- AWS EC2 costing;
- AWS Batch;
- Spot modelling;
- EBS costing;
- HPC costing;
- Sentieon runtime;
- DRAGEN/ICA;
- GLnexus;
- new genomics benchmarks;
- transfer execution;
- multi-leg transfer planning.

013a closes the foundation first.

---

# 58. No Persistence Beyond Session

Do not add:

- database;
- saved projects;
- accounts;
- local browser storage;
- shareable URLs;
- cloud project persistence.

`New project` resets the current Streamlit-session project only.

Persistent project storage may be considered later if needed.

---

# 59. No New Logo or Branding Work

Preserve the current simplified branding:

```text
CBIO

Genomics Infrastructure Cost Planner
```

Do not reintroduce:

- DNA logo;
- strapline;
- decorative divider;
- new branding assets.

The Project area should use the existing GRO typography and spacing.

---

# 60. Responsive Behaviour

Verify the Project area at approximately:

```text
1440 px
1024 px
390 px
```

On narrow screens:

- project metadata may wrap;
- Load Example and New project may stack;
- buttons must remain usable;
- no horizontal overflow;
- module content remains readable.

Do not force desktop single-line layout onto mobile.

---

# 61. Automated Tests — Transfer Persistence

Add/retain automated tests for:

```text
777 Mbps
137 ms
source location
destination location
note
```

including simulated widget-key removal where practical.

These tests must verify canonical state survives UI lifecycle.

---

# 62. Automated Tests — Conditional Transfer Fields

Test:

```text
Measured
777
→ Unknown
→ Measured
→ 777
```

and:

```text
RTT enabled
137
→ disabled
→ enabled
→ 137
```

---

# 63. Automated Tests — Status

Test that:

```text
visiting a page
```

alone does not incorrectly change module status.

Test intentional configuration separately from page rendering.

---

# 64. Automated Tests — New Project

Test:

```text
configured project
→ new_project()
```

Expected:

- new canonical ProjectState;
- configured false;
- module results cleared;
- stale revisions removed;
- old module configuration gone;
- statuses reset appropriately.

---

# 65. Automated Test — Cancel New Project

If confirmation logic is testable below UI level, verify:

```text
Cancel
```

does not invoke project replacement.

At minimum browser-test this behaviour.

---

# 66. Automated Test — Ghost State

Simulate:

```text
old canonical project
+
old widget keys
```

then:

```text
New project
```

Ensure subsequent hydration uses the new canonical state and cannot restore old widget values.

This is especially important for:

```text
500
777
137
7 / 13 / 333
```

---

# 67. Documentation

Update:

```text
docs/design-and-assumptions.md
```

only where materially necessary.

Document:

- Project setup is shared application context;
- WGS 30× / Custom Project is project-level;
- one canonical ProjectState remains authoritative;
- New project atomically replaces canonical state;
- widget state is ephemeral;
- module status is derived from intentional configuration, validity, result and dependencies.

Do not add lengthy debugging history.

---

# 68. README

Update only if the user-facing application flow described there changes materially.

The flow should now be understood as:

```text
Configure Project

Storage
→ Compute
→ Transfer
→ Project Summary
```

without adding a fifth navigation page.

---

# 69. Deployed Browser Acceptance Gate

After deployment, perform a fresh browser review.

Do not declare 013a complete based only on automated tests.

---

# 70. Browser Gate A — Existing 013 Persistence

Fresh session:

```text
Load 500-sample example
→ Compute
→ Storage
```

Expected:

```text
500 samples
5 years
Example WGS Project
```

and Storage assumptions/results retained.

If this regresses:

```text
FAIL
```

---

# 71. Browser Gate B — Project Setup Placement

Verify:

- WGS 30× / Custom Project appears as project-level configuration;
- Load Example appears in Project setup;
- New project appears in Project setup;
- Storage begins with Storage-specific configuration;
- top navigation remains Storage / Compute / Transfer / Project Summary.

---

# 72. Browser Gate C — Transfer Persistence

Configure:

```text
FASTQ
777 Mbps
Globus
137 ms
Cape Town test source
AWS Cape Town test destination
013a persistence test
```

Navigate:

```text
Transfer
→ Project Summary
→ Storage
→ Compute
→ Transfer
```

Every value must remain.

If:

```text
777 → 0
```

or the note/location/RTT disappears:

```text
FAIL
```

---

# 73. Browser Gate D — Conditional Transfer Persistence

Test:

```text
Measured
777
→ Unknown
→ Measured
```

Expected:

```text
777
```

Test:

```text
RTT on
137
→ off
→ on
```

Expected:

```text
137
```

---

# 74. Browser Gate E — Status Semantics

Fresh project.

Navigate through:

```text
Storage
Compute
Transfer
```

Verify pages do not become Complete merely because they were visited.

Then intentionally configure valid modules and verify they can become Complete.

For Transfer specifically verify:

```text
Measured mode + 0 Mbps
```

cannot be Complete.

---

# 75. Browser Gate F — Immediate Dependency Status

Complete the 500-sample project.

Then:

```text
500 → 1000
```

Before visiting Compute or Transfer:

Expected:

```text
Storage
Complete

Compute
Needs review

Transfer
Needs review
```

If downstream status changes only after visiting a downstream page:

```text
FAIL
```

---

# 76. Browser Gate G — New Project Cancel

From a fully configured project:

```text
New project
→ Cancel
```

Expected:

```text
nothing changes
```

---

# 77. Browser Gate H — New Project Confirm

From a fully configured project:

```text
New project
→ Start new project
```

Expected:

- returns to Storage;
- fresh/default project state;
- configured false;
- Storage Not configured;
- Compute Not configured;
- Transfer Not configured;
- old results gone;
- old 500/777/137/7/13/333 values gone.

---

# 78. Browser Gate I — Ghost State

After New project, navigate:

```text
Storage
→ Compute
→ Transfer
→ Project Summary
→ Storage
```

No value from the previous project may reappear.

---

# 79. Browser Gate J — Reload Example

After New project:

```text
Load 500 × 30× WGS / 5-year demo profile
```

Expected:

```text
Example WGS Project
WGS 30×
500 samples
5 years
```

and known calculations.

---

# 80. Browser Gate K — Responsive Layout

Check:

```text
desktop
tablet
mobile
```

especially Project setup and New project controls.

No clipping or horizontal overflow.

---

# 81. Acceptance Criteria

013a is complete only when all of the following are true:

1. 013 canonical ProjectState remains the sole project source of truth.
2. Existing 500-sample Storage persistence remains fixed.
3. Transfer measured throughput survives navigation.
4. Transfer note survives navigation.
5. Transfer source location survives navigation.
6. Transfer destination location survives navigation.
7. Transfer RTT survives navigation.
8. Conditional throughput values survive mode switching.
9. Conditional RTT survives toggling.
10. No Transfer field relies solely on widget state.
11. Page visits alone do not incorrectly make modules Complete.
12. Transfer cannot be Complete with invalid measured throughput.
13. Status remains centrally derived.
14. 500→1000 immediately invalidates downstream results.
15. WGS 30× / Custom Project is visibly project-level.
16. Load Example is visibly project-level.
17. Storage no longer appears to own project type.
18. Project identity is consistently visible.
19. New project exists at project level.
20. New project requires confirmation.
21. Cancel preserves current project exactly.
22. Confirm atomically replaces canonical ProjectState.
23. New project clears all previous results.
24. New project clears old module configuration.
25. New project sets configured state to false.
26. New project returns to Storage.
27. old widget state cannot resurrect old project values.
28. Load Example works after New project.
29. existing Storage calculations remain unchanged.
30. existing Compute calculations remain unchanged.
31. existing Transfer calculations remain unchanged.
32. Summary financial structure remains unchanged.
33. explicit Transfer charge remains separate.
34. desktop layout remains clean.
35. mobile layout remains usable.
36. automated state tests pass.
37. existing test suite passes.
38. deployed browser acceptance passes.

---

# 82. Required Completion Report

After implementation report:

## Project setup

1. files modified;
2. project-level controls moved;
3. final Project area layout;
4. WGS 30× / Custom Project behaviour;
5. Load Example behaviour;
6. shared project identity rendering.

## Transfer closure

7. exact root cause of `777 → 0`;
8. exact root cause of note loss;
9. whether RTT/location fields had the same root cause;
10. final Transfer canonical-state mapping;
11. hydration behaviour;
12. conditional-field retention behaviour.

## Status

13. previous reason page visits caused Complete;
14. final Complete semantics;
15. Transfer completion requirements;
16. Compute completion semantics;
17. immediate 500→1000 invalidation result.

## New project

18. implementation of atomic reset;
19. confirmation behaviour;
20. cancel behaviour;
21. configured-state reset;
22. module-result clearing;
23. widget-key cleanup strategy;
24. ghost-state test result;
25. Load Example after reset result.

## Regression

26. 500-sample Storage result;
27. 500-sample Compute result;
28. 500-sample Transfer result;
29. 1000-sample regression;
30. Summary financial regression.

## Testing

31. Transfer persistence tests;
32. conditional-widget tests;
33. status tests;
34. New project tests;
35. ghost-state tests;
36. full automated test-suite result.

## Deployment

37. deployed 500→Compute→Storage result;
38. deployed Transfer round-trip result;
39. deployed conditional-field result;
40. deployed status result;
41. deployed New project Cancel result;
42. deployed New project Confirm result;
43. deployed ghost-state result;
44. responsive-layout result.

## Final status

45. remaining known correctness issues;
46. whether 013 and 013a can now be formally closed.

If any mandatory state-persistence, status, or New project acceptance criterion fails, report:

```text
013a NOT COMPLETE
```

Do not describe a partially working implementation as complete.

---

# 83. Closure

If 013a passes the deployed acceptance gate, formally close the project-state/UI-foundation work:

```text
012   Transfer model
012a  Initial project-state integrity
012c  Project-flow closure
012d  Transfer-state closure attempt
013   Canonical project-state architecture
013a  Project setup and state closure
```

At that point, stop iterating on Streamlit state unless a new concrete defect appears.

Resume development of the actual infrastructure-planning functionality.

The next major work should return to the deferred Compute roadmap rather than further state-management changes.

---

## Final Principle

The application should now communicate the same architecture in both code and UI:

```text
A project exists first.

Storage, Compute and Transfer describe that project.

Project Summary brings those descriptions together.
```

And there should be exactly two intentional ways to replace the current project:

```text
Load Example
```

or:

```text
New project
```

Normal navigation must never reset, recreate or silently redefine it.