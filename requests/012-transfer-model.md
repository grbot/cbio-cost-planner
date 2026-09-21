# 012 — Transfer Model and Initial Transfer Planner

## Objective

Implement the first functional **Transfer** module of the CBIO Genomics Infrastructure Cost Planner.

Storage and Compute now provide the first two parts of the infrastructure model:

```text
Storage
   ↓
Compute
   ↓
Transfer
   ↓
Project Summary
```

Transfer should answer:

> What data needs to move, between which endpoints, at what effective throughput, approximately how long will it take, and which transfer costs are currently known?

This first implementation must remain:

- deterministic;
- transparent;
- evidence-aware;
- editable;
- conservative about unknowns;
- independent from speculative network-performance claims.

Do not turn Transfer into a network simulator.

The user must be able to distinguish:

```text
dataset size
link capacity
measured throughput
planning throughput
transfer duration
provider transfer charges
```

These are different concepts and must not be conflated.

---

# 1. Preserve Existing Application Architecture

Retain:

```text
Storage
Compute
Transfer
Project Summary
```

Preserve all completed Storage and Compute behaviour.

Do not modify:

- Storage calculations;
- Storage lifecycle logic;
- Compute runtime calculations;
- Compute evidence;
- Compute working-storage calculations;
- Compute execution options;
- existing project/session-state architecture;
- navigation;
- branding.

Transfer must use the existing shared project state.

---

# 2. Transfer Is About Data Movement

The Transfer module models movement between infrastructure endpoints.

Examples:

```text
local institution → AWS S3
AWS S3 → Ilifu
Ilifu → AWS S3
sequencing centre → Ilifu
sequencing centre → AWS S3
AWS S3 → another object store
ICA → institutional storage
```

Transfer is not itself:

- durable storage;
- compute;
- workflow execution;
- network procurement;
- a data-transfer application.

It is a planning model.

---

# 3. Core Transfer Model

Represent a transfer with a reusable model similar conceptually to:

```python
TransferPlan(
    source=...,
    destination=...,
    dataset=...,
    size_gb=...,
    throughput_mode=...,
    throughput_mbps=...,
    transfer_method=...,
    provider_cost=...,
    evidence=...,
)
```

Exact implementation is flexible.

Keep calculation logic separate from Streamlit UI.

The model must support future multiple transfer legs.

---

# 4. Transfer Endpoints

Provide structured endpoint types.

Initial options should include:

```text
Institutional / local storage
Ilifu / HPC
AWS S3
Illumina ICA
Other object storage
Custom endpoint
```

Do not assume all institutional storage is Ilifu.

Do not assume all object storage is AWS.

For custom endpoints allow a short user-defined name.

---

# 5. Source and Destination

The user should explicitly select:

```text
Source
Destination
```

For example:

```text
Source       Institutional storage
Destination AWS S3
```

or:

```text
Source       AWS S3
Destination Ilifu / HPC
```

Prevent or warn about nonsensical identical source/destination selections.

Do not infer geography purely from endpoint type.

---

# 6. Dataset Selection

For WGS 30× projects, provide useful dataset presets derived from the shared project model.

For example:

```text
FASTQ
CRAM
gVCF / QC
All durable project data
Custom dataset
```

Using the existing WGS defaults:

```text
FASTQ          100 GB/sample
CRAM            40 GB/sample
gVCF/QC         10 GB/sample
```

For a project of `N` samples:

```text
FASTQ transfer size =
N × FASTQ GB/sample
```

etc.

Do not add Storage headroom automatically to a transfer unless the selected transfer explicitly represents that capacity.

Transfer actual expected data volume, not provisioned storage capacity.

---

# 7. Custom Dataset

Allow:

```text
Dataset name
Dataset size
Unit
```

Units:

```text
GB
TB
```

Use the existing calculator convention:

```text
1 TB = 1024 GB
```

Custom Project mode should use the datasets already defined in the shared project where practical.

Avoid duplicating dataset definitions unnecessarily.

---

# 8. Direction Matters

Transfer direction affects:

- provider charges;
- operational method;
- potentially network path.

For example:

```text
AWS → Ilifu
```

