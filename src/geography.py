"""Shared, conservative geographic scope for the current Ernakulam study."""

from __future__ import annotations

import re

import pandas as pd


ACTIVE_DISTRICT = "Ernakulam"
STUDY_AREA_LABEL = "Study area: Ernakulam district, Kerala."

_ALIASES = {
    "alappuzha": "Alappuzha", "alleppey": "Alappuzha",
    "ernakulam": "Ernakulam", "idukki": "Idukki", "kannur": "Kannur",
    "kasaragod": "Kasaragod", "kasargod": "Kasaragod", "kollam": "Kollam",
    "quilon": "Kollam", "kottayam": "Kottayam", "kozhikode": "Kozhikode",
    "calicut": "Kozhikode", "malappuram": "Malappuram", "palakkad": "Palakkad",
    "palghat": "Palakkad", "pathanamthitta": "Pathanamthitta",
    "thiruvananthapuram": "Thiruvananthapuram", "trivandrum": "Thiruvananthapuram",
    "thrissur": "Thrissur", "trichur": "Thrissur", "wayanad": "Wayanad",
}


def normalize_district(value: object) -> str | None:
    """Normalize documented district name variants; unknown/missing stays unknown."""
    if value is None or pd.isna(value):
        return None
    text = re.sub(r"[^a-z]+", " ", str(value).casefold()).strip()
    text = re.sub(r"^(district of )", "", text)
    text = re.sub(r"\s+(district|dt|dist)$", "", text).strip()
    return _ALIASES.get(text)


def filter_to_study_district(
    frame: pd.DataFrame, *, district_column: str = "District"
) -> tuple[pd.DataFrame, dict[str, int | str]]:
    """Return only records explicitly attributed to Ernakulam and audit exclusions."""
    if district_column not in frame.columns:
        return frame.iloc[0:0].copy(), {
            "source_rows": len(frame), "retained_rows": 0,
            "excluded_unknown_geography": len(frame), "excluded_other_district": 0,
            "missing_district_field": district_column,
        }
    normalized = frame[district_column].map(normalize_district)
    keep = normalized.eq(ACTIVE_DISTRICT)
    unknown = normalized.isna()
    return frame.loc[keep].copy(), {
        "source_rows": len(frame), "retained_rows": int(keep.sum()),
        "excluded_unknown_geography": int(unknown.sum()),
        "excluded_other_district": int((~keep & ~unknown).sum()),
        "missing_district_field": "",
    }
