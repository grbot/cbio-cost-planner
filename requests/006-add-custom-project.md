# 006 — Custom Project Mode

## Objective

Extend the CBIO Genomics Infrastructure Cost Planner so that it can cost projects other than the existing WGS 30× profile.

Add two top-level project modes:

- **WGS 30×**
- **Custom Project**

The existing WGS calculator must continue to produce the same results for the same assumptions.

The new **Custom Project** mode should allow a user to define one or more arbitrary datasets and specify how each dataset is stored and accessed.

The main architectural principle is:

> WGS 30× should become a predefined project template that generates datasets. Custom Project allows the user to define those datasets manually. Both modes must use the same underlying calculation engine.

Do not create a second independent calculator.

---

# 1. Project mode

At the top of the project configuration area add two tabs:

**WGS 30×** | **Custom Project**

Use the existing GRO styling.

The selected mode determines how the project datasets are created.

All downstream calculations should use the same calculation engine.

---

# 2. Simplify WGS 30× mode

The current WGS 30× profile already assumes 30× sequencing.

Therefore, remove the separate sequencing-depth input from the normal WGS interface.

The main WGS inputs should be:

- Number of samples
- Project retention period

The existing WGS 30× defaults remain:

- FASTQ: 100 GB/sample
- CRAM: 40 GB/sample
- gVCF/QC/indexes: 10 GB/sample

These already represent 30× WGS.

Do not scale them again by sequencing depth.

If these values are currently editable under advanced assumptions, retain that functionality.

The existing **500 × 30× WGS** demo must continue to produce the same results.

---

# 3. Shared dataset model

Refactor where necessary so that both WGS and Custom Project ultimately create the same internal dataset representation.

Conceptually:

```python
Dataset(
    name="FASTQ",
    size_gb=50000,
    retrieval_fraction=1.0,
    read_passes=1,
    active_months=1,
    archive_class="Glacier Flexible Retrieval",
)
```

A project then contains:

```python
Project(
    datasets=[...],
    retention_years=5,
    transfer_contingency=0.20,
    ...
)
```

Do not duplicate storage or transfer calculations between WGS and Custom Project.

The desired architecture is:

```text
Project profile / Custom input
            ↓
      Dataset definitions
            ↓
 Shared calculation engine
            ↓
       Cost results
```

---

# 4. Custom Project interface

When **Custom Project** is selected, show:

> Define one or more datasets and describe how each dataset will be stored and accessed. Use this mode for projects that do not yet have a predefined CBIO project profile.

Start with one dataset:

### Dataset 1

For each dataset allow the user to configure:

- Dataset name
- Dataset size
- Size unit: GB or TB
- Retrieval percentage
- Number of read passes
- Active storage duration
- Archive storage class

Use project-level retention by default.

Suggested initial values:

```text
Dataset name: Dataset 1
Size: 1
Unit: TB
Retrieval: 100%
Read passes: 1
Active storage: 1 month
Archive class: Glacier Flexible Retrieval
```

---

# 5. Dataset size

Allow:

- GB
- TB

Internally convert everything to GB.

Continue using the existing convention:

```text
1 TB = 1024 GB
```

Do not change this convention.

Where useful, show the conversion, for example:

```text
20 TB = 20,480 GB
```

Avoid unnecessary decimal precision.

---

# 6. Retrieval percentage

Each dataset has an independent:

**Retrieval %**

This means the proportion of that dataset expected to be read from object storage during one workflow pass.

Examples:

```text
100% = entire dataset is read
10% = approximately one tenth is read
0% = stored but not normally retrieved
```

Valid range:

```text
0–100%
```

Internally represent this as a fraction between 0 and 1.

Add concise help text so the meaning is clear.

---

# 7. Number of read passes

Each dataset has:

**Number of read passes**

This represents how many times the selected retrieval fraction is expected to be read from object storage.

Example:

```text
Dataset size = 10 TB
Retrieval = 100%
Passes = 2

Base workflow egress = 20 TB
```

Another example:

```text
Dataset size = 20 TB
Retrieval = 10%
Passes = 1

Base workflow egress = 2 TB
```

Allow zero passes.

---

# 8. Data movement calculation

For every dataset:

```text
base workflow egress =
dataset size × retrieval fraction × number of read passes
```

Then:

```text
total base workflow egress =
Σ(dataset base workflow egress)
```

Apply the existing project-level transfer contingency:

```text
planned workflow egress =
total base workflow egress × (1 + transfer contingency)
```

Do not change the existing contingency logic.

---

# 9. WGS regression example

The existing 500 × 30× WGS profile must still calculate:

```text
FASTQ:
500 × 100 GB = 50,000 GB
Retrieval 100%
Passes 1

Egress = 50,000 GB


CRAM:
500 × 40 GB = 20,000 GB
Retrieval 10%
Passes 1

Egress = 2,000 GB


gVCF/QC:
500 × 10 GB = 5,000 GB
Retrieval 100%
Passes 2

Egress = 10,000 GB
```

Therefore:

```text
Durable volume =
50,000 + 20,000 + 5,000
= 75,000 GB
```

