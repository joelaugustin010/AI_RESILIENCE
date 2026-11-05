# JRC GloFAS flood-hazard data: licence and attribution

This repository contains unmodified source tiles from the Copernicus Emergency
Management Service Global Flood Awareness System (GloFAS) global river flood
hazard maps, version 2.1.2, published by the European Commission Joint Research
Centre (JRC).

## Files

| Local file | Role | SHA-256 |
|---|---|---|
| `jrc_glofas_rp100_ID185_N20_E70_depth.tif` | RP100 modelled river-flood depth, tile ID185 | `93ba198ffeb0fb7436c6b97d66cf6b47b10cd59c4e6cf742a8aff59f46bdaf3b` |
| `jrc_glofas_rp100_ID186_N10_E70_depth.tif` | RP100 modelled river-flood depth, tile ID186 | `cd78d43b91c235e39aa443550319ab099b816ca679f76ab83c339b5e7a9f1a30` |
| `ID185_N20_E70_permanent_water.tif` | Permanent-water mask used to patch tile ID185 | `a0a1dffab2c9313b037878a3f6a41a84217c8f0343fc6484619b3ff5d72daf6c` |
| `ID186_N10_E70_permanent_water.tif` | Permanent-water mask used to patch tile ID186 | `944b05a8ea6f2ec6592dccc9d978abe40655387eec9b45457499c04720c0fca0` |

Source directory:
<https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-GLOFAS/flood_hazard/>

## Licence

The dataset README states **Open Data Commons Open Database License v1.0
(ODbL 1.0)**. The linked JRC copyright notice states **Creative Commons
Attribution 4.0 International (CC BY 4.0)**.

Both statements permit reuse with attribution. This project applies the
stricter **ODbL 1.0** basis, which requires attribution, indication of changes,
and share-alike for publicly distributed derived databases.

- README: <https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-GLOFAS/flood_hazard/README.txt>
- Copyright notice: <https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-GLOFAS/copyright.txt>
- ODbL 1.0: <https://opendatacommons.org/licenses/odbl/1-0/>
- CC BY 4.0: <https://creativecommons.org/licenses/by/4.0/>

## Required attribution

> © European Union, 1995–2026. Global river flood hazard maps (CEMS-GLOFAS
> v2.1.2), Copernicus Emergency Management Service / European Commission Joint
> Research Centre (JRC). Modelled scenario data; cropped and rendered by
> AI RESILIENCE. Used under ODbL 1.0 / CC BY 4.0.

Recommended citation from the source README:

> Baugh, Calum; Colonese, Juan; D'Angelo, Claudia; Francesco, Dottori; Neal,
> Jeffrey; Prudhomme, Christel; Salamon, Peter (2024): Modelled flood inundation
> for different return period scenarios at the global scale. European
> Commission, Joint Research Centre (JRC).

## Changes made by this project

- Created a transparent PNG preview cropped to the Kochi display rectangle.
- Sampled raster cells at provisional OpenStreetMap asset representative points.
- Excluded cells marked as permanent water by the matching JRC masks.
- No source tile values or georeferencing were modified.

## Restrictions

- Do not describe this layer as observed flooding, a forecast, an official
  warning, a damage estimate, or a site-specific engineering result.
- Transparent, zero-depth, and NoData pixels do not establish safety.
- Derived databases distributed publicly must comply with ODbL share-alike.
- The separate spurious-depth artifact mask was not downloaded, so documented
  artifact flags for unrealistic depths cannot be applied.