is not economically equivalent to:

```text
Ilifu → AWS
```

AWS ingress may have different charging behaviour from AWS internet egress.

Therefore source and destination must remain explicit in the model and exports.

---

# 9. Throughput Input Modes

Provide three throughput modes.

## Mode A — Measured throughput

Preferred when the user has an actual transfer measurement.

Example:

```text
Measured throughput
650 Mbps
```

Evidence classification:

```text
Measured
```

Allow an optional note such as:

```text
Globus transfer UCT → Ilifu
```

Do not automatically treat a speed-test result as equivalent to sustained bulk-transfer throughput.

---

## Mode B — Known link capacity

Use when the user knows the nominal network capacity.

Example:

```text
Link capacity
1 Gbps
```

Because applications rarely sustain theoretical line rate, require or provide an editable efficiency assumption.

For example:

```text
Link capacity       1 Gbps
Efficiency          70%
Planning throughput 700 Mbps
```

Classification:

```text
Planning assumption
```

Do not silently assume 100% efficiency.

Default efficiency may be:

```text
70%
```

but must be clearly labelled:

**Planning assumption**

and editable.

---

## Mode C — Unknown throughput

If the user does not know throughput, show planning scenarios rather than selecting one as truth.

Use:

```text
100 Mbps
500 Mbps
1 Gbps
5 Gbps
10 Gbps
```

Show estimated duration for each.

Do not call these measured or expected speeds.

Label them:

```text
Planning scenarios
```

This mode is particularly useful before transfer testing has been performed.

---

# 10. Units

Network throughput uses decimal networking units:

```text
1 Mbps = 1,000,000 bits/second
1 Gbps = 1,000 Mbps
```

Dataset capacity continues to use:

```text
1 GB = 1024^3 bytes
1 TB = 1024 GB
```

Document this explicitly.

Do not mix decimal network units and binary storage units silently.

---

# 11. Transfer-Time Formula

Use:

```text
seconds =
size_GB × 1024^3 × 8
/
(throughput_Mbps × 10^6)
```

Then derive:

```text
minutes
hours
days
```

Use sufficient precision internally.

Round only for display.

---

# 12. Deterministic Test Example

For:

```text
size       1 TB
throughput 1 Gbps
```

where:

```text
1 TB = 1024 GB
1 Gbps = 1000 Mbps
```

calculate using the defined formula.

The implementation and tests must derive this value rather than hard-code it.

Expected duration is approximately:

```text
2.44 hours
```

before protocol/application inefficiency.

If using Mode B with:

```text
1 Gbps
70% efficiency
```

effective planning throughput is:

```text
700 Mbps
```

and duration should be approximately:

```text
3.41 hours
```

Use exact calculated values in tests with appropriate tolerance.

---

# 13. Transfer Method

Allow the user to record the expected transfer mechanism.

Initial options:

```text
Globus
AWS CLI / S3 multipart
rclone
Institutional DTN
Illumina ICA transfer
Other
Not yet selected
```

This field is descriptive in 012.

Do not change throughput automatically based solely on transfer method.

A future evidence model may associate measured throughput with methods.

---

# 14. Do Not Benchmark Through the Streamlit Application

The Streamlit application must never be used as the bulk genomic-data path.

Do not implement:

- FASTQ uploads;
- CRAM uploads;
- throughput tests through Streamlit;
- proxy transfers through the planner.

The planner models transfers.

Actual transfers occur through appropriate tools such as:

```text
Globus
DTNs
S3 multipart
rclone
ICA tooling
```

---

# 15. Transfer Result

For a configured transfer show something similar to:

```text
Transfer

FASTQ
Institutional storage → AWS S3

Data volume
48.83 TB

Throughput basis
1 Gbps link × 70% planning efficiency

Planning throughput
700 Mbps

Estimated transfer duration
~6.9 days

Transfer method
Globus

Provider transfer cost
Not currently calculated
```

Values above are illustrative only.

Always calculate actual displayed values.

---

# 16. WGS Transfer Presets

For WGS 30× projects, useful common transfer legs should be easy to configure.

Do not automatically create all of them.

Examples:

### Sequencing input

