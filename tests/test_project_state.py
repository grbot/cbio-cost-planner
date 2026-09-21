"""Unit tests for canonical project-state revision tracking (spec 012a).

Deterministic, no Streamlit runtime widget interaction — exercises
``cbio_cost.project_state`` directly against plain widget-value dicts.
"""

from __future__ import annotations

import pytest
import streamlit as st

from cbio_cost.project_state import (
    COMPLETE,
    INVALID,
    NEEDS_REVIEW,
    NOT_CONFIGURED,
    ProjectState,
    compute_status,
    mark_transfer_invalid,
    record_compute,
    record_storage,
    record_transfer,
    storage_status,
    sync_widget_defaults,
    transfer_status,
)


@pytest.fixture(autouse=True)
def _clear_session_state():
    st.session_state.clear()
    yield
    st.session_state.clear()


def _storage_widgets(**overrides) -> dict:
    base = {
        "project_mode": "WGS 30×",
        "project_name": "Test",
        "num_samples": 500,
        "retention_years": 5.0,
        "usd_zar": 16.05,
        "vat_percent": 15.0,
        "dataset_sizes_snapshot": (("FASTQ", 50000), ("CRAM", 20000), ("gVCF", 5000)),
        "dataset_lifecycle_snapshot": (("FASTQ", "glacier_flexible", 1.0, 1.0, 1.0),),
        "headroom_percent": 20.0,
        "active_months": 1.0,
        "transfer_contingency_percent": 20.0,
        "onboarding_hours": 8.0,
        "operations_hours_per_year": 12.0,
        "closeout_hours": 4.0,
        "hourly_rate_zar": 1000.0,
        "custom_datasets": None,
    }
    base.update(overrides)
    return base


# 1. Revision bumping is scoped to the right counter ------------------------


def test_num_samples_change_bumps_project_revision_only():
    state = ProjectState()
    record_storage(state, _storage_widgets(num_samples=500), result="estimate-1")
    record_storage(state, _storage_widgets(num_samples=1000), result="estimate-2")

    assert state.project_revision == 1
    assert state.storage_config_revision == 0


def test_compute_only_widget_change_bumps_compute_config_revision_only():
    state = ProjectState()
    record_storage(state, _storage_widgets(), result="estimate")
    record_compute(state, {"compute_alignment_concurrency": 10}, result="compute-1")
    record_compute(state, {"compute_alignment_concurrency": 20}, result="compute-2")

    assert state.compute_config_revision == 1
    assert state.project_revision == 0


def test_transfer_only_widget_change_bumps_transfer_config_revision_only():
    state = ProjectState()
    record_storage(state, _storage_widgets(), result="estimate")
    record_transfer(state, "plan-1", {"transfer_throughput_mode": "unknown"}, result="transfer-1")
    record_transfer(
        state, "plan-2", {"transfer_throughput_mode": "measured", "transfer_measured_mbps": 777.0}, result="transfer-2"
    )

    assert state.transfer_config_revision == 1
    assert state.project_revision == 0


def test_usd_zar_change_bumps_project_revision():
    state = ProjectState()
    record_storage(state, _storage_widgets(usd_zar=16.05), result="estimate-1")
    record_storage(state, _storage_widgets(usd_zar=17.00), result="estimate-2")

    assert state.project_revision == 1


def test_storage_only_setting_change_bumps_storage_config_revision_not_project():
    state = ProjectState()
    record_storage(state, _storage_widgets(headroom_percent=20.0), result="estimate-1")
    record_storage(state, _storage_widgets(headroom_percent=25.0), result="estimate-2")

    assert state.storage_config_revision == 1
    assert state.project_revision == 0


def test_rerecording_unchanged_values_does_not_bump_any_counter():
    state = ProjectState()
    widgets = _storage_widgets()
    record_storage(state, widgets, result="estimate-1")
    record_storage(state, dict(widgets), result="estimate-2")

    assert state.project_revision == 0
    assert state.storage_config_revision == 0


def test_first_ever_record_does_not_bump_revision():
    state = ProjectState()
    record_storage(state, _storage_widgets(), result="estimate")

    assert state.project_revision == 0
    assert state.storage_config_revision == 0
    assert state.storage_calculated_for == (0, 0)


# 2. Status transitions -------------------------------------------------------


def test_status_not_configured_before_any_record():
    state = ProjectState()
    assert storage_status(state) == NOT_CONFIGURED
    assert compute_status(state) == NOT_CONFIGURED
    assert transfer_status(state) == NOT_CONFIGURED


def test_status_complete_after_record():
    state = ProjectState()
    record_storage(state, _storage_widgets(), result="estimate")
    assert storage_status(state) == COMPLETE


