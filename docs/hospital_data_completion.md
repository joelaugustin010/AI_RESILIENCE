# Hospital data completion

The existing NIHFW directory contains 180 source-reported records explicitly
labelled Ernakulam. Its coordinate field is populated for 149 parseable rows
in the existing review, but the source does not document coordinate order,
CRS/datum, positional accuracy, or current facility status. Those values are
therefore preserved as source text and are not promoted to verified map points.

An official Kerala Department of Health Services 2024–25 register was acquired
from the [List of Modern Medicine Institutions 2024–25](https://health.kerala.gov.in/assets/backend/uploads/Galleryitem/17506790021511401637.pdf).
Nine clearly extractable Ernakulam public-hospital rows were added as a
separate overlay with source-reported phone, email, address, facility type,
government ownership, NIN, and latitude/longitude columns. They were not
fuzzy-matched into the NIHFW directory.

The official overlay coordinates are labelled `source_reported`, not
`verified`, because the PDF does not state CRS or positional accuracy. No bed
count, current operating status, emergency capacity, or vulnerability score
was inferred from the register.

Rebuild the processed overlay with:

```powershell
py -3 scripts\prepare_official_hospital_overlay.py
```

The Streamlit hospital page displays both inventories separately, preserves
the facility-level vulnerability and current-availability safeguards, and
reports modelled normal-condition access separately from disaster-time access.

## Kerala Health availability investigation

The Kerala Health [institution directory](https://health.kerala.gov.in/index.php/institutionSearch)
was retrieved with the Ernakulam (`EKM`) filter on 2026-10-30. The source is a
searchable HTML table, not a documented downloadable CSV/API and not a live
operating-status feed. The snapshot contains 115 Ernakulam institution rows,
including category, address/phone, sanctioned beds, functional beds,
rural/urban, email, and map-button fields where present. It has no per-record
operating status, emergency operating status, ICU capacity, source update date,
or source-defined validity period. The retrieval timestamp records when this
project captured the page; it is not a source freshness or validity timestamp.

The snapshot is stored separately as
`data/raw/hospital_sources/kerala_health_ernakulam_institution_directory_latest.csv`
with its HTML and metadata sidecars, and is copied by the normal data pipeline
to `data/processed/kerala_health_ernakulam_institution_directory_latest.csv`.
All 115 functional-bed fields are displayed as directory values only. None are
treated as current capacity, and zero records qualify as verified current
availability. No automatic joins to NIHFW or the nine-record 2024–25 overlay
are performed; ambiguous identity matches remain unresolved.

## Hospital hazard-exposure audit

The hospital page audits four Ernakulam-relevant hazard families from the
existing spatial catalogue: KSDMA flood products, GSI/KSDMA landslide
susceptibility, KSDMA coastal hazard susceptibility, and KSDMA major
industrial-accident hazard zones. The NIHFW directory has 180 Ernakulam
records, but its coordinate strings do not document coordinate order,
CRS/datum, or positional accuracy; the nine-record Kerala overlay is
explicitly `source_reported` and also lacks CRS/accuracy evidence. Those
separate directories are not assigned facility-specific scenario predictions.

The KSDMA flood archive has readable EPSG:4326 GeoTIFFs, but pixel meaning,
units, valid-cell coverage, and reuse terms are unresolved, so it is not
sampled. The GSI landslide ZIP has not passed CRS/schema/class validation. The
coastal and industrial sources are static maps without verified GIS geometry
or CRS.

## Normal-condition road-network access

The page now calculates network distances from Kochi ward polygon centroids to
named OpenStreetMap hospital features using the existing validated road and
healthcare GeoJSON layers. The network has 72,920 coordinate nodes and 150,293
directed road segments; 372 named OSM hospital features were identified, 171
could be linked to the road network within 750 m, and 72 of 74 ward
representative points snapped to roads within 1,500 m. Of the snapped ward
points, 71 have a directed route to at least one linked hospital.

The first five facilities are ranked by the number of the 74 ward
representative points reachable within the modeled 15-minute drive threshold.
Ward routes report nearest mapped hospital, network distance, estimated drive
time, and nearby alternatives. The estimate uses explicit class-based assumed
speeds (trunk 50, primary 40, secondary 35, tertiary 30, unclassified 25,
residential 20, and living street 10 km/h). It is not a measured travel time,
observed population access, hospital capacity estimate, or emergency-response
time. Ward centroids are unweighted representative points, not population
locations. The result is limited to the partial Kochi urban road and 2022
ward-layer coverage—not Ernakulam district.

Inputs are the OSM road and healthcare snapshots retrieved 2026-10-28
(EPSG:4326; ODbL 1.0; © OpenStreetMap contributors) and the processed Kochi
ward layer retrieved 2026-10-20 (EPSG:4326; CC BY-SA 2.5 India; DataMeet
attribution retained). OSM facility locations are community-mapped, not
independently verified. NIHFW and Kerala Health source-reported coordinates
remain excluded from route linking.

## Scenario screening estimates

The page now gives deterministic, low-confidence screening estimates for the
named OSM hospital candidates within the mapped Kochi/urban extent. It does
not join those candidates to the NIHFW or Kerala Health directory. Flood
screening measures distance from the provisional hospital point/footprint to
mapped OSM `waterway=river` or `waterway=canal` lines. The screening bands are:
Critical <=100 m, High <=250 m, Moderate <=750 m, and Low >750 m. A Low band
means only that no close mapped river/canal was found; it is not evidence that
the site is flood-safe. Distance is not flood depth, inundation extent, or a
damage probability.

Industrial-incident screening measures proximity to community-mapped OSM
`man_made=works`, `landuse=industrial`, or `industrial=*` features using
Critical <=100 m, High <=500 m, Moderate <=1,500 m, and Low >1,500 m. These
features are not verified hazardous installations or incident footprints.
For both supported screening types, a hospital-to-road graph link plus a
nearby mapped context feature results in “At Risk of Disruption”; a linked
facility with no close mapped feature is labelled “Likely Accessible” only
as a low-confidence screening heuristic. This does not inspect the full route
from an origin. “Likely Inaccessible” is used only when an explicitly
verified, scenario-matched road closure is supplied; none is currently
available. A missing graph link produces “Insufficient Information,” not a
claim that the hospital is unreachable.

Cyclones, coastal flooding, landslides, and heatwaves remain Unknown because
the bundled project has no compatible local wind, storm-surge/coastal,
landslide-susceptibility, or heat-exposure layers. A vulnerability category is
a geographic screening tier, not a structural assessment. Building strength,
floor elevation, backup power, water, supplies, staffing, continuity plans,
and current service scope remain unavailable. Hospital operational outlooks
are derived from those screening categories and are not live operating status,
bed availability, or capacity.

The candidate flood training rows are documented as unverified demo data and
are not used to fit a model. All OSM-based screening remains provisional,
incomplete, low-confidence, and restricted to the mapped urban query extent.
