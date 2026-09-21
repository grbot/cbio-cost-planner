"""Shared, cross-module project model (spec 010 §4).

Storage, Compute and Transfer are different infrastructure dimensions of
one genomics project. This module holds the project-level representation
that is built once (by Storage, today) and can be read by other modules
(Project Summary, Compute, Transfer) instead of each module independently
re-asking for the same project information.

This is deliberately minimal: it wraps the existing ``ProjectInputs``/
``Dataset``/``CostEstimate`` types from ``cbio_cost.models`` rather than
introducing a parallel representation. Compute configuration/results are
modelled (spec 011/011a, via ``compute_config``/``compute_result``) and
Transfer configuration/results are modelled (spec 012, via
``transfer_config``/``transfer_result``) below.

``build_project()`` (spec 013 §2, §8, §40-41) is the single, pure way to
obtain a ``Project`` — it derives every field straight from the canonical
``cbio_cost.project_state.ProjectState``, never from a previously-cached
``Project`` object. This replaced an earlier incremental-mutation pattern
(``Project.from_storage()`` + ``with_compute()``/``with_transfer()``) that
had a real, reproduced bug: ``from_storage()`` bare-constructed a fresh
``Project`` on every Storage render, discarding whatever
``compute_result``/``transfer_result`` a prior render had attached — so
navigating Storage → Project Summary (skipping Compute/Transfer) made
Summary wrongly hide fully current, valid Compute/Transfer results even
though the flow-indicator line on the same page (driven by
``ProjectState`` directly) still correctly reported them ``Complete``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

from cbio_cost.compute_models import ComputeConfig, ComputeResult
from cbio_cost.models import CostEstimate, Dataset
from cbio_cost.transfer_plan_models import TransferPlan, TransferPlanResult

if TYPE_CHECKING:
    from cbio_cost.project_state import ProjectState

PROJECT_SESSION_KEY = "project"


@dataclass
class ProjectMetadata:
    """Identity of one genomics project, independent of any single module."""

    name: str
    project_type: str
    num_samples: int | None
    retention_years: Decimal


@dataclass
class Project:
    """One genomics project shared across Storage, Compute and Transfer.

    ``storage_estimate`` is populated once the Storage module has computed a
    result; it is ``None`` until then. ``compute_config``/``compute_result``
    are populated once the Compute module has run (spec 011/011a);
    ``transfer_config``/``transfer_result`` once the Transfer module has run
    (spec 012). Each pair is ``None`` until its module has run.
    """

    metadata: ProjectMetadata
    datasets: list[Dataset] = field(default_factory=list)
    storage_estimate: CostEstimate | None = None
    compute_config: ComputeConfig | None = None
    compute_result: ComputeResult | None = None
    transfer_config: TransferPlan | None = None
    transfer_result: TransferPlanResult | None = None


def build_project(state: "ProjectState") -> Project | None:
    """The one way to obtain a ``Project`` (spec 013 §2, §8, §40-41): a pure,
    total projection of canonical ``ProjectState``, safe to call from any
    page's ``render()`` in any navigation order. ``None`` before Storage has
    ever computed a result (canonical state genuinely has nothing to show
    yet)."""
    if state.storage_result is None:
        return None
    inputs = state.storage_result.inputs
    metadata = ProjectMetadata(
        name=inputs.project_name,
        project_type=inputs.project_type,
        num_samples=inputs.num_samples,
        retention_years=inputs.retention_years,
    )
    return Project(
        metadata=metadata,
        datasets=state.storage_result.datasets,
        storage_estimate=state.storage_result,
        compute_config=state.compute_config,
        compute_result=state.compute_result,
        transfer_config=state.transfer_config,
        transfer_result=state.transfer_result,
    )
