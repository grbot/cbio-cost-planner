"""GRO (Genomics Repository Orchestrator) visual style for the Streamlit UI.

Implements the palette/typography/layout rules from
``requests/002-styling.md``, ``requests/003-styling.md`` and
``requests/004-style.md`` (the latter is the authoritative/final refinement
for palette values and layout hierarchy where they differ from the earlier
passes). This module is UI-only — it must never import from or be imported
by ``cbio_cost`` (the framework-independent calculation engine).
"""

from __future__ import annotations

import streamlit as st

NAVY = "#042C5B"
TEAL = "#0B8BA5"
SLATE = "#172B3A"
BODY = "#111111"
MUTED = "#667580"

PAGE_BG = "#F2F5F7"
APP_SURFACE = "#FBFCFD"
PANEL = "#FFFFFF"
INPUT_BG = "#FFFFFF"

BORDER = "#E3E8EC"
INPUT_BORDER = "#CBD5DC"
INPUT_BORDER_HOVER = "#8FA3AF"

SOFT_BG = "#F7F9FA"
AMBER = "#B7791F"

FONT_STACK_HEADING = '"Aptos Display", "Aptos", "Segoe UI", Arial, sans-serif'
FONT_STACK_BODY = '"Aptos", "Segoe UI", Arial, sans-serif'

