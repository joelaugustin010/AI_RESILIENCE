"""Evidence provenance and suitability states; no numeric quality score is used."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path


class EvidenceState(str, Enum):
    VERIFIED = "Verified"
    PROVISIONALLY_VERIFIED = "Provisionally verified"
    UNVERIFIED = "Unverified"
    OUTDATED = "Outdated"
    INCOMPLETE = "Incomplete"
    CONFLICTING = "Conflicting"
    UNAVAILABLE = "Unavailable"


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    local_path: str
    publisher: str
    source_url: str
    publication_date: str
    retrieval_date: str
    geographic_relevance: str
    temporal_relevance: str
    measurement_quality: str
    spatial_resolution: str
    completeness: str
    licence: str
    verification: str
    limitations: tuple[str, ...] = ()
    available: bool = True
    expected_sha256: str | None = None


_RECORDS = (
    EvidenceRecord(
        "cwc_telemetry_rainfall",
        "data/raw/kerala.csv",
        "Central Water Commission (agency field; NWDP match probable, not checksum-matched)",
        "https://nwdp.nwic.gov.in/dataset/rainfall-cwc-telemetry-hourly/resource/654dd5af-ec2c-4439-a8a5-f9bf5d61ab74",
        "NWDP resource updated 2026-01-24; local publication date unknown",
        "Unknown for local copy; catalog reviewed 2026-10-20",
        "Partial: four named stations; no validated Kochi spatial join",
        "Historical record only; source timezone and live freshness unknown",
        "Conflicting: 324 duplicate station-time groups have different values; no automatic deduplication",
        "Station observations; CRS, datum, and positional accuracy not established",
        "Partial station subset; source matching and completeness unconfirmed",
        "NWDP catalog says Other (Open); applicability to this unmatched file is unconfirmed",
        "Unverified local-source identity",
        ("Do not treat conflicting rows as independent observations or infer accumulated rainfall.",),
        expected_sha256=None,
    ),
    EvidenceRecord(
        "manual_rainfall",
        "data/raw/rainfall_manual_hr_kerala-sw_kl_1991_2020.csv",
        "Kerala Surface Water Department as listed by NWDP",
        "https://nwdp.nwic.gov.in/en/dataset/rainfall-manual-hourly-kerala-sw-department/resource/ceb9ffcf-927b-4b34-8ab5-6c3098dd95a9",
        "Portal resource updated 2025-03-05; local copy publication date unknown",
        "Unknown for local copy; portal metadata reviewed 2026-10-20",
        "Partial: 21 stations across Kerala; coordinates not validated for Kochi matching",
        "Historical only: local rows end 2014-12-31",
        "Partially documented: irregular intervals and no confirmed sampling schedule",
        "Station observations; CRS, positional accuracy, and timezone undocumented",
        "Partial: local period 2000-2014 despite filename's 1991-2020 label",
        "NWDP metadata says Other (Open); verify current portal terms before redistribution",
        "Provisionally verified catalog description; local retrieval/hash not established",
        ("No station-linked flood outcomes; benchmark is rainfall measurement only.",),
    ),
    EvidenceRecord(
        "manual_river_level",
        "data/raw/rwl_manual_hr_kerala_sw_031_2021_2025.csv",
        "Kerala Surface Water Department as listed by NWDP",
        "https://nwdp.nwic.gov.in/dataset/river-water-level-manual-hourly-kerala-sw-godavari/resource/fe95a85e-142d-4acf-83fc-24499afc546b",
        "Portal resource updated 2026-01-24",
        "Unknown for local copy; portal metadata reviewed 2026-10-20",
        "Partial: six named stations; basin/district metadata needs provider confirmation",
        "Historical observations through 2025-03-31; no live feed established",
        "Conflicting reference metadata: gauge zero/reference unresolved",
        "Station observations; CRS and positional accuracy undocumented",
        "Partial station subset; no outcome labels or local threshold links",
        "NWDP metadata says Other (Open); verify current portal terms before redistribution",
        "Provisionally verified catalog association; datum and geography unverified",
        ("No official warning threshold is linked to these values.",),
    ),
    EvidenceRecord(
        "telemetry_river_level",
        "data/raw/rwl_tel_hr_kerala_sw_031_2021_2025.csv",
        "Kerala Surface Water Department as listed by NWDP",
        "https://nwdp.nwic.gov.in/dataset/river-water-level-telemetry-hourly-kerala-surface-water-department/resource/a6de190e-40b6-484b-ad4c-a9f811f061ba",
        "Portal resource updated 2026-01-24",
        "Unknown for local copy; portal metadata reviewed 2026-10-20",
        "Partial: six stations; some source geographic descriptors are inconsistent",
        "Historical observations through 2025-03-10; no live feed established",
        "Conflicting: gauge reference and a large change across a 69-day gap unresolved",
        "Station observations; CRS and positional accuracy undocumented",
        "Partial station subset; no outcome labels or local threshold links",
        "NWDP metadata says Other (Open); verify current portal terms before redistribution",
        "Provisionally verified catalog association; measurements/datum not resolved",
        ("No correction or cross-station threshold comparison is justified.",),
    ),
    EvidenceRecord(
        "sample_air_pollution",
        "data/raw/air_pollution_data.csv",
        "Unknown",
        "Not documented",
        "Not documented",
        "Not documented",
        "Unknown",
        "Timestamp field present; source time basis not documented",
        "Unverified sample records",
        "Coordinates/source semantics undocumented",
        "Five sample rows; provenance incomplete",
        "Unknown",
        "Unverified",
        ("Not used for source attribution or numerical assessment.",),
    ),
    EvidenceRecord(
        "sample_hospital_vulnerability",
        "data/raw/hospital_vulnerability_data.csv",
        "Unknown",
        "Not documented",
        "Not documented",
        "Not documented",
        "Unknown",
        "Date range unavailable",
        "Scores and measurements undocumented",
        "Coordinates and CRS undocumented",
        "Five sample rows; provenance incomplete",
        "Unknown",
        "Unverified",
        ("Not used as an asset layer or vulnerability model.",),
    ),
    EvidenceRecord(
        "sample_disaster_probability",
        "data/raw/disaster_probability_data.csv",
        "Unknown; metadata describes demonstration/example rows",
        "Not documented",
        "Not documented",
        "Not documented",
        "Unknown",
        "Single-date example rows; not an event time series",
        "Example labels not independently verified",
        "No validated local spatial coverage",
        "Five rows; insufficient and undocumented for model evaluation",
        "Unknown",
        "Unverified",
        ("Model readiness audit blocks training on these rows.",),
        expected_sha256="687b059f610a99495fe3a522c1cb88a7f2fc185ce37f290551f886951aa8bea2",
    ),
    EvidenceRecord(
        "sample_compound_events",
        "data/raw/compound_disaster_data.csv",
        "Unknown",
        "Not documented",
        "Not documented",
        "Not documented",
        "Unknown",
        "Event dates present; overlap definitions absent",
        "Unverified labels",
        "Spatial matching not documented",
        "Five sample rows",
        "Unknown",
        "Unverified",
        ("Not used for compound-scenario calculations.",),
    ),
    EvidenceRecord(
        "kochi_boundary",
        "data/reference/kochi_corporation_boundary.geojson",
        "DataMeet Municipal Spatial Data; upstream attribution to Kerala OpenSDI",
        "https://opensdi.kerala.gov.in/layers/opensdi_data:geonode:KSUDP_KCH_Corporation_Boundary",
        "Not stated",
        "2026-10-20",
        "One provisional Kochi Corporation polygon",
        "Currency not established",
        "Not a measurement; source topology includes a self-intersection",
        "Single polygon; source scale and positional accuracy not stated",
        "One geometry, but not accepted as a valid spatial-coverage mask",
        "CC BY-SA 2.5 India per DataMeet README",
        "Provisionally verified community copy; live upstream not cross-checked",
        ("Administrative reference only; not a hazard or exposure layer.",),
        expected_sha256="02e3217959ed1edef2c91d852305e86d1d7ff55a90971a8f61fcd3a9ce0dcdbf",
    ),
    EvidenceRecord(
        "kochi_wards",
        "data/raw/koch_wards_2022.geojson",
        "DataMeet; source attributed to Kerala OpenSDI",
        "https://raw.githubusercontent.com/datameet/Municipal_Spatial_Data/master/Kochi/KCH_wards.geojson",
        "Source README says wards as of 2022",
        "2026-10-20",
        "Kochi Corporation ward snapshot",
        "Historical 2022 snapshot; current/legal validity unconfirmed",
        "Not a measurement; three of 77 source polygons self-intersect",
        "Polygon layer; source scale and positional accuracy unstated",
        "Partial: invalid features excluded and six ward identifiers missing",
        "CC BY-SA 2.5 India per DataMeet README",
        "Provisionally verified community copy; live upstream not cross-checked",
        ("Context layer only; not an exposure or legal boundary layer.",),
        expected_sha256="d8de90012f5c785b9d63c4b6f0b8bee69c72125da828051934de159d8f80dc17",
    ),
    EvidenceRecord(
        "hospital_directory",
        "data/raw/nihfw_national_hospital_directory.csv",
        "NIHFW; hosted by Government of India OGD",
        "https://www.data.gov.in/resource/national-hospital-directory-geo-code-and-additional-parameters-updated-till-last-month",
        "Published 2017-08-10; portal states updated 2025-06-02",
        "2026-10-20",
        "India-wide directory; Ernakulam subset is not spatially validated",
        "Directory may be stale; current operational status not confirmed",
        "Facility coordinates lack documented order/CRS and quality; duplicate/missing pairs",
        "Coordinate field exists; coordinate semantics and accuracy unknown",
        "Partial: Ernakulam subset has 31 unparseable coordinate pairs and duplicate groups",
        "Government Open Data License - India per portal",
        "Source provisionally authenticated; location values unverified",
        ("Review-only; do not convert to hazard exposure points.",),
        expected_sha256="1ddcad9f9b922142a4374c7b89b70fb6cefd8a257448c70a61e1c07d98845134",
    ),
    EvidenceRecord(
        "jrc_rp100_depth",
        "data/raw/jrc_glofas_rp100_ID185_N20_E70_depth.tif",
        "JRC / Copernicus GloFAS",
        "https://global-flood.emergency.copernicus.eu/technical-information/glofas/",
        "Tile index modified 2025-12-18",
        "2026-10-20",
        "Modeled global river-flood tile; Kochi coverage requires tile and boundary checks",
        "RP100 scenario layer; not current conditions or an event observation",
        "Modeled depth; documented DEM/model limitations and artifact warnings",
        "Approximately 90 m; WGS 84; depth in metres; -9999 NoData",
        "Incomplete for exposure: no verified asset geometry or masks applied",
        "CC BY 4.0 with attribution per JRC source notice",
        "Provisional: file metadata and tile checks documented; no local validation",
        ("No-data/transparent cells cannot establish safety; exposure join not completed.",),
        expected_sha256="93ba198ffeb0fb7436c6b97d66cf6b47b10cd59c4e6cf742a8aff59f46bdaf3b",
    ),
    EvidenceRecord(
        "ksdma_return_probability",
        "data/raw/ksdma_flood_return_probability_historical_10_25_50.zip",
        "Kerala State Disaster Management Authority (KSDMA); cited technical inputs include UNEP, UN GRID, CIMA Italy, and RMSI / National Insurance Academy",
        "https://sdma.kerala.gov.in/hazard-maps/",
        "Not stated for this exact ZIP; archive TIFF timestamps are 2026-04-12",
        "2026-10-20",
        "Statewide raster grid; not a delineated flood extent",
        "Historical 10/25/50-year labeled products; return-period interpretation needs provider confirmation",
        "Pixel-value units, class meaning, and NoData semantics undocumented",
        "EPSG:4326; 3004x5371 grid; cell size approximately 0.0008333 degrees",
        "Incomplete for interpretation and exposure use",
        "No dataset-specific reuse terms found",
        "Official catalogue source; contents not eligible for analysis pending clarification",
        ("Archive integrity passes; no hazard depth or probability should be inferred from raw cell values.",),
        expected_sha256="4057b36cdfc467ecaf618afb1e74b725187ef1d2a20326cdc1e4eb32df54605e",
    ),
)


def classify_evidence(record: EvidenceRecord) -> EvidenceState:
    """Classify suitability from explicit evidence properties, never a weighted score."""
    if not record.available:
        return EvidenceState.UNAVAILABLE
    if "conflict" in record.measurement_quality.casefold():
        return EvidenceState.CONFLICTING
    if record.temporal_relevance.casefold().startswith("outdated"):
        return EvidenceState.OUTDATED
    if (
        record.verification.casefold().startswith("unverified")
        or "hash mismatch" in record.verification.casefold()
        or record.publisher.casefold() == "unknown"
    ):
        return EvidenceState.UNVERIFIED
    if record.verification.casefold().startswith("provision"):
        return EvidenceState.PROVISIONALLY_VERIFIED
    if (
        record.completeness.casefold().startswith(("partial", "incomplete", "unknown"))
        or record.publication_date.casefold() in {"unknown", "not documented", "not stated"}
        or record.retrieval_date.casefold() in {"unknown", "not documented"}
        or record.licence.casefold() in {"unknown", "not documented"}
    ):
        return EvidenceState.INCOMPLETE
    if record.verification.casefold() == "verified":
        return EvidenceState.VERIFIED
    return EvidenceState.UNVERIFIED


def evidence_quality_inventory(project_root: Path) -> list[dict[str, str]]:
    """Return one provenance/quality record for every configured workflow item."""
    rows = []
    for record in _RECORDS:
        source_path = project_root / record.local_path
        exists = source_path.is_file()
        available = exists and record.available
        verification = record.verification
        if available and record.expected_sha256:
            actual_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
            if actual_sha256 == record.expected_sha256:
                verification = f"{verification}; source SHA-256 matched"
            else:
                verification = f"Unverified: source hash mismatch (expected {record.expected_sha256}; observed {actual_sha256})"
        state = classify_evidence(
            replace(record, available=available, verification=verification)
        )
        rows.append(
            {
                "Evidence ID": record.evidence_id,
                "Dataset / file": record.local_path,
                "Evidence state": state.value,
                "Source authority": record.publisher,
                "Source URL": record.source_url,
                "Publication / update date": record.publication_date,
                "Retrieval / review date": record.retrieval_date,
                "Geographic relevance": record.geographic_relevance,
                "Temporal relevance": record.temporal_relevance,
                "Measurement quality": record.measurement_quality,
                "Spatial resolution / CRS": record.spatial_resolution,
                "Completeness": record.completeness,
                "Licence": record.licence,
                "Verification status": verification,
                "Limitations": "; ".join(record.limitations) if record.limitations else "None documented in this register.",
            }
        )
    return rows
