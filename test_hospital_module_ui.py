from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parent


def _hospital_page() -> AppTest:
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120).run()
    app.switch_page("app_pages/hospital_vulnerability.py").run()
    assert not app.exception
    return app


def _headings(app: AppTest) -> list[str]:
    return [element.value for element in app.subheader]


def test_hospital_page_map_is_first_and_only_selected_analysis_is_rendered():
    app = _hospital_page()
    assert _headings(app)[0] == "Hospital Map"
    assert app.radio[0].value == "Accessibility"
    assert "Hospital Accessibility" in _headings(app)
    assert "Hospital Vulnerability" not in _headings(app)
    assert "Hospital Availability" not in _headings(app)

    app.radio[0].set_value("Vulnerability").run()
    assert not app.exception
    assert _headings(app)[0] == "Hospital Map"
    assert "Hospital Vulnerability" in _headings(app)
    assert "Hospital Accessibility" not in _headings(app)
    assert "Hospital Availability" not in _headings(app)

    app.radio[0].set_value("Availability").run()
    assert not app.exception
    assert _headings(app)[0] == "Hospital Map"
    assert "Hospital Availability" in _headings(app)
    assert "Hospital Accessibility" not in _headings(app)
    assert "Hospital Vulnerability" not in _headings(app)


def test_disaster_selector_updates_the_active_hospital_assessment():
    app = _hospital_page()
    app.radio[0].set_value("Availability").run()
    disaster_selector = next(widget for widget in app.selectbox if widget.label == "Disaster type")
    disaster_selector.select("Cyclones").run()
    assert not app.exception
    assert app.radio[0].value == "Availability"
    assert "Hospital Availability" in _headings(app)
    assert "Predicted operational condition: Unknown" in "\n".join(
        element.value for element in app.markdown
    )
