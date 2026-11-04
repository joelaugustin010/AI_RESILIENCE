"""Location and forecast safeguards for the Ernakulam disaster dashboard."""

from __future__ import annotations

import csv
import json
import math
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
LOCATION_PATH = ROOT / "data" / "reference" / "ernakulam_locations.json"
EVIDENCE_PATH = ROOT / "data" / "reference" / "ernakulam_disaster_evidence.json"
SUMMARY_PATH = ROOT / "data" / "processed" / "ernakulam_disaster_summary.json"
FLOOD_STATISTICS_PATH = (
    ROOT / "data" / "reference" / "ksdma_ernakulam_flood_return_period_statistics_2022.json"
)
CWC_RAINFALL_PATH = ROOT / "data" / "raw" / "kerala.csv"
LANDSLIDE_CATALOG_PATH = (
    ROOT / "data" / "external" / "hazards" / "raw" / "landslide"
    / "nasa_global_landslide_catalog.csv"
)
CYCLONE_TRACK_PATH = (
    ROOT / "data" / "external" / "hazards" / "raw" / "cyclone"
    / "ibtracs_north_indian_ocean_v04r01.csv"
)

HAZARDS = {
    "flood": {
        "label": "Flood and Urban Waterlogging",
        "icon": "🌊",
        "color": "#1677a5",
    },
    "cyclone": {
        "label": "Cyclone and Coastal Storm Impacts",
        "icon": "🌀",
        "color": "#7258a6",
    },
    "landslide": {
        "label": "Landslide",
        "icon": "⛰️",
        "color": "#a05a35",
    },
    "drought": {
        "label": "Drought and Water Scarcity",
        "icon": "☀️",
        "color": "#bd8421",
    },
}

SOURCE_KEYS = {
    "municipalities": "municipality",
    "corporations": "corporation",
    "grama_panchayats": "grama_panchayat",
}
OTHER_KERALA_DISTRICTS = {
    "Alappuzha",
    "Idukki",
    "Kannur",
    "Kasaragod",
    "Kollam",
    "Kottayam",
    "Kozhikode",
    "Malappuram",
    "Palakkad",
    "Pathanamthitta",
    "Thiruvananthapuram",
    "Thrissur",
    "Wayanad",
}


def load_location_registry(path: Path = LOCATION_PATH) -> dict[str, Any]:
    """Load LSGD-verified local-body names and reject out-of-district entries."""
    registry = json.loads(path.read_text(encoding="utf-8"))
    if registry.get("district") != "Ernakulam" or registry.get("state") != "Kerala":
        raise ValueError("Location reference must be restricted to Ernakulam, Kerala.")
    if registry.get("register_vintages", {}).get("municipalities") != 2020 or registry.get(
        "register_vintages", {}
    ).get("grama_panchayats") != 2020:
        raise ValueError(
            "Municipality and panchayat names must retain their verified source vintage."
        )

    required_groups = {
        "municipalities": 13,
        "corporations": 1,
        "grama_panchayats": 82,
    }
    for group, expected_count in required_groups.items():
        locations = registry.get(group)
        if (
            not isinstance(locations, list)
            or len(locations) != expected_count
            or not all(isinstance(location, str) and location.strip() for location in locations)
        ):
            raise ValueError(f"Location reference has an invalid {group} list.")
        if len({location.casefold() for location in locations}) != len(locations):
            raise ValueError(f"Location reference contains duplicate {group} names.")
        other_district_names = {district.casefold() for district in OTHER_KERALA_DISTRICTS}
        if any(location.casefold() in other_district_names for location in locations):
            raise ValueError(f"Location reference contains a non-Ernakulam district in {group}.")
        source = registry.get("sources", {}).get(SOURCE_KEYS[group])
        if not isinstance(source, dict) or not source.get("url", "").startswith("https://"):
            raise ValueError(f"Location reference has no source for {group}.")

    all_names = [
        location
        for group in required_groups
        for location in registry[group]
    ]
    if len({name.casefold() for name in all_names}) != len(all_names):
        raise ValueError("Location reference contains names duplicated across local-body types.")
    return registry


def location_options(registry: Mapping[str, Any]) -> list[str]:
    """Return one district aggregate and all local bodies in the register."""
    district_option = "Ernakulam district (all areas)"
    options = [district_option]
    options.extend(f"{name} Municipality" for name in registry["municipalities"])
    options.extend(f"{name} Grama Panchayat" for name in registry["grama_panchayats"])
    options.extend(f"{name} Corporation" for name in registry["corporations"])
    if len(options) != len(set(options)):
        raise ValueError("Location labels must be unique.")
    return options


