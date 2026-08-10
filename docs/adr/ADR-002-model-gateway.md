# ADR-002: Model Gateway

Status: Accepted

## Context

GAIA must support local, hosted-free, and future manually enabled paid model providers without coupling domain logic to any provider.

## Decision

All model access goes through a provider-neutral Model Gateway. Providers advertise capabilities, modality support, structured-output support, local/remote status, context window, and cost class. Selection is policy-based.

## Consequences

- Nemotron 3 Nano Omni can be benchmarked without becoming a dependency.
- Ollama, llama.cpp/OpenAI-compatible runtimes, NVIDIA runtimes, Cloudflare Workers AI, or future providers can be swapped.
- Core domain objects cannot contain provider-native message types.

