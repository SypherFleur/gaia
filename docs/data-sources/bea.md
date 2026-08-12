# BEA Regional Economic Data

Purpose: future regional economic context such as income, employment, GDP, and related explanatory indicators.

Fields planned: geography, metric, value, unit, observation period, publication date, retrieval time, source record.

Cost: official public/free API. No paid source is enabled in Phase 10.

Credentials: BEA API access may require registration/configuration. GAIA does not require it to boot or test.

Quota: provider-specific; Phase 10 does not run live BEA calls in CI.

Cache behavior: regional economic context should use medium/long TTLs depending on release cadence.

Data semantics: BEA data is broad economic context. It must not be treated as crop profitability or farm-specific economics.

Geographic limitations: depends on dataset and geography support.

Failure behavior: unavailable BEA data should not break plant care, Sentinel, Season, or Mercator's other sources.

Licensing/attribution notes: retain BEA attribution and dataset metadata.

Source URL: https://apps.bea.gov/api/signup/

Last verification date: 2026-08-12.

