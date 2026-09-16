"""Tests for the shared project model (spec 010 §4)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from cbio_cost.calculator import build_estimate
from cbio_cost.config import build_wgs_datasets, load_currency_defaults, load_pricing, load_profiles
from cbio_cost.project import Project, ProjectMetadata

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


@pytest.fixture
def estimate(profile, wgs_datasets, pricing):
    currency = load_currency_defaults(CONFIG_DIR / "aws-pricing.yaml")
    return build_estimate(profile.project, wgs_datasets, profile.engineering, pricing, currency)


def test_project_from_storage_wraps_inputs_datasets_and_estimate(profile, wgs_datasets, estimate):
    project = Project.from_storage(profile.project, wgs_datasets, estimate)

    assert project.metadata == ProjectMetadata(
        name=profile.project.project_name,
        project_type=profile.project.project_type,
        num_samples=profile.project.num_samples,
        retention_years=profile.project.retention_years,
    )
    assert project.datasets == wgs_datasets
    assert project.storage_estimate is estimate


def test_project_from_storage_does_not_alter_calculated_figures(profile, wgs_datasets, estimate):
    """Wrapping a CostEstimate into a Project must not recompute or change any
    figure — it is a structural bridge only (spec 010 §4)."""
    project = Project.from_storage(profile.project, wgs_datasets, estimate)

    assert project.storage_estimate.volume.raw_total_gb == estimate.volume.raw_total_gb
    assert project.storage_estimate.grand_total_zar == estimate.grand_total_zar
    assert project.storage_estimate.line_items == estimate.line_items


def test_project_metadata_custom_project_has_no_sample_count():
    metadata = ProjectMetadata(
        name="Custom", project_type="Custom Project", num_samples=None, retention_years=Decimal(2)
    )
    assert metadata.num_samples is None
