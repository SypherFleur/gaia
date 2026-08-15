# GAIA Protocol Three Status

Status date: 2026-08-15

Protocol Three is at the local-owner manual alpha gate. The engine is production-grade; the deployment story is not, and cannot be until the owner makes the authentication and hosting decisions listed under "Blocked on a human decision".

## One-command startup

```bash
python3 -m apps.cli.gaia --database sqlite:///./local_data/gaia-alpha.sqlite3 dev
```

Browser: `http://127.0.0.1:8765/`. Optional seed: `python3 -m apps.cli.gaia --database sqlite:///./local_data/gaia-alpha.sqlite3 seed demo`.

`npm test`, `make test`, and the direct `python3 -m unittest` command all work on Linux, macOS, and Windows. Set `GAIA_PYTHON` to pin an interpreter.

## Verification status

- **Test suite: 436 tests, 0 failures, 8 opt-in skips.** Fully green on Linux.
- **CI: `.github/workflows/ci.yml`** runs the offline suite and constitution check on Linux/macOS/Windows across Python 3.12 and 3.13, plus guardrail jobs asserting the financial constitution stays intact and every live smoke stays opt-in. CI never reaches a live provider.
- **Cash: $0.00 spent, $20.00 reserve intact.** No paid API, model, storage, telemetry, or overage path is enabled.
- **Full code audit with five remediation tiers:** `docs/architecture/code-audit-2026-08-15.md`.

## Provider modes — what is actually real

Defaults come from `apps/api/gaia_api/runtime.py::_fixture_defaults_for_runtime`. Tests and `:memory:` databases get all-fixture. **A file-backed database defaults the free providers to live**, so the documented startup above makes real HTTP calls.

| Provider | Default (file-backed) | Reality |
| --- | --- | --- |
| Census geocoder (Atlas admin) | live | Real, free, keyless. Gateway-mediated, coordinates reduced to ~1.1 km |
| NWS | live | Real, free, keyless |
| NASA POWER | live | Real, free, keyless |
| SSURGO soil | live | Real, free, keyless |
| USGS Water | live | Real, free, keyless |
| Atlas watershed (USGS NLDI) | live | Real, free, keyless |
| GBIF | live | Real, free, keyless |
| Europe PMC | live | Real, free, keyless |
| Ollama text / LLaVA | local | Real; requires local Ollama |
| Genesys PGR | disabled | Real adapter; optional OAuth creds, fails closed without them |
| USDA NASS | live iff key set | Real normalization; needs a free API key |
| USDA AMS | live iff key set | Real normalization; needs a free API key |
| Kew POWO | disabled | Real adapter; held pending terms-of-use review |
| APHIS / Florida FDACS | disabled | Live mode is a page-probe for provenance only — **yields zero structured rules** |
| Texas Agriculture | fixture | No live path exists |
| Atlas hardiness / regulatory geometry | fixture | No live path exists |
| Pl@ntNet | disabled | `NotImplementedError`; needs a key |
| Google Calendar | disabled | `NotImplementedError`; needs OAuth and is an external write |

**Sentinel's decision source is hand-authored fixture rules.** Live mode proves the official pages are reachable and hashes them for provenance; it does not parse regulatory text. This is deliberate — see "Deliberately deferred".

## Not verified against live endpoints yet

The eight keyless live adapters were built and tested structurally (real HTTP client usage, real response-schema parsing, fail-closed paths, parity with fixture contracts) but **no successful live call has been recorded**. The development sandbox blocks those hosts at the egress proxy, and NASS/AMS additionally need keys that have not been issued.

**This is the highest-value next action and only the owner can do it.** On a machine with open egress:

```bash
GAIA_ATLAS_GEOGRAPHY_MODE=live GAIA_ATLAS_WATERSHED_MODE=live \
  GAIA_USDA_SOIL_MODE=live GAIA_USGS_WATER_MODE=live \
  python3 -m apps.cli.gaia --database sqlite:///./local_data/gaia-alpha.sqlite3 dev
```

Set a real location in the UI and check the environment view. Any schema drift fails closed with a reason string rather than corrupting data; report the reason and it is a small fix.

## Blocked on a human decision

- **Production authentication.** The alpha uses one deterministic local development identity. No identity provider has been chosen. No code should be written until it is.
- **Public deployment, Postgres release validation.** Gated on the owner's manual browser approval (`docs/testing/manual-alpha-checklist.md`). Docker was unavailable in the development environment, so no live Postgres run is claimed.
- **Pl@ntNet** (needs a key) and **Google Calendar** (needs OAuth, and is an external write path). Both require an explicit human go under the financial constitution.
- **Kew POWO** terms-of-use review.
- **USDA NASS / AMS free API keys** if market data is wanted.

## Deliberately deferred

- **Sentinel regulatory rule ingestion.** Parsing APHIS/TDA/FDACS HTML into structured quarantine rules is brittle, and a subtly wrong answer in a fail-closed legal system is worse than an honest curated one. The current posture — hand-authored rules with live provenance probes and a documented review date — is the recommended interim until a structured government feed exists. Revisit only with a deliberate decision.
- **Vector-semantic knowledge retrieval.** Institutional search is FTS5/BM25 with stemming: real ranked lexical retrieval, not embeddings. It matches words, not meaning. Adequate today; upgrading means a real embedding model, not the checksum `FixtureEmbeddingProvider`.

## Guardrail status

- Tool Gateway mediates every external provider call; no bypass exists.
- Tenancy is enforced on queries, cache keys, and persisted records. Private-content cache keys are namespaced by organization at the gateway.
- No bibliographic identifier reaches persistence unverified — including identifiers written into narrative prose.
- Circuit breaker opens on repeated failure and recovers through a half-open probe; outbound HTTP retries only transient failures with jittered backoff.
- Sovereign mode available via `--sovereign`; remote model egress stays disabled.
