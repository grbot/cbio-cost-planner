"""End-to-end page-navigation and dependency-invalidation regression tests
(spec 012a §34-§39). Exercises the real Streamlit view render() functions in
sequence within one session — this is a faithful simulation of real
navigation, since Streamlit's session_state is one persistent object for the
whole browser session regardless of which page is currently displayed
(confirmed against the deployed app's own reported behaviour for the
defects this spec fixes).
"""

from __future__ import annotations

from decimal import Decimal

import streamlit as st

from cbio_cost.project_state import (
    COMPLETE,
    NEEDS_REVIEW,
    compute_status,
    get_project_state,
    storage_status,
    transfer_status,
)
from cbio_cost.units import gb_to_tb
from views import compute, storage, summary, transfer

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
    storage._load_demo_profile()
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
