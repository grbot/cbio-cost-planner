"""End-to-end page-navigation and dependency-invalidation regression tests
(spec 012a §34-§39). Exercises the real Streamlit view render() functions in
sequence within one session — this is a faithful simulation of real
navigation, since Streamlit's session_state is one persistent object for the
whole browser session regardless of which page is currently displayed
(confirmed against the deployed app's own reported behaviour for the
defects this spec fixes).
"""

from __future__ import annotations

import json
from decimal import Decimal

import streamlit as st

from cbio_cost import export as cost_export
from cbio_cost.project import build_project
from cbio_cost.project_state import (
    COMPLETE,
    INVALID,
    NEEDS_REVIEW,
    NOT_CONFIGURED,
    compute_status,
    get_module_status,
    get_project_state,
    storage_status,
    transfer_status,
)
from cbio_cost.units import gb_to_tb
from views import compute, storage, summary, transfer

import project_setup

TRACKED_KEYS = [
    "num_samples",
    "project_name",
    "retention_years",
    "compute_alignment_concurrency",
    "compute_deepvariant_concurrency",
    "compute_scratch_gib_per_worker",
    "transfer_dataset_choice",
    "transfer_throughput_mode",
    "transfer_measured_mbps",
]


def _configure_reviewed_scenario() -> None:
    """spec 012a §35: 500 samples/5yr, 7/13 workers, 333 GiB scratch, FASTQ
    measured 777 Mbps — the exact deployed reviewed example."""
    storage.ensure_project_state()
    storage.load_demo_profile()
    project = storage._build_project_from_session_state()
    st.session_state["project"] = project
    storage.render()

    st.session_state.update(
        {
            "compute_alignment_concurrency": 7,
            "compute_deepvariant_concurrency": 13,
            "compute_scratch_gib_per_worker": 333.0,
        }
    )
    compute.render()

    st.session_state.update(
        {
            "transfer_dataset_choice": "FASTQ",
            "transfer_throughput_mode": "measured",
            "transfer_measured_mbps": 777.0,
        }
    )
    transfer.render()


# 1. Round-trip navigation persistence (spec 012a §34, §39) -----------------


def test_full_round_trip_navigation_preserves_all_configuration():
    st.session_state.clear()
    _configure_reviewed_scenario()
    summary.render()

    before = {k: st.session_state.get(k) for k in TRACKED_KEYS}

    for _ in range(2):
        storage.render()
        compute.render()
        transfer.render()
        summary.render()
        storage.render()
        transfer.render()
        compute.render()
        summary.render()

    after = {k: st.session_state.get(k) for k in TRACKED_KEYS}
    assert after == before


def test_round_trip_navigation_does_not_change_calculated_results():
    st.session_state.clear()
    _configure_reviewed_scenario()
    state = get_project_state()

    compute_hours_before = state.compute_result.known_modelled_elapsed_hours
    transfer_hours_before = state.transfer_result.duration_hours
    storage_total_before = state.storage_result.grand_total_zar

    for _ in range(2):
        storage.render()
        compute.render()
        transfer.render()
        summary.render()

    assert state.compute_result.known_modelled_elapsed_hours == compute_hours_before
    assert state.transfer_result.duration_hours == transfer_hours_before
    assert state.storage_result.grand_total_zar == storage_total_before
    assert storage_status(state) == COMPLETE
    assert compute_status(state) == COMPLETE
    assert transfer_status(state) == COMPLETE


# 2. Direct-page entry (spec 012a §38) ---------------------------------------


def test_direct_compute_entry_does_not_crash_or_show_contradictory_identity():
    st.session_state.clear()
    storage.ensure_project_state()  # app.py's own bootstrap, run unconditionally
    compute.render()  # user's first-ever page view this session

    project = st.session_state["project"]
    assert project.metadata.num_samples == 1  # minimum-valid default, not a mismatched identity


def test_direct_transfer_entry_does_not_crash():
    st.session_state.clear()
    storage.ensure_project_state()
    transfer.render()

    assert st.session_state["project"].transfer_result is not None


def test_direct_summary_entry_does_not_present_default_as_authoritative():
    st.session_state.clear()
    storage.ensure_project_state()
    summary.render()  # no exception is the primary assertion here


# 3. 500-sample end-to-end regression (spec 012a §35-§36) --------------------


def test_500_sample_reviewed_scenario_reproduces_exact_figures():
    st.session_state.clear()
    _configure_reviewed_scenario()
    state = get_project_state()

    s = state.storage_result
    c = state.compute_result
    t = state.transfer_result

    assert s.volume.raw_total_gb == 75000
    assert gb_to_tb(s.volume.raw_total_gb) == Decimal("73.2421875")
    assert gb_to_tb(s.volume.envelope_gb) == Decimal("87.890625")
    assert gb_to_tb(s.transfer.planned_egress_gb) == Decimal("72.65625")

    assert c.known_modelled_elapsed_hours == Decimal("419.0415333333333333333333333")
    assert c.working_storage.alignment_peak_gib == Decimal(2331)
    assert c.working_storage.deepvariant_peak_gib == Decimal(4329)
    assert c.working_storage.peak_simultaneous_gib == Decimal(4329)

    assert t.size_tb == Decimal("48.828125")
    assert round(t.duration_hours, 1) == Decimal("153.5")
    assert t.provider_cost.status == "calculated"
    assert t.provider_cost.cost_usd == Decimal(0)  # institutional -> AWS S3 default = ingress, not charged


