"""Independent verification of what a coding agent did.

Nothing here reads the agent's report. Every check runs a command and believes
only its exit code and output. This is the whole point of the harness: GAIA's
worst bugs shipped with a green suite and a confident summary.
"""

from __future__ import annotations

import fnmatch
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from .contract import CheckResult, GateReport, Outcome

# A keyless host GAIA genuinely depends on. Reachability here separates "this
# adapter is broken" from "this machine has no egress" -- the same distinction
# `providers verify` draws for providers, applied one level up.
EGRESS_CANARY = "https://api.weather.gov/"
EGRESS_TIMEOUT_SECONDS = 10.0

SUITE = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"]
CONSTITUTION = [sys.executable, "scripts/bootstrap/validate_constitution.py"]
VERIFY = [sys.executable, "-m", "apps.cli.gaia", "providers", "verify"]

# Shared, invariant-bearing files. An agent that edits these has left its lane
# regardless of what its task declared, because these are where tenancy, cost,
# egress, provenance, and schema ordering are enforced for everyone.
PROTECTED = (
    "packages/tools/gateway.py",
    "packages/persistence/sqlite.py",
    "apps/api/gaia_api/runtime.py",
    "pyproject.toml",
    "AGENTS.md",
    "CLAUDE.md",
)


def _run(command: list[str], cwd: Path, timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def has_egress() -> bool:
    """Can GAIA reach the network *the way GAIA reaches it*?

    This must use urllib, not a raw socket. A bare TCP connect ignores
    HTTPS_PROXY and succeeds on machines where every proxied request is
    refused, which reports a sandbox as having egress and turns every
    "could not check" into a false "adapter is broken".
    """
    request = urllib.request.Request(EGRESS_CANARY, headers={"User-Agent": "GAIA build harness egress canary"})
    try:
        with urllib.request.urlopen(request, timeout=EGRESS_TIMEOUT_SECONDS):
            return True
    except urllib.error.HTTPError:
        # The host answered; the status does not matter. Egress works.
        return True
    except Exception:
        return False


def changed_files(repo: Path, base: str) -> list[str]:
    result = _run(["git", "diff", "--name-only", base], repo, timeout=60)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def check_ownership(repo: Path, base: str, owns: list[str], allow_protected: bool) -> CheckResult:
    """The agent may only touch paths its task declared."""
    touched = changed_files(repo, base)
    if not touched:
        return CheckResult("ownership", Outcome.FAIL, "No files changed. The task produced nothing.")

    strays = [path for path in touched if not any(fnmatch.fnmatch(path, pattern) for pattern in owns)]
    protected = [] if allow_protected else [p for p in touched if p in PROTECTED]

    problems = []
    if strays:
        problems.append("Modified files outside this task's declared scope:\n  " + "\n  ".join(strays))
    if protected:
        problems.append(
            "Modified shared invariant-bearing files:\n  " + "\n  ".join(protected)
            + "\nThese are owned by a human. Revert them."
        )
    if problems:
        return CheckResult("ownership", Outcome.FAIL, "\n\n".join(problems))
    return CheckResult("ownership", Outcome.PASS, f"{len(touched)} file(s), all in scope.")


def check_migrations(repo: Path, base: str, claimed: str | None) -> CheckResult:
    """Migrations are append-only and numbered; two agents must not claim one number."""
    added = [p for p in changed_files(repo, base) if p.startswith("migrations/")]
    if not added:
        return CheckResult("migrations", Outcome.PASS, "No migration touched.")

    existing = {p.name for p in (repo / "migrations").glob("*.sql")}
    modified_existing = [p for p in added if Path(p).name in existing and Path(p).name != claimed]
    if modified_existing:
        return CheckResult(
            "migrations",
            Outcome.FAIL,
            "Edited an existing migration. Migrations are append-only:\n  " + "\n  ".join(modified_existing),
        )
    if claimed and any(Path(p).name != claimed for p in added):
        return CheckResult(
            "migrations",
            Outcome.FAIL,
            f"This task was allocated migration {claimed!r}; it wrote {added!r} instead.",
        )
    return CheckResult("migrations", Outcome.PASS, f"Added {added}.")


def check_suite(repo: Path) -> CheckResult:
    result = _run(SUITE, repo)
    if result.returncode == 0:
        tail = (result.stderr or result.stdout).strip().splitlines()[-3:]
        return CheckResult("tests", Outcome.PASS, "\n".join(tail))
    return CheckResult("tests", Outcome.FAIL, (result.stderr or result.stdout)[-6000:])


def check_constitution(repo: Path) -> CheckResult:
    result = _run(CONSTITUTION, repo, timeout=120)
    if result.returncode == 0:
        return CheckResult("constitution", Outcome.PASS, result.stdout.strip())
    return CheckResult("constitution", Outcome.FAIL, (result.stdout + result.stderr)[-3000:])


def check_live_provider(repo: Path, provider_id: str) -> CheckResult:
    """Did this provider actually return real data from its real endpoint?

    The only check in the gate that is evidence the work *works*. Everything
    else is evidence it did no harm.
    """
    if not has_egress():
        return CheckResult(
            "live",
            Outcome.UNVERIFIABLE,
            f"No outbound network from this machine ({EGRESS_CANARY} unreachable), so "
            f"`providers verify` cannot say whether {provider_id!r} works. Re-run this task "
            "on a machine with open egress.",
        )

    result = _run(VERIFY, repo, timeout=300)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return CheckResult("live", Outcome.FAIL, f"`providers verify` produced no JSON:\n{result.stdout[-3000:]}")

    entry = next((p for p in payload.get("providers", []) if p.get("provider_id") == provider_id), None)
    if entry is None:
        listed = [p.get("provider_id") for p in payload.get("providers", [])]
        return CheckResult(
            "live",
            Outcome.FAIL,
            f"{provider_id!r} is not covered by `providers verify`. Add it to "
            f"packages/providers/verification.py. Currently listed: {listed}",
        )

    outcome = entry.get("outcome")
    if outcome == "OK":
        return CheckResult("live", Outcome.PASS, json.dumps(entry, indent=2, sort_keys=True))
    # NO_DATA is correct fail-closed behaviour in general, but for a task whose
    # whole purpose is making a provider return real data it means not done.
    return CheckResult("live", Outcome.FAIL, json.dumps(entry, indent=2, sort_keys=True))


def evaluate(repo: Path, base: str, *, owns: list[str], provider_id: str | None,
             claimed_migration: str | None = None, allow_protected: bool = False) -> GateReport:
    checks = [
        check_ownership(repo, base, owns, allow_protected),
        check_migrations(repo, base, claimed_migration),
        check_suite(repo),
        check_constitution(repo),
    ]
    if provider_id:
        checks.append(check_live_provider(repo, provider_id))
    return GateReport(checks=checks)
