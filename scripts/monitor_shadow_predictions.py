"""Shadow-only drift, freshness and service monitoring; never issues warnings."""
import argparse, csv, json
from pathlib import Path
import numpy as np
from scipy.stats import ks_2samp

def read_csv(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as f: return list(csv.DictReader(f))

def psi(ref,cur,bins=10):
    edges=np.unique(np.quantile(ref,np.linspace(0,1,bins+1)))
    if len(edges)<3: return 0.0
    edges[0],edges[-1]=-np.inf,np.inf
    a=np.histogram(ref,bins=edges)[0]/len(ref); b=np.histogram(cur,bins=edges)[0]/len(cur)
    a=np.clip(a,1e-6,None); b=np.clip(b,1e-6,None)
    return float(np.sum((b-a)*np.log(b/a)))

def build_report(reference,current,features,max_age=180,baseline_approved=False):
    required={"input_age_minutes","latency_ms","source_status","model_status"}
    for name,rows in (("reference",reference),("current",current)):
        if not rows: raise ValueError(name+" ledger is empty")
        missing=required-set(rows[0])
        if missing: raise ValueError(name+" ledger missing "+str(sorted(missing)))
    drift={}
    for feature in features:
        r=np.asarray([float(x[feature]) for x in reference]); c=np.asarray([float(x[feature]) for x in current])
        r=r[np.isfinite(r)]; c=c[np.isfinite(c)]
        if min(len(r),len(c))<20: drift[feature]={"status":"INSUFFICIENT_DATA"}; continue
        ks=ks_2samp(r,c)
        drift[feature]={"ks_statistic":float(ks.statistic),"ks_p_value":float(ks.pvalue),"psi":psi(r,c)}
    ages=np.asarray([float(x["input_age_minutes"]) for x in current])
    latency=np.asarray([float(x["latency_ms"]) for x in current])
    sf=sum(x["source_status"].upper() not in {"OK","SUCCESS"} for x in current)
    mf=sum(x["model_status"].upper() not in {"OK","SUCCESS"} for x in current)
    stale=int((ages>max_age).sum())
    alerts=[k for k,v in drift.items() if v.get("psi",0)>=.2 or v.get("ks_p_value",1)<.01]
    reasons=[]
    if stale: reasons.append("STALE_INPUTS")
    if sf: reasons.append("SOURCE_FAILURES")
    if mf: reasons.append("MODEL_FAILURES")
    if alerts: reasons.append("FEATURE_DRIFT")
    state="HEALTHY_SHADOW" if not reasons else ("VALIDATED_BASELINE_FALLBACK_CANDIDATE" if baseline_approved and not stale and not sf else "UNAVAILABLE_ABSTAIN")
    return {"monitor_type":"SHADOW_ONLY","feature_drift":drift,"drift_alert_features":alerts,
            "input_age_p95_minutes":float(np.quantile(ages,.95)),"stale_rows":stale,
            "latency_p50_ms":float(np.quantile(latency,.5)),"latency_p95_ms":float(np.quantile(latency,.95)),
            "source_failure_rows":sf,"model_failure_rows":mf,"reasons":reasons,"safe_state":state,
            "fallback_policy":"Use only separately validated approved baseline." if state=="VALIDATED_BASELINE_FALLBACK_CANDIDATE" else "Abstain; show deterministic preparedness guidance.",
            "automatic_operational_promotion":False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reference",required=True); p.add_argument("--current",required=True)
    p.add_argument("--features",required=True); p.add_argument("--output",default="reports/shadow_monitor.json")
    p.add_argument("--max-age-minutes",type=float,default=180); p.add_argument("--baseline-approved",action="store_true")
    a=p.parse_args()
    report=build_report(read_csv(a.reference),read_csv(a.current),[x.strip() for x in a.features.split(",") if x.strip()],a.max_age_minutes,a.baseline_approved)
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2,allow_nan=False)+"\\n",encoding="utf-8")
    print(json.dumps({"safe_state":report["safe_state"],"reasons":report["reasons"],"output":str(out)})); return 0
if __name__=="__main__": raise SystemExit(main())
