# 012d — Transfer State and Dependency Final Closure

## Objective

Close the remaining project-state defects identified during the deployed review after 012c.

This is a **correctness-only closure iteration**.

Do not add features.

Do not redesign the UI.

Do not change Storage, Compute or Transfer calculation logic.

Do not change pricing.

Do not add deeper Compute functionality.

The purpose of 012d is to fix two remaining architectural defects:

1. several Transfer fields are still owned by transient Streamlit widget state rather than the canonical Transfer configuration;
2. module completion/status can remain `Complete` after an upstream project change has made the stored result stale.

The central rules remain:

> Streamlit widgets are views onto canonical project state. They are not the project state.

and:

> A module is Complete only when its current configuration is valid, its current result is valid, and that result was calculated against the current dependencies.

---

# 1. Current Deployed State

The deployed application already has substantial 012a/012c functionality working.

Preserve all of the following:

- Storage configuration persists across page navigation.
- Compute configuration persists across page navigation.
- project identity is shared consistently.
- Transfer no longer crashes when returning to the page.
- configured projects no longer incorrectly display the minimum/default-project warning.
- guided workflow/status UI exists.
- Continue actions exist.
- Project Summary financial structure is correct.
- explicit Transfer-plan charges remain separate from Storage workflow-egress cost.
- direct `/project-summary` works.
- module-specific changes generally do not invalidate unrelated modules.
- stale Transfer results are removed from Summary when Transfer becomes invalid.

Do not regress these behaviours.

---

# 2. Remaining Blocking Defects

The deployed 012c review reproduced the following.

A project was configured as:

```text
Example WGS Project
WGS 30×
500 samples
5 years
```

Compute:

```text
Alignment workers
7

DeepVariant workers
13

Scratch
333 GiB/worker
```

Transfer included:

```text
Dataset
FASTQ

Measured throughput
777 Mbps

RTT enabled
137 ms

distinctive source location
distinctive destination location
distinctive note
```

After:

```text
Storage
→ Compute
→ Transfer
→ Project Summary
→ Storage
→ Compute
→ Transfer
```

some Transfer fields persisted while others did not.

### Persisted

```text
dataset
source endpoint
destination endpoint
throughput basis/mode
transfer method
RTT enabled/disabled
```

### Lost/reset

```text
measured throughput
777 → 0.00 Mbps

RTT
137 → 0.00 ms

source location
lost

destination location
lost

note
lost
```

This caused:

```text
Measured throughput must be greater than zero
```

Transfer then correctly became Invalid.

This persistence defect is the primary blocker.

---

# 3. Second Blocking Defect — Dependency Status

After changing:

```text
Samples
500 → 1000
```

Storage correctly recalculated.

However, the flow/status indicator still showed:

```text
Compute
Complete
```

instead of:

```text
Compute
Needs review
```

before Compute was revisited/recalculated.

This means module status is not consistently derived from result dependency validity.

Fix this centrally rather than patching the Storage page.

---

# 4. No More Individual Transfer Field Patches

Do not fix only:

```text
measured_throughput
```

or only the fields observed during the deployed review.

Audit **every editable Transfer field**.

For every field determine:

1. widget key;
2. canonical configuration field;
3. initial/default source;
4. widget hydration path;
5. widget → canonical-state update path;
6. validation behaviour;
7. dependency relevance;
8. export path;
9. round-trip test coverage.

The implementation is incomplete until every editable Transfer field has been accounted for.

---

# 5. Required Transfer State Audit

Before changing code, inspect the current Transfer implementation and construct an internal audit equivalent to:

| Transfer field | Widget key | Canonical field | Hydrates from canonical state | Writes to canonical state | Round-trip tested |
|---|---|---|---|---|---|
| Dataset | ... | ... | Yes/No | Yes/No | Yes/No |
| Source endpoint | ... | ... | ... | ... | ... |
| Source location | ... | ... | ... | ... | ... |
| Destination endpoint | ... | ... | ... | ... | ... |
| Destination location | ... | ... | ... | ... | ... |
| Throughput mode | ... | ... | ... | ... | ... |
| Measured throughput | ... | ... | ... | ... | ... |
| Link capacity | ... | ... | ... | ... | ... |
| Efficiency | ... | ... | ... | ... | ... |
| Transfer method | ... | ... | ... | ... | ... |
| RTT enabled | ... | ... | ... | ... | ... |
| RTT value | ... | ... | ... | ... | ... |
| Note | ... | ... | ... | ... | ... |

