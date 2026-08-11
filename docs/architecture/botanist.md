# Botanist

Last verification date: 2026-08-11

Botanist is GAIA's canonical biological context layer. It resolves source-backed taxonomy, keeps cultivar identity separate from species identity, creates derived plant profiles, searches germplasm records, and assembles plant context for the orchestrator without requiring a model call.

Phase 5 implements:

- GBIF-backed taxonomy provider boundary with fixture tests.
- Synonym/canonical-name resolution.
- Ambiguous common-name safe failure.
- Genesys PGR germplasm provider boundary with fixture tests.
- `PlantProfile` records with field-level provenance and inspectable conflicts.
- Expanded `UserPlant` and `Observation` fields.
- `BotanistContextProvider` behavior through `BotanistService.build_context()`.
- Plant Workspace API helpers.
- Plant-aware chat context injection for Phase 4 reasoning.

Knowledge is separated into:

- canonical biological facts: taxonomy and source-backed plant profile attributes;
- user observations: observed facts, measurements, notes, media references, lifecycle-stage observations;
- GAIA hypotheses: model/system inferences stored separately from observations and never promoted to canonical facts silently.

Cultivar names remain user/plant-instance context unless a later cultivar registry source backs a cultivar object. For example, `Solanum lycopersicum` is the species and `Cherokee Purple` is a cultivar on the user plant.

Botanist does not answer legal movement, import, shipping, or availability questions. Genesys accessions carry caveats and future Sentinel/market workflows must handle those decisions.