def format_probability(probability: float | None) -> str:
    """Format a probability already produced by an eligible model."""
    if probability is None:
        return "Not available"
    if isinstance(probability, bool) or not isinstance(probability, (int, float)):
        raise ValueError("Probability must be a numeric value from 0 to 1.")
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("Probability must be a finite value from 0 to 1.")
    return f"{probability * 100:.1f}%"


def _validated_model_result(
    result: Mapping[str, Any],
    hazard_id: str,
    location: str,
) -> bool:
    evaluation = result.get("evaluation")
    return (
        result.get("model_status") == "validated"
        and result.get("hazard_id") == hazard_id
        and result.get("district") == "Ernakulam"
        and result.get("location") == location
        and result.get("evidence_status") == "verified"
        and isinstance(result.get("forecast_period"), str)
        and bool(result["forecast_period"].strip())
        and isinstance(result.get("confidence_basis"), str)
        and bool(result["confidence_basis"].strip())
        and result.get("confidence") in {"High", "Moderate", "Low"}
        and isinstance(evaluation, Mapping)
        and evaluation.get("chronological_validation") is True
        and evaluation.get("calibration_checked") is True
        and evaluation.get("beats_baselines") is True
    )


def _validated_risk_label(result: Mapping[str, Any], probability: float) -> str | None:
    thresholds = result.get("risk_thresholds")
    if not isinstance(thresholds, Mapping):
        return None
    values = [thresholds.get(key) for key in ("moderate", "high", "very_high")]
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
        return None
    moderate, high, very_high = values
    if not (
        0 <= moderate < high < very_high <= 1
        and isinstance(result.get("risk_threshold_basis"), str)
        and result["risk_threshold_basis"].strip()
    ):
        return None
    if probability >= very_high:
        return "Very High"
    if probability >= high:
        return "High"
    if probability >= moderate:
        return "Moderate"
    return "Low"


def _load_cwc_rainfall_summary(path: Path = CWC_RAINFALL_PATH) -> dict[str, Any]:
    """Summarize only source-tagged Ernakulam rows without resolving conflicts."""
    required_fields = {
        "Agency",
        "District",
        "Station",
        "Data Acquisition Time",
        "Telemetry Hourly Rainfall (mm)",
    }
    grouped: dict[tuple[str, datetime], list[float]] = defaultdict(list)
    source_row_count = 0
    invalid_row_count = 0
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not required_fields.issubset(reader.fieldnames or []):
            raise ValueError("CWC rainfall file is missing required source columns.")
        for row in reader:
            if (
                row.get("Agency", "").strip().casefold() != "cwc"
                or row.get("District", "").strip().casefold() != "ernakulam"
            ):
                continue
            source_row_count += 1
            try:
                timestamp = datetime.strptime(
                    row["Data Acquisition Time"].strip(), "%d-%m-%Y %H:%M"
                )
                rainfall = float(row["Telemetry Hourly Rainfall (mm)"])
                if not math.isfinite(rainfall) or rainfall < 0:
                    raise ValueError("Rainfall measurement is invalid.")
            except (KeyError, TypeError, ValueError):
                invalid_row_count += 1
                continue
            grouped[(row["Station"].strip(), timestamp)].append(rainfall)

    if not source_row_count or not grouped:
        raise ValueError("No parseable CWC rainfall observations are tagged Ernakulam.")

    single_record_groups = [
        (key, values[0])
        for key, values in grouped.items()
        if len(values) == 1
    ]
    conflicting_groups = sum(
        len(values) > 1 and len(set(values)) > 1 for values in grouped.values()
    )
    duplicate_groups = sum(len(values) > 1 for values in grouped.values())
    timestamps = [key[1] for key, _ in single_record_groups]
    return {
        "source_row_count": source_row_count,
        "single_record_station_time_count": len(single_record_groups),
        "duplicate_station_time_groups": duplicate_groups,
        "conflicting_station_time_groups": conflicting_groups,
        "invalid_row_count": invalid_row_count,
        "station_names": sorted({station for station, _ in grouped}),
        "first_unambiguous_timestamp": min(timestamps).isoformat(),
        "last_unambiguous_timestamp": max(timestamps).isoformat(),
        "district_scope": "Ernakulam source District field; one station only",
        "source_file": str(path.relative_to(ROOT)),
    }


