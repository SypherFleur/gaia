"""The GAIA build queue.

Each task declares the files it owns, the provider it must prove works, and a
hard cost cap. Tasks are deliberately narrow: anything touching the Tool
Gateway, the repository layer, the runtime wiring, or AGENTS.md is a human's
job and is fenced off in gate.PROTECTED.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Task:
    key: str
    title: str
    brief: str
    owns: list[str]
    provider_id: str | None = None
    budget_usd: float = 2.00
    max_turns: int = 40
    # Env vars that must be set for this task to be verifiable at all. A task
    # whose provider needs a key cannot prove anything without it, so the
    # dispatcher refuses to start rather than burning turns to reach
    # "UNVERIFIABLE".
    requires_env: list[str] = field(default_factory=list)
    claimed_migration: str | None = None
    allow_protected: bool = False


TASKS: list[Task] = [
    Task(
        key="wbd-watershed-fix",
        title="Fix the USGS WBD watershed adapter",
        provider_id="usgs-wbd",
        owns=["packages/geospatial/live_adapters.py", "tests/phase13/test_atlas_watershed.py", "tests/fixtures/*"],
        budget_usd=3.00,
        brief="""
`providers verify` reports `usgs-wbd` as NO_DATA with reason
`coordinate_outside_wbd_coverage` for the Austin probe coordinate (30.27,
-97.74). Austin is unambiguously inside WBD coverage, so this is a defect in
the adapter, not an honest no-coverage answer.

Three known problems in `packages/geospatial/live_adapters.py`:

1. `coordinate_outside_wbd_coverage` is returned from two different places --
   an HTTP 404, and an empty `features` list. Those are completely different
   failures (wrong endpoint vs. genuinely no feature at this point) and must
   have distinct reason strings, or a probe run tells you nothing about which.

2. `select_hydrologic_unit_layer` picks the *most specific* `N-digit HU` layer
   the service publishes. WBD defines 14- and 16-digit hydrologic units, but
   they are mapped in only a handful of states. If the service exposes those
   layers, this rule selects one and every CONUS coordinate returns zero
   features. Do not guess which layer is right -- fetch
   `{base}/MapServer?f=json` and look at the real layer list.

3. `DEFAULT_HU_LAYER_ID = 6` is a pinned magic index, which is exactly what the
   discovery logic exists to avoid.

Fix by cascading from the 12-digit level (the national standard, complete CONUS
coverage) outward to coarser levels until a *named* unit is found, reporting
which level answered. Never return a HUC code in place of a name.

Capture the real service responses you used into `tests/fixtures/` with the URL
and capture date in the file, and drive the tests from those captured payloads.
Hand-written payloads are not acceptable evidence here: the bug you are fixing
was introduced with a hand-written test fixture that asserted the bug as
correct behaviour.
""",
    ),
    Task(
        key="capture-live-fixtures",
        title="Capture real provider responses as test fixtures",
        owns=["tests/fixtures/*", "tests/phase13/*"],
        budget_usd=3.00,
        brief="""
Every live adapter's normalizer is currently tested against payloads someone
typed by hand. That is how the watershed bug shipped: the fixture confirmed the
author's assumption instead of describing the real service.

For each keyless live provider -- census-geocoder, nws, nasa-power,
usda-nrcs-sda, usgs-water, gbif, europe-pmc -- issue the adapter's real request,
save the verbatim response under `tests/fixtures/<provider_id>/`, and record the
request URL and capture date inside the file. Then repoint the existing
normalizer tests at the captured payloads.

Do not change adapter behaviour in this task. If a captured response reveals a
normalizer bug, do not fix it -- report it in `unresolved` so a human can
schedule it. Changing behaviour and changing the evidence in the same commit
makes both unreviewable.
""",
    ),
    Task(
        key="nass-verify",
        title="Verify the USDA NASS adapter against the real endpoint",
        provider_id="usda-nass",
        owns=["packages/mercator/live_adapters.py", "packages/providers/verification.py", "tests/phase10/*", "tests/fixtures/*"],
        requires_env=["GAIA_NASS_API_KEY"],
        budget_usd=2.50,
        brief="""
The NASS adapter has real normalization but has never been run against the real
Quick Stats endpoint. A key is now available in the environment.

Add `usda-nass` to `packages/providers/verification.py` so `providers verify`
covers it, then make it return real data. Capture the real response under
`tests/fixtures/usda-nass/` and drive the normalizer test from it.

The key must be read from the environment. Never write a key into a file, a
test, a fixture, or a commit.
""",
    ),
    Task(
        key="ams-verify",
        title="Verify the USDA AMS adapter against the real endpoint",
        provider_id="usda-ams",
        owns=["packages/mercator/live_adapters.py", "packages/providers/verification.py", "tests/phase10/*", "tests/fixtures/*"],
        requires_env=["GAIA_AMS_API_KEY"],
        budget_usd=2.50,
        brief="""
Same shape as the NASS task, for USDA AMS Market News. Add `usda-ams` to
`packages/providers/verification.py`, prove it returns real data, capture the
response as a fixture, and drive the normalizer test from it.

The key must be read from the environment and never committed.
""",
    ),
    Task(
        key="plantnet-adapter",
        title="Implement the live Pl@ntNet identification adapter",
        provider_id="plantnet",
        owns=["packages/vision/plantnet.py", "packages/providers/verification.py", "tests/phase6/*", "tests/fixtures/*"],
        requires_env=["GAIA_PLANTNET_API_KEY"],
        budget_usd=4.00,
        brief="""
`packages/vision/plantnet.py:54` raises NotImplementedError. Implement the live
path against the Pl@ntNet v2 identify API.

Hard constraints, all of which are existing GAIA invariants:
- The call goes through the Tool Gateway. Never call the adapter directly.
- The normalized result must match the fixture sibling's contract exactly.
- Add it to `packages/providers/verification.py`.
- Add a parity test following `tests/phase13/test_protocol_three_provider_parity.py`.
- The live smoke is opt-in via `GAIA_RUN_PLANTNET_SMOKE=1` and must never be
  required by CI.
- User images are private content. Respect the existing egress policy for
  private images; do not weaken it to make the call succeed.
""",
    ),
]


BY_KEY = {task.key: task for task in TASKS}
