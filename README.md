# CBIO Genomics Infrastructure Cost Planner

A small Streamlit application for CBIO that estimates the infrastructure
cost of hosting and processing genomics projects — initially WGS projects
using AWS S3 (`af-south-1`) for durable/archive storage and Ilifu for
compute and scratch, with AWS-to-Ilifu data transfer modelled as an
explicit project cost.

This is a **planning tool**, not an AWS billing system. See
[`docs/assumptions.md`](docs/assumptions.md) for the full list of
assumptions and simplifications — in particular, all cloud prices shipped
in `config/aws-pricing.yaml` are **unverified placeholders**.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

The app has four top-level pages: **Storage** (implemented), **Compute**
and **Transfer** (placeholders — planning scope only, no calculations
yet), and **Project Summary** (shows what Storage has computed so far).
Click **"Load 500 x 30x WGS / 5-year demo profile"** on the Storage page
for a ready-made example.

## Tests

```bash
pytest
```

## Project structure

```text
cbio-cost-planner/
├── app.py                    # Entry point: page config, theme, header, top navigation
├── views/                    # One module per top-level page (spec 010)
│   ├── storage.py             # Storage UI (WGS 30x / Custom Project) — no calculation logic here
│   ├── compute.py              # Compute placeholder (Planned — no calculations)
│   ├── transfer.py             # Transfer placeholder (Planned — no calculations)
│   └── summary.py               # Project Summary — reads the shared Project, computes nothing
├── config/
│   ├── aws-pricing.yaml      # AWS pricing assumptions (placeholders — see docs/assumptions.md)
│   └── project-profiles.yaml # Demo project profile + sensitivity scenarios
├── cbio_cost/                # Calculation engine (framework-independent)
│   ├── units.py               # GB/TB conversion (1 TB = 1024 GB)
│   ├── config.py               # YAML config loading/validation
│   ├── models.py                # Typed dataclasses for inputs/pricing/results
│   ├── project.py                # Shared cross-module Project model (spec 010 §4)
│   ├── storage.py                 # Data volume, active + archive storage cost
│   ├── transfer.py                 # Data movement / AWS egress cost
│   ├── operations.py                # Engineering setup/ops/closeout cost
│   ├── calculator.py                 # Orchestration, scenarios, plain-English explanation
│   └── export.py                      # CSV / JSON / Markdown export
├── theme.py                  # GRO visual style (Streamlit CSS injection) — UI-only
├── tests/                    # Unit/regression tests for the calculation engine + app smoke test
└── docs/assumptions.md        # Assumptions, simplifications, pricing-verification checklist
```

## Design documentation

See [`docs/design-and-assumptions.md`](docs/design-and-assumptions.md) for
architecture decisions, planning assumptions, benchmark provenance and
open research questions.

## Scope

Implemented in this first version: data volume/envelope modelling, the
FASTQ/CRAM/gVCF data-movement model, tiered AWS storage/egress pricing,
S3 lifecycle-transition to Glacier storage classes, infrastructure
engineering costing, USD/ZAR/VAT rollups, a Low/Expected/High sensitivity
comparison, calculation-detail auditability, and CSV/JSON/Markdown export.

**Not implemented yet** (by design): authentication, a database, live AWS
API calls, Terraform, Ilifu integration/compute charging, or PDF export.
