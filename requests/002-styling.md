# Restyle the existing Streamlit app using GRO styling

The calculator functionality and structure are correct.

**Do not redesign, restructure, remove or change any functionality.**

Do not change:
- calculations
- inputs
- defaults
- data model
- navigation
- output content
- charts/tables unless styling requires minor visual changes
- application behaviour

This task is **styling only**.

## Design objective

Make the application look like a polished internal UCT/CBIO genomics infrastructure tool using the GRO (Genomics Repository Orchestrator) visual language.

The desired feeling is:

**technical, calm, spacious, precise, professional.**

It should not look like:
- a default Streamlit application
- a SaaS marketing dashboard
- a Bootstrap admin template
- a colourful analytics dashboard

Think:

**research infrastructure planning tool / architecture console / professional technical report.**

---

# GRO palette

Use:

```text
Navy:          #042C5B
Teal:          #0B8BA5
Dark blue-grey:#172B3A
Body:          #111111
Background:    #FFFFFF
Light surface: #F7F9FA
Border:        #E3E8EC
Muted text:    #667580
```

The interface should be approximately:

**85–90% white/light neutral**
**8–10% navy**
**2–5% teal**

Do not flood the interface with GRO colours.

Teal is an accent, not a background colour.

---

# Typography

Prefer:

```text
Aptos
Aptos Display
```

with sensible fallbacks:

```css
font-family: "Aptos", "Segoe UI", Arial, sans-serif;
```

Main page title:
- dark navy
- strong but not oversized
- approximately 30–34 px
- moderate weight

Section headings:
- navy
- approximately 18–21 px
- strong hierarchy

Body:
- 14–16 px
- dark blue-grey/body colour

Supporting text:
- muted grey-blue
- smaller

Avoid excessive bold text.

---

# Page

Use a white overall background.

Increase the usable content width.

Aim for approximately:

```css
max-width: 1400px;
```

with comfortable horizontal padding.

Reduce the feeling that everything is floating in the middle of a large Streamlit page.

Use generous but controlled vertical whitespace.

---

# Header

Create a restrained GRO header.

Something visually similar to:

```text
GRO                                      CBIO | UCT

Genomics Infrastructure Cost Planner
Estimate storage, transfer and engineering costs for genomics projects
──────────────────────────────────────────────────────────────────────
```

GRO should be visually identifiable but not enormous.

Use a thin teal rule/accent somewhere in the header.

Do not create a giant navy banner.

---

# Sidebar

If the application uses a Streamlit sidebar, make it look deliberately designed.

Use:
- very light neutral background
- subtle right border
- navy section headings
- normal dark text
- compact but comfortable spacing

Avoid dark navy sidebar backgrounds.

Input labels should be clear and relatively small.

---

# Inputs

Restyle Streamlit inputs so they feel consistent.

Use:
- white input backgrounds
- subtle `#E3E8EC` borders
- modest border radius, approximately 5–7 px
- navy/dark text
- teal focus state

Avoid:
- pill-shaped controls
- excessive rounding
- shadows
- bright coloured input backgrounds

The interface should feel technical rather than playful.

---

# Buttons

Primary button:

```text
background: #042C5B
text: white
```

Hover/focus may use teal subtly.

Secondary buttons should preferably be:
- white
- navy text
- thin navy/grey border

Do not make every button teal.

---

# Metric cards

This is particularly important.

Do NOT use large colourful dashboard cards.

Metrics should look almost like figures in a technical report.

Example:

```text
75 TB
Durable genomic data

90 TB
Planning envelope

62 TB
Expected AWS egress

R 482,000
5-year infrastructure estimate
```

Use:
- white background
- very subtle border
- little or no shadow
- 4–6 px border radius
- navy numbers
- muted labels

For the single most important metric, a thin teal top border or teal number is acceptable.

Do not make every metric visually equally important.

---

# Containers/cards

Reduce unnecessary cards.

Not every section needs a box around it.

Where containers are useful:

```css
background: #FFFFFF;
border: 1px solid #E3E8EC;
border-radius: 6px;
```

No heavy shadows.

If a shadow is absolutely necessary, make it extremely subtle.

Prefer whitespace and typography to separate sections.

---

# Tables

Tables should resemble GRO technical-document tables.

Header:
- navy background OR very light grey with navy text
- choose whichever works better with the existing table

Body:
- white
- subtle horizontal separators
- minimal vertical lines

Numerical columns:
- right aligned where possible

Totals:
- visually stronger
- thin teal/navy rule
- bold total

Do not use colourful heatmap-style tables.

---

# Charts

Do not change the data represented.

Restyle existing charts to:
- white background
- navy as primary series
- teal as secondary/highlight series
- grey for supporting series
- minimal grid lines
- no chart border
- no unnecessary legend if labels are obvious

Avoid using many unrelated colours.

---

# Expanders

Sections such as:

```text
Advanced assumptions
Calculation details
Pricing assumptions
```

should be visually quiet.

Use them to keep technical complexity out of the main visual hierarchy.

Style expanders with:
- white/light background
- thin border
- navy heading
- minimal rounding

---

# Cost summary

Give the final project estimate slightly stronger visual hierarchy than everything else.

For example:

```text
ESTIMATED 5-YEAR INFRASTRUCTURE COST

R XXX,XXX

Storage • Transfer • Archive • Engineering
Compute not yet included
```

Do NOT put this inside a giant colourful tile.

Use whitespace, typography and perhaps a thin teal accent.

---

# Status / informational messages

Replace the visual feel of Streamlit's default bright blue/yellow/green message boxes where practical.

Use restrained GRO-style informational callouts:

```text
border-left: 3px solid #0B8BA5;
background: #F7F9FA;
```

Warnings can use an appropriate muted warning colour, but do not overuse alerts.

---

# Streamlit chrome

Where safe, reduce unnecessary Streamlit visual clutter.

Do not break functionality.

The application should feel like a purpose-built CBIO tool rather than a Streamlit demo.

---

# Important constraint

Before making changes, inspect the current application.

**Preserve its existing information architecture and functionality.**

The user is happy with the calculator itself.

This is a visual refinement pass only.

Do not "improve" the calculator by moving sections, changing assumptions or redesigning the workflow.

After styling, run the application and visually inspect it at normal desktop width.

Fix:
- inconsistent spacing
- clipped text
- poor contrast
- awkward control heights
- mismatched borders
- excessive whitespace
- default Streamlit styling that clashes with GRO

The finished application should look credible if shown live in a meeting with CBIO management.