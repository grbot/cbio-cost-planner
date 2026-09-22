# 014 — V1 Release Hardening

## Objective

Prepare the CBIO Genomics Infrastructure Cost Planner for its first stable release:

```text
v1.0.0
```

This is a **release-hardening iteration**.

It is not a new feature iteration.

The application now has a substantially working architecture:

```text
Project
   │
   ├── Storage
   ├── Compute
   └── Transfer
          │
          ▼
    Project Summary
```

The canonical `ProjectState` introduced in 013 has fixed the major project-persistence problem.

013a has also moved project configuration into the shared Project area and introduced the `New project` workflow.

The goal of 014 is to remove the remaining correctness and state-semantic defects that would make a V1 release misleading or unreliable.

After the acceptance gate passes:

```text
tag/release v1.0.0
```

and stop feature development for this release.

Do not add additional infrastructure-planning functionality in 014.

---

# 1. Release Principle

V1 does not need to model everything.

V1 does need to be internally trustworthy.

A user must be able to trust that:

```text
the project shown
=
the project being calculated
=
the project shown in Summary
```

and:

```text
Not configured
```

really means:

```text
no project has yet been intentionally configured
```

The application must never silently present defaults or stale results as though they describe the current project.

---

# 2. Scope

014 addresses only:

1. truthful unconfigured-state presentation;
2. Project Summary synchronization with canonical ProjectState;
3. stale-result handling;
4. remaining Transfer canonical-state persistence defects;
5. New project/reset correctness;
6. release regression testing;
7. versioning/documentation required for `v1.0.0`.

Do not expand beyond this scope unless necessary to fix a blocking correctness defect.

---

# 3. Preserve the Current Architecture

Do not redesign the application again.

Preserve:

- canonical `ProjectState`;
- shared Project header;
- WGS 30× / Custom Project selection;
- Load Example;
- New project;
- Storage;
- Compute;
- Transfer;
- Project Summary;
- current calculation engines;
- current GRO styling;
- current native Streamlit top navigation.

Fix the remaining defects inside this architecture.

---

# 4. Current Known Good Behaviour

Preserve the following deployed behaviour.

The example:

```text
500 × 30× WGS
5-year retention
```

loads correctly.

Storage currently produces approximately:

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

Project identity and Storage state now survive:

```text
Storage
→ Compute
→ Storage
```

and:

```text
Storage
→ Compute
→ Transfer
→ Project Summary
→ Storage
```

The Transfer model correctly produces approximately:

```text
FASTQ
48.83 TB

777 Mbps
153.5 h
```

when correctly configured.

Summary correctly separates:

```text
Storage workflow-egress charge
```

from:

```text
explicit Transfer-plan provider charge
```

and does not double count the explicit Transfer charge.

Preserve these behaviours.

---

# 5. Release Blocker A — Unconfigured State Is Misleading

After:

```text
New project
```

the Project area correctly indicates:

```text
Not yet configured
```

but module content can still imply that a WGS project exists.

Examples observed include:

```text
01 WGS 30× data volume & movement
```

on Storage,

```text
Profile: 1 × 30× WGS
```

on Compute,

and:

```text
Mode: WGS 30×
```

on Transfer.

This is misleading.

The user has not configured a WGS project.

The application is exposing internal/default model values as though they describe user intent.

Fix this.

---

# 6. Defaults Are Not User Intent

The application may internally require defaults such as:

```text
sample count = 1
project mode = WGS30x
```

to initialise models safely.

That does not mean those values should be presented as the user's configured project.

Maintain a clear distinction between:

```text
internal calculator defaults
```

and:

```text
intentional project configuration
```

---

# 7. Unconfigured Project Presentation

When:

```text
project configured = False
```

or equivalent canonical state,

the application should present a genuinely unconfigured experience.

Conceptually:

```text
PROJECT

Not yet configured
```

Then module pages should communicate that configuration is required.

For example:

## Storage

```text
Storage

Configure a project to calculate storage requirements.
```

## Compute

```text
Compute

Configure a project to calculate compute requirements.
```

## Transfer