def test_500_sample_reviewed_scenario_all_statuses_complete_when_freshly_configured():
    st.session_state.clear()
    _configure_reviewed_scenario()
    state = get_project_state()

    assert storage_status(state) == COMPLETE
    assert compute_status(state) == COMPLETE
    assert transfer_status(state) == COMPLETE


# 4. Dependency invalidation (spec 012a §37, §45) ----------------------------


def test_sample_count_change_invalidates_compute_and_transfer_not_storage():
    st.session_state.clear()
    _configure_reviewed_scenario()
    state = get_project_state()

    st.session_state["num_samples"] = 1000
    storage.render()  # only Storage revisited

    assert storage_status(state) == COMPLETE  # Storage always recalculates fresh on its own render
    assert compute_status(state) == NEEDS_REVIEW
    assert transfer_status(state) == NEEDS_REVIEW


def test_compute_concurrency_change_invalidates_only_compute():
    st.session_state.clear()
    _configure_reviewed_scenario()
    state = get_project_state()

    st.session_state["compute_alignment_concurrency"] = 20
    compute.render()

    assert storage_status(state) == COMPLETE
    assert compute_status(state) == COMPLETE  # Compute always recalculates fresh on its own render
    assert transfer_status(state) == COMPLETE


def test_transfer_throughput_change_invalidates_only_transfer():
    st.session_state.clear()
    _configure_reviewed_scenario()
    state = get_project_state()

    st.session_state["transfer_measured_mbps"] = 500.0
    transfer.render()

    assert storage_status(state) == COMPLETE
    assert compute_status(state) == COMPLETE
    assert transfer_status(state) == COMPLETE  # Transfer always recalculates fresh on its own render


def test_revisiting_stale_module_after_upstream_change_clears_needs_review():
    st.session_state.clear()
    _configure_reviewed_scenario()
    state = get_project_state()

    st.session_state["num_samples"] = 1000
    storage.render()
    assert compute_status(state) == NEEDS_REVIEW

    compute.render()
    assert compute_status(state) == COMPLETE


# 5. Individual widget-key healing (spec 012a §7-§8, §29) --------------------
#
# The healing source dict must include every raw widget key, not just the
# derived snapshots used for revision comparison — an earlier version of
# this fix stored only the derived dataset_sizes_snapshot/
# dataset_lifecycle_snapshot in storage_widgets, so a missing vol_FASTQ (or
# any other raw WGS field) could not be healed and crashed. This test pins
# that fix.


def test_storage_heals_individually_missing_wgs_volume_and_archive_keys():
    st.session_state.clear()
    storage.ensure_project_state()
    storage.render()

    del st.session_state["vol_FASTQ"]
    del st.session_state["archive_CRAM"]
    del st.session_state["fastq_passes"]
    storage.render()  # must not raise

    assert st.session_state["vol_FASTQ"] == 100.0
    assert st.session_state["archive_CRAM"] == "glacier_flexible"
    assert st.session_state["fastq_passes"] == 1.0


def test_storage_heals_missing_custom_project_dataset_widgets():
    st.session_state.clear()
    storage.ensure_project_state()
    st.session_state["project_mode"] = "Custom Project"
    storage.render()

    del st.session_state["custom_name_1"]
    del st.session_state["custom_size_1"]
    storage.render()  # must not raise

    assert st.session_state["custom_name_1"] == "Dataset 1"
    # 1.0 TB (the default custom-dataset size/unit) expressed in GB.
    assert st.session_state["custom_size_1"] == 1024.0


# 6. Transfer configuration persistence and validity (spec 012c) ------------


def _round_trip_away_from_transfer_and_back() -> None:
    summary.render()
    storage.render()
    compute.render()
    transfer.render()


def test_transfer_measured_throughput_survives_round_trip():
    """spec 012c §5, §8: the exact reported defect — 777 must not reset to
    0.00 after navigating away from Transfer and back."""
    st.session_state.clear()
    _configure_reviewed_scenario()  # measured mode, 777 Mbps

    _round_trip_away_from_transfer_and_back()

    assert st.session_state["transfer_measured_mbps"] == 777.0
    assert st.session_state["transfer_throughput_mode"] == "measured"
    state = get_project_state()
    assert transfer_status(state) == COMPLETE
    assert state.transfer_result.duration_hours is not None


