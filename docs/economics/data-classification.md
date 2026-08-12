# Economic Data Classification

Mercator never treats broad historical or structural economics as live operational truth.

Classes:

- `REALTIME_OR_CURRENT_REPORT`: a recent market report with a report date and retrieval time.
- `RECENT_PERIODIC_STATISTIC`: a periodic statistic, such as a latest annual NASS figure.
- `HISTORICAL_SERIES`: older comparable observations across periods.
- `STRUCTURAL_SUPPLY_CHAIN`: structural or historical movement context.
- `REGIONAL_ECONOMIC_CONTEXT`: explanatory regional context such as population, employment, farm dependency, or concentration.
- `MODEL_OR_INFERENCE`: explicitly labeled inference, not observed fact.

Rules:

- Annual production is not current availability.
- Old market reports are not today's prices.
- Commodity flow records are not live trucking observations.
- County GDP or population is not crop profitability.
- Missing county data remains missing; GAIA may surface state-level context only with the fallback labeled.

Any model synthesis must preserve the class labels and source dates already attached by Mercator.

