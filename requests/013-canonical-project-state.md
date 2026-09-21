# 013 — Canonical Project State Architecture

## Objective

Replace the fragmented Streamlit state-management approach with one clear, durable and testable canonical project-state architecture.

This is an **application-state architecture correction**.

It is not a new feature iteration.

The existing calculation engines for:

- Storage;
- Compute;
- Transfer;
- Project Summary;

are substantially behaving correctly and must be preserved.

The problem to solve is application state.

Repeated deployed reviews after 012a, 012c and 012d have shown that project configuration and result validity still depend on:

- Streamlit widget lifecycle;
- which page has most recently been rendered;
- conditional widget rendering;
- duplicated state/configuration;
- page-specific invalidation/status logic.

The goal of 013 is to remove that dependency.

The central architectural rule is:

> There is exactly one canonical source of truth for the current project.

Pages display and edit that state.

Widgets do not own it.

---

# 1. Why 013 Is Required

The previous state-management iterations improved several behaviours but did not solve the underlying problem.

The deployed application still demonstrates behaviour such as:

```text
Select 500-sample demo
→ navigate to Compute
→ return to Storage
→ Storage values may return to defaults
```

Transfer continues to demonstrate:

```text
Measured throughput
777 Mbps
→ leave page
→ return
→ 0.00 Mbps
```

Other Transfer values have also disappeared:

```text
RTT
137 ms → 0 ms

source location
lost

destination location
lost

note
lost
```

Conditional widgets also lose state:

```text
Measured
777 Mbps
→ Unknown
→ Measured
→ 0 Mbps
```

There is also a deeper dependency/status problem.

After:

```text
Samples
500 → 1000
```

the Storage page has displayed:

```text
Compute
Complete

Transfer
Complete
```

until Compute or Transfer was subsequently visited.

After visiting Compute, Transfer then changed to:

```text
Needs review
```

This demonstrates that:

> Rendering a page is currently capable of changing the application's understanding of whether another module is current.

That must no longer be possible.

---

# 2. Architectural Goal

After 013, the application should conceptually behave as:

```text
                     ┌──────────────────────┐
                     │     ProjectState     │
                     │  canonical source    │
                     │      of truth        │
                     └──────────┬───────────┘
                                │
             ┌──────────────────┼──────────────────┐
             │                  │                  │
             ▼                  ▼                  ▼
         Storage UI         Compute UI        Transfer UI
             │                  │                  │
             └──────────────────┼──────────────────┘
                                │
                                ▼
                       Project Summary UI
```

The pages do not own project state.

The widgets do not own project state.

The Summary does not maintain a second project snapshot.

There is one project.

---

# 3. One Durable Session-State Root

Use one durable root object in Streamlit session state.

Conceptually:

```python
st.session_state["project_state"]
```

This object contains the canonical state of the current project.

The exact Python implementation may use:

- dataclasses;
- Pydantic;
- typed dictionaries;
- existing project models;
- another clean typed approach.

Use whichever best fits the current repository.

Do not introduce unnecessary dependencies merely for this refactor.

---

# 4. Recommended High-Level Structure

Conceptually:

```text
ProjectState
│
├── config
│   │
│   ├── project
│   │
│   ├── storage
│   │
│   ├── compute
│   │
│   └── transfer
│   │
│   └── commercial / shared assumptions where appropriate
│
├── results
│   │
│   ├── storage
│   ├── compute
│   └── transfer
│
├── revisions
│   │
│   ├── project/shared
│   ├── storage
│   ├── compute
│   └── transfer
│
└── metadata
    ├── configured
    ├── project mode/profile
    └── other genuinely project-level metadata
```

This is conceptual.

Adapt it to the existing models rather than mechanically reproducing these names.

The architectural properties matter more than the exact class layout.

---

# 5. Configuration and Results Must Be Separate

Separate:

```text
what the user configured
```

from:

```text
what the calculator derived
```

For example:

```text
ComputeConfig
alignment_workers = 7
deepvariant_workers = 13
scratch_per_worker_gib = 333
```

is configuration.

Whereas:

```text
ComputeResult
sequential_hours = 419.04
alignment_peak_gib = 2331
overall_peak_gib = 4329
```

is derived state.

Do not mix configuration and calculated values into the same widget/session structure.

---

# 6. Widget State Is Ephemeral

Treat every Streamlit widget key as disposable.

Assume this can happen at any time:

```text
widget exists
→ page disappears
→ Streamlit removes widget key
```

The application must remain correct.

Therefore:

> No business/project value may exist only in a Streamlit widget key.

This applies to:

- text inputs;
- number inputs;
- sliders;
- select boxes;
- radio buttons;
- toggles;
- conditional fields;
- custom dataset fields;
- notes;
- endpoint locations;
- RTT;
- throughput;
- engineering assumptions;
- sample count;
- retention;
- worker counts;
- scratch;
- all other user-editable project inputs.

---

# 7. Widget Keys and Canonical Keys Must Be Distinct Concepts

Do not use the same storage location as both:

```text
canonical project state
```

and:

```text
Streamlit widget state
```

Conceptually:

```text
canonical:
project_state.config.transfer.measured_throughput_mbps
```

versus:

