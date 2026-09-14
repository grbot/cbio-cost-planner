# GRO Styling Refinement — CBIO Genomics Infrastructure Cost Planner

## Purpose

Apply a final GRO visual styling pass to the existing Streamlit application.

The calculator itself is working correctly.

**This task is styling only.**

Do not change:

- calculations
- assumptions
- application logic
- inputs
- outputs
- navigation
- section order
- project profiles
- data model
- sensitivity calculations
- export functionality

The goal is to make the existing application more readable and visually polished while retaining the established GRO visual language.

---

# 1. Visual direction

The application should feel like:

> a professional CBIO research-infrastructure planning tool built using the GRO visual language.

It should be:

- technical
- restrained
- spacious
- readable
- professional
- appropriate for presenting to CBIO management

Avoid making it look like:

- a generic Streamlit application
- a SaaS dashboard
- a Bootstrap admin interface
- a marketing website
- a collection of colourful cards

Use whitespace, typography and subtle contrast rather than decoration.

---

# 2. GRO colour palette

Use the following colours consistently.

```text
Navy:           #042C5B
Teal:           #0B8BA5
Dark blue-grey: #172B3A
Body text:      #111111

Page background:#F2F5F7
App surface:    #FBFCFD
Panel:          #FFFFFF
Input:          #FFFFFF

Border:         #E3E8EC
Input border:   #CBD5DC
Muted text:     #667580
```

Approximate visual balance:

```text
85–90%  white / light neutral
8–10%   navy
2–5%    teal
```

Teal is an **accent colour**, not a general background colour.

---

# 3. Typography

Prefer:

```text
Aptos Display — headings
Aptos         — body
```

with fallback:

```css
font-family: "Aptos", "Segoe UI", Arial, sans-serif;
```

Main title:

```text
30–34 px
navy
strong weight
```

Section headings:

```text
18–21 px
navy
strong weight
```

Body:

```text
14–16 px
#111111 or #172B3A
```

Supporting/explanatory text:

```text
smaller
#667580
```

---

# 4. Overall page background

The application currently feels too white.

Change the outer Streamlit background to:

```css
background-color: #F2F5F7;
```

This should provide a subtle cool blue-grey canvas.

Do not use an obviously blue or dark background.

---

# 5. Main application surface

The central application should sit subtly above the page background.

Use:

```css
background-color: #FBFCFD;
```

Maximum useful content width should remain approximately:

```css
max-width: 1400px;
```

Do not add a heavy shadow.

If a boundary is needed, use:

```css
border: 1px solid #E3E8EC;
```

---

# 6. Section panels

Major numbered sections should have subtle visual separation.

Examples:

```text
01 Project
02 Data volume assumptions
03 Data movement
04 Storage lifecycle
05 Engineering and operations
...
10 Sensitivity analysis
```

Use:

```css
background-color: #FFFFFF;
border: 1px solid #E3E8EC;
border-radius: 6px;
padding: 24px 28px;
margin-bottom: 24px;
```

Do not use:

- shadows
- navy section backgrounds
- teal section backgrounds
- excessive rounding
- nested cards around every control

The intended hierarchy is:

```text
LIGHT BLUE-GREY PAGE

    NEAR-WHITE APPLICATION

        WHITE SECTION 01

        WHITE SECTION 02

        WHITE SECTION 03
```

---

# 7. Section headings

Keep the existing GRO treatment:

```text
01   Project
02   Data volume assumptions
10   Sensitivity analysis
```

The teal section number plus navy title works well.

Use:

```text
section number → #0B8BA5
section title  → #042C5B
```

## Remove the small decorative grey lines

The small grey horizontal line currently appearing beneath section headings should be removed.

It does not communicate information and visually looks like an incomplete UI element.

Do not replace it with another decorative element unless necessary.

The panel itself now provides enough section separation.

---

# 8. Primary buttons

The previous primary button had insufficient text contrast.

All primary buttons must use:

```css
background-color: #042C5B !important;
color: #FFFFFF !important;
border: 1px solid #042C5B !important;
font-weight: 600 !important;
```

Ensure nested Streamlit elements also inherit white:

