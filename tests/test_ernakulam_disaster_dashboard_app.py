"""Streamlit end-to-end checks for Simple and Advanced prediction modes."""

from pathlib import Path

import pytest


streamlit_testing = pytest.importorskip("streamlit.testing.v1")
AppTest = streamlit_testing.AppTest
PAGE_PATH = Path(__file__).resolve().parents[1] / "app_pages" / "disaster_probability.py"


def _rendered_text(app):
    collections = (
        app.title,
        app.header,
        app.subheader,
        app.markdown,
        app.caption,
        app.error,
        app.metric,
        app.info,
        app.warning,
        app.number_input,
        app.text_input,
        app.selectbox,
        app.radio,
        app.date_input,
        app.time_input,
        app.expander,
    )
    displayed = []
    for collection in collections:
        for element in collection:
            for attribute in ("value", "label"):
                value = getattr(element, attribute, None)
                if isinstance(value, (str, int, float)):
                    displayed.append(str(value))
    return "\n".join(displayed)


def _select_hazard(app, hazard_id):
    if not any(getattr(element, "key", None) == "selected_disaster_hazard" for element in app.selectbox):
        return False
    app.selectbox(key="selected_disaster_hazard").set_value(hazard_id).run()
    return True


def _assert_unavailable_gate(app):
    text = _rendered_text(app)
    assert "No hazard currently passes the verified data and model-readiness gates" in text
    assert "Probability prediction is unavailable" in text


def _fill_simple_answers(app, hazard_id):
    answers = {
        "flood": {
            "simple_rain": "Heavy",
            "simple_water_rising": "I don't know",
            "simple_water_collecting": "Across roads or near homes",
            "simple_duration": "1–3 hours",
        },
        "cyclone": {
            "simple_wind": "Strong",
            "simple_weather": "Humid",
            "simple_storm_warning": "I heard an official warning",
        },
        "landslide": {
            "simple_ground": "Wet",
            "simple_slope_signs": "No",
            "simple_unusual_changes": "Yes",
        },
        "drought": {
            "simple_recent_rainfall": "Less than usual",
            "simple_water_shortage": "Some shortage",
        },
    }[hazard_id]
    for key, answer in answers.items():
        app.selectbox(key=key).set_value(answer)


def _assert_shared_results(text, hazard_label):
    assert hazard_label in text
    assert "Assessment results" in text
    assert "Preliminary rule-based assessment" in text
    assert "Risk category" in text
    assert "Insufficient validated data" in text
    assert "Important missing information" in text
    assert "Precautions:" in text
    assert "Percentage cards are shown only for validated, calibrated model outputs." in text
    assert "10.0%" not in text


@pytest.mark.parametrize(
    ("hazard_id", "hazard_label"),
    [
        ("flood", "Flood and Urban Waterlogging"),
        ("cyclone", "Cyclone and Coastal Storm Impacts"),
        ("landslide", "Landslide"),
        ("drought", "Drought and Water Scarcity"),
    ],
)
def test_simple_mode_submits_and_displays_selected_hazard(hazard_id, hazard_label):
    app = AppTest.from_file(str(PAGE_PATH), default_timeout=30).run()
    assert not app.exception
    if not _select_hazard(app, hazard_id):
        _assert_unavailable_gate(app)
        return
    _fill_simple_answers(app, hazard_id)
    app.button[0].click().run()
    assert not app.exception
    _assert_shared_results(_rendered_text(app), hazard_label)


def test_advanced_mode_uses_optional_scientific_measurements_and_shared_results():
    app = AppTest.from_file(str(PAGE_PATH), default_timeout=30).run()
    if not app.radio:
        _assert_unavailable_gate(app)
        return
    app.radio[0].set_value("ADVANCED MODE").run()
    assert not app.exception

    text = _rendered_text(app)
    assert "Rainfall intensity (mm/hour)" in text
    assert "Accumulated rainfall, past 24 hours (mm)" in text
    assert "Forecast rainfall, next 24 hours (mm)" in text
    assert len(app.number_input) > 0

    app.button[0].click().run()
    assert not app.exception

    text = _rendered_text(app)
    _assert_shared_results(text, "Flood and Urban Waterlogging")
    assert "Percentage cards are shown only for validated, calibrated model outputs." in text
    assert "Live weather and warning feeds are not connected" in text


def test_simple_mode_requires_an_explicit_answer_for_each_question():
    app = AppTest.from_file(str(PAGE_PATH), default_timeout=30).run()
    if not app.button:
        _assert_unavailable_gate(app)
        return
    app.button[0].click().run()
    assert not app.exception

    text = _rendered_text(app)
    assert "Choose an answer for: How is the rain in your area?" in text
    assert "preliminary risk category" not in text.lower()


def test_advanced_mode_requires_reference_when_water_level_is_entered():
    app = AppTest.from_file(str(PAGE_PATH), default_timeout=30).run()
    if not app.radio:
        _assert_unavailable_gate(app)
        return
    app.radio[0].set_value("ADVANCED MODE").run()
    app.number_input(key="advanced_water_level_m").set_value(1.4)
    app.button[0].click().run()
    assert not app.exception

    text = _rendered_text(app)
    assert "Name the monitoring station and measurement datum/reference" in text
    assert "Prediction unavailable" not in text