```text
widget:
ui_transfer_measured_throughput
```

The exact naming convention is flexible.

The separation is not.

---

# 8. Rendering a Page Must Not Define Project Truth

Rendering:

```text
Storage
Compute
Transfer
Project Summary
```

must not itself change canonical project configuration.

Opening Compute must not reset Storage.

Opening Summary must not reset Transfer.

Opening Transfer must not be required before the application realises Transfer is stale.

Opening Compute must not be required before the application realises Compute is stale.

Page rendering is presentation.

It is not a state transition unless the user actually changes something or explicitly performs an action.

---

# 9. Page Render Idempotence

Rendering the same page repeatedly without user edits must be idempotent.

Conceptually:

```text
state_before = ProjectState

render Storage
render Storage
render Storage

state_after = ProjectState
```

Expected:

```text
state_before == state_after
```

excluding irrelevant UI-only metadata.

Apply the same principle to:

```text
Compute
Transfer
Project Summary
```

---

# 10. Hydration Pattern

When a page renders:

```text
canonical ProjectState
        ↓
hydrate page widgets
        ↓
display UI
```

If widget keys no longer exist because Streamlit removed them, recreate them from canonical state.

Example:

```text
ProjectState says:

samples = 500
```

Storage widget key is missing.

Expected:

```text
Storage sample widget
500
```

not:

```text
1
```

---

# 11. User Edit Pattern

When a user genuinely edits a widget:

```text
widget edit
    ↓
validate
    ↓
canonical ProjectState config
    ↓
revision/dependency update
    ↓
recalculate affected module
       OR
mark dependent result stale
```

The canonical object is updated intentionally.

Do not treat page hydration as a user edit.

---

# 12. Prevent Hydration Write-Back

Audit carefully for this failure pattern:

```text
widget key missing
        ↓
widget gets default
        ↓
callback executes
        ↓
default written into canonical state
```

This may be responsible for some current defects.

Hydrating a widget from canonical state must not accidentally overwrite canonical state with a default.

---

# 13. Remove Duplicate Sources of Truth

Inspect the current repository before implementing changes.

Identify all current locations where project state is stored, including:

- widget keys;
- module config objects;
- project config objects;
- result snapshots;
- status flags;
- revision values;
- demo/profile values;
- page-specific defaults;
- Summary snapshots;
- export-specific state;
- helper caches.

Create an internal inventory before refactoring.

Then decide which are:

```text
canonical
derived
UI-only
obsolete
```

Remove obsolete duplicate state where safe.

Do not simply place `ProjectState` above the existing tangled state system and keep every old state mechanism alive underneath it.

The desired outcome is **less state machinery**.

---

# 14. Existing State Architecture May Be Replaced

Do not preserve existing state implementation merely to minimise the diff.

012a, 012c and 012d attempted incremental repair.

If inspection shows that the current combination of:

- callbacks;
- widget keys;
- module configuration;
- result snapshots;
- status flags;
- dependency state;

has become unnecessarily tangled, simplify or replace it.

Preserve correct calculation models.

Do not preserve faulty state architecture for compatibility.

---

# 15. Project Configuration

Project-level configuration should include the genuinely shared inputs.

For example:

```text
project name
project type / mode
sample count
retention period
selected profile
```

and any other values that genuinely affect multiple modules.

Do not duplicate:

```text
sample count
```

separately inside Storage, Compute and Transfer if they all refer to the same project sample count.

---

# 16. Module Configuration

Module-specific configuration belongs under the module.

Examples:

## Storage

```text
file-size assumptions
headroom
active-storage duration
archive class
workflow transfer assumptions
engineering assumptions where currently owned
pricing assumptions where currently owned
```

## Compute

```text
alignment workers
DeepVariant workers
scratch per worker
runtime/resource assumptions
```

## Transfer

```text
dataset
source endpoint
source location
destination endpoint
destination location
throughput mode
measured throughput
known link capacity
efficiency
transfer method
RTT enabled
RTT
note
```

Use actual current fields.

Do not add new functionality.

---

# 17. The 500-Sample Demo Must Become Ordinary Project State

The 500-sample demo/profile must not have a special persistence mechanism.

Selecting the demo should simply load canonical configuration.

Conceptually:

```python
load_project_profile("wgs_500")
```

results in:

```text
ProjectState.config = configured demo values
```

After loading, it should be indistinguishable from the user manually entering the same configuration.

---

# 18. Demo Loading Must Be Atomic

Loading the 500-sample demo should intentionally replace/reset the relevant canonical configuration as one operation.

It must not rely on:

```text
setting Storage widgets
then hoping Compute/Transfer discover those values later
```

Conceptually:

```text
load profile
    ↓
canonical project config updated
    ↓
canonical module config updated where profile specifies it
    ↓
revisions updated
    ↓
affected results calculated/invalidated
    ↓
UI reflects state
```

---

# 19. Demo Must Not Reapply Itself

After the demo has been loaded, navigating between pages must not cause the demo loader to run again.

Likewise, a page must not detect:

```text
demo selected
```

and overwrite subsequent user edits every time it renders.

Demo loading is an explicit state transition.

It is not a permanent page-render behaviour.

---

# 20. First Hard Acceptance Test

