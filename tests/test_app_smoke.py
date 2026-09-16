"""App-level smoke test (spec 010 §18: confirm the application starts).

``st.navigation`` pages built from callables (as used in ``app.py``) don't
expose a real script path for ``AppTest.switch_page`` to target in this
Streamlit version, so this only exercises the default (Storage) page — the
one most at risk of regressing, since it does all the calculation. Compute,
Transfer and Project Summary are verified by running the app manually.
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"


def test_app_starts_and_renders_default_storage_page():
    at = AppTest.from_file(str(APP_PATH), default_timeout=30)
    at.run()
    assert not at.exception
    assert at.title[0].value == "CBIO Genomics Infrastructure Cost Planner"
