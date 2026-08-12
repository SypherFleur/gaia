# NIST AI RMF Mapping

This is an internal architectural mapping, not a certification claim.

## Govern

- Organization policy centralizes model, tool, egress, telemetry, retention, export, and sharing controls.
- Human review records approval/rejection without rewriting original outputs.
- Cost Firewall prevents automatic paid model/API/overage use.

## Map

- ResearchRuns preserve task, inputs, datasets, context, tools, prompts, models, evidence, and outputs.
- Knowledge collections distinguish public, project, organization, and private sources.
- Dataset sensitivity and rights metadata are explicit.

## Measure

- Evaluation suites/cases/runs/results support metrics, pass/fail criteria, and human ratings.
- ModelComparison preserves candidate versions and does not declare winners without metrics.
- Reproducibility bundles include hashes and version references.

## Manage

- Tool and Model Gateways enforce policy before remote execution.
- Sovereign profile disables private egress and telemetry.
- Export packages include checksums and scrub secrets.

