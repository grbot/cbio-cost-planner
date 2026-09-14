# CBIO Genomics Infrastructure Cost Planner — Initial Build

## Goal

Build a small, maintainable Streamlit application for CBIO that estimates the infrastructure cost of hosting and processing genomics projects.

The initial focus is WGS projects using:

- AWS S3 in the Cape Town region (`af-south-1`) for durable storage
- S3 Glacier storage classes for long-term retention
- Ilifu for compute and temporary scratch
- AWS-to-Ilifu data transfer as an explicit project cost

The calculator must be suitable for early project planning and grant budgeting.

It is a planning tool, not an AWS billing system.

---

# 1. Core principle

The calculator should model the lifecycle of genomic data rather than simply calculate:

> TB × storage price

Different file types move differently during a genomics project.

For example:

- FASTQs are normally uploaded to durable object storage, then transferred to Ilifu for primary processing.
- CRAMs are produced on Ilifu and uploaded into durable object storage. They may only occasionally be downloaded again.
- gVCFs are produced on Ilifu, uploaded to object storage, and may later be downloaded again for joint calling.
- Temporary/intermediate workflow files should normally remain on Ilifu scratch and are not durable project storage.

Therefore the cost model must separately calculate:

1. Active storage
2. Archive storage
3. AWS data transfer out
4. S3/API/lifecycle request costs
5. Project infrastructure setup effort
6. Ongoing infrastructure management effort
7. Project closeout effort

Ilifu compute costing/fairshare will be added later and must initially remain a separate section marked:

**Compute cost not yet included.**

---

# 2. Technology

Use:

- Python 3
- Streamlit
- pandas where useful
- standard Python libraries
- TOML/YAML/JSON configuration for pricing and assumptions

Avoid unnecessary frameworks.

The application should be easy to run locally with:

```bash
streamlit run app.py
```

Structure the project so that pricing logic is separate from the Streamlit UI.

Suggested structure:

```text
cbio-cost-planner/
├── app.py
├── README.md
├── requirements.txt
├── config/
│   ├── aws-pricing.yaml
│   └── project-profiles.yaml
├── cbio_cost/
│   ├── __init__.py
│   ├── models.py
│   ├── storage.py
│   ├── transfer.py
│   ├── operations.py
│   └── calculator.py
├── tests/
│   └── test_calculator.py
└── docs/
    └── assumptions.md
```

Do not put calculation logic directly into Streamlit widgets.

---

# 3. Initial user interface

Create a clear single-page calculator with sections.

## Project

Inputs:

- Project name
- Project type
  - WGS 30× initially
  - allow future extension
- Number of samples
- Sequencing depth
- Project duration / retention period in years

Default example:

```text
Project type: WGS
Samples: 500
Depth: 30×
Retention: 5 years
```

---

# 4. Data volume assumptions

Make all assumptions editable.

Initial planning defaults per 30× WGS sample:

| File type | Default |
|---|---:|
| FASTQ | 100 GB |
| CRAM | 40 GB |
| gVCF/QC/indexes | 10 GB |

Thus:

```text
durable GB/sample = FASTQ + CRAM + gVCF/QC
```

For 500 samples:

```text
FASTQ       50 TB
CRAM        20 TB
gVCF/etc.    5 TB
-----------------
Raw model   75 TB
```

Allow an optional storage-headroom percentage.

Default:

```text
20%
```

Show both:

- calculated data volume
- provisioned planning envelope

For the above example, this should result in approximately a 90 TB envelope and may be rounded operationally to a 100 TB project allocation.

Do not silently round calculations.

---

# 5. Data movement model

This is critical.

Users must be able to specify expected movements for each file type.

Initial defaults:

## FASTQ

Primary processing requires FASTQs to move:

```text
AWS S3 → Ilifu
```

Default:

```text
processing passes = 1
```

Therefore:

```text
FASTQ egress = FASTQ volume × passes
```

## CRAM

CRAMs generally move:

```text
Ilifu → S3
```

AWS internet ingress is generally free.

Only some CRAMs may subsequently need to be retrieved.

Default:

```text
CRAM retrieval fraction = 10%
CRAM retrieval passes = 1
```

Therefore:

```text
CRAM egress =
CRAM volume × retrieval fraction × retrieval passes
```

## gVCF

gVCFs may need to move back to Ilifu for cohort joint calling.

Default:

```text
gVCF processing/retrieval passes = 2
```

Therefore:

```text
gVCF egress =
gVCF volume × passes
```

## Transfer contingency

Allow a transfer contingency covering:

- reprocessing
- failed/restarted transfers
- workflow changes
- additional QC investigations

Default:

```text
20%
```

Calculate:

```text
base egress =
FASTQ egress +
CRAM egress +
gVCF egress

planned egress =
base egress × (1 + contingency)
```

Display this prominently.

---

# 6. AWS transfer model

Separate ingress and egress.

## AWS ingress

Display:

