# GBIF

Last verification date: 2026-08-11

Source URL: https://techdocs.gbif.org/en/openapi/

Purpose:
GBIF provides taxonomy and occurrence data. Phase 5 uses it for taxonomy lookup, accepted-name resolution, synonyms, and source-backed identifiers.

Fields used:

- usage key / accepted usage key
- scientific name / accepted scientific name
- canonical name
- rank
- kingdom, family, genus, species
- match type
- alternatives when a name is ambiguous

Cost:
Free. No paid fallback is enabled.

Credentials:
Most read API use does not require authentication. GAIA's live adapter requires a configured User-Agent.

Quota:
GBIF may rate-limit rapid or numerous search requests with HTTP 429. GAIA caches taxonomy resolution aggressively.

Cache behavior:
Taxonomy resolution uses long TTL caching and stale-if-error fallback where allowed.

Data semantics:
GBIF occurrence records are evidence of observed presence. GAIA must not treat occurrence as proof of cultivation suitability at a location.

Geographic limitations:
Global taxonomy and global occurrence coverage, but data completeness varies by taxon and region.

Failure behavior:
Unresolved, ambiguous, or provider-error lookups do not create canonical plant entities.

Licensing / attribution:
License and attribution are preserved as source metadata where available. Unknown rights remain `unknown`.
