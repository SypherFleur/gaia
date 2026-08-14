# GAIA Protocol Three Status

Status date: 2026-08-14

Protocol Three is at the local-owner manual alpha gate. Public deployment, production authentication, live Postgres release validation, calendar writes, paid providers, and international legal jurisdiction packs remain blocked until Jason manually tests the browser alpha and approves the next gate.

## One-Command Startup

Run from the repository root:

```powershell
py -3.13 -m apps.cli.gaia --database sqlite:///./local_data/gaia-alpha.sqlite3 dev
```

Manual browser URL:

```text
http://127.0.0.1:8765/
```

Optional seed command:

```powershell
py -3.13 -m apps.cli.gaia --database sqlite:///./local_data/gaia-alpha.sqlite3 seed demo
```

Development identity:

- Label: `Development Identity`
- Organization/workspace: stable local alpha organization and `Alpha Workspace`
- Primary location: Austin garden, Travis County, TX
- Session model: one seeded local development identity/session per alpha database

## Runnable Components

- GAIA CLI: `doctor`, `dev`, `seed demo`, `providers health`, `chat`, `plant`, `vision`, `botanist`, `scholar`, `sentinel`, `season`, `mercator`, `research`, and `eval`.
- Local alpha API/UI: stdlib HTTP server under `/api/v1` plus static browser workspace.
- Database: SQLite default at `sqlite:///./local_data/gaia-alpha.sqlite3`.
- Seeded alpha data: one organization, one workspace, Texas locations, Cherokee Purple Tomato, observations, plant profile, sample research project, internal Season Plan, and seeded GuidancePlan.
- Model gateway: local Ollama text model when `GAIA_TEXT_MODEL_MODE=local`; fixture model when set to fixture.
- Vision gateway: local Ollama LLaVA when `GAIA_VISION_MODEL_MODE=local`; fixture vision when set to fixture.
- Provider registry, cost firewall, audit/provenance, tenant scoping, sovereign context, Atlas, Terra, Botanist, Vision, Scholar, Sentinel, Season, Mercator, model gateway, tool gateway, calendar gateway, and provider registry are composed in the alpha runtime.

## Broken Or Gated Components

- Docker/Postgres: Docker CLI is installed, but `docker version` cannot reach the Docker Desktop Linux engine pipe: `//./pipe/dockerDesktopLinuxEngine` is missing. No live Postgres test is claimed.
- Public deployment: blocked until owner manual browser approval.
- Production auth: not implemented for this gate; the alpha uses a deterministic local development identity only.
- Google Calendar writes: disabled by default. Calendar preview is local; external writes remain gated.
- Pl@ntNet: disabled by default unless credentials and mode are explicitly configured later.
- NASS/AMS: fixture-backed for alpha use. Existing opt-in smoke tests remain separate.
- International legal jurisdiction: not implemented. GAIA remains U.S.-jurisdiction-only for regulation, with global botanical biology/taxonomy/research context.
- Enterprise IAM, certifications, background jobs, large vector infrastructure, paid storage, paid telemetry, and paid model/API fallback: not enabled.

## Local Environment Status

Last checked with `gaia doctor`, `docker version`, `ollama list`, and `gaia providers health` on 2026-08-14.

- Python: PASS, `Python 3.13.3`
- Node: PASS, `v22.14.0`
- npm: PASS, `10.9.2`
- Git: PASS, `2.48.1.windows.1`
- Docker engine: WARN, Docker Desktop Linux engine pipe unavailable
- SQLite: PASS
- Ollama: PASS, `llama3.1:latest` and `llava:latest` listed
- UI/API reachability during doctor: DISABLED when not running
- Cost firewall: PASS, automatic paid usage off, spend `$0.00`, reserve `$20.00`

## Provider Modes

Default local alpha modes:

| Provider | Default mode | Notes |
| --- | --- | --- |
| NWS | fixture | Explicit free live mode via `GAIA_NWS_MODE=live` |
| NASA POWER | fixture | Explicit free live mode via `GAIA_NASA_POWER_MODE=live` |
| GBIF | fixture | Explicit free live mode via `GAIA_GBIF_MODE=live` |
| Genesys PGR | fixture | Global germplasm discovery remains fixture-backed by default |
| Europe PMC | fixture | Explicit free live mode via `GAIA_EUROPE_PMC_MODE=live` |
| APHIS | fixture | Explicit live mode is read-only official-page provenance probing |
| Texas Agriculture | fixture | U.S. state pack fixture |
| Florida FDACS | fixture | Explicit live mode is read-only official-page provenance probing |
| NASS | fixture | No automatic live credential usage |
| AMS | fixture | No automatic live credential usage |
| Google Calendar | disabled | Preview-only local alpha; external writes gated |
| Pl@ntNet | disabled | No key or paid path required |
| Ollama text | local | `llama3.1:latest` by default |
| Ollama vision | local | `llava:latest` by default |
| Future paid provider | disabled | Manual paid provider is disabled and no overage is allowed |

Fixture-vs-live parity tests verify that NWS, NASA POWER, GBIF, Europe PMC, APHIS, and FDACS live normalizers/read-only adapters return the same normalized contract shape as fixture mode.

## Validation Status

Manual owner checklist:

```text
docs/testing/manual-alpha-checklist.md
```

Automated final verification for this checkpoint:

- Final full test count: 324 tests
- Final opt-in skip count: 8 skips
- Eval prompt count: 81 fixture prompts
- Browser/manual scenario automation: server/static UI smoke plus API owner-scenario smoke passed; no repo-local Playwright/Puppeteer/Selenium runner was installed, so no real browser driver was added.
- Supervised dev smoke: `gaia dev --smoke-seconds 0.2` started, printed ports/model/database/spend, and shut down cleanly.
- Port-collision regression: `gaia dev` now fails if the target port is serving a non-GAIA status endpoint or the child process exits.
- Persistence restart proof: using `sqlite:///./local_data/gaia-alpha.sqlite3`, after seed, stop, restart, and persistence read, the same workspace retained 1 plant, 1 observation, 1 Season Plan, and 1 GuidancePlan.
- Local-agent review: two read-only local agents reviewed guardrails/runtime. Findings were fixed before final verification: port-collision false pass, disabled provider health/mode clarity, UI hardcoded cost policy display, and incomplete economics chat provenance display.

## Guardrail Status

- Cash: `$0.00` spent, `$20.00` reserve intact.
- Paid usage: no paid API, paid model, paid storage, paid telemetry, paid vector DB, or overage path enabled.
- Tenant isolation: alpha runtime uses one stable local organization/workspace identity and repository-scoped queries.
- Provenance: API/UI display source IDs, source chips, provider modes, and source-backed records from GAIA services.
- Sovereign mode: available through `--sovereign`; remote model egress remains disabled.
- Route/UI boundary: HTTP route handlers and browser UI are presentation/runtime layers over existing GAIA services, gateways, policy checks, provenance, tenancy, and cost controls.
