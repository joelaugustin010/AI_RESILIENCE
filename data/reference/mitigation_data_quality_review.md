# AI RESILIENCE — Mitigation Evidence Data Quality Review

**Scope:** Local inspection of seven downloaded files from the official-source collection script.  
**Review date:** 8 November 2026  
**Status:** Evidence review documented; raw files are not committed by this change.

## Executive decision

Use selected Ernakulam observations as **supporting historical context only**. Do not describe them as live Kochi measurements, direct urban-waterlogging observations, or ML-ready training data. The raw downloads remain in the user's local `data/raw/source_downloads/` directory and are not included in this repository change.

## Dataset findings

| Source file | Local finding | Decision |
|---|---|---|
| Kerala SW rainfall 1991–2020 | 24 records, 2015-01-01 to 2018-05-17; no Ernakulam rows | Exclude from Kochi trend analysis |
| Kerala SW rainfall 2021–2025 | 188,045 statewide records; 14,347 Ernakulam records across 9 stations; irregular intervals | Conditional historical context; preserve station/time gaps |
| Kerala SW discharge 2001–2025 | 4,904 records, all in 2011; no Ernakulam rows | Exclude from Kochi analysis pending source clarification |
| CWC daily discharge 2001–2025 | 26,692 Ernakulam rows across KALAMPUR, NEELEESWARAM, PALLIPPADY and RAMAMANGALAM | Conditional watershed context; conflicting duplicates need source review |
| CWC velocity/discharge 2021–2025 | 6,128 Ernakulam rows; missing area 16.30%, velocity 29.83%, level 7.80% | Conditional context; do not impute missing values without a documented method |
| KSDMA Ernakulam historic and RCP 8.5 PDFs | PDF signatures validated; map content not yet inspected | Not yet spatially integrated |
| GSI and KSDMA flood-return ZIPs | Five ZIP downloads failed local signature validation | Exclude until verified |

## Duplicate and overlap checks

- CWC daily discharge: 153 station/timestamp groups had conflicting values; 2 duplicate groups had identical values.
- CWC velocity/discharge: 70 station/timestamp groups had conflicting values; 1 duplicate group had identical values.
- Across 6,049 common Ernakulam station/timestamps between the two CWC files, each timestamp had at least one matching discharge value. This indicates shared observations or a shared upstream source; treat them as related evidence, not independent corroboration.
- Do not average, delete, or silently deduplicate conflicting records. Preserve original rows and source provenance pending clarification.

## Rainfall cadence and geography

The nine Ernakulam stations in the 2021–2025 rainfall file do not provide a continuous, uniform hourly series. Thirty minutes was the most common interval at each of the nine stations in the user's interval output; other intervals and gaps also occur. Do not convert missing intervals to zero rainfall or calculate rolling/hourly totals until cadence and accumulation semantics are validated.

These stations are district-level observations. They must not be labelled as central Kochi urban-core measurements without a geographic check.

## Interpretation safeguards

1. Keep the raw files unchanged; any cleaning must produce a separate derived dataset and a reproducible log.
2. Retain station, timestamp, units, agency and original source reference with every derived observation.
3. Do not count the two overlapping CWC files as independent sources in evidence scoring.
4. Do not treat river discharge as road-level flood depth or drainage performance.
5. Do not interpret a climate scenario or return period as a deterministic prediction.
6. No dataset in this review is approved as ML training data. A supervised model requires a defined target, traceable labels, leakage-safe splits, sufficient examples and holdout evaluation against a baseline.

## Integration boundary

This review is documentation and source-quality metadata. It does not load the raw files into the Streamlit app, change model readiness, generate flood forecasts, estimate avoided damage, or approve investments. The Mitigation Budget's transparent human-assessed priority score and arithmetic portfolio scenario remain separate from ML.

## Reproducibility note

Counts and quality statistics above were produced by the user's local Python/PowerShell validation scripts and supplied in the project conversation. They have not been independently recomputed from raw files in this repository because raw data are intentionally not committed here.