Before testing anything else, this must pass:

```text
Fresh app
→ Storage
→ select/load 500-sample demo
→ confirm Samples = 500
→ Compute
→ Storage
```

Expected:

```text
Samples = 500
```

All other demo-loaded Storage values must also remain unchanged.

If this fails:

> stop.

Do not continue to more complex acceptance tests.

The architecture is not yet correct.

---

# 21. Manual Project Configuration Must Behave the Same

Repeat without using the demo.

Example:

```text
Fresh app
→ Storage
→ configure project manually
→ Samples = 437
→ Retention = 4.25 years
→ enter distinctive project name
→ Compute
→ Storage
```

Expected:

```text
437
4.25
distinctive project name
```

and all other manually configured Storage values remain.

Use distinctive values to prevent accidental default matches.

---

# 22. Storage State Test

Configure distinctive values across every editable Storage field.

Navigate:

```text
Storage
→ Compute
→ Transfer
→ Project Summary
→ Storage
```

Every Storage configuration field must remain.

Do not test only sample count.

Audit every editable Storage widget.

---

# 23. Compute State Test

Configure:

```text
Alignment workers
7

DeepVariant workers
13

Scratch
333 GiB/worker
```

plus distinctive values for any other editable Compute fields.

Navigate:

```text
Compute
→ Storage
→ Transfer
→ Project Summary
→ Compute
```

Every Compute configuration field must remain.

---

# 24. Transfer State Test

Configure:

```text
Dataset
FASTQ

Measured throughput
777 Mbps

RTT enabled
True

RTT
137 ms

distinctive source location

distinctive destination location

distinctive note

Globus
```

plus all other editable Transfer fields.

Navigate:

```text
Transfer
→ Storage
→ Compute
→ Project Summary
→ Transfer
```

Every value must remain.

Specifically verify:

```text
777 Mbps
137 ms
source location
destination location
note
```

These are mandatory regression fields because they repeatedly failed in deployed reviews.

---

# 25. Conditional Widget State

Canonical state must also survive conditional UI rendering.

Example:

```text
Measured throughput
777 Mbps
```

Switch:

```text
Measured
→ Unknown
→ Measured
```

Preferred expected result:

```text
777 Mbps
```

Likewise:

```text
RTT enabled
137 ms
```

Switch:

```text
enabled
→ disabled
→ enabled
```

Preferred expected result:

```text
137 ms
```

Do not erase inactive configuration unless the user explicitly resets it.

---

# 26. Project State Must Not Depend on Page Order

All reasonable navigation sequences must preserve state.

Test at least:

```text
Storage
→ Compute
→ Storage
```

```text
Storage
→ Transfer
→ Storage
```

```text
Storage
→ Project Summary
→ Storage
```

```text
Transfer
→ Compute
→ Transfer
```

```text
Compute
→ Project Summary
→ Compute
```

and:

```text
Storage
→ Compute
→ Transfer
→ Project Summary
→ Storage
→ Compute
→ Transfer
```

No sequence should reset project configuration.

---

# 27. Results Must Know Their Dependencies

Each derived module result must contain or be associated with enough metadata to determine whether it is still valid.

Conceptually:

```text
StorageResult
based_on:
    project_revision
    storage_config_revision

ComputeResult
based_on:
    project_revision
    compute_config_revision

TransferResult
based_on:
    project_revision
    transfer_config_revision
```

Exact dependency granularity may be more precise.

Prefer accurate dependency tracking rather than globally invalidating everything.

---

# 28. Revisions Are State, Status Is Derived

Do not maintain independent booleans such as:

```text
compute_complete = True
transfer_complete = True
```

if they can disagree with current state.

Prefer:

```text
current revisions
+
result dependency revisions
+
configuration validity
=
module status
```

Status should be derived.

---

# 29. Status Function Must Be Pure

Conceptually:

```python
status = get_module_status(project_state, module)
```

Calling this function must not mutate state.

It should return one of the supported statuses based on current canonical state.

At minimum:

```text
Not configured
Complete
Needs review
Invalid
```

---

# 30. Status Definitions

## Not configured

The user has not established sufficient intentional configuration for the module.

## Complete

The module has:

- valid current configuration;
- a valid result;
- result dependencies matching current canonical dependencies.

## Needs review

The module retains valid/intended configuration, but its last result is stale because an upstream dependency changed.

## Invalid

Current module configuration fails validation.

---

# 31. Page Visits Must Not Change Status

This is a hard requirement.

Suppose current state is:

```text
Storage       Complete
Compute       Needs review
Transfer      Needs review
```

Then navigating:

```text
Storage
→ Project Summary
→ Storage
```

must still show:

```text
Storage       Complete
Compute       Needs review
Transfer      Needs review
```

unless the user actually changed/recalculated something.

---

# 32. 500 → 1000 Must Invalidate Immediately

This is the second hard acceptance test.

Start with a fully current:

```text
500-sample project
```

with:

```text
Storage       Complete
Compute       Complete
Transfer      Complete
```

While on Storage change:

```text
Samples
500 → 1000
```

Immediately — before visiting Compute or Transfer — the canonical state must imply:

```text
Storage       Complete
Compute       Needs review
Transfer      Needs review
```

