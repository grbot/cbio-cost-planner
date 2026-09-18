"""Provenance/evidence model for Compute assumptions and benchmarks (spec 011 §2-§3).

Every significant Compute figure must be traceable to one of four evidence
classes. This module holds that structured record so classification is part
of the internal model, not only explanatory UI text (spec 011 §2, last line).
"""

from __future__ import annotations

from dataclasses import dataclass

EVIDENCE_LABELS: dict[str, str] = {
    "measured": "Measured — CBIO/Ilifu",
    "published_benchmark": "Published benchmark",
    "planning_assumption": "Planning assumption",
    "local_commercial_assumption": "Local commercial assumption",
}


@dataclass
class Evidence:
    """One traceable provenance record for a Compute figure (spec 011 §3)."""

    classification: str
    source: str
    date: str
    value: str
    notes: str = ""
    label: str = ""

    def __post_init__(self) -> None:
        if self.classification not in EVIDENCE_LABELS:
            raise ValueError(f"Unknown evidence classification '{self.classification}'")
        if not self.label:
            self.label = EVIDENCE_LABELS[self.classification]
