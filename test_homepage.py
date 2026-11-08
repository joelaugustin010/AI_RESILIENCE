"""Regression checks for the Kochi-focused homepage and navigation."""

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


def test_home_is_the_default_page_with_the_minimal_koch_aerial_hero():
    app = _home()
    html = _markup(app)

    assert "ar-cine-hero ar-home-minimal" in html
    assert "AI <span>RESILIENCE</span>" in html
    assert "Understanding Kochi. Preparing for Risk. Building a Resilient Future." in html
    assert "Aerial_view_of_Kochi_-_panoramio.jpg" in html
    assert "Aerial view of Kochi, Kerala" in html

    labels = [button.label for button in app.button]
    assert "Explore Intelligence" in labels
    assert "Explore Kochi's Risk Context" in labels


def test_home_links_every_registered_workspace():
    app = _home()
    linked = {link.page for link in app.page_link}
    assert linked == EXPECTED_PAGES


def test_hero_video_uses_local_mp4_or_verified_koch_webm_with_poster_fallback():
    html = _markup(_home())
    assert "<video" in html
    video = html.split("<video", 1)[1].split("</video>", 1)[0]
    assert 'poster="app/static/images/hero-kerala-fallback.jpg"' in video
    assert "autoplay muted loop playsinline" in video
    assert (
        'src="https://upload.wikimedia.org/wikipedia/commons/2/2b/Chinese_Fishing_nets.webm"'
        in video
        or 'src="app/static/videos/kerala_hero.mp4"' in video
    )
    assert "http://" not in video
    assert "Chinese Fishing nets at Kochi" in html


def test_both_hero_calls_to_action_navigate():
    for key in ("home_explore_intelligence", "home_explore_risks"):
        app = _home()
        app.button(key=key).click().run()
        assert not app.exception
        assert "ar-cine-hero" not in _markup(app)



def test_home_hero_has_a_1400x900_desktop_first_screen_fit():
    html = _markup(_home())
    # The implementation note is a Python comment, not rendered HTML.
    # Assert the actual CSS contract instead of expecting that comment in markup.
    assert "calc(100svh - 330px)" in html
    assert "min-height: clamp(480px, calc(100svh - 330px), 570px)" in html
    assert "st-key-ar-hero-ctas" in html
