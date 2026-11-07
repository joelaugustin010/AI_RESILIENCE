import pytest
from src.ml.operational_validation import evaluate_independent_spatial_holdout
from scripts.monitor_shadow_predictions import build_report

def rows():
    out=[]
    for i in range(40):
        out.append({"partition":"calibration","region_id":f"c{i%4}","event_id":f"ce{i}","y_true":i%2,"model_probability":.2 if i%2==0 else .8,"baseline_probability":.5})
    for i in range(60):
        out.append({"partition":"test","region_id":f"t{i%3}","event_id":f"te{i}","y_true":i%2,"model_probability":.2 if i%2==0 else .8,"baseline_probability":.5})
    return out

def test_spatial_holdout_requires_independent_groups_and_never_clears_operational():
    r=evaluate_independent_spatial_holdout(rows(),bootstrap_iterations=40)
    assert r["geographic_groups"]==3 and r["independent_positive_events"]==30
    assert r["operational_clearance"] is False and "platt" in r["calibration_methods"]

def test_spatial_leakage_is_rejected():
    x=rows(); x[-1]["region_id"]="c0"
    with pytest.raises(ValueError,match="Geographic leakage"): evaluate_independent_spatial_holdout(x,bootstrap_iterations=10)

def test_event_leakage_is_rejected():
    x=rows(); x[-1]["event_id"]="ce0"
    with pytest.raises(ValueError,match="Event leakage"): evaluate_independent_spatial_holdout(x,bootstrap_iterations=10)

def test_monitor_abstains_when_sources_fail_or_inputs_stale():
    base=[{"issued_at_utc":"2026-01-01T00:00:00Z","outcome_observed_at_utc":"","prediction_probability":"0.4","input_age_minutes":"5","latency_ms":"20","source_status":"OK","model_status":"OK","rain":str(i)} for i in range(25)]
    current=[dict(x,input_age_minutes="300",source_status="FAILED") for x in base]
    r=build_report(base,current,["rain"])
    assert r["safe_state"]=="UNAVAILABLE_ABSTAIN"
    assert "SOURCE_FAILURES" in r["reasons"] and "STALE_INPUTS" in r["reasons"]
