The current GRO styling is close, but the form controls have insufficient contrast. Do not change the layout or functionality. Fix only the visual styling described below.

## 1. Primary button is unreadable

The button:

`Load 500 x 30x WGS / 5-year demo profile`

currently has a navy background but dark/black text.

All primary buttons must use:

```css
background-color: #042C5B !important;
color: #FFFFFF !important;
border: 1px solid #042C5B !important;
font-weight: 600 !important;
```

Ensure **all text elements inside the Streamlit button inherit white**, including nested `<p>` elements:

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

Do not use black text on navy or teal buttons.

---

## 2. Input controls need visible boundaries

The Project name, Project type, Number of samples, Sequencing depth and Retention period controls currently blend into the page.

Give inputs a clearly visible but restrained technical border:

```css
background: #FFFFFF;
border: 1px solid #CBD5DC;
border-radius: 6px;
```

On hover:

```css
border-color: #8FA3AF;
```

On focus:

```css
border-color: #0B8BA5;
box-shadow: 0 0 0 1px #0B8BA5;
```

Do NOT use shadows otherwise.

The controls should clearly look editable without becoming visually heavy.

---

## 3. Make labels distinct from values

Currently:

`Project name`

and:

`Example WGS Project`

have almost the same visual weight.

Form labels should use:

```css
font-size: 13px;
font-weight: 600;
color: #172B3A;
margin-bottom: 6px;
```

Input values should use:

```css
font-size: 15px;
font-weight: 400;
color: #111111;
```

This should make the hierarchy immediately apparent:

```text
PROJECT NAME
Example WGS Project
```

Do not necessarily uppercase the labels; the example above illustrates hierarchy only.

---

## 4. Slightly distinguish the input area

Keep the page white, but use a very subtle input fill if needed:

```css
background-color: #FAFBFC;
```

with the visible border:

```css
border: 1px solid #CBD5DC;
```

This should provide enough distinction from the white page.

Do NOT turn inputs grey or blue.

---

## 5. Numeric +/- controls

The minus and plus controls currently visually float inside the field.

Add subtle separators around the increment/decrement controls if Streamlit's DOM permits it.

They should remain understated but clearly interactive.

Ensure:

```css
color: #042C5B;
```

and use teal for hover:

```css
color: #0B8BA5;
```

---

## 6. Select dropdown arrow

The Project Type dropdown arrow should use:

```css
color: #042C5B;
```

The selected value must remain:

```css
color: #111111;
```

---

## 7. Preserve everything else

Do NOT:
- move controls
- change widths
- change calculations
- change labels
- change section structure
- add cards
- add shadows
- add coloured backgrounds

This is strictly a **contrast and form-control refinement**.

After implementing, visually verify that:

1. The demo-profile button has clearly readable white text.
2. Every input has an obvious boundary.
3. Labels are visually distinguishable from entered values.
4. Focused inputs have a subtle teal state.
5. The result still feels restrained and consistent with GRO styling.