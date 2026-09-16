"""CBIO Genomics Infrastructure Cost Planner — application entry point.

Owns only app-level chrome: page config, GRO theme injection, the shared
title/strapline header (rendered identically on every page so the app does
not feel like four separate applications), and top-level navigation between
the Storage / Compute / Transfer / Project Summary modules (spec 010).

Each module's own UI and calculation-triggering logic lives in
``views/<module>.py``; no calculation or widget logic belongs here.
"""

from __future__ import annotations

import streamlit as st

import theme
from views import compute, storage, summary, transfer

st.set_page_config(page_title="CBIO Infrastructure Cost Planner", layout="wide")
theme.inject()
theme.header()

pages = [
    st.Page(storage.render, title="Storage", url_path="storage", default=True),
    st.Page(compute.render, title="Compute", url_path="compute"),
    st.Page(transfer.render, title="Transfer", url_path="transfer"),
    st.Page(summary.render, title="Project Summary", url_path="project-summary"),
]
st.navigation(pages, position="top").run()
