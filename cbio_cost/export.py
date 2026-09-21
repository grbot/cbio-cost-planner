"""Serialize a CostEstimate to CSV, JSON, and Markdown (spec §18; spec 006 §21)."""

from __future__ import annotations

import csv
import io
import json
from decimal import Decimal
from typing import Any

from cbio_cost.compute_models import ComputeResult
from cbio_cost.models import CostEstimate, PricingConfig
from cbio_cost.units import gb_to_tb

STORAGE_CLASS_LABELS = {
    "s3_standard": "S3 Standard",
    "glacier_instant": "Glacier Instant Retrieval",
    "glacier_flexible": "Glacier Flexible Retrieval",
    "glacier_deep_archive": "Glacier Deep Archive",
}


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Object of type {type(value)} is not JSON serializable")


def _provenance_rows(estimate: CostEstimate, pricing: PricingConfig) -> list[list[str]]:
    """Pricing/assumption provenance as label/value pairs, shared by CSV and (in spirit) Markdown."""
    return [
        ["AWS region", f"{pricing.region_name} ({pricing.region})"],
        ["Pricing source", pricing.pricing_source],
        ["Pricing last verified", pricing.pricing_last_verified],
        ["USD/ZAR exchange rate", str(estimate.currency.usd_zar)],
        ["VAT", f"{estimate.currency.vat_fraction * 100}%"],
        ["Engineering rate", "Illustrative planning assumption, not an approved UCT/CBIO rate"],
        ["Compute", "Resource/runtime planning available on Compute page — cost not included"],
    ]


