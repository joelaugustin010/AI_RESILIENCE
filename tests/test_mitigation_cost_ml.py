import numpy as np
import pandas as pd
import pytest
from src.mitigation_cost_ml import CostModelDataError,estimate_cost,prepare_cost_records,train_cost_model

def records(n=80):
    rng=np.random.default_rng(7); interventions=["Drainage","Rain garden","Pump","Storage"]
    areas=["Urban road","Residential","Commercial"]; units=["metres","units","sq metres"]
    rows=[]
    for i in range(n):
        name=interventions[i%4]; qty=float(rng.integers(10,300)); months=float(rng.integers(1,18))
        cost=18000+qty*850+months*1400+interventions.index(name)*12000+rng.normal(0,1200)
        rows.append({"intervention":name,"area_type":areas[i%3],"scope_quantity":qty,
          "scope_unit":units[i%3],"duration_months":months,"actual_cost_inr":max(1000,cost),
          "source_reference":f"Completed project {i+1}"})
    return pd.DataFrame(rows)

def test_requires_sourced_records_and_minimum_sample():
    data=records(45); data.loc[0,"source_reference"]=""
    assert len(prepare_cost_records(data))==44
    with pytest.raises(CostModelDataError,match="At least 40"):
        prepare_cost_records(records(20))

def test_missing_schema_rejected():
    with pytest.raises(CostModelDataError,match="Missing required columns"):
        prepare_cost_records(pd.DataFrame({"actual_cost_inr":[100]}))

def test_training_reports_holdout_and_baseline():
    m=train_cost_model(records())["metrics"]
    assert m["records_used"]==80 and m["validation_records"]>=8
    assert m["mae_inr"]>=0 and m["baseline_mae_inr"]>=0

def test_prediction_validation_and_error_band():
    model=train_cost_model(records())
    if not model["metrics"]["beats_baseline"]: pytest.skip("Fixture did not beat baseline.")
    result=estimate_cost(model,intervention="Drainage",area_type="Urban road",
        scope_quantity=100,scope_unit="metres",duration_months=6)
    assert result["lower_estimate_inr"]<=result["estimated_cost_inr"]<=result["upper_estimate_inr"]
    with pytest.raises(CostModelDataError):
        estimate_cost(model,intervention="Drainage",area_type="Urban road",
            scope_quantity=0,scope_unit="metres",duration_months=6)

def test_model_blocked_when_baseline_not_beaten():
    model=train_cost_model(records()); model["metrics"]["beats_baseline"]=False
    with pytest.raises(CostModelDataError,match="median baseline"):
        estimate_cost(model,intervention="Drainage",area_type="Urban road",
            scope_quantity=100,scope_unit="metres",duration_months=6)
