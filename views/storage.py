"""Storage module — Streamlit UI (spec 010: moved from the former app.py).

This module only reads widget inputs, builds the typed assumption objects
from ``cbio_cost.models``, calls into ``cbio_cost.calculator`` for every
calculation, and renders the results. No arithmetic happens here.

Two project modes are supported (spec 006): WGS 30x (a predefined template
that generates datasets from a sample count) and Custom Project (datasets
entered directly). Both reduce to the same ``list[Dataset]`` before reaching
the shared calculation engine — see cbio_cost/calculator.py.

App-level chrome (page config, theme injection, title/strapline, top
navigation) lives in ``app.py``, which calls :func:`render` for this page.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
import streamlit as st

import theme
from data_volume_guide import DATA_VOLUME_GUIDE
from cbio_cost import config as cost_config
from cbio_cost import export as cost_export
from cbio_cost.calculator import build_estimate, build_scenarios, explain_result
from cbio_cost.export import STORAGE_CLASS_LABELS
from cbio_cost.models import (
    WGS_FILE_TYPES,
    CostEstimate,
    CurrencyAssumptions,
    Dataset,
    EngineeringAssumptions,
    FileTypeVolumeAssumption,
    ProjectInputs,
    ScenarioAssumptions,
    WgsMovementAssumptions,
)
from cbio_cost.project import PROJECT_SESSION_KEY, Project, build_project
from cbio_cost.project_state import (
    STATUS_LABELS,
    ProjectState,
    compute_status,
    get_project_state,
    record_storage,
    sync_widget_defaults,
    transfer_status,
)
from cbio_cost.units import gb_to_tb

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
GB_PER_TB = Decimal(1024)
CUSTOM_MAX_DATASETS = 20
WGS_MODE = "WGS 30×"
CUSTOM_MODE = "Custom Project"


def _load_pricing():
    # Deliberately uncached: parsing this small YAML file is cheap, and
    # st.cache_resource previously caused a stale PricingConfig (missing the
    # pricing_source/region_name/pricing_last_verified fields added in
    # requests/005-pricing-and-disclaimer.md) to survive a lightweight
    # redeploy, since the cache key is derived from this wrapper's own
    # source, not from cbio_cost/config.py or the YAML it reads.
    return cost_config.load_pricing(CONFIG_DIR / "aws-pricing.yaml")


def _load_profile_and_scenarios():
    # See _load_pricing() above — deliberately uncached for the same reason.
    return cost_config.load_profiles(CONFIG_DIR / "project-profiles.yaml")


def _dec(value) -> Decimal:
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return Decimal(0)


# ---------------------------------------------------------------------------
# Custom Project dataset session-state management (spec 006 §10-§12)
# ---------------------------------------------------------------------------


def _seed_custom_dataset_defaults(dataset_id: int, name: str) -> None:
    st.session_state[f"custom_name_{dataset_id}"] = name
    st.session_state[f"custom_size_{dataset_id}"] = 1.0
    st.session_state[f"custom_unit_{dataset_id}"] = "TB"
    st.session_state[f"custom_retrieval_{dataset_id}"] = 100.0
    st.session_state[f"custom_passes_{dataset_id}"] = 1.0
    st.session_state[f"custom_active_months_{dataset_id}"] = 1.0
    st.session_state[f"custom_archive_{dataset_id}"] = "glacier_flexible"


def _init_custom_datasets() -> None:
    if "custom_dataset_ids" not in st.session_state:
        st.session_state["custom_dataset_ids"] = [1]
        st.session_state["custom_next_id"] = 2
        _seed_custom_dataset_defaults(1, "Dataset 1")


def _heal_custom_dataset_widgets(canonical_datasets: list[Dataset] | None) -> None:
    """Reseed any individually-missing per-dataset widget key from the last
    canonical dataset list (spec 012a §8) — ``custom_dataset_ids`` surviving
    while a specific ``custom_name_{id}`` key does not is exactly the class
    of partial state loss spec 012a reproduces for Transfer (§4)."""
    ids = st.session_state.get("custom_dataset_ids", [])
    for i, dataset_id in enumerate(ids):
        if f"custom_name_{dataset_id}" in st.session_state:
            continue
        if canonical_datasets and i < len(canonical_datasets):
            d = canonical_datasets[i]
            st.session_state[f"custom_name_{dataset_id}"] = d.name
            st.session_state[f"custom_size_{dataset_id}"] = float(d.size_gb)
            st.session_state[f"custom_unit_{dataset_id}"] = "GB"
            st.session_state[f"custom_retrieval_{dataset_id}"] = float(d.retrieval_fraction * 100)
            st.session_state[f"custom_passes_{dataset_id}"] = float(d.read_passes)
            st.session_state[f"custom_active_months_{dataset_id}"] = float(d.active_months)
            st.session_state[f"custom_archive_{dataset_id}"] = d.archive_class
        else:
            _seed_custom_dataset_defaults(dataset_id, f"Dataset {i + 1}")


def _add_custom_dataset() -> None:
    ids = st.session_state["custom_dataset_ids"]
    if len(ids) >= CUSTOM_MAX_DATASETS:
        return
    new_id = st.session_state["custom_next_id"]
    st.session_state["custom_next_id"] += 1
    ids.append(new_id)
    _seed_custom_dataset_defaults(new_id, f"Dataset {len(ids)}")


def _remove_custom_dataset(dataset_id: int) -> None:
    ids = st.session_state["custom_dataset_ids"]
    if dataset_id in ids and len(ids) > 1:
        ids.remove(dataset_id)


def _default_state() -> dict:
    profile, _scenarios = _load_profile_and_scenarios()
    currency = cost_config.load_currency_defaults(CONFIG_DIR / "aws-pricing.yaml")
    state = {
        "project_mode": WGS_MODE,
        "project_name": profile.project.project_name,
        "num_samples": profile.project.num_samples,
        "retention_years": float(profile.project.retention_years),
        "headroom_percent": float(profile.project.headroom_fraction * 100),
        "active_months": float(profile.active_months),
        "fastq_passes": float(profile.movement.fastq_passes),
        "cram_retrieval_percent": float(profile.movement.cram_retrieval_fraction * 100),
        "cram_retrieval_passes": float(profile.movement.cram_retrieval_passes),
        "gvcf_passes": float(profile.movement.gvcf_passes),
        "transfer_contingency_percent": float(profile.project.transfer_contingency * 100),
        "onboarding_hours": float(profile.engineering.onboarding_hours),
        "operations_hours_per_year": float(profile.engineering.operations_hours_per_year),
        "closeout_hours": float(profile.engineering.closeout_hours),
        "hourly_rate_zar": float(profile.engineering.hourly_rate_zar),
        "usd_zar": float(currency.usd_zar),
        "vat_percent": float(currency.vat_fraction * 100),
    }
    for name, v in profile.volumes.items():
        state[f"vol_{name}"] = float(v.gb_per_sample)
        state[f"archive_{name}"] = v.archive_class
    return state


def _minimum_valid_state() -> dict:
    # Conservative minimum-valid WGS 30x project — the application's actual
    # starting state (spec 011a §2). Keeps all config-driven planning
    # defaults (volumes, movement, engineering, currency) from
    # _default_state() and overrides only the project-identity fields that
    # made the app look like a specific real 500-sample project on first
    # load. The full 500x30x/5-year example remains available via the
    # explicit "Load demo profile" button (load_demo_profile() below).
    state = _default_state()
    state["project_name"] = ""
    state["num_samples"] = 1
    state["retention_years"] = 1.0
    return state


def load_demo_profile() -> None:
    """Project-level action (spec 013a §26): atomically loads the full
    500x30x/5-year example into canonical widget state. Called from the
    shared Project setup area (``project_setup.py``), not owned by Storage
    -- the example project spans project identity plus every module's
    planning defaults in one profile."""
    st.session_state.update(_default_state())


def _wgs_datasets_from_session_state():
    """(num_samples, volumes, wgs_movement, active_months, datasets,
    headroom_fraction) for WGS 30x mode, read from current session-state
    widget values. Shared by render()'s WGS branch and
    _build_project_from_session_state() (spec 011a §3) so there is one
    source of truth for how WGS datasets are derived from session state."""
    num_samples = int(st.session_state["num_samples"])
    volumes = {
        file_type: FileTypeVolumeAssumption(
            name=file_type,
            gb_per_sample=_dec(st.session_state[f"vol_{file_type}"]),
            archive_class=st.session_state[f"archive_{file_type}"],
        )
        for file_type in WGS_FILE_TYPES
    }
    wgs_movement = WgsMovementAssumptions(
        fastq_passes=_dec(st.session_state["fastq_passes"]),
        cram_retrieval_fraction=_dec(st.session_state["cram_retrieval_percent"]) / Decimal(100),
        cram_retrieval_passes=_dec(st.session_state["cram_retrieval_passes"]),
        gvcf_passes=_dec(st.session_state["gvcf_passes"]),
    )
    active_months = _dec(st.session_state["active_months"])
    datasets = cost_config.build_wgs_datasets(num_samples, volumes, wgs_movement, active_months)
    headroom_fraction = _dec(st.session_state["headroom_percent"]) / Decimal(100)
    return num_samples, volumes, wgs_movement, active_months, datasets, headroom_fraction


def _current_storage_widgets(datasets: list[Dataset]) -> dict:
    """Canonical snapshot of every Storage input that matters for revision
    tracking (spec 012a §6, §12), read from already-synced session state.

    ``dataset_sizes_snapshot`` (shared — affects Storage/Compute/Transfer)
    and ``dataset_lifecycle_snapshot`` (storage-only — archive class,
    retrieval, read passes, active months, which affect Storage's own cost
    but not Transfer's size-based presets or Compute at all) are derived
    from the resolved dataset list rather than tracked per raw widget, so
    this works identically for WGS and Custom Project mode.
    """
    widgets = {
        "project_mode": st.session_state["project_mode"],
        "project_name": st.session_state["project_name"],
        "num_samples": st.session_state.get("num_samples") if st.session_state["project_mode"] == WGS_MODE else None,
        "retention_years": st.session_state["retention_years"],
        "usd_zar": st.session_state["usd_zar"],
        "vat_percent": st.session_state["vat_percent"],
        # Derived snapshots, used for shared-vs-storage-only revision
        # comparison (record_storage) — a change to any raw contributing
        # field below (volumes, movement, custom dataset entries) shows up
        # here automatically, without tracking each raw field separately.
        "dataset_sizes_snapshot": tuple((d.name, d.size_gb) for d in datasets),
        "dataset_lifecycle_snapshot": tuple(
            (d.name, d.archive_class, d.retrieval_fraction, d.read_passes, d.active_months) for d in datasets
        ),
        "headroom_percent": st.session_state.get("headroom_percent"),
        "active_months": st.session_state.get("active_months"),
        "transfer_contingency_percent": st.session_state["transfer_contingency_percent"],
        "onboarding_hours": st.session_state["onboarding_hours"],
        "operations_hours_per_year": st.session_state["operations_hours_per_year"],
        "closeout_hours": st.session_state["closeout_hours"],
        "hourly_rate_zar": st.session_state["hourly_rate_zar"],
        "custom_datasets": tuple(datasets) if st.session_state["project_mode"] != WGS_MODE else None,
    }
    # Raw WGS per-field widget keys: not compared individually for revision
    # purposes (their net effect is already captured by the snapshots
    # above), but must still be present here so sync_widget_defaults() can
    # heal any of them if individually missing (spec 012a §8).
    for file_type in WGS_FILE_TYPES:
        widgets[f"vol_{file_type}"] = st.session_state.get(f"vol_{file_type}")
        widgets[f"archive_{file_type}"] = st.session_state.get(f"archive_{file_type}")
    widgets["fastq_passes"] = st.session_state.get("fastq_passes")
    widgets["cram_retrieval_percent"] = st.session_state.get("cram_retrieval_percent")
    widgets["cram_retrieval_passes"] = st.session_state.get("cram_retrieval_passes")
    widgets["gvcf_passes"] = st.session_state.get("gvcf_passes")
    return widgets


def _build_project_from_session_state() -> Project:
    """Build the shared WGS 30x Project from current session-state values,
    without requiring any widget to have been drawn (spec 011a §3). Used to
    bootstrap session state before navigation dispatches to a page —
    Streamlit widgets read their initial value from session state by key,
    so this works even though no widget has executed yet this run."""
    pricing = _load_pricing()
    num_samples, _volumes, _wgs_movement, _active_months, datasets, headroom_fraction = (
        _wgs_datasets_from_session_state()
    )
    transfer_contingency = _dec(st.session_state["transfer_contingency_percent"]) / Decimal(100)
    inputs = ProjectInputs(
        project_name=st.session_state["project_name"] or "Untitled project",
        project_type="WGS 30x",
        retention_years=_dec(st.session_state["retention_years"]),
        transfer_contingency=transfer_contingency,
        headroom_fraction=headroom_fraction,
        num_samples=num_samples,
    )
    engineering = EngineeringAssumptions(
        onboarding_hours=_dec(st.session_state["onboarding_hours"]),
        operations_hours_per_year=_dec(st.session_state["operations_hours_per_year"]),
        closeout_hours=_dec(st.session_state["closeout_hours"]),
        hourly_rate_zar=_dec(st.session_state["hourly_rate_zar"]),
    )
    currency = CurrencyAssumptions(
        usd_zar=_dec(st.session_state["usd_zar"]),
        vat_fraction=_dec(st.session_state["vat_percent"]) / Decimal(100),
    )
    estimate = build_estimate(inputs, datasets, engineering, pricing, currency)
    estimate.explanation = explain_result(estimate)

    state = get_project_state()
    record_storage(state, _current_storage_widgets(datasets), estimate)

    return build_project(state)


@dataclass
class _StorageComputation:
    """Everything derived from one Storage-estimate recompute (spec 014
    §12-§14, §22) that a caller might need afterwards -- returned rather
    than left as ``render()``-local variables so the same computation can be
    triggered from outside Storage's own page (``refresh_current_estimate``,
    called from ``app.py`` on every run) as well as from ``render()`` itself
    (which additionally needs these values to build sensitivity scenarios)."""

    estimate: CostEstimate
    datasets: list[Dataset]
    engineering: EngineeringAssumptions
    currency: CurrencyAssumptions
    transfer_contingency: Decimal
    num_samples: int | None
    volumes: dict[str, FileTypeVolumeAssumption] | None
    wgs_movement: WgsMovementAssumptions | None
    active_months: Decimal | None


def _recompute_estimate(state: ProjectState) -> _StorageComputation:
    """Build this run's Storage estimate from current ``st.session_state``
    values and record it into canonical ``ProjectState`` (spec 014 §12-§14,
    §22, §25) -- the one place Storage's cost estimate is actually computed,
    shared by Storage's own ``render()`` and ``refresh_current_estimate()``
    below. Safe to call before any Storage widget has been drawn this run:
    session state already holds each widget's current value by the time any
    script executes (Streamlit's own rerun mechanism, plus
    ``sync_widget_defaults`` healing), so this does not depend on Storage's
    own widgets having rendered first. Raises ``ValueError`` on invalid
    input -- callers decide how to surface that."""
    pricing = _load_pricing()
    is_wgs_mode = st.session_state["project_mode"] == WGS_MODE

    if is_wgs_mode:
        project_type = "WGS 30x"
        num_samples, volumes, wgs_movement, active_months, datasets, headroom_fraction = (
            _wgs_datasets_from_session_state()
        )
    else:
        project_type = "Custom Project"
        num_samples = None
        volumes = None
        wgs_movement = None
        active_months = None
        headroom_fraction = Decimal(0)
        datasets = []
        for dataset_id in st.session_state["custom_dataset_ids"]:
            unit = st.session_state[f"custom_unit_{dataset_id}"]
            size = _dec(st.session_state[f"custom_size_{dataset_id}"])
            size_gb = size * GB_PER_TB if unit == "TB" else size
            datasets.append(
                Dataset(
                    name=st.session_state[f"custom_name_{dataset_id}"],
                    size_gb=size_gb,
                    retrieval_fraction=_dec(st.session_state[f"custom_retrieval_{dataset_id}"]) / Decimal(100),
                    read_passes=_dec(st.session_state[f"custom_passes_{dataset_id}"]),
                    active_months=_dec(st.session_state[f"custom_active_months_{dataset_id}"]),
                    archive_class=st.session_state[f"custom_archive_{dataset_id}"],
                )
            )

    transfer_contingency = _dec(st.session_state["transfer_contingency_percent"]) / Decimal(100)
    inputs = ProjectInputs(
        project_name=st.session_state["project_name"] or "Untitled project",
        project_type=project_type,
        retention_years=_dec(st.session_state["retention_years"]),
        transfer_contingency=transfer_contingency,
        headroom_fraction=headroom_fraction,
        num_samples=num_samples,
    )
    engineering = EngineeringAssumptions(
        onboarding_hours=_dec(st.session_state["onboarding_hours"]),
        operations_hours_per_year=_dec(st.session_state["operations_hours_per_year"]),
        closeout_hours=_dec(st.session_state["closeout_hours"]),
        hourly_rate_zar=_dec(st.session_state["hourly_rate_zar"]),
    )
    currency = CurrencyAssumptions(
        usd_zar=_dec(st.session_state["usd_zar"]),
        vat_fraction=_dec(st.session_state["vat_percent"]) / Decimal(100),
    )

    estimate = build_estimate(inputs, datasets, engineering, pricing, currency)
    estimate.explanation = explain_result(estimate)

    # Canonical project state (spec 012a §6): record this result against
    # the current widget configuration, bumping revisions only where an
    # actual value changed, so Project Summary can later tell whether
    # this (or any other module's) result is still current.
    record_storage(state, _current_storage_widgets(datasets), estimate)

    # Shared project model (spec 010 §4, spec 013 §2/§8/§40-41): a pure
    # projection of ProjectState, built fresh here (never mutated
    # incrementally) so Compute/Transfer attachments already recorded in
    # ProjectState survive a Storage re-render regardless of navigation
    # order.
    st.session_state[PROJECT_SESSION_KEY] = build_project(state)

    return _StorageComputation(
        estimate=estimate,
        datasets=datasets,
        engineering=engineering,
        currency=currency,
        transfer_contingency=transfer_contingency,
        num_samples=num_samples,
        volumes=volumes,
        wgs_movement=wgs_movement,
        active_months=active_months,
    )


def refresh_current_estimate(state: ProjectState) -> None:
    """Unconditional per-run recompute (spec 014 §12-§14, §22, §25), called
    from ``app.py`` before ``st.navigation`` dispatches to whichever page is
    active -- keeps ``storage_result``/``storage_widgets``/``project_revision``
    live-current for Compute/Transfer/Summary even when Storage's own page
    is never visited this session (previously they only refreshed when
    Storage's own ``render()`` executed, so a project-header edit made while
    on another page was invisible to Summary/status until Storage was next
    opened). Swallows invalid input rather than crashing the whole app:
    canonical state simply keeps its last-good value, and Storage's own
    page still surfaces the real error to the user when they visit it."""
    sync_widget_defaults(state.storage_widgets or _minimum_valid_state())
    _init_custom_datasets()
    _heal_custom_dataset_widgets(state.storage_widgets.get("custom_datasets"))
    try:
        _recompute_estimate(state)
    except ValueError:
        pass


def ensure_project_state() -> None:
    """Guarantee a shared Project exists in session state before any page
    renders, regardless of which page the user opens first (spec 011a §3).
    Seeds minimum-valid WGS defaults (spec 011a §2) — never the 500-sample
    example — so direct navigation to Compute/Transfer/Project Summary in a
    fresh session sees a coherent, if minimal, project instead of a
    contradictory "no project configured" state. Also establishes the
    canonical ProjectState (spec 012a §6) so it exists before any page's
    widgets are drawn."""
    state = get_project_state()
    if not state.storage_widgets:
        sync_widget_defaults(_minimum_valid_state())
    if PROJECT_SESSION_KEY not in st.session_state:
        st.session_state[PROJECT_SESSION_KEY] = _build_project_from_session_state()


def render() -> None:
    state = get_project_state()
    # Shared "which page rendered last" marker (spec 014 §26-30) -- see
    # views/transfer.py's own use of this for why it exists: Transfer needs
    # to know whether it was the page active on the immediately preceding
    # script run, since any of its widgets not drawn that run get silently
    # reset by Streamlit to their declared defaults. Every page stamps its
    # own name here unconditionally, even when about to show its own
    # unconfigured guidance and return, so the marker always reflects the
    # truth by the time any other page's render() reads it.
    st.session_state["_last_active_page"] = "storage"

    # Unconfigured gate (spec 014 §5-§8, §47): the minimum-valid bootstrap
    # project (1 sample, blank name) always calculates successfully, but it
    # is not something the user has actually configured -- never present its
    # WGS-specific labels/figures as though it describes a real project.
    if not state.project_configured:
        with st.container(border=True, key="section_storage_unconfigured"):
            theme.section_header(1, "Storage")
            theme.callout(
                "Storage",
                'Configure a project to calculate storage requirements. Use "Edit project" '
                'or "Load Example" above to get started.',
            )
        return

    # Per-key healing every render (spec 012a §8), not a single one-time
    # flag: seeds minimum-valid defaults only for a genuinely new project
    # (state.storage_widgets empty), otherwise heals any individually-
    # missing widget key from the last canonical values so navigation can
    # never silently reset a configured project (spec 012a §2-§3).
    sync_widget_defaults(state.storage_widgets or _minimum_valid_state())

    _init_custom_datasets()
    _heal_custom_dataset_widgets(state.storage_widgets.get("custom_datasets"))

    theme.guided_flow_line(
        [
            ("1 Storage", "You are here"),
            ("2 Compute", STATUS_LABELS[compute_status(state)]),
            ("3 Transfer", STATUS_LABELS[transfer_status(state)]),
            ("4 Project Summary", "Overview"),
        ]
    )

    st.caption(
        "Early-stage planning and grant-budgeting tool for CBIO genomics projects. "
        "This is a planning estimate, not an AWS billing system."
    )

    pricing = _load_pricing()
    _, wgs_scenario_overlays = _load_profile_and_scenarios()

    # Project mode (spec 006 §1) is now project-level configuration, set by
    # the shared Project setup area (project_setup.py, spec 013a §19-§23),
    # which always renders earlier in the same script run (app.py). Storage
    # only reads the resulting canonical value.
    is_wgs_mode = st.session_state["project_mode"] == WGS_MODE

    # ---------------------------------------------------------------------------
    # Sensitive data and governance notice (spec 008) — informational only,
    # visible without opening an expander, in both modes; not a calculated value.
    # ---------------------------------------------------------------------------
    theme.callout(
        "Sensitive data and governance",
        "This calculator estimates infrastructure costs only. Genomic, phenotype and other "
        "sensitive research data should only be stored in cloud/object storage where this is "
        "permitted by the project's consent, ethics approvals, data-access agreements and "
        "applicable institutional policies. Storage location, access controls, encryption, audit "
        "logging, retention and data-transfer requirements should be reviewed before deployment. "
        "<strong>A cost estimate does not constitute approval to store project data in AWS.</strong>",
    )
    st.caption("Do not enter participant-level or other sensitive research data into this planning tool.")

    # ---------------------------------------------------------------------------
    # Data volume reference guide (spec 007) — documentation only, collapsed by
    # default, visible from both modes; never feeds calculations.
    # ---------------------------------------------------------------------------
    with st.expander("Data volume reference guide"):
        st.caption("Rough file-size estimates for common bioinformatics data types. Use measured project volumes where available.")
        theme.table(
            columns=["Data / format", "Rough planning size", "Notes"],
            rows=[[row["format"], row["size"], row["notes"]] for row in DATA_VOLUME_GUIDE],
            align=["left", "right", "left"],
        )
        st.caption(
            "**Planning estimates only.** Actual file sizes vary with sequencing platform, coverage, "
            "read length, compression, assay design, variant caller and processing pipeline. Where "
            "measured project volumes are available, use those instead."
        )

    # Project name/samples/retention are also project-level (spec 013a §24)
    # and are rendered by the shared Project setup area — Storage below
    # reads them via st.session_state as canonical values, same as before.

    # ---------------------------------------------------------------------------
    # 2. Project datasets (mode-dependent construction, spec 006 §1-§4)
    # ---------------------------------------------------------------------------
    with st.container(border=True, key="section_1"):
        if is_wgs_mode:
            theme.section_header(1, "WGS 30x data volume & movement")
            st.caption(
                "The WGS 30x profile already assumes 30x sequencing depth — per-sample volumes "
                "below already reflect that and are not scaled again."
            )
            st.caption(
                "The WGS 30x profile uses **100 GB FASTQ, 40 GB CRAM and 10 GB gVCF/QC per sample** "
                "as planning defaults. See the Data volume reference guide above for typical ranges."
            )
            with st.expander("Advanced WGS assumptions"):
                st.caption("Editable planning defaults, not measured data.")
                vol_cols = st.columns(3)
                for col, file_type in zip(vol_cols, WGS_FILE_TYPES):
                    with col:
                        st.number_input(
                            f"{file_type} GB/sample",
                            min_value=0.0,
                            step=1.0,
                            key=f"vol_{file_type}",
                        )
                st.number_input("Storage headroom (%)", min_value=0.0, step=1.0, key="headroom_percent")

                st.markdown("**FASTQ** — moves AWS S3 -> Ilifu for primary processing.")
                st.number_input("FASTQ processing passes", min_value=0.0, step=1.0, key="fastq_passes")

                st.markdown("**CRAM** — moves Ilifu -> S3; only a fraction are later retrieved.")
                mcol1, mcol2 = st.columns(2)
                with mcol1:
                    st.number_input(
                        "CRAM retrieval fraction (%)",
                        min_value=0.0,
                        max_value=100.0,
                        step=1.0,
                        key="cram_retrieval_percent",
                    )
                with mcol2:
                    st.number_input("CRAM retrieval passes", min_value=0.0, step=1.0, key="cram_retrieval_passes")

                st.markdown("**gVCF** — may move back to Ilifu for cohort joint calling.")
                st.number_input("gVCF processing/retrieval passes", min_value=0.0, step=1.0, key="gvcf_passes")

                st.caption(
                    "Data does not need to move to a separate bucket — the same S3 object key can "
                    "transition storage class via an S3 Lifecycle rule."
                )
                arc_cols = st.columns(3)
                for col, file_type in zip(arc_cols, WGS_FILE_TYPES):
                    with col:
                        st.selectbox(
                            f"{file_type} archive class",
                            options=list(STORAGE_CLASS_LABELS.keys()),
                            format_func=lambda k: STORAGE_CLASS_LABELS[k],
                            key=f"archive_{file_type}",
                        )

                st.number_input("Active S3 Standard period (months)", min_value=0.0, step=1.0, key="active_months")
        else:
            theme.section_header(1, "Custom Project datasets")
            st.caption(
                "Define one or more datasets and describe how each dataset will be stored and "
                "accessed. Use this mode for projects that do not yet have a predefined CBIO "
                "project profile."
            )
            ids = st.session_state["custom_dataset_ids"]
            for i, dataset_id in enumerate(ids):
                display_name = st.session_state.get(f"custom_name_{dataset_id}", "").strip()
                title = f"Dataset {i + 1} — {display_name}" if display_name else f"Dataset {i + 1}"
                with st.expander(title, expanded=(i == 0)):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.text_input("Dataset name", key=f"custom_name_{dataset_id}")
                    with col2:
                        st.selectbox("Unit", options=["GB", "TB"], key=f"custom_unit_{dataset_id}")

                    col3, col4 = st.columns(2)
                    with col3:
                        st.number_input(
                            "Size",
                            min_value=0.0,
                            step=1.0,
                            key=f"custom_size_{dataset_id}",
                            help=(
                                "Enter the total size of this dataset, not the size per sample. If "
                                "the actual volume is not known, use the Data volume reference guide "
                                "above as a rough planning estimate."
                            ),
                        )
                    with col4:
                        unit = st.session_state[f"custom_unit_{dataset_id}"]
                        size = _dec(st.session_state[f"custom_size_{dataset_id}"])
                        gb_value = size * GB_PER_TB if unit == "TB" else size
                        st.caption(f"{size:g} {unit} = {gb_value:,.0f} GB")

                    col5, col6 = st.columns(2)
                    with col5:
                        st.number_input(
                            "Retrieval (%)",
                            min_value=0.0,
                            max_value=100.0,
                            step=1.0,
                            key=f"custom_retrieval_{dataset_id}",
                            help=(
                                "Proportion of this dataset expected to be read from object "
                                "storage during one workflow pass. 100% = entire dataset is read; "
                                "0% = stored but not normally retrieved."
                            ),
                        )
                    with col6:
                        st.number_input(
                            "Read passes",
                            min_value=0.0,
                            step=1.0,
                            key=f"custom_passes_{dataset_id}",
                            help="How many times the selected retrieval fraction is expected to be read.",
                        )

                    col7, col8 = st.columns(2)
                    with col7:
                        st.number_input(
                            "Active storage duration (months)",
                            min_value=0.0,
                            step=1.0,
                            key=f"custom_active_months_{dataset_id}",
                            help="Months this dataset remains in S3 Standard before being archived.",
                        )
                    with col8:
                        st.selectbox(
                            "Archive class",
                            options=list(STORAGE_CLASS_LABELS.keys()),
                            format_func=lambda k: STORAGE_CLASS_LABELS[k],
                            key=f"custom_archive_{dataset_id}",
                        )

                    if i > 0:
                        st.button(
                            "Remove dataset",
                            key=f"custom_remove_{dataset_id}",
                            on_click=_remove_custom_dataset,
                            args=(dataset_id,),
                        )

            add_disabled = len(ids) >= CUSTOM_MAX_DATASETS
            st.button("+ Add dataset", on_click=_add_custom_dataset, disabled=add_disabled)
            if add_disabled:
                st.caption(f"Maximum of {CUSTOM_MAX_DATASETS} datasets reached.")

    # ---------------------------------------------------------------------------
    # 3. Data movement & transfer (project-level, shared by both modes)
    # ---------------------------------------------------------------------------
    with st.container(border=True, key="section_2"):
        theme.section_header(2, "Data movement & transfer")
        st.caption(
            "Data transferred into AWS: AWS internet data-transfer charge: $0. This does not "
            "mean S3 PUT/API requests are free — request and lifecycle-transition costs are "
            "modelled separately below."
        )
        st.markdown("**Transfer contingency** — covers reprocessing, failed/restarted transfers, workflow changes, QC.")
        st.number_input("Transfer contingency (%)", min_value=0.0, step=1.0, key="transfer_contingency_percent")
        theme.callout(
            "Key implication",
            "AWS-to-Ilifu transfer over the public internet can be a major project cost and "
            "may exceed storage costs.",
        )

    # ---------------------------------------------------------------------------
    # 4. Infrastructure engineering
    # ---------------------------------------------------------------------------
    with st.container(border=True, key="section_3"):
        theme.section_header(3, "Infrastructure engineering / management")
        _current_rate = st.session_state.get("hourly_rate_zar", 0)
        theme.callout(
            f"Illustrative engineering rate: R{_current_rate:,.0f}/hour",
            "Planning assumption only — not an approved UCT/CBIO institutional rate. "
            "Replace with an approved CBIO/UCT loaded technical staff rate.",
        )
        ecol1, ecol2, ecol3, ecol4 = st.columns(4)
        with ecol1:
            st.number_input("Onboarding hours", min_value=0.0, step=1.0, key="onboarding_hours")
        with ecol2:
            st.number_input("Operations hours/year", min_value=0.0, step=1.0, key="operations_hours_per_year")
        with ecol3:
            st.number_input("Closeout hours", min_value=0.0, step=1.0, key="closeout_hours")
        with ecol4:
            st.number_input("Hourly rate (ZAR)", min_value=0.0, step=50.0, key="hourly_rate_zar")

    # ---------------------------------------------------------------------------
    # 5. Ilifu compute
    # ---------------------------------------------------------------------------
    with st.container(border=True, key="section_4"):
        theme.section_header(4, "Ilifu compute")
        theme.callout(
            "Compute infrastructure cost not yet included",
            "Compute runtime and resource planning are available on the Compute page. "
            "Compute infrastructure cost / entitlement is not yet included in this total.",
        )
        st.caption(
            "Future versions should model project classes such as CBIO core, CBIO "
            "collaborative, external academic, and externally funded/service projects, "
            "with controls for fairshare weight, maximum concurrent jobs, CPU/GPU "
            "allocation, scratch quota, and turnaround expectations. No monetary compute "
            "charging is implemented yet. See the Compute page for the planned scope."
        )

    # ---------------------------------------------------------------------------
    # 6. Currency
    # ---------------------------------------------------------------------------
    with st.container(border=True, key="section_5"):
        theme.section_header(5, "Currency assumptions")
        ccol1, ccol2 = st.columns(2)
        with ccol1:
            st.number_input("USD/ZAR exchange rate", min_value=0.01, step=0.05, key="usd_zar")
        with ccol2:
            st.number_input("VAT (%)", min_value=0.0, step=1.0, key="vat_percent")
        st.caption("Exchange rate/VAT are illustrative defaults — confirm against an approved source before use.")

    # ---------------------------------------------------------------------------
    # Build inputs -> run calculation
    # ---------------------------------------------------------------------------

    try:
        computation = _recompute_estimate(state)
    except ValueError as exc:
        st.error(f"Invalid input: {exc}")
        st.stop()

    estimate = computation.estimate
    datasets = computation.datasets

    # Sensitivity scenarios (spec 006 §19): built from the *current* (possibly
    # edited) datasets, varying only movement behaviour and contingency.
    if is_wgs_mode:
        scenarios = {
            name: ScenarioAssumptions(
                datasets=cost_config.build_wgs_datasets(
                    computation.num_samples, computation.volumes, movement, computation.active_months
                ),
                transfer_contingency=contingency,
            )
            for name, (movement, contingency) in wgs_scenario_overlays.items()
        }
    else:
        scenario_multipliers = {"Low movement": Decimal("0.5"), "Expected": Decimal("1"), "High movement": Decimal("2")}
        scenarios = {
            name: ScenarioAssumptions(
                datasets=[replace(d, read_passes=d.read_passes * multiplier) for d in datasets],
                transfer_contingency=computation.transfer_contingency * multiplier,
            )
            for name, multiplier in scenario_multipliers.items()
        }
    scenario_estimates = build_scenarios(
        estimate.inputs, computation.engineering, pricing, computation.currency, scenarios
    )

    # ---------------------------------------------------------------------------
    # 7. Cost output
    # ---------------------------------------------------------------------------
    with st.container(border=True, key="section_6"):
        theme.section_header(6, "Cost summary")

        raw_tb = gb_to_tb(estimate.volume.raw_total_gb)
        envelope_tb = gb_to_tb(estimate.volume.envelope_gb)
        egress_tb = gb_to_tb(estimate.transfer.planned_egress_gb)

        scol1, scol2, scol3, scol4 = st.columns(4)
        scol1.metric("Datasets", str(len(estimate.datasets)))
        scol2.metric("Durable project data", f"{raw_tb:.1f} TB")
        scol3.metric("Provisioned envelope", f"{envelope_tb:.1f} TB")
        scol4.metric("Planned workflow egress", f"{egress_tb:.1f} TB")

        theme.headline(
            "Estimated infrastructure cost",
            f"R{estimate.grand_total_zar:,.0f}",
            "Storage • Transfer • Archive • Engineering — compute infrastructure cost not yet included",
        )

        st.markdown("**Dataset summary**")
        dataset_rows = [
            [
                d.name,
                f"{gb_to_tb(d.size_gb):.2f} TB" if d.size_gb >= GB_PER_TB else f"{d.size_gb:,.0f} GB",
                f"{d.retrieval_fraction * 100:.0f}%",
                f"{d.read_passes:g}",
                f"{d.active_months:g} mo",
                STORAGE_CLASS_LABELS.get(d.archive_class, d.archive_class),
            ]
            for d in estimate.datasets
        ]
        theme.table(
            columns=["Dataset", "Size", "Retrieval", "Passes", "Active", "Archive"],
            rows=dataset_rows,
            align=["left", "right", "right", "right", "right", "left"],
        )

        TOTAL_LABEL = "Total project infrastructure cost"
        table_rows: list[list[str]] = []
        table_row_classes: list[str | None] = []
        for item in estimate.line_items:
            table_rows.append([item.label, f"R{item.amount_zar:,.0f}", item.note])
            table_row_classes.append("gro-row-total" if item.label == TOTAL_LABEL else None)
        table_rows.append(
            ["Compute", "Not included", "Resource/runtime planning available on Compute page — cost not included"]
        )
        table_row_classes.append(None)

        theme.table(
            columns=["Cost component", "Cost (ZAR)", "Note"],
            rows=table_rows,
            align=["left", "right", "left"],
            row_class=table_row_classes,
        )

        ccol1, ccol2 = st.columns(2)
        ccol1.metric("Total AWS cost (USD)", f"${estimate.total_aws_usd:,.2f}")
        ccol2.metric("Total AWS cost (ZAR, ex VAT)", f"R{estimate.total_aws_zar_ex_vat:,.0f}")
        ccol3, ccol4 = st.columns(2)
        ccol3.metric("Total AWS cost (ZAR, incl. VAT)", f"R{estimate.total_aws_zar_inc_vat:,.0f}")
        ccol4.metric("Engineering cost (ZAR)", f"R{estimate.total_engineering_zar:,.0f}")

        chart_df = pd.DataFrame(
            {
                i.label: [float(i.amount_zar)]
                for i in estimate.line_items
                if i.label != "Total project infrastructure cost"
            }
        ).T
        chart_df.columns = ["ZAR"]
        st.bar_chart(chart_df, color=[theme.TEAL])

    # ---------------------------------------------------------------------------
    # 8. Sensitivity analysis
    # ---------------------------------------------------------------------------
    with st.container(border=True, key="section_7"):
        theme.section_header(7, "Sensitivity analysis")
        st.caption("Demonstrates that transfer behaviour can materially change total project cost.")

        sensitivity_rows: list[list[str]] = []
        sensitivity_row_classes: list[str | None] = []
        for name, est in scenario_estimates.items():
            storage_cost = next(i.amount_zar for i in est.line_items if i.label == "Active S3 storage")
            transfer_cost = next(i.amount_zar for i in est.line_items if i.label == "AWS to Ilifu transfer")
            archive_cost = next(i.amount_zar for i in est.line_items if i.label == "Archive storage")
            sensitivity_rows.append(
                [
                    name,
                    f"{gb_to_tb(est.transfer.planned_egress_gb):.2f} TB",
                    f"R{storage_cost:,.0f}",
                    f"R{transfer_cost:,.0f}",
                    f"R{archive_cost:,.0f}",
                    f"R{est.total_engineering_zar:,.0f}",
                    f"R{est.grand_total_zar:,.0f}",
                ]
            )
            sensitivity_row_classes.append("gro-row-emphasis" if name == "Expected" else None)

        theme.table(
            columns=[
                "Scenario",
                "Expected egress",
                "Storage (ZAR)",
                "Transfer (ZAR)",
                "Archive (ZAR)",
                "Engineering (ZAR)",
                "Total (ZAR)",
            ],
            rows=sensitivity_rows,
            align=["left", "right", "right", "right", "right", "right", "right"],
            row_class=sensitivity_row_classes,
        )

    # ---------------------------------------------------------------------------
    # 9. Explanation
    # ---------------------------------------------------------------------------
    with st.container(border=True, key="section_8"):
        theme.section_header(8, "Result explanation")
        theme.callout("Summary", estimate.explanation)

    # ---------------------------------------------------------------------------
    # Calculation details — kept outside any section panel (utility detail, not
    # a primary section; avoids nesting a card inside a card).
    # ---------------------------------------------------------------------------
    with st.expander("Calculation details"):
        st.subheader("Data volume")
        for line in estimate.volume.trace:
            st.text(f"{line.label}: {line.detail}")
        st.subheader("Data movement / transfer")
        for line in estimate.transfer.trace:
            st.text(f"{line.label}: {line.detail}")
        st.subheader("Storage cost")
        for line in estimate.storage.trace:
            st.text(f"{line.label}: {line.detail}")
        st.subheader("Engineering cost")
        for line in estimate.operations.trace:
            st.text(f"{line.label}: {line.detail}")
        st.subheader("Archive class details")
        for r in estimate.storage.datasets:
            st.markdown(f"**{r.name} — {STORAGE_CLASS_LABELS[r.archive_class]}**")
            st.text(r.retrieval_characteristics)
            if r.minimum_duration_warning:
                st.warning(r.minimum_duration_warning)

    # ---------------------------------------------------------------------------
    # 10. Pricing & assumptions
    # ---------------------------------------------------------------------------
    with st.container(border=True, key="section_9"):
        theme.section_header(9, "Pricing & assumptions")
        st.markdown(
            "AWS storage, request, archive retrieval and data-transfer costs are based on "
            "published AWS pricing for the Africa (Cape Town) region (`af-south-1`). Prices "
            "are planning estimates and should be verified against current AWS/UCT pricing "
            "before budgeting or procurement."
        )

        pcol1, pcol2, pcol3 = st.columns(3)
        with pcol1:
            st.markdown(f"**AWS pricing source:**  \n[{pricing.pricing_source}]({pricing.pricing_source})")
        with pcol2:
            st.markdown(f"**AWS region:**  \n{pricing.region_name} — `{pricing.region}`")
        with pcol3:
            st.markdown(f"**Pricing last verified:**  \n{pricing.pricing_last_verified}")

        st.caption(
            "Data volumes, workflow data movement, retention periods, exchange rate, VAT and "
            "engineering effort are configurable planning assumptions. Compute runtime and "
            "resource planning are available on the Compute page; compute infrastructure cost "
            "is not yet included in this total."
        )

        acol1, acol2 = st.columns(2)
        with acol1:
            st.markdown(
                "**Published AWS pricing**\n"
                "- S3 Standard storage price\n"
                "- Glacier storage prices\n"
                "- Request charges\n"
                "- Retrieval charges\n"
                "- Internet data-transfer charges"
            )
        with acol2:
            st.markdown(
                "**CBIO/project planning assumptions**\n"
                "- Dataset sizes, retrieval %, read passes\n"
                "- Active & archive storage duration per dataset\n"
                "- Archive class selection\n"
                "- Transfer contingency\n"
                "- Exchange rate, VAT\n"
                "- Engineering hours & hourly rate"
            )

    # ---------------------------------------------------------------------------
    # 11. Export
    # ---------------------------------------------------------------------------
    with st.container(border=True, key="section_10"):
        theme.section_header(10, "Export")
        excol1, excol2, excol3 = st.columns(3)
        with excol1:
            st.download_button(
                "Download CSV",
                data=cost_export.to_csv(estimate, pricing),
                file_name=f"{estimate.inputs.project_name.replace(' ', '_')}_cost_estimate.csv",
                mime="text/csv",
            )
        with excol2:
            st.download_button(
                "Download JSON",
                data=cost_export.to_json(estimate, pricing),
                file_name=f"{estimate.inputs.project_name.replace(' ', '_')}_cost_estimate.json",
                mime="application/json",
            )
        with excol3:
            st.download_button(
                "Download Markdown summary",
                data=cost_export.to_markdown(estimate, pricing),
                file_name=f"{estimate.inputs.project_name.replace(' ', '_')}_cost_estimate.md",
                mime="text/markdown",
            )

    # Convenience forward action (spec 012c §21) — a deferred, function-
    # local import is required to avoid a circular import with navigation.py
    # (see that module's docstring). Using the top navigation instead
    # behaves identically; this link is never required for state
    # persistence.
    from navigation import COMPUTE_PAGE

    st.page_link(COMPUTE_PAGE, label="Continue to Compute →")

    theme.disclaimer(
        "Prototype planning tool — estimates should be validated before budgeting or procurement.",
        "Actual costs may vary with AWS pricing, exchange rates, data volumes, access "
        "patterns, network path, retrieval behaviour and institutional agreements.",
    )
