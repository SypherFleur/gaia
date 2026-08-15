# GAIA Agent Instructions

Operating instructions for any coding agent (Claude Code, Codex, or other) working in this repository. Read this before making changes. The governing product spec is `GAIA_MASTER_BUILD_PLAN.md`; resolved decisions are in `DECISIONS.md`; current gate status is `PROTOCOL_THREE_STATUS.md`; the latest full code audit (bugs, architecture, fixture-vs-live map) is `docs/architecture/code-audit-2026-08-15.md`.

## What GAIA is

A local-first, multi-tenant agricultural intelligence system for SylionX. The primary product object is a `GuidancePlan` with evidence and provenance — not a chat transcript. Deterministic data paths (geography, environment, regulation, economics) must answer without model calls; model inference is reserved for reasoning routes and always validated before persistence.

## Hard invariants — never violate these

1. **Money.** No paid API, paid model, storage upgrade, or overage may be enabled by code. `allow_automatic_paid_*` stays `False`. The $20 reserve is spent only by a human after a documented blocker. Do not "fix" a failing feature by enabling a paid provider.
2. **Tool Gateway.** Every external provider call goes through `packages/tools/gateway.py::execute()`. Never call an adapter directly from a service, API handler, or CLI command. The gateway is where tenancy, permissions, cost, quota, egress, cache, audit, and provenance are enforced — bypassing it silently disables all of them.
3. **Tenancy.** Every query, cache key, and persisted record must be scoped by `organization_id` (and workspace where applicable). A new cache key without tenant scoping is a cross-tenant leak (see audit finding S1-1 for the existing instance).
4. **Provenance.** External data gets a source record from GAIA's own compiled context. Model-generated citations/source IDs are rejected, never persisted. Do not weaken `packages/model_gateway/validation.py` or `packages/research/validation.py`.
5. **Fail closed.** Sentinel (regulatory) and anything legal/safety-adjacent returns `UNRESOLVED`/`UNAVAILABLE` rather than guessing. A regulatory rule that matches too broadly is worse than one that doesn't match.
6. **No fake reasoning.** Hardcoded values presented as computed output are bugs, not placeholders (audit S1-2 — chat season plans shipped with frozen 2026 dates — was exactly this). If real behavior can't be built yet, return an explicit `UNAVAILABLE`/deferred status — never a plausible-looking constant.
7. **Messy input is normal; handle it, don't refuse it.** GAIA should reach credible, verified, data-backed outcomes even when user input is incomplete or ambiguous — the way a person would. The reasoning layer interprets vague requests deterministically where possible (e.g., `derive_season_window` maps "plan my spring garden" to a real date window from today), states its assumptions and uncertainty in the output, and conveys results in usable forms (plans, calendars, reports). Non-determinism lives in interpretation and model reasoning — never in the guardrails above, and never as a license to fabricate: when the data genuinely can't support an answer, say `UNRESOLVED` and show what evidence is missing.
8. **Migrations are append-only.** New schema = new `migrations/NNNN_*.sql`. Never edit an existing migration. Index every tenant-scoped table you add (`organization_id`, plus common sort columns).
9. **External writes are gated.** Calendar writes, or any side effect leaving the machine, require the specific permission (`calendar.create`) and an explicit preview/commit step. Never make an external write path automatic.

## Architecture map

```
apps/cli/gaia.py ─┐
                  ├─> create_runtime() [apps/api/gaia_api/runtime.py] ─> apps/api/gaia_api/*_api.py handlers
apps/api server ──┘                                                        │
                                                                           v
packages/orchestration (orchestrator + guidance_graph LangGraph adapter)
   └─> subsystem services (environment/terra, geospatial/atlas, botany, vision,
        research, sentinel, season, mercator, calendar_gateway, institutional)
          └─> packages/tools/gateway.py  ── enforces ──> cost, quota, permissions,
                │                                        egress, cache, audit, provenance
                └─> provider adapters (fixture_adapters.py / live_adapters.py per package)
packages/model_gateway ── Ollama or fixture; validates GuidancePlan before persist
packages/persistence/sqlite.py ── single repository layer over migrations/*.sql
```

- CLI and API share one runtime and one handler layer. Add features in the service/handler layer once; do not duplicate logic per entry point.
- `guidance_graph.py` wraps the orchestrator's `_handle_*` methods. LangGraph is optional; the compat executor must stay behavior-identical. If you change a `_handle_*` method, both paths change — keep it that way.

## Commands (cross-platform warning)