def to_csv(estimate: CostEstimate, pricing: PricingConfig) -> str:
    """Render the cost-component breakdown as CSV text."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Project", estimate.inputs.project_name])
    writer.writerow(["Project mode", estimate.inputs.project_type])
    writer.writerow(["Retention (years)", estimate.inputs.retention_years])
    writer.writerow([])
    writer.writerow(["Datasets", str(len(estimate.datasets))])
    writer.writerow(["Dataset", "Size (GB)", "Retrieval %", "Passes", "Active (months)", "Archive class"])
    for d in estimate.datasets:
        writer.writerow(
            [
                d.name,
                str(d.size_gb),
                str(d.retrieval_fraction * 100),
                str(d.read_passes),
                str(d.active_months),
                STORAGE_CLASS_LABELS.get(d.archive_class, d.archive_class),
            ]
        )
    writer.writerow([])
    writer.writerow(["Cost component", "Amount (ZAR)", "Note"])
    for item in estimate.line_items:
        writer.writerow([item.label, str(item.amount_zar), item.note])
    writer.writerow(["Compute", "Not included", "Resource/runtime planning available on Compute page — cost not included"])
    writer.writerow([])
    writer.writerow(["Pricing & assumptions", ""])
    for label, value in _provenance_rows(estimate, pricing):
        writer.writerow([label, value])
    return buffer.getvalue()


def to_json(estimate: CostEstimate, pricing: PricingConfig) -> str:
    """Render the full estimate (including per-dataset detail) as JSON text."""
    payload = {
        "project": {
            "project_name": estimate.inputs.project_name,
            "project_type": estimate.inputs.project_type,
            "num_samples": estimate.inputs.num_samples,
            "retention_years": str(estimate.inputs.retention_years),
            "transfer_contingency_percent": str(estimate.inputs.transfer_contingency * 100),
            "headroom_percent": str(estimate.inputs.headroom_fraction * 100),
        },
        "datasets": [
            {
                "name": d.name,
                "size_gb": str(d.size_gb),
                "retrieval_percent": str(d.retrieval_fraction * 100),
                "read_passes": str(d.read_passes),
                "active_months": str(d.active_months),
                "archive_class": STORAGE_CLASS_LABELS.get(d.archive_class, d.archive_class),
            }
            for d in estimate.datasets
        ],
        "volume": {
            "raw_total_gb": str(estimate.volume.raw_total_gb),
            "envelope_gb": str(estimate.volume.envelope_gb),
        },
        "transfer": {
            "per_dataset_egress_gb": {d.name: str(d.base_egress_gb) for d in estimate.transfer.datasets},
            "base_egress_gb": str(estimate.transfer.base_egress_gb),
            "planned_egress_gb": str(estimate.transfer.planned_egress_gb),
            "egress_cost_usd": str(estimate.transfer.egress_cost_usd),
        },
        "cost_components_zar": {item.label: str(item.amount_zar) for item in estimate.line_items},
        "totals": {
            "total_aws_usd": str(estimate.total_aws_usd),
            "total_aws_zar_ex_vat": str(estimate.total_aws_zar_ex_vat),
            "total_aws_zar_inc_vat": str(estimate.total_aws_zar_inc_vat),
            "total_engineering_zar": str(estimate.total_engineering_zar),
            "grand_total_zar": str(estimate.grand_total_zar),
        },
        "compute": "Resource/runtime planning available on Compute page — cost not included",
        "explanation": estimate.explanation,
        "pricing_provenance": {
            "provider": pricing.provider,
            "region_code": pricing.region,
            "region_name": pricing.region_name,
            "pricing_source": pricing.pricing_source,
            "pricing_last_verified": pricing.pricing_last_verified,
            "usd_zar_exchange_rate": str(estimate.currency.usd_zar),
            "vat_percent": str(estimate.currency.vat_fraction * 100),
            "engineering_rate_note": "Illustrative planning assumption, not an approved UCT/CBIO rate",
            "compute_note": "Resource/runtime planning available on Compute page — cost not included",
        },
    }
    return json.dumps(payload, indent=2, default=_json_default)


def to_markdown(estimate: CostEstimate, pricing: PricingConfig) -> str:
    """Render a concise Markdown project-cost summary."""
    inputs = estimate.inputs
    raw_tb = gb_to_tb(estimate.volume.raw_total_gb)
    envelope_tb = gb_to_tb(estimate.volume.envelope_gb)
    egress_tb = gb_to_tb(estimate.transfer.planned_egress_gb)

    lines = [
        f"# {inputs.project_name} — Infrastructure Cost Estimate",
        "",
        f"- Project mode: {inputs.project_type}",
    ]
    if inputs.num_samples is not None:
        lines.append(f"- Samples: {inputs.num_samples}")
    lines.extend(
        [
            f"- Retention: {inputs.retention_years} years",
            f"- Datasets: {len(estimate.datasets)}",
            f"- Durable data: {raw_tb:.1f} TB",
            f"- Provisioned envelope: {envelope_tb:.1f} TB",
            f"- Expected AWS egress: {egress_tb:.1f} TB",
            "",
            "## Datasets",
            "",
            "| Dataset | Size (GB) | Retrieval | Passes | Active (months) | Archive class |",
            "|---|---:|---:|---:|---:|---|",
        ]
    )
    for d in estimate.datasets:
        lines.append(
            f"| {d.name} | {d.size_gb:,.0f} | {d.retrieval_fraction * 100:.0f}% | {d.read_passes} | "
            f"{d.active_months} | {STORAGE_CLASS_LABELS.get(d.archive_class, d.archive_class)} |"
        )
    lines.append("")
    lines.append("| Cost component | Cost (ZAR) |")
    lines.append("|---|---:|")
    for item in estimate.line_items:
        lines.append(f"| {item.label} | R{item.amount_zar:,.2f} |")
    lines.append("| Compute | Not included (resource/runtime planning available on Compute page) |")
    lines.append("")
    if estimate.explanation:
        lines.append(estimate.explanation)
        lines.append("")

    lines.append("## Pricing & assumptions")
    lines.append("")
    lines.append(f"- AWS region: {pricing.region_name} (`{pricing.region}`)")
    lines.append(f"- Pricing source: {pricing.pricing_source}")
    lines.append(f"- Pricing last verified: {pricing.pricing_last_verified}")
    lines.append(f"- USD/ZAR exchange rate: {estimate.currency.usd_zar}")
    lines.append(f"- VAT: {estimate.currency.vat_fraction * 100}%")
    lines.append("- Engineering rate is an illustrative planning assumption, not an approved UCT/CBIO rate.")
    lines.append("- Compute runtime and resource planning are available on the Compute page; compute infrastructure cost is not yet included.")
    lines.append(
        "- Infrastructure cost estimates do not constitute approval to store sensitive research "
        "data in AWS or other cloud/object storage. Project-specific consent, ethics, data-access "
        "and institutional requirements must be reviewed separately."
    )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Compute exports (spec 011 §33) — additive; Storage's to_csv/to_json/
# to_markdown above are untouched. GLnexus/AWS pricing/Sentieon export as
# ``None``/"not modelled"/"excluded", never as ``0``.
# ---------------------------------------------------------------------------


def _stage_row(stage) -> dict[str, Any]:
    return {
        "name": stage.name,
        "workflow_stage": stage.workflow_stage,
        "scope": stage.scope,
        "status": stage.status,
        "cpu": stage.cpu,
        "memory_gib": str(stage.memory_gib) if stage.memory_gib is not None else None,
        "runtime_hours": str(stage.runtime_hours) if stage.runtime_hours is not None else None,
        "included_in_total": stage.included_in_total,
        "evidence": {
            key: {
                "classification": ev.classification,
                "label": ev.label,
                "source": ev.source,
                "date": ev.date,
                "value": ev.value,
                "notes": ev.notes,
            }
            for key, ev in stage.evidence.items()
        },
    }


def _concurrency_row(result) -> dict[str, Any]:
    return {
        "samples": result.samples,
        "configured_concurrency": result.configured_concurrency,
        "effective_concurrency": result.effective_concurrency,
        "runtime_per_unit_hours": str(result.runtime_per_unit_hours),
        "runtime_basis": result.runtime_basis,
        "waves": result.waves,
        "worker_hours": str(result.worker_hours),
        "idealised_elapsed_hours": str(result.idealised_elapsed_hours),
        "runtime_evidence_classification": result.runtime_evidence.classification,
    }


EXECUTION_ENVIRONMENT_SUMMARY = "Ilifu/HPC (reference) and AWS (architecture defined, pricing pending)"
ELAPSED_TIME_MODEL = "Sequential-stage planning estimate"
COMPUTE_COST_STATUS = "Not yet calculated"


def compute_to_json(project_name: str, num_samples: int, result: ComputeResult) -> str:
    """Render the Compute planning result as JSON text (spec 011 §33; fields
    extended in spec 011a §26)."""
    alignment_stage = next(s for s in result.stages if s.name == "BWA-MEM2 + sort")
    cram_index_stage = next(s for s in result.stages if s.name == "CRAM index")

    payload = {
        "project": {"project_name": project_name, "num_samples": num_samples},
        "workflow": "FASTQ -> BWA-MEM2 -> CRAM index -> DeepVariant -> gVCF -> GLnexus -> cohort VCF",
        "execution_environment": EXECUTION_ENVIRONMENT_SUMMARY,
        "stages": [_stage_row(s) for s in result.stages],
        "alignment": _concurrency_row(result.alignment),
        "alignment_measured_peak_ram": alignment_stage.evidence["measured_peak_memory"].value,
        "alignment_planning_ram": f"{alignment_stage.memory_gib} GiB",
        "configured_alignment_workers": result.alignment.configured_concurrency,
        "effective_alignment_concurrency": result.alignment.effective_concurrency,
        "configured_deepvariant_workers": result.deepvariant.configured_concurrency,
        "effective_deepvariant_concurrency": result.deepvariant.effective_concurrency,
        "cram_index": _concurrency_row(result.cram_index),
        "cram_index_runtime": str(cram_index_stage.runtime_hours),
        "cram_index_evidence": cram_index_stage.evidence["runtime"].label,
        "deepvariant": _concurrency_row(result.deepvariant),
        "glnexus": {
            "status": result.glnexus.status,
            "runtime_hours": None,
            "included_in_total": False,
            "note": "not modelled — no approved planning benchmark",
        },
        "glnexus_status": result.glnexus.status,
        "known_modelled_elapsed_hours": str(result.known_modelled_elapsed_hours),
        "elapsed_time_model": ELAPSED_TIME_MODEL,
        "excluded_stages": result.excluded_stages,
        "unmodelled_overhead": result.unmodelled_overhead,
        "working_storage": {
            "scratch_per_worker_gib": str(result.working_storage.scratch_per_worker_gib),
            "alignment_configured_concurrency": result.working_storage.alignment_configured_concurrency,
            "alignment_effective_concurrency": result.working_storage.alignment_effective_concurrency,
            "deepvariant_configured_concurrency": result.working_storage.deepvariant_configured_concurrency,
            "deepvariant_effective_concurrency": result.working_storage.deepvariant_effective_concurrency,
            "alignment_peak_gib": str(result.working_storage.alignment_peak_gib),
            "deepvariant_peak_gib": str(result.working_storage.deepvariant_peak_gib),
            "peak_simultaneous_gib": str(result.working_storage.peak_simultaneous_gib),
        },
        "scratch_evidence": result.working_storage.evidence.label,
        "aws": {
            "region_code": result.aws.region_code,
            "region_name": result.aws.region_name,
            "architecture_steps": result.aws.architecture_steps,
            "batch_orchestration_fee_usd": str(result.aws.batch_orchestration_fee_usd),
            "purchase_model": result.aws.purchase_model,
            "pricing_status": result.aws.pricing_status,
            "compute_cost": "not modelled",
        },
        "hpc": {
            "status": result.hpc.status,
            "alignment_runtime_evidence": result.hpc.alignment_runtime_evidence.label,
            "deepvariant_runtime_evidence": result.hpc.deepvariant_runtime_evidence.label,
            "glnexus_status": result.hpc.glnexus_status,
            "monetary_cost_status": result.hpc.monetary_cost_status,
            "working_storage_status": result.hpc.working_storage_status,
            "scheduling_status": result.hpc.scheduling_status,
        },
        "compute_cost_status": COMPUTE_COST_STATUS,
        "sentieon": {
            "usd_per_genome": str(result.sentieon.usd_per_genome),
            "total_usd": str(result.sentieon.total_usd),
            "total_zar": str(result.sentieon.total_zar),
            "status": result.sentieon.status,
            "included_in_total": False,
        },
        "limitations": result.limitations,
    }
    return json.dumps(payload, indent=2, default=_json_default)


def compute_to_csv(project_name: str, num_samples: int, result: ComputeResult) -> str:
    """Render the Compute stage/runtime breakdown as CSV text (spec 011 §33;
    fields extended in spec 011a §26)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Project", project_name])
    writer.writerow(["Samples", num_samples])
    writer.writerow(["Execution environment", EXECUTION_ENVIRONMENT_SUMMARY])
    writer.writerow([])
    writer.writerow(["Stage", "Scope", "CPU", "Memory (GiB)", "Runtime (h)", "Status", "Included in total"])
    for s in result.stages:
        writer.writerow(
            [
                s.name,
                s.scope,
                s.cpu if s.cpu is not None else "not modelled",
                s.memory_gib if s.memory_gib is not None else "not modelled",
                s.runtime_hours if s.runtime_hours is not None else "not modelled",
                s.status,
                s.included_in_total,
            ]
        )
    writer.writerow([])
    writer.writerow(["Elapsed time model", ELAPSED_TIME_MODEL])
    writer.writerow(["Known modelled elapsed time (h)", str(result.known_modelled_elapsed_hours)])
    writer.writerow(["Excluded stages", "; ".join(result.excluded_stages)])
    writer.writerow(["Unmodelled overhead", result.unmodelled_overhead])
    writer.writerow(["GLnexus status", result.glnexus.status])
    writer.writerow([])
    writer.writerow(["Working storage: scratch/worker (GiB)", str(result.working_storage.scratch_per_worker_gib)])
    writer.writerow(["Working storage: scratch evidence", result.working_storage.evidence.label])
    writer.writerow(
        ["Working storage: alignment configured concurrency", str(result.working_storage.alignment_configured_concurrency)]
    )
    writer.writerow(
        ["Working storage: alignment effective concurrency", str(result.working_storage.alignment_effective_concurrency)]
    )
    writer.writerow(["Working storage: alignment peak (GiB)", str(result.working_storage.alignment_peak_gib)])
    writer.writerow(
        ["Working storage: DeepVariant configured concurrency", str(result.working_storage.deepvariant_configured_concurrency)]
    )
    writer.writerow(
        ["Working storage: DeepVariant effective concurrency", str(result.working_storage.deepvariant_effective_concurrency)]
    )
    writer.writerow(["Working storage: DeepVariant peak (GiB)", str(result.working_storage.deepvariant_peak_gib)])
    writer.writerow(["Working storage: peak simultaneous (GiB)", str(result.working_storage.peak_simultaneous_gib)])
    writer.writerow([])
    writer.writerow(["configured_alignment_workers", result.alignment.configured_concurrency])
    writer.writerow(["effective_alignment_concurrency", result.alignment.effective_concurrency])
    writer.writerow(["configured_deepvariant_workers", result.deepvariant.configured_concurrency])
    writer.writerow(["effective_deepvariant_concurrency", result.deepvariant.effective_concurrency])
    writer.writerow([])
    writer.writerow(["AWS region", f"{result.aws.region_name} ({result.aws.region_code})"])
    writer.writerow(["AWS compute price", result.aws.pricing_status])
    writer.writerow(["HPC monetary cost", result.hpc.monetary_cost_status])
    writer.writerow(["Compute cost status", COMPUTE_COST_STATUS])
    writer.writerow([])
    writer.writerow(["Sentieon (US$/genome)", str(result.sentieon.usd_per_genome)])
    writer.writerow(["Sentieon status", result.sentieon.status])
    return buffer.getvalue()


