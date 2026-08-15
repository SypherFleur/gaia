# GAIA Code Audit — 2026-08-15

Scope: full read-through of `packages/`, `apps/`, `migrations/`, `tests/`, and root/architecture docs, focused on (a) concrete bugs, (b) architectural health, and (c) the gap between fixture/mock defaults and real live data. Test baseline on the audit machine (Linux, Python 3.11): **347 tests, 1 failure, 8 opt-in skips**. The one failure is itself Finding P-1 below.

Severity tiers: **S1** = tenant/security/guardrail or wrong-answer bugs; **S2** = broken or unreachable features; **S3** = latent/dormant defects and inconsistencies; **P** = portability/docs drift.

---

## 1. What is genuinely sound

Verified by reading code, not docs:

- **Tool Gateway mediation is real.** Every provider-backed service (Terra, Botanist, Vision, Scholar, Sentinel, Mercator, Calendar) routes through `packages/tools/gateway.py::execute()`, which enforces tenant membership, permissions, provider enabled-state, egress, org policy, Cost Firewall, quota, cache, audit, and the usage ledger. No bypasses were found.
- **No paid-usage bypass exists.** `packages/cost/firewall.py`, the Tool Gateway, and `packages/model_gateway/gateway.py` consistently gate on `MANUAL_PAID` billing class and `allow_automatic_paid_*` flags (default `False`). CLI, API, and orchestrator share one `GaiaRuntime`, so there is a single enforcement path.
- **CLI/API do not drift.** `apps/cli/gaia.py` and `apps/api/gaia_api/server.py` both call `create_runtime()` and the same `apps/api/gaia_api/*_api.py` handlers. No duplicated business logic.
- **Orchestrator vs LangGraph adapter is not parallel/dead code.** `GuidanceWorkflowGraph` (`packages/orchestration/guidance_graph.py`) wraps the orchestrator's own `_handle_*` methods; LangGraph is an optional compiled backend with an equivalent local compat executor. Both paths delegate identically. Note: `langgraph` is not installed in this environment, so only the compat path has ever run here.
- **Citation defense works for structured fields.** `packages/model_gateway/validation.py` and `packages/research/validation.py` recursively reject model-fabricated IDs under the known citation keys, and the orchestrator persists only system-created source records.

---

## 2. S1 — Highest severity findings

### S1-1. Vision analysis cache leaks across tenants and ignores prompt/context
`packages/vision/service.py:98-119`; schema at `migrations/0002_tool_cost_provenance.sql:54-65`.

Cache key is `vision:{provider_id}:{sha256(image_bytes)}`. The `cache_records` table has no `organization_id` column.

- **Cross-tenant leak:** byte-identical images uploaded by two different organizations share one cache entry; Org B receives Org A's cached analysis (candidates, hypotheses, safety notes) — even with `contains_private_image=True`.
- **Same-tenant staleness:** the key excludes `prompt`, `user_plant_context`, and `environmental_context`, all of which are sent to the model. Re-analyzing the same image with a different prompt within the 24h TTL returns the first answer verbatim, while the persisted `VisualAnalysis` records the *new* context — stored context and stored findings disagree.

Fix direction: include organization_id and a hash of prompt+context in the cache key (or add tenant scoping to the cache backend itself).

### S1-2. Chat-driven Season plans hardcode the date range
`packages/orchestration/orchestrator.py:377-397` (`_handle_season`).

Every season plan created through chat uses `start_date="2026-09-15"`, `end_date="2026-12-15"`, `planning_date="2026-08-11"` regardless of the user's message. "Plan my spring garden starting in March" produces a fall 2026 plan. Crops are extracted from the message; dates never are. The REST/CLI paths accept explicit date overrides, but the chat path has neither an override nor natural-language date parsing, and the LangGraph adapter inherits the same call. This is a mock-in-disguise: a hardcoded value presented as reasoning output.

### S1-3. Genesys live mode crashes at request time
`packages/botany/live_adapters.py:78-115` vs. call site `packages/botany/tools.py:82`.

`GenesysPGRAdapter` defines only `normalize_accession_search()`; it has no `search_accessions()`, which is what the tool invokes on the provider. Setting the documented `GAIA_GENESYS_MODE=live` (`apps/api/gaia_api/runtime.py:1402`) yields `AttributeError` on first germplasm query instead of a graceful `UNAVAILABLE`. `.env.example` also documents `GENESYS_CLIENT_ID`/`GENESYS_CLIENT_SECRET` that the adapter never reads.

### S1-4. Mercator price comparison ignores grade
`packages/mercator/normalization.py:78-87` (`comparable_units`); used by `packages/mercator/service.py:130-136`.

`normalize_unit()` captures `grade`, but `comparable_units` never inspects it: two `$/lb` observations with different USDA grades (Grade A vs Grade C) are reported as directly comparable with a computed price delta, silently conflating quality tiers. The existing test suite covers package mismatch only, not grade mismatch (`tests/phase10/test_mercator_economic_intelligence.py:211-215`).