```text
Data transferred into AWS:
AWS internet data-transfer charge: $0
```

Do not imply that S3 PUT/API requests are free.

## AWS egress

Use configurable pricing tiers for `af-south-1`.

The price configuration must support tiered egress pricing.

Do not hard-code all arithmetic into the UI.

Allow a configurable monthly free allowance.

The UI should explain:

> AWS-to-Ilifu transfer over the public internet can be a major project cost and may exceed storage costs.

---

# 7. Active S3 storage

Initial storage class:

```text
S3 Standard
```

Calculate active-storage cost based on:

- data volume
- number of months active
- tiered Cape Town S3 Standard pricing

Default active period:

```text
1 month
```

Support a user-adjustable value.

---

# 8. Archive storage

Allow the user to select separately where different file types go after active processing.

Options:

- remain S3 Standard
- Glacier Instant Retrieval
- Glacier Flexible Retrieval
- Glacier Deep Archive

Suggested initial defaults:

```text
FASTQ  → Glacier Flexible Retrieval
CRAM   → Glacier Flexible Retrieval
gVCF   → Glacier Flexible Retrieval
```

Do not automatically assume Deep Archive.

Show:

- archive storage class
- monthly cost
- annual cost
- total cost over selected retention period
- minimum-storage-duration warning
- retrieval characteristics

Configuration should include at least:

```text
S3 Standard
Glacier Instant Retrieval
Glacier Flexible Retrieval
Glacier Deep Archive
```

---

# 9. Lifecycle mechanics

The application should make clear that data does not need to move to a separate bucket.

Example:

```text
s3://project-x/fastq/sample.fastq.gz
```

can remain at the same object key while its storage class changes through an S3 Lifecycle rule.

Show the conceptual lifecycle:

```text
S3 Standard
     ↓
processing / validation
     ↓
S3 Lifecycle transition
     ↓
Glacier
```

For Flexible Retrieval and Deep Archive, clearly warn:

> Objects must normally be restored before being read.

Glacier Instant Retrieval can be read directly but has retrieval charges.

---

# 10. Infrastructure engineering / management costs

Infrastructure support must not be assumed to be free.

Create these categories:

## Once-off onboarding

Potential tasks:

- create/project-register storage
- bucket/prefix structure
- IAM roles
- encryption controls
- lifecycle rules
- budget alarms
- project tagging
- Ilifu Unix/project groups
- scratch quota
- manifests/checksum process
- connectivity test
- monitoring setup

Input:

```text
onboarding engineering hours
```

Default planning value:

```text
8 hours
```

## Ongoing operations

Potential tasks:

- access changes
- monitoring
- cost review
- troubleshooting
- restore requests
- lifecycle review
- annual project review

Inputs:

```text
operations hours/year
```

Default planning value:

```text
12 hours/year
```

## Closeout

Potential tasks:

- verify released outputs
- final archive transition
- remove scratch/project bulk data
- revoke credentials
- verify manifests
- final storage report
- project handover

Default:

```text
4 engineering hours
```

## Engineering hourly rate

Do NOT assume CBIO's actual institutional loaded rate.

Use a clearly marked placeholder:

```text
R1,000/hour
```

The interface must display:

> Illustrative planning rate — replace with approved CBIO/UCT loaded technical staff rate.

Calculate:

```text
setup cost
operations cost over project lifetime
closeout cost
```

---

# 11. Compute

Add a section called:

## Ilifu compute

For V1 display:

```text
Compute cost / entitlement not yet included.
```

Add explanatory text:

Future versions should model project classes such as:

- CBIO core
- CBIO collaborative
- external academic
- externally funded/service

Possible future controls:

- fairshare weight
- maximum concurrent jobs
- CPU allocation
- GPU allocation
- scratch quota
- turnaround expectations

Do not implement monetary compute charging yet.

---

# 12. Cost output

Show a summary with:

```text
Project:
500 × 30× WGS

Durable data:
XX TB

Provisioned envelope:
XX TB

Expected AWS egress:
XX TB
```

Then:

| Cost component | Cost |
|---|---:|
| Project onboarding | R... |
| Active S3 storage | R... |
| S3/API/lifecycle requests | R... |
| AWS → Ilifu transfer | R... |
| Archive storage | R... |
| Operational management | R... |
| Project closeout | R... |
| **Total project infrastructure cost** | **R...** |
| Compute | Not included |

Show:

- USD AWS cost
- ZAR AWS cost ex VAT
- ZAR including configurable VAT
- staff/engineering cost in ZAR

Use configurable:

```text
USD/ZAR exchange rate
VAT %
```

Defaults may initially be:

```text
USD/ZAR = 16.05
VAT = 15%
```

but make both editable and clearly label the date/source assumption.

---

# 13. Sensitivity analysis

Create three project scenarios:

### Low movement
- fewer retrievals
- lower contingency

### Expected
- default assumptions