def test_transfer_known_capacity_mode_survives_round_trip():
    """spec 012c §9: distinctive known-capacity values (not just measured)."""
    st.session_state.clear()
    storage.ensure_project_state()
    storage.render()
    st.session_state.update(
        {
            "transfer_dataset_choice": "FASTQ",
            "transfer_throughput_mode": "known_capacity",
            "transfer_link_capacity_mbps": 2500.0,
            "transfer_efficiency_percent": 63.0,
        }
    )
    transfer.render()

    _round_trip_away_from_transfer_and_back()

    assert st.session_state["transfer_throughput_mode"] == "known_capacity"
    assert st.session_state["transfer_link_capacity_mbps"] == 2500.0
    assert st.session_state["transfer_efficiency_percent"] == 63.0
    state = get_project_state()
    assert transfer_status(state) == COMPLETE
    assert state.transfer_result.throughput.effective_mbps == Decimal("1575.00")


def test_transfer_unknown_mode_survives_round_trip():
    """spec 012c §9: unknown mode and its scenario table survive too. spec
    013a §12-§16: unknown mode never produces a genuine duration, so status
    is NOT_CONFIGURED, not COMPLETE, however many pages are visited."""
    st.session_state.clear()
    storage.ensure_project_state()
    storage.render()
    st.session_state["transfer_throughput_mode"] = "unknown"
    transfer.render()

    _round_trip_away_from_transfer_and_back()

    assert st.session_state["transfer_throughput_mode"] == "unknown"
    state = get_project_state()
    assert transfer_status(state) == NOT_CONFIGURED
    assert len(state.transfer_result.scenarios) > 0


def test_transfer_distinctive_optional_fields_survive_round_trip():
    """spec 012c §10, §35: every currently-supported optional field, with
    distinctive values, round-tripped through every page."""
    st.session_state.clear()
    storage.ensure_project_state()
    storage.render()
    st.session_state.update(
        {
            "transfer_dataset_choice": "FASTQ",
            "transfer_source_type": "institutional",
            "transfer_source_location": "Cape Town",
            "transfer_destination_type": "aws_s3",
            "transfer_destination_location": "Cape Town AWS region",
            "transfer_throughput_mode": "measured",
            "transfer_measured_mbps": 777.0,
            "transfer_method": "Globus",
            "transfer_rtt_enabled": True,
            "transfer_rtt_ms": 37.0,
        }
    )
    transfer.render()

    _round_trip_away_from_transfer_and_back()

    assert st.session_state["transfer_source_location"] == "Cape Town"
    assert st.session_state["transfer_destination_location"] == "Cape Town AWS region"
    assert st.session_state["transfer_method"] == "Globus"
    assert st.session_state["transfer_rtt_enabled"] is True
    assert st.session_state["transfer_rtt_ms"] == 37.0
    state = get_project_state()
    assert transfer_status(state) == COMPLETE
    assert state.transfer_result.bdp is not None
    assert state.transfer_result.bdp.rtt_ms == Decimal("37.0")


def test_transfer_export_uses_canonical_configuration_after_round_trip():
    """spec 012c §33: exported configuration must reflect the originally
    configured values, not anything reset by intervening navigation."""
    st.session_state.clear()
    _configure_reviewed_scenario()
    _round_trip_away_from_transfer_and_back()

    state = get_project_state()
    payload = cost_export.transfer_plan_to_json("Test project", state.transfer_result)
    data = json.loads(payload)
    assert data["dataset_name"] == "FASTQ"
    assert data["throughput_mode"] == "measured"
    assert data["measured_throughput_mbps"] == "777.0"


def test_transfer_invalid_current_input_does_not_report_complete():
    """spec 012c §11-13, §32: a temporarily-broken current input must never
    be reported as Complete, and must not erase the last valid result."""
    st.session_state.clear()
    _configure_reviewed_scenario()  # valid measured/777 configuration
    state = get_project_state()
    assert transfer_status(state) == COMPLETE
    good_result = state.transfer_result

    st.session_state["transfer_measured_mbps"] = 0.0
    transfer.render()

    assert transfer_status(state) == INVALID
    # Last good config/result must still be available, untouched.
    assert state.transfer_result is good_result
    assert state.transfer_config.measured_mbps == Decimal("777.0")


def test_transfer_recovers_to_complete_after_fixing_invalid_input():
    st.session_state.clear()
    _configure_reviewed_scenario()
    state = get_project_state()

    st.session_state["transfer_measured_mbps"] = 0.0
    transfer.render()
    assert transfer_status(state) == INVALID

    st.session_state["transfer_measured_mbps"] = 500.0
    transfer.render()
    assert transfer_status(state) == COMPLETE


# 7. project_configured detection (spec 012c §14-17) -------------------------


def test_fresh_session_is_not_configured():
    st.session_state.clear()
    storage.ensure_project_state()
    state = get_project_state()
    assert state.project_configured is False


def test_500_sample_reviewed_scenario_is_configured():
    """Reproduces the exact spec 012c §14 bug reproduction: a genuinely
    configured 500-sample project must not be reported as the minimum
    default project."""
    st.session_state.clear()
    _configure_reviewed_scenario()
    state = get_project_state()
    assert state.project_configured is True


def test_1000_sample_reconfiguration_remains_configured():
    st.session_state.clear()
    _configure_reviewed_scenario()
    st.session_state["num_samples"] = 1000
    storage.render()
    state = get_project_state()
    assert state.project_configured is True