```text
FASTQ
sequencing centre / institutional storage
→
compute environment
```

### Alignment output

```text
CRAM
compute environment
→
durable object storage
```

### Variant output

```text
gVCF
compute environment
→
durable object storage
```

The user should still explicitly confirm source/destination.

---

# 17. Relationship to Existing Storage Egress Model

The Storage module currently contains an expected AWS egress assumption based on workflow reads.

Do not silently duplicate or double-count this.

The existing Storage transfer assumption and the new Transfer module serve different purposes:

### Existing Storage model

Provides a lifecycle/storage-cost planning assumption.

### Transfer module

Provides explicit endpoint-to-endpoint movement planning.

Document this distinction.

Do not add Transfer costs to Project Summary totals until cost ownership/deduplication is explicit.

Later we may migrate provider transfer costing from Storage into Transfer.

Do not perform that migration in 012.

---

# 18. Provider Transfer Cost

For 012, cost support may remain limited.

If the current verified AWS Cape Town internet-egress pricing can be reused safely from the existing Storage pricing configuration, the architecture may expose it.

However:

- do not duplicate pricing logic;
- do not introduce a second AWS pricing source;
- do not invent provider charges;
- do not assume every AWS transfer uses public-internet egress;
- do not assume ingress charges where none have been verified.

If cost applicability is uncertain, display:

```text
Provider transfer cost
Not currently calculated
```

with an explanation.

Correctness is more important than filling the field.

---

# 19. AWS Directional Cost Context

The model should be capable of distinguishing:

```text
AWS S3 → external endpoint
```

from:

```text
external endpoint → AWS S3
```

because provider transfer charges can differ.

But 012 should not attempt to model:

- Direct Connect;
- inter-region transfer;
- Availability Zone transfer;
- CloudFront;
- private peering;
- every AWS transfer category.

These belong to later refinement.

---

# 20. Optional Network Path Metadata

Allow optional descriptive metadata such as:

```text
Source location
Destination location
```

Examples:

```text
Cape Town
Johannesburg
Frankfurt
Kampala
```

These are descriptive.

Do not infer bandwidth from geography.

Do not say:

```text
Cape Town → Frankfurt = 500 Mbps
```

without actual evidence.

---

# 21. Latency / RTT

RTT is useful but secondary to sustained throughput for the initial planner.

Provide an optional advanced field:

```text
Round-trip time (RTT)
milliseconds
```

If supplied, calculate bandwidth-delay product.

Formula:

```text
BDP_bytes =
throughput_bits_per_second
×
RTT_seconds
/
8
```

Example:

```text
10 Gbps
180 ms RTT
```

gives approximately:

```text
225 MB
```

of data in flight.

Clearly state that BDP is **not additional project storage**.

It is a networking characteristic useful for understanding TCP/window/parallel-transfer requirements.

---

# 22. RTT Guidance

If RTT is provided, show concise operational guidance such as:

> Long-distance high-bandwidth paths may require sufficient TCP windowing and/or parallel streams to approach link capacity.

Possible transfer approaches may include:

```text
Globus
parallel multipart S3 transfers
rclone parallelism
institutional DTNs
```

Do not prescribe exact TCP tuning parameters in 012.

Do not alter the calculated throughput automatically based on RTT.

---

# 23. Evidence Model

Reuse the existing evidence architecture.

Relevant classifications include:

```text
Measured
Planning assumption
Published / provider pricing
User supplied
Unknown
```

Examples:

```text
650 Mbps sustained Globus transfer
→ Measured

1 Gbps link × 70% efficiency
→ Planning assumption

500 Mbps scenario
→ Planning scenario

AWS internet egress tariff
→ Published/provider pricing
```

Do not label user-entered link capacity as measured throughput.

---

# 24. Transfer UI Structure

Suggested page structure:

```text
01 Transfer Planning

02 Data to transfer

03 Endpoints

04 Network throughput

05 Transfer method

06 Transfer estimate

07 Network path details
   optional / advanced

08 Cost status

09 Assumptions and evidence

10 Export
```

Exact numbering may be adjusted to fit the existing application.

Keep the GRO visual language used by Storage and Compute.

---

