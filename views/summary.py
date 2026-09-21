"""Project Summary — cross-module rollup (spec 010 §3; state integrity spec 012a).

Renders only what has already been computed by Storage/Compute/Transfer (via
the shared ``cbio_cost.project.Project`` model in session state) — it
performs no calculation of its own and never fabricates a figure. Since spec
012a it also reads the canonical ``ProjectState`` (``cbio_cost.
project_state``) to determine whether each module's stored result is still
current for the project's live configuration, so it never silently combines
results calculated from different project states (spec 012a §5, §19).
"""

from __future__ import annotations

from decimal import Decimal

import streamlit as st

import theme
from cbio_cost.export import STORAGE_CLASS_LABELS
from cbio_cost.project import PROJECT_SESSION_KEY
from cbio_cost.project_state import (
    COMPLETE,
    NOT_CONFIGURED,
    STATUS_LABELS,
    compute_status,
    get_project_state,
    storage_status,
    transfer_status,
)
from cbio_cost.units import gb_to_tb

STORAGE_RELATED_LABELS = ("Active S3 storage", "S3/API/lifecycle requests", "Archive storage")


def _needs_review_callout(module_label: str) -> None:
    theme.callout(
        "Needs review",
        f"Project inputs changed after this {module_label} estimate was calculated. "
        f"Review {module_label} before treating this result as current.",
    )


def _guided_flow_line(s_status: str, c_status: str, t_status: str) -> None:
    # Restrained, text-only guided-flow indicator (spec 012a §14, §16) — no
    # clickable page-jump buttons (see plan's design decision 5) and no
    # traffic-light-only colour semantics; the existing top navigation
    # already lets users jump to any module directly.
    st.caption(
        f"Recommended flow — 1 Storage: {STATUS_LABELS[s_status]}  ·  "
        f"2 Compute: {STATUS_LABELS[c_status]}  ·  "
        f"3 Transfer: {STATUS_LABELS[t_status]}  ·  "
        "4 Project Summary"
    )