The Storage page flow indicator must show that immediately.

Project Summary must show the same state if opened next.

---

# 33. Visiting Compute Must Not Cause Transfer Invalidation

This currently appears to happen indirectly.

That must stop.

If changing:

```text
500 → 1000
```

invalidates Transfer, then Transfer becomes stale at the moment the sample count changes.

Not when Compute is later visited.

Compute rendering must not be the event that discovers or creates Transfer staleness.

---

# 34. Recalculating Compute

After the 500→1000 change, Compute configuration should remain:

```text
Alignment workers
7

DeepVariant workers
13

Scratch
333 GiB
```

Visiting/reviewing Compute should recalculate using the new project.

Then:

```text
Compute
Complete
```

Transfer should remain:

```text
Needs review
```

until Transfer itself is recalculated.

---

# 35. Recalculating Transfer

When Transfer is revisited after the upstream change, its configuration must remain:

```text
FASTQ
777 Mbps
137 ms
locations
method
note
```

It may then recalculate using the new project volume.

After successful recalculation:

```text
Transfer
Complete
```

---

# 36. Dependency Isolation

Do not solve state validity by invalidating everything after every change.

Dependencies must remain sensible.

## Compute-only edit

Changing:

```text
alignment workers
7 → 8
```

should affect:

```text
Compute
Project Summary
```

It should not invalidate Storage.

It should not invalidate Transfer unless Transfer genuinely depends on that Compute configuration.

Under the current model it generally should not.

## Transfer-only edit

Changing:

```text
777 → 888 Mbps
```

should affect:

```text
Transfer
Project Summary
```

It should not invalidate Storage or Compute.

---

# 37. Storage Dependencies

Changing Storage-only commercial assumptions such as an archive setting should not automatically invalidate Compute if Compute does not depend on that setting.

However, changing a shared data-volume assumption that Compute or Transfer uses may invalidate dependent results.

Use actual dependency relationships.

Do not use page ownership as dependency logic.

---

# 38. Shared Inputs

Explicitly identify which inputs are shared dependencies.

Likely examples include:

```text
project type
sample count
dataset/file-size assumptions where shared
```

Document the actual dependency graph in code and in the design documentation where useful.

---

# 39. Suggested Dependency Graph

Conceptually:

```text
Project identity / sample count
          │
          ├─────────────┬──────────────┐
          ▼             ▼              ▼
       Storage       Compute        Transfer
          │             │              │
          └─────────────┼──────────────┘
                        ▼
                     Summary
```

But individual module settings should remain isolated.

For example:

```text
Compute concurrency
→ Compute only
```

and:

```text
Transfer throughput
→ Transfer only
```

---

# 40. Project Summary Must Be Read-Only With Respect to Project State

Rendering Project Summary must not initialise, reset or repair project configuration.

Summary consumes:

```text
ProjectState
```

and presents:

- current configuration;
- current valid results;
- module statuses;
- financial summary.

Summary must not mutate the project merely because it was opened.

---

# 41. Summary Must Never Mix Revisions

Summary must not combine:

```text
Storage result for 1000 samples
Compute result for 500 samples
Transfer result for 500 samples
```

as though they were one current project.

If Compute/Transfer are stale:

```text
Needs review
```

and their stale results must not be presented as current authoritative estimates.

---

# 42. Preserve Financial Summary Behaviour

Do not change the now-working financial structure.

At 500 samples, the currently observed project includes approximately:

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

At 1000 samples, currently observed approximately:

```text
Storage lifecycle
R883,393

Planned workflow egress
R334,525

Engineering
R72,000

Current included total
R1,289,918
```

Use exact calculation values internally.

Do not hard-code these rounded values.

---

# 43. Explicit Transfer Charge Remains Separate

Preserve the current distinction between:

```text
Storage planned workflow egress
```

and:

```text
explicit Transfer plan provider charge
```

Do not automatically add the explicit Transfer plan into:

```text
Current included total
```

unless a later architecture explicitly defines ownership/deduplication.

That remains out of scope.

---

# 44. Preserve Existing Calculation Engines

Do not alter the business logic solely because state architecture is being refactored.

Preserve:

## Storage

- dataset volume calculations;
- headroom;
- lifecycle;
- archive;
- workflow egress;
- engineering;
- FX/VAT;
- sensitivity.

## Compute

- alignment benchmark;
- CRAM indexing;
- DeepVariant benchmark;
- worker/concurrency model;
- scratch;
- sequential-stage estimate.

## Transfer

- dataset volume;
- throughput conversion;
- duration;
- link efficiency;
- RTT/BDP;
- current provider-charge behaviour.

---

# 45. 500-Sample Numerical Regression

After state refactor, the established 500-sample regression must still approximately produce:

## Storage

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

## Compute

Configuration:

```text
Alignment workers
7

DeepVariant workers
13

Scratch
333 GiB/worker
```

Result approximately:

```text
419.04 h

Alignment peak
2,331 GiB

DeepVariant / overall peak
4,329 GiB
```

## Transfer

Configuration:

```text
FASTQ
777 Mbps
```

Result approximately:

```text
48.83 TB
153.5 h
```

Do not change the calculation model to make tests pass.

---