Use the actual current fields.

Do not invent fields solely to satisfy this table.

Include the completed audit in the implementation report.

---

# 6. One Canonical Transfer Configuration

There must be one durable Transfer configuration model.

Conceptually:

```text
TransferConfig
│
├── dataset
├── custom_dataset_*
│
├── source_endpoint
├── source_location
│
├── destination_endpoint
├── destination_location
│
├── throughput_mode
├── measured_throughput_mbps
├── link_capacity_*
├── efficiency
│
├── transfer_method
│
├── rtt_enabled
├── rtt_ms
│
└── note
```

The exact field names should follow the existing implementation.

Do not create a second competing Transfer configuration object.

---

# 7. Canonical State Must Survive Widget Destruction

Assume Streamlit may remove widget-associated session keys when their widgets are not rendered.

The application must remain correct under that assumption.

Therefore:

```text
Transfer widget disappears
        ↓
widget key disappears
        ↓
canonical TransferConfig remains intact
        ↓
Transfer page rendered again
        ↓
widget recreated from TransferConfig
```

This lifecycle must work for every Transfer field.

---

# 8. Widget Hydration

When Transfer renders, widget values must be hydrated from canonical Transfer configuration.

Conceptually:

```python
canonical_value = transfer_config.measured_throughput_mbps

if widget_key not in st.session_state:
    st.session_state[widget_key] = canonical_value
```

or another correct Streamlit pattern.

The exact implementation is flexible.

The requirement is not.

A missing widget key must never cause a configured canonical value such as:

```text
777 Mbps
```

to become:

```text
0 Mbps
```

---

# 9. Widget Update Path

When the user changes a Transfer widget:

```text
widget
  ↓
validate
  ↓
canonical TransferConfig
  ↓
calculation
  ↓
TransferResult
```

The canonical config must be updated deliberately.

Do not rely on the continued existence of the widget key as persistence.

---

# 10. Do Not Use Defaults as Persistence

Defaults such as:

```text
0.00 Mbps
0.00 ms
blank location
blank note
```

are initial UI values only.

They are not valid fallback values for an already configured Transfer plan.

If canonical state contains:

```text
777 Mbps
137 ms
Cape Town
AWS Cape Town
Test note
```

those values must be restored.

---

# 11. Optional Fields Are Still State

Do not treat optional fields as disposable.

The following types of fields must persist if the user entered them:

```text
location
RTT
notes
custom endpoint labels
custom dataset metadata
```

Optional means:

> the user does not have to provide it.

It does not mean:

> the application may forget it.

---

# 12. Hidden Conditional Widgets

Pay particular attention to widgets rendered conditionally.

Examples:

```text
Measured throughput field
only visible when throughput mode = Measured
```

or:

```text
RTT value
only visible when RTT enabled = True
```

or:

```text
custom endpoint fields
only visible for Custom endpoint
```

These are especially vulnerable to Streamlit widget cleanup.

Their canonical values must survive temporary non-rendering.

Example:

```text
RTT enabled
True

RTT
137 ms
```

Navigate away.

Return.

Expected:

```text
RTT enabled
True

RTT
137 ms
```

not:

```text
True
0 ms
```

---

# 13. Switching Transfer Modes

Also test temporary conditional hiding within the Transfer page.

Example:

```text
Measured throughput
777 Mbps
```

Then switch:

```text
Measured
→ Known capacity
```

Then switch back:

```text
Known capacity
→ Measured
```

The intended behaviour should be explicit.

Preferred behaviour:

```text
Measured throughput
777 Mbps
```

is retained unless the user explicitly resets/replaces it.

Likewise for known-capacity settings.

