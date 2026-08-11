# Jurisdiction Packs

Jurisdiction packs are versioned bundles of provider adapters, authority metadata, regulatory zones, rule records, source references, and matching policy for a legal geography.

## Stack

Sentinel evaluates overlapping jurisdiction layers:

```text
country
federal or national
state, province, or region
county, district, or municipality
quarantine polygon or regulated zone
property or facility context
```

County boundaries are one layer only. GAIA must not encode plant movement as `origin_county != destination_county`.

## Phase 8 Packs

`us_federal` covers APHIS fixture rules for citrus-related federal movement and plant import context.

`us_tx` covers Texas Department of Agriculture fixture rules for citrus movement, citrus zone context, and citrus greening quarantine context.

`us_fl_fixture` and `sg_fixture` are declared in tests to prove the pack abstraction remains extensible, but comprehensive rules are deferred.

## Geometry

Atlas supplies administrative context plus `regulatory_zones`, `quarantine_zones`, and `pest_zones`. When authoritative geometry exists, polygon/zone membership is preferred over county approximation. Phase 8 stores `sentinel_zone_features.geometry_reference` so future map rendering can display origin, destination, and quarantine boundaries.

## Source URLs

Initial official sources checked on 2026-08-11:

- USDA APHIS citrus quarantine descriptions: https://www.aphis.usda.gov/plant-pests-diseases/citrus-diseases/federal-citrus-pest-disease-written-quarantine-descriptions
- USDA APHIS plant import guidance: https://www.aphis.usda.gov/plant-imports/how-to-import
- Texas citrus information: https://texasagriculture.gov/Regulatory-Programs/Plant-Quality/Citrus-Information
- Texas citrus greening information: https://texasagriculture.gov/Regulatory-Programs/Plant-Quality/Pest-and-Disease-Alerts/Citrus-Greening
- Texas quarantines landing page: https://texasagriculture.gov/Regulatory-Programs/Quarantines

