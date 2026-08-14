# GAIA Manual Local Alpha Checklist

This checklist is the owner gate for Protocol Three. Public deployment, production auth, live Postgres validation, and calendar writes remain blocked until Jason completes this browser test and approves the next gate.

## Startup

Use this exact startup command from the repository root:

```powershell
py -3.13 -m apps.cli.gaia --database sqlite:///./local_data/gaia-alpha.sqlite3 dev
```

Open this URL:

```text
http://127.0.0.1:8765/
```

Optional seed command if the browser workspace is empty:

```powershell
py -3.13 -m apps.cli.gaia --database sqlite:///./local_data/gaia-alpha.sqlite3 seed demo
```

Expected launch result:

- The terminal prints `GAIA Local Alpha`, the UI URL, the API URL, SQLite database mode, local or fixture model labels, and `$0 automatic paid usage`.
- The browser opens a GAIA workspace with Chat, Plants, Vision, Season, Research, Movement, Markets, and Settings navigation.
- The identity label says `Development Identity`.

## Owner Steps

1. Open Settings.
   Expected: database is SQLite, telemetry is disabled, spend is `$0.00`, reserve is `$20.00`, paid providers are not enabled, and provider modes are visible.

2. Click `Seed Demo`.
   Expected: Cherokee Purple Tomato appears in Plants. Settings persistence shows at least one plant, one observation, one Season Plan, and one GuidancePlan.

3. Open Plants and select Cherokee Purple Tomato.
   Expected: the plant profile shows `Solanum lycopersicum`, cultivar `Cherokee Purple`, source-backed profile fields, and observation history.

4. In Chat, ask: `What county am I in?`
   Expected: GAIA answers Travis County, Texas. Route should be geography or context-like, and model runs should remain zero.

5. In Chat, ask: `What environment context matters for this tomato today?`
   Expected: GAIA shows weather/climate/soil context with source chips or provider status. It must not invent weather beyond the provider context.

6. In Vision, upload a plant photo and click Analyze Photo.
   Expected: visual observations and hypotheses are shown separately. No confirmed diagnosis is claimed from the image alone.

7. In Season, create a plan for tomato from `2026-09-15` to `2026-12-15`, then click Preview Events.
   Expected: a Season Plan and preview events appear. Google Calendar remains disconnected or preview-only. External calendar writes must remain zero.

8. In Research, search: `Do lunar phases improve germination?`
   Expected: evidence results show source/evidence quality and uncertainty. Lunar claims should not dominate over soil temperature, water, cultivar, or local context.

9. In Research, synthesize: `What research supports tomato companion planting?`
   Expected: GAIA returns an evidence synthesis with claims, limitations, and source IDs. Model use is not required for this alpha check.

10. In Movement, check `Citrus sinensis` from Houston, TX to Orlando, FL as a live plant.
    Expected: result is restricted or conditional, includes USDA APHIS and/or FDACS authority, and shows applicable rule/source context. GAIA must not claim to be the legal authority.

11. In Markets, view context for `tomato`.
    Expected: dated market/production context appears with freshness labels. It must not be a forecast, guarantee, trading signal, or live logistics claim.

12. Open Settings again.
    Expected: spend remains `$0.00`, reserve remains `$20.00`, paid providers are disabled, and provider modes remain fixture/local/disabled unless explicitly changed by environment variables.

## Persistence Restart Gate

This is required before Protocol Three is considered complete.

1. In the browser, create or verify one GuidancePlan through Chat or the seeded demo.
2. Stop GAIA with `Ctrl+C` in the terminal.
3. Start GAIA again with the same startup command:

```powershell
py -3.13 -m apps.cli.gaia --database sqlite:///./local_data/gaia-alpha.sqlite3 dev
```

4. Refresh the browser at `http://127.0.0.1:8765/`.
5. Verify the same development workspace, Cherokee Purple Tomato, observation history, and at least one GuidancePlan still exist.

If this restart test fails, the alpha is not accepted.

## Provider Mode Matrix

Default local alpha modes:

- Local zero-cost models: Ollama text `llama3.1:latest`, Ollama vision `llava:latest` when available.
- Fixture by default: NWS, NASA POWER, GBIF, Genesys PGR, Europe PMC, APHIS, Texas Agriculture, Florida FDACS, NASS, AMS.
- Disabled by default: Google Calendar, Pl@ntNet, future paid providers.
- Explicit free live opt-in only: `GAIA_NWS_MODE=live`, `GAIA_NASA_POWER_MODE=live`, `GAIA_GBIF_MODE=live`, `GAIA_EUROPE_PMC_MODE=live`, `GAIA_APHIS_MODE=live`, `GAIA_FLORIDA_FDACS_MODE=live`.

Live APHIS and FDACS are read-only official-page provenance probes. Movement decisions still flow through Sentinel jurisdiction packs and must not scrape new legal logic from route handlers or UI code.
