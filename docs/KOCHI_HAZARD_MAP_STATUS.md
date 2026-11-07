# Kochi hazard-map availability and source boundaries

Reviewed: 2026-11-06

## What the map now does

- The Kochi Map page can be opened directly and a user can select any of the ten registered workflow hazards.
- When opened from the Decision Workflow, the submitted hazard is carried into the map.
- The JRC GloFAS RP100 preview is enabled by default for Flood and registered scenarios that contain a Flood component. Re-entering the map from a flood scenario re-enables the preview even if the user had previously switched it off.
- The map retains its administrative/context layers and renders an orientation marker if no optional layer is active.
- A source-reference section links the official KSDMA hazard maps relevant to the selected hazard. These links are references, not georeferenced overlays.

## Available local map evidence

| Hazard | What can be shown now | Important limitation |
|---|---|---|
| Flood | JRC GloFAS v2.1.2 RP100 modelled river-flood-depth preview; KSDMA district/raster references | JRC is a modelled scenario, not observed flooding. KSDMA raster valid-pixel meaning/units and dataset-level reuse terms remain unresolved, so it is not rendered or used for exposure. |
| Landslide | KSDMA/GSI 2022 Ernakulam shapefile download and district PDF references | The archive has not yet been ingested and its schema, CRS, licence and geometries must be checked first. |
| Drought | KSDMA statewide drought-prone map reference | Map states data period 2012–2013; not current Kochi water-availability evidence. |
| Earthquake | KSDMA earthquake/tremor and seismograph reference | The map states a 2000–2016 reference period; it is not a ground-shaking susceptibility or forecast layer. |
| Industrial incident | KSDMA major industrial accident susceptibility reference | State-level reference only; not a current facility-specific release or plume footprint. |
| Cyclone | KSDMA coastal-hazard reference | Coastal erosion/surge/tsunami reference is not a cyclone track, wind field or event-specific surge footprint. |
| Compound cyclone + flood | Flood-component reference and JRC preview | No validated cyclone track/wind/surge overlay; this is not a compound footprint. |
| Compound heavy rainfall + drainage failure | Flood-component reference and JRC preview | No validated municipal drainage inventory or drainage-capacity footprint. |
| Heatwave | KSDMA/C-DIT portal index lists a state-level Heat map; Ernakulam multi-hazard PDF is also linked | Neither has been validated as a local temperature/exposure GIS layer. Do not substitute land cover for heat exposure. |
| Infrastructure failure | Ernakulam multi-hazard PDF reference; no hazard-specific local outage layer | Community-mapped roads/bridges are context only, not outage observations. |

## Official KSDMA references

- [KSDMA Hazard Maps catalogue](https://sdma.kerala.gov.in/hazard-maps/)
- [Ernakulam historical flood probability map](https://sdma.kerala.gov.in/wp-content/uploads/2022/05/Ernakulam_Hist.pdf)
- [KSDMA historical flood return-probability raster ZIP](https://sdma.kerala.gov.in/wp-content/uploads/2026/06/1.-Flood-Return-Probability-Historical-10-25-50-years.zip)
- [GSI 2022 Ernakulam landslide-susceptibility shapefile ZIP](https://sdma.kerala.gov.in/wp-content/uploads/2025/08/Ernakulam.zip)
- [GSI Bhusanket public portal](https://bhusanket.gsi.gov.in/) — portal lists susceptibility maps, landslide impact-probability products, forecasts and field-validated inventory; no Kochi layer is ingested or independently validated by this app.
- [GSI 2022 Ernakulam landslide-susceptibility district PDF](https://sdma.kerala.gov.in/wp-content/uploads/2025/06/Landslide_Susceptibility_Zones_Districts_FINAL.pdf)
- [KSDMA drought-prone area map (2012–2013 data period)](https://sdma.kerala.gov.in/wp-content/uploads/2018/10/KL-Drought-1.jpg)
- [KSDMA earthquake/tremor map (2000–2016 reference)](https://sdma.kerala.gov.in/wp-content/uploads/2018/10/Map-Earthquake-incidents.jpg)
- [KSDMA coastal-hazard susceptibility map](https://sdma.kerala.gov.in/wp-content/uploads/2018/10/Map-Coastal-Hazard-Susceptibility.jpg)
- [KSDMA major industrial accident hazard map](https://sdma.kerala.gov.in/wp-content/uploads/2018/10/Map-Major-Industrial-Accident-Hazard-Zones.jpg)

- [Kerala Fire and Rescue Services — Ernakulam multi-hazard map (PDF)](https://fire.kerala.gov.in/wp-content/uploads/2021/11/7_Multi_hazard_Map_of_Ernakulam.pdf) — district-level reference only, not a georeferenced Kochi GIS layer.
- [KSDMA/C-DIT disaster portal](https://sdma.cditproject.org/) — portal index includes a Heat map; the map itself has not been independently validated or ingested as a local GIS layer.

## Why the prone-area overlay is not yet complete

A map image or a district-level PDF is not a GIS polygon. Before a source is promoted to a Kochi map layer, the project must verify:

1. Exact archive contents and data dictionary.
2. CRS, coordinate order, units and spatial coverage.
3. Licence/reuse terms and required attribution.
4. Geometry validity, completeness and source vintage.
5. Whether the source scale supports the intended spatial resolution.
6. Independent GIS review before any ward-level exposure calculations.

The KSDMA flood ZIP is already preserved in `data/raw/`, but its valid raster values do not have documented units/meaning and dataset-level reuse terms were not found. It remains blocked from rendering and exposure analysis. The GSI Ernakulam ZIP is linked by the official KSDMA catalogue, but its binary archive has not yet been downloaded and inspected in this branch. Do not infer its field schema or convert it based on a guessed CRS.

The current Kochi administrative outline and older ward geometry are provisional/contextual and are not approved as current legal boundaries or exposure masks. A statewide/district reference must not be resampled or visually cropped and then described as a validated ward-level risk map.

## Engineering follow-up

- Retrieve the GSI Ernakulam archive from the official KSDMA link in a network-enabled project environment. The new metadata-only helper is `python scripts/inspect_gsi_landslide_archive.py --download`; it preserves the ZIP, checks archive CRCs, inventories shapefile sidecars, reads the declared `.prj` and DBF field schema, and writes `reports/gsi_ernakulam_landslide_archive_inspection.json` without extracting or promoting the layer.
- Inspect the ZIP members and shapefile sidecars; confirm CRS and licence with KSDMA/GSI metadata.
- Convert only after the schema is confirmed, preserve the original archive, record checksums and processing provenance, and run independent geometry validation.
- Add a separate hazard layer with explicit status and source attribution; do not merge it with the JRC flood scenario or treat susceptibility as event probability.
- Keep exposure unknown until a compatible, validated asset layer and a defensible current boundary are available.
