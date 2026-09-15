# 007 — Data Volume Reference Guide

## Objective

Add a small **Data volume reference guide** to the CBIO Genomics Infrastructure Cost Planner.

The purpose is to help users choose reasonable dataset sizes when actual project measurements are not yet available, particularly when using **Custom Project** mode.

This is a reference guide only.

Do **not** add new file-size calculation algorithms or attempt to derive file sizes from sequencing depth, read length, platform or other sequencing parameters.

The existing WGS 30× defaults remain planning assumptions.

---

# 1. Placement

Add one collapsed Streamlit expander immediately below the top-level:

**WGS 30× | Custom Project**

mode selector and before the main project inputs.

Label it:

> **Data volume reference guide**

Below the heading/inside the expander, explain:

> Rough file-size estimates for common bioinformatics data types. Use measured project volumes where available.

The guide should be accessible from both WGS 30× and Custom Project modes.

Do not duplicate the guide elsewhere in the application.

Keep it collapsed by default so that it does not add clutter to the normal workflow.

---

# 2. Reference table

Inside the expander add a compact table containing the following planning ranges:

| Data / format | Rough planning size | Notes |
|---|---:|---|
| 30× WGS FASTQ | ~80–120 GB/sample | Paired-end compressed FASTQ |
| 30× WGS BAM | ~80–120 GB/sample | Can vary substantially |
| 30× WGS CRAM | ~30–50 GB/sample | Reference-based compression |
| 30× WGS gVCF | ~5–10 GB/sample | Pipeline/caller dependent |
| 30× WGS QC + indexes | ~1–5 GB/sample | Usually relatively small |
| WES FASTQ | ~8–15 GB/sample | Depends strongly on target and sequencing depth |
| WES BAM/CRAM | ~5–10 GB/sample | Rough planning range |
| RNA-seq FASTQ | ~5–15 GB/sample | Highly dependent on read count |
| RNA-seq BAM | ~5–20 GB/sample | Alignment size varies with workflow |
| Genotyping array | <1 GB/sample | Usually small relative to sequencing |
| Joint VCF/BCF | Project-level | Depends strongly on cohort size and variant representation |

Use the existing GRO table styling.

Do not introduce a new table style.

---

# 3. Planning disclaimer

Immediately below the table include:

> **Planning estimates only.** Actual file sizes vary with sequencing platform, coverage, read length, compression, assay design, variant caller and processing pipeline. Where measured project volumes are available, use those instead.

The wording should make it clear that these are approximate capacity-planning ranges rather than guaranteed or authoritative file sizes.

---

# 4. Explain the WGS 30× defaults

In the WGS 30× mode, near the existing WGS dataset assumptions, add a short note:

> The WGS 30× profile uses **100 GB FASTQ, 40 GB CRAM and 10 GB gVCF/QC per sample** as planning defaults. See the Data volume reference guide above for typical ranges.

Do not change the existing values.

The current defaults remain:

```text
FASTQ: 100 GB/sample
CRAM: 40 GB/sample
gVCF/QC/indexes: 10 GB/sample
```

These values should continue to generate the existing WGS calculations.

The reference ranges are explanatory only.

---

# 5. Custom Project dataset-size help

For the **Dataset size** input in Custom Project mode, add concise help text:

> Enter the total size of this dataset, not the size per sample. If the actual volume is not known, use the Data volume reference guide above as a rough planning estimate.

This distinction is important:

WGS mode calculates dataset volume from:

```text
number of samples × estimated size per sample
```

Custom Project expects:

```text
total dataset size
```

Do not automatically multiply Custom Project dataset sizes by a sample count.

---

# 6. Do not derive file sizes

Do not add logic such as:

```text
coverage × genome size
```

or calculations based on:

- sequencing depth
- genome size
- read length
- number of reads
- sequencing platform
- compression ratio
- assay type

The purpose of this change is documentation and guidance, not biological data-volume modelling.

The calculator should remain simple and transparent.

---

# 7. Do not make the reference table interactive

Do not make values in the reference guide automatically populate calculator inputs.

Do not add:

- "Use this value" buttons
- automatic dataset creation
- automatic WES profiles
- automatic RNA-seq profiles
- automatic BAM/CRAM conversions
- automatic file-size estimation

The guide should simply help users decide what value to enter.

This avoids creating a second layer of calculation assumptions.

---

# 8. Keep the guide deliberately small

Do not attempt to create a comprehensive bioinformatics file-format reference.

The guide should focus on file types that materially affect project storage planning.

Do not add small supporting formats such as:

- BED
- BEDPE
- VCF indexes
- small annotation tables
- workflow logs
- scripts
- configuration files
- reference FASTA indexes

unless there is a clear capacity-planning reason.

The goal is:

> Help a user answer: "What rough dataset size should I enter if I do not yet have measured project volumes?"

It is not intended to explain every bioinformatics format.

---

# 9. Joint VCF/BCF

Do not give a simple per-sample estimate for joint VCF/BCF.

Keep:

```text
Joint VCF/BCF | Project-level | Depends strongly on cohort size and variant representation
```

This avoids implying that joint cohort callsets scale predictably as a fixed number of GB per sample.

---

# 10. WGS profile relationship

The UI should make the relationship between the reference guide and WGS defaults understandable.

For example:

```text
Typical 30× WGS FASTQ range:
~80–120 GB/sample

Calculator planning default:
100 GB/sample
```

and:

```text
Typical 30× WGS CRAM range:
~30–50 GB/sample

Calculator planning default:
40 GB/sample
```

The calculator defaults therefore sit within the displayed planning ranges.

Do not alter calculations based on these ranges.

---

# 11. Styling

Preserve the existing GRO styling introduced in previous changes.

The guide should:

- be collapsed by default;
- use existing typography;
- use the existing navy/teal styling;
- use the existing table styling;
- have subtle explanatory text;
- not become a large visual section;
- not introduce nested cards;
- not substantially increase page length while collapsed.

The reference guide should feel like optional supporting documentation rather than another major calculator section.

---

# 12. Existing functionality

Do not change:

- WGS calculations
- Custom Project calculations
- AWS prices
- storage lifecycle calculations
- transfer calculations
- sensitivity calculations
- engineering calculations
- FX assumptions
- VAT assumptions
- project defaults
- exports
- pricing provenance
- GRO styling
- existing tests except where necessary to accommodate the new UI/help text

This change should have **no effect on calculated costs**.

---

# 13. Future extensibility

Keep the reference data easy to update later.

It is acceptable to store the guide entries in a simple Python constant or configuration structure rather than embedding every table row directly into the Streamlit UI code.

For example:

```python
DATA_VOLUME_GUIDE = [
    {
        "format": "30× WGS FASTQ",
        "size": "~80–120 GB/sample",
        "notes": "Paired-end compressed FASTQ",
    },
    ...
]
```

Do not build a complex configuration or database system for this.

Later we may extend the guide as we gain better planning data for:

- WES
- RNA-seq
- long-read sequencing
- metagenomics
- other common CBIO workloads

That future extension should not require changes to the costing engine.

---

# 14. Acceptance criteria

Before completing the implementation verify:

- [ ] A collapsed Data volume reference guide appears below the WGS 30× / Custom Project selector.
- [ ] It is visible from both project modes.
- [ ] The guide contains the requested common bioinformatics data types.
- [ ] WGS FASTQ shows ~80–120 GB/sample.
- [ ] WGS CRAM shows ~30–50 GB/sample.
- [ ] WGS gVCF shows ~5–10 GB/sample.
- [ ] The guide clearly states that values are planning estimates.
- [ ] WGS mode explains that its defaults are 100 GB FASTQ, 40 GB CRAM and 10 GB gVCF/QC per sample.
- [ ] Custom Project explains that Dataset size means total dataset size, not per-sample size.
- [ ] No automatic file-size calculation has been introduced.
- [ ] No automatic population of Custom Project inputs has been introduced.
- [ ] Existing WGS calculations remain identical.
- [ ] Existing Custom Project calculations remain identical.
- [ ] AWS pricing and other assumptions remain unchanged.
- [ ] Existing exports continue to work.
- [ ] Existing tests pass.
- [ ] The full Streamlit application renders without errors.