```text
Transfer

Configure a project to calculate transfer requirements.
```

Exact wording may follow the existing UI style.

Keep it concise.

---

# 8. Do Not Display Fake WGS Context When Unconfigured

When the project is not configured, do not display project-specific labels such as:

```text
1 × 30× WGS
```

or:

```text
Mode: WGS 30×
```

or:

```text
WGS 30× data volume & movement
```

as though they describe the current project.

These may appear once the user intentionally chooses/configures WGS 30×.

---

# 9. Project Type Selection

The shared Project setup may still offer:

```text
WGS 30×
Custom Project
```

as available choices.

That is different from saying:

```text
the current project is WGS 30×
```

before the user has configured it.

Ensure the UI distinction is clear.

---

# 10. Unconfigured Module Status

After `New project`, expected module status is:

```text
Storage
Not configured

Compute
Not configured

Transfer
Not configured
```

Normal navigation must not change this merely because a page was opened.

---

# 11. Visiting an Unconfigured Module

Test:

```text
New project
→ Compute
→ Transfer
→ Project Summary
→ Storage
```

Expected:

```text
project remains Not yet configured
```

and all modules remain appropriately:

```text
Not configured
```

unless the user intentionally configures something.

Page visits are not project configuration.

---

# 12. Release Blocker B — Project Summary Does Not Follow Current Samples

A deployed review observed:

```text
configured project
500 samples
```

then:

```text
Samples
500 → 1000
```

The shared Project header correctly showed:

```text
1000 samples
```

but Project Summary continued showing information associated with:

```text
500 samples
```

including old Storage values.

This is a V1 correctness blocker.

---

# 13. Summary Project Identity Must Be Canonical

Project Summary must always obtain project identity/configuration directly from current canonical `ProjectState`.

This includes at minimum:

```text
project name
project type
sample count
retention
```

and other project-level identity fields currently displayed.

Do not obtain current project identity from a module result snapshot.

---

# 14. Summary Sample Count Test

Configure:

```text
500 samples
```

Open Summary.

Expected:

```text
500 samples
```

Then change:

```text
500 → 1000
```

Open Summary.

Expected project identity:

```text
1000 samples
```

immediately.

It must never continue to display:

```text
500 samples
```

as the current project.

---

# 15. Current Project Versus Stale Results

After an upstream project change, it is possible to have:

```text
Current project
1000 samples
```

while a previously calculated result was based on:

```text
500 samples
```

This is acceptable internally.

What is not acceptable is presenting that old result as though it describes the current 1000-sample project.

---

# 16. Release Blocker C — Stale Results

A deployed review observed the dangerous combination:

```text
Project header
1000 samples
```

while Summary still displayed:

```text
500-sample-derived values
73.2 TB
R693,613
```

without sufficiently preventing them from appearing current.

Fix this.

---

# 17. Stale Result Policy

Use the canonical dependency/revision mechanism.

For every module result determine:

```text
Current
```

or:

```text
Stale
```

relative to current ProjectState.

Summary must never treat a stale result as current.

---

# 18. Preferred Stale Result Presentation

For V1, keep this simple.

If a module result is stale, prefer:

```text
Compute
Needs review

The project configuration has changed.
Revisit Compute to refresh this estimate.
```

rather than displaying old numbers prominently.

Likewise for Transfer.

For Storage, if Storage is automatically recalculated safely when project-level inputs change, display the new current Storage result.

---

# 19. Do Not Mix Current and Stale Results

Never present:

```text
1000-sample project
```

with:

```text
500-sample Compute estimate
```

or:

```text
500-sample Transfer estimate
```

as though they are current.

Either:

- recalculate automatically where safe;
- or mark the module Needs review and suppress/de-emphasise stale numbers.

---

# 20. Summary Must State What Is Current

Project Summary should make status obvious.

For example:

```text
Storage
Complete

Compute
Needs review

Transfer
Needs review
```

Then only current results should be presented as authoritative.

Do not create a complex warning system.

Use the existing status model.

---

# 21. Current Included Total

The Summary's:

```text
Current included total
```

must only use current values that belong to the current project.

