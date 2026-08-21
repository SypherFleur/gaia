"""Dispatch a task to a coding agent, then verify it independently and retry.

The loop is: run the agent -> run the gate ourselves -> if the gate failed,
hand the agent the real failure output and go again. The agent's own account of
its work never advances the loop.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from agentfield.harness import HarnessRunner

from . import gate
from .contract import GateReport, TaskReport
from .tasks import Task

SYSTEM_PROMPT = """\
You are working inside the GAIA repository.

Read CLAUDE.md and AGENTS.md before you touch anything. AGENTS.md holds nine
hard invariants, the provider truth table, and the known-bug list. They are not
advisory.

The rules that matter most for the work you are about to do:

- A hardcoded value presented as computed output is a bug, not a placeholder.
  If real behaviour cannot be built, return an explicit UNAVAILABLE/UNRESOLVED
  status. Never a plausible-looking constant.
- An identifier is not a name. Returning a code where a name is expected is a
  wrong answer wearing the costume of a right one.
- Never write a test fixture by hand for a live adapter. Capture the real
  response, save it under tests/fixtures/ with its URL and capture date, and
  test against that. A hand-written fixture tests your assumption, not the
  service.
- Every external provider call goes through packages/tools/gateway.py::execute().
- Never enable a paid API or model. allow_automatic_paid_* stays False.
- Migrations are append-only. Never edit an existing one.
- Do not modify files outside the scope you were given. Shared files
  (the Tool Gateway, the repository layer, the runtime wiring, AGENTS.md) are
  owned by a human and edits to them will be rejected.

Your work is checked by commands, not by your summary of it. Claiming a check
passed when you did not run it is the worst outcome available to you -- worse
than failing, because it is the failure mode this entire pipeline exists to
catch. If you could not verify something, say so in `unresolved`.
"""

GATE_INSTRUCTIONS = """\
## Definition of done

Run all of these yourself before you report. The dispatcher will run them again
independently and believe only its own results:

    python3 -m unittest discover -s tests -p 'test_*.py'
    python3 scripts/bootstrap/validate_constitution.py
{provider_line}
Report `live_probe_output` verbatim. If you could not run the probe, set it to
null and explain why in `unresolved`. Do not paraphrase an outcome you did not
observe.
"""


@dataclass(slots=True)
class Attempt:
    number: int
    report: TaskReport | None
    gate: GateReport
    cost_usd: float


@dataclass(slots=True)
class TaskOutcome:
    task: Task
    attempts: list[Attempt]

    @property
    def passed(self) -> bool:
        return bool(self.attempts) and self.attempts[-1].gate.passed

    @property
    def needs_human_verification(self) -> bool:
        return bool(self.attempts) and bool(self.attempts[-1].gate.unverifiable)

    @property
    def total_cost_usd(self) -> float:
        return sum(attempt.cost_usd for attempt in self.attempts)


def build_prompt(task: Task, feedback: str | None) -> str:
    provider_line = (
        f"    python3 -m apps.cli.gaia providers verify   # {task.provider_id} must report OK\n"
        if task.provider_id
        else ""
    )
    sections = [
        f"# Task: {task.title}",
        task.brief.strip(),
        f"## Files you may modify\n" + "\n".join(f"- `{pattern}`" for pattern in task.owns),
        GATE_INSTRUCTIONS.format(provider_line=provider_line),
    ]
    if feedback:
        sections.append(
            "## Your previous attempt did not pass the gate\n\n"
            "This is the verbatim output. Fix the cause; do not work around the check.\n\n"
            + feedback
        )
    return "\n\n".join(sections)


def missing_env(task: Task) -> list[str]:
    return [name for name in task.requires_env if not os.environ.get(name)]


def run_task(
    task: Task,
    repo: Path,
    *,
    base: str,
    provider: str = "claude-code",
    attempts: int = 3,
    dry_run: bool = False,
) -> TaskOutcome:
    runner = HarnessRunner()
    results: list[Attempt] = []
    feedback: str | None = None

    for number in range(1, attempts + 1):
        prompt = build_prompt(task, feedback)
        if dry_run:
            print(prompt)
            return TaskOutcome(task=task, attempts=[])

        result = runner.run(
            prompt,
            schema=TaskReport,
            provider=provider,
            project_dir=str(repo),
            cwd=str(repo),
            max_turns=task.max_turns,
            max_budget_usd=task.budget_usd,
            system_prompt=SYSTEM_PROMPT,
        )

        report = result.parsed if not result.is_error else None
        verdict = gate.evaluate(
            repo,
            base,
            owns=task.owns,
            provider_id=task.provider_id,
            claimed_migration=task.claimed_migration,
            allow_protected=task.allow_protected,
        )
        results.append(Attempt(number=number, report=report, gate=verdict, cost_usd=result.cost_usd or 0.0))

        if verdict.passed:
            break
        if verdict.unverifiable and not verdict.failures:
            # Nothing the agent can do about a machine with no egress. Stop
            # spending turns and hand it to a human rather than looping.
            break
        feedback = verdict.feedback()

    return TaskOutcome(task=task, attempts=results)
