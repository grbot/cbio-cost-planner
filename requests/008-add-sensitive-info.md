# 008 — Data Governance Notice and Low-Pass WGS Reference

## Objective

Make two small guidance improvements to the CBIO Genomics Infrastructure Cost Planner:

1. Add a clear but restrained **Sensitive data and governance** notice explaining that a cost estimate does not imply approval to store genomic or other sensitive research data in AWS/object storage.
2. Extend the existing **Data volume reference guide** with rough planning ranges for **4× and 12× WGS**, alongside the existing 30× WGS estimates.

This is a guidance/UI change only.

Do not change any calculations, pricing, project profiles, storage logic, transfer logic or sensitivity analysis.

---

# 1. Sensitive data and governance notice

Add a compact informational notice near the top of the application.

Place it:

- below the WGS 30× / Custom Project mode selector;
- before the main project configuration inputs;
- close to the existing Data volume reference guide.

Use the existing GRO informational/callout styling.

Do not use alarming warning/error styling unless required by the existing UI conventions.

Suggested heading:

> **Sensitive data and governance**

Suggested text:

> This calculator estimates infrastructure costs only. Genomic, phenotype and other sensitive research data should only be stored in cloud/object storage where this is permitted by the project's consent, ethics approvals, data-access agreements and applicable institutional policies. Storage location, access controls, encryption, audit logging, retention and data-transfer requirements should be reviewed before deployment.

Add a short final sentence:

> **A cost estimate does not constitute approval to store project data in AWS.**

Keep the notice concise.

---

# 2. Purpose of the governance notice

The application currently models AWS S3 and Glacier costs in the Africa (Cape Town) region.

Do not imply that:

- AWS is automatically approved for all CBIO/UCT projects;
- de-identification automatically makes genomic data non-sensitive;
- use of the Cape Town AWS region automatically satisfies governance requirements;
- encryption alone makes a deployment compliant;
- the calculator performs a privacy, ethics or security assessment.

The calculator is a **planning tool**, not an approval or compliance system.

---

# 3. Genomic data sensitivity

The wording should reflect that genomic data may remain sensitive and potentially identifying even where direct identifiers have been removed.

However, do not add lengthy legal or regulatory explanations.

Do not attempt to determine compliance with:

- POPIA;
- GDPR;
- research ethics requirements;
- specific funder requirements;
- specific Data Access Committee requirements;
- individual project consent conditions.

Those decisions are outside the scope of this calculator.

The notice should simply prompt the user to check the appropriate governance requirements before deployment.

---

# 4. Security considerations

The governance notice should briefly identify the main categories that need to be considered before using object/cloud storage for sensitive project data:

- consent and ethics approval;
- data-access agreements;
- institutional policy;
- permitted storage location/jurisdiction;
- access control;
- encryption;
- audit logging;
- retention;
- deletion;
- data-transfer requirements.

Do not turn these into interactive controls.

Do not add a compliance checklist.

Do not require the user to confirm them before using the calculator.

This is informational guidance only.

---

# 5. Do not collect sensitive information

Do not add inputs requesting:

- participant identifiers;
- patient identifiers;
- cohort participant details;
- phenotype values;
- genomic variants;
- consent information;
- ethics approval numbers;
- credentials;
- AWS keys;
- bucket credentials.

The calculator should continue to work only with infrastructure-planning information such as dataset sizes, retention and movement assumptions.

If appropriate, add a small sentence to the governance notice:

> Do not enter participant-level or other sensitive research data into this planning tool.

Do not make this sentence visually dominant.

---

# 6. Extend the Data volume reference guide

Update the existing **Data volume reference guide** introduced in `007-data-volume-guide.md`.

Add low-pass WGS planning estimates for:

- 4× WGS
- 12× WGS

Keep the existing 30× WGS entries.

The WGS portion of the guide should contain approximately:

| Data / format | Rough planning size | Notes |
|---|---:|---|
| 4× WGS FASTQ | ~12–20 GB/sample | Low-pass WGS; sequencing yield varies by platform |
| 4× WGS CRAM | ~5–8 GB/sample | Reference-based compression; approximate planning range |
| 12× WGS FASTQ | ~35–50 GB/sample | Medium-depth WGS; approximate planning range |
| 12× WGS CRAM | ~12–20 GB/sample | Reference-based compression; approximate planning range |
| 30× WGS FASTQ | ~80–120 GB/sample | Paired-end compressed FASTQ |
| 30× WGS BAM | ~80–120 GB/sample | Can vary substantially |
| 30× WGS CRAM | ~30–50 GB/sample | Reference-based compression |
| 30× WGS gVCF | ~5–10 GB/sample | Pipeline/caller dependent |
| 30× WGS QC + indexes | ~1–5 GB/sample | Usually relatively small |

Preserve the existing WES, RNA-seq, genotyping array and joint VCF/BCF entries from 007.

Do not remove them.

---

# 7. Do not scale gVCF by sequencing depth

Do not add estimated 4× or 12× gVCF sizes simply by scaling the existing 30× gVCF value according to sequencing depth.

gVCF size does not necessarily scale linearly with coverage because it depends on factors including:

- variant caller;
- reference-block representation;
- sequencing quality;
- callable regions;
- pipeline configuration.

For now, keep the specific gVCF planning range associated with the existing 30× WGS reference only.

If desired, the table notes may state:

> gVCF size is pipeline/caller dependent and does not necessarily scale linearly with sequencing depth.

Do not introduce additional calculation logic.

---

# 8. Planning estimates disclaimer

Preserve the existing disclaimer below the Data volume reference guide:

> **Planning estimates only.** Actual file sizes vary with sequencing platform, coverage, read length, compression, assay design, variant caller and processing pipeline. Where measured project volumes are available, use those instead.

