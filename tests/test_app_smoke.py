"""App-level smoke test (spec 010 §18: confirm the application starts).

``st.navigation`` pages built from callables (as used in ``app.py``) don't
expose a real script path for ``AppTest.switch_page`` to target in this
Streamlit version, so this only exercises the default (Storage) page — the
one most at risk of regressing, since it does all the calculation. Compute,
Transfer and Project Summary are verified by running the app manually (and
via the ``views.*.render()``-sequencing tests in ``tests/
test_state_navigation.py``, which exercise all four pages directly).

Since spec 012c, ``app.py`` sources its ``st.Page`` objects from
``navigation.py`` instead of inlining them — this test re-executes the
whole import chain fresh via ``AppTest.from_file``, so it also catches any
import-order/circularity mistake in that refactor (``navigation.py``
imports the view render callables at load time; views must only import
``navigation`` back via a function-local import inside ``render()``).
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"


def test_app_starts_and_renders_default_storage_page():
    """spec 014 §5-§8, §76: a brand-new session is genuinely unconfigured --
    Storage must show its "Configure a project..." guidance, not a full
    calculator for a project nobody set up (the pre-014 defect). This still
    exercises the real import/render chain (AppTest, not bare-mode), so it
    keeps catching any import-order/circularity mistake per this module's
    original purpose -- only the expected page content changed."""
    at = AppTest.from_file(str(APP_PATH), default_timeout=30)
    at.run()
    assert not at.exception
    # The branding header (spec 010a) is raw HTML via theme.header(), not a
    # real st.title element, so look for it in the rendered markdown instead.
    assert any("CBIO" in md.value for md in at.markdown)
    # Fresh/unconfigured: no calculator, no "Continue to Compute →" link --
    # just the guidance callout.
    assert any("Configure a project" in md.value for md in at.markdown)
    assert len(at.get("page_link")) == 0

    # Loading the demo profile (the shared Project setup area's "Load
    # Example" button) must produce the real calculator, including the
    # forward "Continue to Compute →" page_link (spec 012c §21).
    at.button(key="load_demo_button").click().run()
    assert not at.exception
    assert len(at.get("page_link")) == 1
