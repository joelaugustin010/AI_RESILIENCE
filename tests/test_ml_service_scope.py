"""Geographic scope guards for location-specific disaster research models."""

from src.ml.service import _geographic_scope_problem


def _kochi_card():
    return {"provenance": {"location": "kochi"}}


def test_kochi_weather_model_accepts_explicit_kochi_location():
    assert _geographic_scope_problem(
        _kochi_card(),
        {"location": "Kochi Municipal Corporation — area not specified"},
    ) is None


def test_kochi_weather_model_rejects_other_city():
    problem = _geographic_scope_problem(
        _kochi_card(), {"location": "Thiruvananthapuram, Kerala"}
    )

    assert problem is not None
    assert "cannot be applied" in problem


def test_kochi_weather_model_requires_explicit_location():
    problem = _geographic_scope_problem(_kochi_card(), {"rainfall_mm": 100})

    assert problem is not None
    assert "explicit location is required" in problem


def test_non_local_model_without_location_scope_is_not_restricted():
    card = {"provenance": {"source": "IBTrACS North Indian Ocean"}}

    assert _geographic_scope_problem(card, {}) is None