# 25. Data-to-Transfer UI

Show:

```text
Dataset
Transfer size
```

For WGS presets, derive the size from project/sample configuration.

For custom data, allow explicit size entry.

Always show the calculated volume before estimating duration.

Example:

```text
FASTQ
500 samples × 100 GB
=
50,000 GB
=
48.83 TB
```

This traceability is important.

---

# 26. Endpoint UI

Show clearly:

```text
From
Institutional storage

To
AWS S3
```

Avoid ambiguous labels such as:

```text
Location 1
Location 2
```

Direction must be visually obvious.

---

# 27. Throughput UI

For measured mode:

```text
Throughput basis
Measured sustained throughput

Measured throughput
650 Mbps
```

For known-capacity mode:

```text
Link capacity
1 Gbps

Planning efficiency
70%

Planning throughput
700 Mbps
```

For unknown mode:

show the scenario table.

Do not hide the effective throughput used in the duration calculation.

---

# 28. Unknown-Throughput Scenario Table

For unknown throughput show approximately:

| Planning throughput | Estimated duration |
|---:|---:|
| 100 Mbps | ... |
| 500 Mbps | ... |
| 1 Gbps | ... |
| 5 Gbps | ... |
| 10 Gbps | ... |

Calculate values from the selected dataset.

Do not select a recommended throughput.

Do not use traffic-light colours.

---

# 29. Transfer Duration Presentation

For short transfers show:

```text
2.4 hours
```

For larger transfers:

```text
6.9 days
```

Optionally also show hours in supporting detail.

Do not display excessive decimal precision.

Keep exact values internally and in machine-readable export where useful.

---

# 30. Multiple Transfer Legs

Design the calculation model so that multiple transfer legs can be supported later.

For 012 UI, one active transfer plan at a time is sufficient.

Do not build a complex multi-leg workflow editor yet.

Future examples could include:

```text
sequencer → S3
S3 → Ilifu
Ilifu → S3
```

The model should not prevent this later extension.

---

# 31. Project Summary

When a valid Transfer plan exists in session state, add a small Transfer section to Project Summary.

Show at minimum:

```text
Dataset
Source → destination
Data volume
Throughput basis
Effective/planning throughput
Estimated duration
Transfer method
Provider transfer cost status
```

For example:

```text
Transfer

FASTQ
Institutional storage → AWS S3

Volume
48.83 TB

Planning throughput
700 Mbps

Estimated duration
6.9 days

Method
Globus

Provider transfer cost
Not currently calculated
```

Do not add unknown transfer cost as zero.

Do not double-count Storage's existing AWS egress assumption.

---

# 32. Export

Support:

```text
CSV
JSON
Markdown
```

following the existing application conventions.

Include where applicable:

```text
dataset_name
dataset_size_gb
dataset_size_tb
source_endpoint
destination_endpoint
source_location
destination_location
throughput_mode
link_capacity_mbps
efficiency
effective_throughput_mbps
measured_throughput_mbps
transfer_method
estimated_seconds
estimated_hours
estimated_days
rtt_ms
bandwidth_delay_product_bytes
provider_cost_status
evidence_classification
```

Use `null` / not-modelled states rather than zero for unavailable costs.

---

# 33. Documentation

Update:

```text
docs/design-and-assumptions.md
```

with:

- purpose of Transfer;
- endpoint model;
- WGS dataset presets;
- custom datasets;
- directionality;
- throughput modes;
- decimal networking versus binary storage units;
- transfer-time formula;
- efficiency assumption;
- unknown-throughput scenarios;
- transfer methods;
- RTT and BDP;
- evidence classifications;
- relationship to Storage's existing egress model;
- provider-cost limitations;
- future multi-leg design.

Do not turn the document into a changelog.

---

# 34. Tests

Add deterministic tests for the calculation layer.

At minimum test:

### Unit conversion

```text
1 TB
=
1024 GB
```

### Transfer duration

```text
1 TB @ 1 Gbps
≈ 2.44 h
```

using the exact formula.

### Planning efficiency

```text
1 Gbps × 70%
=
700 Mbps
```

and:

```text
1 TB @ 700 Mbps
≈ 3.41 h
```