This disclaimer applies to the new 4× and 12× estimates as well.

---

# 9. Relationship to WGS 30× profile

Do not create new calculator profiles for:

- WGS 4×
- WGS 12×

The top-level project modes remain:

**WGS 30× | Custom Project**

The existing WGS 30× profile remains unchanged.

The low-pass estimates are provided only as guidance for users constructing a **Custom Project**.

For example, a user planning 500 × 12× WGS samples can use the reference guide to estimate the relevant total dataset sizes and enter those into Custom Project.

Do not automate this in this change.

---

# 10. Do not derive file sizes from depth

Do not add calculations such as:

```text
30× FASTQ size × 4 / 30
```

or:

```text
30× CRAM size × 12 / 30
```

The displayed ranges should remain explicit planning guidance.

Do not introduce inputs for:

- sequencing depth;
- genome size;
- read length;
- sequencing platform;
- number of reads;
- compression ratio.

The calculator should remain generic and transparent.

---

# 11. Preserve WGS 30× defaults

Do not change the existing WGS 30× calculator defaults:

```text
FASTQ: 100 GB/sample
CRAM: 40 GB/sample
gVCF/QC/indexes: 10 GB/sample
```

These remain the predefined WGS 30× planning assumptions.

The existing 500 × 30× regression calculation must remain unchanged.

---

# 12. Suggested layout

Keep the top of the application visually simple.

A suitable order is:

```text
CBIO Genomics Infrastructure Cost Planner

[ WGS 30× ] [ Custom Project ]

Sensitive data and governance
[compact informational notice]

▸ Data volume reference guide

Project configuration
...
```

The governance notice should be visible without opening an expander.

The Data volume reference guide should remain collapsed by default.

---

# 13. Styling

Preserve the existing GRO visual style.

For the governance notice:

- use a subtle informational callout;
- use the existing navy/teal palette;
- maintain good contrast;
- avoid red;
- avoid warning triangles unless already part of the established design;
- keep padding and spacing consistent with existing panels.

The notice should communicate:

> Important project governance consideration

rather than:

> Application error or dangerous action.

The Data volume reference guide should retain the existing table styling from 007.

---

# 14. Pricing disclaimer remains separate

Do not merge the new data-governance notice with the existing pricing/procurement disclaimer from `005-pricing-and-disclaimer.md`.

They serve different purposes.

The application should retain:

### Near the top

**Sensitive data and governance**

This addresses whether a project's data may appropriately be stored using the proposed infrastructure.

### Near the bottom

Existing pricing/procurement disclaimer.

This addresses whether the calculated costs are suitable for budgeting/procurement.

Keep these concerns separate.

---

# 15. Exports

If the existing Markdown export contains a notes/disclaimer section, add a concise governance statement such as:

> Infrastructure cost estimates do not constitute approval to store sensitive research data in AWS or other cloud/object storage. Project-specific consent, ethics, data-access and institutional requirements must be reviewed separately.

Do not substantially expand JSON or CSV exports for this change.

Do not add governance fields to the calculation model.

The governance notice is not a calculated value.

---

# 16. No compliance functionality

Do not add:

- compliance scoring;
- security scoring;
- risk scoring;
- POPIA compliance determination;
- GDPR compliance determination;
- ethics approval validation;
- consent validation;
- institutional approval workflows;
- AWS security configuration;
- IAM configuration;
- bucket provisioning;
- encryption configuration;
- data classification workflows.

These may be considered separately in future.

This change is guidance only.

---

# 17. Existing functionality

Do not change:

- WGS calculations;
- Custom Project calculations;
- AWS pricing;
- storage calculations;
- archive calculations;
- retrieval calculations;
- transfer/egress calculations;
- sensitivity calculations;
- engineering calculations;
- FX;
- VAT;
- project defaults;
- WGS 30× profile;
- pricing provenance;
- existing GRO styling;
- Streamlit session-state behaviour.

This change must have **no effect on calculated costs**.

---

# 18. Tests and verification

Run the existing test suite.

No calculation regression should occur.

Verify manually or through appropriate UI testing that:

- WGS 30× renders correctly;
- Custom Project renders correctly;
- the governance notice is visible in both modes;
- the Data volume reference guide opens correctly;
- 4× and 12× WGS entries appear;
- existing 30×, WES, RNA-seq, array and joint VCF/BCF entries remain;
- the application does not crash;
- exports continue to work.

---

# 19. Acceptance criteria

Before completing the implementation verify:

- [ ] A visible Sensitive data and governance notice appears near the top of the app.
- [ ] It states that the calculator estimates infrastructure costs only.
- [ ] It states that sensitive data use depends on project-specific governance requirements.
- [ ] It mentions consent, ethics, data-access agreements and institutional policies.
- [ ] It mentions storage location, access controls, encryption, audit logging, retention and transfer requirements.
- [ ] It states that a cost estimate does not constitute approval to store project data in AWS.
- [ ] It advises against entering participant-level or sensitive research data into the calculator.
- [ ] The notice is informational rather than alarming.
- [ ] The Data volume reference guide contains 4× WGS FASTQ and CRAM ranges.
- [ ] The guide contains 12× WGS FASTQ and CRAM ranges.
- [ ] Existing 30× WGS ranges remain.
- [ ] Existing WES/RNA-seq/array/joint VCF entries remain.
- [ ] No 4× or 12× WGS calculator profile has been added.
- [ ] No depth-based file-size calculation has been added.
- [ ] Existing WGS 30× defaults remain 100 GB FASTQ, 40 GB CRAM and 10 GB gVCF/QC per sample.
- [ ] No pricing or calculation logic has changed.
- [ ] Existing tests pass.
- [ ] Both project modes render without errors.