def _load_landslide_reports(path: Path = LANDSLIDE_CATALOG_PATH) -> list[dict[str, str]]:
    """Return catalog records that explicitly name Ernakulam in their location."""
    reports = []
    required_fields = {
        "country_code",
        "admin_division_name",
        "event_date",
        "event_title",
        "location_description",
        "landslide_category",
        "event_id",
        "source_name",
        "source_link",
    }
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not required_fields.issubset(reader.fieldnames or []):
            raise ValueError("Landslide catalog is missing required source columns.")
        for row in reader:
            location_text = " ".join(
                (row.get("event_title", ""), row.get("location_description", ""))
            )
            if (
                row.get("country_code", "").strip() != "IN"
                or row.get("admin_division_name", "").strip().casefold() != "kerala"
                or not row.get("landslide_category", "").strip()
                or not re.search(r"\bernakulam\b|\berakulam\b", location_text, re.I)
            ):
                continue
            try:
                event_date = datetime.strptime(
                    row["event_date"].strip(), "%m/%d/%Y %I:%M:%S %p"
                ).date()
            except ValueError as error:
                raise ValueError(
                    f"Could not parse a district-mentioned landslide date: {row['event_date']!r}"
                ) from error
            reports.append(
                {
                    "event_id": row["event_id"].strip(),
                    "date": event_date.isoformat(),
                    "title": row["event_title"].strip(),
                    "location": row["location_description"].strip(),
                    "source_name": row["source_name"].strip(),
                    "source_url": row["source_link"].strip(),
                    "location_accuracy": row.get("location_accuracy", "").strip(),
                }
            )
    return reports


def _load_cyclone_track_summary(path: Path = CYCLONE_TRACK_PATH) -> dict[str, Any]:
    """Read regional track coverage without converting tracks into local impacts."""
    required_fields = {"SID", "SEASON", "ISO_TIME", "LAT", "LON"}
    storm_ids: set[str] = set()
    seasons: list[int] = []
    track_rows = 0
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not required_fields.issubset(reader.fieldnames or []):
            raise ValueError("Cyclone track file is missing required source columns.")
        for row in reader:
            if not row.get("SID", "").strip():
                continue
            track_rows += 1
            storm_ids.add(row["SID"].strip())
            try:
                seasons.append(int(row["SEASON"]))
            except (TypeError, ValueError):
                continue
    if not track_rows or not seasons:
        raise ValueError("Cyclone track archive contains no readable regional records.")
    return {
        "track_row_count": track_rows,
        "storm_count": len(storm_ids),
        "first_season": min(seasons),
        "last_season": max(seasons),
        "source_file": str(path.relative_to(ROOT)),
    }


def load_assessment_data() -> dict[str, Any]:
    """Load verified district context and explicitly bounded local observations."""
    evidence = load_technical_evidence()
    flood_statistics = json.loads(FLOOD_STATISTICS_PATH.read_text(encoding="utf-8"))
    flood_dataset_id = flood_statistics.get("dataset_id")
    flood_geography = flood_statistics.get("geographic_coverage")
    if (
        flood_dataset_id != "ksdma_ernakulam_flood_return_period_statistics_2022"
        or flood_geography
        != "Ernakulam district aggregate, not Kochi Corporation or individual wards"
    ):
        raise ValueError("Flood statistics are not verified as Ernakulam district aggregates.")
    if not isinstance(flood_statistics.get("historical_scenario"), list):
        raise ValueError("KSDMA flood statistics have no historical scenario records.")
    return {
        "technical_evidence": evidence,
        "flood_statistics": flood_statistics,
        "rainfall": _load_cwc_rainfall_summary(),
        "landslide_reports": _load_landslide_reports(),
        "cyclone_tracks": _load_cyclone_track_summary(),
    }


