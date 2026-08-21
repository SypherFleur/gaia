"""What an agent must report back, and what the dispatcher independently checks.

The agent's report is a *claim*. `GateReport` is *evidence*: it is produced by
the dispatcher running commands itself. Where the two disagree, the gate wins.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field


class TaskReport(BaseModel):
    """Structured output required from the coding agent.

    Deliberately asks for evidence rather than assurance: which files, which
    commands, what the live probe actually printed. "Done" is not a field.
    """

    summary: str = Field(description="What you changed and why, in two or three sentences.")
    files_changed: list[str] = Field(default_factory=list, description="Repo-relative paths you created or modified.")
    commands_run: list[str] = Field(default_factory=list, description="Every verification command you ran, verbatim.")
    live_probe_output: str | None = Field(
        default=None,
        description=(
            "Verbatim output for this provider from `providers verify`, if the task "
            "touched a provider. Null if you could not run it — do not summarize or "
            "paraphrase it, and never state an outcome you did not observe."
        ),
    )
    captured_fixtures: list[str] = Field(
        default_factory=list,
        description="Paths of real captured API responses saved under tests/fixtures/, if any.",
    )
    unresolved: list[str] = Field(
        default_factory=list,
        description="Anything you could not verify or had to assume. Be specific; an empty list is a strong claim.",
    )


class Outcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    # The check could not be run at all — no egress, missing key, absent tool.
    # Never collapse this into PASS or FAIL: "couldn't check" is its own answer,
    # and treating it as either is how a broken provider ships looking green.
    UNVERIFIABLE = "UNVERIFIABLE"


@dataclass(slots=True)
class CheckResult:
    name: str
    outcome: Outcome
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.outcome is Outcome.PASS


@dataclass(slots=True)
class GateReport:
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Every check passed outright. UNVERIFIABLE never counts as success."""
        return bool(self.checks) and all(check.ok for check in self.checks)

    @property
    def failures(self) -> list[CheckResult]:
        return [c for c in self.checks if c.outcome is Outcome.FAIL]

    @property
    def unverifiable(self) -> list[CheckResult]:
        return [c for c in self.checks if c.outcome is Outcome.UNVERIFIABLE]

    def feedback(self) -> str:
        """The failure text handed back to the agent for its next attempt.

        Real command output, not a summary — a paraphrased failure is one the
        agent has to guess at.
        """
        lines: list[str] = []
        for check in self.failures:
            lines.append(f"### Check `{check.name}` FAILED\n{check.detail.strip()}")
        for check in self.unverifiable:
            lines.append(
                f"### Check `{check.name}` COULD NOT BE RUN\n{check.detail.strip()}\n"
                "Do not claim this passed. If it cannot be run here, say so in `unresolved`."
            )
        return "\n\n".join(lines)
