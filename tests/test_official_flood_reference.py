"""Integrity checks for the KSDMA district-level flood reference table."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "data" / "reference" / "ksdma_ernakulam_flood_return_period_statistics_2022.json"


def test_flood_reference_is_scoped_to_ernakulam_district_and_source_traced():
    data = json.loads(REFERENCE.read_text(encoding="utf-8"))
    assert "KSDMA" in data["publisher"]
    assert data["source_url"].startswith("https://")
    assert data["geographic_coverage"] == "Ernakulam district aggregate, not Kochi Corporation or individual wards"
    assert len(data["historical_scenario"]) == 6
    assert len(data["rcp_8_5_scenario"]) == 6
    assert any("not be assigned to Kochi Corporation" in item for item in data["limitations"])


def test_flood_reference_periods_and_statistics_are_ordered_and_nonnegative():
    data = json.loads(REFERENCE.read_text(encoding="utf-8"))
    expected_periods = [10, 25, 50, 100, 200, 500]
    for scenario_key in ("historical_scenario", "rcp_8_5_scenario"):
        rows = data[scenario_key]
        assert [row["return_period_years"] for row in rows] == expected_periods
        assert all(row["area_affected_sq_km"] >= 0 for row in rows)
        assert all(row["hospitals_exposed"] >= 0 for row in rows)
        assert all(row["schools_exposed"] >= 0 for row in rows)
        assert all(
            rows[index]["area_affected_sq_km"] <= rows[index + 1]["area_affected_sq_km"]
            for index in range(len(rows) - 1)
        )
