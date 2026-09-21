"""Unit tests for the Transfer calculation engine (spec 012 §34).

Deterministic, no Streamlit dependency — mirrors tests/test_compute.py's
style. Pins the worked examples from spec 012 §11-§12, §21, deriving values
from the formulas rather than hard-coding spec text (spec 012 §12 explicit
instruction).

Note on the spec's §12 worked example: 1 TB (1024 GB) at 1000 Mbps gives
≈2.44 h via the §11 formula — matches the spec text exactly. The same
formula applied to 700 Mbps (1000 Mbps × 70% efficiency) gives ≈3.49 h, not
the "≈3.41 h" the spec text states — duration scales as 1/throughput, so
2.44h × (1000/700) ≈ 3.49h. This looks like an arithmetic slip in the
spec's illustrative text, not in the mandated formula. Per §12's own
instruction to derive rather than hard-code, the test below asserts against
the formula's own output, not either figure from the spec text.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from cbio_cost.calculator import build_estimate
from cbio_cost.config import build_wgs_datasets, load_currency_defaults, load_pricing, load_profiles
from cbio_cost.project import Project
from cbio_cost.transfer_plan import (
    bandwidth_delay_product_bytes,
    dataset_presets,
    provider_cost,
    transfer_duration_seconds,
    unknown_throughput_scenarios,
)
from cbio_cost.transfer_plan_models import Endpoint, TransferPlan
from cbio_cost.units import gb_to_tb, tb_to_gb

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


@pytest.fixture
def pricing():
    return load_pricing(CONFIG_DIR / "aws-pricing.yaml")


# 1. Unit conversion (spec 012 §34) ------------------------------------------


def test_tb_to_gb_matches_project_convention():
    assert tb_to_gb(Decimal(1)) == Decimal(1024)


# 2. Transfer duration (spec 012 §11-§12, §34) -------------------------------


def test_transfer_duration_1tb_at_1gbps():
    seconds = transfer_duration_seconds(tb_to_gb(Decimal(1)), Decimal(1000))
    hours = seconds / Decimal(3600)
    assert hours == pytest.approx(Decimal("2.44"), abs=Decimal("0.01"))


def test_transfer_duration_at_planning_efficiency_matches_formula_not_spec_text():
    """See module docstring — the spec text's "3.41 hours" example doesn't
    match its own formula; this asserts against the formula's derivation."""
    throughput_mbps = Decimal(1000) * Decimal("0.7")
    seconds = transfer_duration_seconds(tb_to_gb(Decimal(1)), throughput_mbps)
    hours = seconds / Decimal(3600)

    baseline_seconds = transfer_duration_seconds(tb_to_gb(Decimal(1)), Decimal(1000))
    baseline_hours = baseline_seconds / Decimal(3600)
    expected_hours = baseline_hours * (Decimal(1000) / throughput_mbps)

    # Decimal division at fixed context precision isn't perfectly associative,
    # so compare with a tight tolerance rather than exact equality.
    assert hours == pytest.approx(expected_hours, abs=Decimal("0.0000001"))
    assert hours == pytest.approx(Decimal("3.49"), abs=Decimal("0.01"))


# 3. Planning efficiency (spec 012 §9, §34) ----------------------------------


def test_planning_efficiency_arithmetic():
    assert Decimal(1000) * Decimal("0.7") == Decimal(700)


# 4. WGS preset (spec 012 §6, §34) -------------------------------------------


def test_wgs_fastq_preset_matches_500_sample_regression(pricing):
    profile, _scenarios = load_profiles(CONFIG_DIR / "project-profiles.yaml")
    datasets = build_wgs_datasets(
        profile.project.num_samples, profile.volumes, profile.movement, profile.active_months
    )
    currency = load_currency_defaults(CONFIG_DIR / "aws-pricing.yaml")
    estimate = build_estimate(profile.project, datasets, profile.engineering, pricing, currency)
    project = Project.from_storage(profile.project, datasets, estimate)

    presets = dataset_presets(project)

    assert presets["FASTQ"] == Decimal(50000)
    assert gb_to_tb(presets["FASTQ"]) == pytest.approx(Decimal("48.828125"), abs=Decimal("0.000001"))
    assert presets["All durable project data"] == Decimal(75000)


# 5. Direction distinctness (spec 012 §8, §19, §34) --------------------------


def test_aws_direction_distinctness(pricing):
    aws = Endpoint(type="aws_s3", label="AWS S3")
    institutional = Endpoint(type="institutional", label="Institutional / local storage")

    egress = provider_cost(aws, institutional, Decimal(50000), pricing)
    ingress = provider_cost(institutional, aws, Decimal(50000), pricing)

    assert egress.status == "calculated"
    assert ingress.status == "calculated"
    assert ingress.cost_usd == Decimal(0)
    assert egress.cost_usd > Decimal(0)
    assert egress.cost_usd != ingress.cost_usd


# 6. Unknown-throughput scenarios (spec 012 §9, §28, §34) --------------------


def test_unknown_throughput_scenarios_decrease_monotonically():
    scenarios = unknown_throughput_scenarios(Decimal(1024))
    durations = [s.duration_hours for s in scenarios]
    assert durations == sorted(durations, reverse=True)
    assert len(set(durations)) == len(durations)


# 7. RTT / BDP (spec 012 §21, §34) -------------------------------------------


def test_bandwidth_delay_product_10gbps_180ms():
    bdp_bytes = bandwidth_delay_product_bytes(Decimal(10000), Decimal(180))
    assert bdp_bytes == Decimal(225000000)


# 8. Missing provider cost (spec 012 §18, §34) -------------------------------


def test_provider_cost_not_calculated_for_non_aws_pair(pricing):
    institutional = Endpoint(type="institutional", label="Institutional / local storage")
    ilifu = Endpoint(type="ilifu", label="Ilifu / HPC")

    result = provider_cost(institutional, ilifu, Decimal(1000), pricing)

    assert result.status == "not_calculated"
    assert result.cost_usd is None


# 9. Validation (spec 012 §35) -----------------------------------------------


def _base_plan_kwargs():
    return dict(
        dataset_name="FASTQ",
        size_gb=Decimal(1024),
        source=Endpoint(type="institutional", label="Institutional / local storage"),
        destination=Endpoint(type="aws_s3", label="AWS S3"),
        throughput_mode="unknown",
        transfer_method="Not yet selected",
    )


def test_validation_rejects_non_positive_size():
    kwargs = _base_plan_kwargs()
    kwargs["size_gb"] = Decimal(0)
    with pytest.raises(ValueError):
        TransferPlan(**kwargs)


def test_validation_rejects_zero_measured_throughput():
    kwargs = _base_plan_kwargs()
    kwargs["throughput_mode"] = "measured"
    kwargs["measured_mbps"] = Decimal(0)
    with pytest.raises(ValueError):
        TransferPlan(**kwargs)


def test_validation_rejects_efficiency_outside_range():
    kwargs = _base_plan_kwargs()
    kwargs["throughput_mode"] = "known_capacity"
    kwargs["link_capacity_mbps"] = Decimal(1000)
    kwargs["efficiency_percent"] = Decimal(150)
    with pytest.raises(ValueError):
        TransferPlan(**kwargs)


def test_validation_rejects_negative_rtt():
    kwargs = _base_plan_kwargs()
    kwargs["rtt_ms"] = Decimal(-1)
    with pytest.raises(ValueError):
        TransferPlan(**kwargs)


def test_validation_rejects_blank_custom_endpoint_name():
    with pytest.raises(ValueError):
        Endpoint(type="custom", label="   ")