### WGS preset

For:

```text
500 samples
FASTQ 100 GB/sample
```

expect:

```text
50,000 GB
≈ 48.828125 TB
```

### Direction

Verify:

```text
AWS → Ilifu
```

and:

```text
Ilifu → AWS
```

remain distinct transfer plans.

### Unknown throughput

Verify scenario durations decrease monotonically as throughput increases.

### RTT / BDP

For:

```text
10 Gbps
180 ms
```

expect approximately:

```text
225,000,000 bytes
```

using decimal network units.

### Missing provider cost

Ensure:

```text
not calculated
```

is represented as null/not-modelled, not zero.

### Existing regressions

All Storage and Compute tests must continue to pass.

---

# 35. Validation

Validate:

- source and destination cannot be empty;
- throughput must be greater than zero when required;
- efficiency must be > 0 and <= 100%;
- dataset size must be > 0;
- RTT, if supplied, must be >= 0;
- configured units are recognised;
- custom endpoint names are not empty when Custom is selected.

Provide useful user-facing validation messages.

Do not allow divide-by-zero errors.

---

# 36. Explicit Limitations

Communicate at least:

1. Transfer duration assumes sustained effective throughput.
2. Real throughput may vary over time.
3. Link capacity is not equivalent to application throughput.
4. Protocol overhead is represented only through the planning-efficiency assumption where applicable.
5. RTT does not directly determine throughput in this model.
6. BDP is informational and does not change the duration calculation.
7. Provider transfer charges are not fully modelled.
8. Institutional network bottlenecks are not automatically known.
9. Transfer-method selection does not automatically alter throughput.
10. The planner does not move genomic data itself.

---

# 37. Explicitly Out of Scope for 012

Do not implement:

- live network speed tests;
- genomic file uploads;
- actual S3 transfers;
- Globus API integration;
- rclone execution;
- AWS CLI execution;
- automatic endpoint discovery;
- network-route discovery;
- traceroute;
- automatic RTT measurement;
- TCP tuning;
- Direct Connect modelling;
- VPN modelling;
- AWS inter-region pricing;
- AWS Availability Zone pricing;
- complex multi-leg workflow editor;
- AI/LLM recommendations;
- transfer automation;
- new Compute functionality;
- GLnexus benchmarking;
- Sentieon/DRAGEN costing.

---

# 38. User-Facing Language

Avoid internal implementation language such as:

```text
spec 012
§12
```

in the user interface.

Prefer:

```text
Measured throughput
Planning assumption
Planning scenario
Provider pricing
Not yet modelled
```

Keep numbered specifications in development documentation only.

---

# 39. Implementation Principle

Transfer should make a user think in this sequence:

```text
What am I moving?
        ↓
How much data is it?
        ↓
Where is it now?
        ↓
Where must it go?
        ↓
What throughput can I realistically sustain?
        ↓
How long will it take?
        ↓
What transfer charges might apply?
```

Do not skip directly from dataset size to a cost or duration without showing the assumptions between them.

---

# 40. Completion Report

After implementation report:

1. files created/modified;
2. transfer model architecture;
3. endpoint model;
4. WGS preset behaviour;
5. custom dataset behaviour;
6. throughput modes;
7. transfer-time formula;
8. efficiency handling;
9. RTT/BDP implementation;
10. evidence classifications;
11. provider-cost status;
12. Project Summary integration;
13. export fields;
14. tests run/results;
15. documentation changes;
16. assumptions made;
17. functionality deliberately deferred.

---

# 41. Completion Gate

After deployment:

1. open `/transfer` directly in a fresh session;
2. test a 1-sample WGS FASTQ transfer;
3. test a 500-sample FASTQ transfer;
4. test measured throughput;
5. test known capacity with 70% efficiency;
6. test unknown-throughput scenarios;
7. reverse source and destination;
8. test a custom dataset;
9. test optional RTT/BDP;
10. inspect Project Summary;
11. verify exports;
12. confirm Storage values remain unchanged;
13. confirm Compute values remain unchanged;
14. run the full automated test suite;
15. perform a final read-only deployed review.

Once these checks pass, mark Transfer 012 complete.
