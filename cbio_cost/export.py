"""Serialize a CostEstimate to CSV, JSON, and Markdown (spec §18)."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict
from decimal import Decimal
from typing import Any

from cbio_cost.models import CostEstimate, PricingConfig
from cbio_cost.units import gb_to_tb


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
    writer.writerow(["Project type", estimate.inputs.project_type])
    writer.writerow(["Samples", estimate.inputs.num_samples])
    writer.writerow(["Retention (years)", estimate.inputs.retention_years])
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
    return "\n".join(lines) + "\n"
