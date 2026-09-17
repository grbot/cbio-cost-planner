# 010c — Simplify Application Header

## Purpose

Simplify the branding/header of the:

CBIO Genomics Infrastructure Cost Planner

The graphical logo work is being deferred until later.

The application should use a clean typography-first identity with the
primary application navigation immediately underneath it.

This is a presentation/navigation-layout change only.

Do not modify calculator logic, project models, pricing, assumptions,
exports, or calculations.


# 1. Application identity

The application header should contain only:

CBIO

Genomics Infrastructure Cost Planner

Keep this application name exactly.

Do not rename the application.


# 2. Remove graphical logo

Remove the DNA / infrastructure SVG mark from the application header.

Do not display:

assets/branding/cbio-infrastructure-mark.svg

in the application.

Do not redesign or replace the graphical mark in this task.

The graphical identity may be revisited later.

Existing branding/reference assets may remain in the repository for
future use unless there is a strong technical reason to remove them.


# 3. Remove strapline

Remove:

STORAGE | COMPUTE | TRANSFER

from the branding header completely.


# 4. Remove branding divider

Remove the decorative divider associated with:

STORAGE | COMPUTE | TRANSFER

Do not replace it with another decorative separator inside the branding
block.


# 5. Typography-first identity

The visible application identity should therefore simply be:

CBIO
Genomics Infrastructure Cost Planner

Use the existing GRO visual language.

Preferred colours:

CBIO:
#042C5B

Genomics Infrastructure Cost Planner:
#172B3A


# 6. Typography hierarchy

CBIO should remain the dominant identity.

Desktop target:

CBIO:
approximately 40–44 px
Aptos Display Bold or appropriate system fallback

Genomics Infrastructure Cost Planner:
approximately 24–28 px
Aptos Display / Aptos or appropriate system fallback

The application name should have strong visual presence.

It should not look like ordinary body text.


# 7. Streamlit navigation clearance

Ensure the application identity begins clearly below Streamlit's fixed
top UI/navigation.

Neither:

CBIO

nor:

Genomics Infrastructure Cost Planner

may be clipped or hidden behind Streamlit's fixed interface.

Do not solve clipping by shrinking the typography.

Use appropriate layout spacing/top offset instead.


# 8. Primary application navigation

Position the existing top-level application navigation immediately
underneath:

Genomics Infrastructure Cost Planner

The navigation is:

Storage
Compute
Transfer
Project Summary

The desired visual structure is:

CBIO
Genomics Infrastructure Cost Planner

Storage     Compute     Transfer     Project Summary

[page content]

The navigation should visually feel like part of the application header.


# 9. Preserve navigation architecture

Keep the existing:

st.navigation
st.Page

architecture introduced in 010.

Do NOT replace this with:

- radio buttons;
- custom page-state switching;
- manually implemented navigation;
- another navigation framework

simply to obtain different styling.

Work with Streamlit's existing navigation architecture.


# 10. Navigation placement

Move/work the navigation visually so that it sits directly below the
application name rather than feeling detached from the branding.

Target approximately:

12–20 px

between:

Genomics Infrastructure Cost Planner

and the navigation area.

Use the closest clean implementation Streamlit allows.

Avoid large empty vertical gaps.


# 11. Navigation appearance

Navigation labels:

Storage
Compute
Transfer
Project Summary

should be clearly readable.

Suggested visual size:

approximately 15–17 px

The active page should be clearly identifiable using the existing
GRO navy/teal visual language where Streamlit allows this.

Navigation should remain visually subordinate to:

CBIO
Genomics Infrastructure Cost Planner

Avoid:

- oversized buttons;
- card-style navigation;
- excessive borders;
- decorative icons unless already inherent to Streamlit navigation.


# 12. Header alignment

Where practical, align:

CBIO

Genomics Infrastructure Cost Planner

Storage | Compute | Transfer | Project Summary

to the same main content grid.

The three levels should visually read as one coherent application
identity and navigation system.


# 13. Header spacing

The simplified header should use considerably less vertical space than
the previous logo-based implementation.

Use purposeful whitespace.

Avoid:

- large empty areas;
- excessive margins;
- unnecessary separators;
- oversized header containers.

The hierarchy should come primarily from typography rather than empty
space.


# 14. Relationship to page content

After the navigation, begin the current page content with enough
separation to make the hierarchy clear.

Conceptually:

CBIO
Genomics Infrastructure Cost Planner
Storage     Compute     Transfer     Project Summary

------------------------------------------------ page content

01 Storage Planning
...

Do not repeat:

CBIO Genomics Infrastructure Cost Planner

inside individual pages.


# 15. Responsive behaviour

At narrower widths:

- keep CBIO fully visible;
- keep Genomics Infrastructure Cost Planner readable;
- allow the application title to wrap only when genuinely necessary;
- allow Streamlit navigation to use its supported responsive behaviour;
- do not recreate custom mobile navigation;
- avoid horizontal scrolling;
- avoid excessive top whitespace.

The header should remain intentionally composed at approximately:

1440 px
1024 px
768 px
600 px


# 16. Desired visual character

The header should feel:

- simple;
- technical;
- professional;
- restrained;
- content-first;
- consistent with GRO.

Do not introduce:

- graphical logos;
- DNA graphics;
- infrastructure icons;
- gradients;
- shadows;
- header cards;
- illustrations;
- decorative straplines.


# 17. Remove obsolete header rendering

Remove obsolete active rendering/CSS associated specifically with:

- the SVG graphical mark;
- DNA/infrastructure logo positioning;
- logo/text horizontal layout;
- stacked-logo responsive behaviour;
- STORAGE | COMPUTE | TRANSFER;
- the strapline divider;
- spacing that existed solely to accommodate the graphical logo.

Do not leave obsolete CSS actively affecting the simplified header.

The branding assets themselves may remain in the repository for possible
future use.


# 18. Do not modify functionality

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
- Compute placeholder functionality;
- Transfer placeholder functionality;
- Project Summary calculations.


# 19. Visual validation

Perform browser-based visual validation at approximately:

- 1440 px;
- 1024 px;
- 768 px;
- 600 px.

Verify:

- CBIO is fully visible;
- Genomics Infrastructure Cost Planner is fully visible;
- neither is obscured by Streamlit UI;
- no graphical logo is displayed;
- no STORAGE | COMPUTE | TRANSFER strapline remains;
- the old decorative divider is removed;
- Storage / Compute / Transfer / Project Summary appear immediately
  beneath the application identity;
- navigation remains functional;
- active-page state is clear;
- header height is substantially reduced;
- spacing is compact and intentional;
- narrow layouts remain usable.


# 20. Regression validation

Verify:

- Storage loads;
- WGS 30× mode works;
- Custom Project works;
- Compute loads;
- Transfer loads;
- Project Summary loads;
- navigation works;
- exports work;
- calculations remain unchanged;
- existing tests pass.


# 21. Documentation

Review:

docs/design-and-assumptions.md

Do not rename the application.

The application remains:

CBIO Genomics Infrastructure Cost Planner

Only update documentation if necessary to reflect the simplified
header/navigation presentation.

Do not add implementation-level styling noise or changelog entries.


# 22. Implementation report

At completion report:

1. files changed;
2. obsolete branding elements removed;
3. simplified header implementation;
4. navigation/header integration;
5. final typography and spacing;
6. viewport sizes visually tested;
7. tests run and results;
8. any Streamlit limitation preventing the navigation from sitting as
   close beneath the application title as intended.

Do not implement Compute or Transfer functionality in this task.