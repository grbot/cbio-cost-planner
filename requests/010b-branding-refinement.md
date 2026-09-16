# 010b — Branding Header Refinement

## Purpose

Refine the application branding/header introduced in 010a based on
visual inspection of the deployed Streamlit application.

This is a visual-only correction.

Do not modify calculator logic, project models, navigation architecture,
pricing, assumptions, exports, or calculations.


# 1. Problems identified in deployed application

A read-only visual review identified the following issues.

## Definite layout bug

The branding header overlaps the fixed Streamlit navigation.

Observed behaviour:

- at 1440 px and 768 px widths, the custom header begins at approximately
  y=53 px;
- Streamlit's fixed navigation occupies approximately the first 58–60 px;
- the top of "CBIO" is therefore hidden;
- at approximately 600 px width, the stacked logo is also clipped.

This is primarily a navigation/header overlap and top-offset problem.

It is NOT primarily a CBIO line-height problem.

The existing CBIO typography is approximately:

- font size: 41–42 px;
- line height: approximately 44 px.

Do not solve this by simply reducing the CBIO font size.


# 2. Fix navigation/header overlap

The first visible branding content must begin clearly below Streamlit's
fixed navigation.

Target approximately:

72–80 px from the top of the viewport

on normal desktop layouts, giving approximately:

16–24 px

of visual clearance below the fixed navigation.

Implement this robustly rather than relying on accidental margins.

Verify the behaviour at multiple viewport widths.

Do not introduce excessive whitespace once the overlap is corrected.


# 3. Improve the SVG mark

The current SVG technically contains:

- DNA double helix;
- storage node;
- compute node;
- transfer node.

However, at deployed size it does not immediately read as a DNA helix.

It currently resembles a generic network diagram or plumbing glyph.

Refine:

assets/branding/cbio-infrastructure-mark.svg

using:

assets/branding/cbio-infrastructure-banner-reference.png

as the approved visual reference.


## DNA helix

Make the DNA double helix the dominant visual feature of the mark.

It should be immediately recognisable as DNA even before the viewer
examines the infrastructure nodes.

Improve:

- strand curvature;
- strand separation;
- alternating visual crossover;
- helix rhythm;
- connecting base-pair/rung structure where appropriate.

Keep the geometry clean and technical rather than illustrative.

Do not make the helix overly detailed.


## Infrastructure nodes

Retain the three conceptual nodes:

1. storage/database;
2. compute/chip;
3. bidirectional transfer.

Increase the internal symbols enough that they remain recognisable at
normal application-header size.

The symbols should not become decorative micro-details that disappear
when the SVG is scaled down.


## Connectors

The connectors currently compete visually with the DNA helix.

Reduce their visual dominance.

Use thinner/lighter connector geometry relative to the DNA strands and
node outlines.

The intended reading should be:

DNA → infrastructure

rather than:

network diagram with DNA attached.


# 4. Mark size

Desktop target:

approximately 105–120 px high.

Do not simply scale the existing problematic geometry.

First improve its visual legibility, then size it appropriately.


# 5. Mark/text relationship

Reduce the horizontal gap between the SVG mark and text block.

Target approximately:

16–20 px

rather than the current approximately 24 px.

Vertically align the mark more deliberately with the overall text block.

The mark should not appear to hang noticeably below the CBIO/title
composition.


# 6. CBIO typography

Keep CBIO visually prominent.

Target:

40–44 px

on normal desktop widths.

Do not reduce CBIO merely to work around the navigation overlap.

Fix the actual overlap instead.


# 7. Application title

Use:

Genomics Infrastructure Cost Planner

Target approximately:

24–27 px

on normal desktop widths.

Keep the title on ONE LINE at normal desktop widths.

The title should remain clearly secondary to CBIO but substantially more
prominent than ordinary application text.


# 8. Strapline

The current:

STORAGE | COMPUTE | TRANSFER

is approximately 12–13 px and appears too small relative to the
navigation and body typography.

Increase it to approximately:

14–15 px

