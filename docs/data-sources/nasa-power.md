# NASA POWER

Last verification date: 2026-08-11.

Source URL: https://power.larc.nasa.gov/docs/services/api/

Purpose:

- Climate, modeled meteorological history, precipitation context, and solar radiation.

Fields used:

- `T2M` temperature context;
- `PRECTOTCORR` precipitation context;
- `ALLSKY_SFC_SW_DWN` solar radiation context;
- temporal resolution;
- parameter/date/value/unit.

Cost:

- Free public API.

Credentials:

- No API key required for the planned v0 usage.

Quota:

- Handle HTTP `429 Too Many Requests` as quota/rate limiting.

Cache behavior:

- Long TTL for historical/climatology-style context.

Data semantics:

- NASA POWER is regional/model-derived environmental data.
- GAIA must not describe NASA POWER values as exact on-site sensor readings.

Geographic limitations:

- Global modeled gridded data, subject to parameter availability.

Failure behavior:

- Provider failure leaves climate/solar context unavailable but should not fail the whole snapshot.

Licensing/attribution:

- Record license metadata as `unknown` until terms are reviewed in the source registry; attribute NASA POWER.