# 8. Real widget-lifecycle key-deletion regression (spec 012d §45-46) -------
#
# Every test above that exercises "round trip navigation" does so by calling
# view render() functions directly in one Python process against one shared
# st.session_state dict -- it never actually removes a widget's session-state
# entry, so it cannot reproduce the one Streamlit behaviour spec 012a's own
# module docstring names as the reason sync_widget_defaults() exists: a
# widget's st.session_state key can be individually absent on any given
# script run (e.g. because that widget -- or the whole page -- was not
# instantiated on an intervening run). The tests below explicitly `del` each
# Transfer widget key between renders to simulate that removal for real,
# which is what actually distinguishes a defect from a false-passing test.

ALL_TRANSFER_WIDGET_KEYS = [
    "transfer_dataset_choice",
    "transfer_custom_name",
    "transfer_custom_size",
    "transfer_custom_unit",
    "transfer_source_type",
    "transfer_source_custom_name",
    "transfer_destination_type",
    "transfer_destination_custom_name",
    "transfer_throughput_mode",
    "transfer_measured_mbps",
    "transfer_measured_note",
    "transfer_link_capacity_mbps",
    "transfer_efficiency_percent",
    "transfer_method",
    "transfer_source_location",
    "transfer_destination_location",
    "transfer_rtt_enabled",
    "transfer_rtt_ms",
]


def _configure_full_distinctive_transfer_scenario() -> None:
    """spec 012d §30: every editable Transfer field set to a distinctive,
    non-default value."""
    storage.ensure_project_state()
    storage.render()
    st.session_state.update(
        {
            "transfer_dataset_choice": "FASTQ",
            "transfer_source_type": "institutional",
            "transfer_source_location": "Cape Town test location",
            "transfer_destination_type": "aws_s3",
            "transfer_destination_location": "AWS Cape Town test location",
            "transfer_throughput_mode": "measured",
            "transfer_measured_mbps": 777.0,
            "transfer_measured_note": "012d persistence test",
            "transfer_method": "Globus",
            "transfer_rtt_enabled": True,
            "transfer_rtt_ms": 137.0,
        }
    )
    transfer.render()


def _delete_keys(*keys: str) -> None:
    for key in keys:
        del st.session_state[key]


def test_transfer_measured_throughput_survives_widget_key_deletion():
    """Test A (spec §46): 777 Mbps survives widget-key removal + rehydration."""
    st.session_state.clear()
    _configure_reviewed_scenario()  # measured mode, 777 Mbps

    _delete_keys("transfer_measured_mbps")
    summary.render()
    storage.render()
    compute.render()
    transfer.render()

    assert st.session_state["transfer_measured_mbps"] == 777.0
    state = get_project_state()
    assert transfer_status(state) == COMPLETE
    assert state.transfer_result.duration_hours is not None


def test_transfer_rtt_survives_widget_key_deletion():
    """Test B (spec §46): RTT enabled + 137 ms survive widget-key removal."""
    st.session_state.clear()
    storage.ensure_project_state()
    storage.render()
    st.session_state.update(
        {
            "transfer_dataset_choice": "FASTQ",
            "transfer_throughput_mode": "measured",
            "transfer_measured_mbps": 777.0,
            "transfer_rtt_enabled": True,
            "transfer_rtt_ms": 137.0,
        }
    )
    transfer.render()

    _delete_keys("transfer_rtt_enabled", "transfer_rtt_ms")
    summary.render()
    storage.render()
    compute.render()
    transfer.render()

    assert st.session_state["transfer_rtt_enabled"] is True
    assert st.session_state["transfer_rtt_ms"] == 137.0
    state = get_project_state()
    assert transfer_status(state) == COMPLETE
    assert state.transfer_result.bdp is not None
    assert state.transfer_result.bdp.rtt_ms == Decimal("137.0")


def test_transfer_locations_survive_widget_key_deletion():
    """Test C (spec §46): distinctive source/destination locations survive
    widget-key removal -- these are read via _endpoint_from_state()'s
    st.session_state.get(key, "") fallback (views/transfer.py), which must
    fall back to canonical state, not a hardcoded blank."""
    st.session_state.clear()
    storage.ensure_project_state()
    storage.render()
    st.session_state.update(
        {
            "transfer_dataset_choice": "FASTQ",
            "transfer_throughput_mode": "measured",
            "transfer_measured_mbps": 777.0,
            "transfer_source_location": "Cape Town test location",
            "transfer_destination_location": "AWS Cape Town test location",
        }
    )
    transfer.render()

    _delete_keys("transfer_source_location", "transfer_destination_location")
    summary.render()
    storage.render()
    compute.render()
    transfer.render()

    assert st.session_state["transfer_source_location"] == "Cape Town test location"
    assert st.session_state["transfer_destination_location"] == "AWS Cape Town test location"
    state = get_project_state()
    assert transfer_status(state) == COMPLETE


