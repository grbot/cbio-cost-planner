# 010 — Application Architecture and Navigation

## Purpose

Refactor the CBIO Genomics Infrastructure Cost Planner so that it can
grow from the current storage calculator into a broader genomics
infrastructure planning tool.

The intended application architecture is:

1. Storage
2. Compute
3. Transfer
4. Project Summary

This change should establish the architecture and navigation required
for those modules.

It should NOT yet implement the full Compute or Transfer calculators.

The existing Storage calculator must continue to work and its current
calculations must not change as a side effect of this refactor.


# 1. Design principle

The application should represent one genomics project.

Storage, Compute and Transfer are different infrastructure dimensions
of the same project.

The architecture should therefore become:

                    PROJECT
                       |
        +--------------+--------------+
        |              |              |
        v              v              v
     STORAGE        COMPUTE        TRANSFER
        |              |              |
        +--------------+--------------+
                       |
                       v
                PROJECT SUMMARY


The project definition should be shared between modules rather than
each module independently asking for the same information.


# 2. Application navigation

Replace the current storage-centric application structure with
top-level navigation for:

- Storage
- Compute
- Transfer
- Project Summary

The exact Streamlit navigation mechanism may be chosen based on what
best fits the existing application architecture.

The interface should remain simple and should not feel like four
separate applications.


# 3. Current implementation status

After this change:

## Storage

Status: IMPLEMENTED

The existing storage functionality should remain operational.

This includes:

- WGS 30× project mode
- Custom Project mode
- storage volume calculations
- lifecycle/archive calculations
- AWS pricing
- transfer/egress assumptions currently used specifically by the
  storage cost model
- engineering cost assumptions
- sensitivity calculations
- exports
- pricing provenance
- governance guidance
- data-volume guidance

Do not materially change existing storage calculations in this task.


## Compute

Status: PLANNED

Create a placeholder module/page only.

The placeholder should briefly explain that Compute will eventually
estimate:

- workflow stages
- CPU/GPU requirements
- memory
- runtime
- concurrency
- temporary/working storage
- cloud/HPC execution options
- software/licensing costs
- expected completion time

Do not implement these calculations yet.


## Transfer

Status: PLANNED

Create a placeholder module/page only.

The placeholder should briefly explain that Transfer will eventually
estimate:

- data movement between infrastructure endpoints
- expected transfer volume
- measured or assumed throughput
- transfer duration
- network constraints
- transfer method
- transfer-related cloud costs

Do not implement these calculations yet.


## Project Summary

Status: PLANNED / PARTIALLY AVAILABLE

Create a summary page that can display the project information already
known from the Storage module.

For now it may contain:

- project type
- sample count where applicable
- durable data volume
- retention period
- selected storage lifecycle
- estimated storage-related cost
- engineering cost
- relevant assumptions

It should clearly indicate that Compute and Transfer results will be
added in later development stages.

Do not invent compute or transfer values.


# 4. Shared project model

Introduce or prepare a shared project-level model that can eventually
be consumed by Storage, Compute and Transfer.

Do not over-engineer this.

The goal is to prevent duplicated project definitions as the
application grows.

Conceptually:

Project
    metadata
    datasets
    storage configuration
    compute configuration
    transfer configuration

Not all sections need to be populated yet.


# 5. Dataset model

The existing WGS 30× and Custom Project modes should increasingly
converge on a common dataset representation.

Conceptually a dataset may contain:

- name
- data type
- size
- unit
- durable / temporary classification
- retention
- archive/storage class
- expected read/retrieval behaviour

The current WGS 30× template should remain a convenience template that
creates the appropriate datasets.

For example:

500 × 30× WGS

FASTQ
    approximately 50,000 GB

CRAM
    approximately 20,000 GB

gVCF / QC
    approximately 5,000 GB

The existing calculation logic remains authoritative.


# 6. Durable versus temporary storage

Establish an important architectural distinction:

## Durable storage

Belongs to the Storage module.

Examples:

- FASTQ
- CRAM
- gVCF
- released VCF
- QC outputs
- manifests
- retained project outputs


## Temporary / working storage

Belongs to the future Compute module.

Examples:

- sort temporary files
- workflow work directories
- DeepVariant intermediate files
- temporary BAM/CRAM processing files
- container/cache working space
- cohort-calling temporary files


Do not add temporary compute storage to the current durable storage
cost calculation.

This distinction should be reflected in the code architecture and
documentation.


# 7. Transfer staging

Transfer staging should ultimately belong to the Transfer module rather
than durable Storage.

Examples may include:

- temporary upload staging
- transfer buffers
- resumable transfer working areas

Do not implement transfer staging calculations yet.


# 8. Preserve the current WGS regression case

