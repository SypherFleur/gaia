# Ollama LLaVA

Last verification date: 2026-08-11.

Source URLs:

- https://ollama.com/library/llava
- https://docs.ollama.com/api/introduction
- https://github.com/ollama/ollama/blob/main/docs/api.md

## Purpose

Ollama LLaVA is the first local development vision adapter for GAIA. It supports practical smoke testing of image-plus-text analysis through the provider-neutral Vision boundary.

## Fields Used

GAIA accepts only structured JSON with:

- visual observations;
- cautious visual hypotheses;
- plant candidates;
- image quality;
- required next evidence;
- safety notes.

Raw provider output is not exposed as a domain object.

## Cost

Local execution is recorded as zero cash cost. It does not use paid APIs or hosted model calls.

## Credentials

No API key is required. Ollama must be installed and serving locally for smoke tests.

## Quota

No external provider quota applies. Local hardware capacity and model availability are operational limits.

## Cache Behavior

Vision calls can be cached by image content hash and provider. Automated tests verify fixture-provider cache behavior.

## Data Semantics

LLaVA output is visual evidence. It is not an agronomic diagnosis, laboratory test, pest authority, regulatory authority, or guaranteed plant ID.

## Geographic Limitations

The model itself is not jurisdiction-aware. Location-specific interpretation must come from Atlas, Terra, Botanist, Scholar, or Sentinel context.

## Failure Behavior

Missing Ollama, timeout, invalid JSON, or diagnostic overclaiming returns provider error or validation failure. Unsafe output is not persisted as useful plant evidence.

## Licensing And Attribution

Local model license metadata is recorded as local model license until a specific model license review is attached.