def test_transfer_note_survives_widget_key_deletion():
    """Test D (spec §46): a distinctive note survives widget-key removal."""
    st.session_state.clear()
    storage.ensure_project_state()
    storage.render()
    st.session_state.update(
        {
            "transfer_dataset_choice": "FASTQ",
            "transfer_throughput_mode": "measured",
            "transfer_measured_mbps": 777.0,
            "transfer_measured_note": "012d persistence test",
        }
    )
    transfer.render()

    _delete_keys("transfer_measured_note")
    summary.render()
    storage.render()
    compute.render()
    transfer.render()

    assert st.session_state["transfer_measured_note"] == "012d persistence test"
    state = get_project_state()
    assert transfer_status(state) == COMPLETE


def test_full_transfer_configuration_survives_widget_key_deletion_round_trip():
    """Test E (spec §46, §30-31): every editable Transfer field, configured
    with a distinctive value, survives a full round trip with every single
    transfer_* widget key explicitly deleted before each return to Transfer
    -- the closest simulation of the deployed 012c/012d bug report available
    without a real browser."""
    st.session_state.clear()
    _configure_full_distinctive_transfer_scenario()

    for _ in range(2):
        _delete_keys(*ALL_TRANSFER_WIDGET_KEYS)
        summary.render()
        storage.render()
        compute.render()
        transfer.render()

    assert st.session_state["transfer_dataset_choice"] == "FASTQ"
    assert st.session_state["transfer_source_location"] == "Cape Town test location"
    assert st.session_state["transfer_destination_location"] == "AWS Cape Town test location"
    assert st.session_state["transfer_throughput_mode"] == "measured"
    assert st.session_state["transfer_measured_mbps"] == 777.0
    assert st.session_state["transfer_measured_note"] == "012d persistence test"
    assert st.session_state["transfer_method"] == "Globus"
    assert st.session_state["transfer_rtt_enabled"] is True
    assert st.session_state["transfer_rtt_ms"] == 137.0

    state = get_project_state()
    assert transfer_status(state) == COMPLETE
    assert state.transfer_result.duration_hours is not None
    assert state.transfer_result.bdp is not None
    assert state.transfer_result.bdp.rtt_ms == Decimal("137.0")


def test_transfer_measured_mode_survives_switch_away_and_back_with_key_deletion():
    """spec §13, §32: measured throughput must be retained (not silently
    erased) when switching to known_capacity mode and back, even if the
    inactive mode's widget key is removed while its widget isn't drawn."""
    st.session_state.clear()
    storage.ensure_project_state()
    storage.render()
    st.session_state.update(
        {
            "transfer_dataset_choice": "FASTQ",
            "transfer_throughput_mode": "measured",
            "transfer_measured_mbps": 777.0,
        }
    )
    transfer.render()

    # Switch to known_capacity -- transfer_measured_mbps's widget is no
    # longer drawn this run, so simulate Streamlit removing its key.
    st.session_state["transfer_throughput_mode"] = "known_capacity"
    st.session_state.setdefault("transfer_link_capacity_mbps", 1000.0)
    st.session_state.setdefault("transfer_efficiency_percent", 70.0)
    _delete_keys("transfer_measured_mbps")
    transfer.render()
    assert st.session_state["transfer_throughput_mode"] == "known_capacity"

    # Switch back to measured -- 777 must be restored, not reset to 0.
    st.session_state["transfer_throughput_mode"] = "measured"
    transfer.render()

    assert st.session_state["transfer_measured_mbps"] == 777.0


def test_transfer_rtt_value_survives_disable_and_reenable_with_key_deletion():
    """spec §13, §32: RTT value must be retained across disabling and
    re-enabling RTT, even if the value widget's key is removed while
    RTT is disabled."""
    st.session_state.clear()
    storage.ensure_project_state()
    storage.render()
    st.session_state.update(
        {
            "transfer_dataset_choice": "FASTQ",
            "transfer_rtt_enabled": True,
            "transfer_rtt_ms": 137.0,
        }
    )
    transfer.render()

    # Disable RTT -- transfer_rtt_ms's widget is no longer drawn this run.
    st.session_state["transfer_rtt_enabled"] = False
    _delete_keys("transfer_rtt_ms")
    transfer.render()
    assert st.session_state["transfer_rtt_enabled"] is False

    # Re-enable RTT -- 137 ms must be restored, not reset to 0.
    st.session_state["transfer_rtt_enabled"] = True
    transfer.render()

    assert st.session_state["transfer_rtt_ms"] == 137.0


# 9. Canonical project-state architecture (spec 013) -------------------------
#
# 013's central complaint: project state must not depend on which page most
# recently rendered. One real, reproduced defect was found: views/storage.py
# used to bare-construct a fresh Project on every Storage render (via
# Project.from_storage()), discarding whatever compute_result/transfer_result
# a prior Compute/Transfer render had attached -- so navigating Storage ->
# Project Summary (skipping Compute/Transfer) made Summary wrongly hide fully
# current, valid Compute/Transfer results. Fixed by cbio_cost.project.
# build_project(state): a pure, total projection of ProjectState, called
# fresh by every page instead of incrementally mutating a cached Project.


