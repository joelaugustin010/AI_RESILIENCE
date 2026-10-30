# CPCB National AQI calculation in AI RESILIENCE

## Status

The implementation in `src/cpcb_aqi.py` is a **calculation module**, not an AQI observation feed and not a claim that a source dataset is valid. Its output is labelled `CALCULATED INDICATOR`.

## Method source

Central Pollution Control Board, *Report on National Air Quality Index*, especially:
- Table 3.2: six AQI categories.
- Tables 3.3–3.10: pollutant breakpoint development.
- Table 3.11: summary concentration breakpoints for the eight pollutants.
- Section 3.3: segmented-linear sub-index method and maximum-sub-index aggregation.

Official report:
https://cpcb.nic.in/displaypdf.php?id=bmF0aW9uYWwtYWlyLXF1YWxpdHktaW5kZXgvRklOQUwtUkVQT1JUX0FRSV8ucGRm

CPCB's AQI explanation also states that at least three pollutants are required, one of which must be PM2.5 or PM10, and that at least 16 hours of data are needed for a pollutant sub-index:
https://cpcb.nic.in/displaypdf.php?id=bWFudWFsLW1vbml0b3JpbmcvQVFJX05BTVBfUmVwX1NlcHRlbWJlcnoyMDE2LnBkZg==

## Input contract

Each record represents one pollutant at one station/location and one reporting window:
- `pollutant`: one of PM2.5, PM10, NO2, O3, CO, SO2, NH3, Pb.
- `concentration`: non-negative numeric concentration.
- `unit`: exactly `ug/m3`, except CO which is `mg/m3`.
- `averaging_period`: 24-hour for PM2.5, PM10, NO2, SO2, NH3, Pb; 8-hour for CO and O3.
- `valid_hours`: number of valid hourly observations contributing to the reported averaging window; must be at least 16.

The function does not calculate averages from raw hourly samples. Acquisition and preprocessing must establish the averaging window and valid-hour count. It also does not verify that multiple records share the same station, date, instrument, or reporting window; the caller must enforce that grouping before calculation.

## Important upper-band treatment

CPCB Table 3.11 gives open-ended concentration ranges for the Severe band (for example, PM2.5 250+ µg/m³). The module does not invent a concentration upper breakpoint or extrapolate a linear relation beyond the published range. Values above the last listed breakpoint are top-coded to AQI 500 and explicitly flagged `capped_at_500`.

## Known limitations

- The method source is the CPCB National AQI report; it does not make the output an official CPCB-reported AQI.
- A correct calculation still depends on source measurement quality, station identity, temporal alignment, instrument QA, and the valid-hour count being documented.
- Date-only daily summary rows whose precise averaging interval or completeness is unstated must not be passed into this function as though those conditions were known.
- The Eloor monthly extracts in this repository currently mark pollutant rows `unassessed` and describe daily values whose exact averaging interval and row-level QA/completeness are not stated. They are therefore not automatically eligible for this calculation.
- This module does not calculate source contributions, exposure, forecasts, or health risk.
