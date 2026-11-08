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

The current 29-row dataset does **not** unlock ML. Cost records without duration may contribute to cost-model training after the minimum is reached; they cannot train the delivery model.

## Next collection priorities

Prioritise additional KWA, LSGD/Sulekha, KIIDC, PWD and Irrigation Department project profiles where project-level completed status, final paid expenditure or clearly defined cost-of-completion, measurable scope, and traceable references are available. Keep separate source cohorts when their cost basis or scope units differ.


## Supplemental government and private-sector collection (8 November 2026)

A separate lead register is maintained at `mitigation_project_supplemental_candidates.csv`. It contains twenty-nine project references identified from official government/audit pages and private-sector project portfolios:

- KIIDC Kuppithodu regulator: official project page reports construction dates, completed status and ₹55.82 crore project cost; the project is multi-component and its scope is not yet suitable for the current single-quantity model.
- Kochi Elamkulam 5 MLD STP: CAG audit reports physical completion in May 2022 and expenditure of ₹12.06 crore; commissioning followed in October 2024. No verified start date was captured, so duration is blank.
- Rajagiri institutional STP, Aluva: contractor portfolio lists a ₹4,39,96,403 contract amount, but its additional-work field repeats the same amount and final paid expenditure/completion date are not stated.
- Hotel Food Magic 6 KLD STP, Kunnamkulam: vendor case study reports a ₹5.9 lakh turnkey value and operational installation, but no completion date or independent final expenditure.

The supplemental file is a **source-lead and audit register**, not an extension of the ML training CSV. All four records are currently marked not eligible for ML; the Elamkulam record is a cost-model review candidate only after feature and cohort comparability checks. Contract values, vendor-reported values and audited expenditure must not be pooled as if they were identical cost targets.

Additional aggregate context (not project-level training rows): AMRUT Kerala's city-wise progress page reports Kochi storm-water drainage (SWD) 49 projects, 48 completed and ₹45.45 crore expenditure as at 31 August 2024. These are aggregate statistics and must not be expanded into 49 fabricated project records:
https://amrutkerala.org/city-wise-progress/

Other official discovery source: KIIDC completed-projects listing:
https://kiidc.kerala.gov.in/category/our-current-projects/completed-projects/


### Additional KWA records reviewed (8 November 2026)
- KWA PASK DEPOSIT-KMC pipeline replacement along Ashan Road, Kochi Division 48: start 19 August 2024; work completed 16 December 2024; total bill paid ₹1,128,549; final bill submitted 18 January 2025. PASK does not expose a comparable pipe-length quantity in the captured profile. Retained in supplemental candidates, excluded from current ML training.
- KWA PASK Muttathara 107 MLD STP three-year operation-and-maintenance package: reported total bill paid ₹48,618,926; start 1 September 2019; actual completion 31 January 2023; subsequent O&M contract commenced 1 February 2023. Retained as O&M evidence, not mixed with capital construction records.

### Kochi AMRUT audit evidence
CAG Performance Audit on AMRUT in Kerala reports 49 Kochi storm-water-drain works with project cost ₹53.86 crore; 48 completed with expenditure ₹34.15 crore. Audit test-checked nine works (project cost ₹28.18 crore), reporting ₹21.47 crore spent and noting that much of the spending related to routine maintenance. This is an aggregate/audit finding, not 49 project-level records. It must not be expanded into synthetic rows. Source: https://cag.gov.in/uploads/download_audit_report/2025/Print-version-english_AMRUT_Kerala_10.12.25-with-legislature-date-0699d302521f715.11884185.pdf

KIIDC's completed-project listing includes Punnamada post-flood renovation; the page states final billing was still in progress, so it is a discovery lead and not treated as a final-cost training record. Source: https://kiidc.kerala.gov.in/category/our-current-projects/completed-projects/


### Further KWA project leads reviewed (8 November 2026)
Four additional KWA PASK profiles have been added to the supplemental register, bringing it to **29 source leads** (the separate core training CSV remains at **29 records**):
- Paittukattu lane, Division 36, Kochi Corporation: 63 mm PVC pipeline extension; ₹62,000 AS/TS; profile has no final bill paid or actual completion date, and no pipe length.
- Honest Byline Road, Kalamassery: ₹80,000 AS/TS; profile shows completed status but no actual completion date, no scope quantity and no final paid expenditure.
- Nanma One apartment complex, Vyttila/Tripunithura: ₹560,000 AS and ₹490,000 TS; completed 16 July 2026, but bill submitted/paid fields are both zero and scope quantity is absent.
- Ward X pipeline extension, Marady Panchayat: ₹1,266,558 bill submitted; payment is not confirmed, and measurable pipeline quantity and actual completion date were not captured.

These are **discovery leads only**. Sanctioned/technical-sanction amounts and submitted-but-unpaid bills are not actual final expenditure. None of these four is marked ML-eligible. The new leads are retained to guide source follow-up, not to increase the training count.


### Additional audited STP evidence (8 November 2026)
- CAG's AMRUT performance audit reports the 5 MLD sewage treatment plant at Medical College, Thiruvananthapuram commenced in March 2019 and was completed in January 2022, with expenditure of ₹14.65 crore against an approved project cost of ₹19.16 crore. The audit also found that the plant was not functioning properly in February 2024. This is retained as an audited cost-evidence lead with month-level dates only; it is not yet eligible for ML because exact date granularity, cohort comparability and outcome context need review. Source: https://cag.gov.in/uploads/download_audit_report/2025/Print-version-english_AMRUT_Kerala_10.12.25-with-legislature-date-0699d302521f715.11884185.pdf


