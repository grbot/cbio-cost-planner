"""CBIO Genomics Infrastructure Cost Planner — Streamlit UI.

This module only reads widget inputs, builds the typed assumption objects
from ``cbio_cost.models``, calls into ``cbio_cost.calculator`` for every
calculation, and renders the results. No arithmetic happens here.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
import streamlit as st

import theme
from cbio_cost import config as cost_config
from cbio_cost import export as cost_export
from cbio_cost.calculator import build_estimate, build_scenarios, explain_result
from cbio_cost.models import (
    CurrencyAssumptions,
    EngineeringAssumptions,
    FileTypeVolumeAssumption,
    MovementAssumptions,
    ProjectInputs,
    StorageAssumptions,
)
from cbio_cost.units import gb_to_tb

CONFIG_DIR = Path(__file__).resolve().parent / "config"
STORAGE_CLASS_LABELS = {
    "s3_standard": "S3 Standard",
    "glacier_instant": "Glacier Instant Retrieval",
    "glacier_flexible": "Glacier Flexible Retrieval",
    "glacier_deep_archive": "Glacier Deep Archive",
}

st.set_page_config(page_title="CBIO Infrastructure Cost Planner", layout="wide")
theme.inject()


def _load_pricing():
    # Deliberately uncached: parsing this small YAML file is cheap, and
    # st.cache_resource previously caused a stale PricingConfig (missing the
    # pricing_source/region_name/pricing_last_verified fields added in
    # requests/005-pricing-and-disclaimer.md) to survive a lightweight
    # redeploy, since the cache key is derived from this wrapper's own
    # source, not from cbio_cost/config.py or the YAML it reads.
    return cost_config.load_pricing(CONFIG_DIR / "aws-pricing.yaml")


def _load_profile_and_scenarios():
    # See _load_pricing() above — deliberately uncached for the same reason.
    return cost_config.load_profiles(CONFIG_DIR / "project-profiles.yaml")


def _default_state() -> dict:
    profile, scenarios = _load_profile_and_scenarios()
    currency = cost_config.load_currency_defaults(CONFIG_DIR / "aws-pricing.yaml")
    state = {
        "project_name": profile.project.project_name,
        "project_type": profile.project.project_type,
        "num_samples": profile.project.num_samples,
        "depth_label": profile.project.depth_label,
        "retention_years": float(profile.project.retention_years),
        "headroom_percent": float(profile.storage.headroom_fraction * 100),
        "active_months": float(profile.storage.active_months),
        "fastq_passes": float(profile.movement.fastq_passes),
        "cram_retrieval_percent": float(profile.movement.cram_retrieval_fraction * 100),
        "cram_retrieval_passes": float(profile.movement.cram_retrieval_passes),
        "gvcf_passes": float(profile.movement.gvcf_passes),
        "transfer_contingency_percent": float(profile.movement.transfer_contingency * 100),
        "onboarding_hours": float(profile.engineering.onboarding_hours),
        "operations_hours_per_year": float(profile.engineering.operations_hours_per_year),
        "closeout_hours": float(profile.engineering.closeout_hours),
        "hourly_rate_zar": float(profile.engineering.hourly_rate_zar),
        "usd_zar": float(currency.usd_zar),
        "vat_percent": float(currency.vat_fraction * 100),
    }
    for name, v in profile.volumes.items():
        state[f"vol_{name}"] = float(v.gb_per_sample)
        state[f"archive_{name}"] = v.archive_class
    return state


if "loaded" not in st.session_state:
    st.session_state.update(_default_state())
    st.session_state["loaded"] = True


def _load_demo_profile() -> None:
    st.session_state.update(_default_state())


st.title("CBIO Genomics Infrastructure Cost Planner")
st.caption(
    "Early-stage planning and grant-budgeting tool for CBIO genomics projects. "
    "This is a planning estimate, not an AWS billing system."
)
st.button("Load 500 x 30x WGS / 5-year demo profile", key="load_demo_button", on_click=_load_demo_profile)

pricing = _load_pricing()
_, scenario_movements = _load_profile_and_scenarios()

# ---------------------------------------------------------------------------
# 1. Project
# ---------------------------------------------------------------------------
with st.container(border=True, key="section_1"):
    theme.section_header(1, "Project")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.text_input("Project name", key="project_name")
    with col2:
        st.selectbox("Project type", options=["WGS 30x"], key="project_type")
    with col3:
        st.number_input("Number of samples", min_value=1, step=1, key="num_samples")
    with col4:
        st.text_input("Sequencing depth", key="depth_label")
    with col5:
        st.number_input("Retention period (years)", min_value=0.1, step=0.5, key="retention_years")

# ---------------------------------------------------------------------------
# 2. Data volume assumptions
# ---------------------------------------------------------------------------
with st.container(border=True, key="section_2"):
    theme.section_header(2, "Data volume assumptions")
    st.caption("All assumptions below are editable planning defaults, not measured data.")

    vol_cols = st.columns(3)
    for col, file_type in zip(vol_cols, ("FASTQ", "CRAM", "gVCF")):
        with col:
            st.number_input(
                f"{file_type} GB/sample",
                min_value=0.0,
                step=1.0,
                key=f"vol_{file_type}",
            )

    st.number_input("Storage headroom (%)", min_value=0.0, step=1.0, key="headroom_percent")

# ---------------------------------------------------------------------------
# 3. Data movement model
# ---------------------------------------------------------------------------
with st.container(border=True, key="section_3"):
    theme.section_header(3, "Data movement model")
    st.markdown("**FASTQ** — moves AWS S3 -> Ilifu for primary processing.")
    st.number_input("FASTQ processing passes", min_value=0.0, step=1.0, key="fastq_passes")

    st.markdown("**CRAM** — moves Ilifu -> S3; only a fraction are later retrieved.")
    mcol1, mcol2 = st.columns(2)
    with mcol1:
        st.number_input(
            "CRAM retrieval fraction (%)", min_value=0.0, max_value=100.0, step=1.0, key="cram_retrieval_percent"
        )
    with mcol2:
        st.number_input("CRAM retrieval passes", min_value=0.0, step=1.0, key="cram_retrieval_passes")

    st.markdown("**gVCF** — may move back to Ilifu for cohort joint calling.")
    st.number_input("gVCF processing/retrieval passes", min_value=0.0, step=1.0, key="gvcf_passes")

    st.markdown("**Transfer contingency** — covers reprocessing, failed/restarted transfers, workflow changes, QC.")
    st.number_input("Transfer contingency (%)", min_value=0.0, step=1.0, key="transfer_contingency_percent")

# ---------------------------------------------------------------------------
# 4. Archive storage class selection (grouped with data volume for UI flow)
# ---------------------------------------------------------------------------
with st.container(border=True, key="section_4"):
    theme.section_header(4, "Archive storage class per file type")
    st.caption(
        "Data does not need to move to a separate bucket — the same S3 object key can "
        "transition storage class via an S3 Lifecycle rule."
    )
    theme.process_diagram(
        ["S3 Standard", "Processing / validation", "Lifecycle transition", "Glacier"],
        accent_indices={2},
    )
    st.caption(
        "For Flexible Retrieval and Deep Archive, objects must normally be restored "
        "before being read. Glacier Instant Retrieval can be read directly but has "
        "retrieval charges."
    )
    arc_cols = st.columns(3)
    for col, file_type in zip(arc_cols, ("FASTQ", "CRAM", "gVCF")):
        with col:
            st.selectbox(
                f"{file_type} archive class",
                options=list(STORAGE_CLASS_LABELS.keys()),
                format_func=lambda k: STORAGE_CLASS_LABELS[k],
                key=f"archive_{file_type}",
            )

# ---------------------------------------------------------------------------
# 5. Active storage + AWS transfer settings
# ---------------------------------------------------------------------------
with st.container(border=True, key="section_5"):
    theme.section_header(5, "Active S3 storage & AWS transfer")
    st.number_input("Active S3 Standard period (months)", min_value=0.0, step=1.0, key="active_months")
    st.caption(
        "Data transferred into AWS: AWS internet data-transfer charge: $0. This does not "
        "mean S3 PUT/API requests are free — request and lifecycle-transition costs are "
        "modelled separately below."
    )
    theme.callout(
        "Key implication",
        "AWS-to-Ilifu transfer over the public internet can be a major project cost and "
        "may exceed storage costs.",
    )

# ---------------------------------------------------------------------------
# 6. Infrastructure engineering
# ---------------------------------------------------------------------------
with st.container(border=True, key="section_6"):
    theme.section_header(6, "Infrastructure engineering / management")
    _current_rate = st.session_state.get("hourly_rate_zar", 0)
    theme.callout(
        f"Illustrative engineering rate: R{_current_rate:,.0f}/hour",
        "Planning assumption only — not an approved UCT/CBIO institutional rate. "
        "Replace with an approved CBIO/UCT loaded technical staff rate.",
    )
    ecol1, ecol2, ecol3, ecol4 = st.columns(4)
    with ecol1:
        st.number_input("Onboarding hours", min_value=0.0, step=1.0, key="onboarding_hours")
    with ecol2:
        st.number_input("Operations hours/year", min_value=0.0, step=1.0, key="operations_hours_per_year")
    with ecol3:
        st.number_input("Closeout hours", min_value=0.0, step=1.0, key="closeout_hours")
    with ecol4:
        st.number_input("Hourly rate (ZAR)", min_value=0.0, step=50.0, key="hourly_rate_zar")

# ---------------------------------------------------------------------------
# 7. Ilifu compute
# ---------------------------------------------------------------------------
with st.container(border=True, key="section_7"):
    theme.section_header(7, "Ilifu compute")
    theme.callout("Compute cost not yet included", "Compute cost / entitlement not yet included.")
    st.caption(
        "Future versions should model project classes such as CBIO core, CBIO "
        "collaborative, external academic, and externally funded/service projects, "
        "with controls for fairshare weight, maximum concurrent jobs, CPU/GPU "
        "allocation, scratch quota, and turnaround expectations. No monetary compute "
        "charging is implemented yet."
    )

# ---------------------------------------------------------------------------
# 8. Currency
# ---------------------------------------------------------------------------
with st.container(border=True, key="section_8"):
    theme.section_header(8, "Currency assumptions")
    ccol1, ccol2 = st.columns(2)
    with ccol1:
        st.number_input("USD/ZAR exchange rate", min_value=0.01, step=0.05, key="usd_zar")
    with ccol2:
        st.number_input("VAT (%)", min_value=0.0, step=1.0, key="vat_percent")
    st.caption("Exchange rate/VAT are illustrative defaults — confirm against an approved source before use.")

# ---------------------------------------------------------------------------
# Build inputs -> run calculation
# ---------------------------------------------------------------------------


def _dec(value) -> Decimal:
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return Decimal(0)


try:
    inputs = ProjectInputs(
        project_name=st.session_state["project_name"] or "Untitled project",
        project_type=st.session_state["project_type"],
        num_samples=int(st.session_state["num_samples"]),
        depth_label=st.session_state["depth_label"],
        retention_years=_dec(st.session_state["retention_years"]),
    )
    volumes = {
        file_type: FileTypeVolumeAssumption(
            name=file_type,
            gb_per_sample=_dec(st.session_state[f"vol_{file_type}"]),
            archive_class=st.session_state[f"archive_{file_type}"],
        )
        for file_type in ("FASTQ", "CRAM", "gVCF")
    }
    storage_assumptions = StorageAssumptions(
        headroom_fraction=_dec(st.session_state["headroom_percent"]) / Decimal(100),
        active_months=_dec(st.session_state["active_months"]),
    )
    movement = MovementAssumptions(
        fastq_passes=_dec(st.session_state["fastq_passes"]),
        cram_retrieval_fraction=_dec(st.session_state["cram_retrieval_percent"]) / Decimal(100),
        cram_retrieval_passes=_dec(st.session_state["cram_retrieval_passes"]),
        gvcf_passes=_dec(st.session_state["gvcf_passes"]),
        transfer_contingency=_dec(st.session_state["transfer_contingency_percent"]) / Decimal(100),
    )
    engineering = EngineeringAssumptions(
        onboarding_hours=_dec(st.session_state["onboarding_hours"]),
        operations_hours_per_year=_dec(st.session_state["operations_hours_per_year"]),
        closeout_hours=_dec(st.session_state["closeout_hours"]),
        hourly_rate_zar=_dec(st.session_state["hourly_rate_zar"]),
    )
    currency = CurrencyAssumptions(
        usd_zar=_dec(st.session_state["usd_zar"]),
        vat_fraction=_dec(st.session_state["vat_percent"]) / Decimal(100),
    )

    estimate = build_estimate(inputs, volumes, storage_assumptions, movement, engineering, pricing, currency)
    estimate.explanation = explain_result(estimate)
except ValueError as exc:
    st.error(f"Invalid input: {exc}")
    st.stop()

# ---------------------------------------------------------------------------
# 9. Cost output
# ---------------------------------------------------------------------------
with st.container(border=True, key="section_9"):
    theme.section_header(9, "Cost summary")

    raw_tb = gb_to_tb(estimate.volume.raw_total_gb)
    envelope_tb = gb_to_tb(estimate.volume.envelope_gb)
    egress_tb = gb_to_tb(estimate.transfer.planned_egress_gb)

    scol1, scol2, scol3 = st.columns(3)
    scol1.metric("Durable data", f"{raw_tb:.1f} TB")
    scol2.metric("Provisioned envelope", f"{envelope_tb:.1f} TB")
    scol3.metric("Expected AWS egress", f"{egress_tb:.1f} TB")

    theme.headline(
        "Estimated infrastructure cost",
        f"R{estimate.grand_total_zar:,.0f}",
        "Storage • Transfer • Archive • Engineering — compute not yet included",
    )

    TOTAL_LABEL = "Total project infrastructure cost"
    table_rows: list[list[str]] = []
    table_row_classes: list[str | None] = []
    for item in estimate.line_items:
        table_rows.append([item.label, f"R{item.amount_zar:,.0f}", item.note])
        table_row_classes.append("gro-row-total" if item.label == TOTAL_LABEL else None)
    table_rows.append(["Compute", "Not included", "Not included"])
    table_row_classes.append(None)

    theme.table(
        columns=["Cost component", "Cost (ZAR)", "Note"],
        rows=table_rows,
        align=["left", "right", "left"],
        row_class=table_row_classes,
    )

    ccol1, ccol2 = st.columns(2)
    ccol1.metric("Total AWS cost (USD)", f"${estimate.total_aws_usd:,.2f}")
    ccol2.metric("Total AWS cost (ZAR, ex VAT)", f"R{estimate.total_aws_zar_ex_vat:,.0f}")
    ccol3, ccol4 = st.columns(2)
    ccol3.metric("Total AWS cost (ZAR, incl. VAT)", f"R{estimate.total_aws_zar_inc_vat:,.0f}")
    ccol4.metric("Engineering cost (ZAR)", f"R{estimate.total_engineering_zar:,.0f}")

    chart_df = pd.DataFrame(
        {
            i.label: [float(i.amount_zar)]
            for i in estimate.line_items
            if i.label != "Total project infrastructure cost"
        }
    ).T
    chart_df.columns = ["ZAR"]
    st.bar_chart(chart_df, color=[theme.TEAL])

# ---------------------------------------------------------------------------
# 10. Sensitivity analysis
# ---------------------------------------------------------------------------
with st.container(border=True, key="section_10"):
    theme.section_header(10, "Sensitivity analysis")
    st.caption("Demonstrates that transfer behaviour can materially change total project cost.")

    scenario_estimates = build_scenarios(
        inputs, volumes, storage_assumptions, engineering, pricing, currency, scenario_movements
    )
    sensitivity_rows: list[list[str]] = []
    sensitivity_row_classes: list[str | None] = []
    for name, est in scenario_estimates.items():
        storage_cost = next(i.amount_zar for i in est.line_items if i.label == "Active S3 storage")
        transfer_cost = next(i.amount_zar for i in est.line_items if i.label == "AWS to Ilifu transfer")
        archive_cost = next(i.amount_zar for i in est.line_items if i.label == "Archive storage")
        sensitivity_rows.append(
            [
                name,
                f"{gb_to_tb(est.transfer.planned_egress_gb):.2f} TB",
                f"R{storage_cost:,.0f}",
                f"R{transfer_cost:,.0f}",
                f"R{archive_cost:,.0f}",
                f"R{est.total_engineering_zar:,.0f}",
                f"R{est.grand_total_zar:,.0f}",
            ]
        )
        sensitivity_row_classes.append("gro-row-emphasis" if name == "Expected" else None)

    theme.table(
        columns=[
            "Scenario",
            "Expected egress",
            "Storage (ZAR)",
            "Transfer (ZAR)",
            "Archive (ZAR)",
            "Engineering (ZAR)",
            "Total (ZAR)",
        ],
        rows=sensitivity_rows,
        align=["left", "right", "right", "right", "right", "right", "right"],
        row_class=sensitivity_row_classes,
    )

# ---------------------------------------------------------------------------
# 11. Explanation
# ---------------------------------------------------------------------------
with st.container(border=True, key="section_11"):
    theme.section_header(11, "Result explanation")
    theme.callout("Summary", estimate.explanation)

# ---------------------------------------------------------------------------
# Calculation details — kept outside any section panel (utility detail, not
# a primary section; avoids nesting a card inside a card).
# ---------------------------------------------------------------------------
with st.expander("Calculation details"):
    st.subheader("Data volume")
    for line in estimate.volume.trace:
        st.text(f"{line.label}: {line.detail}")
    st.subheader("Data movement / transfer")
    for line in estimate.transfer.trace:
        st.text(f"{line.label}: {line.detail}")
    st.subheader("Storage cost")
    for line in estimate.storage.trace:
        st.text(f"{line.label}: {line.detail}")
    st.subheader("Engineering cost")
    for line in estimate.operations.trace:
        st.text(f"{line.label}: {line.detail}")
    st.subheader("Archive class details")
    for r in estimate.storage.archive_results:
        st.markdown(f"**{r.file_type} — {STORAGE_CLASS_LABELS[r.storage_class]}**")
        st.text(r.retrieval_characteristics)
        if r.minimum_duration_warning:
            st.warning(r.minimum_duration_warning)

# ---------------------------------------------------------------------------
# 12. Pricing & assumptions
# ---------------------------------------------------------------------------
with st.container(border=True, key="section_12"):
    theme.section_header(12, "Pricing & assumptions")
    st.markdown(
        "AWS storage, request, archive retrieval and data-transfer costs are based on "
        "published AWS pricing for the Africa (Cape Town) region (`af-south-1`). Prices "
        "are planning estimates and should be verified against current AWS/UCT pricing "
        "before budgeting or procurement."
    )

    pcol1, pcol2, pcol3 = st.columns(3)
    with pcol1:
        st.markdown(f"**AWS pricing source:**  \n[{pricing.pricing_source}]({pricing.pricing_source})")
    with pcol2:
        st.markdown(f"**AWS region:**  \n{pricing.region_name} — `{pricing.region}`")
    with pcol3:
        st.markdown(f"**Pricing last verified:**  \n{pricing.pricing_last_verified}")

    st.caption(
        "Data volumes, workflow data movement, retention periods, exchange rate, VAT and "
        "engineering effort are configurable planning assumptions. Compute costs are not "
        "currently included."
    )

    acol1, acol2 = st.columns(2)
    with acol1:
        st.markdown(
            "**Published AWS pricing**\n"
            "- S3 Standard storage price\n"
            "- Glacier storage prices\n"
            "- Request charges\n"
            "- Retrieval charges\n"
            "- Internet data-transfer charges"
        )
    with acol2:
        st.markdown(
            "**CBIO/project planning assumptions**\n"
            "- FASTQ / CRAM / gVCF GB per sample\n"
            "- Active & archive storage duration\n"
            "- Archive class selection\n"
            "- Workflow read/pass counts, CRAM retrieval %\n"
            "- Transfer contingency\n"
            "- Exchange rate, VAT\n"
            "- Engineering hours & hourly rate"
        )

# ---------------------------------------------------------------------------
# 13. Export
# ---------------------------------------------------------------------------
with st.container(border=True, key="section_13"):
    theme.section_header(13, "Export")
    excol1, excol2, excol3 = st.columns(3)
    with excol1:
        st.download_button(
            "Download CSV",
            data=cost_export.to_csv(estimate, pricing),
            file_name=f"{inputs.project_name.replace(' ', '_')}_cost_estimate.csv",
            mime="text/csv",
        )
    with excol2:
        st.download_button(
            "Download JSON",
            data=cost_export.to_json(estimate, pricing),
            file_name=f"{inputs.project_name.replace(' ', '_')}_cost_estimate.json",
            mime="application/json",
        )
    with excol3:
        st.download_button(
            "Download Markdown summary",
            data=cost_export.to_markdown(estimate, pricing),
            file_name=f"{inputs.project_name.replace(' ', '_')}_cost_estimate.md",
            mime="text/markdown",
        )

theme.disclaimer(
    "Prototype planning tool — estimates should be validated before budgeting or procurement.",
    "Actual costs may vary with AWS pricing, exchange rates, data volumes, access "
    "patterns, network path, retrieval behaviour and institutional agreements.",
)