```css
.stButton button,
.stButton button *,
button[kind="primary"],
button[kind="primary"] * {
    color: #FFFFFF !important;
}
```

Hover:

```css
background-color: #0B8BA5 !important;
border-color: #0B8BA5 !important;
color: #FFFFFF !important;
```

Never use black/dark text on navy or teal backgrounds.

---

# 9. Input controls

The current improved input styling should be retained.

Inputs should have:

```css
background: #FFFFFF;
border: 1px solid #CBD5DC;
border-radius: 6px;
color: #111111;
```

Hover:

```css
border-color: #8FA3AF;
```

Focus:

```css
border-color: #0B8BA5;
box-shadow: 0 0 0 1px #0B8BA5;
```

Do not add general shadows.

Controls should clearly look editable but remain restrained.

---

# 10. Form labels

Labels must remain visually distinguishable from entered values.

Use approximately:

```css
font-size: 13px;
font-weight: 600;
color: #172B3A;
margin-bottom: 6px;
```

Input values:

```css
font-size: 15px;
font-weight: 400;
color: #111111;
```

For example:

```text
Project name
Example WGS Project
```

should clearly read as:

```text
LABEL
value
```

without needing uppercase labels.

---

# 11. Number inputs

Keep the current number-input layout.

The plus/minus controls should be visually distinct from the value area using subtle separators.

Use:

```text
normal: #042C5B
hover:  #0B8BA5
```

Do not turn these into prominent buttons.

---

# 12. Select controls

Dropdown selected values:

```css
color: #111111;
```

Dropdown arrows:

```css
color: #042C5B;
```

Focus state:

```css
border-color: #0B8BA5;
```

---

# 13. Tables — IMPORTANT CONTRAST FIX

The current Sensitivity Analysis table has a serious readability problem.

The table header uses a navy background but the text is dark/black.

This must be fixed globally for all tables.

## Table header

Use:

```css
background-color: #042C5B !important;
color: #FFFFFF !important;
font-weight: 600 !important;
```

All nested header elements must also inherit white:

```css
.stDataFrame thead th,
.stDataFrame thead th *,
[data-testid="stDataFrame"] thead th,
[data-testid="stDataFrame"] thead th * {
    background-color: #042C5B !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
}
```

If Streamlit renders dataframe headers using a different DOM structure, inspect the rendered HTML and target the appropriate elements.

**Do not accept dark text on the navy header.**

Verify this visually after implementation.

---

# 14. Table body

Table body should remain light and highly readable.

Use:

```css
background-color: #FFFFFF;
color: #111111;
```

Borders:

```css
border-color: #E3E8EC;
```

Prefer subtle horizontal separators.

Avoid heavy grid lines.

Numeric columns should be right aligned where practical.

---

# 15. Financial number formatting

Where the application controls formatting, financial tables should not display values such as:

```text
44,656.8138
330,781.4719
626,791.8878
```

Instead display currency values rounded appropriately:

```text
R44,657
R330,781
R626,792
```

or, where cents are useful:

```text
R44,656.81
```

For management/project-planning views, prefer whole rand.

This is a **display-formatting change only**.

Do not alter underlying calculations or precision.

Similarly, TB values should generally be displayed with no more than 1–2 decimal places:

```text
72.66 TB
```

rather than:

```text
72.6563
```

Again, preserve full internal precision.

---

# 16. Sensitivity Analysis table

The Sensitivity Analysis section should therefore visually resemble:

```text
Scenario        Expected egress    Storage      Transfer      Archive       Engineering    Total
─────────────────────────────────────────────────────────────────────────────────────────────
Low movement       60.16 TB        R44,657      R152,652      R330,781      R72,000        R600,095
Expected           72.66 TB        R44,657      R179,349      R330,781      R72,000        R626,792
High movement     164.06 TB        R44,657      R374,570      R330,781      R72,000        R822,013
```

with:

```text
NAVY HEADER
WHITE HEADER TEXT

WHITE/LIGHT BODY
DARK BODY TEXT
```

Optionally make the `Expected` row subtly stronger, but do not use a bright coloured row.

For example:

```css
background-color: #F7F9FA;
font-weight: 600;
```