def test_storage_then_summary_does_not_hide_current_compute_and_transfer():
    """Regression pin for the confirmed spec 013 bug: Storage -> Project
    Summary (skipping Compute/Transfer entirely) must still show Compute/
    Transfer as current, not as "not configured"."""
    st.session_state.clear()
    _configure_reviewed_scenario()
    state = get_project_state()

    storage.render()  # revisit Storage only -- no Compute/Transfer revisit

    project = build_project(state)
    assert project.compute_result is not None
    assert project.transfer_result is not None
    assert compute_status(state) == COMPLETE
    assert transfer_status(state) == COMPLETE

    summary.render()  # must not raise, must not silently disagree with the above


def test_get_module_status_dispatches_to_the_same_pure_status_functions():
    st.session_state.clear()
    _configure_reviewed_scenario()
    state = get_project_state()

    assert get_module_status(state, "storage") == storage_status(state) == COMPLETE
    assert get_module_status(state, "compute") == compute_status(state) == COMPLETE
    assert get_module_status(state, "transfer") == transfer_status(state) == COMPLETE


# 9a. Pairwise navigation orders (spec 013 §26) -------------------------------


def test_storage_transfer_storage_preserves_configuration():
    st.session_state.clear()
    _configure_reviewed_scenario()
    before = {k: st.session_state.get(k) for k in TRACKED_KEYS}

    storage.render()
    transfer.render()
    storage.render()

    after = {k: st.session_state.get(k) for k in TRACKED_KEYS}
    assert after == before


def test_storage_summary_storage_preserves_configuration():
    """Skips Compute/Transfer entirely -- the exact order that exposed the
    Project-snapshot bug fixed above."""
    st.session_state.clear()
    _configure_reviewed_scenario()
    before = {k: st.session_state.get(k) for k in TRACKED_KEYS}
    state = get_project_state()

    storage.render()
    summary.render()
    storage.render()

    after = {k: st.session_state.get(k) for k in TRACKED_KEYS}
    assert after == before
    assert compute_status(state) == COMPLETE
    assert transfer_status(state) == COMPLETE


def test_transfer_compute_transfer_preserves_configuration():
    st.session_state.clear()
    _configure_reviewed_scenario()
    before = {k: st.session_state.get(k) for k in TRACKED_KEYS}

    transfer.render()
    compute.render()
    transfer.render()

    after = {k: st.session_state.get(k) for k in TRACKED_KEYS}
    assert after == before


def test_compute_summary_compute_preserves_configuration():
    st.session_state.clear()
    _configure_reviewed_scenario()
    before = {k: st.session_state.get(k) for k in TRACKED_KEYS}

    compute.render()
    summary.render()
    compute.render()

    after = {k: st.session_state.get(k) for k in TRACKED_KEYS}
    assert after == before


# 9b. Render idempotence (spec 013 §9, §66) -----------------------------------


def test_storage_render_without_edits_does_not_bump_revisions():
    st.session_state.clear()
    _configure_reviewed_scenario()
    state = get_project_state()
    before = (state.project_revision, state.storage_config_revision, dict(state.storage_widgets))

    storage.render()
    storage.render()

    after = (state.project_revision, state.storage_config_revision, dict(state.storage_widgets))
    assert after == before


def test_compute_render_without_edits_does_not_bump_revision():
    st.session_state.clear()
    _configure_reviewed_scenario()
    state = get_project_state()
    before = (state.compute_config_revision, dict(state.compute_widgets))

    compute.render()
    compute.render()

    after = (state.compute_config_revision, dict(state.compute_widgets))
    assert after == before


def test_transfer_render_without_edits_does_not_bump_revision():
    st.session_state.clear()
    _configure_reviewed_scenario()
    state = get_project_state()
    before = (state.transfer_config_revision, dict(state.transfer_widgets))

    transfer.render()
    transfer.render()

    after = (state.transfer_config_revision, dict(state.transfer_widgets))
    assert after == before


def test_summary_render_is_read_only():
    """spec 013 §40, §71: rendering Summary must not mutate ProjectState at
    all -- not config, not results, not revisions."""
    st.session_state.clear()
    _configure_reviewed_scenario()
    state = get_project_state()
    before = dict(vars(state))

    summary.render()
    summary.render()

    after = dict(vars(state))
    assert after == before


# 9c. Compute widget-key-deletion persistence (spec 013 §63) ------------------


