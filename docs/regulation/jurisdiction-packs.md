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

## Phase 12 Pack Contract

Every pack has:

```text
JurisdictionPackMetadata
- pack_id
- version
- display_name
- country_code
- authority_ids
- source_urls
- enabled
- legal_scope
- freshness_required
```

U.S. state packs use `USStateJurisdictionPack` and add `state_code`. A future state should be addable through the pack registry without editing Atlas, Botanist, Season, Mercator, or the Sentinel rule engine.

## Phase 12 Packs

`us_federal` covers APHIS fixture rules for citrus-related federal movement and plant import context.

`us_tx` covers Texas Department of Agriculture fixture rules for citrus movement, citrus zone context, and citrus greening quarantine context.

`us_fl` covers Florida FDACS fixture rules for citrus movement, nursery-stock context, approved citrus structures, aquatic plant permit context, and Broward giant African land snail regulated articles.

`sg_fixture` remains an extensibility fixture only. Protocol Two does not implement foreign legal jurisdiction.

## Geometry

Atlas supplies administrative context plus `regulatory_zones`, `quarantine_zones`, and `pest_zones`. When authoritative geometry exists, polygon/zone membership is preferred over county approximation. Phase 8 stores `sentinel_zone_features.geometry_reference` so future map rendering can display origin, destination, and quarantine boundaries.

## Source URLs

Initial official sources checked on 2026-08-11:

- USDA APHIS citrus quarantine descriptions: https://www.aphis.usda.gov/plant-pests-diseases/citrus-diseases/federal-citrus-pest-disease-written-quarantine-descriptions
- USDA APHIS plant import guidance: https://www.aphis.usda.gov/plant-imports/how-to-import
- Texas citrus information: https://texasagriculture.gov/Regulatory-Programs/Plant-Quality/Citrus-Information
- Texas citrus greening information: https://texasagriculture.gov/Regulatory-Programs/Plant-Quality/Pest-and-Disease-Alerts/Citrus-Greening
- Texas quarantines landing page: https://texasagriculture.gov/Regulatory-Programs/Quarantines

Florida official sources checked on 2026-08-13:

- FDACS Plant Inspection: https://www.fdacs.gov/Agriculture-Industry/Plants-and-Nurseries/Plant-Inspection
- FDACS Citrus Quarantine and Disease Detection Maps: https://www.fdacs.gov/Agriculture-Industry/Pests-and-Diseases/Plant-Pests-and-Diseases/Citrus-Health-Response-Program/Citrus-Quarantine-and-Disease-Detection-Maps
- FDACS Summary of Plant Import Regulations: https://www.fdacs.gov/Agriculture-Industry/Plant-Industry-Permits/Summary-of-Plant-Import-Regulations
- FDACS Growing Citrus in Approved Structures: https://www.fdacs.gov/Agriculture-Industry/Pests-and-Diseases/Plant-Pests-and-Diseases/Citrus-Health-Response-Program/Growing-Citrus-in-Approved-Structures
- FDACS Broward County giant African land snail quarantine information: https://www.fdacs.gov/Agriculture-Industry/Pests-and-Diseases/Plant-Pests-and-Diseases/Invasive-Mollusks/Giant-African-Land-Snail/Broward-County-Quarantine-and-Treatment-Information
