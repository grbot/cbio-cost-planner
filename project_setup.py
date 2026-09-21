"""Shared Project setup area (spec 013a §19-§43).

Rendered exactly once per script run, from ``app.py``, before
``st.navigation`` dispatches to whichever page is active -- so project
identity, project type (WGS 30x / Custom Project), "Load Example" and "New
project" appear identically on every page without being duplicated per
page (spec 013a §30). This module owns only genuinely project-level
concepts; Storage/Compute/Transfer-specific configuration stays in their
own view modules.

Project setup is not a fifth navigable page (spec 013a §21) -- it is
shared chrome, the same category as ``theme.header()``.
"""

from __future__ import annotations

import streamlit as st

from cbio_cost.project_state import get_project_state
from views import storage
from views.storage import CUSTOM_MODE, WGS_MODE


def reset_project() -> None:
    """The one atomic "New project" transition (spec 013a §36-§39).

    Clears session state entirely and re-runs the exact bootstrap a
    genuinely fresh session goes through, rather than hand-enumerating
    every canonical/widget key to reset -- this is what makes the reset
    atomic and immune to ghost widget state by construction (spec 013a
    §43, §66): nothing survives ``clear()`` for a stale key to "heal" from.
    """
    st.session_state.clear()
    storage.ensure_project_state()
    st.session_state["_new_project_toast"] = True


@st.dialog("Start a new project?")
def _confirm_new_project() -> None:
    st.write(
        "This will clear the current Storage, Compute and Transfer configuration "
        "and all calculated results. This cannot be undone."
    )
    cancel_col, confirm_col = st.columns(2)
    with cancel_col:
        if st.button("Cancel", use_container_width=True):
            st.rerun()
    with confirm_col:
        if st.button("Start new project", type="primary", use_container_width=True):
            reset_project()
            # Function-local import (see navigation.py's own docstring): a
            # module-level import here would construct navigation's st.Page
            # objects outside of any real script-run context as a side
            # effect of merely importing this module, which corrupts them
            # for any later streamlit.testing.v1.AppTest run in the same
            # process.
            from navigation import STORAGE_PAGE

            st.switch_page(STORAGE_PAGE)


def _looks_configured(state) -> bool:
    """Whether to show the real project identity rather than "Not yet
    configured". Checks raw widget state first, not only the sticky
    ``project_configured`` flag: that flag is only updated inside
    ``record_storage()``, which runs later in the same script pass (inside
    ``storage.render()``, dispatched by st.navigation *after* this area
    renders) -- relying on it alone would show a stale "Not yet configured"
    for the entire script run immediately after Load Example or a direct
    project-field edit, since Streamlit does not retroactively update
    already-emitted markdown."""
    if state.project_configured:
        return True
    return not (
        st.session_state.get("project_name", "") == ""
        and st.session_state.get("num_samples", 1) == 1
        and float(st.session_state.get("retention_years", 1.0)) == 1.0
        and st.session_state.get("project_mode", WGS_MODE) == WGS_MODE
    )


def _project_identity_line() -> str:
    """Reads raw widget state directly (already current after any callback
    or edit, unlike canonical ``storage_result``/``project_configured``,
    which only update once Storage's own render() runs later this pass)."""
    name = st.session_state.get("project_name") or "Untitled project"
    mode = st.session_state.get("project_mode", WGS_MODE)
    parts = [name, mode]
    if mode == WGS_MODE:
        parts.append(f"{st.session_state.get('num_samples', 1)} samples")
    parts.append(f"{float(st.session_state.get('retention_years', 1.0)):g} years")
    return "  ·  ".join(parts)


def render_project_area() -> None:
    state = get_project_state()

    if st.session_state.pop("_new_project_toast", False):
        st.toast("New project started.")

    identity = _project_identity_line() if _looks_configured(state) else "Not yet configured"
    identity_col, action_col = st.columns([5, 1])
    with identity_col:
        st.caption("PROJECT")
        st.markdown(f"**{identity}**")
    with action_col:
        if st.button("New project", key="new_project_button"):
            _confirm_new_project()

    with st.expander("Edit project"):
        st.radio(
            "Project type",
            options=[WGS_MODE, CUSTOM_MODE],
            key="project_mode",
            horizontal=True,
            label_visibility="collapsed",
        )
        is_wgs_mode = st.session_state["project_mode"] == WGS_MODE
        if is_wgs_mode:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.text_input("Project name", key="project_name")
            with col2:
                st.number_input("Number of samples", min_value=1, step=1, key="num_samples")
            with col3:
                st.number_input("Retention period (years)", min_value=0.1, step=0.5, key="retention_years")
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("Project name", key="project_name")
            with col2:
                st.number_input("Retention period (years)", min_value=0.1, step=0.5, key="retention_years")
        st.button(
            "Load 500 x 30x WGS / 5-year demo profile",
            key="load_demo_button",
            on_click=storage.load_demo_profile,
        )
