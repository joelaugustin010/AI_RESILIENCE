"""Audit real-observation event panels without converting unknowns to negatives."""
import argparse, csv, json
from datetime import datetime, timezone
from pathlib import Path

FLOOD_REQUIRED=("event_id","site_id","observation_time_utc","rain_observed_at_utc","rain_mm_24h",
"river_observed_at_utc","river_level_m","tide_observed_at_utc","tide_level_m","flood_observed",
"sar_scene_id","sar_acquired_at_utc","footprint_uri","source_record_id","source_publisher","license","adjudication_status")
LANDSLIDE_REQUIRED=("site_id","slope_unit_id","monitoring_start_utc","monitoring_end_utc","monitoring_coverage_fraction",
"inspection_method","inspected_by","event_observed","source_record_id","source_publisher","license","adjudication_status")

def dt(value):
    parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    if parsed.tzinfo is None: raise ValueError("timestamps must include UTC offset")
    return parsed.astimezone(timezone.utc)

def audit(rows,kind,max_offset_hours=6.0):
    if kind not in {"flood", "landslide"}: raise ValueError("kind must be flood or landslide")
    if not rows: raise ValueError("Observation panel is empty.")
    if not 0 <= max_offset_hours <= 24: raise ValueError("max_offset_hours must be between 0 and 24")
    required=FLOOD_REQUIRED if kind=="flood" else LANDSLIDE_REQUIRED
    missing=sorted(set(required)-set(rows[0]))
    if missing: raise ValueError("Missing required columns: "+", ".join(missing))
    problems=[]; unknown=0; duplicate=set()
    for i,row in enumerate(rows, start=2):
        key=(row.get("event_id"),row.get("site_id"),row.get("observation_time_utc")) if kind=="flood" else (row.get("site_id"),row.get("monitoring_start_utc"),row.get("monitoring_end_utc"))
        if key in duplicate: problems.append({"row":i,"issue":"DUPLICATE_PANEL_KEY"})
        duplicate.add(key)
        identity_fields = ("event_id", "site_id") if kind == "flood" else ("site_id", "slope_unit_id")
        if any(not row.get(field, "").strip() for field in identity_fields):
            problems.append({"row":i,"issue":"MISSING_PANEL_IDENTITY"})
        if not row.get("source_record_id") or not row.get("source_publisher") or not row.get("license"):
            problems.append({"row":i,"issue":"MISSING_SOURCE_PROVENANCE"})
        try:
            if kind=="flood":
                obs=dt(row["observation_time_utc"])
                for field in ("rain_observed_at_utc","river_observed_at_utc","tide_observed_at_utc","sar_acquired_at_utc"):
                    offset=abs((dt(row[field])-obs).total_seconds())/3600
                    if offset>max_offset_hours: problems.append({"row":i,"issue":"TIME_ALIGNMENT_EXCEEDED","field":field,"offset_hours":round(offset,3)})
                if row["flood_observed"] not in {"0","1"} or row.get("adjudication_status", "").casefold() not in {"reviewed", "confirmed", "adjudicated"}:
                    problems.append({"row":i,"issue":"FLOOD_LABEL_NOT_ADJUDICATED"})
                if row["flood_observed"]=="1" and not row.get("footprint_uri"): problems.append({"row":i,"issue":"EVENT_WITHOUT_FOOTPRINT_REFERENCE"})
            else:
                start,end=dt(row["monitoring_start_utc"]),dt(row["monitoring_end_utc"])
                if end<=start: problems.append({"row":i,"issue":"INVALID_MONITORING_INTERVAL"})
                coverage=float(row["monitoring_coverage_fraction"])
                if not 0<=coverage<=1: problems.append({"row":i,"issue":"INVALID_MONITORING_COVERAGE"})
                label = row.get("event_observed", "")
                reviewed = row.get("adjudication_status", "").casefold() in {"reviewed", "confirmed", "adjudicated"}
                if label not in {"0", "1"}:
                    unknown += 1
                elif not reviewed:
                    problems.append({"row":i,"issue":"LANDSLIDE_LABEL_NOT_ADJUDICATED"})
                if label == "0" and (coverage<0.9 or not row.get("inspection_method") or not row.get("inspected_by") or not reviewed):
                    problems.append({"row":i,"issue":"UNSUPPORTED_NON_EVENT_LABEL"})
        except (ValueError,KeyError) as exc:
            problems.append({"row":i,"issue":"INVALID_OR_MISSING_VALUE","detail":str(exc)})
    blocking=sum(x["issue"] in {"MISSING_SOURCE_PROVENANCE","MISSING_PANEL_IDENTITY","INVALID_OR_MISSING_VALUE","LANDSLIDE_LABEL_NOT_ADJUDICATED","UNSUPPORTED_NON_EVENT_LABEL","FLOOD_LABEL_NOT_ADJUDICATED","TIME_ALIGNMENT_EXCEEDED","DUPLICATE_PANEL_KEY","EVENT_WITHOUT_FOOTPRINT_REFERENCE"} for x in problems)
    return {"panel_kind":kind,"rows":len(rows),"problems":problems,"problem_count":len(problems),
            "unknown_or_unlabelled_rows":unknown,"training_ready":False,
            "status":"BLOCKED_DATA_QUALITY" if blocking else "AUDIT_ONLY_REQUIRES_HUMAN_ADJUDICATION",
            "interpretation":"Schema and timing audit only. Does not verify source truth, legal access, spatial accuracy or model suitability."}

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--kind",choices=["flood","landslide"],required=True)
    p.add_argument("--input",required=True); p.add_argument("--output",default="reports/observation_panel_audit.json")
    p.add_argument("--max-offset-hours",type=float,default=6); a=p.parse_args()
    with Path(a.input).open(encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f))
    report=audit(rows,a.kind,a.max_offset_hours); out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":report["status"],"rows":report["rows"],"problems":report["problem_count"],"training_ready":False})); return 0
if __name__=="__main__": raise SystemExit(main())
