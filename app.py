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
from navigation import PAGES
from views import storage

st.set_page_config(page_title="CBIO Infrastructure Cost Planner", layout="wide")
theme.header()

# Guarantee a shared Project exists before navigation dispatches to whichever
# page the user opens first (spec 011a §3) — st.navigation only runs the
# render() of the selected page, so a fresh session opened directly at
# Compute/Transfer/Project Summary would otherwise never see Storage's
# session-state bootstrap.
storage.ensure_project_state()

st.navigation(PAGES, position="top").run()