Do not silently erase inactive mode configuration.

---

# 14. Transfer Validation

Validation must operate on canonical configuration/current widget values without destroying previous valid configuration unnecessarily.

For example:

```text
Measured throughput
0
```

may produce:

```text
Invalid
```

but must not erase:

```text
source
destination
locations
method
RTT
note
```

When the user restores:

```text
777 Mbps
```

Transfer should recover normally.

---

# 15. Transfer Result Validity

A Transfer result is current only when:

```text
Transfer configuration valid
AND
Transfer result exists
AND
result dependencies match current project state
```

If any condition is false, Transfer cannot be `Complete`.

---

# 16. Central Module Status Function

Audit the existing status implementation.

Do not allow each page to independently decide whether a module is:

```text
Complete
Needs review
Invalid
Not configured
```

Create or consolidate one shared status mechanism.

Conceptually:

```python
get_module_status(
    module_config,
    module_result,
    current_dependencies,
    result_dependencies,
)
```

or equivalent.

Storage, Compute, Transfer, Project Summary and progress indicators should consume the same status source.

---

# 17. Status Semantics

Use consistent semantics.

## Not configured

The module has not yet been configured sufficiently to produce an intentional result.

## Complete

The module:

- has valid current configuration;
- has a valid current result;
- result dependencies match current project dependencies.

## Needs review

The module has retained configuration, but an upstream dependency changed after its last valid calculation.

Example:

```text
500 samples
→
1000 samples
```

with old Compute/Transfer results.

## Invalid

Current module configuration fails validation.

Example:

```text
Measured throughput
0 Mbps
```

No module with current status:

```text
Invalid
```

may simultaneously appear as:

```text
Complete
```

elsewhere.

---

# 18. Dependency Signature or Revision

Use the existing dependency/revision mechanism if present.

Do not invent a parallel mechanism unnecessarily.

A module result should have enough metadata to determine whether it corresponds to the current dependencies.

Conceptually:

```text
ComputeResult
project_dependency_signature = ABC123
```

Current project:

```text
project_dependency_signature = DEF456
```

Therefore:

```text
Compute = Needs review
```

Exact implementation may instead use revisions or structured hashes.

---

# 19. Sample Count Dependency

Sample count is a shared upstream dependency.

Changing:

```text
500 → 1000
```

must immediately cause dependent module status to become:

```text
Compute
Needs review

Transfer
Needs review
```

unless those modules are automatically and safely recalculated at the same time.

Do not continue displaying:

```text
Complete
```

against results calculated for 500 samples.

---

# 20. Dataset Dependency

If Storage/shared project changes alter the WGS dataset volumes used by Transfer, Transfer must become:

```text
Needs review
```

until recalculated.

Its configuration must remain intact.

For example:

```text
FASTQ
Measured
777 Mbps
137 ms
```

must remain configured even though its previous duration is stale.

---

# 21. Compute Configuration Must Survive Staleness

Preserve the working 012a behaviour.

After:

```text
500 → 1000 samples
```

Compute should become:

```text
Needs review
```

but retain:

```text
Alignment workers
7

DeepVariant workers
13

Scratch
333 GiB
```

When Compute is revisited, recalculate using those retained settings.

The deployed review observed approximately:

```text
831.74 h
```

for the reviewed configuration.

Do not alter the calculation model.

---

# 22. Transfer Configuration Must Survive Staleness

Likewise after:

```text
500 → 1000 samples
```

Transfer should become:

```text
Needs review
```

while retaining:

```text
Dataset
FASTQ

Throughput mode
Measured

Measured throughput
777 Mbps

RTT
137 ms

locations
method
note
```

When Transfer is revisited, recalculate against the new 1000-sample data volume.

---

# 23. Module-Specific Dependency Isolation

Preserve correct isolation.

## Compute-only change

Example:

```text
Alignment workers
7 → 8
```

Expected:

```text
Compute
recalculated/current

Storage
Complete

Transfer
unchanged/current if its dependencies did not change
```

## Transfer-only change

Example:

```text
Measured throughput
777 → 888 Mbps
```

Expected:

```text
Transfer
recalculated/current

Storage
Complete

Compute
Complete
```

Do not globally invalidate all modules for every edit.

---

# 24. Progress Indicator Must Use Central Status

The guided flow indicator must not maintain its own stale copy of status.

For example, after:

```text
500 → 1000
```

if central state says:

```text
Compute
Needs review
```

then every place showing Compute status must show:

```text
Needs review
```

including:

- Storage page flow indicator;
- Compute page flow indicator;
- Transfer page flow indicator;
- Project Summary.

No page-specific status divergence.

---

# 25. Summary Must Use the Same Status

Project Summary must consume the same canonical module-status mechanism.

Do not separately infer status from whether a stored result object exists.

A result object may exist but be stale.

Therefore:

```text
result exists
```

does not imply:

```text
Complete
```

---

# 26. Preserve Summary Stale-Result Safety

The deployed application correctly stopped showing the old Transfer result after Transfer became Invalid.

Preserve this behaviour.

Similarly, stale Compute/Transfer results must not appear as current authoritative values.

They may optionally be described as needing review, but do not present them as current project estimates.

---

# 27. No New UI Work

012d is not a visual iteration.

Do not:

- redesign the progress component;
- change typography;
- change colours;
- move navigation;
- add cards;
- add icons;
- alter the CBIO header;
- add new guidance panels;
- redesign Project Summary;
- change responsive layout unless required to fix a correctness regression.

The existing guided flow and Continue actions are sufficient.

Focus only on state correctness.

---

# 28. No Calculation Changes

Do not change:

- WGS file-size defaults;
- Storage lifecycle formulas;
- workflow-egress formulas;
- engineering formulas;
- Compute runtime formulas;
- concurrency formulas;
- scratch formulas;
- Transfer duration formulas;
- RTT/BDP formulas;
- AWS pricing;
- FX assumptions;
- VAT logic.

This iteration should produce the same numbers from the same valid inputs.

---

# 29. Baseline Regression — 500 Samples

Use:

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

Expected Storage approximately:

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

Compute:

```text
Alignment workers
7

DeepVariant workers
13

Scratch
333 GiB/worker
```

Expected approximately:

```text
Sequential-stage estimate
419.04 h

Alignment peak
2,331 GiB

DeepVariant peak
4,329 GiB

Overall peak
4,329 GiB
```

Transfer:

```text
Dataset
FASTQ

Throughput
777 Mbps
```

Expected approximately:

```text
Volume
48.83 TB

Duration
153.5 h

AWS ingress
US$0
```

Use exact internal values for automated tests.

---

# 30. Full Distinctive Transfer Configuration Test

Configure every currently supported editable Transfer field with a distinctive non-default value.

For example, where supported:

```text
Dataset
FASTQ

Source endpoint
Institutional/local storage

Source location
Cape Town test location

Destination endpoint
AWS S3

Destination location
AWS Cape Town test location

Throughput mode
Measured

Measured throughput
777 Mbps

Transfer method
Globus

RTT enabled
True

RTT
137 ms

Note
012d persistence test
```

Use actual valid options from the implementation.

Do not add fields merely for this test.

---

# 31. Full Round-Trip Test

After configuring the distinctive Transfer state, navigate:

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

Then again:

```text
Transfer
→ Storage
→ Project Summary
→ Compute
→ Transfer
```

Every Transfer field must retain exactly the configured value.

Specifically verify:

```text
777 Mbps
137 ms
source location
destination location
note
```

These are mandatory regression checks because they failed in deployed 012c.

---

# 32. Conditional Widget Test

Test within Transfer:

```text
Measured = 777 Mbps
```

Switch to another throughput mode.

Then return to:

```text
Measured
```

Verify:

```text
777 Mbps
```

remains available.

Likewise test RTT:

```text
RTT enabled
137 ms
```

disable RTT temporarily, then re-enable it.

Preferred result:

```text
137 ms
```

is restored.

Document actual intended behaviour in the implementation report.

---

# 33. 500 → 1000 Dependency Test

