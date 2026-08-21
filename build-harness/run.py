#!/usr/bin/env python3
"""CLI for the GAIA build harness. Not part of GAIA -- see README.md."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gaia_build import gate  # noqa: E402
from gaia_build.dispatch import missing_env, run_task  # noqa: E402
from gaia_build.tasks import BY_KEY, TASKS  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


def cmd_doctor(_: argparse.Namespace) -> int:
    from agentfield.harness import harness_doctor

    print(f"repo:   {REPO}")
    print(f"egress: {'yes' if gate.has_egress() else 'NO -- provider tasks cannot be verified here'}\n")
    for health in asyncio.run(harness_doctor()):
        mark = "ok " if health.usable else "-- "
        print(f"{mark}{health.provider:12} {'usable' if health.usable else ', '.join(health.issues)}")
        if not health.usable:
            print(f"   install: {health.install_command}")
            if health.auth_env_vars:
                print(f"   auth:    {' or '.join(health.auth_env_vars)}")
    return 0


def cmd_list(_: argparse.Namespace) -> int:
    for task in TASKS:
        blocked = missing_env(task)
        status = f"BLOCKED (set {', '.join(blocked)})" if blocked else "ready"
        print(f"{task.key:22} ${task.budget_usd:>5.2f}  {status:32} {task.title}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    task = BY_KEY.get(args.key)
    if task is None:
        print(f"unknown task {args.key!r}. `run.py list` shows the queue.", file=sys.stderr)
        return 2

    blocked = missing_env(task)
    if blocked and not args.dry_run:
        # Starting would burn agent turns only to end at UNVERIFIABLE.
        print(f"{task.key} needs {', '.join(blocked)} in the environment. Not starting.", file=sys.stderr)
        return 2

    if task.budget_usd > args.max_spend:
        print(f"{task.key} caps at ${task.budget_usd:.2f}, above --max-spend ${args.max_spend:.2f}.", file=sys.stderr)
        return 2

    outcome = run_task(task, REPO, base=args.base, provider=args.provider,
                       attempts=args.attempts, dry_run=args.dry_run)
    if args.dry_run:
        return 0

    print(f"\n=== {task.key} ===")
    for attempt in outcome.attempts:
        print(f"\nattempt {attempt.number}  (${attempt.cost_usd:.2f})")
        for check in attempt.gate.checks:
            print(f"  {check.outcome.value:13} {check.name}")
            if check.outcome.value != "PASS":
                print("      " + check.detail.strip().replace("\n", "\n      ")[:1500])
        if attempt.report and attempt.report.unresolved:
            print("  agent reported unresolved:")
            for item in attempt.report.unresolved:
                print(f"      - {item}")

    print(f"\nspend: ${outcome.total_cost_usd:.2f}")
    if outcome.passed:
        print("GATE PASSED -- review the diff, then commit.")
        return 0
    if outcome.needs_human_verification:
        print("NEEDS HUMAN VERIFICATION -- a check could not be run here. Re-run on a machine with egress.")
        return 3
    print("GATE FAILED -- nothing here is ready to commit.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatch GAIA build tasks to coding agents and verify them.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Show provider availability and whether this machine can verify live work.")
    sub.add_parser("list", help="Show the task queue.")

    run_parser = sub.add_parser("run", help="Run one task through the agent-and-gate loop.")
    run_parser.add_argument("key")
    run_parser.add_argument("--provider", default="claude-code")
    run_parser.add_argument("--attempts", type=int, default=3)
    run_parser.add_argument("--base", default="HEAD", help="Git ref the diff is measured against.")
    run_parser.add_argument("--max-spend", type=float, default=5.0, help="Refuse tasks whose cap exceeds this.")
    run_parser.add_argument("--dry-run", action="store_true", help="Print the prompt and dispatch nothing.")

    args = parser.parse_args()
    return {"doctor": cmd_doctor, "list": cmd_list, "run": cmd_run}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
