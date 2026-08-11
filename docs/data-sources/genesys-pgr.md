# Genesys PGR

Last verification date: 2026-08-11

Source URLs:

- https://www.genesys-pgr.org/documentation/apis
- https://www.genesys-pgr.org/documentation/brapi
- https://www.genesys-pgr.org/documentation/basics

Purpose:
Genesys PGR provides global plant genetic resources accession and passport-data discovery. Phase 5 uses it for germplasm search and normalized accession candidates.

Fields used:

- accession identifier / accession number
- taxon or crop
- institute / genebank code and name
- origin metadata where available
- passport data where available
- published traits or descriptors where actually present
- collection metadata where available

Cost:
Free discovery boundary. No paid fallback is enabled.

Credentials:
Genesys API and BrAPI documentation describe OAuth access for API use. Phase 5 automated tests use fixtures. Live credentials are not required to boot GAIA.

Quota:
No paid quota path is enabled in GAIA. Any future live quota handling must go through the Tool Gateway and Cost Firewall.

Cache behavior:
Germplasm search results use medium/long TTL caching and stale-if-error fallback where allowed.

Data semantics:
A discoverable accession does not mean the material can legally ship, is commercially available, is free, can be imported into the user's country, or is agronomically suitable.

Geographic limitations:
Global accession coverage depends on contributing genebanks and available passport/descriptor data.

Failure behavior:
Genesys outage degrades germplasm discovery only. Existing plant workspaces and ordinary plant-care reasoning remain available.

Licensing / attribution:
GAIA preserves Genesys attribution and records unknown licensing fields as `unknown` until reviewed.
