"""Structural regression test for the responsive workflow diagram (spec 011b §6).

Doesn't render a real browser — asserts the generated HTML groups each
step's incoming arrow together with its box in one wrapper, which is what
prevents flexbox from wrapping an arrow away from the box it points to.
"""

from __future__ import annotations

import theme


def test_process_diagram_keeps_arrow_attached_to_its_box(monkeypatch):
    captured: dict[str, str] = {}

    def fake_markdown(html, unsafe_allow_html=False):
        captured["html"] = html

    monkeypatch.setattr(theme.st, "markdown", fake_markdown)

    theme.process_diagram(["FASTQ", "BWA-MEM2", "cohort VCF"])

    html = captured["html"]
    steps = html.split('<div class="gro-diagram-step">')[1:]

    assert len(steps) == 3
    # First step has no incoming arrow.
    assert "gro-diagram-arrow" not in steps[0]
    assert "gro-diagram-box" in steps[0]

    # Every later step's arrow is nested inside the same wrapper as, and
    # precedes, its box — so wrapping can never separate them.
    for step_html in steps[1:]:
        arrow_index = step_html.find("gro-diagram-arrow")
        box_index = step_html.find("gro-diagram-box")
        assert arrow_index != -1
        assert box_index != -1
        assert arrow_index < box_index
