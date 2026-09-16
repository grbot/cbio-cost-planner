# 010a — Application Branding Header

## Purpose

Implement the approved branding for the CBIO Genomics Infrastructure
Cost Planner.

This is a visual-only change.

Do not modify calculator logic, project models, navigation architecture,
pricing, assumptions, exports, or calculations.


# 1. Approved visual reference

The approved design reference is:

assets/branding/cbio-infrastructure-banner-reference.png

This PNG is a DESIGN REFERENCE ONLY.

It was generated during the design process and represents the approved
visual direction.

Do NOT use this PNG as the production application header.

Do NOT recreate the complete banner as another raster image.


# 2. Production asset

Create:

assets/branding/cbio-infrastructure-mark.svg

This SVG is the production graphical asset used by the application.

The SVG must contain ONLY the graphical mark.

It must NOT contain:

- CBIO
- Genomics Infrastructure Cost Planner
- STORAGE | COMPUTE | TRANSFER

All wording must be rendered as application text using HTML/CSS or the
appropriate Streamlit rendering mechanism.


# 3. SVG mark

Reproduce the graphical mark from the approved PNG reference.

The mark consists conceptually of:

                STORAGE NODE
                     ○
                     │
DNA HELIX ───────────┤
                     │
                COMPUTE NODE
                     ○
                     │
                     │
                TRANSFER NODE
                     ○

More specifically:

- a vertical DNA double helix on the left;
- three horizontal connectors;
- top circular node containing a storage/database symbol;
- middle circular node containing a compute/chip symbol;
- bottom circular node containing bidirectional transfer arrows.

Use the reference PNG for the exact visual relationship.

Simplify geometry where appropriate for a clean production SVG.

The mark should remain recognisable and crisp at approximately
105–125 px high.


# 4. GRO colours

Use exact GRO colours in the SVG and application header.

Primary navy:

#042C5B

Teal:

#0B8BA5

Dark blue-grey:

#172B3A

Background:

transparent

Do not use:

- gradients;
- shadows;
- photographic effects;
- raster elements inside the SVG.


# 5. Application header

Construct the production header from:

1. the SVG graphical mark;
2. application-rendered typography.

Desktop concept:

[ SVG MARK ]    CBIO
                Genomics Infrastructure Cost Planner
                ─────────────────────────────────────
                STORAGE | COMPUTE | TRANSFER


# 6. Header wording

Use exactly:

CBIO

Genomics Infrastructure Cost Planner

STORAGE | COMPUTE | TRANSFER


IMPORTANT:

On normal desktop widths:

Genomics Infrastructure Cost Planner

must appear on ONE LINE.

Do not deliberately split it into:

Genomics Infrastructure
Cost Planner


# 7. Typography

Preferred typography:

CBIO:
Aptos Display Bold

Genomics Infrastructure Cost Planner:
Aptos Display / Aptos

STORAGE | COMPUTE | TRANSFER:
Aptos SemiBold

Use sensible browser/system fallbacks when Aptos is unavailable.

Do not bundle, download, or distribute font files.


# 8. Approximate visual hierarchy

Desktop targets:

CBIO:
approximately 40–44 px

Genomics Infrastructure Cost Planner:
approximately 23–26 px

STORAGE | COMPUTE | TRANSFER:
approximately 12–14 px

SVG mark:
approximately 105–125 px high

Use these as visual guidance rather than rigid pixel requirements.


# 9. Divider

Place a thin teal horizontal rule between:

Genomics Infrastructure Cost Planner

and:

STORAGE | COMPUTE | TRANSFER

The divider should align naturally with the text block.

Do not extend it unnecessarily across the full application width.


# 10. Layout

The header should:

- sit directly on the normal application background;
- use generous whitespace;
- feel lightweight;
- not appear inside a card;
- not use shadows;
- not use gradients;
- avoid unnecessary borders;
- avoid a vertical separator unless technically necessary.

The SVG and typography should read visually as one application identity.


# 11. Responsive behaviour

The header must remain usable on narrower screens.

At smaller viewport widths it is acceptable to:

- reduce SVG size;
- reduce typography size;
- stack the mark above the wording;
- allow the application title to wrap.

The one-line title requirement applies to normal desktop widths.

Do not create horizontal scrolling merely to keep the title on one line.


# 12. Relationship to navigation

The branding header belongs above the top-level application navigation:

Storage
Compute
Transfer
Project Summary

Do not change the navigation architecture introduced in 010.

Do not duplicate the application title below the branding header.


# 13. Shared component

The same application identity should appear consistently on:

- Storage
- Compute
- Transfer
- Project Summary.

Avoid copying complex header code into each page.

Create a shared header component/helper where appropriate to the current
application architecture.


# 14. Accessibility

The application name must remain real text.

Do not rely on the SVG to communicate the application name.

The SVG may be treated as decorative where the adjacent text provides
the identity.

Maintain appropriate colour contrast.


# 15. Preserve existing GRO styling

Do not restyle unrelated application components.

Preserve:

- existing cards;
- navigation;
- input styling;
- tables;
- governance notices;
- section numbering;
- charts;
- exports.

This task is specifically about application identity/header branding.


# 16. Do not modify functionality

Do NOT modify:

- Storage calculations;
- AWS pricing;
- archive calculations;
- workflow egress calculations;
- engineering calculations;
- sensitivity analysis;
- WGS project modelling;
- Custom Project modelling;
- exports;
- Project Summary calculations;
- Compute placeholder behaviour;
- Transfer placeholder behaviour.


# 17. Documentation

Review:

docs/design-and-assumptions.md

Only update the document if the branding implementation is materially
relevant to the description of the application.

Do not add visual implementation noise or a changelog.


# 18. Validation

After implementation verify:

- SVG is used as the production logo mark;
- PNG is not displayed as the production banner;
- SVG uses exact GRO colours;
- SVG contains no embedded raster image;
- SVG contains no application wording;
- application wording is rendered as real text;
- title remains on one line at normal desktop widths;
- header renders on Storage;
- header renders on Compute;
- header renders on Transfer;
- header renders on Project Summary;
- navigation still works;
- WGS 30× still works;
- Custom Project still works;
- exports still work;
- existing calculations are unchanged;
- narrow/mobile layout remains usable;
- existing tests pass.


# 19. Implementation report

At completion report:

1. files changed;
2. SVG asset created;
3. shared header implementation;
4. responsive behaviour;
5. font fallback used;
6. tests run and results;
7. any Streamlit limitations encountered.

Do not implement Compute or Transfer functionality as part of this task.