def build_assessment_card(
    hazard_id: str,
    location: str,
    allowed_locations: list[str],
    assessment_data: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a hazard-specific evidence card without inventing local estimates."""
    if hazard_id not in HAZARDS:
        raise ValueError(f"Unsupported disaster selector: {hazard_id!r}")
    if location not in allowed_locations:
        raise ValueError("Selected location is not in the verified Ernakulam register.")

    hazard = HAZARDS[hazard_id]
    technical_evidence = assessment_data["technical_evidence"]
    evidence = next(
        item
        for item in technical_evidence["hazards"]
        if item["id"] == hazard_id
    )
    card = {
        "hazard_id": hazard_id,
        "hazard_name": hazard["label"],
        "icon": hazard["icon"],
        "color": hazard["color"],
        "location": location,
        "probability": None,
        "probability_text": None,
        "risk_label": "Not rated",
        "primary_value": "No local assessment",
        "primary_label": "No defensible location-level result",
        "explanation": evidence["key_findings"][0],
        "assessment_label": "Historical context",
        "scope": evidence["spatial_coverage"],
        "period": evidence["observation_period"],
        "evidence_quality": evidence["uncertainty"],
        "method": evidence["method"],
        "uncertainty": evidence["uncertainty"],
        "sources": evidence["sources"],
        "record_coverage": evidence["record_coverage"],
        "result_level": "historical_assessment",
    }

    if hazard_id == "flood":
        statistics = assessment_data["flood_statistics"]
        scenario = next(
            item
            for item in statistics["historical_scenario"]
            if item["return_period_years"] == 10
        )
        return_period = scenario["return_period_years"]
        probability_percent = scenario["annual_exceedance_probability_percent"]
        if not math.isclose(probability_percent, 100 / return_period):
            raise ValueError("KSDMA flood scenario return period and exceedance label disagree.")
        probability = probability_percent / 100
        area_affected = scenario["area_affected_sq_km"]
        if isinstance(area_affected, bool) or not isinstance(area_affected, (int, float)):
            raise ValueError("KSDMA flood affected-area value is invalid.")
        card.update(
            {
                "probability": probability,
                "probability_text": format_probability(probability),
                "primary_value": format_probability(probability),
                "primary_label": (
                    "Approx. annual exceedance · KSDMA historical 10-year scenario"
                ),
                "risk_label": "Not rated",
                "assessment_label": "Historical modelled scenario",
                "explanation": (
                    f"KSDMA reports {area_affected:,.2f} km² affected in this "
                    "Ernakulam-wide historical flood scenario."
                ),
                "scope": (
                    "Ernakulam district aggregate; not the selected locality or "
                    "urban waterlogging"
                ),
                "period": (
                    "KSDMA 2022 report; underlying historical-model reference "
                    "period is not stated"
                ),
                "evidence_quality": (
                    "Official KSDMA district scenario; not a current forecast "
                    "or a locality-specific estimate."
                ),
                "record_coverage": (
                    f"Source scenario: {return_period}-year return period; "
                    f"{probability_percent:g}% approximate annual exceedance."
                ),
                "result_level": "source_model_scenario",
            }
        )
    elif hazard_id == "cyclone":
        tracks = assessment_data["cyclone_tracks"]
        card.update(
            {
                "primary_value": "Regional tracks only",
                "primary_label": "NOAA/NCEI IBTrACS · North Indian Ocean",
                "assessment_label": "Local impact assessment not established",
                "explanation": (
                    f"The loaded archive contains {tracks['storm_count']:,} storms "
                    f"and {tracks['track_row_count']:,} track records "
                    f"({tracks['first_season']}–{tracks['last_season']}); "
                    "no verified Ernakulam impact inventory or district-boundary "
                    "track analysis is available."
                ),
                "scope": "Regional tracks only; no Ernakulam impact attribution",
                "period": (
                    f"Regional archive seasons {tracks['first_season']}–"
                    f"{tracks['last_season']}"
                ),
                "evidence_quality": (
                    "Authoritative track archive loaded; track positions alone "
                    "do not establish local wind, surge, damage, or impact."
                ),
                "record_coverage": (
                    f"{tracks['storm_count']:,} regional storms; "
                    f"{tracks['track_row_count']:,} track records."
                ),
                "result_level": "regional_historical_context",
            }
        )
    elif hazard_id == "landslide":
        reports = assessment_data["landslide_reports"]
        dated_reports: dict[str, list[dict[str, str]]] = defaultdict(list)
        for report in reports:
            dated_reports[report["date"]].append(report)
        report_periods = sorted(dated_reports)
        if report_periods:
            period_labels = []
            for report_date in report_periods:
                event_date = datetime.fromisoformat(report_date).date()
                reports_for_date = dated_reports[report_date]
                named_report = next(
                    (
                        item
                        for item in reports_for_date
                        if item["location"].split(",")[0].strip().casefold()
                        not in {"ernakulam", "erakulam"}
                    ),
                    reports_for_date[0],
                )
                place = named_report["location"].split(",")[0].strip()
                period_labels.append(f"{place} ({event_date.strftime('%b %Y')})")
            card.update(
                {
                    "primary_value": " · ".join(period_labels),
                    "primary_label": (
                        "Historical catalog reports; not a complete event count"
                    ),
                    "assessment_label": "Historical reports; no local susceptibility class",
                    "explanation": (
                        "NASA's catalog includes reports at "
                        f"{', '.join(period_labels)}. These are historical examples, "
                        "not a complete event count; invalid GSI polygons prevent "
                        "a susceptibility class from being assigned to this area."
                    ),
                    "scope": (
                        "Named source reports only; not spatially joined to local "
                        "government boundaries"
                    ),
                    "period": "Catalog entries dated " + ", ".join(
                        datetime.fromisoformat(value).strftime("%Y")
                        for value in report_periods
                    ),
                    "evidence_quality": (
                        "Global media-reported event catalog plus an official "
                        "susceptibility layer whose three geometries are invalid."
                    ),
                    "record_coverage": (
                        f"{len(reports)} catalog entries across "
                        f"{len(report_periods)} reported dates; duplicate or "
                        "incomplete event reporting is possible."
                    ),
                    "sources": [
                        *evidence["sources"],
                        *[
                            {
                                "title": (
                                    f"{report['source_name']} report: {report['title']}"
                                ),
                                "publisher": "Source cited by NASA Global Landslide Catalog",
                                "url": report["source_url"],
                                "reuse_note": (
                                    f"Catalog record {report['event_id']}; "
                                    f"reported location accuracy: "
                                    f"{report['location_accuracy'] or 'not stated'}."
                                ),
                            }
                            for report in reports
                        ],
                    ],
                    "result_level": "historical_catalog_context",
                }
            )
    elif hazard_id == "drought":
        card.update(
            {
                "primary_value": "No district series",
                "primary_label": (
                    "Drought index, groundwater, reservoir, and water-supply "
                    "observations are missing"
                ),
                "assessment_label": "No local drought assessment",
                "explanation": (
                    "No verified Ernakulam drought-index or water-scarcity "
                    "time series is present in the project data."
                ),
                "scope": "No district or locality-level drought evidence",
                "period": "No usable Ernakulam observation period",
                "evidence_quality": (
                    "The national source reference is not a verified district "
                    "dataset; missing data are not interpreted as low risk."
                ),
                "result_level": "evidence_gap",
            }
        )
    return card


def build_prediction_card(
    hazard_id: str,
    location: str,
    allowed_locations: list[str],
    forecast_result: Mapping[str, Any] | None = None,
    assessment_data: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Use a validated forecast when supplied; otherwise return sourced context."""
    data = assessment_data or load_assessment_data()
    card = build_assessment_card(hazard_id, location, allowed_locations, data)
    if forecast_result is None or not _validated_model_result(
        forecast_result, hazard_id, location
    ):
        return card

    probability = forecast_result.get("probability")
    probability_text = format_probability(probability)
    if probability is None:
        return card
    risk_label = _validated_risk_label(forecast_result, probability)
    if risk_label is None:
        return card

    return {
        **card,
        "probability": probability,
        "probability_text": probability_text,
        "risk_label": risk_label,
        "primary_value": probability_text,
        "primary_label": "Validated location-specific forecast",
        "explanation": forecast_result.get(
            "plain_language_explanation", card["explanation"]
        ),
        "period": forecast_result["forecast_period"],
        "scope": location,
        "evidence_quality": forecast_result["confidence_basis"],
        "assessment_label": "Validated prediction",
        "model_status": "validated",
        "result_level": "validated_prediction",
    }


def build_assessment_cards(
    location: str,
    allowed_locations: list[str],
    assessment_data: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build the four hazard cards for one verified Ernakulam selector value."""
    data = assessment_data or load_assessment_data()
    return [
        build_prediction_card(
            hazard_id,
            location,
            allowed_locations,
            assessment_data=data,
        )
        for hazard_id in HAZARDS
    ]


def load_technical_evidence(path: Path = EVIDENCE_PATH) -> dict[str, Any]:
    """Load source and model-limit notes for the technical details expander."""
    evidence = json.loads(path.read_text(encoding="utf-8"))
    if evidence.get("district") != "Ernakulam":
        raise ValueError("Technical evidence must be scoped to Ernakulam.")
    hazards = evidence.get("hazards")
    if not isinstance(hazards, list) or {
        item.get("id") for item in hazards if isinstance(item, dict)
    } != set(HAZARDS):
        raise ValueError("Technical evidence must cover the four dashboard hazards.")
    return evidence
