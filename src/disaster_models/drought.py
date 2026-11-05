"""Station-level Standardized Precipitation Index (SPI-1) when history permits."""

from __future__ import annotations

import csv
import io
import math
from datetime import datetime
from typing import Any

from src.disaster_models.common import build_assessment, recommendation, validate_top_level

SOURCES = [
    {
        "title": "WMO, Standardized Precipitation Index User Guide",
        "url": "https://library.wmo.int/idurl/4/39629",
        "role": "SPI distribution-fitting method and recommended climate reference record.",
    },
    {
        "title": "McKee, Doesken and Kleist (1993), The relationship of drought frequency and duration to time scales",
        "url": "https://climate.colostate.edu/pdfs/relationshipofdroughtfrequency.pdf",
        "role": "SPI construction and standardized drought-category conventions.",
    },
]

# McKee et al. (1993) category boundaries.  Threshold values belong to the more
# severe category on the dry side (SPI <= -2.0 is extremely dry, -2.0 < SPI <=
# -1.5 is severely dry, -1.5 < SPI <= -1.0 is moderately dry) and to the wetter
# category on the wet side (SPI >= 1.0 is moderately wet, >= 1.5 very wet,
# >= 2.0 extremely wet).  Near normal is strictly between -1.0 and 1.0.  A
# previous ``lower <= spi < upper`` lookup misclassified exact threshold values.
SPI_CATEGORY_BOUNDARIES = (
    (-2.0, "Extremely dry"),
    (-1.5, "Severely dry"),
    (-1.0, "Moderately dry"),
    (1.0, "Moderately wet"),
    (1.5, "Very wet"),
    (2.0, "Extremely wet"),
)

MIN_REFERENCE_YEARS = 30
MIN_POSITIVE_REFERENCE_VALUES = 10


def spi_category(spi: float) -> str:
    """Return the McKee SPI category, inclusive at each documented threshold."""
    if not math.isfinite(spi):
        raise ValueError("SPI must be a finite number to assign a category.")
    if spi <= -1.0:
        for boundary, label in SPI_CATEGORY_BOUNDARIES[:3]:
            if spi <= boundary:
                return label
    elif spi >= 1.0:
        for boundary, label in reversed(SPI_CATEGORY_BOUNDARIES[3:]):
            if spi >= boundary:
                return label
    return "Near normal"


def parse_monthly_precipitation_csv(text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(text))
    expected = {"month", "precipitation_mm"}
    if reader.fieldnames is None or set(reader.fieldnames) != expected:
        raise ValueError("Monthly rainfall CSV must have exactly: month,precipitation_mm.")
    records: list[dict[str, Any]] = []
    for row_number, row in enumerate(reader, start=2):
        try:
            month = datetime.strptime(row["month"].strip(), "%Y-%m")
            value = float(row["precipitation_mm"])
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid month or precipitation value on CSV row {row_number}.") from exc
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"Precipitation on CSV row {row_number} must be finite and non-negative.")
        records.append({"month": month, "precipitation_mm": value})
    return records