# 46. 1000-Sample Numerical Regression

After:

```text
500 → 1000
```

Storage should continue to produce approximately:

```text
146.5 TB durable

175.8 TB provisioned

145.3 TB workflow egress

R1,289,918 current included total
```

Compute with retained:

```text
7 / 13 / 333
```

should continue to produce approximately:

```text
831.74 h
```

under the current calculation model.

---

# 47. Demo Regression Must Be Separate From Calculation Regression

Do not confuse:

```text
demo successfully loaded
```

with:

```text
calculation returned expected values
```

Test both.

First:

```text
demo state survives navigation
```

Then:

```text
demo produces expected calculations
```

State correctness comes first.

---

# 48. Project Configured State

Preserve the corrected configured/default-project behaviour.

A fresh session may show the minimum/default project and indicate:

```text
project setup not yet completed
```

Once the user:

- loads the demo;
- or intentionally configures the project;

canonical metadata should reflect:

```text
configured = True
```

or equivalent.

Navigating pages must not reset this flag.

---

# 49. Do Not Infer Configuration From Non-Default Values

A user may intentionally configure:

```text
1 sample
```

or another value equal to a default.

Therefore:

```text
configured
```

must be intentional project state.

Do not infer it solely from:

```text
value != default
```

---

# 50. Export Must Read Canonical State

All exports must be generated from canonical configuration/results.

Do not export directly from transient widget keys.

This applies to:

- JSON;
- CSV;
- Markdown;
- any current export formats.

---

# 51. Export Round-Trip Test

Configure distinctive project values.

Navigate through all pages.

Then export.

Verify exported values match canonical state.

For Transfer specifically include:

```text
777 Mbps
137 ms
source location
destination location
note
```

where currently supported.

---

# 52. Reset Behaviour

If the application currently has an explicit:

```text
Reset
New project
Load demo
```

action, preserve its intended functionality.

But reset must be explicit.

Normal page navigation must never behave like reset.

---

# 53. Defaults

Defaults should be used only when creating a genuinely new project/configuration.

Conceptually:

```text
ProjectState does not exist
        ↓
create default ProjectState once
```

Not:

```text
Storage widget missing
        ↓
reapply Storage defaults
```

Not:

```text
Transfer page opened
        ↓
reapply Transfer defaults
```

Not:

```text
Summary opened
        ↓
create default module config
```

---

# 54. Initialise Once

Audit application startup.

Canonical ProjectState should be initialised once per Streamlit session unless an explicit project-reset/load action occurs.

Conceptually:

```python
if "project_state" not in st.session_state:
    st.session_state["project_state"] = create_default_project()
```

Do not rebuild it on every page.

---

# 55. Avoid `setdefault` Traps

Audit uses of:

```python
setdefault()
```

and similar initialisation helpers.

They are fine for genuinely missing canonical state.

They are dangerous when used against transient widget keys and then synchronized back into canonical state.

Ensure widget cleanup cannot trigger default project values.

---

# 56. Callback Audit

Inspect all callbacks related to:

- project;
- Storage;
- Compute;
- Transfer;
- demo/profile loading;
- Summary;
- progress/status.

For each callback determine:

```text
What canonical state does it read?

What canonical state does it write?

Is it triggered by user action or hydration?

Can it fire after widget recreation?

Can it overwrite canonical state with a default?
```

Remove unnecessary callbacks where simpler explicit synchronization is safer.

---

# 57. Page-Level Initialisation Audit

Inspect every page for code such as:

```text
if key missing:
    create default
```

or:

```text
ensure_*_state()
```

or:

```text
initialise_*()
```

Determine whether it operates on:

```text
canonical state
```

or:

```text
page/widget state
```

Page-level initialisation must not reset existing canonical configuration.

---

# 58. State Inventory Required in Completion Report

Before/after implementation, report the state architecture.

Include a table conceptually like:

| State | Canonical? | Derived? | UI-only? | Owner |
|---|---|---|---|---|
| Project config | Yes | No | No | ProjectState |
| Storage config | Yes | No | No | ProjectState |
| Storage result | No | Yes | No | ProjectState results |
| Compute config | Yes | No | No | ProjectState |
| Transfer config | Yes | No | No | ProjectState |
| Transfer throughput widget | No | No | Yes | Streamlit UI |
| Module status | No | Yes | No | status function |

Use actual implementation names.

---

# 59. Automated State Tests Are Mandatory

Do not rely only on calculation-unit tests.

Create tests specifically for application state transitions.

These tests should operate below the browser level where practical.

Model:

```text
initialise project
edit config
destroy widget/page UI state
rehydrate page
assert canonical config unchanged
```

---

# 60. Test Widget Destruction Explicitly

Where possible, simulate Streamlit widget cleanup.

For example:

```text
canonical throughput = 777
widget throughput = 777

remove widget key

render/hydrate Transfer

canonical throughput = 777
widget throughput = 777
```

Do this for all historically failing fields.

---

# 61. Mandatory Test — Demo Persistence

Automate:

```text
create fresh state
load 500-sample demo
destroy Storage widget keys
render/hydrate Compute
destroy Compute widget keys
render/hydrate Storage
```

Assert:

```text
samples == 500
retention == demo retention
all demo Storage config unchanged
```

---

# 62. Mandatory Test — Manual Storage Persistence

Use distinctive values such as:

```text
samples = 437
retention = 4.25
```

and distinctive values for other editable fields.

Destroy/recreate page UI state.

Assert exact persistence.

---

# 63. Mandatory Test — Compute Persistence

Use:

```text
alignment = 7
deepvariant = 13
scratch = 333
```

Destroy/recreate Compute UI state.

Assert exact persistence.

---

# 64. Mandatory Test — Transfer Persistence

Use:

```text
throughput = 777
RTT = 137
source location = distinctive
destination location = distinctive
note = distinctive
```

Destroy/recreate Transfer UI state.

Assert exact persistence.

---

# 65. Mandatory Test — Conditional Transfer State

Set:

```text
Measured = 777
```

switch mode away and back.

Assert:

```text
777
```

remains canonical.

Set:

```text
RTT enabled
RTT = 137
```

toggle off/on.

Assert canonical RTT behaviour matches the intended retention policy.

Preferred:

```text
137
```

retained.

---

# 66. Mandatory Test — Render Idempotence

For every page:

```text
state_before = deep copy canonical ProjectState

render page without user edit

state_after = canonical ProjectState
```

Assert no project configuration mutation.

Where testing Streamlit rendering directly is impractical, test the page state-initialisation/hydration functions independently.

---

# 67. Mandatory Test — Immediate Invalidation

Create fully current 500-sample state.

Change:

```text
samples = 1000
```

Without invoking Compute or Transfer page logic, assert:

```text
Storage = Complete
Compute = Needs review
Transfer = Needs review
```

This test is essential.

---

# 68. Mandatory Test — Visiting Pages Does Not Discover Staleness

After the previous test:

```text
status_before_visiting_compute
```

must already be:

```text
Compute = Needs review
Transfer = Needs review
```

Then render Compute.

Transfer must remain:

```text
Needs review
```

but it must not transition from Complete to Needs review merely because Compute was rendered.

---

# 69. Mandatory Test — Compute Isolation

With current modules:

```text
alignment workers
7 → 8
```

assert:

```text
Storage current
Compute updated/stale as appropriate during calculation
Transfer current
```

Do not invalidate unrelated modules.

---

# 70. Mandatory Test — Transfer Isolation

Change:

```text
777 → 888 Mbps
```

assert:

```text
Storage current
Compute current
Transfer updated
```

---

# 71. Mandatory Test — Summary Read-Only

Take deep copy:

```text
state_before
```

render/calculate Summary presentation.

Then:

```text
state_after
```

Canonical configuration must be unchanged.

---

# 72. Mandatory Test — No Mixed Revisions

Create:

```text
Storage current for 1000
Compute stale from 500
Transfer stale from 500
```

Summary must not present all three as current.

Assert module statuses and current-result filtering.

---

# 73. Browser-Level Deployment Gate

Automated tests are necessary but not sufficient.

After deployment, perform a fresh read-only browser review.

The browser test must begin with the simplest known failure.

---

# 74. Browser Gate A — Demo Persistence

Fresh session:

```text
Storage
→ load/select 500-sample demo
→ confirm 500
→ Compute
→ Storage
```

Expected:

```text
500
```

If Storage resets:

```text
FAIL
```

Stop the deployment review.

Do not proceed.

---

# 75. Browser Gate B — Storage Round Trip

With 500-sample demo loaded:

```text
Storage
→ Compute
→ Transfer
→ Project Summary
→ Storage
```

Verify every Storage field remains configured.

---

# 76. Browser Gate C — Compute Round Trip

Configure:

```text
7 / 13 / 333
```

Navigate through other pages and back.

Expected:

```text
7 / 13 / 333
```

---

# 77. Browser Gate D — Transfer Round Trip

Configure:

```text
FASTQ
777 Mbps
137 ms
source location
destination location
note
Globus
```

Navigate through every page and back.

Expected:

```text
all exact values retained
```

If:

```text
777 → 0
```

or any location/note/RTT disappears:

```text
FAIL
```

---

# 78. Browser Gate E — Immediate Dependency Status

With all modules Complete at 500 samples:

```text
Storage
500 → 1000
```

Before opening another module, inspect status.

Expected:

```text
Storage       Complete
Compute       Needs review
Transfer      Needs review
```

If either downstream module still says Complete:

```text
FAIL
```

---

# 79. Browser Gate F — Recalculate Compute

Visit Compute.

Verify:

```text
7 / 13 / 333
```

remain.

Recalculate/review.

Expected approximately:

```text
831.74 h
```

Then:

```text
Storage       Complete
Compute       Complete
Transfer      Needs review
```

---

# 80. Browser Gate G — Recalculate Transfer

Visit Transfer.

Verify retained:

```text
FASTQ
777 Mbps
137 ms
locations
note
Globus
```

Recalculate.

Expected:

```text
Transfer
Complete
```

---

# 81. Browser Gate H — Isolation

Change:

```text
alignment
7 → 8
```

Verify unrelated modules remain current.

Then change:

```text
throughput
777 → 888
```

Verify Storage and Compute remain current.

---

# 82. Browser Gate I — Summary

