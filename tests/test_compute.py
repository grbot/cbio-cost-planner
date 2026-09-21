"""Unit tests for the Compute calculation engine (spec 011 §32; effective-vs-
configured concurrency, spec 011b §12).

Deterministic, no Streamlit dependency — mirrors tests/test_calculator.py's
style. Pins the exact worked examples from spec 011 §14/§32 and spec 011b
§2-§4.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from cbio_cost import compute_benchmarks as bm
from cbio_cost import export as cost_export
from cbio_cost.compute import (
    build_compute_result,
    concurrency_result,
    working_storage_result,
)
from cbio_cost.compute_models import ComputeConfig

# 1. Worker-hours (spec 011 §14, §32) ----------------------------------------


def test_bwa_worker_hours():
    result = concurrency_result(
        "BWA-MEM2 + sort", 500, 10, Decimal("4.945"), bm.BWA_RUNTIME_EVIDENCE, "benchmark"
    )
    assert result.worker_hours == Decimal("2472.5")


# 2-3. Concurrency waves/elapsed (spec 011 §14, §32) -------------------------


def test_concurrency_10_workers():
    result = concurrency_result(
        "BWA-MEM2 + sort", 500, 10, Decimal("4.945"), bm.BWA_RUNTIME_EVIDENCE, "benchmark"
    )
    assert result.waves == 50
    assert result.idealised_elapsed_hours == Decimal("247.25")


def test_concurrency_50_workers():
    result = concurrency_result(
        "BWA-MEM2 + sort", 500, 50, Decimal("4.945"), bm.BWA_RUNTIME_EVIDENCE, "benchmark"
    )
    assert result.waves == 10
    assert result.idealised_elapsed_hours == Decimal("49.45")


# Effective vs configured concurrency (spec 011b §2-§3, §12 items 1-3) -------


def test_effective_concurrency_capped_by_sample_count():
    """Only one per-sample task can run at once per sample — configured
    capacity beyond the sample count cannot be active."""
    result = concurrency_result(
        "BWA-MEM2 + sort", 1, 10, Decimal("4.945"), bm.BWA_RUNTIME_EVIDENCE, "benchmark"
    )
    assert result.configured_concurrency == 10
    assert result.effective_concurrency == 1
    assert result.waves == 1
    assert result.idealised_elapsed_hours == Decimal("4.945")


def test_effective_concurrency_equals_configured_when_samples_match():
    result = concurrency_result(
        "BWA-MEM2 + sort", 10, 10, Decimal("4.945"), bm.BWA_RUNTIME_EVIDENCE, "benchmark"
    )
    assert result.effective_concurrency == 10


def test_effective_concurrency_equals_configured_when_samples_exceed():
    result = concurrency_result(
        "BWA-MEM2 + sort", 500, 10, Decimal("4.945"), bm.BWA_RUNTIME_EVIDENCE, "benchmark"
    )
    assert result.configured_concurrency == 10
    assert result.effective_concurrency == 10


def test_worker_hours_independent_of_concurrency():
    low = concurrency_result("BWA-MEM2 + sort", 500, 10, Decimal("4.945"), bm.BWA_RUNTIME_EVIDENCE, "benchmark")
    high = concurrency_result("BWA-MEM2 + sort", 500, 50, Decimal("4.945"), bm.BWA_RUNTIME_EVIDENCE, "benchmark")
    assert low.worker_hours == high.worker_hours == Decimal("2472.5")


# 4. Scratch — stage-specific peak, effective concurrency (spec 011a §12; spec 011b §4, §12 items 4-5, 7) --


def test_scratch_working_storage_stage_specific_peak():
    result = working_storage_result(Decimal(250), 500, alignment_configured_concurrency=10, deepvariant_configured_concurrency=20)
    assert result.alignment_peak_gib == Decimal(2500)
    assert result.deepvariant_peak_gib == Decimal(5000)
    # max(2500, 5000), not their sum (7500), under the sequential-stage model.
    assert result.peak_simultaneous_gib == Decimal(5000)


def test_working_storage_unequal_stage_concurrency():
    """spec 011b §4 worked example: 20 samples, 2 alignment workers, 3
    DeepVariant workers, 250 GiB/worker."""
    result = working_storage_result(Decimal(250), 20, alignment_configured_concurrency=2, deepvariant_configured_concurrency=3)
    assert result.alignment_peak_gib == Decimal(500)
    assert result.deepvariant_peak_gib == Decimal(750)
    assert result.peak_simultaneous_gib == Decimal(750)


def test_working_storage_capacity_exceeds_small_project():
    """spec 011b §4 worked example: 2 samples, 10/20 configured workers —
    effective concurrency is capped at 2 for both stages."""
    result = working_storage_result(Decimal(250), 2, alignment_configured_concurrency=10, deepvariant_configured_concurrency=20)
    assert result.alignment_effective_concurrency == 2
    assert result.deepvariant_effective_concurrency == 2
    assert result.alignment_peak_gib == Decimal(500)
    assert result.deepvariant_peak_gib == Decimal(500)
    assert result.peak_simultaneous_gib == Decimal(500)


def test_working_storage_one_sample_default_project():
    """spec 011b §4 worked example: the minimum-valid 1-sample project with
    default 10/10 configured workers must show 250 GiB, not 2,500 GiB."""
    result = working_storage_result(Decimal(250), 1, alignment_configured_concurrency=10, deepvariant_configured_concurrency=10)
    assert result.alignment_peak_gib == Decimal(250)
    assert result.deepvariant_peak_gib == Decimal(250)
    assert result.peak_simultaneous_gib == Decimal(250)


def test_scratch_result_unchanged_for_500_sample_regression():
    """min(500, 10) == 10, so the existing 500-sample/10-worker scratch
    figure must remain exactly what it was before spec 011b."""
    result = working_storage_result(Decimal(250), 500, alignment_configured_concurrency=10, deepvariant_configured_concurrency=10)
    assert result.alignment_peak_gib == Decimal(2500)
    assert result.peak_simultaneous_gib == Decimal(2500)


# 5. Evidence separation (spec 011 §11, §36) ---------------------------------


def test_evidence_classification_separation():
    config = ComputeConfig(alignment_concurrency=10, deepvariant_concurrency=10, scratch_gib_per_worker=Decimal(250))
    result = build_compute_result(500, config, Decimal("16.05"))
    alignment_stage = next(s for s in result.stages if s.name == "BWA-MEM2 + sort")

    assert alignment_stage.evidence["cpu"].classification == "measured"
    assert alignment_stage.evidence["memory"].classification == "planning_assumption"
    assert alignment_stage.evidence["measured_peak_memory"].classification == "measured"

    planning_ram = alignment_stage.memory_gib
    measured_peak_ram = Decimal(alignment_stage.evidence["measured_peak_memory"].value.split(" ")[0])
    assert planning_ram == Decimal(160)
    assert measured_peak_ram != planning_ram
    assert measured_peak_ram == pytest.approx(Decimal("116.7"), abs=Decimal("0.1"))


# 6. Derived-value traceability (spec 011 §4) --------------------------------


def test_bwa_derived_values_traceable():
    assert bm.BWA_CPU_CORE_HOURS == pytest.approx(Decimal("68.1"), abs=Decimal("0.1"))
    assert bm.BWA_PEAK_RAM_GIB == pytest.approx(Decimal("116.7"), abs=Decimal("0.1"))
    assert bm.BWA_WALL_TIME_HOURS == Decimal("4.945")


# 7. GLnexus excluded, CRAM index included (spec 011 §9; spec 011a §8-§9) ----


def test_glnexus_excluded_from_total():
    config = ComputeConfig(alignment_concurrency=10, deepvariant_concurrency=10, scratch_gib_per_worker=Decimal(250))
    result = build_compute_result(500, config, Decimal("16.05"))

    assert result.glnexus.included_in_total is False
    assert result.glnexus.runtime_hours is None
    assert result.excluded_stages == ["GLnexus (cohort joint calling)"]


def test_cram_index_included_in_total():
    config = ComputeConfig(alignment_concurrency=10, deepvariant_concurrency=10, scratch_gib_per_worker=Decimal(250))
    result = build_compute_result(500, config, Decimal("16.05"))

    cram_index_stage = next(s for s in result.stages if s.name == "CRAM index")
    assert cram_index_stage.included_in_total is True
    # CRAM index shares the alignment stage's configured concurrency.
    assert result.cram_index.configured_concurrency == config.alignment_concurrency

    expected = (
        result.alignment.idealised_elapsed_hours
        + result.cram_index.idealised_elapsed_hours
        + result.deepvariant.idealised_elapsed_hours
    )
    assert result.known_modelled_elapsed_hours == expected
    # Not just alignment + DeepVariant — CRAM index must actually contribute.
    assert result.known_modelled_elapsed_hours != (
        result.alignment.idealised_elapsed_hours + result.deepvariant.idealised_elapsed_hours
    )


def test_cram_index_shares_alignment_effective_concurrency():
    """spec 011b §12 item 6: for a small project where configured
    concurrency exceeds sample count, CRAM index's effective concurrency
    must match the alignment stage's, not the raw configured value."""
    config = ComputeConfig(alignment_concurrency=10, deepvariant_concurrency=10, scratch_gib_per_worker=Decimal(250))
    result = build_compute_result(1, config, Decimal("16.05"))

    assert result.alignment.effective_concurrency == 1
    assert result.cram_index.effective_concurrency == result.alignment.effective_concurrency == 1


