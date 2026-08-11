# USGS Water

Last verification date: 2026-08-11.

Source URL: https://waterservices.usgs.gov/

Purpose:

- Water context, nearby sites, current conditions, and historical conditions.

Fields used in Phase 3:

- nearby hydrologic site boundary only, fixture-backed.

Cost:

- Free public U.S. government service.

Credentials:

- No API key required for the planned boundary.

Quota:

- Avoid broad queries; use narrow filters and cache where appropriate.

Cache behavior:

- Short TTL for current conditions.
- Longer TTL for site metadata and historical summaries.

Data semantics:

- WaterServices provides machine-readable USGS water data through REST APIs.
- The legacy WaterServices family is scheduled for decommissioning in early 2027, so GAIA must not hard-couple domain objects to legacy response shapes.

Geographic limitations:

- U.S. water data coverage.

Failure behavior:

- Water context may be unavailable while other Terra context remains available.

Licensing/attribution:

- U.S. government public data; attribute USGS.