Do not make Low/Expected/High red/green traffic-light colours.

---

# 17. Metric cards

Avoid large colourful dashboard cards.

Metrics should resemble figures in a technical report.

Example:

```text
75 TB
Durable genomic data

90 TB
Planning envelope

72.66 TB
Expected AWS egress

R626,792
Expected 5-year infrastructure cost
```

Use:

```text
white background
subtle border
little/no shadow
navy number
muted label
```

The single primary project-cost figure may use teal emphasis.

Do not make every metric equally visually dominant.

---

# 18. Cost summary

The final project estimate should have stronger hierarchy.

For example:

```text
ESTIMATED 5-YEAR INFRASTRUCTURE COST

R626,792

Storage • Transfer • Archive • Engineering

Compute not yet included
```

Use typography and whitespace rather than a giant coloured tile.

A thin teal accent is acceptable.

---

# 19. Informational callouts

Where possible, avoid default bright Streamlit alert boxes.

Use restrained informational callouts such as:

```css
background: #F7F9FA;
border-left: 3px solid #0B8BA5;
color: #172B3A;
```

Use warning colours only for genuine warnings.

---

# 20. Expanders

Sections such as:

```text
Advanced assumptions
Calculation details
Pricing assumptions
```

should remain visually quiet.

Use:

```text
white/light background
thin border
navy heading
minimal rounding
```

These sections exist to keep complexity away from the primary interface.

---

# 21. Charts

Do not change the data or calculations represented.

Use GRO colours:

```text
primary:   #042C5B
highlight: #0B8BA5
secondary: muted grey/blue-grey
```

Use:

- white chart background
- minimal gridlines
- no decorative border
- no unnecessary legends
- no rainbow palettes

---

# 22. Header

Keep the existing title:

```text
CBIO Genomics Infrastructure Cost Planner
```

The existing large navy title and teal horizontal rule work well.

Do not place the title inside a card.

Supporting text should remain muted.

The demo-profile button should remain below the introductory text.

---

# 23. Do not overuse cards

This is important.

Do not wrap:

- every metric
- every input
- every paragraph
- every table

in separate cards.

The main numbered section panel is sufficient.

Prefer:

```text
page
    section
        heading
        explanatory text
        controls
        table
```

rather than:

```text
page
    card
        card
            card
```

---

# 24. Accessibility and contrast

Visually inspect all elements with coloured backgrounds.

In particular verify:

### Navy background

Text must normally be:

```text
#FFFFFF
```

### Teal background

Text must have sufficient contrast.

Prefer white for buttons.

### White/light background

Use:

```text
#111111
#172B3A
```

for primary text.

Never rely on browser/Streamlit inheritance for text colour when a custom background colour has been applied.

Explicitly set foreground and background colours together.

---

# 25. Streamlit CSS robustness

Streamlit components sometimes contain nested elements whose inherited colours override custom CSS.

Where a background is explicitly styled, inspect the DOM and ensure nested text elements receive the correct foreground colour.

This is particularly important for:

- buttons
- dataframe headers
- select controls
- tabs
- expanders

Use `!important` only where necessary to override Streamlit's generated styles.

Avoid fragile selectors where a stable `data-testid` selector exists.

---

# 26. Final visual QA

After implementing these changes:

1. Run the Streamlit application.
2. Open it at normal desktop width.
3. Load the `500 × 30× WGS / 5-year demo profile`.
4. Scroll through the complete application.
5. Visually inspect every section.

Specifically verify:

- page has subtle blue-grey background
- main content remains light
- sections are clearly distinguishable
- no excessive cards
- no decorative grey lines under section headings
- demo-profile button has white readable text
- labels are distinguishable from values
- inputs have visible boundaries
- dropdowns are readable
- +/- controls are readable
- all navy table headers have white text
- sensitivity table is immediately readable
- financial values have sensible display precision
- no text disappears because of CSS inheritance
- teal remains an accent rather than dominating the interface
- no calculations or functionality changed

The final application should look credible when presented live to CBIO management alongside the GRO-styled proposal and presentation.

## Core principle

**Do not redesign the calculator. Refine the visual presentation of the calculator that already works.**