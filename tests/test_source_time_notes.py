"""Regression tests for source/time note capture and display."""

from src.decision_workflow import evidence_provenance_summary


def test_source_time_notes_are_shown_verbatim_as_unverified():
    notes = "IMD bulletin; issued 31 Oct 2026, 10:00 IST; valid until 20:30 IST; wind km/h"
    result = evidence_provenance_summary({
        "input_classification": "Forecast supplied by user (not checked by app)",
        "source_and_time": notes,
    })

    assert notes in result["Source/time notes"]
    assert result["Source/time notes"].startswith("User-entered (not independently verified):")
    assert "not checked by the app" in result["Provenance status"].lower()


def test_source_time_notes_are_trimmed_and_multiline_text_is_preserved():
    notes = "  Source: official bulletin\nIssue time: 10:00 IST\nUnits: km/h  "
    result = evidence_provenance_summary({
        "input_classification": "Unknown / unverified",
        "source_and_time": notes,
    })

    assert result["Source/time notes"].endswith(
        "Source: official bulletin\nIssue time: 10:00 IST\nUnits: km/h"
    )


def test_blank_source_time_notes_are_reported_as_not_supplied():
    result = evidence_provenance_summary({
        "input_classification": "Unknown / unverified",
        "source_and_time": "   ",
    })

    assert result["Source/time notes"] == "Not supplied"