### S1-5. Shared SQLite connection across a threading HTTP server, no locking
`apps/api/gaia_api/runtime.py:1055` (`check_same_thread=False`) + `apps/api/gaia_api/server.py:209` (`ThreadingHTTPServer`).

One `sqlite3.Connection` (and the repository/gateways wrapping it) is used from a new thread per request with zero synchronization anywhere in the repo. Concurrent writes (two chats, or chat + plant edit) can race: `database is locked` errors at best, interleaved transaction state at worst. Fix direction: per-request connections, a connection pool, or a global write lock.

---

## 3. S2 — Broken or unreachable features

- **S2-1. `patch_plant`/`delete_plant` are unreachable.** Implemented in `apps/api/gaia_api/plant_api.py:69-86`, but `server.py` only handles GET/POST — no PATCH/DELETE routes exist, and no POST route calls them. Editing or soft-deleting a plant 404s through the running API.
- **S2-2. 500 responses echo raw exception details.** `apps/api/gaia_api/server.py:103-104, 152-153` return exception class + message verbatim to the client. Acceptable for a localhost alpha; must be fixed before any exposure.
- **S2-3. Institutional knowledge search is not semantic.** `packages/institutional/embeddings.py` produces a 3-number checksum "embedding"; `packages/institutional/services.py:323` never reads stored embeddings and does keyword substring counting. Real retrieval must be built, not just re-pointed at a real model.

---

## 4. S3 — Latent defects and inconsistencies

- **S3-1. Sentinel `_scope_matches` early-return skips county/quarantine checks when `state_code == "ANY"`** (`packages/sentinel/engine.py:110-142`). No current fixture rule combines `ANY` with `counties`/`quarantine_zone`, so it is dormant — but the first rule that does will match too broadly. In a fail-closed regulatory engine, this is the wrong direction to fail.
- **S3-2. `UsageLedger.estimated_external_spend` aggregates across all organizations** (`packages/audit/ledger.py:67-69`), unlike every sibling method. Today it only feeds status displays; if it is ever wired into spend-based enforcement, one tenant's usage throttles another's budget.
- **S3-3. Prose-field citation gap.** Both validators only inspect the fixed citation keys; a model that free-texts a fabricated DOI inside `recommendations[].summary` is not caught. Possibly an accepted tradeoff — should be a documented decision rather than an accident.
- **S3-4. DST-unaware timezone fallback** (`packages/season/calculations.py:62-72`). When `tzdata` is unavailable, `America/Chicago` becomes a fixed `-5` offset; during CST (Nov–Mar) computed action times are silently off by one hour.
- **S3-5. `GBIFApiAdapter` has no try/except around fetch/parse** (`packages/botany/live_adapters.py:26-31`), unlike sibling `KewPOWOApiAdapter`. Caught downstream by the Tool Gateway's broad handler, so not exploitable — but the two adapters report failures differently.

---

## 5. Fixture vs. live: the real-data map

### 5.1 The default-mode contradiction

`apps/api/gaia_api/runtime.py` holds two default tables: `_fixture_provider_defaults()` (~line 1302, everything fixture) and `_normal_provider_defaults()` (~line 1324, NWS/NASA POWER/GBIF/Europe PMC **live**; NASS/AMS live if keyed). Selection (`_fixture_defaults_for_runtime()`, ~line 1293): fixture defaults apply only when `GAIA_RUNTIME_MODE` ∈ {demo, fixture, test} or the DB is `:memory:`.

Consequences:
- The documented one-command startup (file-backed SQLite, no `GAIA_RUNTIME_MODE`) runs NWS, NASA POWER, GBIF, and Europe PMC **live** — real, uncached-across-restarts, unthrottled HTTP on every request.
- Every automated test uses `:memory:`, so CI only ever exercises fixtures.
- `PROTOCOL_THREE_STATUS.md`'s provider table ("default: fixture" for all) is wrong for the run it describes; `docs/architecture/source-reconciliation-2026-08-14.md` (same date) states the actual behavior. Resolve to one truth table.

### 5.2 Provider truth table