def test_compute_fields_survive_widget_key_deletion():
    st.session_state.clear()
    storage.ensure_project_state()
    storage.render()
    st.session_state.update(
        {
            "compute_alignment_concurrency": 7,
            "compute_deepvariant_concurrency": 13,
            "compute_scratch_gib_per_worker": 333.0,
            "compute_alignment_override_enabled": True,
            "compute_alignment_override_hours": 12.5,
            "compute_deepvariant_override_enabled": True,
            "compute_deepvariant_override_hours": 8.5,
        }
    )
    compute.render()

    _delete_keys(
        "compute_alignment_concurrency",
        "compute_deepvariant_concurrency",
        "compute_scratch_gib_per_worker",
        "compute_alignment_override_enabled",
        "compute_alignment_override_hours",
        "compute_deepvariant_override_enabled",
        "compute_deepvariant_override_hours",
    )
    summary.render()
    storage.render()
    transfer.render()
    compute.render()

    assert st.session_state["compute_alignment_concurrency"] == 7
    assert st.session_state["compute_deepvariant_concurrency"] == 13
    assert st.session_state["compute_scratch_gib_per_worker"] == 333.0
    assert st.session_state["compute_alignment_override_enabled"] is True
    assert st.session_state["compute_alignment_override_hours"] == 12.5
    assert st.session_state["compute_deepvariant_override_enabled"] is True
    assert st.session_state["compute_deepvariant_override_hours"] == 8.5
    state = get_project_state()
    assert compute_status(state) == COMPLETE


# 9d. Full-field Storage round trip with distinctive values (spec 013 §22, §62)

DISTINCTIVE_STORAGE_FIELDS = {
    "project_name": "013 distinctive project",
    "num_samples": 437,
    "retention_years": 4.25,
    "vol_FASTQ": 123.0,
    "vol_CRAM": 55.0,
    "vol_gVCF": 17.0,
    "archive_FASTQ": "glacier_instant",
    "archive_CRAM": "glacier_deep_archive",
    "archive_gVCF": "s3_standard",
    "headroom_percent": 33.0,
    "fastq_passes": 3.0,
    "cram_retrieval_percent": 44.0,
    "cram_retrieval_passes": 2.0,
    "gvcf_passes": 5.0,
    "active_months": 7.0,
    "transfer_contingency_percent": 31.0,
    "onboarding_hours": 19.0,
    "operations_hours_per_year": 29.0,
    "closeout_hours": 11.0,
    "hourly_rate_zar": 1234.0,
    "usd_zar": 17.77,
    "vat_percent": 16.5,
}


def test_full_distinctive_storage_configuration_survives_round_trip():
    st.session_state.clear()
    storage.ensure_project_state()
    st.session_state.update(DISTINCTIVE_STORAGE_FIELDS)
    storage.render()

    compute.render()
    transfer.render()
    summary.render()
    storage.render()
    compute.render()
    transfer.render()
    summary.render()

    for key, value in DISTINCTIVE_STORAGE_FIELDS.items():
        assert st.session_state[key] == value, key


def test_full_distinctive_storage_configuration_survives_widget_key_deletion():
    st.session_state.clear()
    storage.ensure_project_state()
    st.session_state.update(DISTINCTIVE_STORAGE_FIELDS)
    storage.render()

    _delete_keys(*DISTINCTIVE_STORAGE_FIELDS.keys())
    compute.render()
    transfer.render()
    summary.render()
    storage.render()

    for key, value in DISTINCTIVE_STORAGE_FIELDS.items():
        assert st.session_state[key] == value, key


# 9e. No mixed revisions (spec 013 §72) ---------------------------------------


def test_summary_never_presents_stale_compute_or_transfer_as_current():
    st.session_state.clear()
    _configure_reviewed_scenario()
    state = get_project_state()

    st.session_state["num_samples"] = 1000
    storage.render()  # Storage current for 1000; Compute/Transfer still stamped for 500

    assert storage_status(state) == COMPLETE
    assert compute_status(state) == NEEDS_REVIEW
    assert transfer_status(state) == NEEDS_REVIEW

    project = build_project(state)
    # The stale results must still be retrievable (so Summary can show them
    # labelled "Needs review"), but never reported as COMPLETE.
    assert project.compute_result is not None
    assert project.transfer_result is not None

    summary.render()  # must not raise, must not silently upgrade either to Complete
    assert compute_status(state) == NEEDS_REVIEW
    assert transfer_status(state) == NEEDS_REVIEW


# 10. Status tightening -- a page visit alone must not be Complete (spec 013a §12-§18)


def test_transfer_fresh_visit_is_not_configured_not_complete():
    """Transfer's default state (throughput_mode == "unknown") is a valid
    TransferPlan but never a genuine estimate -- opening the page must not
    read as Complete."""
    st.session_state.clear()
    storage.ensure_project_state()
    transfer.render()

    state = get_project_state()
    assert transfer_status(state) == NOT_CONFIGURED


def test_transfer_becomes_complete_once_measured_throughput_configured():
    st.session_state.clear()
    storage.ensure_project_state()
    storage.render()
    transfer.render()
    state = get_project_state()
    assert transfer_status(state) == NOT_CONFIGURED

    st.session_state.update({"transfer_throughput_mode": "measured", "transfer_measured_mbps": 777.0})
    transfer.render()
    assert transfer_status(state) == COMPLETE


