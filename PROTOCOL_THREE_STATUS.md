# GAIA Protocol Three Status

Status date: 2026-08-16

Protocol Three is at the local-owner manual alpha gate. The engine is production-grade; the deployment story is not, and cannot be until the owner makes the authentication and hosting decisions listed under "Blocked on a human decision".

## One-command startup

```bash
python3 -m apps.cli.gaia --database sqlite:///./local_data/gaia-alpha.sqlite3 dev
```

Browser: `http://127.0.0.1:8765/`. Optional seed: `python3 -m apps.cli.gaia --database sqlite:///./local_data/gaia-alpha.sqlite3 seed demo`.

`npm test`, `make test`, and the direct `python3 -m unittest` command all work on Linux, macOS, and Windows. Set `GAIA_PYTHON` to pin an interpreter.

## Verification status

- **Test suite: 475 tests, 0 failures, 9 opt-in skips.** Fully green on Linux.
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
| Atlas watershed (USGS WBD) | live | Real, free, keyless |
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

## Live verification — RECORDED 2026-08-16

**All eight keyless providers returned real data from their real endpoints: `checked 8, ok 8, failed 0`.** Verified by the owner on a machine with open egress (the development sandbox blocks these hosts at its egress proxy, so this could only be run locally).

| Provider | Outcome | Sample returned |
| --- | --- | --- |
| census-geocoder | OK | Travis County, TX |
| usgs-nldi | OK | `5781313` — see caveat below; source since replaced by `usgs-wbd` |
| nws | OK | 76 °F |
| nasa-power | OK | `null` — see caveat below |
| usda-nrcs-sda | OK | Urban land, 0 to 6 percent slopes |
| usgs-water | OK | 38 sites |
| gbif | OK | Solanum lycopersicum L. (+ `occurrence_is_not_cultivation_suitability`) |
| europe-pmc | OK | 1 work |

Two data-quality caveats found by that run, both fixed on 2026-08-16:

- **NASA POWER** reported OK with a `null` temperature. POWER publishes on a variable lag, so the probe's recent date had no value yet. The adapter now requests a 10-day window and uses the most recent day the service actually published, reporting it as `observation_date`.
- **Atlas watershed** returned a bare COMID (`5781313`) rather than a watershed name. NLDI's position endpoint returns the NHDPlus *flowline* at the coordinate — a stream reach, not a watershed — and its `name` is a GNIS stream name that is usually empty, so the answer fell through to the identifier. The source is now the USGS Watershed Boundary Dataset, which is the authority that names hydrologic units; a code is never returned in place of a name.

Both fixes changed which endpoint or date range is requested, so **re-run `providers verify` to confirm the watershed name and POWER temperature now come back populated.**

Still unverified: **USDA NASS and AMS**, which need their own free API keys. Everything else in the table above is confirmed against production endpoints.

## Re-running verification

```bash
python3 -m apps.cli.gaia providers verify
```

It makes real network calls, needs no key, writes nothing, and spends nothing. Each provider reports one of:

- **OK** — a real response parsed into GAIA's contract. Any `warnings` are semantic caveats that travel with a good answer (e.g. GBIF's `occurrence_is_not_cultivation_suitability`), never failures.
- **NO_DATA** — the provider answered but had nothing for the probe coordinate. Correct fail-closed behavior, not a defect.
- **FAILED / ERROR** — unreachable endpoint or drifted schema. Paste the `detail` string; each maps to a specific adapter and is a small fix.

Probe a specific location with `--latitude` / `--longitude`. For an end-to-end check afterwards, start the alpha and set a real location in the UI:

```bash
python3 -m apps.cli.gaia --database sqlite:///./local_data/gaia-alpha.sqlite3 dev
```

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
