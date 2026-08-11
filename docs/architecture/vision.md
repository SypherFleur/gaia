# Vision Architecture

Last verification date: 2026-08-11.

GAIA Vision is a multimodal plant-perception subsystem. It produces evidence for the existing reasoning architecture; it is not a standalone disease classifier and does not own final agronomic decisions.

## Boundary

Vision providers implement `VisionProvider` with:

- `capabilities() -> VisionCapabilities`
- `analyze(VisionRequest) -> VisionResponse`

Capabilities describe plant identification, general visual reasoning, symptom description, image quality assessment, optional bounding regions, optional multiframe support, and future video support.

## Domain Semantics

`VisualObservation` records what is visible in the image, such as yellowing, lesions, wilting, insect damage patterns, or image-quality limitations.

`VisualHypothesis` records what may explain the observations. Hypothesis statuses must remain cautious: `hypothesis`, `possible`, or `candidate`.

Vision output must not persist confirmed diagnoses from image evidence alone. Unsafe or overconfident provider output becomes `VALIDATION_FAILED`.

## GAIA Integration

`VisionService` can attach analysis to:

- tenant workspace;
- media attachment;
- user plant;
- Botanist context;
- Atlas `GeoContext`;
- Terra `EnvironmentalSnapshot`;
- SourceRecord provenance.

When attached to a Plant Workspace, visual observations are stored as observed facts and visual hypotheses are stored separately as GAIA inferences.

## Provider Policy

Vision providers are invoked through the Tool Gateway. The gateway enforces permissions, tenant membership, provider registry status, Cost Firewall, quota, egress policy, cache, usage ledger, and audit log.

Automated tests use deterministic fixtures. Local LLaVA through Ollama is optional smoke coverage and is not required for CI. Pl@ntNet is optional and cannot trigger a paid upgrade.

## Security Notes

Image bytes are private by default. Remote provider calls are denied when private-image egress is disabled. Audit events must not store raw image bytes.

Prompt-injection text inside retrieved context or user prompts cannot alter system, privacy, tool, provenance, or cost policy.

