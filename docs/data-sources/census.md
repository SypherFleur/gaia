# U.S. Census APIs

Purpose: future regional economic and demographic context, such as county population and related explanatory indicators.

Fields planned: geography, metric, value, unit, observation period, publication date, retrieval time, source record.

Cost: official public/free API. No paid source is enabled in Phase 10.

Credentials: an API key may be optional or useful depending on request patterns. GAIA does not require it to boot or test.

Quota: Census API limits apply; Phase 10 CI uses fixtures only.

Cache behavior: demographic context should use medium/long TTLs based on dataset cadence.

Data semantics: county population or demographic data is explanatory context. It is not crop profitability, farm revenue, or a market forecast.

Geographic limitations: U.S. and Census-supported geographies.

Failure behavior: unavailable Census context remains missing and does not block other GAIA workflows.

Licensing/attribution notes: retain U.S. Census Bureau attribution and dataset metadata.

Source URL: https://www.census.gov/data/developers/guidance/api-user-guide.html

Last verification date: 2026-08-12.