| Provider | Live adapter exists | Live genuinely functional | Effective default (file-DB alpha) | Blocking real data |
|---|---|---|---|---|
| NWS weather | Yes (`environment/live_adapters.py:17`) | **Yes** | live | Nothing |
| NASA POWER | Yes (`environment/live_adapters.py:80`) | **Yes** (handles `-999` sentinels) | live | Nothing |
| GBIF taxonomy | Yes (`botany/live_adapters.py:13`) | **Yes** | live | Nothing |
| Europe PMC | Yes (`research/europe_pmc.py:28`) | **Yes** (most complete adapter in repo) | live | Nothing |
| Ollama text | Yes (`model_gateway/ollama.py:16`) | **Yes** | local | Needs Ollama running |
| Ollama LLaVA vision | Yes (`vision/ollama_llava.py:23`) | **Yes** | local | Needs Ollama + `llava` |
| Kew POWO | Yes (`botany/live_adapters.py:118`) | **Yes** | disabled | Policy hold (Kew terms review) |
| USDA SSURGO soil | No fetch method — normalizer only (`environment/live_adapters.py:140`) | No | disabled | Adapter unfinished (no HTTP path) |
| USGS Water | No live class at all | — | disabled | Never started |
| Genesys PGR | Broken (S1-3) | No — crashes | disabled | Missing method + unwired auth |
| APHIS (Sentinel) | Page-probe only (`sentinel/adapters.py:441`) | No — returns **zero rules** (parity tests assert `rules == []`) | disabled | Rule extraction never built; all rules are hand-authored fixtures |
| Texas Agriculture | No live class | — | disabled | Same as APHIS, minus even the probe |
| Florida FDACS | Page-probe only | No — zero rules | disabled | Same |
| USDA NASS | Partial (`mercator/live_adapters.py:19`) | No — returns raw record count, warning `live_normalization_deferred_to_fixture_contracts`; 4 of 5 methods hardcoded UNAVAILABLE | live iff `GAIA_NASS_API_KEY` | Normalization never written |
| USDA AMS | Stub (`mercator/live_adapters.py:50`) | No — zero HTTP calls even with key | UNAVAILABLE always | Never implemented past key check |
| Pl@ntNet | Class raises `NotImplementedError` (`vision/plantnet.py:54`) | No | disabled | Deliberately deferred |
| Google Calendar | Class raises `NotImplementedError` (`calendar_gateway/fixture_provider.py:51-75`) | No | disabled | No OAuth wiring exists |
| **Atlas geocoding** | **No live provider anywhere.** "Non-fixture" `CLIGeographyProvider` (`runtime.py:1187`) is a ~6-county hardcoded bounding-box table with Travis County, TX fallback | — | hardcoded lookup | No geocoder was ever integrated |

### 5.3 Recommended real-data sequence

1. **Atlas live geocoding** (e.g., US Census Geocoder — free, no key). Everything location-sensitive (Terra, Sentinel, Season, Mercator geography) is capped at ~6 counties until this exists. Single highest-leverage change.
2. **Fix S1-1..S1-5** before widening live traffic — the vision cache and SQLite threading issues get worse, not better, with real data and real concurrency.
3. **Mercator NASS/AMS normalization** — keys are free; the missing piece is parsing into `ProductionStatistic`/market-report contracts.
4. **Genesys**: implement `search_accessions()` + OAuth client-credentials flow, or mark the mode invalid so it fails closed instead of crashing.
5. **SSURGO fetch path** (free SDA endpoint) — the normalizer half already exists.
6. **Sentinel rule ingestion** — hardest; requires structured extraction from APHIS/TDA/FDACS pages or feeds. Keep fail-closed posture; hand-authored rules with live provenance probes is a defensible interim, but label it as such in user-facing output.
7. **Pl@ntNet / Google Calendar / paid providers** — require credentials and (for Calendar) external writes; each needs an explicit human go-decision per the financial constitution.

---

## 6. P — Portability and docs drift

- **P-1. The entire command surface is Windows-only.** `package.json` scripts, the `Makefile` (documented as the Unix mirror), and the doctor's Python check (`apps/api/gaia_api/runtime.py:1014`, `["py", "-3.13", "--version"]`) all invoke the Windows `py` launcher. On Linux/macOS: `npm test`/`make test` fail outright, and `gaia doctor` reports Python FAIL on a working machine — which is exactly the one test failure in the current suite (`tests/cli/test_gaia_cli.py:28`). Fix: resolve `sys.executable` for doctor; make scripts use `python3` or an env-var interpreter.
- **P-2. Test-count drift.** `PROTOCOL_THREE_STATUS.md` says 324 tests; the suite is 347. Minor, but status docs are load-bearing here.
- **P-3. Env-var naming split.** `.env.example` documents both `USDA_NASS_API_KEY` and `GAIA_NASS_API_KEY`; code reads only the `GAIA_*` names (`mercator/live_adapters.py:14`, `runtime.py:1337-1338`). Operators setting the USDA-prefixed names silently stay disabled.
- **P-4. Missing indexes on Phase 11–13 tables.** `migrations/0011`–`0013` create ~13 tenant-scoped tables with zero `CREATE INDEX` statements (migrations 0001–0010 index consistently). List queries (`WHERE organization_id = ? ORDER BY created_at`) will degrade as institutional workloads grow.

---

## 7. Verification notes

- All findings cite file:line and were made by reading source, not inferring from names or docs.
- Not verified: live endpoints were not called (adapters judged "functional" by real HTTP client usage + real schema parsing + error handling in code); the LangGraph compiled path has not executed in this environment (`langgraph` not installed).
- Dormant findings (S3-1, S3-2) are labeled as such: not currently triggerable, but wrong by construction.