Do not calculate an apparently authoritative total from mixed project revisions.

If required inputs for the current included total are stale, either:

- recalculate the relevant included component automatically where deterministic and safe;
- or clearly indicate the total needs refresh.

Do not silently use an old project total.

---

# 22. Storage Recalculation

Storage appears capable of deterministic recalculation when project-level sample count changes.

If the current architecture already supports this safely:

```text
500 → 1000
```

may immediately recalculate Storage.

Expected approximate 1000-sample values under the current model:

```text
Durable
146.5 TB

Provisioned
175.8 TB

Workflow egress
145.3 TB

Current included total
R1,289,918
```

Use exact internal values.

Do not hard-code these numbers.

---

# 23. Compute Staleness

When:

```text
500 → 1000
```

and the Compute result was calculated for 500,

Compute should become:

```text
Needs review
```

unless the architecture intentionally and safely recalculates Compute automatically.

For V1, retaining configuration and requiring review/recalculation is acceptable.

---

# 24. Transfer Staleness

Similarly:

```text
500 → 1000
```

should make the previous Transfer result:

```text
Needs review
```

if the transferred dataset volume depends on sample count.

Retain Transfer configuration such as:

```text
777 Mbps
Globus
137 ms
locations
note
```

while marking the result stale.

---

# 25. Immediate Invalidation

The stale/current state must be determined when the upstream project configuration changes.

It must not depend on subsequently visiting Compute or Transfer.

Test:

```text
all modules current at 500

Samples
500 → 1000
```

Immediately expected:

```text
Storage
Complete

Compute
Needs review

Transfer
Needs review
```

before opening Compute or Transfer.

---

# 26. Release Blocker D — Remaining Transfer Persistence

The deployed application still loses some Transfer values.

Observed:

```text
Measured throughput
777 Mbps
```

can become:

```text
0.00 Mbps
```

after:

```text
Measured
→ Unknown
→ Measured
```

and/or after navigation.

The Transfer note has also been lost.

RTT entry:

```text
137 ms
```

has snapped back to:

```text
0.00
```

These are V1 blockers.

---

# 27. Finish Transfer Canonicalisation

Do not patch only one widget.

Audit every editable Transfer field against canonical `ProjectState`.

At minimum verify:

```text
dataset
custom dataset size where applicable
source endpoint
source location
destination endpoint
destination location
throughput mode
measured throughput
link capacity
efficiency
transfer method
RTT enabled
RTT
note
```

Use actual implemented fields.

---

# 28. Transfer Canonical Rule

Every meaningful Transfer value must live in canonical state.

Streamlit widget keys remain UI-only.

Widget deletion must not destroy:

```text
777 Mbps
137 ms
locations
note
```

---

# 29. Fix RTT Commit Behaviour

The deployed review observed:

```text
enter 137
→ snaps back to 0.00
```

Trace the exact cause.

Possible classes include:

- callback ordering;
- hydration overwriting user edits;
- default write-back;
- validation writing old canonical state;
- widget-key recreation;
- number-input rerun behaviour.

Do not assume the cause.

Identify and report it.

Expected:

```text
enter 137
→ canonical RTT = 137
→ widget remains 137
```

---

# 30. Conditional Transfer Values

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
RTT enabled
137
→ disabled
→ enabled
```

Expected:

```text
137
```

Inactive values should remain canonical unless explicitly reset.

---

# 31. Transfer Full Round Trip

Configure:

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
014 V1 persistence test
```

Navigate:

```text
Transfer
→ Project Summary
→ Storage
→ Compute
→ Transfer
```

Expected:

```text
every value retained exactly
```

If any value disappears:

```text
V1 release gate FAIL
```

---

# 32. Transfer Calculation Regression

With the 500-sample example:

```text
FASTQ
777 Mbps
```

continue to produce approximately:

```text
48.83 TB
153.5 h
```

Do not change the transfer arithmetic during this hardening iteration.

---

# 33. Compute Default Versus Regression Configuration

Do not treat:

```text
7 alignment workers
13 DeepVariant workers
333 GiB scratch
```

as required example-profile defaults.