Starting from the valid 500-sample project:

```text
Storage       Complete
Compute       Complete
Transfer      Complete
```

change:

```text
Samples
500 → 1000
```

Immediately inspect the flow indicator **before visiting Compute or Transfer**.

Expected:

```text
Storage       Complete
Compute       Needs review
Transfer      Needs review
```

This exact timing matters.

The old Compute/Transfer results must not still be classified as Complete.

---

# 34. Revisit Compute After Invalidation

Navigate to Compute.

Verify configuration remains:

```text
Alignment workers
7

DeepVariant workers
13

Scratch
333 GiB
```

Recalculate/review.

Expected approximately:

```text
831.74 h
```

under the currently deployed calculation model.

Compute should then return to:

```text
Complete
```

---

# 35. Transfer Must Remain Needs Review

After Compute is recalculated, Transfer should remain:

```text
Needs review
```

unless Transfer itself was recalculated.

Do not make Transfer Complete simply because Compute was reviewed.

---

# 36. Revisit Transfer After Invalidation

Navigate to Transfer.

Before changing anything, verify retained configuration:

```text
FASTQ
Measured
777 Mbps
137 ms
source location
destination location
method
note
```

Then allow Transfer to recalculate/review against the 1000-sample project.

Transfer should then become:

```text
Complete
```

with the new duration.

---

# 37. 1000-Sample Storage Regression

Preserve the currently observed Storage results approximately:

```text
Durable data
146.5 TB

Provisioned envelope
175.8 TB

Current included total
R1,289,918
```

Summary approximately:

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

Do not alter these calculations in 012d.

---

# 38. Compute-Only Isolation Test

With all modules current, change:

```text
Alignment workers
7 → 8
```

The deployed application previously produced approximately:

```text
738.18 h
```

Preserve existing logic.

Verify:

```text
Storage
Complete

Compute
Complete after recalculation

Transfer
Complete
```

provided Transfer dependencies did not change.

---

# 39. Transfer-Only Isolation Test

Then change:

```text
Measured throughput
777 → 888 Mbps
```

The deployed review previously observed approximately:

```text
268.7 h
```

for the 1000-sample FASTQ transfer.

Verify:

```text
Storage
Complete

Compute
Complete

Transfer
Complete
```

after Transfer recalculation.

---

# 40. Status Consistency Test

At every stage compare module status across:

- Storage flow indicator;
- Compute flow indicator;
- Transfer flow indicator;
- Project Summary.

For a given canonical state, the same module must have the same status everywhere.

No example such as:

```text
Storage page:
Compute = Complete
```

while:

```text
Summary:
Compute = Needs review
```

is acceptable.

---

# 41. Transfer Export Regression

After the full navigation round trip, export Transfer configuration.

Verify the export contains the canonical values, including where applicable:

```text
dataset
source endpoint
source location
destination endpoint
destination location
throughput mode
777 Mbps
transfer method
RTT enabled
137 ms
note
```

Exports must not depend on transient widget keys.

---

# 42. State Reset Audit

Search the Transfer implementation for code patterns that may reset canonical values when widgets are absent.

Examples to inspect:

```python
st.session_state.get(key, 0)
```

```python
if key not in st.session_state:
    value = 0
```

```python
config.field = st.session_state.get(widget_key, default)
```

and any bulk initialisation/reset helper.

A missing widget key must not overwrite a valid canonical field with a default.

This is especially important.

The bug may not only be failed hydration.

It may also be:

> missing widget key → default value → default written back into canonical config.

Identify which is happening.

---

# 43. Callback Audit

Inspect any:

```text
on_change
callback
sync
hydrate
initialise
reset
```

functions used by Transfer.

Ensure callbacks:

- update canonical config from real user edits;
- do not fire during hydration in a way that replaces canonical values with defaults;
- do not depend on widgets from another page still existing.

Avoid callback loops.

---

# 44. Session-State Namespace Audit

Check whether canonical project/configuration keys and widget keys are clearly separated.

For example, conceptually:

```text
project_state.transfer.config.measured_throughput
```