def compute_to_markdown(project_name: str, num_samples: int, result: ComputeResult) -> str:
    """Render a concise Markdown Compute planning summary (spec 011 §33;
    fields extended in spec 011a §26)."""
    lines = [
        f"# {project_name} — Compute Planning",
        "",
        f"- Samples: {num_samples}",
        "- Workflow: FASTQ -> BWA-MEM2 -> CRAM index -> DeepVariant -> gVCF -> GLnexus -> cohort VCF",
        f"- Execution environment: {EXECUTION_ENVIRONMENT_SUMMARY}",
        "",
        "## Workflow stages",
        "",
        "| Stage | Scope | Resources | Runtime | Status |",
        "|---|---|---|---:|---|",
    ]
    for s in result.stages:
        resources = ", ".join(
            part
            for part in [
                f"{s.cpu} CPU" if s.cpu is not None else None,
                f"{s.memory_gib} GiB" if s.memory_gib is not None else None,
            ]
            if part
        ) or "not modelled"
        runtime = f"{s.runtime_hours:.3f} h" if s.runtime_hours is not None else "not modelled"
        lines.append(f"| {s.name} | {s.scope} | {resources} | {runtime} | {s.status} |")
    lines.extend(
        [
            "",
            f"**Elapsed time model:** {ELAPSED_TIME_MODEL}",
            f"**Known modelled elapsed time:** {result.known_modelled_elapsed_hours:.2f} h "
            f"(excludes {', '.join(result.excluded_stages)}; {result.unmodelled_overhead})",
            "",
            "## Working storage",
            "",
            f"- Scratch/worker: {result.working_storage.scratch_per_worker_gib} GiB "
            f"({result.working_storage.evidence.label})",
            f"- Alignment: {result.working_storage.alignment_effective_concurrency} of "
            f"{result.working_storage.alignment_configured_concurrency} configured workers active -> "
            f"{result.working_storage.alignment_peak_gib} GiB peak",
            f"- DeepVariant: {result.working_storage.deepvariant_effective_concurrency} of "
            f"{result.working_storage.deepvariant_configured_concurrency} configured workers active -> "
            f"{result.working_storage.deepvariant_peak_gib} GiB peak",
            f"- Peak simultaneous scratch: {result.working_storage.peak_simultaneous_gib} GiB "
            "(max of the two stage peaks, not their sum)",
            "- Working storage is temporary compute capacity and is not included in the durable "
            "Storage estimate.",
            "",
            "## Execution environment",
            "",
            f"- Ilifu/HPC: {result.hpc.status}; monetary cost {result.hpc.monetary_cost_status}; "
            f"working storage {result.hpc.working_storage_status}; scheduling "
            f"{result.hpc.scheduling_status}.",
            "",
            "### AWS execution architecture",
            "",
            f"- Region: {result.aws.region_name} (`{result.aws.region_code}`)",
            f"- Architecture: {' -> '.join(result.aws.architecture_steps)}",
            f"- AWS Batch orchestration fee: ${result.aws.batch_orchestration_fee_usd}",
            f"- Purchase model: {result.aws.purchase_model}",
            f"- Compute cost: {result.aws.pricing_status}",
            "",
            f"**Compute cost status:** {COMPUTE_COST_STATUS}",
            "",
            "## Sentieon (excluded from current workflow)",
            "",
            f"- US${result.sentieon.usd_per_genome}/genome x {num_samples} samples = "
            f"US${result.sentieon.total_usd:,.2f} (R{result.sentieon.total_zar:,.2f})",
            f"- Status: {result.sentieon.status}",
            "",
            "## Limitations",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in result.limitations)
    lines.append("")
    return "\n".join(lines) + "\n"
