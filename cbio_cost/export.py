"""Serialize a CostEstimate to CSV, JSON, and Markdown (spec §18; spec 006 §21)."""

from __future__ import annotations

import csv
import io
import json
from decimal import Decimal
from typing import Any

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
        ["Compute", "Not included"],
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
    writer.writerow(["Compute", "Not included", ""])
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
        "compute": "Not included",
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
            "compute_note": "Not included",
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
    lines.append("| Compute | Not included |")
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
    lines.append("- Compute cost is not included.")
    lines.append(
        "- Infrastructure cost estimates do not constitute approval to store sensitive research "
        "data in AWS or other cloud/object storage. Project-specific consent, ethics, data-access "
        "and institutional requirements must be reviewed separately."
    )
    return "\n".join(lines) + "\n"
