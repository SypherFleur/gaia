# USDA NASS Quick Stats

Purpose: production statistics, yield, acreage, inventory, irrigation, prices, and Census of Agriculture context.

Fields used in Phase 10 fixtures: statistic, commodity, unit, geography, observation year/period, publication/update date, source record ID.

Cost: official public/free source. No paid fallback is enabled.

Credentials: optional `GAIA_NASS_API_KEY`. GAIA boots and tests without a key.

Quota: key- and service-dependent; CI uses fixtures only.

Cache behavior: historical and annual statistics use long cache TTLs. Source periods are never discarded.

Data semantics: NASS statistics are periodic or historical agricultural statistics. They are not current crop availability and not live market intelligence.

Geographic limitations: U.S. focused; county data is not available for every commodity/statistic. State-level fallback must be labeled.

Failure behavior: provider errors produce partial Mercator context. No paid fallback activates.

Licensing/attribution notes: U.S. government/public source where applicable; retain USDA NASS attribution and source URL.

Source URL: https://quickstats.nass.usda.gov/api and https://www.nass.usda.gov/developer/index.php

Last verification date: 2026-08-12.

