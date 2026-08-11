# Orchestrator And Chat

Last verification date: 2026-08-11

GAIA owns orchestration semantics. The first orchestrator performs deterministic routing before it considers model inference.

Phase 4 routes:

- Geography: `What county am I in?` uses Atlas only and persists assistant/user messages with zero ModelRuns.
- Environment: `What are the environmental conditions here?` uses Atlas + Terra and persists messages with zero ModelRuns.
- Reasoning: planting guidance compiles a structured `ContextBundle`, calls the approved local model provider, validates JSON, attaches trusted provenance from context, persists a `GuidancePlan`, and records one ModelRun.

Conversations and messages are persisted in GAIA tables. Framework-specific memory/checkpoint formats are not domain memory.

Prompt injection boundary:

- User text is marked untrusted.
- Retrieved context is supplied as normalized evidence, not executable instruction.
- Prompt/tool/cost/privacy policy is never derived from user or retrieved content.
- Model-generated source IDs/citations are rejected.
- Trusted source IDs are attached only by GAIA after context compilation.

Streaming is represented as simple route/token/final events suitable for server-sent events. A future HTTP framework can expose the same contract without changing domain orchestration.

The development UI in `apps/web` is a static inspection surface for route, model-run count, source count, provider diagnostics, and zero-cost behavior. It is not the final GAIA product UI.