Base workflow egress:

```text
50,000 + 2,000 + 10,000
= 62,000 GB
```

With 20% transfer contingency:

```text
62,000 × 1.20
= 74,400 GB
```

Using:

```text
1 TB = 1024 GB
```

this is:

```text
72.66 TB
```

Use this as a regression test.

---

# 10. Multiple datasets

Custom Project must allow users to add additional datasets.

Provide:

**+ Add dataset**

The user can create:

- Dataset 1
- Dataset 2
- Dataset 3
- etc.

Each dataset is independently configurable.

A reasonable technical limit such as 20 datasets is acceptable if needed for Streamlit state management.

---

# 11. Remove datasets

Datasets added after Dataset 1 should have:

**Remove dataset**

The project must never contain zero datasets.

Use stable Streamlit session-state identifiers.

Adding or removing a dataset must not reset values entered for the other datasets.

---

# 12. Dataset names

Dataset names are free text.

Examples:

- Raw sequencing data
- Alignment files
- Variant calls
- Array data
- Imaging data
- Analysis outputs
- Intermediate results
- Released data

Do not constrain Custom Project to genomics file types.

This mode is intentionally generic.

---

# 13. Storage lifecycle per dataset

Each dataset should independently specify:

## Active storage duration

Number of months the dataset remains in S3 Standard before being archived.

## Archive class

Use only storage classes already supported by the calculator:

- S3 Standard
- Glacier Instant Retrieval
- Glacier Flexible Retrieval
- Glacier Deep Archive

Do not introduce additional AWS storage classes in this change.

## Retention

Use the project's retention period by default.

If per-dataset retention is easy to support cleanly with the existing architecture, it may be added as an override.

Otherwise retain one project-level retention value for this version.

Prefer simplicity.

---

# 14. S3 Standard-only datasets

A dataset must be able to remain in S3 Standard for the entire project.

If:

```text
Archive class = S3 Standard
```

do not calculate an archive transition.

Do not show misleading Glacier transition or archive costs.

---

# 15. Durable project volume

For Custom Project calculate:

```text
Total durable project volume =
Σ(dataset sizes)
```

Display prominently:

- Number of datasets
- Total durable project volume
- Planned workflow egress

For example:

```text
3 datasets
75.0 TB durable project data
72.66 TB planned workflow egress
```

Use the existing GRO metric styling.

---

# 16. Dataset summary

Provide a compact summary table before or within the results.

For example:

| Dataset | Size | Retrieval | Passes | Active | Archive |
|---|---:|---:|---:|---:|---|
| Raw data | 50 TB | 100% | 1 | 1 mo | Flexible |
| Alignment | 20 TB | 10% | 1 | 1 mo | Flexible |
| Variants | 5 TB | 100% | 2 | 1 mo | Flexible |

Use the existing GRO table styling.

---

# 17. Storage cost calculation

Calculate storage independently for every dataset according to:

- dataset size
- active storage duration
- archive class
- archive duration
- applicable request/lifecycle charges

Then sum the dataset costs.

Conceptually:

```text
Project storage cost =
Σ(dataset storage costs)
```

Transfer is calculated from aggregate planned egress:

```text
Project transfer cost =
cost(planned workflow egress)
```

Engineering remains project-level.

Therefore:

```text
Project total =
storage
+ requests/lifecycle
+ transfer
+ engineering
```

Continue to state:

> Compute not currently included.

Do not change AWS pricing values.

---

# 18. Engineering costs

Engineering remains project-level.

Do not multiply engineering effort by the number of datasets.

Preserve the existing defaults:

```text
Onboarding: 8 hours
Operations: 12 hours/year
Closeout: 4 hours
Illustrative engineering rate: R1,000/hour
```

For five years:

```text
8 + (12 × 5) + 4
= 72 hours
```

Continue to label the engineering rate:

> Planning assumption only — not an approved UCT/CBIO institutional rate.

---

# 19. Sensitivity analysis

The existing Low / Expected / High sensitivity analysis must work for both:

- WGS 30×
- Custom Project

For Custom Project, calculate sensitivity using the generic datasets.

Do not assume that FASTQ, CRAM or gVCF datasets exist.

If the existing sensitivity code is coupled to WGS file types, refactor it to work from the shared dataset model.

The WGS sensitivity results must remain unchanged.

---

# 20. Calculation details

Update the existing **Calculation details** expander so it works for Custom Project.

For example:

```text
Dataset: Alignment data

Size:
20 TB = 20,480 GB

Retrieval:
10%

Passes:
2

Base workflow egress:
20,480 GB × 10% × 2
= 4,096 GB
```

Then show:

```text
Total base workflow egress
+ transfer contingency
= planned workflow egress
```

The user should be able to understand how the result was calculated.

---

# 21. Exports

Preserve the existing CSV, JSON and Markdown export functionality.

Clearly identify:

```text
Project mode: WGS 30×
```

or:

```text
Project mode: Custom Project
```

For Custom Project include the dataset definitions.

For example:

```text
Datasets

1. Raw sequencing data
   Size: 50 TB
   Retrieval: 100%
   Passes: 1
   Active storage: 1 month
   Archive: Glacier Flexible Retrieval

2. Processed results
   Size: 10 TB
   Retrieval: 20%
   Passes: 2
   Active storage: 1 month
   Archive: Glacier Flexible Retrieval
```

Preserve pricing provenance in exported results.

---

# 22. Pricing provenance

Preserve everything introduced in:

`005-pricing-and-disclaimer.md`

Including:

- AWS pricing source
- Africa (Cape Town), `af-south-1`
- pricing last verified date
- planning assumptions explanation
- engineering-rate disclaimer
- final planning-tool disclaimer
- export pricing provenance

Do not hard-code pricing metadata in `app.py`.

Use the existing pricing configuration/model.

Do not reintroduce the previous `pricing.pricing_source` AttributeError.

---

# 23. Validation

Handle invalid inputs gracefully.

Examples:

- blank dataset name
- zero dataset size
- negative size
- retrieval outside 0–100%
- negative passes
- active storage longer than retention
- invalid archive configuration

Use normal Streamlit validation/help messages.

Normal input mistakes must not produce Python exceptions in the UI.

---

# 24. Styling

Preserve the existing GRO styling.

Use:

- navy headings
- teal section numbers/accents
- existing page background
- white section panels
- existing input styling
- existing tables
- existing spacing
- existing typography

Do not redesign the application.

Avoid excessive nested cards.

For multiple datasets, using an expander per dataset is encouraged if it improves readability.

For example:

```text
▾ Dataset 1 — Raw sequencing data
▸ Dataset 2 — Alignment files
▸ Dataset 3 — Variant calls
```

---

# 25. Tests

Add tests for the generic dataset model.

## Single dataset

Input:

```text
Size = 10 TB
Retrieval = 100%
Passes = 1
Contingency = 20%
```

Expected:

```text
Base egress = 10 TB
Planned egress = 12 TB
```

## Partial retrieval

Input:

```text
Size = 20 TB
Retrieval = 10%
Passes = 1
```

Expected:

```text
Base egress = 2 TB
```

## Multiple passes

Input:

```text
Size = 5 TB
Retrieval = 100%
Passes = 2
```

Expected:

```text
Base egress = 10 TB
```

## Multiple datasets

Verify that:

- durable volume sums correctly
- base egress sums correctly
- planned egress sums correctly
- storage costs sum correctly

## WGS regression

The existing 500 × 30× profile must still produce:

```text
FASTQ = 50,000 GB
CRAM = 20,000 GB
gVCF/QC = 5,000 GB

Durable volume = 75,000 GB

Base workflow egress = 62,000 GB

Planned workflow egress =
74,400 GB
```

Existing cost regression tests must continue to pass.

---

# 26. Future extensibility

Design this so future predefined project profiles can populate the same dataset model.

Potential future profiles:

- WES
- RNA-seq
- array/genotyping
- long-read WGS
- metagenomics

Do not implement these now.

The intended architecture is:

```text
WGS 30× profile ─────┐
                     │
Future WES profile ──┤
                     ├──> Dataset model
Future RNA-seq ──────┤          │
                     │          ↓
Custom Project ──────┘   Shared calculator
                                │
                                ↓
                           Cost results
```

Custom Project therefore becomes the generic infrastructure model, while WGS 30× is the first convenient predefined template.

---

# 27. Out of scope

Do not add:

- WES profiles
- RNA-seq profiles
- array profiles
- long-read profiles
- compute pricing
- scheduler/fairshare pricing
- AWS API integration
- automatic AWS price retrieval
- authentication
- database storage
- GRO integration
- Ilifu API integration
- AI functionality

Keep this change focused on reusable project storage and data-movement costing.

---

# 28. Acceptance criteria

Before completing the implementation verify:

- [ ] WGS 30× and Custom Project tabs exist.
- [ ] WGS no longer asks for a redundant sequencing-depth input.
- [ ] Existing WGS calculations remain unchanged.
- [ ] Custom Project starts with one dataset.
- [ ] Additional datasets can be added.
- [ ] Datasets can be removed safely.
- [ ] Adding/removing datasets does not reset other dataset inputs.
- [ ] Each dataset supports name, size, unit, retrieval %, passes, active storage and archive class.
- [ ] GB and TB work correctly.
- [ ] 1 TB = 1024 GB throughout.
- [ ] Durable project volume sums all datasets.
- [ ] Egress is calculated per dataset and summed.
- [ ] Transfer contingency is applied correctly.
- [ ] Storage lifecycle costs are calculated per dataset.
- [ ] S3 Standard-only datasets work correctly.
- [ ] Sensitivity analysis works for Custom Project.
- [ ] Engineering remains project-level.
- [ ] Calculation details explain Custom Project calculations.
- [ ] Exports identify project mode and datasets.
- [ ] Pricing provenance from 005 remains intact.
- [ ] No AWS pricing values have changed.
- [ ] Compute remains explicitly excluded.
- [ ] Existing GRO styling is preserved.
- [ ] Full test suite passes.
- [ ] Streamlit renders successfully in both modes.