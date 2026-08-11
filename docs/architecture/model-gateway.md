# Model Gateway

Last verification date: 2026-08-11

The Model Gateway is GAIA's provider-neutral boundary for inference. Core domain objects depend on `ModelRequest`, `ModelResponse`, and `ModelCapabilities`, not on Ollama, llama.cpp, hosted APIs, or a specific model family.

Phase 4 implements:

- `ModelProvider` protocol with `capabilities()` and `generate()`.
- Local `OllamaModelProvider`.
- Fixture guidance provider for deterministic CI.
- ModelRun persistence with provider, model, prompt ID/version/hash, request hash, response hash, token/unit counts, elapsed time, status, and cost.
- Cost Firewall checks before generation.
- Egress/privacy checks for remote providers.
- `model.chat` permission checks for reasoning.

Provider selection remains policy-owned. Deterministic Atlas/Terra routes run before model selection and produce zero ModelRuns.

Paid models remain disabled by default. Manual-paid providers cannot be enabled automatically, and nonzero model cost is denied by the gateway.

Local Ollama is an adapter, not an architectural dependency. Phase 4 smoke-tested `llama3.1:latest` locally where available. `llava:latest` is installed and remains available for future vision phases, but Phase 4 does not use multimodal reasoning.

Malformed output is not persisted as a GuidancePlan. The gateway persists the ModelRun for audit, while the orchestrator validates structured output before creating domain guidance.