_CSS = f"""
<style>
:root {{
    color-scheme: light;
}}

html, body, [data-testid="stAppViewContainer"] {{
    background-color: {PAGE_BG};
    color: {BODY};
    font-family: {FONT_STACK_BODY};
    color-scheme: light;
}}

input, textarea, select {{
    color-scheme: light;
}}

[data-testid="stHeader"] {{
    background-color: {PAGE_BG};
    border-bottom: 1px solid {BORDER};
    box-shadow: none;
}}

/* Top-level Storage / Compute / Transfer / Project Summary navigation
   (spec 010 §11). st.navigation(position="top") renders each page as a
   real <a data-testid="stTopNavLink"> link (genuine URL-based navigation,
   confirmed against the rendered app), with the current page marked via
   the standard aria-current="page" attribute. */
[data-testid="stTopNavLinkContainer"] {{
    background: none;
    box-shadow: none;
}}
a[data-testid="stTopNavLink"] {{
    font-family: {FONT_STACK_HEADING};
    font-weight: 600;
    font-size: 0.95rem;
    color: {MUTED};
    text-decoration: none;
    padding: 0.6rem 0.9rem;
    border-bottom: 3px solid transparent;
    border-radius: 0;
    box-shadow: none;
    background: none;
}}
a[data-testid="stTopNavLink"]:hover {{
    color: {NAVY};
}}
a[data-testid="stTopNavLink"][aria-current="page"] {{
    color: {NAVY};
    border-bottom-color: {TEAL};
}}

/* Central application surface: sits subtly above the page background */
[data-testid="stMainBlockContainer"] {{
    background-color: {APP_SURFACE};
    max-width: 1400px;
    border: 1px solid {BORDER};
    padding: 2rem 2.5rem;
}}

h1, h2, h3, h4, h5,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 {{
    font-family: {FONT_STACK_HEADING};
    color: {NAVY};
    font-weight: 600;
    letter-spacing: -0.01em;
}}

h1 {{
    font-size: 2.05rem;
    border-bottom: 3px solid {TEAL};
    padding-bottom: 0.5rem;
    margin-bottom: 0.25rem;
}}

/* Secondary headings (st.subheader, inside the calculation-details expander)
   use dark blue-grey per the style guide, not navy. */
h3, [data-testid="stMarkdownContainer"] h3 {{
    color: {SLATE};
    font-size: 1.05rem;
}}

[data-testid="stCaptionContainer"], .stCaption, small {{
    color: {MUTED};
    font-family: {FONT_STACK_BODY};
}}

p, li, label, [data-testid="stMarkdownContainer"] p {{
    color: {BODY};
    font-family: {FONT_STACK_BODY};
    font-size: 15px;
}}

hr {{
    border: none;
    border-top: 1px solid {BORDER};
    margin: 0.75rem 0 1.5rem 0;
}}

/* Metrics: figures in a technical report — navy number, muted label */
[data-testid="stMetric"] {{
    background-color: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 2px;
    padding: 0.75rem 1rem;
}}
[data-testid="stMetricLabel"] {{
    color: {MUTED};
    font-family: {FONT_STACK_BODY};
    font-size: 0.85rem;
    white-space: normal;
    overflow-wrap: break-word;
}}
[data-testid="stMetricValue"] {{
    color: {NAVY};
    font-family: {FONT_STACK_HEADING};
    font-weight: 600;
    font-size: 1.6rem;
    white-space: normal;
    overflow-wrap: break-word;
    line-height: 1.25;
}}

/* Buttons: navy, square-ish corners, no shadow/gradient */
div[data-testid="stButton"] button,
div[data-testid="stDownloadButton"] button {{
    background-color: {NAVY} !important;
    color: #FFFFFF !important;
    border: 1px solid {NAVY} !important;
    font-weight: 600 !important;
    border-radius: 2px;
    font-family: {FONT_STACK_BODY};
    box-shadow: none;
    padding: 0.5rem 1.1rem;
}}
/* Ensure all nested text (Streamlit wraps button labels in a <p>) inherits white */
div[data-testid="stButton"] button *,
div[data-testid="stDownloadButton"] button * {{
    color: #FFFFFF !important;
}}
div[data-testid="stButton"] button:hover,
div[data-testid="stDownloadButton"] button:hover {{
    background-color: {TEAL} !important;
    border-color: {TEAL} !important;
    color: #FFFFFF !important;
}}
div[data-testid="stButton"] button:hover *,
div[data-testid="stDownloadButton"] button:hover * {{
    color: #FFFFFF !important;
}}

/* Tables: navy header, subtle separators, no heavy borders */
table {{
    border-collapse: collapse;
    width: 100%;
    font-family: {FONT_STACK_BODY};
}}
table thead th {{
    background-color: {NAVY} !important;
    color: white !important;
    font-family: {FONT_STACK_HEADING};
    font-weight: 600;
    text-align: left;
    border: none !important;
    padding: 0.5rem 0.75rem !important;
}}
table tbody td {{
    border: none !important;
    border-bottom: 1px solid {BORDER} !important;
    padding: 0.45rem 0.75rem !important;
    color: {BODY};
    background-color: {PANEL};
}}
table tbody tr:last-child td {{
    border-bottom: none !important;
}}
/* Row emphasis modifiers (see theme.table()) */
tr.gro-row-total td {{
    font-weight: 700 !important;
    color: {TEAL} !important;
    border-top: 2px solid {TEAL} !important;
}}
tr.gro-row-emphasis td {{
    background-color: {SOFT_BG} !important;
    font-weight: 600 !important;
}}

/* Alerts (info/warning/error): restrained tint + left rule instead of bright fill */
[data-testid="stAlert"] {{
    background-color: {SOFT_BG};
    border: 1px solid {BORDER};
    border-left: 3px solid {TEAL};
    border-radius: 2px;
    color: {SLATE};
}}
[data-testid="stAlert"] p {{
    color: {SLATE};
}}
/* Genuine warnings (e.g. archive minimum-storage-duration) stay visually distinct */
[data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]) {{
    border-left-color: {AMBER};
}}

/* Expander: quiet, thin border, navy heading */
[data-testid="stExpander"] {{
    background-color: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 2px;
}}
[data-testid="stExpander"] summary {{
    font-family: {FONT_STACK_HEADING};
    color: {NAVY};
    font-weight: 600;
}}

/* Section header component (see section_header() below) */
.gro-section {{
    display: flex;
    align-items: baseline;
    gap: 0.75rem;
    margin-bottom: 1rem;
}}
.gro-section-number {{
    font-family: {FONT_STACK_HEADING};
    color: {TEAL};
    font-weight: 700;
    font-size: 1.0rem;
    min-width: 2.1rem;
}}
.gro-section-title {{
    font-family: {FONT_STACK_HEADING};
    color: {NAVY};
    font-weight: 600;
    font-size: 1.3rem;
}}

/* Section panel (see app.py: st.container(border=True, key="section_N")) */
[class*="st-key-section_"] {{
    background-color: {PANEL} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 6px !important;
    padding: 24px 28px !important;
    margin-bottom: 24px !important;
}}

/* Final-page disclaimer (see disclaimer() below) — plain text, not a warning box */
.gro-disclaimer {{
    border-top: 1px solid {BORDER};
    margin-top: 2rem;
    padding-top: 1rem;
}}
.gro-disclaimer-headline {{
    font-family: {FONT_STACK_HEADING};
    color: {SLATE};
    font-weight: 600;
    font-size: 0.95rem;
}}
.gro-disclaimer-body {{
    font-family: {FONT_STACK_BODY};
    color: {MUTED};
    font-size: 0.85rem;
    margin-top: 0.3rem;
}}

/* Callout component (see callout() below) */
.gro-callout {{
    background-color: {SOFT_BG};
    border-left: 3px solid {TEAL};
    border-radius: 2px;
    padding: 0.9rem 1.1rem;
    margin: 0.75rem 0 1.25rem 0;
}}
.gro-callout-title {{
    font-family: {FONT_STACK_HEADING};
    color: {TEAL};
    font-weight: 700;
    font-size: 0.78rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.35rem;
}}
.gro-callout-body {{
    font-family: {FONT_STACK_BODY};
    color: {SLATE};
    font-size: 1rem;
    line-height: 1.5;
}}

/* Headline cost figure (see headline() below) — the one place teal dominates */
.gro-headline {{
    border-top: 3px solid {TEAL};
    padding-top: 1rem;
    margin: 1rem 0 1.5rem 0;
}}
.gro-headline-label {{
    font-family: {FONT_STACK_HEADING};
    color: {NAVY};
    font-weight: 700;
    font-size: 0.8rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.4rem;
}}
.gro-headline-value {{
    font-family: {FONT_STACK_HEADING};
    color: {TEAL};
    font-weight: 700;
    font-size: 2.6rem;
    line-height: 1.1;
}}
.gro-headline-sublabel {{
    font-family: {FONT_STACK_BODY};
    color: {MUTED};
    font-size: 0.9rem;
    margin-top: 0.4rem;
}}

/* Lifecycle / process diagram */
.gro-diagram {{
    display: flex;
    align-items: center;
    gap: 0;
    margin: 1rem 0 1.5rem 0;
    flex-wrap: wrap;
}}
.gro-diagram-box {{
    border: 1.5px solid {NAVY};
    color: {NAVY};
    font-family: {FONT_STACK_HEADING};
    font-weight: 600;
    font-size: 0.85rem;
    text-align: center;
    padding: 0.65rem 1rem;
    border-radius: 2px;
    background: {PANEL};
    min-width: 9rem;
}}
.gro-diagram-box.gro-diagram-box--teal {{
    border-color: {TEAL};
    color: {TEAL};
}}
.gro-diagram-arrow {{
    color: {TEAL};
    font-size: 1.3rem;
    padding: 0 0.6rem;
    font-weight: 700;
}}

/* ---- Form control contrast (requests/003-styling.md, requests/004-style.md) ---- */

/* Labels distinct from values */
label[data-testid="stWidgetLabel"] p {{
    font-size: 13px;
    font-weight: 600;
    color: {SLATE};
    margin-bottom: 6px;
}}

/* Visible but restrained boundary on every input field, white fill (004 supersedes
   the 003 off-white fill — inputs now match panel white, border does the work) */
div[data-testid="stNumberInputContainer"],
div[data-testid="stTextInputRootElement"],
div[data-testid="stSelectbox"] div[role="group"] {{
    background-color: {INPUT_BG};
    border: 1px solid {INPUT_BORDER};
    border-radius: 6px;
    box-shadow: none;
}}
div[data-testid="stNumberInputContainer"]:hover,
div[data-testid="stTextInputRootElement"]:hover,
div[data-testid="stSelectbox"] div[role="group"]:hover {{
    border-color: {INPUT_BORDER_HOVER};
}}
div[data-testid="stNumberInputContainer"]:focus-within,
div[data-testid="stTextInputRootElement"]:focus-within,
div[data-testid="stSelectbox"] div[role="group"]:focus-within {{
    border-color: {TEAL};
    box-shadow: 0 0 0 1px {TEAL};
}}

/* Input value typography */
input[data-testid="stNumberInputField"],
input[data-testid="stTextInputField"],
div[data-testid="stSelectbox"] input {{
    background-color: transparent;
    font-size: 15px;
    font-weight: 400;
    color: {BODY};
}}

/* Numeric +/- controls: subtle separators, navy default / teal hover */
div[data-testid="stNumberInputContainer"] > div {{
    border-left: 1px solid {INPUT_BORDER};
}}
button[data-testid="stNumberInputStepDown"],
button[data-testid="stNumberInputStepUp"] {{
    color: {NAVY};
    background: transparent;
}}
button[data-testid="stNumberInputStepUp"] {{
    border-left: 1px solid {INPUT_BORDER};
}}
button[data-testid="stNumberInputStepDown"]:hover,
button[data-testid="stNumberInputStepUp"]:hover {{
    color: {TEAL};
}}

/* Select dropdown arrow (selected value stays body-dark) */
div[data-testid="stSelectbox"] button[aria-label="Open"] {{
    color: {NAVY};
}}
div[data-testid="stSelectbox"] button[aria-label="Open"]:hover {{
    color: {TEAL};
}}

/* Charts: white/transparent background, no decorative border */
[data-testid="stArrowVegaLiteChart"] {{
    background-color: transparent;
}}

/* Project-mode selector (see mode_tabs() below) — a horizontal radio
   styled as a pair of clean, native-feeling GRO tabs. Real st.tabs() has no
   way to report which tab is active back to Python, so a horizontal radio
   is used instead where the active mode must drive server-side branching. */
div[data-testid="stRadio"][class*="st-key-project_mode"] > label {{
    display: none;
}}
div[data-testid="stRadio"][class*="st-key-project_mode"] div[role="radiogroup"] {{
    display: flex;
    gap: 0.5rem;
    border-bottom: 1px solid {BORDER};
    margin-bottom: 1.25rem;
}}
div[data-testid="stRadio"][class*="st-key-project_mode"] label {{
    background: transparent;
    border: none;
    border-bottom: 3px solid transparent;
    border-radius: 0;
    padding: 0.6rem 0.25rem;
    margin-bottom: -1px;
}}
div[data-testid="stRadio"][class*="st-key-project_mode"] label p {{
    font-family: {FONT_STACK_HEADING};
    font-weight: 600;
    font-size: 1.05rem;
    color: {MUTED};
}}
div[data-testid="stRadio"][class*="st-key-project_mode"] label:has(input:checked) {{
    border-bottom-color: {TEAL};
}}
div[data-testid="stRadio"][class*="st-key-project_mode"] label:has(input:checked) p {{
    color: {NAVY};
}}
div[data-testid="stRadio"][class*="st-key-project_mode"] label div:first-child {{
    display: none;
}}
</style>
"""


