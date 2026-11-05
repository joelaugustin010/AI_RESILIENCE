"""Streamlit regression checks for the blocked flood-exposure user flows."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parent


def _page(path: str) -> AppTest:
    # The map page reads and validates the processed spatial layers on a cold
    # cache; allow enough time for that one-time work without changing what the
    # tests assert.
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=180).run()
    app.switch_page(path).run()
    assert not app.exception
    return app


def _text(app: AppTest) -> str:
    elements = []
    for collection in (
        app.title,
        app.header,
        app.subheader,
        app.caption,
        app.markdown,
        app.get("text"),
        app.warning,
        app.info,
        app.error,
    ):
        elements.extend(
            "\n".join(
                str(value)
                for value in (getattr(item, "title", ""), getattr(item, "value", ""))
                if value
            )
            for item in collection
        )
    return "\n".join(elements)


def test_data_readiness_reports_flood_analysis_unavailable_and_license_conflict():
    app = _page("app_pages/data_readiness.py")
    rendered = _text(app)
    assert "Operational exposure analysis is unavailable" in rendered
    assert "No real asset-to-flood exposure count is currently supported" in rendered
    assert "ODbL 1.0" in rendered
    assert "CC BY 4.0" in rendered
    assert "Sametham" in rendered


def test_kochi_map_displays_licensed_jrc_preview_as_modelled_context():
    app = _page("app_pages/kochi_map.py")
    rendered = _text(app)
    assert "ODbL 1.0" in rendered
    assert "CC BY 4.0" in rendered
    assert "not observed flooding" in rendered.lower()
    assert "unknown / unassessable exposure" in rendered.lower()
    jrc_toggles = [box for box in app.checkbox if "jrc" in box.label.lower()]
    assert len(jrc_toggles) == 1
    assert "modelled" in jrc_toggles[0].label.lower()
    assert jrc_toggles[0].value is False


def test_hospital_page_does_not_rank_unsupported_scores():
    app = _page("app_pages/hospital_vulnerability.py")
    rendered = _text(app)
    assert "No hospital vulnerability ranking is available" in rendered
    assert "not used to identify a most-vulnerable hospital" in rendered
    assert not any("score" in element.label.lower() for element in app.slider)
