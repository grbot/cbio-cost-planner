# 005 — Pricing Sources and Planning Disclaimer

## Objective

Improve the transparency and credibility of the CBIO Genomics Infrastructure Cost Planner by clearly documenting:

1. where the AWS pricing comes from;
2. which values are published prices versus planning assumptions;
3. when pricing was last verified;
4. that the calculator is a planning tool rather than an official quotation.

This is a documentation/UI change only.

**Do not change any calculation logic, pricing values, project defaults, sensitivity calculations, existing functionality, or GRO styling.**

---

## 1. Add a "Pricing & assumptions" section

Add a compact section near the bottom of the application, after the calculator results/sensitivity content and before the final footer.

Use the existing GRO section styling.

Heading:

### Pricing & assumptions

Text:

> AWS storage, request, archive retrieval and data-transfer costs are based on published AWS pricing for the Africa (Cape Town) region (`af-south-1`). Prices are planning estimates and should be verified against current AWS/UCT pricing before budgeting or procurement.

Then show:

**AWS pricing source:**  
https://aws.amazon.com/s3/pricing/

**AWS region:**  
Africa (Cape Town) — `af-south-1`

**Pricing last verified:**  
31 August 2026

If `pricing_last_verified` and the pricing source already exist in the application's configuration, read and display them from configuration rather than duplicating the values in the UI.

If the source URL is already stored in configuration, use that value.

Make the AWS pricing source a clickable link.

---

## 2. Explain planning assumptions

Immediately below the AWS pricing information, add a short explanation:

> Data volumes, workflow data movement, retention periods, exchange rate, VAT and engineering effort are configurable planning assumptions. Compute costs are not currently included.

Keep this concise.

The purpose is to distinguish between:

- published AWS prices;
- project/workflow assumptions;
- CBIO operational assumptions.

Do not imply that AWS has validated the resulting project estimate.

---

## 3. Engineering-rate clarification

Where the engineering/support rate is displayed, make it clear that it is not an approved UCT or CBIO charge.

Use wording such as:

> **Illustrative engineering rate:** R1,000/hour

and immediately below or alongside it:

> Planning assumption only — not an approved UCT/CBIO institutional rate.

Do not change the current R1,000/hour default.

The rate must remain configurable exactly as it is now.

---

## 4. AWS pricing versus planning assumptions

Where practical without making the interface cluttered, make the distinction clear between:

### Published AWS pricing

Examples:

- S3 Standard storage price
- Glacier storage prices
- request charges
- retrieval charges
- internet data-transfer charges

and:

### CBIO/project planning assumptions

Examples:

- FASTQ GB/sample
- CRAM GB/sample
- gVCF/QC GB/sample
- active-storage duration
- archive duration
- archive class selection
- workflow read/pass counts
- CRAM retrieval percentage
- transfer contingency
- exchange rate
- engineering hours
- engineering hourly rate

This does not require redesigning the application.

Prefer concise explanatory text or existing expanders/help text rather than adding many new cards.

---

## 5. Final disclaimer

Add a restrained footer/disclaimer at the bottom of the application:

> **Prototype planning tool — estimates should be validated before budgeting or procurement.**

Below this, in smaller/muted text:

> Actual costs may vary with AWS pricing, exchange rates, data volumes, access patterns, network path, retrieval behaviour and institutional agreements.

Use the existing muted-text styling from the GRO theme.

Do not use a warning/error colour. This is normal planning guidance, not an application warning.

---

## 6. Source transparency in exports

If the application already exports Markdown, JSON or CSV calculation summaries, add pricing provenance to the appropriate metadata where this can be done without changing the existing export structure substantially.

For Markdown/JSON, include where appropriate:

- AWS region: `af-south-1`
- pricing source
- pricing last verified date
- currency/exchange-rate assumption
- VAT assumption
- statement that engineering rates are illustrative
- statement that compute is not included

Do not add the full disclaimer repeatedly throughout exported data.

For CSV, do not complicate the tabular format solely to accommodate this requirement if there is no clean metadata mechanism.

---

## 7. Configuration remains the source of truth

Do not hard-code pricing values into the Streamlit UI.

The existing pricing configuration must remain the source of truth for AWS rates.

Where available, display:

- pricing source
- pricing verification date
- AWS region

from configuration.

If any of these metadata fields do not currently exist, add them to the pricing configuration rather than embedding them only in `app.py`.

Suggested structure:

```yaml
provider: AWS
region_name: Africa (Cape Town)
region_code: af-south-1
pricing_source: https://aws.amazon.com/s3/pricing/
pricing_last_verified: 2026-08-31