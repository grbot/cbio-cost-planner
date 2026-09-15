"""Unit tests for the cost-calculation engine (spec §20; spec 006 §25).

Both WGS 30x and Custom Project reduce to a ``list[Dataset]`` before
reaching the calculation engine, so most tests here exercise the generic
dataset-based API directly. The WGS regression test pins the exact
durable-volume and workflow-egress figures given in spec 006 §9 — the
numbers a real CBIO WGS 500x30x project would recognise — while cost
totals are checked for internal consistency (they are now computed by
tiering each dataset's storage independently and summing, per spec 006
§17, rather than tiering one combined envelope as the pre-006 engine did).
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from cbio_cost.calculator import build_estimate, build_scenarios
from cbio_cost.config import build_wgs_datasets, load_currency_defaults, load_pricing, load_profiles
from cbio_cost.export import to_csv, to_json, to_markdown
from cbio_cost.models import (
    Dataset,
    EngineeringAssumptions,
    ProjectInputs,
    ScenarioAssumptions,
)
from cbio_cost.operations import build_operations_cost_result
from cbio_cost.storage import build_storage_cost_result, calculate_data_volume, tiered_cost
from cbio_cost.transfer import apply_contingency, build_transfer_result, dataset_base_egress_gb, tiered_egress_cost

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


@pytest.fixture
def pricing():
    return load_pricing(CONFIG_DIR / "aws-pricing.yaml")


@pytest.fixture
def profile():
    profile, _scenarios = load_profiles(CONFIG_DIR / "project-profiles.yaml")
    return profile


@pytest.fixture
def wgs_datasets(profile):
    return build_wgs_datasets(
        profile.project.num_samples, profile.volumes, profile.movement, profile.active_months
    )


# 1. Single dataset egress (spec 006 §25) ------------------------------------------------


def test_single_dataset_base_and_planned_egress():
    dataset = Dataset(
        name="Raw data",
        size_gb=Decimal(10) * 1024,
        retrieval_fraction=Decimal(1),
        read_passes=Decimal(1),
        active_months=Decimal(1),
        archive_class="glacier_flexible",
    )
    base = dataset_base_egress_gb(dataset)
    assert base == Decimal(10 * 1024)
    planned = apply_contingency(base, Decimal("0.20"))
    assert planned == Decimal(12 * 1024)


# 2. Partial retrieval (spec 006 §25) -----------------------------------------------------


def test_partial_retrieval_base_egress():
    dataset = Dataset(
        name="Alignment data",
        size_gb=Decimal(20) * 1024,
        retrieval_fraction=Decimal("0.10"),
        read_passes=Decimal(1),
        active_months=Decimal(1),
        archive_class="glacier_flexible",
    )
    assert dataset_base_egress_gb(dataset) == Decimal(2 * 1024)


# 3. Multiple passes (spec 006 §25) -------------------------------------------------------


def test_multiple_passes_base_egress():
    dataset = Dataset(
        name="Variant calls",
        size_gb=Decimal(5) * 1024,
        retrieval_fraction=Decimal(1),
        read_passes=Decimal(2),
        active_months=Decimal(1),
        archive_class="glacier_flexible",
    )
    assert dataset_base_egress_gb(dataset) == Decimal(10 * 1024)


# 4. Multiple datasets sum correctly (spec 006 §25) ---------------------------------------


def test_multiple_datasets_sum(pricing):
    datasets = [
        Dataset("A", Decimal(50000), Decimal(1), Decimal(1), Decimal(1), "glacier_flexible"),
        Dataset("B", Decimal(20000), Decimal("0.10"), Decimal(1), Decimal(1), "glacier_flexible"),
        Dataset("C", Decimal(5000), Decimal(1), Decimal(2), Decimal(1), "glacier_flexible"),
    ]
    volume = calculate_data_volume(datasets, Decimal(0))
    assert volume.raw_total_gb == Decimal(75000)

    transfer = build_transfer_result(datasets, Decimal("0.20"), pricing)
    assert transfer.base_egress_gb == Decimal(62000)
    assert transfer.planned_egress_gb == Decimal("74400.0")

    storage = build_storage_cost_result(datasets, volume.raw_total_gb, transfer.planned_egress_gb, Decimal(0), Decimal(5), pricing)
    assert storage.active_storage_cost_usd == sum((d.active_storage_cost_usd for d in storage.datasets), Decimal(0))
    assert storage.archive_total_cost_usd == sum((d.archive_total_cost_usd for d in storage.datasets), Decimal(0))


# 5. WGS regression: durable volume + workflow egress (spec 006 §9) -----------------------


def test_wgs_500x30x_durable_volume_and_egress(wgs_datasets, pricing):
    by_name = {d.name: d for d in wgs_datasets}
    assert by_name["FASTQ"].size_gb == Decimal(500 * 100)
    assert by_name["CRAM"].size_gb == Decimal(500 * 40)
    assert by_name["gVCF"].size_gb == Decimal(500 * 10)

    volume = calculate_data_volume(wgs_datasets, Decimal("0.20"))
    assert volume.raw_total_gb == Decimal(75000)
    assert volume.envelope_gb == Decimal(90000)  # 75,000 x 1.20

    transfer = build_transfer_result(wgs_datasets, Decimal("0.20"), pricing)
    egress_by_name = {d.name: d.base_egress_gb for d in transfer.datasets}
    assert egress_by_name["FASTQ"] == Decimal(50000)
    assert egress_by_name["CRAM"] == Decimal(2000)
    assert egress_by_name["gVCF"] == Decimal(10000)
    assert transfer.base_egress_gb == Decimal(62000)
    assert transfer.planned_egress_gb == Decimal("74400.0")
    planned_egress_tb = transfer.planned_egress_gb / Decimal(1024)
    assert round(planned_egress_tb, 2) == Decimal("72.66")


def test_wgs_storage_cost_sums_per_dataset_results(wgs_datasets, pricing):
    """Spec 006 §17: storage is costed independently per dataset then summed —
    this is a deliberate change from the pre-006 engine, which tiered one
    combined S3 Standard envelope across all file types. Dollar totals may
    therefore differ slightly from before; internal consistency is what's
    pinned here."""
    volume = calculate_data_volume(wgs_datasets, Decimal("0.20"))
    transfer = build_transfer_result(wgs_datasets, Decimal("0.20"), pricing)
    storage = build_storage_cost_result(
        wgs_datasets, volume.raw_total_gb, transfer.planned_egress_gb, Decimal("0.20"), Decimal(5), pricing
    )
    assert len(storage.datasets) == 3
    assert storage.active_storage_cost_usd == sum((d.active_storage_cost_usd for d in storage.datasets), Decimal(0))
    assert storage.archive_total_cost_usd == sum((d.archive_total_cost_usd for d in storage.datasets), Decimal(0))
    # retention 5 years = 60 months, active period 1 month -> 59 months archived
    for d in storage.datasets:
        assert d.months_in_archive == Decimal(60 - 1)


# 6. Tiered S3 Standard pricing -----------------------------------------------------------


def test_tiered_s3_standard_pricing_crosses_boundary(pricing):
    s3_standard = pricing.storage_classes["s3_standard"]
    quantity = Decimal(60000)  # crosses the 51,200 GB tier boundary
    cost = tiered_cost(quantity, s3_standard.tiers)
    expected = Decimal(51200) * Decimal("0.0274") + Decimal(8800) * Decimal("0.0262")
    assert cost == expected


# 7. Tiered internet egress pricing --------------------------------------------------------


def test_tiered_internet_egress_pricing_crosses_boundary(pricing):
    quantity = Decimal(10440)  # crosses the 10,240 GB tier boundary after free allowance
    cost = tiered_egress_cost(quantity, pricing)
    billable = quantity - pricing.egress.free_allowance_gb_per_month  # 100 GB free
    tier1_cap = pricing.egress.tiers[0].up_to_gb
    expected = tier1_cap * Decimal("0.1540") + (billable - tier1_cap) * Decimal("0.1350")
    assert cost == expected


def test_tiered_internet_egress_pricing_within_free_allowance(pricing):
    assert tiered_egress_cost(Decimal(50), pricing) == Decimal(0)


# 8. S3-Standard-only dataset: no archive transition (spec 006 §14) -----------------------


def test_s3_standard_only_dataset_has_no_archive_cost(pricing):
    dataset = Dataset(
        name="Live index",
        size_gb=Decimal(1000),
        retrieval_fraction=Decimal(1),
        read_passes=Decimal(1),
        active_months=Decimal(1),
        archive_class="s3_standard",
    )
    storage = build_storage_cost_result([dataset], Decimal(1000), Decimal(1000), Decimal(0), Decimal(5), pricing)
    result = storage.datasets[0]
    assert result.months_in_archive == Decimal(0)
    assert result.archive_total_cost_usd == Decimal(0)
    assert result.active_storage_cost_usd > Decimal(0)
    # Priced over the full 5-year retention (60 months), not just active_months.
    s3_monthly = tiered_cost(Decimal(1000), pricing.storage_classes["s3_standard"].tiers)
    assert result.active_storage_cost_usd == s3_monthly * Decimal(60)


# 9. Engineering support cost -----------------------------------------------------------------


def test_engineering_support_cost():
    inputs = ProjectInputs(
        project_name="Test",
        project_type="Custom Project",
        retention_years=Decimal(3),
        transfer_contingency=Decimal("0.2"),
    )
    engineering = EngineeringAssumptions(
        onboarding_hours=Decimal(8),
        operations_hours_per_year=Decimal(12),
        closeout_hours=Decimal(4),
        hourly_rate_zar=Decimal(1000),
    )
    result = build_operations_cost_result(inputs, engineering)

    assert result.onboarding_cost_zar == Decimal(8000)
    assert result.operations_cost_zar == Decimal(12 * 3 * 1000)
    assert result.closeout_cost_zar == Decimal(4000)
    assert result.total_zar == Decimal(8000 + 36000 + 4000)


# 10. Validation (spec 006 §23) ------------------------------------------------------------


def test_blank_dataset_name_raises():
    with pytest.raises(ValueError):
        Dataset("  ", Decimal(1000), Decimal(1), Decimal(1), Decimal(1), "glacier_flexible")


def test_zero_dataset_size_raises():
    with pytest.raises(ValueError):
        Dataset("Data", Decimal(0), Decimal(1), Decimal(1), Decimal(1), "glacier_flexible")


def test_negative_dataset_size_raises():
    with pytest.raises(ValueError):
        Dataset("Data", Decimal(-1), Decimal(1), Decimal(1), Decimal(1), "glacier_flexible")


def test_retrieval_fraction_out_of_range_raises():
    with pytest.raises(ValueError):
        Dataset("Data", Decimal(1000), Decimal("1.5"), Decimal(1), Decimal(1), "glacier_flexible")


def test_negative_read_passes_raises():
    with pytest.raises(ValueError):
        Dataset("Data", Decimal(1000), Decimal(1), Decimal(-1), Decimal(1), "glacier_flexible")


def test_zero_read_passes_allowed():
    dataset = Dataset("Data", Decimal(1000), Decimal(1), Decimal(0), Decimal(1), "glacier_flexible")
    assert dataset_base_egress_gb(dataset) == Decimal(0)


def test_empty_dataset_list_raises(pricing):
    engineering = EngineeringAssumptions(Decimal(0), Decimal(0), Decimal(0), Decimal(1000))
    currency = load_currency_defaults(CONFIG_DIR / "aws-pricing.yaml")
    inputs = ProjectInputs(
        project_name="Empty",
        project_type="Custom Project",
        retention_years=Decimal(1),
        transfer_contingency=Decimal(0),
    )
    with pytest.raises(ValueError):
        build_estimate(inputs, [], engineering, pricing, currency)


def test_negative_retention_raises():
    with pytest.raises(ValueError):
        ProjectInputs(
            project_name="Test",
            project_type="Custom Project",
            retention_years=Decimal(-1),
            transfer_contingency=Decimal(0),
        )


def test_negative_headroom_raises():
    with pytest.raises(ValueError):
        ProjectInputs(
            project_name="Test",
            project_type="Custom Project",
            retention_years=Decimal(1),
            transfer_contingency=Decimal(0),
            headroom_fraction=Decimal("-0.1"),
        )


# Pricing provenance metadata (spec 005) ---------------------------------------------------


def test_pricing_config_provenance_metadata(pricing):
    assert pricing.provider == "AWS"
    assert pricing.region_name
    assert pricing.pricing_source.startswith("https://")
    assert pricing.pricing_last_verified


@pytest.fixture
def estimate(profile, wgs_datasets, pricing):
    currency = load_currency_defaults(CONFIG_DIR / "aws-pricing.yaml")
    return build_estimate(profile.project, wgs_datasets, profile.engineering, pricing, currency)


def test_csv_export_includes_pricing_provenance(estimate, pricing):
    csv_text = to_csv(estimate, pricing)
    assert pricing.pricing_source in csv_text
    assert pricing.pricing_last_verified in csv_text
    assert "FASTQ" in csv_text


def test_json_export_includes_pricing_provenance(estimate, pricing):
    json_text = to_json(estimate, pricing)
    assert '"pricing_source"' in json_text
    assert pricing.pricing_source in json_text
    assert pricing.pricing_last_verified in json_text


def test_markdown_export_includes_pricing_provenance(estimate, pricing):
    md_text = to_markdown(estimate, pricing)
    assert "Pricing & assumptions" in md_text
    assert pricing.pricing_source in md_text
    assert pricing.pricing_last_verified in md_text
    assert "Project mode: WGS 30x" in md_text


def test_config_loaders_are_not_cache_resource():
    """Regression guard for the deployed AttributeError on pricing.pricing_source.

    st.cache_resource keys its cache on the wrapper function's own source, not
    on cbio_cost/config.py or the YAML it reads. That let a lightweight
    Streamlit Cloud redeploy (code sync + rerun, no full process restart)
    keep serving a PricingConfig built before pricing_source/region_name/
    pricing_last_verified existed. app.py's config loaders must stay
    uncached so every rerun reflects the current config on disk.
    """
    app_source = (CONFIG_DIR.parent / "app.py").read_text()
    for func_name in ("_load_pricing", "_load_profile_and_scenarios"):
        def_index = app_source.index(f"def {func_name}(")
        preceding_lines = app_source[:def_index].strip().splitlines()
        assert "cache_resource" not in preceding_lines[-1], (
            f"{func_name} must not be decorated with st.cache_resource"
        )


# 11. Scenarios / sensitivity analysis (spec 006 §19) --------------------------------------


def test_build_scenarios_generic_over_arbitrary_datasets(pricing):
    """Custom Project datasets (no FASTQ/CRAM/gVCF) must work through the
    same scenario machinery as WGS."""
    engineering = EngineeringAssumptions(Decimal(8), Decimal(12), Decimal(4), Decimal(1000))
    currency = load_currency_defaults(CONFIG_DIR / "aws-pricing.yaml")
    inputs = ProjectInputs(
        project_name="Custom",
        project_type="Custom Project",
        retention_years=Decimal(2),
        transfer_contingency=Decimal("0.20"),
    )
    baseline = [
        Dataset("Imaging data", Decimal(10000), Decimal("0.5"), Decimal(1), Decimal(1), "glacier_flexible"),
    ]
    scenarios = {
        "Low movement": ScenarioAssumptions(
            datasets=[Dataset("Imaging data", Decimal(10000), Decimal("0.5"), Decimal("0.5"), Decimal(1), "glacier_flexible")],
            transfer_contingency=Decimal("0.10"),
        ),
        "Expected": ScenarioAssumptions(datasets=baseline, transfer_contingency=Decimal("0.20")),
        "High movement": ScenarioAssumptions(
            datasets=[Dataset("Imaging data", Decimal(10000), Decimal("0.5"), Decimal(2), Decimal(1), "glacier_flexible")],
            transfer_contingency=Decimal("0.40"),
        ),
    }
    estimates = build_scenarios(inputs, engineering, pricing, currency, scenarios)
    assert set(estimates.keys()) == {"Low movement", "Expected", "High movement"}
    assert (
        estimates["Low movement"].transfer.planned_egress_gb
        < estimates["Expected"].transfer.planned_egress_gb
        < estimates["High movement"].transfer.planned_egress_gb
    )