These were distinctive regression/test settings.

The deployed example currently showing:

```text
10 / 10 / 250
```

is not itself a V1 defect if those are the intended defaults.

Preserve current intended example defaults unless there is another documented reason to change them.

---

# 34. Explicit Compute Regression

Separately test the known distinctive configuration:

```text
Alignment workers
7

DeepVariant workers
13

Scratch
333 GiB/worker
```

for the 500-sample project.

Expected approximately:

```text
419.04 h

Alignment peak
2,331 GiB

Overall peak
4,329 GiB
```

This validates the Compute engine without requiring the demo to default to those settings.

---

# 35. Compute Visit Semantics

A previous review observed that merely visiting Compute could mark it:

```text
Complete
```

For V1, simplify this question.

If:

- the project has been intentionally configured;
- Compute has valid default configuration;
- the Compute engine produces a valid current estimate;

then `Complete` is acceptable even if the user did not manually edit Compute.

Do not create unnecessary workflow-state complexity merely to require a click.

However:

```text
unconfigured project
```

must never become configured/Complete merely because Compute was visited.

The important distinction is:

```text
valid configured project with valid default Compute estimate
```

versus:

```text
no configured project
```

---

# 36. Transfer Status Semantics

Transfer with:

```text
Measured throughput
0 Mbps
```

must not be:

```text
Complete
```

The deployed application currently marks this:

```text
Invalid
```

which is acceptable.

Preserve that behaviour.

---

# 37. Unknown Throughput Mode

If Unknown mode intentionally provides planning scenarios such as:

```text
100 Mbps
500 Mbps
1 Gbps
5 Gbps
10 Gbps
```

decide whether that constitutes a valid completed Transfer planning view.

Use the current intended model.

Do not invent additional workflow semantics solely for release hardening.

Document the decision briefly.

---

# 38. New Project

Complete the New project behaviour introduced in 013a.

The action should remain:

```text
New project
```

with confirmation:

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

---

# 39. New Project Cancel

Verify:

```text
New project
→ Cancel
```

changes nothing.

Canonical project state must remain exactly unchanged.

---

# 40. New Project Confirm

Verify:

```text
New project
→ Start new project
```

atomically replaces the canonical project state.

Expected:

```text
Project
Not yet configured

Storage
Not configured

Compute
Not configured

Transfer
Not configured
```

No previous results remain current.

---

# 41. No Ghost Values

Before New project configure distinctive values:

```text
500 samples

Compute
7 / 13 / 333

Transfer
777 Mbps
137 ms
Globus
distinctive locations
014 V1 persistence test
```

Then:

```text
New project
→ Start new project
```

Navigate through every page.

None of the old values may reappear.

---

# 42. Load Example After Reset

After New project:

```text
Load 500 × 30× WGS / 5-year demo profile
```

Expected:

```text
Example WGS Project
500 samples
5 years
WGS 30×
```

and known Storage calculations.

This verifies that:

```text
reset
→ configure
```

remains clean.

---

# 43. Project Summary After Reset

After New project, Summary must not show old project values.

It should communicate that the project is not yet configured.

Do not show:

```text
500 samples
73.2 TB
R693,613
```

from the previous project.

---

# 44. Project Summary Current Identity

Summary project identity must always come directly from canonical state.

Test transitions:

```text
Not configured
→ 500
→ 1000
→ New project
→ 500 example
```

Summary must reflect each state correctly.

---

# 45. Project Summary Result Validity

For each transition above, verify results are either:

```text
current
```

or:

```text
clearly unavailable / Needs review
```

Never silently stale.

---

# 46. Shared Project Header

Preserve the shared PROJECT area introduced in 013a.

It should continue to contain/represent:

- project status/identity;
- WGS 30× / Custom Project;
- Load Example;
- New project.

Do not move these controls back into Storage.

---

# 47. Storage Page

Storage should remain focused on Storage.

Do not reintroduce project ownership into the Storage section.

When unconfigured, show concise setup guidance rather than fake WGS calculations.

---

# 48. Compute Page

Compute should remain focused on Compute.

When project is unconfigured:

```text
Configure a project to calculate compute requirements.
```

or equivalent.

Do not show:

```text
Profile: 1 × 30× WGS
```

as though that project exists.

---

# 49. Transfer Page

Transfer should remain focused on Transfer.

When project is unconfigured:

```text
Configure a project to calculate transfer requirements.
```

or equivalent.

Do not show:

```text
Mode: WGS 30×
```

as current project state.

---

# 50. Summary Page

When unconfigured, Summary should not fabricate a one-sample project.

Show concise guidance.

For example:

```text
Project not yet configured.

Configure a project to generate an infrastructure summary.
```

---

# 51. Custom Project Regression

Do not focus only on WGS.

Perform a basic Custom Project smoke test:

```text
New project
→ Custom Project
→ configure a small distinctive dataset
→ Storage
→ Compute/Transfer where supported
→ Summary
→ back
```

Verify:

- project mode remains Custom Project;
- no WGS identity appears incorrectly;
- configured data persists;
- Summary identifies the project correctly.

Do not add new Custom functionality.

---

# 52. Existing Storage Regression

Preserve all current Storage calculations and pricing behaviour.

Do not change:

- 1 TB = 1024 GB;
- lifecycle calculations;
- AWS pricing config;
- FX;
- VAT;
- engineering;
- archive assumptions;
- workflow egress;
- sensitivity calculations.

---

# 53. Existing Compute Regression

Preserve:

- BWA-MEM2 benchmark;
- CRAM indexing;
- DeepVariant benchmark;
- configured/effective concurrency;
- scratch peak logic;
- sequential-stage estimate;
- current defaults.

No deeper Compute work in 014.

---

# 54. Existing Transfer Regression

Preserve:

- throughput formulas;
- binary storage conversion;
- decimal network rates;
- link-efficiency calculation;
- unknown-throughput scenarios;
- RTT/BDP calculation;
- provider-cost handling.

Only fix state persistence.

---

# 55. Existing Summary Financial Structure

Preserve:

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

separate and excluded unless explicitly owned by the current financial model.

Do not double count.

---

# 56. Pricing Provenance

Preserve current pricing provenance/disclaimer.

Do not refresh AWS pricing in this release unless required because existing configured values or documentation are internally inconsistent.

This iteration is not a pricing research update.

---

# 57. Version

After all release gates pass, set the application/package/repository version where currently appropriate to:

```text
1.0.0
```

Use the repository's existing versioning mechanism.

Do not invent multiple conflicting version sources.

If no formal version source currently exists, introduce one simple authoritative version location appropriate to the repository and reuse it where displayed/documented.

---

# 58. Semantic Versioning

Use:

```text
v1.0.0
```

for the Git release/tag.

Application/internal version:

```text
1.0.0
```

where conventional.

Do not tag/release until all mandatory gates pass.

---

# 59. UI Version Display

Do not add a large version badge.

If the application already displays a version in the footer/about area, update it.

If it does not, a restrained footer reference such as:

```text
v1.0.0
```

is acceptable but not mandatory.

Do not clutter the main interface.

---

# 60. Documentation

Update:

```text
docs/design-and-assumptions.md
```

to describe the final V1 behaviour.

Ensure it accurately documents:

- canonical ProjectState;
- configured versus unconfigured project;
- project-level setup;
- Storage/Compute/Transfer architecture;
- stale-result handling;
- Transfer persistence;
- Summary current-state behaviour;
- New project semantics;
- current calculation limitations.

Do not add debugging history.

---

# 61. README

Update README for V1.

It should concisely describe:

```text
CBIO Genomics Infrastructure Cost Planner
```

and the workflow:

```text
Configure Project
      ↓
Storage
      ↓
Compute
      ↓
Transfer
      ↓
Project Summary
```

Include:

- what V1 does;
- what it does not yet do;
- how to run locally;
- how to run tests;
- link to deployed application if already present;
- version.

Do not turn README into the full design document.

---

# 62. V1 Limitations

Document important current limitations honestly.

Examples include:

- Compute infrastructure monetary costing not yet implemented;
- AWS instance recommendations not yet implemented;
- HPC monetary costing not yet implemented;
- Sentieon runtime/cost integration not yet implemented beyond any existing placeholder/licensing information;
- DRAGEN/ICA comparison not yet implemented;
- GLnexus cohort compute not yet modelled;
- Transfer is planning only, not execution;
- pricing estimates require validation before budgeting/procurement.

Use only limitations actually applicable to the current application.

---

# 63. No New Features Before V1

Do not add:

- AWS EC2 recommendations;
- Spot;
- AWS Batch;
- Nextflow deployment;
- EBS cost model;
- HPC pricing;
- Sentieon execution model;
- DRAGEN/ICA model;
- GLnexus compute;
- multi-leg transfer;
- saved projects;
- authentication;
- database;
- AI recommendations;
- PDF report generation;
- new dashboard features.

Those belong after V1 feedback.

---

# 64. Automated Test Gate

Before deployment run the complete automated test suite.

Do not weaken existing assertions merely to get green tests.

Add focused tests for the V1 blockers.

---

# 65. Mandatory Test — Unconfigured State

Create fresh/default ProjectState.

Assert:

```text
configured = False
```

and:

```text
Storage status = Not configured
Compute status = Not configured
Transfer status = Not configured
```

Ensure page-view helpers do not convert these statuses merely by rendering.

---

# 66. Mandatory Test — Summary Sample Synchronization

Test:

```text
500
→ Summary = 500

500 → 1000
→ Summary identity = 1000
```

without requiring Compute/Transfer visits.

---

# 67. Mandatory Test — Stale Results

Start with current 500-sample results.

Change:

```text
500 → 1000
```

Assert:

```text
old Compute result is not current
old Transfer result is not current
```

and Summary does not present them as current.

---

# 68. Mandatory Test — Immediate Status

After:

```text
500 → 1000
```

assert immediately:

```text
Storage
Complete

Compute
Needs review

Transfer
Needs review
```

according to the current dependency model.

No downstream page-render call may be necessary.

---

# 69. Mandatory Test — Transfer Persistence

Test canonical persistence for:

```text
777
137
source location
destination location
note
Globus
```

after simulated widget-key removal.

---

# 70. Mandatory Test — Transfer Conditional State

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
RTT
137
→ disabled
→ enabled
→ 137
```

---

# 71. Mandatory Test — New Project

Start with fully configured state.

Call the canonical New project/reset transition.

Assert:

```text
configured = False
old results absent
old module config absent
statuses Not configured
```

---

# 72. Mandatory Test — Ghost State

Simulate stale widget keys from the previous project after canonical reset.

Hydrate pages.

Assert old values cannot overwrite the new ProjectState.

---

# 73. Mandatory Test — Example Reload

Test:

```text
New project
→ Load Example
```

and verify:

```text
500 samples
5 years
WGS 30×
```

plus expected Storage result.

---

# 74. Mandatory Test — Custom Project

Create a Custom Project with distinctive values.

Verify:

- persistence;
- correct project identity;
- no accidental WGS identity;
- Summary current identity.

---

# 75. Deployed Browser Release Gate

After deployment, run a fresh browser review.

Do not tag V1 before this passes.

---

# 76. Browser Gate A — Fresh State

Open a fresh session.

Expected:

```text
PROJECT
Not yet configured
```

Verify:

```text
Storage
Compute
Transfer
Summary
```

do not pretend a `1 × 30× WGS` project exists.

---

# 77. Browser Gate B — Navigation While Unconfigured

Navigate:

```text
Storage
→ Compute
→ Transfer
→ Project Summary
→ Storage
```

Expected:

```text
still Not yet configured
```

No module becomes configured merely from being visited.

---

# 78. Browser Gate C — Load Example

Load:

```text
500 × 30× WGS / 5-year demo
```

Verify:

```text
Example WGS Project
500 samples
5 years
```

Storage approximately:

```text
73.2 TB durable
87.9 TB provisioned
72.7 TB workflow egress
R693,613
```

---

# 79. Browser Gate D — Compute Regression

Configure:

```text
7 / 13 / 333
```

Verify approximately:

```text
419.04 h
2,331 GiB alignment peak
4,329 GiB overall peak
```

Do not require these to be demo defaults.

---

# 80. Browser Gate E — Transfer Persistence

Configure:

```text
FASTQ
777 Mbps
Globus
137 ms
Cape Town test source
AWS Cape Town test destination
014 V1 persistence test
```

Navigate full round trip.

Verify every value survives.

---

# 81. Browser Gate F — Conditional Transfer

Verify:

```text
Measured
777
→ Unknown
→ Measured
→ 777
```

and:

```text
RTT on
137
→ off
→ on
→ 137
```

---

# 82. Browser Gate G — 500 → 1000

With modules current at 500:

```text
500 → 1000
```

Before visiting Compute or Transfer verify:

```text
Project header
1000