The existing WGS planning case must continue to produce the same
results after the architecture refactor.

Important regression case:

500 samples
30× WGS

Planning data volumes:

FASTQ:
500 × 100 GB = 50,000 GB

CRAM:
500 × 40 GB = 20,000 GB

gVCF/QC:
500 × 10 GB = 5,000 GB

Durable data:
75,000 GB

Expected workflow reads:

FASTQ:
50,000 × 100% × 1 pass

CRAM:
20,000 × 10% × 1 pass

gVCF:
5,000 × 100% × 2 passes

Base:
62,000 GB

With 20% contingency:

74,400 GB

Using the calculator convention:

1 TB = 1024 GB

74,400 GB = 72.65625 TB

The refactor must not alter this behaviour.


# 9. Branding preparation

Create the following directory if it does not already exist:

assets/branding/

The approved visual reference for the application branding will be
stored as:

assets/branding/cbio-infrastructure-banner-reference.png

Do not attempt to redesign the logo in this task.

Do not depend on the reference PNG for core application functionality.

A production SVG mark/header will be implemented separately.


# 10. GRO visual language

Continue using the established GRO visual language.

Primary colours:

Navy:
#042C5B

Teal:
#0B8BA5

Dark blue-grey:
#172B3A

Body text:
#111111

Application background:
#F2F5F7

Main content:
#FBFCFD

Panels:
#FFFFFF

Panel border:
#E3E8EC

Muted text:
#667580


Typography:

Headings/display:
Aptos Display

Body:
Aptos

Use sensible fallbacks where the browser does not provide Aptos.

Do not bundle or distribute font files.


# 11. Navigation styling

The new Storage / Compute / Transfer / Project Summary navigation
should feel like part of the existing GRO-styled application.

Requirements:

- restrained
- technical
- professional
- no gradients
- no shadows
- no oversized cards
- clear active state
- navy/teal accents
- generous whitespace

Avoid making the navigation visually dominate the calculator.


# 12. Application title

The application name remains:

CBIO Genomics Infrastructure Cost Planner

The conceptual strapline is:

STORAGE | COMPUTE | TRANSFER

Do not rename the project.


# 13. AI

AI functionality is explicitly OUT OF SCOPE for this task.

The calculator must remain deterministic.

Future AI functionality may provide an optional advisory/explanation
layer over deterministic results, but it must not become part of the
calculation engine.

Do not add:

- LLM APIs
- chatbot functionality
- API keys
- model dependencies
- AI-generated infrastructure calculations


# 14. Do not implement yet

Do NOT implement in this task:

- AWS compute costing
- instance selection
- AWS Batch
- Slurm configuration
- Nextflow execution
- BWA-MEM2 runtime modelling
- DeepVariant runtime modelling
- GLnexus runtime modelling
- Sentieon modelling
- ICA/DRAGEN modelling
- network throughput calculations
- RTT/BDP calculations
- transfer duration calculations
- transfer method recommendations
- AI adviser


These belong to later instructions.


# 15. Documentation

Review:

docs/design-and-assumptions.md

Update it only where this architectural change materially affects the
document.

Document:

- Storage / Compute / Transfer / Summary architecture
- shared Project concept
- durable versus temporary storage distinction
- transfer staging ownership
- module implementation status

Do not turn the design document into a changelog.

The design document describes what the system currently means and why.


# 16. Tests

Existing tests must continue to pass.

Add tests where necessary for:

- shared project model
- WGS template conversion into datasets
- preservation of current WGS calculations
- module/navigation state where appropriate

The 500 × 30× WGS regression case is especially important.

No existing calculation should change merely because the UI and model
architecture have been reorganised.


# 17. Repository inspection

Before implementation:

1. inspect the current repository structure;
2. identify the current Streamlit entry point;
3. identify where project/storage models currently live;
4. identify where session state is used;
5. identify existing tests;
6. identify the current styling implementation;
7. identify how exports obtain their project information.

Refactor the existing implementation rather than creating duplicate
parallel logic.


# 18. Validation

After implementation:

- run the test suite;
- run any formatting/linting already configured by the repository;
- confirm the application starts;
- confirm Storage still works;
- confirm WGS 30× still works;
- confirm Custom Project still works;
- confirm exports still work;
- confirm the 500-sample regression case remains unchanged;
- confirm Compute and Transfer do not fabricate results;
- confirm Project Summary only shows information actually available.


# 19. Implementation report

At completion provide a concise report containing:

1. files changed;
2. architectural changes made;
3. tests run and results;
4. confirmation of the 500 × 30× regression case;
5. any assumptions made;
6. any issues or technical debt discovered;
7. recommended next implementation step.

Do not implement the recommended next step as part of this task.