def inject() -> None:
    """Inject the GRO stylesheet. Call once, immediately after set_page_config."""
    st.markdown(_CSS, unsafe_allow_html=True)


def section_header(number: int, title: str) -> None:
    """Render a numbered GRO-style section header (navy title, teal number)."""
    st.markdown(
        f'<div class="gro-section">'
        f'<span class="gro-section-number">{number:02d}</span>'
        f'<span class="gro-section-title">{title}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )


def callout(title: str, body: str) -> None:
    """Render a restrained GRO-style callout (slate text, teal left rule)."""
    st.markdown(
        f'<div class="gro-callout">'
        f'<div class="gro-callout-title">{title}</div>'
        f'<div class="gro-callout-body">{body}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def headline(label: str, value: str, sublabel: str) -> None:
    """Render the one prominent teal-emphasis project-cost figure (spec item 18)."""
    st.markdown(
        f'<div class="gro-headline">'
        f'<div class="gro-headline-label">{label}</div>'
        f'<div class="gro-headline-value">{value}</div>'
        f'<div class="gro-headline-sublabel">{sublabel}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def disclaimer(headline_text: str, body: str) -> None:
    """Render the restrained final-page disclaimer — plain text, no warning box."""
    st.markdown(
        f'<div class="gro-disclaimer">'
        f'<div class="gro-disclaimer-headline">{headline_text}</div>'
        f'<div class="gro-disclaimer-body">{body}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def process_diagram(steps: list[str], accent_indices: set[int] | None = None) -> None:
    """Render a simple box-and-arrow process/lifecycle diagram (spec: architecture diagrams).

    ``accent_indices`` marks which boxes (0-indexed) render in teal instead of
    navy — used for the important transition/action step.
    """
    accent_indices = accent_indices or set()
    parts: list[str] = ['<div class="gro-diagram">']
    for i, step in enumerate(steps):
        if i > 0:
            parts.append('<span class="gro-diagram-arrow">&rarr;</span>')
        css_class = "gro-diagram-box gro-diagram-box--teal" if i in accent_indices else "gro-diagram-box"
        parts.append(f'<div class="{css_class}">{step}</div>')
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def table(
    columns: list[str],
    rows: list[list[str]],
    align: list[str],
    row_class: list[str | None] | None = None,
) -> None:
    """Render a hand-authored GRO-style table (navy header, white body).

    ``st.table()`` with a pandas Styler silently drops custom per-cell
    styling, so row-level emphasis (a bold/teal total row, a subtly
    highlighted scenario row) is rendered directly as HTML instead.

    ``columns`` are header labels, ``rows`` are pre-formatted cell strings
    (formatting/rounding is the caller's responsibility), ``align`` is
    "left"/"right" per column, and ``row_class`` optionally assigns a CSS
    class (e.g. "gro-row-total", "gro-row-emphasis") per row.
    """
    row_class = row_class or [None] * len(rows)
    parts: list[str] = ["<table><thead><tr>"]
    for col, a in zip(columns, align):
        parts.append(f'<th style="text-align:{a};">{col}</th>')
    parts.append("</tr></thead><tbody>")
    for row, cls in zip(rows, row_class):
        tr_class = f' class="{cls}"' if cls else ""
        parts.append(f"<tr{tr_class}>")
        for cell, a in zip(row, align):
            parts.append(f'<td style="text-align:{a};">{cell}</td>')
        parts.append("</tr>")
    parts.append("</tbody></table>")
    st.markdown("".join(parts), unsafe_allow_html=True)
