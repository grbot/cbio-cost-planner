# CBIO Genomics Infrastructure Cost Planner

**v1.0.0**

A Streamlit application for CBIO that estimates the infrastructure cost of
hosting and processing genomics projects — initially WGS projects using
AWS S3 (`af-south-1`) for durable/archive storage and Ilifu for compute
and scratch, with data movement modelled as an explicit project cost.

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

The app has a shared **Project** area (project type, name, sample count,
retention, "Load Example" and "New project") at the top of every page,
followed by four top-level pages:

```text
Configure Project
      ↓
Storage
      ↓
Compute
      ↓
Transfer
      ↓
Project Summary
```

A fresh session starts genuinely **unconfigured** — each page shows brief
guidance instead of fabricating a project nobody has set up. Click
**"Load 500 x 30x WGS / 5-year demo profile"** in the Project area for a
ready-made example, or configure a project yourself (WGS 30x or Custom
Project).

## Tests

```bash
pytest
```

## Project structure

```text
cbio-cost-planner/
├── app.py                      # Entry point: page config, theme, header, project bootstrap, top navigation
├── navigation.py                # st.Page definitions for the four top-level pages
├── project_setup.py             # Shared Project area (type/name/samples/retention, Load Example, New project)
├── data_volume_guide.py         # Static reference data for the Data volume reference guide
├── theme.py                     # GRO visual style (Streamlit CSS injection) — UI-only
├── views/                       # One module per top-level page
│   ├── storage.py                 # Storage UI (WGS 30x / Custom Project) — no calculation logic here
│   ├── compute.py                  # Compute UI (WGS 30x scope)
│   ├── transfer.py                  # Transfer UI (WGS 30x and Custom Project)
│   └── summary.py                    # Project Summary — reads canonical ProjectState, computes nothing
├── config/
│   ├── aws-pricing.yaml         # AWS pricing assumptions (placeholders — see docs/assumptions.md)
│   └── project-profiles.yaml    # Demo project profile + sensitivity scenarios
├── cbio_cost/                   # Calculation engine (framework-independent)
│   ├── units.py                   # GB/TB conversion (1 TB = 1024 GB)
│   ├── config.py                   # YAML config loading/validation
│   ├── models.py                    # Typed dataclasses for storage inputs/pricing/results
│   ├── evidence.py                   # Evidence classification (Measured/Published/Planning/...)
│   ├── project.py                     # Shared cross-module Project read-model
│   ├── project_state.py                # Canonical, session-level ProjectState (spec 012a/013)
│   ├── storage.py                       # Data volume, active + archive storage cost
│   ├── transfer.py                       # Storage's own AWS-egress cost assumption
│   ├── transfer_plan.py                   # Endpoint-to-endpoint Transfer planning engine
│   ├── transfer_plan_models.py             # Typed dataclasses for Transfer inputs/results
│   ├── compute.py                           # Compute runtime/working-storage planning engine
│   ├── compute_benchmarks.py                 # BWA-MEM2/DeepVariant benchmark constants
│   ├── compute_models.py                      # Typed dataclasses for Compute inputs/results
│   ├── operations.py                           # Engineering setup/ops/closeout cost
│   ├── calculator.py                            # Orchestration, scenarios, plain-English explanation
│   └── export.py                                 # CSV / JSON / Markdown export
├── tests/                        # Unit/regression tests for the calculation engines + app smoke test
├── requests/                     # Spec-driven development history (this project's own design record)
└── docs/
    ├── assumptions.md            # Assumptions, simplifications, pricing-verification checklist
    └── design-and-assumptions.md # Architecture decisions, evidence, decision record (see below)
```

## Design documentation

See [`docs/design-and-assumptions.md`](docs/design-and-assumptions.md) for
architecture decisions, planning assumptions, benchmark provenance and
open research questions.

## Scope

Implemented in this V1 release:

- shared project configuration (WGS 30x / Custom Project), with a
  genuinely unconfigured starting state until you configure or load the
  example project;
- durable storage/envelope modelling, S3 lifecycle-transition to Glacier
  storage classes, and planned workflow-egress estimates;
- compute resource and runtime planning for the WGS 30x open-source
  reference workflow (BWA-MEM2, CRAM indexing, DeepVariant);
- endpoint-to-endpoint transfer volume, throughput and duration planning,
  with known-provider transfer cost where calculable;
- a consolidated Project Summary that always reflects the current project
  and marks any stale module result as "Needs review" rather than
  presenting it as current;
- configurable AWS pricing/FX/VAT assumptions, a Low/Expected/High
  sensitivity comparison, full calculation-detail auditability, and
  CSV/JSON/Markdown export.

**Not implemented yet** (see
[`docs/design-and-assumptions.md` §15](docs/design-and-assumptions.md)
for the full list): Compute infrastructure monetary costing, AWS
instance-type recommendations, Ilifu/HPC monetary costing, GLnexus cohort
compute, Sentieon/DRAGEN/ICA execution modelling, authentication, a
database, live AWS API calls, and PDF report generation. Transfer is
planning only — it does not execute or schedule an actual data transfer.
