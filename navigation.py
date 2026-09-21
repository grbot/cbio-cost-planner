"""Page registry (spec 012c §18, §21).

Defines the ``st.Page`` objects once so both ``app.py``'s ``st.navigation``
and each view's "Continue to X" ``st.page_link`` calls reference the exact
same objects — required because ``st.page_link`` only accepts a bare path
string for file-based multipage apps; for callable-based pages (as used
here) it requires the actual ``Page`` object (confirmed via
``help(st.page_link)``).

View modules must import the page objects they link to with a **function-
local** import inside ``render()``, not at module top level — this module
imports the view render callables at load time, so a top-level import back
from a view module would be circular. A local import inside ``render()``
resolves fine because it only executes once ``app.py`` has already fully
imported this module (before ``st.navigation(...).run()`` ever calls a
page's ``render()``).
"""

from __future__ import annotations

import streamlit as st

from views import compute, storage, summary, transfer

STORAGE_PAGE = st.Page(storage.render, title="Storage", url_path="storage", default=True)
COMPUTE_PAGE = st.Page(compute.render, title="Compute", url_path="compute")
TRANSFER_PAGE = st.Page(transfer.render, title="Transfer", url_path="transfer")
SUMMARY_PAGE = st.Page(summary.render, title="Project Summary", url_path="project-summary")

PAGES = [STORAGE_PAGE, COMPUTE_PAGE, TRANSFER_PAGE, SUMMARY_PAGE]