def render() -> None:
    with st.container(border=True, key="section_summary"):
        theme.section_header(1, "Project Summary")

        state = get_project_state()
        project = st.session_state.get(PROJECT_SESSION_KEY)
        s_status = storage_status(state)
        c_status = compute_status(state)
        t_status = transfer_status(state)

        _guided_flow_line(s_status, c_status, t_status)

        if project is None or project.storage_estimate is None or s_status == NOT_CONFIGURED:
            theme.callout(
                "Project setup is not complete",
                "Start with Storage to configure the project. Project Summary shows only "
                "information that has actually been calculated — nothing is invented here.",
            )
            return

        # Direct-entry wording (spec 012a §21): a fresh session already has a
        # minimum-valid project (app.py's bootstrap) — say so explicitly
        # rather than implying it reflects the user's actual project, and
        # never call a default-derived figure "last-computed" unless the
        # user actually visited Storage and configured it themselves.
        if state.storage_config_revision == 0:
            theme.callout(
                "Showing the minimum default project",
                "This project has not been configured yet — figures below reflect the "
                "application's 1-sample minimum-valid default, not a real project. "
                "Configure Storage to plan your actual project.",
            )

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
        egress_zar = next(i.amount_zar for i in estimate.line_items if i.label == "AWS to Ilifu transfer")

        mcol1, mcol2, mcol3 = st.columns(3)
        mcol1.metric("Durable data volume", f"{raw_tb:.1f} TB")
        mcol2.metric("Storage lifecycle cost (ZAR)", f"R{storage_related_zar:,.0f}")
        mcol3.metric("Engineering cost (ZAR)", f"R{estimate.total_engineering_zar:,.0f}")

        st.markdown("**Selected storage lifecycle**")
        theme.table(
            columns=["Dataset", "Archive class"],
            rows=[[d.name, STORAGE_CLASS_LABELS.get(d.archive_class, d.archive_class)] for d in estimate.datasets],
            align=["left", "left"],
        )

        # ---------------------------------------------------------------
        # Financial summary (spec 012a §22-§25): explicit "Current included
        # total" breakdown, then a separate "Not yet included" list — never
        # a bare "Total project cost" while major components remain unpriced.
        # ---------------------------------------------------------------
        st.markdown("**Current included costs**")
        st.caption(
            "Covers modelled Storage lifecycle cost, planned workflow egress and engineering. "
            "Compute infrastructure and other pending components are not yet included."
        )
        theme.table(
            columns=["Component", "Amount (ZAR)"],
            rows=[
                ["Storage lifecycle", f"R{storage_related_zar:,.0f}"],
                ["Planned workflow egress", f"R{egress_zar:,.0f}"],
                ["Engineering", f"R{estimate.total_engineering_zar:,.0f}"],
                ["Current included total", f"R{estimate.grand_total_zar:,.0f}"],
            ],
            align=["left", "right"],
            row_class=[None, None, None, "gro-row-total"],
        )

        not_included_rows = [["Compute infrastructure", "Pending"]]
        if project.transfer_result is not None:
            not_included_rows.append(["Explicit transfer-plan cost", "See Transfer section below"])
        not_included_rows.append(["GLnexus", "Pending where relevant"])
        st.markdown("**Not yet included**")
        theme.table(columns=["Component", "Status"], rows=not_included_rows, align=["left", "left"])

        st.markdown("**Relevant assumptions**")
        st.markdown(
            f"- Storage headroom: {estimate.inputs.headroom_fraction * 100:.0f}%\n"
            f"- Transfer contingency: {estimate.inputs.transfer_contingency * 100:.0f}%\n"
            f"- USD/ZAR exchange rate: {estimate.currency.usd_zar}\n"
            f"- VAT: {estimate.currency.vat_fraction * 100:.0f}%"
        )

        if s_status != COMPLETE:
            _needs_review_callout("Storage")
        st.caption(
            "These figures reflect Storage's last-computed values in this session. "
            "Revisit the Storage page after changing any input to refresh them."
        )

        # -----------------------------------------------------------------
        # Compute
        # -----------------------------------------------------------------
        if project.compute_result is not None:
            compute = project.compute_result
            st.markdown("**Compute**")
            if c_status != COMPLETE:
                _needs_review_callout("Compute")
            st.markdown(
                "Workflow: BWA-MEM2 + CRAM index + DeepVariant  \n"
                "GLnexus shown but excluded pending benchmark"
            )
            st.caption(
                "Execution environment: Ilifu/HPC (reference — no monetary cost modelled) and "
                "AWS (architecture defined, pricing pending)."
            )
            ccol1, ccol2, ccol3, ccol4 = st.columns(4)
            ccol1.metric("Sequential-stage planning estimate", f"{compute.known_modelled_elapsed_hours:,.2f} h")
            ccol2.metric(
                "Alignment workers",
                f"{compute.alignment.effective_concurrency} active of "
                f"{compute.alignment.configured_concurrency} configured",
            )
            ccol3.metric(
                "DeepVariant workers",
                f"{compute.deepvariant.effective_concurrency} active of "
                f"{compute.deepvariant.configured_concurrency} configured",
            )
            ccol4.metric(
                "Peak working storage", f"{compute.working_storage.peak_simultaneous_gib:,.0f} GiB"
            )
            st.caption(
                "Evidence status: Measured (alignment, CRAM index) + Published benchmark "
                "(DeepVariant) + Planning assumptions (RAM, scratch) — GLnexus excluded, no "
                "approved benchmark."
            )
            theme.callout(
                "Compute cost — not yet calculated",
                "AWS regional pricing status: pending verified regional pricing (see Compute page).",
            )
        else:
            theme.callout(
                "Compute",
                "Visit the Compute page to configure and calculate Compute figures for this "
                "project. No compute cost or resource figures are shown here yet.",
            )

        # -----------------------------------------------------------------
        # Transfer
        # -----------------------------------------------------------------
        if project.transfer_result is not None:
            transfer = project.transfer_result
            plan = transfer.plan
            st.markdown("**Transfer**")
            if t_status != COMPLETE:
                _needs_review_callout("Transfer")
            st.markdown(f"{plan.dataset_name}  \n{plan.source.label} → {plan.destination.label}")
            tcol1, tcol2, tcol3 = st.columns(3)
            tcol1.metric("Volume", f"{transfer.size_tb:.2f} TB")
            if plan.throughput_mode == "unknown":
                tcol2.metric("Throughput basis", "Planning scenarios")
                tcol3.metric("Duration", "See Transfer page")
            else:
                tcol2.metric("Planning throughput", f"{transfer.throughput.effective_mbps:,.0f} Mbps")
                tcol3.metric("Estimated duration", f"{transfer.duration_hours:,.1f} h")
            st.caption(f"Method: {plan.transfer_method}")
            if transfer.provider_cost.status == "calculated":
                theme.callout(
                    "Explicit transfer plan — provider charge",
                    f"${transfer.provider_cost.cost_usd:,.2f} — {transfer.provider_cost.basis}  \n"
                    "Included in project total: No — shown separately.",
                )
            else:
                theme.callout(
                    "Explicit transfer plan — provider charge not currently calculated",
                    f"{transfer.provider_cost.basis}  \nIncluded in project total: No — shown separately.",
                )
            st.caption(
                "This is a separate endpoint-to-endpoint movement estimate, distinct from Storage's "
                "planned workflow egress above (\"Planned workflow egress\" in Current included "
                "costs); neither figure is folded into the other, and this explicit Transfer-plan "
                "charge is not added to the project total shown above."
            )
        else:
            theme.callout(
                "Transfer",
                "Visit the Transfer page to plan a data-movement leg for this project. No "
                "transfer duration or cost figures are shown here yet.",
            )
