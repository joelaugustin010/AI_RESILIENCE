# Kochi Geospatial & UI Overhaul Report
**Date:** 9 November 2026  
**Repository:** `joelaugustin010/AI_RESILIENCE`  
**Scope:** Kochi GIS page architecture, raster separation, map placement, and geospatial evidence safeguards.

## Executive summary
The Kochi page has been refactored into a split command-centre layout with a dedicated hazard/infrastructure map and a separate ESA WorldCover land-cover context map. The two raster products no longer share a Deck.gl layer stack. The map viewports are reserved in the upper split layout so they are populated in place after source and layer validation.

## Changes implemented
1. **Two independent maps**
   - Main map: provisional Kochi Corporation outline, eligible processed vector/context layers, user-reviewed points, and (when selected and hazard-compatible) JRC GloFAS RP100 modelled flood context.
   - Separate context map: ESA WorldCover 2021 categorical land-cover preview only.
   - Each map has its own Deck.gl instance, map slot, descriptive caption, and legend. The WorldCover class legend is rendered with its own map.
2. **Command-centre placement**
   - Added a 34/66 controls-to-map split using Streamlit columns.
   - Reserved the main and WorldCover map viewports in the map column near the top of the page.
   - Kept the WorldCover description explicit that its classes are not hazard severity, susceptibility, exposure, or live land cover.
3. **Deck.gl bitmap serialization**
   - WorldCover uses the local preview image path, not a manually assembled `data:image;base64,...` expression string.
   - Removed redundant base64 encoding from the cached WorldCover loader while retaining SHA-256, image format, dimensions, and bounds validation.
4. **Hazard compatibility**
   - JRC flood context remains gated to Flood-compatible scenarios.
   - WorldCover remains a contextual layer and is not substituted for a missing hazard footprint.
5. **Regression coverage**
   - Added architecture tests for the split layout, independent WorldCover map, JRC placement, safe raster serialization, and retained evidence caveats.

## Geospatial QA and boundaries: what is and is not repaired
The current repository does not contain an approved, legally current 76-ward production boundary. Available candidates have material source/geometry/version caveats:
- The Esri candidate has 76 polygons and 76 unique source codes, but only 65/76 exact same-number matches against the current SEC register; source reuse terms and legal currency remain unverified.
- The KSMART-linked candidate is marked draft-notification and has geometry/name discrepancies.
- Older ward geometries do not align reliably with the current ward register.
- The corporation outline is a provisional administrative reference and its source does not state positional accuracy or legal currency.

For these reasons, this change **does not silently repair/promote ward candidates or manufacture missing ward identifiers**. A geometry repair can correct topology; it cannot establish the legally correct ward number/name. The raw candidate and its source attributes must remain intact. Any future repaired copy must be a separate derivative with source hash, repair method, before/after validity, discarded-part accounting, and a reviewed SEC/final-notification crosswalk. Unresolved or non-polygon remnants must remain excluded.

## CRS and overlay policy
- GeoJSON map layers are admitted only through the existing provenance checks requiring documented WGS 84 longitude/latitude (EPSG:4326 / CRS84).
- The corporation boundary metadata records EPSG:4326 as an interpretation of GeoJSON coordinate order, not an explicit source declaration; that limitation remains visible.
- The WorldCover preview metadata is checked for WGS84 bounds and image integrity before rendering.
- The JRC preview uses its validated geographic bounds and the local-path PyDeck bitmap serialization route.
- No undocumented CRS is guessed for NIHFW hospital coordinate strings; those remain review-only.
- No unvalidated hazard/ward geometry is used to infer exposure.

## Remaining blockers
1. **Official ward geometry:** obtain the final authoritative GIS polygon dataset, its publication/version metadata, CRS, licence, and documented ward-number crosswalk. A PDF ward map is not a substitute for GIS geometry.
2. **Invalid ward geometry:** repair only after the authoritative source is established; preserve raw geometry and generate a fully audited derivative. Topology repair alone does not cure source identity/name mismatches.
3. **Hazard footprints:** no validated, licence-cleared local footprint is currently available for the ten workflow hazards. The JRC product is modelled river-flood scenario context, not an observed event or official warning.
4. **Exposure:** current provisional OSM context and unverified facility coordinates do not support operational asset exposure or safe/unsafe conclusions.
5. **Runtime verification:** source-level changes and regression tests are committed to the feature branch; live Streamlit browser rendering must be checked after merge/deployment. This report does not claim that the hosted app has already been visually verified.

## Verification status
- Static source checks: added as automated regression tests.
- Live Streamlit UI: pending deployment/browser verification.
- Official ward boundary repair/promotion: intentionally blocked pending authoritative GIS source and legal/source reconciliation.
- Hazard exposure calculations: remain evidence-gated and are not enabled by this UI change.
