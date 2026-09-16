"""Compute module — placeholder page (spec 010 §3).

Status: PLANNED. No calculations are implemented. This page only explains
what the Compute module will eventually estimate; it must never fabricate
a cost, runtime, or resource figure.
"""

from __future__ import annotations

import streamlit as st

import theme
from cbio_cost.project import PROJECT_SESSION_KEY


def render() -> None:
    with st.container(border=True, key="section_compute"):
        theme.section_header(1, "Compute")
        project = st.session_state.get(PROJECT_SESSION_KEY)
        if project is not None:
            st.caption(f"Project: {project.metadata.name}")

        theme.callout(
            "Not yet implemented",
            "Compute cost and resource estimation is planned but not yet implemented. "
            "No compute figures are shown here.",
        )

        st.markdown(
            "Once implemented, Compute will estimate infrastructure requirements for "
            "running genomics workflows against this project's datasets, including:"
        )
        st.markdown(
            "- Workflow stages\n"
            "- CPU/GPU requirements\n"
            "- Memory\n"
            "- Runtime\n"
            "- Concurrency\n"
            "- Temporary/working storage\n"
            "- Cloud/HPC execution options\n"
            "- Software/licensing costs\n"
            "- Expected completion time"
        )

        st.caption(
            "Temporary/working compute storage (e.g. sort temp files, workflow work "
            "directories, container/cache space) is a Compute-module concern, distinct "
            "from the durable storage modelled on the Storage page."
        )
