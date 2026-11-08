# Kerala government completed-project source dataset (candidate records)

## Provenance
Primary source: Government of Kerala, Department of Economics & Statistics, *Evaluation Study on Soil Conservation in Kerala 2019-20* (published 2022).
Source URL: https://ecostat.kerala.gov.in/storage/publications/640.pdf

The report states that the study covers 13 schemes completed by the Soil Survey and Soil Conservation Department and other agencies (report p.1). Table 2.1 (report p.16) lists district, scheme, treated area, total project-work cost and beneficiary count. Scheme descriptions on report pp.4-7 provide start/completion dates for some projects.

## File
`kerala_soil_conservation_completed_projects.csv`

13 district-level completed watershed/soil-conservation scheme records have been transcribed from Table 2.1. The same file now also contains 8 KSDMA cyclone-shelter completion records and 2 KWA PASK records (23 rows total). The Ernakulam row is a particularly relevant drainage/flood-control project: Thirumarayoor Thodu Drainage & Flood Control Project, recorded cost ₹5,875,151 and treated area 261.82 acres.

## Important data handling
- `actual_cost_inr` is the report's stated total project-work cost; it is not represented as a final audited bill or inflation-adjusted cost.
- `scope_quantity` is treated area in acres.
- `duration_months` is calculated from exact start and completion dates printed in the report, using elapsed days / 30.4375 and rounded to one decimal. It is blank when the report gives only a year or incomplete date precision. No duration has been guessed.
- `intervention` and `area_type` are broad research labels assigned consistently to this source cohort; they are not verbatim structured fields in the report.
- The report contains a conflicting Palakkad cost in its chart and table. The CSV uses the Table 2.1 value (₹13,564,643) and flags the discrepancy in source notes.
- This is a small, narrow cohort (13 records, one broad intervention family and rural watershed context). It is **not sufficient to train or validate** the platform's general-purpose cost/delivery models. Do not lower the 40-record minimum or claim model readiness from this file.
- These records are candidate historical evidence, not verified Kochi project data. Do not directly transfer their unit costs to urban Kochi interventions without suitability review and price-year adjustment.
- Keep this source dataset separate from any synthetic/demo data and preserve the source URL and notes during future processing.

## Other official sources identified for further collection
- KSDMA project orders: https://sdma.kerala.gov.in/sdmf-projects/ (contains sanctions/permissions; many are not completion records).
- Kerala Water Authority PASK project monitoring: https://pask.kwa.kerala.gov.in/ (project profiles include status, sanction/technical-sanction amounts, bills and completion fields; each record needs individual validation).
- Kerala eProcurement: https://www.etenders.kerala.gov.in/ (tender/award evidence; tender estimate or award is not automatically final actual cost).
- Kerala LSGD Sulekha: https://plan.lsgkerala.gov.in/ (local-government plan monitoring and expenditure; extract project-level records with status and expenditure evidence).
- KIIDC completed projects: https://kiidc.kerala.gov.in/category/our-current-projects/completed-projects/

## Suggested next data acquisition
Prioritise Kerala Water Authority, Irrigation Department, LSGD/Sulekha, KIIDC and PWD records with project-level completed status, actual final expenditure, intervention type, scope/quantity, area type, start date and actual completion date. Capture at least 40 genuinely independent records with traceable source documents before training; use multiple intervention types and locations and assess whether each record is comparable to the intended prediction task.