versus:

```text
widget_transfer_measured_throughput
```

Do not reuse one key for both purposes if Streamlit widget lifecycle can remove it.

The implementation does not have to use these exact names.

The separation must be architectural.

---

# 45. Automated Test Strategy

Do not rely only on pure calculation tests.

Add state-transition tests that model:

```text
render page
edit widget
persist canonical config
leave page
widget keys disappear
return page
rehydrate widgets
```

Where practical, explicitly simulate removal of Transfer widget keys between renders.

This is important because the defect only appears after navigation.

---

# 46. Mandatory Automated Regression

At minimum automate:

### Test A — measured throughput

```text
777 Mbps
```

survives widget-key removal and rehydration.

### Test B — RTT

```text
enabled
137 ms
```

survives widget-key removal and rehydration.

### Test C — locations

Distinctive source/destination locations survive.

### Test D — note

Distinctive note survives.

### Test E — full Transfer config

All editable fields survive together.

### Test F — upstream invalidation

```text
500 → 1000
```

immediately changes Compute and Transfer:

```text
Complete → Needs review
```

### Test G — module isolation

Compute-only edit does not invalidate Storage/Transfer.

### Test H — Transfer-only edit does not invalidate Storage/Compute.

### Test I — status consistency

All pages consume identical module status.

---

# 47. Existing Tests

Run the complete existing test suite.

Do not weaken existing assertions merely to make 012d pass.

If an existing test conflicts with the correct canonical-state architecture, explain why it was updated.

---

# 48. Documentation

Update:

```text
docs/design-and-assumptions.md
```

only where needed.

Ensure it accurately states:

- Transfer configuration is canonical and independent of widgets;
- optional and conditional Transfer fields persist;
- module status is centrally derived;
- Complete requires current dependency validity;
- upstream project changes create Needs review for dependent modules;
- module-specific edits do not invalidate unrelated modules.

Do not add implementation-debug history to the design document.

---

# 49. No 012e by Default

The intention is that 012d closes this architecture phase.

Do not create or propose another iteration during implementation merely for optional polish.

If all acceptance tests pass, report 012d complete.

If something still fails, report the exact remaining defect rather than broadening scope.

---

# 50. Explicitly Out of Scope

Do not implement:

- new Storage features;
- new Transfer features;
- multi-leg Transfer;
- transfer execution;
- Globus API integration;
- S3 execution;
- AWS EC2 costing;
- AWS instance selection;
- HPC monetary costing;
- Sentieon runtime modelling;
- DRAGEN/ICA costing;
- GLnexus costing;
- new DeepVariant benchmarking;
- new BWA benchmarking;
- new scratch benchmarks;
- workflow pipelining;
- saved projects across sessions;
- database persistence;
- authentication;
- collaboration;
- AI/LLM functionality;
- visual redesign.

---

# 51. Acceptance Criteria

012d is complete only when all of the following pass.

## Transfer persistence

1. Dataset persists.
2. Source endpoint persists.
3. Source location persists.
4. Destination endpoint persists.
5. Destination location persists.
6. Throughput mode persists.
7. Measured throughput persists.
8. Known-capacity settings persist.
9. Efficiency persists.
10. Transfer method persists.
11. RTT enabled state persists.
12. RTT numeric value persists.
13. Note persists.
14. Any other editable Transfer field found during audit persists.

## Widget lifecycle

15. Transfer values survive removal of widget keys.
16. Transfer values rehydrate from canonical config.
17. Missing widget keys never overwrite canonical config with defaults.
18. Conditional widgets retain their canonical values.

## Status

19. Complete means current valid result.
20. Invalid modules never appear Complete.
21. Stale modules show Needs review.
22. 500→1000 immediately marks Compute Needs review.
23. 500→1000 immediately marks Transfer Needs review.
24. Status is consistent across all pages.

## Isolation

25. Compute-only changes do not invalidate Storage.
26. Compute-only changes do not invalidate Transfer unless a true dependency exists.
27. Transfer-only changes do not invalidate Storage.
28. Transfer-only changes do not invalidate Compute.

