from src.mitigation_data_validation import validate_records


def eligible_row(**overrides):
    row = {
        "record_id": "P-001",
        "project_name": "Urban drain rehabilitation",
        "intervention": "Stormwater drainage",
        "area_type": "Urban road",
        "scope_quantity": "250",
        "scope_unit": "metres",
        "actual_cost_inr": "1250000",
        "cost_basis": "final_paid_expenditure",
        "price_year": "2025",
        "source_reference": "https://example.gov.in/project/1",
        "source_verified": "true",
        "completion_status": "Completed",
        "start_date": "2024-01-01",
        "completion_date": "2024-06-30",
        "duration_months": "5.9",
        "ml_cost_eligible": "true",
        "ml_duration_eligible": "true",
    }
    row.update(overrides)
    return row


def test_explicitly_evidenced_record_can_pass_both_gates():
    report = validate_records([eligible_row()])
    assert report["cost_ml_eligible"] == 1
    assert report["duration_ml_eligible"] == 1


def test_supplemental_record_without_evidence_flags_stays_review_required():
    row = eligible_row(ml_cost_eligible="false", ml_duration_eligible="false")
    report = validate_records([row])
    assert report["cost_ml_eligible"] == 0
    assert report["duration_ml_eligible"] == 0
    assert report["rows"][0]["validation_status"] == "REVIEW_REQUIRED"


def test_aggregate_rows_are_never_project_training_records():
    report = validate_records([eligible_row()], dataset_kind="aggregate")
    assert report["cost_ml_eligible"] == 0
    assert report["duration_ml_eligible"] == 0
    assert "aggregate_data_not_project_level" in report["rows"][0]["issues"]


def test_sanctioned_estimate_is_not_accepted_as_final_cost_basis():
    report = validate_records([eligible_row(cost_basis="technical_sanction")])
    assert report["cost_ml_eligible"] == 0
    assert "cost_basis_not_verified_final_expenditure_or_cost_of_completion" in report["rows"][0]["review_reasons"]


def test_invalid_or_reversed_dates_block_duration():
    report = validate_records([eligible_row(start_date="2025-02", completion_date="2024-01-01")])
    assert report["duration_ml_eligible"] == 0
    assert "missing_or_nonexact_start_date" in report["rows"][0]["review_reasons"]


def test_duplicate_project_names_and_source_urls_are_flagged():
    first = eligible_row()
    second = eligible_row(record_id="P-002")
    report = validate_records([first, second])
    assert "duplicate_project_name_of_row_1" in report["rows"][1]["issues"]
    assert "duplicate_source_url_of_row_1" in report["rows"][1]["issues"]
    assert report["cost_ml_eligible"] == 0


def test_nonpositive_quantity_and_invalid_source_are_rejected():
    report = validate_records([eligible_row(scope_quantity="0", source_reference="not-a-url")])
    assert report["rows"][0]["validation_status"] == "REJECTED"
    assert "missing_or_nonpositive_scope_quantity" in report["rows"][0]["issues"]
    assert "missing_or_invalid_source_url" in report["rows"][0]["issues"]
