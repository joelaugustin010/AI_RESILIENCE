from scripts.audit_observation_panel import audit

def flood_row():
    return {"event_id":"e1","site_id":"s1","observation_time_utc":"2026-01-01T00:00:00Z",
    "rain_observed_at_utc":"2026-01-01T00:00:00Z","rain_mm_24h":"80",
    "river_observed_at_utc":"2026-01-01T00:00:00Z","river_level_m":"2.1",
    "tide_observed_at_utc":"2026-01-01T00:00:00Z","tide_level_m":"0.8","flood_observed":"1",
    "sar_scene_id":"S1","sar_acquired_at_utc":"2026-01-01T01:00:00Z","footprint_uri":"event.geojson",
    "source_record_id":"r1","source_publisher":"official","license":"terms","adjudication_status":"reviewed"}

def test_flood_panel_audit_is_never_training_clearance():
    r=audit([flood_row()],"flood")
    assert r["training_ready"] is False
    assert r["status"]=="AUDIT_ONLY_REQUIRES_HUMAN_ADJUDICATION"

def test_flood_panel_flags_time_misalignment():
    x=flood_row(); x["sar_acquired_at_utc"]="2026-01-02T00:00:00Z"
    r=audit([x],"flood",max_offset_hours=6)
    assert any(p["issue"]=="TIME_ALIGNMENT_EXCEEDED" for p in r["problems"])

def test_landslide_non_event_requires_monitored_coverage():
    row={"site_id":"s","slope_unit_id":"u","monitoring_start_utc":"2026-01-01T00:00:00Z",
    "monitoring_end_utc":"2026-01-02T00:00:00Z","monitoring_coverage_fraction":"0.5",
    "inspection_method":"field","inspected_by":"surveyor","event_observed":"0",
    "source_record_id":"r","source_publisher":"agency","license":"terms","adjudication_status":"reviewed"}
    r=audit([row],"landslide")
    assert any(p["issue"]=="UNSUPPORTED_NON_EVENT_LABEL" for p in r["problems"])


def test_flood_label_requires_explicit_adjudication():
    row=flood_row(); row["adjudication_status"]="unreviewed"
    r=audit([row],"flood")
    assert any(p["issue"]=="FLOOD_LABEL_NOT_ADJUDICATED" for p in r["problems"])
    assert r["status"]=="BLOCKED_DATA_QUALITY"

def test_landslide_unknown_label_is_counted_once():
    row={"site_id":"s","slope_unit_id":"u","monitoring_start_utc":"2026-01-01T00:00:00Z",
    "monitoring_end_utc":"2026-01-02T00:00:00Z","monitoring_coverage_fraction":"1.0",
    "inspection_method":"field","inspected_by":"surveyor","event_observed":"",
    "source_record_id":"r","source_publisher":"agency","license":"terms","adjudication_status":"unknown"}
    r=audit([row],"landslide")
    assert r["unknown_or_unlabelled_rows"]==1
    assert r["training_ready"] is False

def test_missing_panel_identity_blocks_audit():
    row=flood_row(); row["site_id"]=""
    r=audit([row],"flood")
    assert any(p["issue"]=="MISSING_PANEL_IDENTITY" for p in r["problems"])
    assert r["status"]=="BLOCKED_DATA_QUALITY"
