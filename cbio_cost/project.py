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
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import Decimal

from cbio_cost.compute_models import ComputeConfig, ComputeResult
from cbio_cost.models import CostEstimate, Dataset, ProjectInputs
from cbio_cost.transfer_plan_models import TransferPlan, TransferPlanResult

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

    @classmethod
    def from_storage(
        cls, inputs: ProjectInputs, datasets: list[Dataset], estimate: CostEstimate
    ) -> "Project":
        """Build the shared project from a completed Storage calculation.

        Wraps the already-computed inputs/datasets/estimate; performs no
        calculation of its own.
        """
        return cls(
            metadata=ProjectMetadata(
                name=inputs.project_name,
                project_type=inputs.project_type,
                num_samples=inputs.num_samples,
                retention_years=inputs.retention_years,
            ),
            datasets=datasets,
            storage_estimate=estimate,
        )

    def with_compute(self, config: ComputeConfig, result: ComputeResult) -> "Project":
        """Attach a completed Compute calculation (spec 011) without
        recomputing Storage."""
        return replace(self, compute_config=config, compute_result=result)

    def with_transfer(self, config: TransferPlan, result: TransferPlanResult) -> "Project":
        """Attach a completed Transfer calculation (spec 012) without
        recomputing Storage or Compute."""
        return replace(self, transfer_config=config, transfer_result=result)