Use semibold weight.

Reduce excessive letter spacing if necessary.

It should remain subordinate to the application title but should be
comfortably readable.


# 9. Divider

The current divider has approximately 32 px vertical margins and creates
too much dead space.

Tighten this relationship.

Target approximately:

16–20 px above the divider

and:

14–18 px below the divider.

The exact implementation may vary slightly depending on typography.

The divider should visually connect:

Genomics Infrastructure Cost Planner

with:

STORAGE | COMPUTE | TRANSFER

rather than separating them into unrelated blocks.

Align the divider deliberately with the text block.

Do not use an arbitrary full-width line.


# 10. Reduce unnecessary header height

The current header consumes substantial vertical space without gaining
equivalent visual presence.

After fixing the clipping:

- tighten internal spacing;
- reduce unnecessary dead space;
- keep generous but purposeful whitespace;
- make the branding visually stronger without making the header taller.

Do not solve the hierarchy problem by simply increasing every element.


# 11. Responsive layout

The approximately 768 px layout is currently generally stable and should
remain so.

At the stacked/mobile breakpoint:

- stack the graphical mark and text intentionally;
- use a mark approximately 72–88 px high;
- use approximately 10–14 px between the mark and CBIO;
- ensure neither mark nor text is hidden behind Streamlit navigation;
- retain clear hierarchy;
- avoid horizontal scrolling.

The stacked composition should look deliberate rather than like a
desktop layout that happened to wrap.


# 12. Preserve production architecture

Continue using:

assets/branding/cbio-infrastructure-mark.svg

as the production graphical asset.

The PNG:

assets/branding/cbio-infrastructure-banner-reference.png

remains a DESIGN REFERENCE ONLY.

Do not display the reference PNG in the application.

The SVG must contain only the graphical mark.

Application wording must remain real application text.


# 13. Preserve GRO visual language

Use exact GRO colours:

Navy:
#042C5B

Teal:
#0B8BA5

Dark blue-grey:
#172B3A

Do not introduce:

- gradients;
- shadows;
- unnecessary cards;
- decorative effects;
- additional colours.


# 14. Do not modify application functionality

Do NOT modify:

- Storage calculations;
- AWS pricing;
- archive calculations;
- workflow egress calculations;
- engineering calculations;
- sensitivity analysis;
- WGS modelling;
- Custom Project modelling;
- exports;
- Compute placeholder behaviour;
- Transfer placeholder behaviour;
- Project Summary calculations;
- top-level navigation architecture.


# 15. Visual validation

Perform an actual browser-based visual check after implementation.

Check at minimum approximately:

- 1440 px desktop;
- 1024 px;
- 768 px;
- 600 px / narrow layout.

Verify:

- CBIO is completely visible;
- SVG is completely visible;
- no content sits behind Streamlit navigation;
- DNA is immediately recognisable as a double helix;
- storage icon is recognisable;
- compute icon is recognisable;
- transfer icon is recognisable;
- connectors do not dominate the mark;
- application title has appropriate visual presence;
- strapline is comfortably readable;
- divider spacing is tighter;
- mark/text alignment is intentional;
- desktop title remains on one line;
- stacked layout looks deliberate.


# 16. Regression validation

Verify:

- Storage loads;
- WGS 30× mode works;
- Custom Project works;
- Compute page loads;
- Transfer page loads;
- Project Summary loads;
- navigation works;
- exports still work;
- calculations remain unchanged;
- existing tests pass.


# 17. Documentation

Review:

docs/design-and-assumptions.md

Only update it if this refinement materially changes documented
application design.

Do not add visual implementation details or changelog noise.


# 18. Implementation report

At completion report:

1. files changed;
2. cause and fix for navigation/header overlap;
3. SVG geometry changes;
4. final desktop dimensions;
5. final responsive dimensions/breakpoint behaviour;
6. viewport sizes visually tested;
7. tests run and results;
8. any remaining Streamlit-specific limitations.

Do not implement Compute or Transfer functionality in this task.