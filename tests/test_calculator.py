"""Unit tests for the cost-calculation engine (spec §20)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from cbio_cost.calculator import build_estimate
from cbio_cost.config import load_currency_defaults, load_pricing, load_profiles
from cbio_cost.export import to_csv, to_json, to_markdown
from cbio_cost.models import (
    EngineeringAssumptions,
    MovementAssumptions,
    ProjectInputs,
    StorageAssumptions,
)
from cbio_cost.operations import build_operations_cost_result
from cbio_cost.storage import archive_storage_cost, calculate_data_volume, tiered_cost
from cbio_cost.transfer import apply_contingency, cram_egress, fastq_egress, gvcf_egress, tiered_egress_cost

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


@pytest.fixture
def pricing():
    return load_pricing(CONFIG_DIR / "aws-pricing.yaml")


@pytest.fixture
def profile():
    profile, _scenarios = load_profiles(CONFIG_DIR / "project-profiles.yaml")
    return profile


# 1. Storage volume for 500 x 30x WGS -------------------------------------------------


def test_data_volume_500x30x_wgs(profile):
    volume = calculate_data_volume(profile.project, profile.volumes, profile.storage)

    assert volume.per_file_type_gb["FASTQ"] == Decimal(500 * 100)
    assert volume.per_file_type_gb["CRAM"] == Decimal(500 * 40)
    assert volume.per_file_type_gb["gVCF"] == Decimal(500 * 10)
    assert volume.raw_total_gb == Decimal(75000)
    assert volume.envelope_gb == Decimal(90000)  # 75,000 * 1.20


# 2. FASTQ egress calculation ----------------------------------------------------------


def test_fastq_egress_calculation():
    assert fastq_egress(Decimal(50000), Decimal(1)) == Decimal(50000)
    assert fastq_egress(Decimal(50000), Decimal(2)) == Decimal(100000)


# 3. CRAM partial-retrieval calculation --------------------------------------------------


def test_cram_partial_retrieval_calculation():
    result = cram_egress(Decimal(20000), Decimal("0.10"), Decimal(1))
    assert result == Decimal(2000)


# 4. gVCF multiple-pass calculation ------------------------------------------------------


def test_gvcf_multiple_pass_calculation():
    result = gvcf_egress(Decimal(5000), Decimal(2))
    assert result == Decimal(10000)


# 5. Transfer contingency ----------------------------------------------------------------


def test_transfer_contingency():
    base = Decimal(62000)
    result = apply_contingency(base, Decimal("0.20"))
    assert result == Decimal("74400.0")


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


# 8. Archive cost over multiple years --------------------------------------------------------


def test_archive_cost_over_multiple_years(profile, pricing):
    volume = calculate_data_volume(profile.project, profile.volumes, profile.storage)
    results, monthly, annual, total = archive_storage_cost(
        profile.project, profile.volumes, volume.per_file_type_gb, profile.storage, pricing
    )
    # retention 5 years = 60 months, active period 1 month -> 59 months archived
    months_in_archive = Decimal(5 * 12) - profile.storage.active_months
    assert all(r.months_in_archive == months_in_archive for r in results)
    assert annual == monthly * Decimal(12)
    assert total == monthly * months_in_archive


# 9. Engineering support cost -----------------------------------------------------------------


def test_engineering_support_cost():
    inputs = ProjectInputs(
        project_name="Test",
        project_type="WGS 30x",
        num_samples=10,
        depth_label="30x",
        retention_years=Decimal(3),
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


# 10. Zero-sample and invalid-input handling ----------------------------------------------------


def test_zero_samples_raises():
    with pytest.raises(ValueError):
        ProjectInputs(
            project_name="Test",
            project_type="WGS 30x",
            num_samples=0,
            depth_label="30x",
            retention_years=Decimal(5),
        )


def test_negative_samples_raises():
    with pytest.raises(ValueError):
        ProjectInputs(
            project_name="Test",
            project_type="WGS 30x",
            num_samples=-5,
            depth_label="30x",
            retention_years=Decimal(5),
        )


def test_negative_retention_raises():
    with pytest.raises(ValueError):
        ProjectInputs(
            project_name="Test",
            project_type="WGS 30x",
            num_samples=10,
            depth_label="30x",
            retention_years=Decimal(-1),
        )


def test_negative_headroom_raises():
    with pytest.raises(ValueError):
        StorageAssumptions(headroom_fraction=Decimal("-0.1"), active_months=Decimal(1))


def test_cram_retrieval_fraction_out_of_range_raises():
    with pytest.raises(ValueError):
        MovementAssumptions(
            fastq_passes=Decimal(1),
            cram_retrieval_fraction=Decimal("1.5"),
            cram_retrieval_passes=Decimal(1),
            gvcf_passes=Decimal(2),
            transfer_contingency=Decimal("0.2"),
        )


# Pricing provenance metadata (spec 005) ---------------------------------------------------


def test_pricing_config_provenance_metadata(pricing):
    assert pricing.provider == "AWS"
    assert pricing.region_name
    assert pricing.pricing_source.startswith("https://")
    assert pricing.pricing_last_verified


@pytest.fixture
def estimate(profile, pricing):
    currency = load_currency_defaults(CONFIG_DIR / "aws-pricing.yaml")
    return build_estimate(
        profile.project, profile.volumes, profile.storage, profile.movement, profile.engineering, pricing, currency
    )


def test_csv_export_includes_pricing_provenance(estimate, pricing):
    csv_text = to_csv(estimate, pricing)
    assert pricing.pricing_source in csv_text
    assert pricing.pricing_last_verified in csv_text


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
