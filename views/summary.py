"""Project Summary — cross-module rollup (spec 010 §3).

Status: PLANNED / PARTIALLY AVAILABLE. Renders only what has already been
computed by the Storage module (via the shared ``cbio_cost.project.Project``
model in session state) — it performs no calculation of its own and never
fabricates a Compute or Transfer figure.
"""

from __future__ import annotations

from decimal import Decimal

import streamlit as st

import theme
from cbio_cost.export import STORAGE_CLASS_LABELS
from cbio_cost.project import PROJECT_SESSION_KEY
from cbio_cost.units import gb_to_tb

STORAGE_RELATED_LABELS = ("Active S3 storage", "S3/API/lifecycle requests", "Archive storage")


def render() -> None:
    with st.container(border=True, key="section_summary"):
        theme.section_header(1, "Project Summary")

        project = st.session_state.get(PROJECT_SESSION_KEY)
        if project is None or project.storage_estimate is None:
            theme.callout(
                "No project yet",
                "Visit the Storage page to define a project. Project Summary shows only "
                "information that has actually been calculated — nothing is invented here.",
            )
            return

        estimate = project.storage_estimate
        meta = project.metadata

        scol1, scol2, scol3 = st.columns(3)
        scol1.metric("Project type", meta.project_type)
        scol2.metric("Samples", str(meta.num_samples) if meta.num_samples is not None else "—")
        scol3.metric("Retention", f"{meta.retention_years:g} years")

        raw_tb = gb_to_tb(estimate.volume.raw_total_gb)
        storage_related_zar = sum(
            (item.amount_zar for item in estimate.line_items if item.label in STORAGE_RELATED_LABELS),
            Decimal(0),
        )

        mcol1, mcol2, mcol3 = st.columns(3)
        mcol1.metric("Durable data volume", f"{raw_tb:.1f} TB")
        mcol2.metric("Storage-related cost (ZAR)", f"R{storage_related_zar:,.0f}")
        mcol3.metric("Engineering cost (ZAR)", f"R{estimate.total_engineering_zar:,.0f}")

        st.markdown("**Selected storage lifecycle**")
        theme.table(
            columns=["Dataset", "Archive class"],
            rows=[[d.name, STORAGE_CLASS_LABELS.get(d.archive_class, d.archive_class)] for d in estimate.datasets],
            align=["left", "left"],
        )

        st.markdown("**Relevant assumptions**")
        st.markdown(
            f"- Storage headroom: {estimate.inputs.headroom_fraction * 100:.0f}%\n"
            f"- Transfer contingency: {estimate.inputs.transfer_contingency * 100:.0f}%\n"
            f"- USD/ZAR exchange rate: {estimate.currency.usd_zar}\n"
            f"- VAT: {estimate.currency.vat_fraction * 100:.0f}%"
        )

        st.caption(
            "These figures reflect the Storage page's last-computed values in this "
            "session. Revisit the Storage page after changing any input to refresh them."
        )

        if project.compute_result is not None:
            compute = project.compute_result
            st.markdown("**Compute**")
            st.markdown(
                "Workflow: FASTQ -> BWA-MEM2 -> CRAM index -> DeepVariant -> gVCF -> GLnexus "
                "(not yet quantified)"
            )
            st.caption(
                "Execution environment: Ilifu/HPC (reference — no monetary cost modelled) and "
                "AWS (architecture defined, pricing pending)."
            )
            ccol1, ccol2, ccol3 = st.columns(3)
            ccol1.metric("Sequential-stage planning estimate", f"{compute.known_modelled_elapsed_hours:,.1f} h")
            ccol2.metric(
                "Concurrency (align/DV)",
                f"{compute.alignment.concurrency} / {compute.deepvariant.concurrency}",
            )
            ccol3.metric(
                "Peak working storage", f"{compute.working_storage.peak_simultaneous_gib:,.0f} GiB"
            )
            st.caption(
                "Evidence status: Measured (alignment, CRAM index) + Published benchmark "
                "(DeepVariant) + Planning assumptions (RAM, scratch) — GLnexus excluded, no "
                "approved benchmark."
            )
            theme.callout("Compute cost — not yet calculated", "AWS compute pricing is pending verified regional pricing (see Compute page).")
        else:
            theme.callout(
                "Compute",
                "Visit the Compute page to configure and calculate Compute figures for this "
                "project. No compute cost or resource figures are shown here yet.",
            )
        theme.callout(
            "Transfer",
            "Transfer results will be added in a later development stage. No transfer "
            "duration or cost figures are shown here.",
        )
