# LangGraph GuidancePlan Workflow

GAIA now uses a LangGraph-compatible state-machine layer above the existing `GaiaOrchestrator` for the core conversational GuidancePlan workflow.

The graph is intentionally thin:

- `classify_route`
- `geography`
- `environment`
- `economics`
- `season`
- `reasoning`

Each graph node delegates to existing GAIA services and handlers. Domain behavior remains in Atlas, Terra, Botanist, Vision, Scholar, Sentinel, Season, Mercator, Tool Gateway, Model Gateway, persistence, policy, and validation layers.

The legacy custom orchestrator is preserved. LangGraph orchestrates GAIA; it does not own GAIA memory, providers, security, Cost Firewall, provenance, tenancy, or domain objects.

If the optional `langgraph` dependency is installed, GAIA compiles a real LangGraph `StateGraph`. If it is absent, GAIA runs the same node/edge contract through a local compatibility executor so manual alpha remains runnable without adding paid services or new infrastructure.

## Guardrails

Graph nodes must not call provider adapters directly. Tool/data calls continue through Tool Gateway, Cost Firewall, quota/cache, provenance, tenancy, egress policy, audit, and usage ledger. Model calls continue through Model Gateway and GuidancePlan validation.

Deterministic routes still run before model selection. Geography, environment, economics, and season routes must not introduce model runs unless their existing service contract already requires one.
