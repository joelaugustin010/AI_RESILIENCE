"""Regression checks for the two-map Kochi command-centre architecture."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "app_pages" / "kochi_map.py").read_text(encoding="utf-8")


def test_map_page_uses_a_split_command_centre_layout():
    assert 'st.columns([0.34, 0.66], gap="large")' in SOURCE
    assert 'with controls_column:' in SOURCE
    assert 'with map_column:' in SOURCE
    assert 'map_slot = st.empty()' in SOURCE
    assert 'context_map_slot = st.empty()' in SOURCE


def test_worldcover_is_not_added_to_the_hazard_infrastructure_map():
    assert 'context_deck_layers.append(' in SOURCE
    assert not re.search(r'(?<!context_)deck_layers\.append\(\s*pdk\.Layer\(\s*"BitmapLayer"', SOURCE)
    assert 'id="worldcover-2021-context"' in SOURCE
    assert 'context_map_slot.pydeck_chart(' in SOURCE
    assert 'key="kochi_worldcover_context_map"' in SOURCE


def test_jrc_flood_context_remains_on_the_hazard_map_only():
    assert 'deck_layers.append(\n                    build_jrc_preview_layer(' in SOURCE
    worldcover_block = SOURCE.split('if show_landcover:', 1)[1].split('worldcover_class_rows =', 1)[0]
    assert 'context_deck_layers.append(' in worldcover_block
    assert not re.search(r'(?<!context_)deck_layers\.append\(', worldcover_block)


def test_worldcover_preview_is_validated_without_base64_expression_payloads():
    assert "validate_worldcover_preview(image_bytes, metadata)" in SOURCE
    assert "image_base64" not in SOURCE
    assert "import base64" not in SOURCE


def test_map_keeps_unknown_hazard_and_boundary_limitations_explicit():
    assert "No validated, licence-cleared hazard footprint is currently available" in SOURCE
    assert "No current official ward polygon set is approved for production exposure analysis." in SOURCE
    assert "not a hazard zone" in SOURCE


def test_command_centre_is_rendered_before_scenario_and_evidence_sections():
    header = SOURCE.index('page_header(')
    shell = SOURCE.index('controls_column, map_column = st.columns([0.34, 0.66]')
    scenario = SOURCE.index('map_context = st.session_state.get(MAP_CONTEXT_KEY)')
    availability = SOURCE.index('st.subheader("Hazard layer availability")')
    evidence = SOURCE.index('"Source and layer catalog"')
    assert header < shell < scenario < availability < evidence
