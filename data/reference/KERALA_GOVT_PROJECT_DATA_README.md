# Kerala government completed-project source dataset

## Current collection

File: `kerala_soil_conservation_completed_projects.csv`

The CSV contains **29 project records** transcribed from three official Government of Kerala monitoring/reporting sources:

- **13** soil/watershed conservation schemes from the Department of Economics & Statistics evaluation report.
- **14** cyclone-shelter projects from KSDMA implementation status.
- **2** KWA PASK project profiles.

## Sources and fields

### 1. Department of Economics & Statistics
*Evaluation Study on Soil Conservation in Kerala 2019–20* (published 2022).
Source: https://ecostat.kerala.gov.in/storage/publications/640.pdf

Table 2.1 (report p.16) lists district, scheme, treated area and total project-work cost. Scheme descriptions on pp.4–7 provide start/completion dates for some projects. The 13 rows are broad rural watershed/soil-conservation records.

### 2. Kerala State Disaster Management Authority
Implementation status, Cyclone Risk Mitigation Infrastructure:
https://sdma.kerala.gov.in/implementation-status/

Fourteen completed shelter records are included where plinth area, commencement date, completion date and reported cost of completion were visible. Rows with date ambiguity or final-bill processing still underway were excluded. The reported cost-of-completion field is preserved in source notes; it is not represented as a final paid bill.

### 3. Kerala Water Authority PASK
- AMRUT Kollam Corporation water connections, Phase II: https://pask.kwa.kerala.gov.in/project/profile/reference/d1e96978c6935ec01d995b1b8e4d8c33iIWMeA
- RKI sewerage survey for four municipal corporations: https://pask.kwa.kerala.gov.in/project/profile/reference/134dd796229f80f23b75af20495b8d50hYaHdYo

These records use total bill paid as the cost target. The sewerage survey does not report a start date, so duration is intentionally blank.

## Data handling and limitations

- `actual_cost_inr` is the source-reported project-work cost, KSDMA cost of completion, or KWA total bill paid as described in each row's `source_notes`. These bases are not identical; review before pooling or interpreting model results.
- `scope_quantity` and `scope_unit` preserve the reported area, connection count or municipal-corporation count. Different units are not directly interchangeable.
- `duration_months` is calculated only where exact reported start and completion dates are available, using elapsed days / 30.4375 and rounding to one decimal. It is blank when exact dates are unavailable.
- Broad `intervention` and `area_type` labels are research categories assigned from the project descriptions, not necessarily verbatim source fields.
- The Palakkad soil-conservation cost uses Table 2.1; the report graph contains a conflicting value, flagged in the CSV source notes.
- The dataset is **29 rows**, not 40. Cost records with complete scope/cost/source fields are currently below the 40-record threshold; the delivery subset is smaller because some sources do not report exact start dates. It is not sufficient to train either model under the current minimum-record gate.
- Even after reaching 40 rows, a mixed dataset is not automatically suitable. Check source comparability, intervention families, price year, scope definitions, geographic coverage, duplicate projects/packages, and holdout performance.
- These records are not all Kochi projects. Do not transfer their unit costs to urban Kochi without local suitability review and price-year adjustment.
- Do not add sanctioned estimates, tender estimates, unpaid bills, synthetic examples, or ongoing-project values as if they were actual completed-project costs.
- Preserve the source URL and source notes for every added record.

## Model readiness

Cost and duration evidence gates are now independent:
- Cost model: at least 40 complete, traceable cost records with valid intervention, area context, scope, unit and source reference.
- Delivery model: at least 40 such records with an additional valid, source-supported duration.
- Both models must beat the median baseline on the holdout set before estimates are enabled.

The current 23-row dataset does **not** unlock ML. Cost records without duration may contribute to cost-model training after the minimum is reached; they cannot train the delivery model.

## Next collection priorities

Prioritise additional KWA, LSGD/Sulekha, KIIDC, PWD and Irrigation Department project profiles where project-level completed status, final paid expenditure or clearly defined cost-of-completion, measurable scope, and traceable references are available. Keep separate source cohorts when their cost basis or scope units differ.


## Supplemental government and private-sector collection (8 November 2026)

A separate lead register is maintained at `mitigation_project_supplemental_candidates.csv`. It contains four additional project references identified from official government/audit pages and private-sector project portfolios:

- KIIDC Kuppithodu regulator: official project page reports construction dates, completed status and ₹55.82 crore project cost; the project is multi-component and its scope is not yet suitable for the current single-quantity model.
- Kochi Elamkulam 5 MLD STP: CAG audit reports physical completion in May 2022 and expenditure of ₹12.06 crore; commissioning followed in October 2024. No verified start date was captured, so duration is blank.
- Rajagiri institutional STP, Aluva: contractor portfolio lists a ₹4,39,96,403 contract amount, but its additional-work field repeats the same amount and final paid expenditure/completion date are not stated.
- Hotel Food Magic 6 KLD STP, Kunnamkulam: vendor case study reports a ₹5.9 lakh turnkey value and operational installation, but no completion date or independent final expenditure.

The supplemental file is a **source-lead and audit register**, not an extension of the ML training CSV. All four records are currently marked not eligible for ML; the Elamkulam record is a cost-model review candidate only after feature and cohort comparability checks. Contract values, vendor-reported values and audited expenditure must not be pooled as if they were identical cost targets.

Additional aggregate context (not project-level training rows): AMRUT Kerala's city-wise progress page reports Kochi storm-water drainage (SWD) 49 projects, 48 completed and ₹45.45 crore expenditure as at 31 August 2024. These are aggregate statistics and must not be expanded into 49 fabricated project records:
https://amrutkerala.org/city-wise-progress/

Other official discovery source: KIIDC completed-projects listing:
https://kiidc.kerala.gov.in/category/our-current-projects/completed-projects/