Storage
Complete

Compute
Needs review

Transfer
Needs review
```

---

# 83. Browser Gate H — Summary After 500 → 1000

Immediately open Summary.

Expected:

```text
Samples
1000
```

Summary must not present:

```text
500
```

as current.

Storage should show current 1000-sample values if recalculated.

Old Compute/Transfer estimates must not appear current.

---

# 84. Browser Gate I — Recalculate Compute

Visit Compute.

Verify:

```text
7 / 13 / 333
```

survives.

Current model should produce approximately:

```text
831.74 h
```

Then:

```text
Compute
Complete
```

Transfer remains:

```text
Needs review
```

until refreshed.

---

# 85. Browser Gate J — Recalculate Transfer

Visit Transfer.

Verify:

```text
777
137
locations
note
Globus
```

survive.

Refresh/recalculate.

Transfer becomes:

```text
Complete
```

for the current 1000-sample project.

---

# 86. Browser Gate K — New Project Cancel

Select:

```text
New project
→ Cancel
```

Verify no state changes.

---

# 87. Browser Gate L — New Project Confirm

Select:

```text
New project
→ Start new project
```

Expected:

```text
PROJECT
Not yet configured
```

and:

```text
Storage
Not configured

Compute
Not configured

Transfer
Not configured
```

Old results disappear.

---

# 88. Browser Gate M — Ghost State

Navigate all pages after reset.

Verify none of the old:

```text
1000
7
13
333
777
137
locations
note
```

reappear.

---

# 89. Browser Gate N — Reload Example

Load the example again.

Verify clean:

```text
500
5 years
WGS 30×
```

and expected Storage calculations.

---

# 90. Browser Gate O — Custom Project

Start New project.

Configure a small distinctive Custom Project.

Navigate through supported modules and Summary.

Verify:

- Custom identity persists;
- Summary identity correct;
- no accidental WGS identity.

---

# 91. Browser Gate P — Responsive Smoke Test

Check approximately:

```text
1440 px
1024 px
390 px
```

Verify:

- Project header usable;
- navigation usable;
- no horizontal overflow;
- Summary readable;
- New project dialog usable.

Do not perform a visual redesign.

---

# 92. Release Acceptance Criteria

V1 may be released only if:

1. fresh project is truthfully unconfigured;
2. no fake `1 × 30× WGS` project is presented as current;
3. page navigation does not configure a project;
4. Load Example works;
5. 500-sample Storage regression passes;
6. explicit 7/13/333 Compute regression passes;
7. Transfer 777 calculation passes;
8. 777 persists;
9. 137 persists;
10. Transfer locations persist;
11. Transfer note persists;
12. conditional Transfer values persist;
13. Summary always displays current canonical sample count;
14. 500→1000 immediately invalidates dependent results;
15. Summary does not present stale results as current;
16. 1000-sample Storage regression passes;
17. Compute configuration survives staleness;
18. Transfer configuration survives staleness;
19. New project Cancel works;
20. New project Confirm works;
21. reset produces Not configured state;
22. no ghost values reappear;
23. example reload after reset works;
24. Custom Project smoke test passes;
25. Summary financial structure remains correct;
26. explicit Transfer charge remains separate;
27. no page crashes;
28. responsive smoke test passes;
29. automated test suite passes;
30. design documentation is current;
31. README is current;
32. version is ready for `1.0.0`.

---

# 93. Do Not Release on Partial Pass

If any correctness blocker remains, report:

```text
V1 RELEASE GATE FAILED
```

with the exact failing acceptance criteria.

Do not tag:

```text
v1.0.0
```

until the mandatory release gate passes.

---

# 94. Git Release

Only after all gates pass:

1. ensure working tree is clean;
2. ensure tests pass;
3. ensure deployed application corresponds to the tested commit;
4. set authoritative version to `1.0.0`;
5. commit release changes;
6. create annotated tag:

```text
v1.0.0
```

7. push the release commit;
8. push the tag.

If this repository uses GitHub Releases and the existing workflow supports it, create a concise V1 release entry.

Do not introduce new release infrastructure solely for this task.

---

# 95. Suggested V1 Release Notes

Keep release notes concise.

Conceptually:

```text
CBIO Genomics Infrastructure Cost Planner v1.0.0

