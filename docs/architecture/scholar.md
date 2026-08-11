# Scholar Architecture

Last verification date: 2026-08-11.

Scholar is GAIA's research and evidence intelligence layer. It retrieves provider-backed scientific/agronomic literature, preserves publication identity, classifies evidence, exposes contradictions, and prepares structured context for synthesis.

## Provider Boundary

Research providers implement:

- `search(ResearchSearchRequest) -> ResearchSearchResponse`
- `fetch(ResearchFetchRequest) -> ResearchDocument`

The domain does not depend on Europe PMC response shapes. Europe PMC is the first live-capable provider and remains fixture-tested by default.

## Pipeline

Scholar follows:

1. deterministic query planning;
2. Tool Gateway search;
3. deduplication by DOI, PMID, PMCID, or provider IDs;
4. metadata provenance persistence;
5. optional fetch;
6. evidence classification;
7. contradiction/applicability analysis;
8. optional model synthesis through Model Gateway;
9. citation validation;
10. `EvidenceSynthesis` persistence/export.

Searching, fetching metadata, deduplication, cache reads, and citation validation do not require a model call.

## Objects

`ResearchWork` is provider-backed publication metadata.

`ResearchClaim` is GAIA's structured interpretation of a work's evidence direction.

`EvidenceSynthesis` is generated interpretation and must not be treated as a source document.

`ResearchCollection` and `ResearchAnnotation` prepare institution research workflows while preserving tenant scope.

## Botanist And Vision

Scholar can receive Botanist context, recent plant observations, recent visual analyses, and Atlas/Terra environmental context. Vision hypotheses remain hypotheses; Scholar does not convert image evidence into confirmed diagnosis.

## Model Use

The model may synthesize retrieved evidence, explain contradictions, or discuss applicability. It may not invent publication metadata or citations. Every synthesis model call creates a `ModelRun`.