Verify:

- project identity correct;
- module statuses consistent;
- no stale result presented as current;
- Storage lifecycle present;
- workflow egress present;
- Engineering present;
- Current included total present;
- explicit Transfer provider charge separate;
- configured project warning absent.

---

# 83. Browser Gate J — Direct Summary

Fresh session:

```text
/project-summary
```

must:

- load without crash;
- show fresh/default project appropriately;
- show Compute/Transfer Not configured where appropriate;
- not mutate project merely because Summary was opened.

---

# 84. No Visual Redesign

013 is not a visual iteration.

Preserve:

- CBIO header;
- Genomics Infrastructure Cost Planner title;
- native top navigation;
- GRO styling;
- guided flow;
- Continue actions;
- tables;
- Summary layout;
- responsive behaviour.

Only make UI changes required to support correct state behaviour.

---

# 85. No New Features

Do not add:

- saved projects;
- database persistence;
- browser local storage;
- user accounts;
- authentication;
- multi-user collaboration;
- project history;
- cloud persistence;
- shareable project links;
- multi-project management.

This is still one project per Streamlit session.

---

# 86. No Deeper Compute Work

Do not implement in 013:

- AWS EC2 instance selection;
- AWS compute pricing;
- Spot modelling;
- EBS costing;
- AWS Batch;
- Nextflow deployment;
- HPC monetary costing;
- Sentieon runtime;
- DRAGEN/ICA costing;
- GLnexus benchmark;
- new DeepVariant benchmark;
- new BWA benchmark;
- workflow pipelining;
- measured scratch benchmarking.

Those resume only after canonical state is reliable.

---

# 87. No New Transfer Work

Do not add:

- multi-leg transfers;
- transfer execution;
- Globus integration;
- S3 upload execution;
- endpoint discovery;
- automatic bandwidth tests;
- new provider pricing.

Fix state only.

---

# 88. Documentation

Update:

```text
docs/design-and-assumptions.md
```

to describe the final state architecture.

Document:

- one canonical ProjectState;
- configuration versus derived results;
- ephemeral widget state;
- hydration/update pattern;
- project/demo loading;
- dependency revisions;
- derived module statuses;
- Summary read-only behaviour;
- module dependency isolation.

Do not turn the document into implementation history.

The 012-series history already documents how we arrived here.

---

# 89. README

Update README only if necessary to reflect:

- application flow;
- current architecture;
- test commands.

Do not add lengthy state-debug history.

---

# 90. Preserve Existing Instruction History

Do not delete:

```text
012
012a
012c
012d
```

documentation/instruction files if they are currently kept as implementation history.

013 supersedes their state-management implementation where necessary, but the historical instructions remain useful context.

---

# 91. Code Quality

Prefer:

- explicit state ownership;
- typed models;
- pure status functions;
- pure dependency calculations;
- small hydration helpers;
- deterministic transitions;
- minimal callbacks;
- testable functions.

Avoid:

- implicit widget synchronization;
- page-specific hidden state;
- duplicated booleans;
- large callback webs;
- global reset helpers;
- defensive defaulting that overwrites valid state.

---

# 92. State Transition Functions

Where helpful, introduce explicit operations such as:

```text
create_default_project()
load_project_profile(...)
update_project_config(...)
update_storage_config(...)
update_compute_config(...)
update_transfer_config(...)
calculate_storage(...)
calculate_compute(...)
calculate_transfer(...)
get_module_status(...)
```

These names are illustrative.

Use the repository's conventions.

The important point is that state transitions should be explicit and testable outside Streamlit page rendering.

---

# 93. Avoid Overengineering

This is still a relatively small Streamlit application.

Do not build:

- Redux;
- event sourcing;
- CQRS;
- a state database;
- a generic workflow engine;
- a complex dependency framework.

A clean typed canonical object plus explicit transition functions is sufficient.

---

# 94. Migration Strategy

Because this is a significant state refactor, implement carefully.

Recommended sequence:

```text
1. inspect current state architecture
2. inventory state owners
3. define canonical ProjectState
4. migrate project/shared configuration
5. migrate Storage configuration
6. migrate Compute configuration
7. migrate Transfer configuration
8. migrate results
9. centralise status/dependency logic
10. migrate Summary
11. migrate exports
12. remove obsolete state machinery
13. run unit/state tests
14. run numerical regressions
15. deploy
16. perform browser acceptance gate
```

Do not leave both old and new state systems indefinitely.

---

# 95. Temporary Compatibility

If temporary adapters are needed during implementation, that is acceptable.

But before completion:

- identify them;
- remove obsolete ones;
- ensure there is still only one canonical source of truth.

Do not mark 013 complete with two parallel project-state architectures.

---

# 96. Acceptance Criteria — Architecture

013 is complete only when:

1. one canonical ProjectState exists;
2. project configuration has one canonical owner;
3. Storage configuration has one canonical owner;
4. Compute configuration has one canonical owner;
5. Transfer configuration has one canonical owner;
6. results are separated from configuration;
7. widget state is explicitly UI-only;
8. widget deletion cannot destroy canonical project values;
9. page rendering without edits does not mutate project configuration;
10. Summary is read-only with respect to configuration;
11. module status is derived from canonical state/result validity;
12. page visits are not required to discover stale results.

