"""Transfer module — placeholder page (spec 010 §3).

Status: PLANNED. No calculations are implemented. This page only explains
what the Transfer module will eventually estimate; it must never fabricate
a duration, throughput, or cost figure.
"""

from __future__ import annotations

import streamlit as st

import theme
from cbio_cost.project import PROJECT_SESSION_KEY


def render() -> None:
    with st.container(border=True, key="section_transfer"):
        theme.section_header(1, "Transfer")
        project = st.session_state.get(PROJECT_SESSION_KEY)
        if project is not None:
            st.caption(f"Project: {project.metadata.name}")

        theme.callout(
            "Not yet implemented",
            "Transfer duration, throughput and network-cost estimation is planned but not "
            "yet implemented. No transfer figures are shown here.",
        )

        st.markdown(
            "Once implemented, Transfer will estimate data movement between this "
            "project's infrastructure endpoints, including:"
        )
        st.markdown(
            "- Data movement between infrastructure endpoints\n"
            "- Expected transfer volume\n"
            "- Measured or assumed throughput\n"
            "- Transfer duration\n"
            "- Network constraints\n"
            "- Transfer method\n"
            "- Transfer-related cloud costs"
        )

        st.caption(
            "Transfer staging (e.g. temporary upload staging, transfer buffers, "
            "resumable transfer working areas) is a Transfer-module concern, distinct "
            "from durable Storage. The AWS-to-Ilifu workflow egress modelled on the "
            "Storage page today is a Storage-specific movement assumption and remains "
            "there for now."
        )