def test_status_needs_review_after_upstream_change_without_rerecording():
    state = ProjectState()
    record_storage(state, _storage_widgets(num_samples=500), result="estimate-1")
    record_compute(state, {"compute_alignment_concurrency": 10}, result="compute-1")
    assert compute_status(state) == COMPLETE

    # Sample count changes (Storage re-recorded); Compute is not revisited.
    record_storage(state, _storage_widgets(num_samples=1000), result="estimate-2")
    assert compute_status(state) == NEEDS_REVIEW
    assert storage_status(state) == COMPLETE


def test_status_returns_to_complete_after_rerecording_stale_module():
    state = ProjectState()
    record_storage(state, _storage_widgets(num_samples=500), result="estimate-1")
    record_compute(state, {"compute_alignment_concurrency": 10}, result="compute-1")
    record_storage(state, _storage_widgets(num_samples=1000), result="estimate-2")
    assert compute_status(state) == NEEDS_REVIEW

    record_compute(state, {"compute_alignment_concurrency": 10}, result="compute-2")
    assert compute_status(state) == COMPLETE


# 3. sync_widget_defaults heals missing keys without touching edited ones ---


def test_sync_widget_defaults_heals_missing_key_only():
    st.session_state["existing_key"] = "user-edited-value"
    sync_widget_defaults({"existing_key": "canonical-value", "missing_key": "canonical-value-2"})

    assert st.session_state["existing_key"] == "user-edited-value"
    assert st.session_state["missing_key"] == "canonical-value-2"


# 4. project_configured explicit flag (spec 012c §14-17) ---------------------


def test_project_configured_starts_false():
    state = ProjectState()
    assert state.project_configured is False


def test_project_configured_stays_false_after_noop_rerecord():
    state = ProjectState()
    widgets = _storage_widgets()
    record_storage(state, widgets, result="estimate-1")
    record_storage(state, dict(widgets), result="estimate-2")

    assert state.project_configured is False


def test_project_configured_becomes_true_after_any_change_including_name_only():
    """project_name has no calculation effect and is tracked by neither
    revision counter, but changing it must still count as configuring the
    project (spec 012c §14-17)."""
    state = ProjectState()
    record_storage(state, _storage_widgets(project_name="Untitled"), result="estimate-1")
    assert state.project_configured is False

    record_storage(state, _storage_widgets(project_name="My real project"), result="estimate-2")
    assert state.project_configured is True
    # Sticky — a later no-op re-record must not flip it back.
    record_storage(state, _storage_widgets(project_name="My real project"), result="estimate-3")
    assert state.project_configured is True


def test_project_configured_becomes_true_after_500_sample_demo_profile_style_change():
    """Reproduces the exact spec 012c §14 bug: loading a full 500-sample
    profile changes project_revision but historically left
    storage_config_revision (the old, wrong "configured" signal) at 0
    forever, since headroom/archive/engineering values are identical
    between the minimum-valid and full-default states."""
    state = ProjectState()
    minimum = _storage_widgets(num_samples=1, retention_years=1.0, project_name="")
    record_storage(state, minimum, result="estimate-1")
    assert state.project_configured is False

    demo_profile = _storage_widgets(num_samples=500, retention_years=5.0, project_name="Example WGS Project")
    record_storage(state, demo_profile, result="estimate-2")

    assert state.project_configured is True
    assert state.storage_config_revision == 0  # the old (buggy) signal would still say "unconfigured"
    assert state.project_revision == 1


# 5. transfer_valid / INVALID status (spec 012c §11-13, §32) -----------------


def test_transfer_valid_starts_true():
    state = ProjectState()
    assert state.transfer_valid is True


def test_mark_transfer_invalid_does_not_touch_last_good_state():
    state = ProjectState()
    record_storage(state, _storage_widgets(), result="estimate")
    record_transfer(state, "good-plan", {"transfer_measured_mbps": 777.0}, result="good-result")

    mark_transfer_invalid(state)

    assert state.transfer_valid is False
    assert state.transfer_config == "good-plan"
    assert state.transfer_widgets == {"transfer_measured_mbps": 777.0}
    assert state.transfer_result == "good-result"


def test_transfer_status_invalid_overrides_complete():
    state = ProjectState()
    record_storage(state, _storage_widgets(), result="estimate")
    record_transfer(state, "plan", {"transfer_measured_mbps": 777.0}, result="result")
    assert transfer_status(state) == COMPLETE

    mark_transfer_invalid(state)
    assert transfer_status(state) == INVALID


def test_transfer_status_invalid_even_with_no_prior_result():
    state = ProjectState()
    mark_transfer_invalid(state)
    assert transfer_status(state) == INVALID


def test_transfer_status_returns_to_complete_after_successful_rerecord():
    state = ProjectState()
    record_storage(state, _storage_widgets(), result="estimate")
    record_transfer(state, "plan-1", {"transfer_measured_mbps": 777.0}, result="result-1")
    mark_transfer_invalid(state)
    assert transfer_status(state) == INVALID

    record_transfer(state, "plan-2", {"transfer_measured_mbps": 500.0}, result="result-2")
    assert transfer_status(state) == COMPLETE
