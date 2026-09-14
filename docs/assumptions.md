# Assumptions and known simplifications

This tool is a **cost-modelling proof of concept** for early-stage CBIO
project planning and grant budgeting. It is **not** an AWS billing system
and does not call any cloud provider APIs. Every number it produces is an
estimate derived from the editable assumptions in `config/` and in the
Streamlit UI.

## Units: 1 TB = 1024 GB

Per the original request, this project uses **1 TB = 1024 GB** throughout
(`cbio_cost/units.py`), to stay consistent with the existing CBIO proposal.
This is neither pure SI decimal (1 TB = 1000 GB) nor IEC binary (1 TiB =
1024 GiB) — it is a project-specific convention, isolated in one module so
it can be changed later without touching calculation logic.

Note: the illustrative worked example in the original request (500 x 30x
WGS -> "75 TB") uses round decimal (1000 GB/TB) arithmetic for readability.
With the 1024 GB/TB convention this tool actually uses, the same 75,000 GB
raw volume displays as **73.2 TB**, and the 90,000 GB envelope as **87.9
TB**. The underlying GB figures match the spec's worked example exactly;
only the TB *display* conversion differs, per the project's own explicit
unit-convention requirement.

## Pricing data — all placeholders, unverified

Every price in `config/aws-pricing.yaml` is marked
`pricing_last_verified: "UNVERIFIED"` with a `source` note that it is an
approximate placeholder. Before using this tool for real budgeting:

- Confirm current AWS af-south-1 (Cape Town) list prices for S3 Standard,
  Glacier Instant/Flexible/Deep Archive, internet data transfer out, and S3
  request pricing.
- Confirm an approved USD/ZAR exchange rate and VAT rate (defaults:
  16.05, 15%, as of 2026-09-14).
- Replace the R1,000/hour engineering rate with an approved CBIO/UCT loaded
  technical staff rate.

## Simplifications in the cost model

- **S3/API/lifecycle request costs** are estimated from data volume using
  an assumed average object size of 5 GB (`AVG_OBJECT_SIZE_GB` in
  `cbio_cost/storage.py`), not from actual file counts (which this tool
  does not track). This is a coarse planning approximation.
- **Glacier retrieval fees** are modelled as a single USD/GB rate per
  storage class. Real AWS pricing has multiple retrieval speed tiers
  (expedited/standard/bulk) with different costs; this is not modelled in
  V1.
- **The AWS egress free allowance** is treated as a single one-time
  deduction from total planned egress for the project, not a recurring
  monthly allowance. This tool estimates project-lifetime cost, not a
  month-by-month bill.
- **Active-period storage pricing** uses one tiered lookup against the
  provisioned envelope, applied uniformly across the active months, rather
  than simulating month-by-month volume growth.
- **VAT** is applied to AWS costs (USD -> ZAR) only. Engineering/staff costs
  are shown as plain ZAR figures; the spec does not indicate VAT should
  apply to internal staff time.
- **Compute cost is not modelled.** Per the request, Ilifu compute/fairshare
  cost is explicitly out of scope for V1 and shown as "Compute cost /
  entitlement not yet included."

## Sensitivity-analysis scenario definitions

Defined in `config/project-profiles.yaml` under `scenarios`, these three
named overlays hold storage volumes, archive-class choices, and engineering
assumptions constant, and vary only the data-movement parameters, to isolate
the effect of transfer behaviour on total project cost:

| Scenario | FASTQ passes | CRAM retrieval % | CRAM passes | gVCF passes | Contingency |
|---|---:|---:|---:|---:|---:|
| Low movement | 1 | 5% | 1 | 1 | 10% |
| Expected | 1 | 10% | 1 | 2 | 20% |
| High movement | 2 | 25% | 1 | 3 | 40% |

## Decimal arithmetic

All calculations use Python's `Decimal` type end-to-end (never `float`) to
avoid floating-point rounding artifacts in financial figures. Rounding only
happens at display/formatting time (UI metrics, export text), never inside
`cbio_cost/*` calculation logic. Percentages and fractions are stored
internally as `Decimal` fractions in `[0, 1]` (e.g. 20% is `Decimal("0.20")`);
UI code converts from user-facing percent inputs.