`package.json` scripts and the `Makefile` currently invoke the Windows-only `py -3.13` launcher (audit P-1). On Linux/macOS use:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'   # full suite
python3 -m apps.cli.gaia doctor                        # env check
python3 -m apps.cli.gaia --database sqlite:///./local_data/gaia-alpha.sqlite3 dev   # local alpha at 127.0.0.1:8765
python3 scripts/bootstrap/validate_constitution.py     # constitution/lint check
```

Baseline as of 2026-08-15: **389 tests, 0 failures, 8 opt-in skips** — fully green on Linux. Any failure you introduce is yours. Run the full suite before every commit; tests use in-memory SQLite (or pin provider modes) and never hit the network. File-backed databases default several providers to live, so a test that creates a file-backed runtime must pin `GAIA_ATLAS_GEOGRAPHY_MODE` (and any other live-defaulting mode) to an offline value — see `tests/phase13/test_protocol_three_runtime.py::setUp`.

## Provider modes — know what's real

Defaults are chosen in `apps/api/gaia_api/runtime.py` (`_fixture_defaults_for_runtime`): tests/`:memory:` DBs get all-fixture; a file-backed DB gets **live** NWS, NASA POWER, GBIF, and Europe PMC. So the local alpha already makes real HTTP calls — CI does not.

- **Genuinely live-capable today:** Atlas geography (US Census geocoder via `GAIA_ATLAS_GEOGRAPHY_MODE=live`, gateway-mediated, privacy-reduced coordinates), NWS, NASA POWER, SSURGO soil (`GAIA_USDA_SOIL_MODE=live`), GBIF, Europe PMC, Genesys (optional `GENESYS_CLIENT_ID`/`GENESYS_CLIENT_SECRET` OAuth; fails closed without them), NASS and AMS (real normalization; each needs its free API key), Ollama text, Ollama LLaVA, Kew POWO (disabled pending terms review).
- **Live mode exists but is empty or partial:** APHIS/FDACS (page-probe only, returns zero rules), Pl@ntNet and Google Calendar (`NotImplementedError`).
- **No live path exists:** USGS Water, Texas Agriculture; Atlas watershed/hardiness/regulatory-geometry remain fixture/local.
- Env vars are `GAIA_*`-prefixed in code (`GAIA_NASS_API_KEY`, not `USDA_NASS_API_KEY`; `.env.example` lists both — the `GAIA_*` ones win).

When you implement or extend a live adapter: it must produce the same normalized contract shape as its fixture sibling, and you must add/extend a parity test (pattern: `tests/phase13/test_protocol_three_provider_parity.py`). Live smokes are opt-in via `GAIA_RUN_*_SMOKE=1` env vars and must never be required by CI.

## Known bugs — check before building nearby

Full detail in `docs/architecture/code-audit-2026-08-15.md` (see its remediation addendum for what was fixed on 2026-08-15: all five S1 bugs, the doctor portability check, the NASS/AMS env-var split, and the Atlas live geocoder). Still open — do not build on top of these without fixing or accounting for them:

- **S2-2** API 500 responses echo raw exception details (`apps/api/gaia_api/server.py`).
- **S2-3** Institutional knowledge search is keyword matching, not semantic retrieval (`packages/institutional/services.py:323`).
- **S3-3** Citation validators only inspect known citation keys; a fabricated DOI free-texted into a prose field is not caught.
- **S3-4** DST-unaware timezone fallback in `packages/season/calculations.py:62-72`.
- **P-1 (partial)** `package.json` scripts and the `Makefile` still invoke the Windows-only `py -3.13` launcher (doctor itself is fixed).
- **P-4** Migrations 0011–0013 create tenant-scoped tables with no indexes.

## Working rules

- **Tests mirror phases.** New work gets tests under the matching `tests/phaseN/` (or a new phase directory). Preserve the deterministic, offline-by-default posture.
- **Docs are load-bearing.** If you change behavior, update `CHANGELOG.md` and whichever status/architecture doc claims the old behavior. Doc drift is a recurring defect class here (two contradictory provider-mode tables shipped on the same day — see audit §5.1).
- **Untrusted content stays untrusted.** Retrieved abstracts, fetched pages, model output, and user uploads never change system policy, tool selection, citations, or cost posture. Prompt-injection boundaries are tested; keep them.
- **Real-data priority order** (when asked to reduce fixture reliance; through SSURGO done 2026-08-15): ~~Atlas geocoder~~ → ~~fix S1 bugs~~ → ~~Mercator NASS/AMS normalization~~ → ~~SSURGO fetch~~ → Sentinel rule ingestion → semantic institutional retrieval → USGS Water. Paid/credentialed providers (Pl@ntNet, Google Calendar, any paid model) require an explicit human decision first — propose, don't enable.
- **Location privacy.** Exact private coordinates never leave the machine; providers receive reduced/centroid geography per `packages/geospatial/privacy.py`. Preserve this in any new adapter.