### High movement
- extra FASTQ processing/reprocessing
- higher CRAM retrieval
- extra gVCF passes
- higher contingency

Display a comparison table:

| Scenario | Expected egress | Storage | Transfer | Archive | Engineering | Total |
|---|---:|---:|---:|---:|---:|---:|

The purpose is to demonstrate that transfer behaviour can materially change total project cost.

---

# 14. Example profile

Include a built-in example:

```text
500 × 30× WGS
5-year retention
```

Planning assumptions:

```text
FASTQ       100 GB/sample
CRAM         40 GB/sample
gVCF/etc.    10 GB/sample

FASTQ passes             1
CRAM retrieval           10%
CRAM retrieval passes    1
gVCF passes              2
transfer contingency     20%

S3 active period         1 month
archive retention        remaining project period
```

This profile must be selectable with one click so that it can be used in demonstrations.

---

# 15. Explain the result

Below the calculations, generate a short plain-English interpretation such as:

> This 500-sample 30× WGS project is estimated to generate approximately 75 TB of durable genomic data. With operational headroom, a 90–100 TB storage envelope is appropriate. The expected AWS-to-Ilifu data movement is approximately XX TB under the selected workflow assumptions. Because AWS internet egress is charged while ingress is generally free, transfer behaviour is an important component of the total project cost.

Do not use an LLM to generate this text. Generate it deterministically from the calculation values.

---

# 16. Configuration

All cloud prices must live outside application logic.

Example:

```yaml
aws:
  region: af-south-1

  exchange_rate:
    usd_zar: 16.05

  vat_percent: 15

  s3_standard:
    storage_tiers:
      - up_to_gb: 51200
        usd_per_gb_month: 0.0274
      - up_to_gb: 512000
        usd_per_gb_month: 0.0262

  glacier_instant:
    usd_per_gb_month: 0.0050

  glacier_flexible:
    usd_per_gb_month: 0.00405

  glacier_deep_archive:
    usd_per_gb_month: 0.0018
```

Create the configuration structure so rates can be updated without touching Python source.

Before using any numerical pricing values in production, mark them with:

```text
pricing_last_verified
source
```

---

# 17. Auditability

Every estimate should expose its assumptions.

Add an expandable:

```text
Calculation details
```

section showing formulas such as:

```text
FASTQ:
500 × 100 GB = 50,000 GB

FASTQ egress:
50,000 GB × 1 pass = 50,000 GB

CRAM:
500 × 40 GB = 20,000 GB

CRAM retrieval:
20,000 × 10% = 2,000 GB
```

A researcher should be able to see why the estimate has a particular value.

---

# 18. Export

V1 should support downloading the project estimate as:

- CSV
- JSON

If straightforward, also provide a concise Markdown project-cost summary.

Do not implement PDF generation in the first pass.

---

# 19. Code quality

Requirements:

- type hints
- docstrings
- unit tests for cost calculations
- no calculation duplicated between UI and backend
- use Decimal where appropriate for financial calculations
- validate percentages and negative values
- clearly distinguish GB/TB assumptions
- document whether TB is decimal or binary

For this project use:

```text
1 TB = 1024 GB
```

to remain consistent with the existing CBIO proposal, but isolate this conversion so it can later be changed.

---

# 20. Initial tests

At minimum test:

1. Storage volume for 500 × 30× WGS
2. FASTQ egress calculation
3. CRAM partial-retrieval calculation
4. gVCF multiple-pass calculation
5. transfer contingency
6. tiered S3 Standard pricing
7. tiered internet egress pricing
8. archive cost over multiple years
9. engineering support cost
10. zero-sample and invalid-input handling

---

# 21. UI style

Keep the design professional and conservative.

It is an internal UCT/CBIO infrastructure planning tool.

Prefer:

- white background
- clear headings
- restrained use of Streamlit metrics
- tables over excessive charts
- one useful cost breakdown chart if appropriate
- concise explanations
- no playful icons or unnecessary decoration

The interface should feel like an infrastructure budgeting tool, not a consumer application.

---

# 22. What to build now

For the first implementation:

1. Create the complete repository structure.
2. Implement the calculation engine.
3. Implement configuration-driven AWS pricing.
4. Implement the WGS data lifecycle model.
5. Implement staff/setup/operations/closeout costing.
6. Implement the Streamlit UI.
7. Add the 500 × 30× / 5-year demo profile.
8. Add calculation-detail expanders.
9. Add CSV and JSON export.
10. Add tests.
11. Add README setup/run instructions.

Do not add authentication, databases, AWS API calls, Terraform, Ilifu integration or live cloud provisioning yet.

This first version is a **cost-modelling PoC**.

Once this works correctly, we will review the assumptions and then consider:

- external versus CBIO compute/fairshare profiles
- live AWS pricing updates
- institutional/non-AWS object-storage providers
- project YAML generation
- Terraform provisioning
- GRO integration
- project monitoring and actual-vs-estimated expenditure.