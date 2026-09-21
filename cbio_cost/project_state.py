"""Canonical, session-level project state (spec 012a).

> Streamlit widgets are views onto project state. They are not the
> project state. (spec 012a §7, quoted directly)

Widget-associated ``st.session_state`` keys can be individually missing on
any given script run (a fresh session, a partially-lost key, a direct
non-Storage page entry). Before spec 012a, each page gated *all* of its
widget defaults behind one boolean flag (``"loaded"``, ``"compute_loaded"``,
``"transfer_loaded"``); if that flag survived but one individual widget key
did not, the next bare ``st.session_state[key]`` read crashed — exactly the
Transfer crash spec 012a §4 reproduces. This module holds one durable
``ProjectState`` object per session that survives regardless of which page's
widgets are drawn on a given run, plus per-module revision counters so
Project Summary can tell whether a stored result is still current for the
project's live configuration rather than silently combining results
calculated from different project states (spec 012a §5, §19).

Deliberately flat ``dict[str, Any]`` config snapshots keyed like each page's
own widget keys (spec 012a §6 explicitly sanctions "typed dictionaries...
existing domain models extended cleanly") rather than a parallel dataclass
hierarchy mirroring every Storage/Compute/Transfer field — this keeps the
change additive and low-risk. The existing ``cbio_cost.project.Project``
read-model is unchanged; it continues to be rebuilt from this state after
each module's render (see each ``views/*.py`` module).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import streamlit as st

from cbio_cost.compute_models import ComputeResult
from cbio_cost.models import CostEstimate
from cbio_cost.transfer_plan_models import TransferPlan, TransferPlanResult

PROJECT_STATE_SESSION_KEY = "project_state"

NOT_CONFIGURED = "not_configured"
COMPLETE = "complete"
NEEDS_REVIEW = "needs_review"
INVALID = "invalid"

# Storage widget keys that define shared project identity or dataset size —
# changing any of these invalidates Storage, Compute and Transfer alike
# (spec 012a §12). Dataset *lifecycle* fields (archive class, retrieval
# fraction, read passes, active months) affect Storage's own cost only, not
# Transfer's size-based presets or Compute at all, so they live in
# STORAGE_ONLY_KEYS instead via ``dataset_lifecycle_snapshot``.
#
# Conservative, documented simplification: a dataset *size* change also
# invalidates Compute even though Compute's own calculation only depends on
# ``num_samples``, not per-sample volumes — spec 012a §12 explicitly permits
# "a conservative broad invalidation model... if it is correct and clearly
# documented" over a full five-edge dependency graph.
SHARED_STORAGE_KEYS = frozenset(
    {
        "project_mode",
        "num_samples",
        "retention_years",
        "usd_zar",
        "vat_percent",
        "dataset_sizes_snapshot",
    }
)

# Storage-only widget keys: affect Storage's own cost result and Project
# Summary, but never Compute or Transfer (spec 012a §9, §12).
STORAGE_ONLY_KEYS = frozenset(
    {
        "headroom_percent",
        "active_months",
        "transfer_contingency_percent",
        "onboarding_hours",
        "operations_hours_per_year",
        "closeout_hours",
        "hourly_rate_zar",
        "dataset_lifecycle_snapshot",
    }
)


@dataclass
class ProjectState:
    storage_widgets: dict[str, Any] = field(default_factory=dict)
    compute_widgets: dict[str, Any] = field(default_factory=dict)
    transfer_widgets: dict[str, Any] = field(default_factory=dict)
    transfer_config: TransferPlan | None = None

    storage_result: CostEstimate | None = None
    compute_result: ComputeResult | None = None
    transfer_result: TransferPlanResult | None = None

    project_revision: int = 0
    storage_config_revision: int = 0
    compute_config_revision: int = 0
    transfer_config_revision: int = 0

    storage_calculated_for: tuple[int, int] | None = None
    compute_calculated_for: tuple[int, int] | None = None
    transfer_calculated_for: tuple[int, int] | None = None

    # Explicit project-identity flag (spec 012c §14-17) — deliberately not
    # inferred from any revision counter. A genuinely configured project may
    # legitimately use default-looking values (e.g. 1 sample), and a
    # storage-only counter (headroom/archive/engineering) can stay at 0 for
    # a fully-configured project if the user never touched those specific
    # fields, so neither revision counter is a reliable "configured" signal.
    project_configured: bool = False

    # Whether the *current* Transfer widget configuration validates
    # successfully (spec 012c §11-13) — distinct from whether a result
    # exists at all. False only while the user is looking at an active
    # validation error; the last valid config/result are left untouched.
    transfer_valid: bool = True


def get_project_state() -> ProjectState:
    """One canonical ``ProjectState`` per session — created once, then
    reused (and mutated in place) on every subsequent render, regardless of
    which page is currently active."""
    return st.session_state.setdefault(PROJECT_STATE_SESSION_KEY, ProjectState())


def sync_widget_defaults(canonical: dict[str, Any]) -> None:
    """Heal any individually-missing widget key from canonical state (spec
    012a §8), every render — not gated behind a single one-time flag. Keys
    already present (including ones mid-edit this run) are left untouched,
    so in-session edits are never overwritten."""
    for key, value in canonical.items():
        if key not in st.session_state:
            st.session_state[key] = value


def record_storage(state: ProjectState, widgets: dict[str, Any], result: CostEstimate) -> None:
    old = state.storage_widgets
    if old:
        old_shared = {k: old.get(k) for k in SHARED_STORAGE_KEYS}
        new_shared = {k: widgets.get(k) for k in SHARED_STORAGE_KEYS}
        if old_shared != new_shared:
            state.project_revision += 1
        old_own = {k: old.get(k) for k in STORAGE_ONLY_KEYS}
        new_own = {k: widgets.get(k) for k in STORAGE_ONLY_KEYS}
        if old_own != new_own:
            state.storage_config_revision += 1
        # Explicit configured-project flag (spec 012c §14-17): any change to
        # any Storage widget at all — including project_name, which no
        # revision counter tracks since it has no calculation effect — means
        # the user has intentionally set up a project. Sticky: never reset.
        if old != widgets:
            state.project_configured = True
    state.storage_widgets = dict(widgets)
    state.storage_result = result
    state.storage_calculated_for = (state.project_revision, state.storage_config_revision)


def record_compute(state: ProjectState, widgets: dict[str, Any], result: ComputeResult) -> None:
    old = state.compute_widgets
    if old and old != widgets:
        state.compute_config_revision += 1
    state.compute_widgets = dict(widgets)
    state.compute_result = result
    state.compute_calculated_for = (state.project_revision, state.compute_config_revision)


def record_transfer(
    state: ProjectState, plan: TransferPlan, widgets: dict[str, Any], result: TransferPlanResult
) -> None:
    old = state.transfer_widgets
    if old and old != widgets:
        state.transfer_config_revision += 1
    state.transfer_widgets = dict(widgets)
    state.transfer_config = plan
    state.transfer_result = result
    state.transfer_valid = True
    state.transfer_calculated_for = (state.project_revision, state.transfer_config_revision)


def mark_transfer_invalid(state: ProjectState) -> None:
    """The *current* Transfer widget configuration fails validation (spec
    012c §11-13, §32) — record that fact without touching the last valid
    ``transfer_config``/``transfer_widgets``/``transfer_result``, so a
    temporarily-broken edit never erases the last good configuration and
    Project Summary can still show it (marked stale/invalid rather than
    silently as current)."""
    state.transfer_valid = False


def storage_status(state: ProjectState) -> str:
    if state.storage_result is None:
        return NOT_CONFIGURED
    if state.storage_calculated_for != (state.project_revision, state.storage_config_revision):
        return NEEDS_REVIEW
    return COMPLETE


def compute_status(state: ProjectState) -> str:
    if state.compute_result is None:
        return NOT_CONFIGURED
    if state.compute_calculated_for != (state.project_revision, state.compute_config_revision):
        return NEEDS_REVIEW
    return COMPLETE


def transfer_status(state: ProjectState) -> str:
    if not state.transfer_valid:
        return INVALID
    if state.transfer_result is None:
        return NOT_CONFIGURED
    if state.transfer_calculated_for != (state.project_revision, state.transfer_config_revision):
        return NEEDS_REVIEW
    return COMPLETE


STATUS_LABELS = {
    NOT_CONFIGURED: "Not configured",
    COMPLETE: "Complete",
    NEEDS_REVIEW: "Needs review",
    INVALID: "Invalid",
}
