"""Regression tests for hazard-compatible map context selection."""

from src.map_integration import hazard_has_flood_component, hazard_layer_availability, hazard_map_references


def test_flood_context_is_available_for_registered_flood_component_scenarios():
    assert hazard_has_flood_component("Flood") is True
    assert hazard_has_flood_component("Compound: cyclone + flood") is True
    assert hazard_has_flood_component("Compound: heavy rainfall + drainage failure") is True


def test_non_flood_hazards_do_not_receive_a_flood_overlay():
    for hazard in (
        "Cyclone",
        "Earthquake",
        "Landslide",
        "Heatwave",
        "Drought",
        "Industrial incident",
        "Infrastructure failure",
    ):
        assert hazard_has_flood_component(hazard) is False


def test_missing_or_custom_hazard_does_not_receive_a_flood_overlay():
    assert hazard_has_flood_component(None) is False
    assert hazard_has_flood_component("Unregistered custom scenario") is False


def test_map_availability_remains_explicit_for_all_registered_hazards():
    rows = hazard_layer_availability("Flood")
    assert len(rows) == 10
    flood = next(row for row in rows if row["Hazard"] == "Flood")
    assert flood["Selected"] is True
    assert flood["Validated hazard footprint"] == "Modelled scenario context available"
    landslide = next(row for row in rows if row["Hazard"] == "Landslide")
    assert landslide["Validated hazard footprint"] == "Not available"



def test_official_flood_and_landslide_reference_maps_are_available():
    flood = hazard_map_references("Flood")
    landslide = hazard_map_references("Landslide")
    assert any("Ernakulam" in item["title"] and item["url"].endswith("Ernakulam_Hist.pdf") for item in flood)
    assert any("shapefile" in item["title"].lower() and item["url"].endswith("Ernakulam.zip") for item in landslide)
    assert all(item["scope"] for item in flood + landslide)


def test_hazard_reference_maps_do_not_claim_to_be_validated_local_gis_layers():
    cyclone = hazard_map_references("Cyclone")
    assert cyclone
    assert any("not a cyclone track" in item["scope"].lower() for item in cyclone)
    assert hazard_map_references("Heatwave") == []
    assert hazard_map_references("Unregistered custom scenario") == []
    assert hazard_map_references(None) == []


def test_compound_hazard_reference_is_limited_to_available_component():
    refs = hazard_map_references("Compound: cyclone + flood")
    assert refs
    assert all("flood component only" in item["scope"].lower() for item in refs)