Initial stable release.

Includes:
- shared project configuration
- 30× WGS and Custom Project planning
- durable storage and lifecycle costing
- workflow-egress estimates
- initial compute resource/runtime planning
- transfer volume, throughput and duration planning
- consolidated Project Summary
- configurable AWS pricing/FX assumptions
- CSV/JSON/Markdown exports
- canonical project-state management

Current limitations:
- compute infrastructure monetary costing is not yet included
- transfer planning does not execute transfers
- provider prices and project assumptions must be validated before budgeting or procurement
```

Adjust to match actual V1 functionality.

---

# 96. Required Completion Report

After implementation provide:

## Correctness fixes

1. files modified;
2. unconfigured-state changes;
3. Summary synchronization fix;
4. stale-result handling;
5. Transfer persistence root cause;
6. RTT root cause;
7. conditional-widget fix;
8. New project final behaviour.

## State

9. final configured/unconfigured semantics;
10. final module-status semantics;
11. dependency invalidation behaviour;
12. Summary current/stale-result rules.

## Regression

13. 500-sample Storage values;
14. 7/13/333 Compute values;
15. 777 Mbps Transfer values;
16. 1000-sample Storage values;
17. 1000-sample Compute value after refresh;
18. Summary financial values.

## Reset

19. New project Cancel result;
20. New project Confirm result;
21. ghost-state result;
22. example reload result.

## Custom

23. Custom Project smoke-test result.

## Testing

24. tests added/changed;
25. full automated test result;
26. responsive smoke-test result.

## Documentation

27. design-and-assumptions update;
28. README update;
29. V1 limitations documented.

## Deployment

30. deployed commit/version;
31. deployed browser acceptance result;
32. any remaining known correctness issues.

## Release

33. authoritative version location;
34. release commit;
35. `v1.0.0` tag;
36. whether tag was pushed;
37. release notes status.

## Final verdict

State exactly one of:

```text
V1 RELEASE GATE PASSED
```

or:

```text
V1 RELEASE GATE FAILED
```

If failed, list only the remaining blockers required before `v1.0.0`.

---

# 97. After V1

Once:

```text
v1.0.0
```

is released, stop development for this iteration.

Do not immediately begin V1.1 changes.

The intended next phase is:

```text
use the planner
show it to colleagues/users
collect feedback
identify which missing capabilities matter in practice
```

Then prioritise future work based on actual use.

Likely future areas include:

- real AWS compute architecture and pricing;
- On-Demand versus Spot;
- working-storage costing;
- Ilifu/HPC modelling;
- Sentieon;
- DRAGEN / ICA;
- GLnexus;
- measured CBIO/Ilifu benchmarks;
- richer transfer architecture;
- scenario comparison;
- infrastructure-plan/report generation.

These are explicitly **post-V1**.

---

## Final Principle

V1 does not need to be complete.

It needs to be trustworthy.

A user should always be able to answer:

```text
What project am I planning?

Which estimates are current?

Which estimates need review?

What is included in the cost?

What assumptions produced these numbers?
```

without the application giving contradictory answers.

Once that is true, release `v1.0.0` and move on.