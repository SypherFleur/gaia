# Terra

Last verification date: 2026-08-11.

Terra is GAIA's environmental context compiler. It builds `EnvironmentalSnapshot` objects from provider-normalized environmental data and local deterministic calculations. Terra is not an LLM workflow.

Environmental evidence types:

- `OBSERVED`
- `FORECAST`
- `HISTORICAL`
- `CLIMATOLOGY`
- `MODELED`
- `SURVEY`
- `USER_MEASURED`
- `SENSOR`
- `DERIVED`

Current implementation:

- NWS forecast tool boundary with fixture provider and live normalizer class;
- NASA POWER climate/model-derived context fixture and normalizer;
- USDA Soil Data Access / SSURGO survey fixture and normalizer;
- USGS water boundary with fixture nearby-site provider;
- deterministic sunrise/sunset, photoperiod, moon phase, and unit conversion utilities;
- partial snapshot behavior when a provider is unavailable;
- provider statuses attached to snapshots;
- source-record provenance for normalized facts.

Important semantics:

- NASA POWER values are regional/model-derived, not exact on-site sensor readings.
- SSURGO is soil survey context, not live soil moisture.
- One failed provider must not fail the entire snapshot.
- Regulatory/current high-risk data must fail closed in later Sentinel workflows.