def calculate_spi1(records: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(records, key=lambda row: row["month"])
    months = [row["month"] for row in ordered]
    if len(set(months)) != len(months):
        raise ValueError("Monthly precipitation records contain duplicate months.")
    for previous, current in zip(months, months[1:]):
        delta = (current.year - previous.year) * 12 + current.month - previous.month
        if delta != 1:
            return {
                "status": "insufficient_evidence",
                "spi1": None,
                "category": None,
                "reason": "SPI input has missing calendar months and is not a complete consecutive reference series.",
            }
    if len(records) < 360:
        return {
            "status": "insufficient_evidence",
            "spi1": None,
            "category": None,
            "reason": "At least 30 complete years of monthly precipitation are required for this SPI-1 implementation.",
        }
    if (months[-1].year - months[0].year + 1) < 30:
        return {
            "status": "insufficient_evidence",
            "spi1": None,
            "category": None,
            "reason": "The input does not span a 30-year reference period.",
        }

    latest = ordered[-1]
    month_number = latest["month"].month
    reference = [
        float(row["precipitation_mm"])
        for row in ordered
        if row["month"].month == month_number
    ]
    positive = [value for value in reference if value > 0]
    if len(reference) < MIN_REFERENCE_YEARS:
        return {
            "status": "insufficient_evidence",
            "spi1": None,
            "category": None,
            "reason": (
                f"Only {len(reference)} reference values exist for the target calendar "
                f"month; at least {MIN_REFERENCE_YEARS} are required to fit the gamma "
                "distribution."
            ),
        }
    if len(positive) < MIN_POSITIVE_REFERENCE_VALUES or len(set(positive)) < 2:
        return {
            "status": "insufficient_evidence",
            "spi1": None,
            "category": None,
            "reason": (
                f"Only {len(positive)} positive reference values (minimum "
                f"{MIN_POSITIVE_REFERENCE_VALUES}) or no positive-value variability "
                "exist for the target calendar month; a gamma fit would be unreliable."
            ),
        }
    try:
        from scipy.stats import gamma, norm

        shape, _, scale = gamma.fit(positive, floc=0)
        zero_probability = (len(reference) - len(positive)) / len(reference)
        precipitation = float(latest["precipitation_mm"])
        cumulative_probability = (
            zero_probability
            + (1 - zero_probability) * gamma.cdf(precipitation, shape, loc=0, scale=scale)
        )
        probability = min(max(float(cumulative_probability), 1e-10), 1 - 1e-10)
        spi = float(norm.ppf(probability))
    except (ImportError, ValueError, FloatingPointError, OverflowError) as exc:
        raise ValueError(f"SPI gamma-distribution fit failed: {exc}") from exc

    category = spi_category(spi)
    return {
        "status": "descriptive_spi1_calculated",
        "spi1": spi,
        "category": category,
        "latest_month": latest["month"].strftime("%Y-%m"),
        "latest_month_precipitation_mm": float(latest["precipitation_mm"]),
        "calendar_month_reference_count": len(reference),
        "zero_probability": zero_probability,
        "method": "Calendar-month gamma fit with zero-probability adjustment, transformed to standard normal.",
    }


def assess(inputs: dict[str, Any]) -> dict[str, Any]:
    validate_top_level(inputs)
    records = inputs.get("monthly_precipitation_records")
    if records is not None and not isinstance(records, list):
        raise ValueError("monthly_precipitation_records must be a list of monthly records.")
    spi = calculate_spi1(records) if records else {
        "status": "insufficient_evidence",
        "spi1": None,
        "category": None,
        "reason": "No station-specific monthly precipitation history was supplied.",
    }
    result = build_assessment(
        hazard="Drought",
        model_id="standardized_precipitation_index_1_month",
        method="Station-level SPI-1 using a calendar-month gamma distribution",
        scientific_basis="SPI standardizes precipitation against its local historical distribution; this implementation requires at least 30 consecutive years, fits a gamma distribution per calendar month, adjusts for zeros, and maps the cumulative probability to the standard normal scale.",
        inputs=inputs,
        result_status=spi["status"],
        hazard_assessment={
            "severity": (
                f"Descriptive SPI-1 category: {spi['category']}."
                if spi.get("spi1") is not None
                else "Drought severity unavailable; insufficient monthly reference data."
            ),
            "indicators": spi,
        },
        calculation={"method": spi.get("method", "No SPI calculation was performed."), "input_requirement": "One location/station, consecutive monthly precipitation totals in mm, and >=30 complete years."},
        consequence_pathways=[
            "Water-supply, agriculture, ecosystems and health consequences require local demand, reservoir, soil-moisture and impact evidence.",
            "SPI precipitation anomaly alone is not a water shortage, impact estimate, or forecast.",
        ],
        recommendations={
            "before": [
                recommendation(
                    "before",
                    "Develop source diversification, leakage reduction and staged demand-management options from a basin water balance and service assessment.",
                    "Long-term drought risk-reduction planning is requested.",
                    "Water-authority source/storage records, verified demand data, and an adopted drought-management plan.",
                    category="prevention",
                    limitations="SPI-1 alone does not establish a water deficit or select infrastructure investments.",
                ),
                recommendation("before", "Review official water-supply status, source storage, demand and drought-contingency triggers.", "A dry SPI observation or drought preparedness review is available.", "Water authority records and locally adopted drought plan."),
            ],
            "during": [recommendation("during", "Coordinate water conservation and essential-service allocation through responsible water authorities.", "An official drought declaration or supply restriction is in force.", "Official allocation rules, current storage and public-health requirements.")],
            "after": [recommendation("after", "Audit source recovery, service interruptions and distributional impacts before revising drought plans.", "Supply conditions recover or restrictions change.", "Reservoir/source and service records with defined dates and populations.")],
        },
        uncertainty=[
            "Monthly precipitation inputs are not independently authenticated or checked for station homogeneity.",
            "Gamma distribution fit and SPI categories depend on adequate, representative reference climatology.",
            "SPI does not incorporate temperature, evapotranspiration, soil moisture, reservoir storage or demand.",
        ],
        data_gaps=[
            "At least 30 complete, quality-controlled years of monthly precipitation at the same station/location.",
            "Water supply/storage, demand, soil moisture and impact records for consequence assessment.",
            "Independent drought outcome records for validation.",
        ],
        sources=SOURCES,
    )
    if records:
        ordered_records = sorted(records, key=lambda row: row["month"])
        result["input_conditions"]["monthly_precipitation_records"] = {
            "row_count": len(ordered_records),
            "first_month": ordered_records[0]["month"].strftime("%Y-%m"),
            "last_month": ordered_records[-1]["month"].strftime("%Y-%m"),
            "station_or_location": inputs.get("location"),
            "independent_provenance_check": "Not performed",
        }
    return result
