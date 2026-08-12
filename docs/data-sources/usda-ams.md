# USDA AMS MyMarketNews

Purpose: produce market reports, wholesale pricing, shipping-point reports, movement, volume, terminal markets, and local/regional market reports.

Fields used in Phase 10 fixtures: report date, market, commodity, package, grade, unit, price/value, geography, source report, retrieval time.

Cost: official public/free source. No commercial market data subscription is enabled.

Credentials: optional `GAIA_AMS_API_KEY`. GAIA boots and tests without a key.

Quota: account/API-key dependent; CI uses fixtures only.

Cache behavior: market reports use short/medium TTLs based on report cadence. Cached reports retain original report dates.

Data semantics: AMS reports are dated market observations. They are not price forecasts, trading signals, or guarantees.

Geographic limitations: coverage depends on commodity, report type, terminal market, and shipping point.

Failure behavior: provider outages leave Mercator partially available if other providers succeed. No paid fallback activates.

Licensing/attribution notes: retain USDA AMS/MyMarketNews attribution and report identity.

Source URL: https://mymarketnews.ams.usda.gov/mymarketnews-api

Last verification date: 2026-08-12.

