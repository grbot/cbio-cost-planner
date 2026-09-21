"""Unit tests for the Compute calculation engine (spec 011 §32).

Deterministic, no Streamlit dependency — mirrors tests/test_calculator.py's
style. Pins the exact worked examples from spec 011 §14/§32.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from cbio_cost import compute_benchmarks as bm
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


# 4. Scratch — stage-specific peak (spec 011a §12, §28) ----------------------


def test_scratch_working_storage_stage_specific_peak():
    result = working_storage_result(Decimal(250), alignment_concurrency=10, deepvariant_concurrency=20)
    assert result.alignment_peak_gib == Decimal(2500)
    assert result.deepvariant_peak_gib == Decimal(5000)
    # max(2500, 5000), not their sum (7500), under the sequential-stage model.
    assert result.peak_simultaneous_gib == Decimal(5000)


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
    # CRAM index shares the alignment stage's concurrency.
    assert result.cram_index.concurrency == config.alignment_concurrency

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


# Existing regression (spec 011 §32) -----------------------------------------
# tests/test_calculator.py's 500x30x regression builds inputs from the YAML
# profile directly (not Streamlit session state), so it is unaffected by the
# spec 011a §2 default-project-state change. See tests/test_project.py for
# the minimum-valid-project-state and session-state-bootstrap tests (spec
# 011a §2-§3).
