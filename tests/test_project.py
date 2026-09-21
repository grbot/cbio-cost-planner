"""Tests for the shared project model (spec 010 §4) and the session-state
bootstrap that fixes direct navigation to a non-Storage page (spec 011a §2-§3)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
import streamlit as st

from cbio_cost.calculator import build_estimate
from cbio_cost.config import build_wgs_datasets, load_currency_defaults, load_pricing, load_profiles
from cbio_cost.project import PROJECT_SESSION_KEY, ProjectMetadata, build_project
from cbio_cost.project_state import ProjectState, record_storage, record_transfer
from cbio_cost.transfer_plan import build_transfer_plan_result
from cbio_cost.transfer_plan_models import Endpoint, TransferPlan
from views import storage

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


def test_build_project_wraps_inputs_datasets_and_estimate(profile, wgs_datasets, estimate):
    state = ProjectState()
    record_storage(state, {}, estimate)
    project = build_project(state)

    assert project.metadata == ProjectMetadata(
        name=profile.project.project_name,
        project_type=profile.project.project_type,
        num_samples=profile.project.num_samples,
        retention_years=profile.project.retention_years,
    )
    assert project.datasets == wgs_datasets
    assert project.storage_estimate is estimate


def test_build_project_does_not_alter_calculated_figures(profile, wgs_datasets, estimate):
    """Projecting a CostEstimate into a Project must not recompute or change
    any figure — it is a pure structural bridge only (spec 010 §4, spec 013
    §2, §8)."""
    state = ProjectState()
    record_storage(state, {}, estimate)
    project = build_project(state)

    assert project.storage_estimate.volume.raw_total_gb == estimate.volume.raw_total_gb
    assert project.storage_estimate.grand_total_zar == estimate.grand_total_zar
    assert project.storage_estimate.line_items == estimate.line_items


def test_project_metadata_custom_project_has_no_sample_count():
    metadata = ProjectMetadata(
        name="Custom", project_type="Custom Project", num_samples=None, retention_years=Decimal(2)
    )
    assert metadata.num_samples is None


def test_build_project_attaches_transfer_config_and_result_without_touching_storage(
    profile, wgs_datasets, estimate, pricing
):
    """spec 012, spec 013 §2: build_project() attaches Transfer config/result
    from canonical ProjectState without recomputing or disturbing Storage or
    Compute state."""
    state = ProjectState()
    record_storage(state, {}, estimate)
    project = build_project(state)

    plan = TransferPlan(
        dataset_name="FASTQ",
        size_gb=Decimal(1024),
        source=Endpoint(type="institutional", label="Institutional / local storage"),
        destination=Endpoint(type="aws_s3", label="AWS S3"),
        throughput_mode="unknown",
        transfer_method="Not yet selected",
    )
    result = build_transfer_plan_result(plan, pricing)
    record_transfer(state, plan, {}, result)

    updated = build_project(state)

    assert updated.transfer_config is plan
    assert updated.transfer_result is result
    assert updated.storage_estimate is project.storage_estimate
    assert updated.compute_result is None


# ---------------------------------------------------------------------------
# Session-state bootstrap (spec 011a §2, §3)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_session_state():
    st.session_state.clear()
    yield
    st.session_state.clear()


def test_minimum_valid_state_is_not_the_500_sample_example():
    state = storage._minimum_valid_state()
    assert state["num_samples"] == 1
    assert state["retention_years"] == 1.0
    assert state["project_name"] == ""


def test_default_state_used_by_demo_profile_button_is_unchanged():
    """The explicit "Load 500 x 30x WGS / 5-year demo profile" button still
    loads the full example — only the app's initial state changed."""
    state = storage._default_state()
    assert state["num_samples"] == 500
    assert state["retention_years"] == 5.0
    assert state["project_name"] == "Example WGS Project"


def test_ensure_project_state_populates_minimum_valid_project_without_any_widget():
    """Simulates app.py's bootstrap call before st.navigation dispatches to a
    page — proving a fresh session opened directly at /compute (or any
    non-Storage page) sees a coherent WGS 30x project instead of the
    "WGS 30x project required" contradiction the bug produced."""
    storage.ensure_project_state()

    project = st.session_state[PROJECT_SESSION_KEY]
    assert project.metadata.project_type == "WGS 30x"
    assert project.metadata.num_samples == 1
    assert project.storage_estimate is not None


def test_ensure_project_state_is_idempotent():
    storage.ensure_project_state()
    first = st.session_state[PROJECT_SESSION_KEY]

    storage.ensure_project_state()

    assert st.session_state[PROJECT_SESSION_KEY] is first
