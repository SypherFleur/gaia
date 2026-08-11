# USDA NRCS Soil Data Access / SSURGO

Last verification date: 2026-08-11.

Source URL: https://sdmdataaccess.nrcs.usda.gov/

Purpose:

- Official U.S. soil survey spatial and tabular context.

Fields used:

- map unit;
- component;
- drainage class;
- hydrologic soil group;
- available water capacity/context;
- texture/context;
- organic matter/context;
- pH/context;
- slope;
- depth or restrictive characteristics where available.

Cost:

- Free public U.S. government service.

Credentials:

- No API key required for planned v0 lookup.

Quota:

- Treat provider failures/rate limits as unavailable; cache aggressively.

Cache behavior:

- Very long TTL because SSURGO survey context changes slowly.

Data semantics:

- SSURGO is soil survey context.
- `SSURGO != live soil moisture`.
- Missing survey results remain missing; GAIA must not infer a soil type.

Geographic limitations:

- U.S. soil survey coverage.

Failure behavior:

- Return unavailable with provenance of attempted lookup.

Licensing/attribution:

- Record license metadata as `unknown` until source terms are reviewed; attribute USDA NRCS.