## Regression

29. 500-sample Storage results remain unchanged.
30. 500-sample Compute results remain unchanged.
31. 500-sample Transfer results remain unchanged.
32. 1000-sample Storage results remain unchanged.
33. Summary finances remain unchanged.
34. Project Summary does not show stale results as current.
35. No page crashes.
36. Exports use canonical state.
37. Existing tests pass.
38. New state-transition tests pass.

---

# 52. Deployment Completion Gate

After implementation and deployment, perform a fresh read-only browser review.

Do not close 012d based only on unit tests.

## Step 1 — Configure project

```text
Example WGS Project
WGS 30×
500 samples
5 years
```

## Step 2 — Configure Compute

```text
Alignment workers
7

DeepVariant workers
13

Scratch
333 GiB/worker
```

## Step 3 — Configure Transfer

Use distinctive values for every supported field.

At minimum:

```text
Dataset
FASTQ

Throughput mode
Measured

Measured throughput
777 Mbps

RTT enabled
True

RTT
137 ms

Source location
distinctive non-default value

Destination location
distinctive non-default value

Note
012d persistence test
```

Configure endpoints/method as appropriate.

## Step 4 — Record baseline

Confirm approximately:

```text
Storage
73.2 TB durable
87.9 TB provisioned
72.7 TB workflow egress
R693,613 current included total

Compute
419.04 h
2,331 GiB alignment peak
4,329 GiB overall peak

Transfer
48.83 TB
777 Mbps
153.5 h
```

## Step 5 — Round trip

Navigate:

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

Verify every Transfer field exactly matches its configured value.

The following must specifically still exist:

```text
777 Mbps
137 ms
source location
destination location
note
```

If any resets, 012d fails.

## Step 6 — Upstream invalidation

Change:

```text
Samples
500 → 1000
```

Before revisiting Compute/Transfer verify:

```text
Storage       Complete
Compute       Needs review
Transfer      Needs review
```

If Compute or Transfer still says Complete, 012d fails.

## Step 7 — Revisit Compute

Verify:

```text
7
13
333 GiB
```

remain configured.

Recalculate/review.

Compute becomes Complete.

Transfer remains Needs review.

## Step 8 — Revisit Transfer

Verify:

```text
777 Mbps
137 ms
source location
destination location
note
```

remain configured.

Recalculate/review.

Transfer becomes Complete.

## Step 9 — Isolation

Change:

```text
Alignment workers
7 → 8
```

Verify Storage and Transfer remain current.

Then change:

```text
Transfer throughput
777 → 888 Mbps
```

Verify Storage and Compute remain current.

## Step 10 — Summary

Verify:

- module statuses are consistent;
- no stale values appear current;
- Storage lifecycle is present;
- planned workflow egress is present;
- Engineering is present;
- Current included total is present;
- explicit Transfer provider charge remains separate.

## Step 11 — Export

Export Transfer configuration after the navigation cycle.

Verify canonical distinctive values are present.

## Step 12 — Tests

Run the complete automated test suite.

Only after all twelve steps pass should the following milestone be marked closed:

```text
012     Transfer Model
012a    Project State
012c    Project Flow Closure
012d    Transfer State Final Closure
```

---

# 53. Required Completion Report

After implementation report:

1. files modified;
2. exact root cause of the Transfer state loss;
3. whether the failure was:
   - missing hydration;
   - default write-back;
   - callback behaviour;
   - widget cleanup;
   - or a combination;
4. complete Transfer state audit table;
5. canonical Transfer configuration structure;
6. widget-key versus canonical-key separation;
7. hydration mechanism;
8. update mechanism;
9. conditional-widget persistence behaviour;
10. central module-status implementation;
11. dependency-signature/revision mechanism;
12. 500→1000 status behaviour;
13. module-isolation behaviour;
14. state-transition tests added;
15. existing test-suite result;
16. deployed round-trip review result;
17. export verification;
18. documentation changes;
19. any remaining known correctness issue.

If any acceptance criterion remains unresolved, do not describe the milestone as complete.