"""Evidence-gated ML cost estimation from sourced completed projects."""
from __future__ import annotations
import math
from typing import Any
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

CATS=("intervention","area_type","scope_unit")
NUMS=("scope_quantity","duration_months")
FEATURES=CATS+NUMS
TARGET="actual_cost_inr"
REQUIRED=FEATURES+(TARGET,"source_reference")
MIN_ROWS=40

class CostModelDataError(ValueError):
    """Historical records do not meet model readiness requirements."""

def prepare_cost_records(records: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(records,pd.DataFrame):
        raise CostModelDataError("Upload a CSV table of completed project records.")
    missing=[c for c in REQUIRED if c not in records.columns]
    if missing:
        raise CostModelDataError("Missing required columns: "+", ".join(missing))
    frame=records.loc[:,list(REQUIRED)].copy()
    for c in CATS+("source_reference",):
        frame[c]=frame[c].fillna("").astype(str).str.strip()
    for c in NUMS+(TARGET,):
        frame[c]=pd.to_numeric(frame[c],errors="coerce")
    valid=(frame[list(CATS)].ne("").all(axis=1)&frame.source_reference.ne("")
           &frame[list(NUMS+(TARGET,))].notna().all(axis=1))
    frame=frame.loc[valid].copy()
    finite=frame[list(NUMS+(TARGET,))].apply(
        lambda col: col.map(lambda v: math.isfinite(float(v)))
    ).all(axis=1)
    positive=(frame.scope_quantity>0)&(frame.duration_months>0)&(frame[TARGET]>0)
    frame=frame.loc[finite&positive].reset_index(drop=True)
    if len(frame)<MIN_ROWS:
        raise CostModelDataError(
            f"Only {len(frame)} complete, sourced records are usable. "
            f"At least {MIN_ROWS} are required before training."
        )
    if frame[TARGET].nunique()<5:
        raise CostModelDataError("The actual-cost target has too few distinct values.")
    return frame

def train_cost_model(records: pd.DataFrame) -> dict[str,Any]:
    frame=prepare_cost_records(records)
    X=frame.loc[:,list(FEATURES)]; y=frame[TARGET].astype(float)
    n_test=max(8,math.ceil(len(frame)*.2))
    if len(frame)-n_test<20:
        raise CostModelDataError("Not enough records remain for holdout evaluation.")
    Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=n_test,random_state=42)
    prep=ColumnTransformer([
        ("cat",Pipeline([("impute",SimpleImputer(strategy="most_frequent")),
                         ("onehot",OneHotEncoder(handle_unknown="ignore"))]),list(CATS)),
        ("num",Pipeline([("impute",SimpleImputer(strategy="median")),
                         ("scale",StandardScaler())]),list(NUMS)),
    ])
    model=Pipeline([("prep",prep),("rf",RandomForestRegressor(
        n_estimators=300,min_samples_leaf=2,random_state=42,n_jobs=-1))])
    baseline=DummyRegressor(strategy="median")
    model.fit(Xtr,ytr); baseline.fit(Xtr,ytr)
    pred=model.predict(Xte); base_pred=baseline.predict(Xte)
    mae=float(mean_absolute_error(yte,pred))
    base_mae=float(mean_absolute_error(yte,base_pred))
    return {
        "model":model,
        "metrics":{
            "records_used":len(frame),"training_records":len(Xtr),
            "validation_records":len(Xte),"mae_inr":mae,
            "baseline_mae_inr":base_mae,"r2":float(r2_score(yte,pred)),
            "beats_baseline":mae<base_mae,
            "validation_method":"Fixed 80/20 holdout; random_state=42",
        },
        "categories":{c:sorted(frame[c].unique().tolist()) for c in CATS},
    }

def estimate_cost(trained:dict[str,Any],*,intervention:str,area_type:str,
                  scope_quantity:float,scope_unit:str,duration_months:float)->dict[str,float]:
    metrics=trained["metrics"]
    if not metrics["beats_baseline"]:
        raise CostModelDataError("Model did not outperform the median baseline on held-out records.")
    numeric={"scope_quantity":float(scope_quantity),"duration_months":float(duration_months)}
    if any(not math.isfinite(v) or v<=0 for v in numeric.values()):
        raise CostModelDataError("Scope quantity and duration must be finite values greater than zero.")
    categorical={"intervention":str(intervention).strip(),
                  "area_type":str(area_type).strip(),"scope_unit":str(scope_unit).strip()}
    if any(not v for v in categorical.values()):
        raise CostModelDataError("Choose an intervention, area type and scope unit.")
    sample=pd.DataFrame([{**categorical,**numeric}],columns=FEATURES)
    estimate=float(trained["model"].predict(sample)[0]); mae=float(metrics["mae_inr"])
    return {"estimated_cost_inr":max(0.0,estimate),"validation_error_inr":mae,
            "lower_estimate_inr":max(0.0,estimate-mae),"upper_estimate_inr":estimate+mae}
