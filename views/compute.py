"""Compute module — WGS 30x resource, runtime, working-storage and AWS
execution-architecture planner (spec 011).

Only widget reading and rendering happens here; every calculation runs in
``cbio_cost.compute`` / ``cbio_cost.compute_benchmarks``. V1 supports the WGS
30x project profile only (spec 011 objective) — Custom Project compute
modelling is a later iteration.
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
from cbio_cost.project import PROJECT_SESSION_KEY, Project

WORKFLOW_STEPS = ["FASTQ", "BWA-MEM2", "CRAM", "DeepVariant", "gVCF", "GLnexus", "cohort VCF"]
AWS_DEFAULT_USD_ZAR = Decimal("16.05")


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


def _resource_text(cpu, memory_gib) -> str:
    parts = []
    if cpu is not None:
        parts.append(f"{cpu} CPU")
    if memory_gib is not None:
        parts.append(f"{memory_gib:g} GiB")
    return " / ".join(parts) if parts else "not modelled"


def _runtime_text(runtime_hours) -> str:
    if runtime_hours is None:
        return "Not included"
    return f"{runtime_hours:.2f} h"


def _evidence_cell(evidence: Evidence | None) -> str:
    if evidence is None:
        return "Benchmark pending"
    return f"<strong>{evidence.label}</strong>"


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
    with st.container(border=True, key="section_compute"):
        theme.section_header(1, "Compute Planning")
        st.caption(
            "Estimate compute resources, working storage and processing time for the current "
            "project. Results combine measured benchmarks, published benchmarks and explicit "
            "planning assumptions."
        )

        project: Project | None = st.session_state.get(PROJECT_SESSION_KEY)
        is_wgs = (
            project is not None
            and project.metadata.project_type == "WGS 30x"
            and project.metadata.num_samples is not None
        )

        if not is_wgs:
            theme.callout(
                "WGS 30x project required",
                "Compute planning currently supports the WGS 30x project profile (30x whole-genome "
                "sequencing, BWA-MEM2 + DeepVariant + GLnexus workflow). Configure a WGS 30x project "
                "on the Storage page to see Compute estimates. Custom Project compute modelling is "
                "planned for a later iteration.",
            )
            return

        num_samples = project.metadata.num_samples
        st.markdown(f"**Project:** {project.metadata.name}  \n**Profile:** {num_samples} × 30× WGS")

    if "compute_loaded" not in st.session_state:
        st.session_state.update(_default_state())
        st.session_state["compute_loaded"] = True

    # ---------------------------------------------------------------------
    # 2. Workflow
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_compute_workflow"):
        theme.section_header(2, "Workflow")
        theme.process_diagram(WORKFLOW_STEPS, accent_indices={5})
        st.caption(
            "Open-source 30x WGS reference workflow (spec 011). GATK/Sentieon/DRAGEN are future "
            "workflow alternatives, not implemented here."
        )

    # ---------------------------------------------------------------------
    # 3. Compute configuration
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_compute_config"):
        theme.section_header(3, "Compute configuration")
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
        st.caption("Scratch/worker is a planning assumption (spec 011 §13), not a measured BWA requirement.")

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
    config = ComputeConfig(
        alignment_concurrency=int(st.session_state["compute_alignment_concurrency"]),
        deepvariant_concurrency=int(st.session_state["compute_deepvariant_concurrency"]),
        scratch_gib_per_worker=_dec(st.session_state["compute_scratch_gib_per_worker"]),
        alignment_runtime_override_hours=(
            _dec(st.session_state["compute_alignment_override_hours"])
            if st.session_state["compute_alignment_override_enabled"]
            else None
        ),
        deepvariant_runtime_override_hours=(
            _dec(st.session_state["compute_deepvariant_override_hours"])
            if st.session_state["compute_deepvariant_override_enabled"]
            else None
        ),
    )
    result: ComputeResult = compute_engine.build_compute_result(num_samples, config, AWS_DEFAULT_USD_ZAR)

    # ---------------------------------------------------------------------
    # 4. Workflow stages
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_compute_stages"):
        theme.section_header(4, "Workflow stages")
        rows = []
        for stage in result.stages:
            evidence = stage.evidence.get("runtime") or next(iter(stage.evidence.values()), None)
            rows.append(
                [
                    stage.name,
                    stage.scope.replace("_", " "),
                    _resource_text(stage.cpu, stage.memory_gib),
                    _runtime_text(stage.runtime_hours),
                    _evidence_cell(evidence),
                    stage.status,
                ]
            )
        theme.table(
            columns=["Stage", "Scope", "Resources", "Runtime", "Evidence", "Status"],
            rows=rows,
            align=["left", "left", "left", "right", "left", "left"],
        )
        st.caption(
            "Resource values marked as a planning allocation (e.g. alignment RAM) are not the same "
            "as a measured requirement — see Calculation basis & evidence below."
        )

    # ---------------------------------------------------------------------
    # 5. Runtime summary
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_compute_runtime"):
        theme.section_header(5, "Runtime summary")

        st.markdown("**Alignment**")
        _runtime_override("alignment", bm.BWA_RUNTIME_EVIDENCE, "Alignment")
        acol1, acol2, acol3, acol4 = st.columns(4)
        acol1.metric("Runtime/sample", f"{result.alignment.runtime_per_unit_hours:.3f} h")
        acol2.metric("Worker-hours", f"{result.alignment.worker_hours:,.1f}")
        acol3.metric("Concurrency", str(result.alignment.concurrency))
        acol4.metric("Idealised elapsed", f"{result.alignment.idealised_elapsed_hours:,.2f} h")

        st.markdown("**DeepVariant**")
        _runtime_override("deepvariant", bm.DEEPVARIANT_RUNTIME_EVIDENCE, "DeepVariant")
        dcol1, dcol2, dcol3, dcol4 = st.columns(4)
        dcol1.metric("Runtime/sample", f"{result.deepvariant.runtime_per_unit_hours:.3f} h")
        dcol2.metric("Worker-hours", f"{result.deepvariant.worker_hours:,.1f}")
        dcol3.metric("Concurrency", str(result.deepvariant.concurrency))
        dcol4.metric("Idealised elapsed", f"{result.deepvariant.idealised_elapsed_hours:,.2f} h")

        st.markdown("**Cohort calling (GLnexus)**")
        theme.callout(
            "Under investigation",
            "No approved planning benchmark. GLnexus is shown for workflow completeness but is not "
            "included in runtime or cost totals.",
        )

        st.markdown("**Overall**")
        theme.headline(
            "Known modelled elapsed time",
            f"{result.known_modelled_elapsed_hours:,.2f} h",
            "Estimated per-sample processing stages (alignment + DeepVariant, treated as fully "
            "sequential across the cohort).",
        )
        st.warning(
            "Excludes: " + ", ".join(result.excluded_stages) + ", and workflow overhead (queue delay, "
            "instance startup, retries, data staging, interruptions, contention)."
        )

    # ---------------------------------------------------------------------
    # 6. Working storage
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_compute_storage"):
        theme.section_header(6, "Working storage")
        wcol1, wcol2, wcol3 = st.columns(3)
        wcol1.metric("Scratch / worker", f"{result.working_storage.scratch_per_worker_gib:g} GiB")
        wcol2.metric("Concurrent workers", str(result.working_storage.concurrent_workers))
        wcol3.metric("Peak simultaneous scratch", f"{result.working_storage.peak_simultaneous_gib:,.0f} GiB")
        st.caption(
            "Working storage is temporary compute capacity (sort temp files, workflow work "
            "directories, container/cache space) and is not included in the durable Storage estimate."
        )

    # ---------------------------------------------------------------------
    # 7. AWS execution architecture
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_compute_aws"):
        theme.section_header(7, "AWS execution architecture")
        theme.process_diagram(result.aws.architecture_steps, accent_indices={1})
        st.markdown(
            f"**Region:** {result.aws.region_name} (`{result.aws.region_code}`) — kept near the "
            "project's currently modelled AWS storage; cross-region transfer/governance implications "
            "are not modelled."
        )
        st.caption(
            f"AWS Batch orchestration fee: ${result.aws.batch_orchestration_fee_usd} — underlying EC2 "
            "and storage resources are billed normally. Purchase model baseline: "
            f"{result.aws.purchase_model} (Spot is a future/optional optimisation; no fixed discount "
            "is assumed)."
        )
        theme.table(
            columns=["Component", "Status"],
            rows=[
                ["Resource model", "Implemented"],
                ["Runtime model", "Implemented"],
                ["Working storage", "Implemented"],
                ["AWS architecture", "Implemented"],
                ["AWS price", result.aws.pricing_status],
            ],
            align=["left", "left"],
        )

    # ---------------------------------------------------------------------
    # 8. Sentieon
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_compute_sentieon"):
        theme.section_header(8, "Sentieon")
        theme.callout(
            result.sentieon.status,
            f"US${result.sentieon.usd_per_genome}/genome × {result.sentieon.num_samples} samples = "
            f"US${result.sentieon.total_usd:,.2f} (R{result.sentieon.total_zar:,.2f}) — software "
            "licensing only. Does not include compute, storage, transfer or engineering, and is not "
            "included in the current workflow's runtime or cost totals.",
        )
        st.caption(f"{result.sentieon.evidence.label}: {result.sentieon.evidence.source}")

    # ---------------------------------------------------------------------
    # 9. Calculation basis & evidence
    # ---------------------------------------------------------------------
    with st.expander("Calculation basis & evidence"):
        alignment_stage = next(s for s in result.stages if s.name == "BWA-MEM2 + sort")
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
        _evidence_block("DeepVariant", deepvariant_stage.evidence["runtime"])
        st.markdown("---")
        _evidence_block("Scratch", result.working_storage.evidence)

    # ---------------------------------------------------------------------
    # 10. Explicit limitations
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_compute_limitations"):
        theme.section_header(9, "Explicit limitations")
        theme.callout("Read before using these figures", "<br>".join(f"{i + 1}. {item}" for i, item in enumerate(result.limitations)))

    # ---------------------------------------------------------------------
    # 11. Export
    # ---------------------------------------------------------------------
    with st.container(border=True, key="section_compute_export"):
        theme.section_header(10, "Export")
        excol1, excol2, excol3 = st.columns(3)
        file_stub = project.metadata.name.replace(" ", "_") + "_compute_estimate"
        with excol1:
            st.download_button(
                "Download CSV",
                data=cost_export.compute_to_csv(project.metadata.name, num_samples, result),
                file_name=f"{file_stub}.csv",
                mime="text/csv",
            )
        with excol2:
            st.download_button(
                "Download JSON",
                data=cost_export.compute_to_json(project.metadata.name, num_samples, result),
                file_name=f"{file_stub}.json",
                mime="application/json",
            )
        with excol3:
            st.download_button(
                "Download Markdown summary",
                data=cost_export.compute_to_markdown(project.metadata.name, num_samples, result),
                file_name=f"{file_stub}.md",
                mime="text/markdown",
            )

    st.session_state[PROJECT_SESSION_KEY] = project.with_compute(config, result)

    theme.disclaimer(
        "Compute planning estimate — validate before budgeting or procurement.",
        "Runtime, resource and working-storage figures are based on one measured CBIO/Ilifu "
        "benchmark, a published DeepVariant benchmark and explicit planning assumptions. AWS "
        "compute pricing is not yet included.",
    )
