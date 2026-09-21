"""Transfer module — endpoint-to-endpoint data-movement planner (spec 012).

Only widget reading and rendering happens here; every calculation runs in
``cbio_cost.transfer_plan``. Works for both WGS 30x and Custom Project modes
(unlike Compute, which is WGS-only for now) since it operates on the shared
project's already-computed ``Dataset`` list rather than any WGS-specific
per-sample logic.

Distinct from Storage's existing AWS-egress-cost assumption (modelled in
``cbio_cost/transfer.py``, unrelated to and untouched by this module) — see
``cbio_cost/transfer_plan.py``'s module docstring for why the two are named
differently.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path

import streamlit as st

import theme
from cbio_cost import config as cost_config
from cbio_cost import export as cost_export
from cbio_cost import transfer_plan
from cbio_cost.evidence import Evidence
from cbio_cost.project import PROJECT_SESSION_KEY, Project, build_project
from cbio_cost.project_state import (
    STATUS_LABELS,
    compute_status,
    get_project_state,
    mark_transfer_invalid,
    record_transfer,
    storage_status,
    sync_widget_defaults,
    transfer_status,
)
from cbio_cost.transfer_plan_models import (
    DEFAULT_EFFICIENCY_PERCENT,
    ENDPOINT_TYPES,
    TRANSFER_METHODS,
    Endpoint,
    TransferPlan,
    TransferPlanResult,
)
from cbio_cost.units import GB_PER_TB, gb_to_tb

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
CUSTOM_DATASET_LABEL = "Custom dataset"
ALL_DATA_LABEL = "All durable project data"


def _load_pricing():
    # Deliberately uncached — see views/storage.py's _load_pricing() for why.
    return cost_config.load_pricing(CONFIG_DIR / "aws-pricing.yaml")


def _dec(value) -> Decimal:
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return Decimal(0)


def _default_state(first_dataset_choice: str) -> dict:
    return {
        "transfer_dataset_choice": first_dataset_choice,
        "transfer_custom_name": "Custom dataset",
        "transfer_custom_size": 1.0,
        "transfer_custom_unit": "TB",
        "transfer_source_type": "institutional",
        "transfer_source_custom_name": "",
        "transfer_destination_type": "aws_s3",
        "transfer_destination_custom_name": "",
        "transfer_throughput_mode": "unknown",
        "transfer_measured_mbps": 0.0,
        "transfer_measured_note": "",
        "transfer_link_capacity_mbps": 1000.0,
        "transfer_efficiency_percent": float(DEFAULT_EFFICIENCY_PERCENT),
        "transfer_method": "Not yet selected",
        "transfer_source_location": "",
        "transfer_destination_location": "",
        "transfer_rtt_enabled": False,
        "transfer_rtt_ms": 0.0,
    }


def _endpoint_from_state(prefix: str, canonical: dict) -> Endpoint:
    endpoint_type = st.session_state[f"transfer_{prefix}_type"]
    if endpoint_type == "custom":
        label = st.session_state[f"transfer_{prefix}_custom_name"].strip()
    else:
        label = ENDPOINT_TYPES[endpoint_type]
    # Fall back to the last canonical value, not a hardcoded blank (spec
    # 012d §10, §42) -- a missing widget key must never present a configured
    # location as empty.
    location_key = f"transfer_{prefix}_location"
    location = st.session_state.get(location_key, canonical.get(location_key, ""))
    return Endpoint(type=endpoint_type, label=label, location=location)


def _duration_text(hours: Decimal | None, days: Decimal | None) -> str:
    if hours is None:
        return "Not available"
    if days is not None and days >= 1:
        return f"{days:.1f} days ({hours:,.1f} h)"
    return f"{hours:.2f} h"


def _evidence_block(label: str, evidence: Evidence | None) -> None:
    if evidence is None:
        st.caption(f"{label}: no single evidence record (see planning scenarios).")
        return
    st.markdown(f"**{label}**")
    st.markdown(f"{evidence.value} — <strong>{evidence.label}</strong>", unsafe_allow_html=True)
    if evidence.source:
        st.caption(f"Source: {evidence.source}" + (f" ({evidence.date})" if evidence.date else ""))
    if evidence.notes:
        st.caption(evidence.notes)


def render() -> None:
    state = get_project_state()
    with st.container(border=True, key="section_transfer"):
        theme.section_header(1, "Transfer Planning")
        st.caption(
            "Estimate data-movement volume, throughput, duration and known transfer costs for "
            "one endpoint-to-endpoint leg of the current project."
        )

        project: Project | None = build_project(state)
        if project is None:
            theme.callout(
                "Project required",
                "Configure a project in Storage before planning a Transfer.",
            )
            return

        st.markdown(f"**Project:** {project.metadata.name or 'Untitled project'}  \n**Mode:** {project.metadata.project_type}")

        theme.guided_flow_line(
            [
                ("1 Storage", STATUS_LABELS[storage_status(state)]),
                ("2 Compute", STATUS_LABELS[compute_status(state)]),
                ("3 Transfer", "You are here"),
                ("4 Project Summary", "Overview"),
            ]
        )

    presets = transfer_plan.dataset_presets(project)
    preset_names = list(presets.keys())
    dataset_options = preset_names + [CUSTOM_DATASET_LABEL]
    default_choice = preset_names[0] if preset_names else CUSTOM_DATASET_LABEL

    # Per-key healing every render (spec 012a §8), fixing the reproduced
    # crash (spec 012a §4): previously all transfer_* defaults were gated
    # behind one "transfer_loaded" flag, so if that flag survived but one
    # individual key (e.g. "transfer_dataset_choice") did not, the next
    # bare st.session_state[...] read below raised a KeyError.
    sync_widget_defaults(state.transfer_widgets or _default_state(default_choice))
    if st.session_state.get("transfer_dataset_choice") not in dataset_options:
        st.session_state["transfer_dataset_choice"] = default_choice

    # ---------------------------------------------------------------------
    # 2. Data to transfer
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_transfer_data"):
        theme.section_header(2, "Data to transfer")
        st.selectbox("Dataset", options=dataset_options, key="transfer_dataset_choice")

        dataset_choice = st.session_state["transfer_dataset_choice"]
        if dataset_choice == CUSTOM_DATASET_LABEL:
            ccol1, ccol2, ccol3 = st.columns([3, 1, 1])
            with ccol1:
                st.text_input("Dataset name", key="transfer_custom_name")
            with ccol2:
                st.number_input("Size", min_value=0.0, step=1.0, key="transfer_custom_size")
            with ccol3:
                st.selectbox("Unit", options=["GB", "TB"], key="transfer_custom_unit")
            size = _dec(st.session_state["transfer_custom_size"])
            unit = st.session_state["transfer_custom_unit"]
            dataset_name = st.session_state["transfer_custom_name"] or "Custom dataset"
            size_gb = size * GB_PER_TB if unit == "TB" else size
        else:
            dataset_name = dataset_choice
            size_gb = presets[dataset_choice]
            size_tb = gb_to_tb(size_gb)
            if dataset_choice != ALL_DATA_LABEL and project.metadata.num_samples:
                gb_per_sample = size_gb / project.metadata.num_samples
                st.caption(
                    f"{project.metadata.num_samples} samples × {gb_per_sample:g} GB/sample = "
                    f"{size_gb:,.0f} GB = {size_tb:.2f} TB"
                )
            else:
                st.caption(f"{size_gb:,.0f} GB = {size_tb:.2f} TB")

        st.caption(
            "Common WGS legs (for reference only — source/destination are always confirmed "
            "explicitly below): FASTQ sequencing centre → compute environment; CRAM/gVCF "
            "compute environment → durable object storage."
        )

    # ---------------------------------------------------------------------
    # 3. Endpoints
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_transfer_endpoints"):
        theme.section_header(3, "Endpoints")
        ecol1, ecol2 = st.columns(2)
        with ecol1:
            st.markdown("**From**")
            st.selectbox(
                "Source",
                options=list(ENDPOINT_TYPES.keys()),
                format_func=lambda k: ENDPOINT_TYPES[k],
                key="transfer_source_type",
                label_visibility="collapsed",
            )
            if st.session_state["transfer_source_type"] == "custom":
                st.text_input("Source name", key="transfer_source_custom_name")
        with ecol2:
            st.markdown("**To**")
            st.selectbox(
                "Destination",
                options=list(ENDPOINT_TYPES.keys()),
                format_func=lambda k: ENDPOINT_TYPES[k],
                key="transfer_destination_type",
                label_visibility="collapsed",
            )
            if st.session_state["transfer_destination_type"] == "custom":
                st.text_input("Destination name", key="transfer_destination_custom_name")

    # Defensive re-heal immediately before reading endpoint/location values
    # (spec 012d §7-9, §42-44): idempotent no-op if line 156's heal already
    # populated every key, but removes any remaining window between a
    # widget key's possible removal and its use here.
    sync_widget_defaults(state.transfer_widgets)

    try:
        source = _endpoint_from_state("source", state.transfer_widgets)
        destination = _endpoint_from_state("destination", state.transfer_widgets)
    except ValueError as exc:
        st.error(f"Invalid endpoint: {exc}")
        st.stop()

    same_endpoint = source.type == destination.type and (source.type != "custom" or source.label == destination.label)
    if same_endpoint:
        theme.callout(
            "Source and destination must differ",
            "Select different source and destination endpoints to see a Transfer estimate.",
        )
        return

    # ---------------------------------------------------------------------
    # 4. Network throughput
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_transfer_throughput"):
        theme.section_header(4, "Network throughput")
        st.radio(
            "Throughput basis",
            options=["measured", "known_capacity", "unknown"],
            format_func=lambda m: {
                "measured": "Measured throughput",
                "known_capacity": "Known link capacity",
                "unknown": "Unknown throughput",
            }[m],
            key="transfer_throughput_mode",
        )
        mode = st.session_state["transfer_throughput_mode"]
        if mode == "measured":
            mcol1, mcol2 = st.columns(2)
            with mcol1:
                st.number_input("Measured throughput (Mbps)", min_value=0.0, step=10.0, key="transfer_measured_mbps")
            with mcol2:
                st.text_input("Note (optional)", key="transfer_measured_note", placeholder="e.g. Globus transfer UCT → Ilifu")
            st.caption("Do not treat a speed-test result as equivalent to sustained bulk-transfer throughput.")
        elif mode == "known_capacity":
            lcol1, lcol2 = st.columns(2)
            with lcol1:
                st.number_input("Link capacity (Mbps)", min_value=0.0, step=100.0, key="transfer_link_capacity_mbps")
            with lcol2:
                st.number_input(
                    "Planning efficiency (%)", min_value=0.0, max_value=100.0, step=5.0, key="transfer_efficiency_percent"
                )
            st.caption(
                f"Planning throughput = link capacity × efficiency. Default efficiency "
                f"({DEFAULT_EFFICIENCY_PERCENT}%) is a planning assumption, not a measured figure — "
                "applications rarely sustain theoretical line rate."
            )
        else:
            st.caption(
                "Throughput is not yet known. The planning-scenario table below shows estimated "
                "duration at several common throughputs — none is presented as expected or measured."
            )

    # ---------------------------------------------------------------------
    # 5. Transfer method
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_transfer_method"):
        theme.section_header(5, "Transfer method")
        st.selectbox("Expected transfer mechanism", options=TRANSFER_METHODS, key="transfer_method")
        st.caption("Descriptive only — the transfer method does not automatically change the throughput used above.")

    # `source`/`destination` above already carry location (_endpoint_from_state
    # reads transfer_{source,destination}_location). Network path details —
    # the widgets for those location fields, plus RTT — are rendered as
    # section 7, below the estimate, matching the spec's suggested page
    # order. Reading them here, before that widget is (re-)drawn later this
    # run, relies on a Streamlit widget's session-state value from the
    # *previous* run persisting at the top of the current one regardless of
    # draw order (spec 012a) — hardened by the explicit re-heal above and
    # _endpoint_from_state()'s canonical-state fallback (spec 012d §7-10,
    # §42-44), so a widget key that Streamlit removed between runs is
    # restored from ``ProjectState`` rather than silently reset to blank.

    # ---------------------------------------------------------------------
    # Build plan -> run calculation
    # ---------------------------------------------------------------------
    try:
        plan = TransferPlan(
            dataset_name=dataset_name,
            size_gb=size_gb,
            source=source,
            destination=destination,
            throughput_mode=mode,
            transfer_method=st.session_state["transfer_method"],
            measured_mbps=_dec(st.session_state["transfer_measured_mbps"]) if mode == "measured" else None,
            measured_note=st.session_state["transfer_measured_note"],
            link_capacity_mbps=_dec(st.session_state["transfer_link_capacity_mbps"]) if mode == "known_capacity" else None,
            efficiency_percent=_dec(st.session_state["transfer_efficiency_percent"]) if mode == "known_capacity" else None,
            rtt_ms=_dec(st.session_state["transfer_rtt_ms"]) if st.session_state["transfer_rtt_enabled"] else None,
        )
    except ValueError as exc:
        # Record invalidity without touching the last valid config/result
        # (spec 012c §11-13, §32) — status must reflect that the *current*
        # input is broken, not silently keep reporting the old calculation
        # as current.
        mark_transfer_invalid(state)
        st.error(f"Invalid input: {exc}")
        st.stop()
        return  # st.stop() halts a real Streamlit script; explicit for tests/bare mode

    pricing = _load_pricing()
    result: TransferPlanResult = transfer_plan.build_transfer_plan_result(plan, pricing)

    # Unconditional capture — no "if key in st.session_state" filter (spec
    # 012c §6): sync_widget_defaults() already guarantees every one of these
    # keys exists by this point, so a filter here could only ever silently
    # and permanently drop a key from canonical state with no way for later
    # healing to recover it (a canonical state with a hole stays full of
    # holes, since healing only ever fills gaps *from* canonical state).
    # Falls back to the previous canonical value (not the hardcoded default)
    # for any key that is somehow still missing (spec 012d §10, §42) — a
    # missing widget key must never write a fresh default over a configured
    # value.
    transfer_widgets = {
        key: st.session_state.get(key, state.transfer_widgets.get(key, default))
        for key, default in _default_state(default_choice).items()
    }
    record_transfer(state, plan, transfer_widgets, result)

    # ---------------------------------------------------------------------
    # 6. Transfer estimate
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_transfer_estimate"):
        theme.section_header(6, "Transfer estimate")
        st.markdown(f"**{plan.dataset_name}**  \n{source.label} → {destination.label}")

        vcol1, vcol2 = st.columns(2)
        vcol1.metric("Data volume", f"{result.size_tb:.2f} TB")
        vcol2.metric("Data volume (GB)", f"{plan.size_gb:,.0f} GB")

        if mode == "unknown":
            st.markdown("**Planning scenarios**")
            theme.table(
                columns=["Planning throughput", "Estimated duration"],
                rows=[[s.label, _duration_text(s.duration_hours, s.duration_days)] for s in result.scenarios],
                align=["right", "right"],
            )
            st.caption("No throughput above is recommended or presented as expected — these are planning scenarios only.")
        else:
            basis = "Measured sustained throughput" if mode == "measured" else "Known link capacity × planning efficiency"
            st.markdown(f"**Throughput basis:** {basis}")
            theme.headline(
                "Estimated transfer duration",
                _duration_text(result.duration_hours, result.duration_days),
                f"Planning throughput: {result.throughput.effective_mbps:,.0f} Mbps",
            )

    # ---------------------------------------------------------------------
    # 7. Network path details (optional / advanced)
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_transfer_path"):
        theme.section_header(7, "Network path details (optional / advanced)")
        with st.expander("Location and round-trip time"):
            pcol1, pcol2 = st.columns(2)
            with pcol1:
                st.text_input("Source location", key="transfer_source_location", placeholder="e.g. Cape Town")
            with pcol2:
                st.text_input("Destination location", key="transfer_destination_location", placeholder="e.g. Frankfurt")
            st.caption("Descriptive only — bandwidth is never inferred from geography.")
            st.checkbox("Provide round-trip time (RTT)", key="transfer_rtt_enabled")
            if st.session_state["transfer_rtt_enabled"]:
                st.number_input("Round-trip time (ms)", min_value=0.0, step=10.0, key="transfer_rtt_ms")

            if result.bdp is not None:
                st.markdown("---")
                bcol1, bcol2 = st.columns(2)
                bcol1.metric("Round-trip time", f"{result.bdp.rtt_ms:g} ms")
                bcol2.metric("Data in flight (BDP)", f"{result.bdp.bdp_mb:,.1f} MB")
                st.caption(
                    "Bandwidth-delay product is informational only — not additional project storage, "
                    "and does not change the duration calculation above. Long-distance high-bandwidth "
                    "paths may require sufficient TCP windowing and/or parallel streams (e.g. Globus, "
                    "parallel multipart S3 transfers, rclone parallelism, institutional DTNs) to "
                    "approach link capacity."
                )

    # ---------------------------------------------------------------------
    # 8. Cost status
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_transfer_cost"):
        theme.section_header(8, "Cost status")
        pc = result.provider_cost
        if pc.status == "calculated":
            theme.headline("Provider transfer cost", f"${pc.cost_usd:,.2f}", pc.basis)
            st.caption(
                f"AWS pricing source: {pricing.pricing_source}  \n"
                f"Pricing last verified: {pricing.pricing_last_verified} — treat as a planning "
                "estimate, the same caveat Storage's pricing carries."
            )
        else:
            theme.callout("Provider transfer cost — not currently calculated", pc.basis)

    # ---------------------------------------------------------------------
    # 9. Assumptions and evidence
    # ---------------------------------------------------------------------
    with st.expander("Assumptions and evidence"):
        _evidence_block("Throughput", result.throughput.evidence)
        if result.provider_cost.evidence is not None:
            st.markdown("---")
            _evidence_block("Provider transfer cost", result.provider_cost.evidence)
        st.markdown("---")
        theme.callout("Read before using these figures", "<br>".join(f"{i + 1}. {item}" for i, item in enumerate(result.limitations)))

    # ---------------------------------------------------------------------
    # 10. Export
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_transfer_export"):
        theme.section_header(10, "Export")
        excol1, excol2, excol3 = st.columns(3)
        file_stub = (project.metadata.name or "project").replace(" ", "_") + "_transfer_estimate"
        with excol1:
            st.download_button(
                "Download CSV",
                data=cost_export.transfer_plan_to_csv(project.metadata.name, result),
                file_name=f"{file_stub}.csv",
                mime="text/csv",
            )
        with excol2:
            st.download_button(
                "Download JSON",
                data=cost_export.transfer_plan_to_json(project.metadata.name, result),
                file_name=f"{file_stub}.json",
                mime="application/json",
            )
        with excol3:
            st.download_button(
                "Download Markdown summary",
                data=cost_export.transfer_plan_to_markdown(project.metadata.name, result),
                file_name=f"{file_stub}.md",
                mime="text/markdown",
            )

    st.session_state[PROJECT_SESSION_KEY] = build_project(state)

    # Convenience forward action (spec 012c §21) — see navigation.py's
    # docstring for why this import must be function-local.
    from navigation import SUMMARY_PAGE

    st.page_link(SUMMARY_PAGE, label="Review Project Summary →")

    theme.disclaimer(
        "Transfer planning estimate — validate before budgeting or scheduling.",
        "Duration and cost figures depend on the throughput basis, endpoint pair and pricing "
        "assumptions selected above. The planner does not move genomic data itself.",
    )
