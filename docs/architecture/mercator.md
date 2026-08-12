# Mercator Architecture

Mercator is GAIA's agricultural economics, market, and supply-chain context layer. It provides structured descriptive context; it is not a trading platform, price forecaster, procurement engine, or financial guarantee system.

Phase 10 introduces `MercatorContextProvider`:

`Atlas geography -> Mercator provider tools -> canonical economics objects -> MercatorContext`

The provider boundary is `EconomicDataProvider`, with methods for production, market reports, prices, regional context, and supply chain. Provider-specific schemas from USDA NASS, USDA AMS, BEA, Census, FAOSTAT, or future sources must not leak into GAIA domain objects.

Canonical objects:

- `Commodity`
- `ProductionStatistic`
- `MarketObservation`
- `EconomicRegionSnapshot`
- `SupplyChainRecord`
- `MercatorContext`

Mercator classifies every economic fact as one of:

- `REALTIME_OR_CURRENT_REPORT`
- `RECENT_PERIODIC_STATISTIC`
- `HISTORICAL_SERIES`
- `STRUCTURAL_SUPPLY_CHAIN`
- `REGIONAL_ECONOMIC_CONTEXT`
- `MODEL_OR_INFERENCE`

The service preserves observation period, publication date, retrieval time, freshness, unit/package/grade, geography, source records, and limitations. Cached data preserves the original source date separately from retrieval and cache use.

Mercator may inform Season planning, but it is lower priority than biological feasibility and Sentinel regulatory constraints. Economic context appears as dated advisory context in `SeasonPlan.market_context`; it cannot turn an impossible crop into a suitable crop or override a restriction.

Model usage is not required for retrieval, normalization, comparison, cache, provenance, or current-versus-historical classification. Any future model synthesis must create a `ModelRun` and cannot persist model-generated prices or production values unless they match trusted Mercator context.

Cost policy: Phase 10 uses official/public/free sources only through the Tool Gateway and Cost Firewall. Paid market data subscriptions and automatic paid fallback remain disabled.