# 8. Runtime override (spec 011 §17) -----------------------------------------


def test_alignment_runtime_override_basis():
    config = ComputeConfig(
        alignment_concurrency=10,
        deepvariant_concurrency=10,
        scratch_gib_per_worker=Decimal(250),
        alignment_runtime_override_hours=Decimal("3.5"),
    )
    result = build_compute_result(500, config, Decimal("16.05"))

    assert result.alignment.runtime_basis == "user_override"
    assert result.alignment.runtime_per_unit_hours == Decimal("3.5")
    assert result.alignment.idealised_elapsed_hours == Decimal(50) * Decimal("3.5")
    # Original benchmark evidence must still be retrievable for reference.
    assert result.alignment.runtime_evidence.classification == "measured"
    assert result.alignment.runtime_evidence.value == f"{bm.BWA_WALL_TIME_HOURS} h/sample"


# Exports expose configured and effective concurrency separately (spec 011b §11-§12 item 12) --


def test_compute_export_includes_configured_and_effective_concurrency():
    config = ComputeConfig(alignment_concurrency=10, deepvariant_concurrency=10, scratch_gib_per_worker=Decimal(250))
    result = build_compute_result(1, config, Decimal("16.05"))

    payload = cost_export.compute_to_json("Test project", 1, result)
    data = json.loads(payload)

    assert data["configured_alignment_workers"] == 10
    assert data["effective_alignment_concurrency"] == 1
    assert data["configured_deepvariant_workers"] == 10
    assert data["effective_deepvariant_concurrency"] == 1
    assert data["alignment"]["configured_concurrency"] == 10
    assert data["alignment"]["effective_concurrency"] == 1
    assert data["working_storage"]["alignment_configured_concurrency"] == 10
    assert data["working_storage"]["alignment_effective_concurrency"] == 1


# Existing regression (spec 011 §32) -----------------------------------------
# tests/test_calculator.py's 500x30x regression builds inputs from the YAML
# profile directly (not Streamlit session state), so it is unaffected by the
# spec 011a §2 default-project-state change. See tests/test_project.py for
# the minimum-valid-project-state and session-state-bootstrap tests (spec
# 011a §2-§3).
