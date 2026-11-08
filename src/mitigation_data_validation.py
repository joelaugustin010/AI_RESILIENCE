"""Evidence-first validation for mitigation project datasets.

This module audits records without modifying source CSVs or silently promoting
records into ML training. Eligibility requires explicit, reviewable evidence fields.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit
from typing import Any, Iterable

TRUE_VALUES = {"true", "1", "yes", "y"}
COMPLETED_VALUES = {"completed", "physically completed", "closed"}
APPROVED_COST_BASES = {"final_paid_expenditure", "verified_cost_of_completion"}
DATE_FIELDS = ("start_date", "completion_date")


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _truthy(value: Any) -> bool:
    return _text(value).lower() in TRUE_VALUES


def _positive_decimal(value: Any) -> bool:
    try:
        number = Decimal(_text(value).replace(",", ""))
        return number.is_finite() and number > 0
    except (InvalidOperation, ValueError):
        return False


def _exact_date(value: Any) -> date | None:
    raw = _text(value)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _valid_source(value: Any) -> bool:
    raw = _text(value)
    try:
        parsed = urlsplit(raw)
        return parsed.scheme in {"https", "http"} and bool(parsed.netloc)
    except ValueError:
        return False


def _record_key(row: dict[str, Any], index: int) -> str:
    return _text(row.get("record_id") or row.get("candidate_id") or row.get("project_id")) or str(index)


def validate_records(
    records: Iterable[dict[str, Any]], *, dataset_kind: str = "project"
) -> dict[str, Any]:
    """Return row-level findings and conservative cost/duration eligibility.

    dataset_kind='aggregate' blocks all rows from project-level ML.
    Project rows need explicit ml_* flags, source verification, cost basis,
    price year, exact dates and compatible scope metadata before eligibility.
    """
    rows = [dict(row) for row in records]
    kind = _text(dataset_kind).lower() or "project"
    findings: list[dict[str, Any]] = []
    seen_names: dict[str, int] = {}
    seen_sources: dict[str, int] = {}

    for index, row in enumerate(rows, start=1):
        key = _record_key(row, index)
        issues: list[str] = []
        review: list[str] = []
        name = _text(row.get("project_name"))
        normalized_name = re.sub(r"\s+", " ", name).casefold()
        source = _text(row.get("source_reference"))
        normalized_source = source.rstrip("/").casefold()

        if not name:
            issues.append("missing_project_name")
        elif normalized_name in seen_names:
            issues.append(f"duplicate_project_name_of_row_{seen_names[normalized_name]}")
        else:
            seen_names[normalized_name] = index

        if not _valid_source(source):
            issues.append("missing_or_invalid_source_url")
        elif normalized_source in seen_sources:
            issues.append(f"duplicate_source_url_of_row_{seen_sources[normalized_source]}")
        else:
            seen_sources[normalized_source] = index

        if not _text(row.get("intervention")):
            issues.append("missing_intervention")
        if not _text(row.get("area_type")):
            issues.append("missing_area_type")
        if not _positive_decimal(row.get("scope_quantity")):
            issues.append("missing_or_nonpositive_scope_quantity")
        if not _text(row.get("scope_unit")):
            issues.append("missing_scope_unit")

        status = _text(row.get("completion_status") or row.get("status_reported")).casefold()
        if status not in COMPLETED_VALUES:
            review.append("completion_status_not_confirmed_as_completed")

        if not _truthy(row.get("source_verified")):
            review.append("source_not_explicitly_verified")
        if kind == "aggregate":
            issues.append("aggregate_data_not_project_level")

        cost_field = "actual_cost_inr" if _text(row.get("actual_cost_inr")) else "reported_cost_inr"
        if not _positive_decimal(row.get(cost_field)):
            issues.append("missing_or_nonpositive_cost")

        cost_basis = _text(row.get("cost_basis")).casefold()
        if cost_basis not in APPROVED_COST_BASES:
            review.append("cost_basis_not_verified_final_expenditure_or_cost_of_completion")
        if not _truthy(row.get("ml_cost_eligible")):
            review.append("ml_cost_eligibility_not_explicitly_approved")
        if not _text(row.get("price_year")).isdigit() or len(_text(row.get("price_year"))) != 4:
            review.append("missing_or_invalid_price_year")

        quantity_unit = _text(row.get("scope_unit")).casefold()
        if not quantity_unit:
            review.append("scope_unit_not_standardised")

        cost_ok = (
            kind != "aggregate"
            and not issues
            and status in COMPLETED_VALUES
            and _truthy(row.get("source_verified"))
            and cost_basis in APPROVED_COST_BASES
            and _truthy(row.get("ml_cost_eligible"))
            and _text(row.get("price_year")).isdigit()
            and len(_text(row.get("price_year"))) == 4
        )

        start = _exact_date(row.get("start_date") or row.get("start_date_reported"))
        end = _exact_date(row.get("completion_date") or row.get("physical_completion_date") or row.get("completion_date_reported"))
        if start is None:
            review.append("missing_or_nonexact_start_date")
        if end is None:
            review.append("missing_or_nonexact_completion_date")
        if start is not None and end is not None and end < start:
            issues.append("completion_date_before_start_date")

        duration_value = row.get("duration_months")
        duration_ok_value = _positive_decimal(duration_value)
        if not duration_ok_value:
            review.append("missing_or_nonpositive_duration_months")
        if not _truthy(row.get("ml_duration_eligible")):
            review.append("ml_duration_eligibility_not_explicitly_approved")

        duration_ok = (
            cost_ok
            and start is not None
            and end is not None
            and end >= start
            and duration_ok_value
            and _truthy(row.get("ml_duration_eligible"))
        )

        if issues or review:
            status_label = "REJECTED" if issues else "REVIEW_REQUIRED"
        else:
            status_label = "VALIDATED_CANDIDATE"

        findings.append({
            "row_number": index,
            "record_id": key,
            "project_name": name,
            "validation_status": status_label,
            "cost_ml_eligible": bool(cost_ok),
            "duration_ml_eligible": bool(duration_ok),
            "issues": issues,
            "review_reasons": review,
        })

    return {
        "dataset_kind": kind,
        "records_received": len(rows),
        "validated_candidates": sum(item["validation_status"] == "VALIDATED_CANDIDATE" for item in findings),
        "review_required": sum(item["validation_status"] == "REVIEW_REQUIRED" for item in findings),
        "rejected": sum(item["validation_status"] == "REJECTED" for item in findings),
        "cost_ml_eligible": sum(item["cost_ml_eligible"] for item in findings),
        "duration_ml_eligible": sum(item["duration_ml_eligible"] for item in findings),
        "rows": findings,
        "policy": (
            "Validation is a screening aid, not proof of source truth. Human review is required. "
            "Source CSVs are never modified. Aggregate rows are never expanded into project records."
        ),
    }
