# Florida FDACS

Last verification date: 2026-08-13

## Purpose

Florida Department of Agriculture and Consumer Services sources support the `us_fl` jurisdiction pack for Florida plant inspection, citrus movement, nursery stock, citrus-health rules, regulated pests, and reporting context.

## Cost And Credentials

The Phase 12 implementation uses fixture-backed official-source summaries. No paid FDACS API, credential, submission workflow, permit filing, or regulator contact automation is enabled.

## Sources

- Plant Inspection: https://www.fdacs.gov/Agriculture-Industry/Plants-and-Nurseries/Plant-Inspection
- Citrus Quarantine and Disease Detection Maps: https://www.fdacs.gov/Agriculture-Industry/Pests-and-Diseases/Plant-Pests-and-Diseases/Citrus-Health-Response-Program/Citrus-Quarantine-and-Disease-Detection-Maps
- Summary of Plant Import Regulations: https://www.fdacs.gov/Agriculture-Industry/Plant-Industry-Permits/Summary-of-Plant-Import-Regulations
- Growing Citrus in Approved Structures: https://www.fdacs.gov/Agriculture-Industry/Pests-and-Diseases/Plant-Pests-and-Diseases/Citrus-Health-Response-Program/Growing-Citrus-in-Approved-Structures
- Broward County Giant African Land Snail Quarantine and Treatment Information: https://www.fdacs.gov/Agriculture-Industry/Pests-and-Diseases/Plant-Pests-and-Diseases/Invasive-Mollusks/Giant-African-Land-Snail/Broward-County-Quarantine-and-Treatment-Information

## Semantics

FDACS fixture rules are current-source movement decision support, not comprehensive legal parsing. They preserve authority, source URL, retrieval time, freshness, conditions, permits, inspections, reporting context, and exceptions where modeled.

## Failure Behavior

If FDACS current validation is unavailable, Sentinel returns `UNRESOLVED` for affected movement decisions rather than `ALLOWED`.

## Limitations

The pack does not submit reports, request permits, create compliance agreements, parse all Florida statutes, or replace FDACS/USDA authority. International legal jurisdiction remains out of scope.
