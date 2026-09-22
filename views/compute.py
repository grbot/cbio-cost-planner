"""Compute module — WGS 30x resource, runtime, working-storage and
execution-environment planner (spec 011; refined in spec 011a and 011b).

Only widget reading and rendering happens here; every calculation runs in
``cbio_cost.compute`` / ``cbio_cost.compute_benchmarks``. V1 supports the WGS
30x project profile only — Custom Project compute modelling is a later
iteration.

Workflow (what processing occurs) and execution environment (where/how it
runs) are deliberately rendered as separate sections (spec 011a §4): the
Workflow section below never mentions AWS/HPC, and the Execution environment
section never re-describes the biological/computational steps.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import streamlit as st

import theme
from cbio_cost import compute as compute_engine
from cbio_cost import compute_benchmarks as bm
from cbio_cost import export as cost_export
from cbio_cost.compute_models import ComputeConfig, ComputeResult
from cbio_cost.evidence import Evidence
from cbio_cost.project import PROJECT_SESSION_KEY, Project, build_project
from cbio_cost.project_state import (
    STATUS_LABELS,
    get_project_state,
    record_compute,
    storage_status,
    sync_widget_defaults,
    transfer_status,
)

WORKFLOW_STEPS = ["FASTQ", "BWA-MEM2", "CRAM", "DeepVariant", "gVCF", "GLnexus", "cohort VCF"]
WORKFLOW_SUBTITLES: list[str | None] = [None, "modelled", None, "modelled", None, "benchmark pending", None]
FALLBACK_USD_ZAR = Decimal("16.05")


def _dec(value) -> Decimal:
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return Decimal(0)


def _default_state() -> dict:
    return {
        "compute_alignment_concurrency": 10,
        "compute_deepvariant_concurrency": 10,
        "compute_scratch_gib_per_worker": 250.0,
        "compute_alignment_override_enabled": False,
        "compute_alignment_override_hours": float(bm.BWA_WALL_TIME_HOURS),
        "compute_deepvariant_override_enabled": False,
        "compute_deepvariant_override_hours": float(bm.DEEPVARIANT_RUNTIME_HOURS),
    }


def _stage_resource_text(stage) -> str:
    if stage.name == "CRAM index":
        return bm.CRAM_INDEX_RESOURCE_NOTE
    parts = []
    if stage.cpu is not None:
        parts.append(f"{stage.cpu} CPU")
    if stage.memory_gib is not None:
        parts.append(f"{stage.memory_gib:g} GiB")
    return " / ".join(parts) if parts else "not modelled"


def _runtime_text(runtime_hours) -> str:
    if runtime_hours is None:
        return "Not included"
    return f"{runtime_hours:.2f} h"


def _evidence_cell(evidence: dict[str, Evidence]) -> str:
    """Every distinct evidence classification present on a stage — a stage
    mixing measured and planning-assumption values must not be shown under a
    single evidence label (spec 011a §7)."""
    if not evidence:
        return "Benchmark pending"
    labels: list[str] = []
    seen: set[str] = set()
    for ev in evidence.values():
        if ev.label not in seen:
            seen.add(ev.label)
            labels.append(ev.label)
    return " + ".join(f"<strong>{label}</strong>" for label in labels)


def _evidence_block(label: str, evidence: Evidence) -> None:
    st.markdown(f"**{label}**")
    st.markdown(
        f"{evidence.value} — <strong>{evidence.label}</strong>",
        unsafe_allow_html=True,
    )
    st.caption(f"Source: {evidence.source} ({evidence.date})")
    if evidence.notes:
        st.caption(evidence.notes)


def _runtime_override(config_key: str, benchmark_evidence: Evidence, label: str) -> None:
    enabled = st.session_state[f"compute_{config_key}_override_enabled"]
    if not enabled:
        return
    override_hours = _dec(st.session_state[f"compute_{config_key}_override_hours"])
    st.caption(
        f"Runtime used in calculation: {override_hours:g} h/sample  \n"
        "Basis: User override  \n"
        f"Reference benchmark: {benchmark_evidence.value} — {benchmark_evidence.label}"
    )


def render() -> None:
    state = get_project_state()
    # Shared "which page rendered last" marker (spec 014 §26-30) -- see
    # views/transfer.py's own use of this for why it exists.
    st.session_state["_last_active_page"] = "compute"
    with st.container(border=True, key="section_compute"):
        theme.section_header(1, "Compute Planning")
        st.caption(
            "Estimate compute resources, working storage and processing time for the current "
            "project. Results combine measured benchmarks, published benchmarks and explicit "
            "planning assumptions."
        )

        # Unconfigured gate (spec 014 §5-§8, §48): the minimum-valid
        # bootstrap project always calculates successfully but is not
        # something the user has actually configured -- never show its
        # WGS-specific profile label as though it describes a real project.
        if not state.project_configured:
            theme.callout(
                "Compute",
                "Configure a project to calculate compute requirements.",
            )
            return

        project: Project | None = build_project(state)
        is_wgs = (
            project is not None
            and project.metadata.project_type == "WGS 30x"
            and project.metadata.num_samples is not None
        )

        if not is_wgs:
            theme.callout(
                "Project required",
                "Configure a project in Storage before calculating Compute requirements. "
                "Compute planning currently supports the WGS 30x project profile (30x whole-genome "
                "sequencing, BWA-MEM2 + DeepVariant + GLnexus workflow). Custom Project compute "
                "modelling is planned for a later iteration.",
            )
            return

        num_samples = project.metadata.num_samples
        project_name = project.metadata.name or "Untitled project"
        st.markdown(f"**Project:** {project_name}  \n**Profile:** {num_samples} × 30× WGS")

        theme.guided_flow_line(
            [
                ("1 Storage", STATUS_LABELS[storage_status(state)]),
                ("2 Compute", "You are here"),
                ("3 Transfer", STATUS_LABELS[transfer_status(state)]),
                ("4 Project Summary", "Overview"),
            ]
        )

    sync_widget_defaults(state.compute_widgets or _default_state())

    # ---------------------------------------------------------------------
    # 2. Workflow — what processing occurs (spec 011a §4)
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_compute_workflow"):
        theme.section_header(2, "Workflow")
        theme.process_diagram(WORKFLOW_STEPS, subtitles=WORKFLOW_SUBTITLES)
        st.caption(
            "Open-source 30x WGS reference workflow. GATK, Sentieon and DRAGEN/ICA are future "
            "workflow/execution alternatives — see Alternative execution options below."
        )

    # ---------------------------------------------------------------------
    # 3. Execution environment — where/how the workflow runs (spec 011a §4-§5,
    #    §18, §20-§21). Independent of the concurrency/scratch configuration
    #    below, so it can be shown before the user configures anything.
    # ---------------------------------------------------------------------
    aws_info = compute_engine.aws_execution_info()
    hpc_info = compute_engine.hpc_execution_info()

    with st.container(border=True, key="section_compute_execenv"):
        theme.section_header(3, "Execution environment")
        st.caption(
            "The workflow above describes what processing occurs. Execution environment "
            "describes where and how it runs — a separate planning dimension."
        )

        st.markdown("**Ilifu / HPC**")
        theme.callout(
            hpc_info.status,
            "No HPC monetary cost is currently calculated — this does not mean HPC execution is "
            "free, only that institutional HPC charging/cost allocation is not currently modelled. "
            "Resource and runtime planning below already draw on Ilifu/HPC evidence.",
        )
        hcol1, hcol2, hcol3 = st.columns(3)
        hcol1.metric("Alignment evidence", hpc_info.alignment_runtime_evidence.label)
        hcol2.metric("DeepVariant evidence", hpc_info.deepvariant_runtime_evidence.label)
        hcol3.metric("GLnexus", hpc_info.glnexus_status)
        st.caption(
            f"Monetary cost: {hpc_info.monetary_cost_status}. Working storage: "
            f"{hpc_info.working_storage_status}. Scheduling: {hpc_info.scheduling_status}."
        )

        st.markdown("---")
        st.markdown("**AWS**")
        theme.process_diagram(aws_info.architecture_steps, accent_indices={1})
        st.markdown(
            f"**Region:** {aws_info.region_name} (`{aws_info.region_code}`) — kept near the "
            "project's currently modelled AWS storage; cross-region transfer/governance implications "
            "are not modelled."
        )
        st.caption(
            "AWS Batch does not add a separate service charge. The EC2 worker compute, working "
            "storage, durable S3 storage, data transfer and any software licensing used by the "
            "workflow remain separately billable. Purchase model baseline: "
            f"{aws_info.purchase_model} (Spot is a future/optional optimisation; no fixed discount "
            "is assumed)."
        )
        theme.table(
            columns=["Component", "Status"],
            rows=[
                ["Workflow resource requirements", "Implemented"],
                ["Sequential runtime planning model", "Implemented"],
                ["Working-storage planning model", "Implemented"],
                ["AWS execution architecture", "Implemented"],
                ["EC2 instance mapping", "Pending"],
                ["AWS regional pricing", f"Pending verified <code>{aws_info.region_code}</code> pricing"],
            ],
            align=["left", "left"],
        )
        st.caption(
            "Ilifu and GCP benchmark performance cannot be assumed to reproduce exactly on AWS."
        )

    # ---------------------------------------------------------------------
    # 4. Compute configuration
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_compute_config"):
        theme.section_header(4, "Compute configuration")
        ccol1, ccol2, ccol3 = st.columns(3)
        with ccol1:
            st.number_input(
                "Concurrent alignment workers", min_value=1, step=1, key="compute_alignment_concurrency"
            )
        with ccol2:
            st.number_input(
                "Concurrent DeepVariant workers", min_value=1, step=1, key="compute_deepvariant_concurrency"
            )
        with ccol3:
            st.number_input(
                "Scratch GiB/worker", min_value=0.0, step=10.0, key="compute_scratch_gib_per_worker"
            )
        st.caption(
            "Scratch/worker is a planning assumption, not a measured BWA requirement. The same "
            "figure is currently used for both alignment and DeepVariant workers — each stage's "
            "peak working storage is driven by its own concurrency setting (see Working storage "
            "below)."
        )

        ocol1, ocol2 = st.columns(2)
        with ocol1:
            st.checkbox("Override alignment runtime", key="compute_alignment_override_enabled")
            if st.session_state["compute_alignment_override_enabled"]:
                st.number_input(
                    "Alignment runtime override (h/sample)",
                    min_value=0.0,
                    step=0.1,
                    key="compute_alignment_override_hours",
                )
        with ocol2:
            st.checkbox("Override DeepVariant runtime", key="compute_deepvariant_override_enabled")
            if st.session_state["compute_deepvariant_override_enabled"]:
                st.number_input(
                    "DeepVariant runtime override (h/sample)",
                    min_value=0.0,
                    step=0.1,
                    key="compute_deepvariant_override_hours",
                )
        st.caption("Runtime overrides are user-supplied planning assumptions and never overwrite benchmark evidence.")

    # ---------------------------------------------------------------------
    # Build config -> run calculation
    # ---------------------------------------------------------------------
    compute_widgets = {
        "compute_alignment_concurrency": int(st.session_state["compute_alignment_concurrency"]),
        "compute_deepvariant_concurrency": int(st.session_state["compute_deepvariant_concurrency"]),
        "compute_scratch_gib_per_worker": float(st.session_state["compute_scratch_gib_per_worker"]),
        "compute_alignment_override_enabled": st.session_state["compute_alignment_override_enabled"],
        "compute_alignment_override_hours": float(st.session_state["compute_alignment_override_hours"]),
        "compute_deepvariant_override_enabled": st.session_state["compute_deepvariant_override_enabled"],
        "compute_deepvariant_override_hours": float(st.session_state["compute_deepvariant_override_hours"]),
    }
    config = ComputeConfig(
        alignment_concurrency=compute_widgets["compute_alignment_concurrency"],
        deepvariant_concurrency=compute_widgets["compute_deepvariant_concurrency"],
        scratch_gib_per_worker=_dec(compute_widgets["compute_scratch_gib_per_worker"]),
        alignment_runtime_override_hours=(
            _dec(compute_widgets["compute_alignment_override_hours"])
            if compute_widgets["compute_alignment_override_enabled"]
            else None
        ),
        deepvariant_runtime_override_hours=(
            _dec(compute_widgets["compute_deepvariant_override_hours"])
            if compute_widgets["compute_deepvariant_override_enabled"]
            else None
        ),
    )
    # Shared USD/ZAR planning rate (spec 012a §9): Sentieon's ZAR conversion
    # now follows Storage's editable rate instead of a separate hardcoded
    # constant, so changing it in one place is reflected everywhere (spec
    # 012a §37 currency-invalidation requirement).
    usd_zar = _dec(state.storage_widgets.get("usd_zar", FALLBACK_USD_ZAR))
    result: ComputeResult = compute_engine.build_compute_result(num_samples, config, usd_zar)
    record_compute(state, config, compute_widgets, result)

    # ---------------------------------------------------------------------
    # 5. Workflow stages
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_compute_stages"):
        theme.section_header(5, "Workflow stages")
        rows = []
        for stage in result.stages:
            rows.append(
                [
                    stage.name,
                    stage.scope.replace("_", " "),
                    _stage_resource_text(stage),
                    _runtime_text(stage.runtime_hours),
                    _evidence_cell(stage.evidence),
                    stage.status,
                ]
            )
        theme.table(
            columns=["Stage", "Scope", "Resources", "Runtime", "Evidence", "Status"],
            rows=rows,
            align=["left", "left", "left", "right", "left", "left"],
        )
        st.caption(
            "Where a stage shows more than one evidence classification, resource values were not "
            "all measured — see Calculation basis & evidence below for the per-value breakdown."
        )

    # ---------------------------------------------------------------------
    # 6. Runtime summary
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_compute_runtime"):
        theme.section_header(6, "Runtime summary")

        st.markdown("**Alignment**")
        _runtime_override("alignment", bm.BWA_RUNTIME_EVIDENCE, "Alignment")
        acol1, acol2, acol3, acol4 = st.columns(4)
        acol1.metric("Runtime/sample", f"{result.alignment.runtime_per_unit_hours:.3f} h")
        acol2.metric("Worker-hours", f"{result.alignment.worker_hours:,.1f}")
        acol3.metric(
            "Active workers",
            f"{result.alignment.effective_concurrency} of {result.alignment.configured_concurrency} configured",
        )
        acol4.metric("Idealised elapsed", f"{result.alignment.idealised_elapsed_hours:,.2f} h")

        st.markdown("**CRAM index**")
        st.caption("Shares the alignment stage's concurrency — a lightweight downstream step on the same worker.")
        icol1, icol2, icol3, icol4 = st.columns(4)
        icol1.metric("Runtime/sample", f"{result.cram_index.runtime_per_unit_hours:.3f} h")
        icol2.metric("Worker-hours", f"{result.cram_index.worker_hours:,.1f}")
        icol3.metric(
            "Active workers",
            f"{result.cram_index.effective_concurrency} of {result.cram_index.configured_concurrency} configured",
        )
        icol4.metric("Idealised elapsed", f"{result.cram_index.idealised_elapsed_hours:,.2f} h")

        st.markdown("**DeepVariant**")
        _runtime_override("deepvariant", bm.DEEPVARIANT_RUNTIME_EVIDENCE, "DeepVariant")
        dcol1, dcol2, dcol3, dcol4 = st.columns(4)
        dcol1.metric("Runtime/sample", f"{result.deepvariant.runtime_per_unit_hours:.3f} h")
        dcol2.metric("Worker-hours", f"{result.deepvariant.worker_hours:,.1f}")
        dcol3.metric(
            "Active workers",
            f"{result.deepvariant.effective_concurrency} of {result.deepvariant.configured_concurrency} configured",
        )
        dcol4.metric("Idealised elapsed", f"{result.deepvariant.idealised_elapsed_hours:,.2f} h")

        st.markdown("**Cohort calling (GLnexus)**")
        theme.callout(
            "Under investigation",
            "No approved planning benchmark. GLnexus is shown for workflow completeness but is not "
            "included in runtime or cost totals.",
        )

        st.markdown("**Overall**")
        theme.headline(
            "Sequential-stage planning estimate",
            f"{result.known_modelled_elapsed_hours:,.2f} h",
            "Assumes alignment, CRAM index and DeepVariant execute sequentially across the whole "
            "cohort. Workflow pipelining may reduce elapsed time; pipelining is not currently "
            "modelled.",
        )
        st.warning("Excludes: " + ", ".join(result.excluded_stages) + ". " + result.unmodelled_overhead)

    # ---------------------------------------------------------------------
    # 7. Working storage
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_compute_storage"):
        theme.section_header(7, "Working storage")
        st.caption(
            "The same scratch/worker planning assumption is currently used for both alignment and "
            "DeepVariant workers; each stage's peak scratch is driven by its own concurrency setting."
        )
        wcol1, wcol2, wcol3 = st.columns(3)
        with wcol1:
            st.metric("Scratch / worker", f"{result.working_storage.scratch_per_worker_gib:g} GiB")
        with wcol2:
            st.metric(
                "Alignment peak",
                f"{result.working_storage.alignment_peak_gib:,.0f} GiB",
                help=(
                    f"{result.working_storage.scratch_per_worker_gib:g} GiB × "
                    f"{result.working_storage.alignment_effective_concurrency} active alignment workers"
                ),
            )
            st.caption(
                f"{result.working_storage.alignment_effective_concurrency} active worker(s) from "
                f"{result.working_storage.alignment_configured_concurrency} configured"
            )
        with wcol3:
            st.metric(
                "DeepVariant peak",
                f"{result.working_storage.deepvariant_peak_gib:,.0f} GiB",
                help=(
                    f"{result.working_storage.scratch_per_worker_gib:g} GiB × "
                    f"{result.working_storage.deepvariant_effective_concurrency} active DeepVariant workers"
                ),
            )
            st.caption(
                f"{result.working_storage.deepvariant_effective_concurrency} active worker(s) from "
                f"{result.working_storage.deepvariant_configured_concurrency} configured"
            )
        theme.headline(
            "Peak simultaneous working storage",
            f"{result.working_storage.peak_simultaneous_gib:,.0f} GiB",
            "max(alignment peak, DeepVariant peak) under the sequential-stage execution model — not "
            "their sum, unless stages are explicitly modelled as running concurrently.",
        )
        st.caption(
            "Working storage is temporary compute capacity (sort temp files, workflow work "
            "directories, container/cache space) and is not included in the durable Storage estimate."
        )

    # ---------------------------------------------------------------------
    # 8. Alternative execution options (spec 011a §15)
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_compute_alternatives"):
        theme.section_header(8, "Alternative execution options")
        st.caption(
            "These are not part of the selected open-source workflow and are not included in the "
            "runtime or cost totals above."
        )

        st.markdown("**Sentieon on HPC**")
        theme.callout(
            result.sentieon.status,
            f"US${result.sentieon.usd_per_genome}/genome × {result.sentieon.num_samples} samples = "
            f"US${result.sentieon.total_usd:,.2f} (R{result.sentieon.total_zar:,.2f}) — software "
            "licensing only. Does not include compute, storage, transfer or engineering, and is not "
            "included in the current workflow's runtime or cost totals.",
        )
        st.caption(f"{result.sentieon.evidence.label}: {result.sentieon.evidence.source}")
        st.caption("Converted using the project's current USD/ZAR planning rate.")

        st.markdown("**DRAGEN / Illumina ICA**")
        theme.callout(
            bm.DRAGEN_ICA_STATUS,
            "A future execution-provider/workflow alternative. Not costed in this iteration.",
        )

    # ---------------------------------------------------------------------
    # 9. Workflow accuracy evidence (spec 011a §20-§23)
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_compute_accuracy"):
        theme.section_header(9, "Workflow accuracy evidence")
        st.caption(
            "Variant-calling accuracy depends on the sample, sequencing technology, coverage, truth "
            "set, reference and software configuration. Where possible, workflows should be "
            "evaluated against an appropriate Genome in a Bottle truth set using a consistent "
            "evaluation methodology. Figures below are evidence categories, not scores — no "
            "workflow is ranked and no F1 comparison is made here."
        )
        theme.table(
            columns=["Workflow", "Accuracy evidence category"],
            rows=[
                [
                    "BWA-MEM2 + DeepVariant",
                    f'<a href="{bm.DEEPVARIANT_SOURCE_URL}" target="_blank" rel="noopener noreferrer">'
                    "Published GIAB / hap.py accuracy metrics (DeepVariant)</a>",
                ],
                ["BWA-MEM2 + GATK HaplotypeCaller", "GIAB / precisionFDA benchmark evidence"],
                ["DRAGEN pipeline", "GIAB / precisionFDA benchmark evidence"],
                ["Sentieon pipeline", "GIAB / precisionFDA benchmark evidence"],
            ],
            align=["left", "left"],
        )

    # ---------------------------------------------------------------------
    # Calculation basis & evidence
    # ---------------------------------------------------------------------
    with st.expander("Calculation basis & evidence"):
        alignment_stage = next(s for s in result.stages if s.name == "BWA-MEM2 + sort")
        cram_index_stage = next(s for s in result.stages if s.name == "CRAM index")
        deepvariant_stage = next(s for s in result.stages if s.name == "DeepVariant")

        _evidence_block("Alignment runtime", alignment_stage.evidence["runtime"])
        st.markdown("---")
        st.markdown("**Alignment RAM**")
        st.markdown(
            f"Measured peak: {alignment_stage.evidence['measured_peak_memory'].value}  \n"
            f"Planning allocation: {alignment_stage.memory_gib:g} GiB — "
            f"<strong>{alignment_stage.evidence['memory'].label}</strong>",
            unsafe_allow_html=True,
        )
        st.caption(alignment_stage.evidence["memory"].notes)
        st.markdown("---")
        _evidence_block("CRAM index runtime", cram_index_stage.evidence["runtime"])
        st.markdown("---")
        _evidence_block("DeepVariant", deepvariant_stage.evidence["runtime"])
        st.markdown("---")
        _evidence_block("Scratch", result.working_storage.evidence)

    # ---------------------------------------------------------------------
    # 10. Explicit limitations
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_compute_limitations"):
        theme.section_header(10, "Explicit limitations")
        theme.callout("Read before using these figures", "<br>".join(f"{i + 1}. {item}" for i, item in enumerate(result.limitations)))

    # ---------------------------------------------------------------------
    # 11. Export
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_compute_export"):
        theme.section_header(11, "Export")
        excol1, excol2, excol3 = st.columns(3)
        file_stub = project_name.replace(" ", "_") + "_compute_estimate"
        with excol1:
            st.download_button(
                "Download CSV",
                data=cost_export.compute_to_csv(project_name, num_samples, result),
                file_name=f"{file_stub}.csv",
                mime="text/csv",
            )
        with excol2:
            st.download_button(
                "Download JSON",
                data=cost_export.compute_to_json(project_name, num_samples, result),
                file_name=f"{file_stub}.json",
                mime="application/json",
            )
        with excol3:
            st.download_button(
                "Download Markdown summary",
                data=cost_export.compute_to_markdown(project_name, num_samples, result),
                file_name=f"{file_stub}.md",
                mime="text/markdown",
            )

    st.session_state[PROJECT_SESSION_KEY] = build_project(state)

    # Convenience forward action (spec 012c §21) — see navigation.py's
    # docstring for why this import must be function-local.
    from navigation import TRANSFER_PAGE

    st.page_link(TRANSFER_PAGE, label="Continue to Transfer →")

    theme.disclaimer(
        "Compute planning estimate — validate before budgeting or procurement.",
        "Runtime, resource and working-storage figures are based on one measured CBIO/Ilifu "
        "benchmark, a published DeepVariant benchmark and explicit planning assumptions. AWS "
        "compute pricing is not yet included.",
    )