def test_navigation_alone_does_not_fabricate_transfer_complete():
    """spec 013a §15: simply navigating Storage -> Compute -> Transfer with
    zero edits must not automatically produce Transfer Complete. Compute
    becoming Complete from its own reasonable default assumptions (10/10
    concurrency, 250 GiB scratch -- real planning values, not a
    placeholder) is intentional (spec 013a §18), not a status defect."""
    st.session_state.clear()
    storage.ensure_project_state()
    storage.render()
    compute.render()
    transfer.render()

    state = get_project_state()
    assert compute_status(state) == COMPLETE
    assert transfer_status(state) == NOT_CONFIGURED


# 11. Transfer persistence gate (spec 013a §3-§11) ----------------------------


def test_transfer_full_distinctive_configuration_survives_013a_gate_sequence():
    """spec 013a §11's exact acceptance gate, reproduced with real
    widget-key deletion between renders (the actual Streamlit widget-
    removal mechanism, not just a same-process function call). This could
    not be reproduced against current code -- see completion report -- so
    this pins the correct (surviving) behaviour as a permanent regression
    test rather than leaving it unverified."""
    st.session_state.clear()
    storage.ensure_project_state()
    storage.render()
    st.session_state.update(
        {
            "transfer_dataset_choice": "FASTQ",
            "transfer_throughput_mode": "measured",
            "transfer_measured_mbps": 777.0,
            "transfer_method": "Globus",
            "transfer_rtt_enabled": True,
            "transfer_rtt_ms": 137.0,
            "transfer_source_location": "Cape Town test source",
            "transfer_destination_location": "AWS Cape Town test destination",
            "transfer_measured_note": "013a persistence test",
        }
    )
    transfer.render()

    _delete_keys(*ALL_TRANSFER_WIDGET_KEYS)
    summary.render()
    storage.render()
    compute.render()
    transfer.render()

    assert st.session_state["transfer_dataset_choice"] == "FASTQ"
    assert st.session_state["transfer_throughput_mode"] == "measured"
    assert st.session_state["transfer_measured_mbps"] == 777.0
    assert st.session_state["transfer_method"] == "Globus"
    assert st.session_state["transfer_rtt_enabled"] is True
    assert st.session_state["transfer_rtt_ms"] == 137.0
    assert st.session_state["transfer_source_location"] == "Cape Town test source"
    assert st.session_state["transfer_destination_location"] == "AWS Cape Town test destination"
    assert st.session_state["transfer_measured_note"] == "013a persistence test"
    state = get_project_state()
    assert transfer_status(state) == COMPLETE


# 12. New project (spec 013a §32-§46) -----------------------------------------


def _configure_full_project_for_reset_tests() -> None:
    _configure_reviewed_scenario()  # 500 samples, 7/13/333, FASTQ measured 777
    st.session_state.update({"transfer_rtt_enabled": True, "transfer_rtt_ms": 137.0})
    transfer.render()


def test_reset_project_clears_configuration_status_and_results():
    st.session_state.clear()
    _configure_full_project_for_reset_tests()
    assert get_project_state().project_configured is True

    project_setup.reset_project()

    state = get_project_state()
    assert state.project_configured is False
    assert compute_status(state) == NOT_CONFIGURED
    assert transfer_status(state) == NOT_CONFIGURED
    # Storage's minimum-valid default still produces a genuine calculation
    # (unchanged, pre-existing semantics spec 013a §48 explicitly reaffirms
    # keeping) -- project_configured, not storage_status, is what
    # distinguishes "the minimum default" from "a real project".
    assert storage_status(state) == COMPLETE


def test_reset_project_ghost_state_does_not_resurrect_old_values():
    """spec 013a §43, §66: after New project, no old widget value may
    reappear, across every page."""
    st.session_state.clear()
    _configure_full_project_for_reset_tests()

    project_setup.reset_project()

    storage.render()
    compute.render()
    transfer.render()
    summary.render()
    storage.render()

    assert st.session_state["num_samples"] == 1
    assert st.session_state["compute_alignment_concurrency"] == 10
    assert st.session_state["compute_deepvariant_concurrency"] == 10
    assert st.session_state["transfer_measured_mbps"] == 0.0
    assert st.session_state["transfer_rtt_enabled"] is False
    assert st.session_state["transfer_rtt_ms"] == 0.0


def test_reset_project_then_load_example_reproduces_clean_demo():
    """spec 013a §45: reset and profile loading are clean inverse
    transitions."""
    st.session_state.clear()
    _configure_full_project_for_reset_tests()
    project_setup.reset_project()

    storage.load_demo_profile()
    storage.render()

    assert st.session_state["project_name"] == "Example WGS Project"
    assert st.session_state["num_samples"] == 500
    assert st.session_state["retention_years"] == 5.0
    state = get_project_state()
    assert state.project_configured is True
    assert storage_status(state) == COMPLETE


def test_load_example_then_reset_project_leaves_fresh_state():
    """spec 013a §46: the reverse order leaves no demo values behind."""
    st.session_state.clear()
    storage.ensure_project_state()
    storage.load_demo_profile()
    storage.render()
    assert get_project_state().project_configured is True

    project_setup.reset_project()

    state = get_project_state()
    assert state.project_configured is False
    assert st.session_state["num_samples"] == 1
    assert st.session_state["project_name"] == ""