---

# 97. Acceptance Criteria — Persistence

13. 500-sample demo survives Storage→Compute→Storage.
14. manually configured Storage survives navigation.
15. all Storage fields survive full round trip.
16. all Compute fields survive full round trip.
17. all Transfer fields survive full round trip.
18. 777 Mbps survives.
19. 137 ms survives.
20. source location survives.
21. destination location survives.
22. note survives.
23. conditional Transfer mode changes do not erase canonical values.
24. configured-project state survives navigation.

---

# 98. Acceptance Criteria — Dependencies

25. 500→1000 immediately marks Compute Needs review.
26. 500→1000 immediately marks Transfer Needs review.
27. this happens before visiting Compute or Transfer.
28. visiting Compute does not create Transfer staleness.
29. Compute config survives staleness.
30. Transfer config survives staleness.
31. Compute recalculation returns Compute to Complete.
32. Transfer remains Needs review until recalculated.
33. Transfer recalculation returns Transfer to Complete.
34. Compute-only edits do not invalidate unrelated modules.
35. Transfer-only edits do not invalidate unrelated modules.

---

# 99. Acceptance Criteria — Regression

36. 500-sample Storage calculation remains unchanged.
37. 500-sample Compute calculation remains unchanged.
38. 500-sample Transfer calculation remains unchanged.
39. 1000-sample Storage calculation remains unchanged.
40. 1000-sample Compute calculation remains unchanged.
41. Summary financial structure remains unchanged.
42. explicit Transfer charge remains separate.
43. stale results are never presented as current.
44. exports reflect canonical state.
45. direct `/project-summary` works.
46. no page crashes.
47. existing relevant tests pass.
48. new state-transition tests pass.
49. deployed browser gate passes.

---

# 100. Stop Conditions During Implementation

If the simplest test:

```text
500 demo
→ Compute
→ Storage
```

still resets Storage, do not proceed to polishing other behaviour.

Fix canonical ownership first.

Likewise, if:

```text
500 → 1000
```

still requires visiting Compute before Compute becomes Needs review, do not patch the progress UI.

Fix dependency/status derivation first.

---

# 101. Completion Gate

Do not mark 013 complete based solely on:

- code review;
- unit tests;
- screenshots;
- individual page behaviour.

It must pass a fresh deployed browser review.

The two most important browser assertions are:

```text
500 demo
→ Compute
→ Storage
→ still 500
```

and:

```text
500 complete project
→ change to 1000 on Storage
→ without visiting anything else:

Compute = Needs review
Transfer = Needs review
```

If either fails:

```text
013 = NOT COMPLETE
```

---

# 102. Required Completion Report

After implementation provide:

## Architecture

1. files modified;
2. previous state architecture summary;
3. identified duplicate sources of truth;
4. obsolete state machinery removed;
5. final ProjectState structure;
6. canonical owner of each configuration domain;
7. configuration/result separation;
8. widget-state strategy;
9. hydration strategy;
10. user-edit synchronization strategy;
11. demo/profile loading strategy;
12. project configured-state strategy.

## Dependencies

13. revision/dependency mechanism;
14. module-status function;
15. dependency graph;
16. immediate 500→1000 invalidation behaviour;
17. module-isolation behaviour.

## Testing

18. state-transition tests added;
19. widget-destruction tests added;
20. render-idempotence tests;
21. demo-persistence test;
22. Storage persistence test;
23. Compute persistence test;
24. Transfer persistence test;
25. conditional-widget test;
26. immediate-invalidation test;
27. Summary read-only test;
28. export-state test;
29. full existing test-suite result.

## Regression

30. 500-sample numerical results;
31. 1000-sample numerical results;
32. Summary financial regression;
33. any calculation differences and explanation.

## Deployment

34. deployed browser Gate A result;
35. deployed Storage round-trip result;
36. deployed Compute round-trip result;
37. deployed Transfer round-trip result;
38. deployed immediate-invalidation result;
39. deployed module-isolation result;
40. direct Summary result.

## Final status

41. remaining known correctness issues, if any;
42. whether 013 can be formally closed.

If any mandatory acceptance criterion fails, report:

```text
013 NOT COMPLETE
```

Do not describe partial implementation as complete.

---

# 103. Milestone After 013

Only after 013 passes the deployed completion gate should the project-state milestone be considered closed.

At that point:

```text
012   Transfer model
012a  Initial project-state work
012c  Project-flow closure attempt
012d  Transfer-state closure attempt
013   Canonical project-state architecture
```

can be treated as the completed foundation.

Then resume deeper Compute modelling, including the previously deferred work around:

- AWS execution architecture;
- EC2 instance selection;
- af-south-1 compute pricing;
- On-Demand versus Spot;
- working-storage costs;
- HPC execution modelling;
- Sentieon;
- DRAGEN / ICA;
- GLnexus;
- additional measured benchmarks.

Do not begin those changes as part of 013.

---

## Final Principle

The implementation should be understandable through one simple rule:

> The project exists independently of the page currently being viewed.

Storage, Compute, Transfer and Project Summary are four views onto the same project.

Leaving a page must never mean leaving its data behind.