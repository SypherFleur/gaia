# Pl@ntNet

Last verification date: 2026-08-11.

Source URLs:

- https://my.plantnet.org/doc/api/identify
- https://my.plantnet.org/pricing
- https://my.plantnet.org/terms_of_use

## Purpose

Pl@ntNet is an optional plant-identification provider. It can suggest candidate taxa from plant images. In GAIA it is not a disease, pest, nutrient, or treatment authority.

## Fields Used

Phase 6 normalizes candidate species fields:

- scientific name;
- common name where present;
- confidence score;
- external species ID where present;
- provider provenance.

## Cost

The public pricing page lists a free tier. Paid upgrades are not enabled by GAIA. The Cost Firewall keeps `estimated_cost_usd = 0.0` and no automatic overage or paid fallback is permitted.

## Credentials

Pl@ntNet requires an API key for live calls. GAIA does not require this key to boot or run automated tests. Missing credentials return `UNAVAILABLE`.

## Quota

The free tier is treated as quota-limited. The provider registry records 500 daily requests for the initial boundary, and quota exhaustion must not trigger a paid upgrade.

## Cache Behavior

Image-identification responses are short-lived cached by image content hash and provider. Stale cache may be used only under normal non-regulatory failure semantics.

## Data Semantics

Pl@ntNet provides image-based plant-identification candidates, not diagnosis. Candidate species are visual hypotheses and require corroboration before they affect plant identity or guidance.

## Geographic Limitations

Pl@ntNet is globally oriented, but species coverage and image evidence quality vary. GAIA must preserve uncertainty and not infer cultivation suitability from an identification candidate.

## Failure Behavior

Missing key, egress denial, quota exhaustion, provider failure, or malformed output produce unavailable or validation-failed responses without blocking the Plant Workspace.

## Licensing And Attribution

Provider-specific terms, attribution requirements, caching, redistribution, derivative-use, and model-training permissions must be reviewed before live use in production.

