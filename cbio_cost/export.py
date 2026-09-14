"""Serialize a CostEstimate to CSV, JSON, and Markdown (spec §18)."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict
from decimal import Decimal
from typing import Any

from cbio_cost.models import CostEstimate
from cbio_cost.units import gb_to_tb


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Object of type {type(value)} is not JSON serializable")


def to_csv(estimate: CostEstimate) -> str:
    """Render the cost-component breakdown as CSV text."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Project", estimate.inputs.project_name])
    writer.writerow(["Project type", estimate.inputs.project_type])
    writer.writerow(["Samples", estimate.inputs.num_samples])
    writer.writerow(["Retention (years)", estimate.inputs.retention_years])
    writer.writerow([])
    writer.writerow(["Cost component", "Amount (ZAR)", "Note"])
    for item in estimate.line_items:
        writer.writerow([item.label, str(item.amount_zar), item.note])
    writer.writerow(["Compute", "Not included", ""])
    return buffer.getvalue()


def to_json(estimate: CostEstimate) -> str:
    """Render the full estimate (including per-file-type detail) as JSON text."""
    payload = {
        "project": asdict(estimate.inputs),
        "volume": {
            "per_file_type_gb": {k: str(v) for k, v in estimate.volume.per_file_type_gb.items()},
            "raw_total_gb": str(estimate.volume.raw_total_gb),
            "envelope_gb": str(estimate.volume.envelope_gb),
        },
        "transfer": {
            "per_file_type_egress_gb": {
                k: str(v) for k, v in estimate.transfer.per_file_type_egress_gb.items()
            },
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
    }
    return json.dumps(payload, indent=2, default=_json_default)


def to_markdown(estimate: CostEstimate) -> str:
    """Render a concise Markdown project-cost summary."""
    inputs = estimate.inputs
    raw_tb = gb_to_tb(estimate.volume.raw_total_gb)
    envelope_tb = gb_to_tb(estimate.volume.envelope_gb)
    egress_tb = gb_to_tb(estimate.transfer.planned_egress_gb)

    lines = [
        f"# {inputs.project_name} — Infrastructure Cost Estimate",
        "",
        f"- Project type: {inputs.project_type}",
        f"- Samples: {inputs.num_samples}",
        f"- Retention: {inputs.retention_years} years",
        f"- Durable data: {raw_tb:.1f} TB",
        f"- Provisioned envelope: {envelope_tb:.1f} TB",
        f"- Expected AWS egress: {egress_tb:.1f} TB",
        "",
        "| Cost component | Cost (ZAR) |",
        "|---|---:|",
    ]
    for item in estimate.line_items:
        lines.append(f"| {item.label} | R{item.amount_zar:,.2f} |")
    lines.append("| Compute | Not included |")
    lines.append("")
    if estimate.explanation:
        lines.append(estimate.explanation)
    return "\n".join(lines) + "\n"
