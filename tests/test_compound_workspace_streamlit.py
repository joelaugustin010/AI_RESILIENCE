"""Streamlit acceptance tests for the all-hazard compound workspace."""
from streamlit.testing.v1 import AppTest

from src.hazard_registry import WORKFLOW_HAZARDS


def test_compound_workspace_renders_all_ten_registered_hazards_and_source_tracks():
    app = AppTest.from_file(
        "app_pages/compound_scenario.py", default_timeout=90
    ).run()
    assert not app.exception
    assert any(
        item.value == "Kochi Multi-Hazard Resilience Workspace"
        for item in app.title
    )
    assert len(app.multiselect) >= 1
    assert set(app.multiselect[0].options) == set(WORKFLOW_HAZARDS)

    app.multiselect[0].set_value(list(WORKFLOW_HAZARDS))
    app.form_submit_button[0].click().run()
    assert not app.exception

    expander_labels = [str(item.label) for item in app.expander]
    assert any("Flood inundation and impacts" in label for label in expander_labels)
    assert any("Landslide event inventory" in label for label in expander_labels)
    assert any("Industrial incident" in label for label in expander_labels)
    assert any("Infrastructure condition" in label for label in expander_labels)
    assert any("Kochi Operation Breakthrough" in label for label in expander_labels)
    assert any("Intervention effectiveness" in label for label in expander_labels)

    rendered = "\n".join(
        str(element.value)
        for elements in (app.info, app.warning, app.caption, app.markdown)
        for element in elements
    )
    assert "ML action-effect ranking is currently withheld" in rendered
    assert "not a validated forecast" in rendered.lower()
