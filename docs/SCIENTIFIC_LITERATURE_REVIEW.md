# Scientific literature and platform review

**Scope:** A bounded desk review of established disaster-risk concepts,
compound-event research, and operational platforms. This is not a systematic
review, exhaustive comparison, or claim of scientific novelty.

## Established approaches

| Work/platform | Established approach | Relevance and boundary for AI_RESILIENCE |
|---|---|---|
| UNDRR Sendai Framework terminology, [Disaster risk](https://www.undrr.org/terminology/disaster-risk) | Frames disaster risk as potential losses determined by hazard, exposure, vulnerability, and capacity; losses may be difficult to quantify. | Supports keeping hazard, exposed people/assets, vulnerability, and capacity distinct. It is not a universal numeric equation or local Kochi parameter set. |
| IPCC AR6 WGII | Assesses climate risk through interacting hazards, exposure, vulnerability, and response/adaptation in context. [Report portal](https://www.ipcc.ch/report/ar6/wg2/) | Supports explicit uncertainty and context. Assessment synthesis does not validate any local dataset or app output. |
| Zscheischler et al. (2020), [A typology of compound weather and climate events](https://doi.org/10.1038/s43017-020-0060-z), *Nature Reviews Earth & Environment*, 1, 333-347 | Reviews compound-event types including multivariate, preconditioned, temporal, and spatially compounding events. | Compound hazards are established science. Rainfall, river, cyclone, drainage, and coastal interactions need event-specific joint observations or defensible process models, not additive dashboard scores. |
| INFORM Risk / INFORM product suite, [JRC/INFORM](https://drmkc.jrc.ec.europa.eu/inform-index) | Global open-source crisis/disaster risk assessment and separate risk, warning, severity, and climate-change products. | Demonstrates established multi-dimensional risk assessment. Global/subnational comparative products are not a verified asset-level Kochi event assessment. |
| FEMA Hazus, [FEMA product page](https://www.fema.gov/flood-maps/products-tools/hazus) | GIS-based hazard and inventory/damage-function methods for estimating physical, economic, and human impacts. | Quantitative impact methods are established. US baseline inventories and damage functions cannot be presumed valid for Kerala. |
| InaSAFE, [project site](https://inasafe.org/) | Open-source scenario tool combines hazard and exposure information to support impact and preparedness analysis. | Hazard/exposure overlays are established; local input quality and validated consequences remain prerequisites. |
| NIST Community Resilience Planning Guide, [Volume II](https://www.nist.gov/publications/community-resilience-planning-guide-buildings-and-infrastructure-systems-volume-ii) | Planning guidance addresses buildings, infrastructure systems, dependencies, cascading consequences, and performance goals. | Infrastructure cascades are not a novel concept. Guidance is not current Kochi network data. |
| Copernicus Emergency Management Service flood services, [EFAS/CEMS](https://european-flood.emergency.copernicus.eu/) | Operational flood-awareness services built on models, hydrometeorological inputs, and warning workflows. | Forecasting and flood awareness are mature domains; this app does not issue operational warnings and has no comparable validated local forecast system. |
| World Bank/GFDRR ThinkHazard!, [platform](https://thinkhazard.org/en/) | Screening-level hazard context for project areas and risk-aware planning. | Screening tools do not replace local studies or facility-level evidence. |

## Literature-to-project synthesis

- Disaster risk is not a property of a hazard layer alone; exposure,
  vulnerability, capacity, and time/space context matter.
- Compound-event classification distinguishes genuine joint/conditional
  processes from hazards that merely occur in the same general region.
- Cascading effects require system topology and observed or engineered
  dependency evidence; a conceptual graph must not be presented as an
  observed failure.
- An evidence-aware decision workflow, data provenance, categorical quality
  states, and uncertainty registers are sound engineering practices, but each
  is established individually and does not establish a novel method.
- No benchmark comparison, systematic search, or peer-reviewed evaluation of
  AI_RESILIENCE was performed for this phase.

## Defensible contribution statement

AI_RESILIENCE's potential contribution is an applied, reproducible Kochi
decision-support workflow that makes source suitability and missingness
visible, keeps uncertainty categories and unresolved dependencies explicit,
and withholds rankings and quantified benefits when local evidence is
insufficient. This is an implementation objective and evaluation hypothesis,
not a claim to be the first system, a new risk theory, or a validated
scientific model. Stakeholder review and independent event validation are
required before making a research-contribution claim.

## References and access notes

- UNDRR. *Sendai Framework Terminology on Disaster Risk Reduction* (2017).
  [Disaster risk definition](https://www.undrr.org/terminology/disaster-risk).
- IPCC. *AR6 WGII Report*. [Report portal](https://www.ipcc.ch/report/ar6/wg2/).
- Zscheischler, J. et al. (2020). *A typology of compound weather and climate
  events*. [DOI: 10.1038/s43017-020-0060-z](https://doi.org/10.1038/s43017-020-0060-z).
  Bibliographic title, issue, pages, and authors were cross-checked against
  Crossref metadata; the publisher page rejected direct retrieval during this
  review.
- INFORM/JRC. [INFORM Index and product suite](https://drmkc.jrc.ec.europa.eu/inform-index).
- FEMA. [Hazus](https://www.fema.gov/flood-maps/products-tools/hazus).
- InaSAFE. [Project site](https://inasafe.org/).
- NIST. [Community Resilience Planning Guide, Volume II](https://www.nist.gov/publications/community-resilience-planning-guide-buildings-and-infrastructure-systems-volume-ii).
- Copernicus Emergency Management Service. [European Flood Awareness System](https://european-flood.emergency.copernicus.eu/).
- World Bank/GFDRR. [ThinkHazard!](https://thinkhazard.org/en/).

For the earlier Phase 1B comparison and implementation context, see
`PHASE_1B_REPORT.md`.