### Three additional Kochi KWA pipeline profiles reviewed (8 November 2026)
The supplemental register now contains **14 source leads**. Three more KWA PASK profiles report total bill paid and completion information:
- Kochi Corporation Division 49 multi-road pipeline replacement: total bill paid ₹26,90,968; start 28 October 2024; actual completion 21 June 2025; final bill submitted 18 July 2025. Several pipe diameters and road segments are listed, but total installed length is not reported.
- Kochi Corporation May 1st Road by-lane and Karolil Lane, Division 45/32: total bill paid ₹5,88,425; start 19 August 2024; reported completion 7 September 2024. The profile's coverage text conflicts with its completion status and dated progress log; pipeline length is not reported.
- Kochi Corporation Kumbalapilly bye-lane, Division 47/33: total bill paid ₹2,77,439; profile reports completion 3 March 2024, but its coverage field says work ongoing and dated status updates continue into April 2024. The reported start/completion interval also requires source verification; pipeline length is not reported.

Although these profiles contain bill-paid values, all three remain **not ML-eligible** because comparable installed pipe length is absent and the status/date fields require reconciliation. They must not be used as cost-per-metre examples or duration labels until source documents resolve these issues.


## Additional programme and project evidence (8 November 2026)

### Kerala AMRUT sector aggregate dataset
A separate aggregate evidence file, `kerala_amrut_sector_aggregates.csv`, has been added from the LSGD Kerala AMRUT programme page:
https://lsgd.kerala.gov.in/en/centrally-sponsored-schemes/through-lsgd/mohua/amrut/

It contains three state-level sector rows (water supply, sewerage and storm-water drainage), including programme project counts, reported project values, completed counts, expenditure and physical progress metrics. The source page does not state a reporting date; the dataset preserves that as unknown rather than inventing one. These are programme aggregates, **not project-level training records**, and the file marks them ineligible for ML.

Key reported storm-water drainage figures are 536 projects, 502 completed, ₹336.83 crore programme value, ₹289.74 crore expenditure, 324 km of 337 km drainage network achieved, and 1,320 of 1,395 waterlogging points reported eliminated. Sewerage reports 109 of 152 projects completed and 75 km of 103 km sewerage network achieved. Water supply reports 172 of 217 projects completed and 1,806 km of 2,084 km network achieved. These state-level aggregates must not be attributed to Kochi.

### Five additional government source leads
The supplemental register now contains **19 source leads** (the core training CSV remains at 29 records):
- Jalanidhi Chakkumkuzhy BG, Parathode: total bill paid ₹4,80,301; start 30 December 2022; completed 22 September 2023. Multi-component scope, so not a comparable unit-cost record.
- Jalanidhi Pathickal BG, Karoor: total bill paid ₹6,77,662; start 1 July 2022; completed 30 November 2022. Scope quantity lacks a unit and pipe length is absent.
- Jalanidhi Cherupuzha rainwater-harvesting programme: 200 planned units, total bill paid ₹1,86,83,360, start 1 February 2023, completion 25 April 2024. Latest visible status narrative itemises 171 units, so cost denominator needs reconciliation.
- KWA Palarivattom–Thammanam pipeline Package II: 1,890 m of 160 mm PVC pipe, completed 2 August 2025; final paid bill and start date are absent.
- KWA Kannur Puzhathi Zone I pipeline project: 9.6 km pipe and 915 household connections reported, total bill paid ₹1,12,37,537 versus ₹1,65,54,275 submitted. Payment is not established as final, and start date is absent.

None of these five leads is marked ML-eligible. Do not convert paid-to-date amounts into final project costs when submitted bills are higher or final accounts are unresolved.


### Ten additional KWA PASK project records reviewed (8 November 2026)
Ten more records have been appended to the supplemental register. They are **source leads, not ML training records**:
1. Kochi Stadium–Janatha Link Road by-lane: completed 18 August 2026; no final bill or pipe length shown.
2. Ollur 500 FHTC and pipeline extension: completed 25 February 2025; no final bill or verified pipe length shown.
3. Kannur Edakkad Zone AMRUT 2.0: completed 29 October 2025; bill fields show zero while status log says final bill submitted.
4. Kozhikode JJM works across nine panchayats: 463 km laid and 429 km charged in a status update; ₹30,25,47,821 paid against ₹40,89,56,750 submitted; start date absent.
5. Manimala and four adjoining panchayats WSS: 9 MLD; ₹41,47,000 paid against ₹1,17,74,601 submitted; completion 5 January 2020; start date and comparable network quantity absent.
6. Keralassery JJM additional distribution works: 12.727 km of 13 km reported laid; PASK paid amount is zero and completion chronology needs review.
7. Guruvayur Chakkamkandam STP tank cleaning: maintenance work reported completed; bill was still under preparation in September 2026.
8. Nayattukundu–Mattathur WSS: 0.70 MLD; ₹10,49,974 submitted and paid; completion 24 January 2025; multi-component scope and start date absent.
9. Karimba–Kongad–Mundur CWSS Phase II: ₹52,56,06,600 paid against ₹64,78,73,250 submitted; completion/status chronology conflicts with an April 2025 progress update reporting remaining work.
10. Varma Road and adjoining roads, Cheranalloor: PASK shows only ₹1 submitted/paid against ₹10 lakh AS/TS, an obvious data anomaly requiring correction.

All ten are marked not eligible for ML. Missing final expenditure, zero or anomalous bill fields, multi-component scopes, missing start dates, and contradictory completion updates are explicitly retained as quality warnings. No sanctioned estimate, paid-to-date amount or anomalous value has been re-labelled as a verified final project cost.
