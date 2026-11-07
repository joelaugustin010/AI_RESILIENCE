"""Streamlit smoke test for the independent model validation gate."""
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


def test_hazard_model_lab_displays_independent_validation_gate():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90).run()
    assert not app.exception
    app.switch_page("app_pages/hazard_model_lab.py").run()
    assert not app.exception
    rendered = "\n".join(item.value for item in app.markdown)
    rendered += "\n" + "\n".join(item.value for item in app.caption)
    rendered += "\n" + "\n".join(item.label for item in app.metric)
    assert "independent validation gate" in rendered.casefold()
    assert any("Models passing independent validation gate" in item.label for item in app.metric)
