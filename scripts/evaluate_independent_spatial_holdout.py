"""Evaluate frozen model probabilities on disjoint geographic and event holdouts."""
import argparse, csv, json
from pathlib import Path
from src.ml.operational_validation import evaluate_independent_spatial_holdout

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--predictions",required=True)
    p.add_argument("--output",default="reports/independent_spatial_holdout.json")
    p.add_argument("--bootstrap-iterations",type=int,default=1000)
    a=p.parse_args()
    with Path(a.predictions).open(encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f))
    report=evaluate_independent_spatial_holdout(rows,bootstrap_iterations=a.bootstrap_iterations)
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,allow_nan=False)+"\\n",encoding="utf-8")
    print(json.dumps({"output":str(out),"groups":report["geographic_groups"],"positive_events":report["independent_positive_events"],"candidate_review_screen_passed":report["candidate_review_screen_passed"],"operational_clearance":False}))
    return 0
if __name__=="__main__": raise SystemExit(main())
