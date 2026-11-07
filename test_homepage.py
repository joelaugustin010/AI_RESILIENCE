"""Regression checks for the Kochi-focused cinematic homepage and navigation."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parent

EXPECTED_PAGES = {
    "decision_workflow",
    "disaster_assistant",
    "kochi_map",
    "air_pollution",
    "data_readiness",
    "hazard_model_lab",
    "hospital_vulnerability",
    "compound_scenario",
    "disaster_probability",
    "mitigation_planner",
    "smart_mitigation_design",
}


def _home() -> AppTest:
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not app.exception
    return app


def _markup(app: AppTest) -> str:
    return "\n".join(element.value for element in app.markdown)


def test_home_is_the_default_page_with_the_cinematic_hero():
    app = _home()
    html = _markup(app)

    assert "ar-cine-hero" in html
    assert "AI <span>RESILIENCE</span>" in html
    assert "Understanding Kochi. Preparing for risk. Strengthening urban resilience." in html
    assert "app/static/images/hero-kerala-fallback.jpg" in html

    labels = [button.label for button in app.button]
    assert "Explore Intelligence" in labels
    assert "Explore Kochi's Risk Context" in labels


def test_home_links_every_registered_workspace():
    app = _home()
    linked = {link.page for link in app.page_link}
    assert linked == EXPECTED_PAGES


def test_hero_video_is_optional_and_always_local():
    html = _markup(_home())
    if "<video" in html:
        assert 'src="app/static/videos/kerala_hero.mp4"' in html
        assert "http://" not in html.split("<video", 1)[1].split("</video>", 1)[0]
        assert 'poster="app/static/images/hero-kerala-fallback.jpg"' in html


def test_both_hero_calls_to_action_navigate():
    for key in ("home_explore_intelligence", "home_explore_risks"):
        app = _home()
        app.button(key=key).click().run()
        assert not app.exception
        assert "ar-cine-hero" not in _markup(app)


def test_original_home_has_compact_1400x900_desktop_layout():
    html = _markup(_home())
    assert "ar-cine-hero" in html
    assert "height: 520px !important" in html
    assert "min-height: 520px !important" in html
    assert "st-key-ar-hero-ctas" in html
    # The original multi-image hero and optional local video remain in place.
    assert "hero-kerala-ghats.jpg" in html
    assert "hero-kerala-landslide.jpg" in html
