# GAIA Build Harness

**This is not part of GAIA.** It is a development tool that *operates on* this
repository from the outside. It has its own dependencies, is excluded from
`pyproject.toml` and from the test suite, and nothing here ever ships in the
product. GAIA itself keeps zero required runtime dependencies.

It dispatches coding tasks to AI coding agents (Claude Code, Codex, Gemini,
OpenCode) through [AgentField](https://github.com/Agent-Field/agentfield)'s
standalone `HarnessRunner`, then **independently verifies** what they did.

## The one idea that matters

An agent reporting "tests pass" is a claim. This harness does not accept claims.

After every agent run, the dispatcher re-runs the verification gate itself and
believes only its own exit codes. If the gate fails, the real failure output is
fed back to the agent and it goes again. That loop — not the agent's own
judgement — is what "iterate until it works" means here.

This exists because the three worst bugs in GAIA's history all shipped with a
fully green test suite: a hardcoded county lookup table, a COMID returned as a
watershed name, and a WBD layer rule whose own unit test asserted the bug. A
deterministic offline suite cannot detect a wrong assumption about a remote
service. Only a live probe can.

## The gate

Every task must clear four checks, run by the dispatcher, not the agent:

| Check | Command | Meaning |
| --- | --- | --- |
| `ownership` | `git diff --name-only` vs the task's declared globs | The agent stayed in its lane |
| `tests` | `python3 -m unittest discover -s tests -p 'test_*.py'` | Nothing else broke |
| `constitution` | `python3 scripts/bootstrap/validate_constitution.py` | Financial invariants intact |
| `live` | `python3 -m apps.cli.gaia providers verify` | The provider actually returns real data |

Only `live` is evidence the work *works*. The rest are evidence it did no harm.

## PASS / FAIL / UNVERIFIABLE

Checks have three outcomes, not two. When the machine has no egress — a cloud
sandbox, a blocked proxy — `providers verify` cannot run, and that is reported
as **UNVERIFIABLE**, never as a pass.

A task with any UNVERIFIABLE check is not complete. It lands in the
needs-human-verification bucket and waits for a run on a machine with real
network. Silently treating "couldn't check" as "checked" is the exact failure
this whole harness exists to prevent.

**Run this on a machine with open egress.** In a sandbox that blocks outbound
HTTP, every provider task will correctly refuse to complete, and you will have
paid for agent turns to learn nothing.

## Setup

```bash
cd build-harness
python3 -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...                    # metered API billing, see Cost
python3 run.py doctor                              # which providers are usable
python3 run.py list                                # the task queue
python3 run.py run wbd-watershed-fix --dry-run     # print the prompt, dispatch nothing
python3 run.py run wbd-watershed-fix
```

## Cost

The harness bills to `ANTHROPIC_API_KEY` — metered API usage, not a Claude
subscription. This is **development tooling spend and is a different pot from
GAIA's financial constitution**, which governs the product's own runtime spend
and stays untouched ($0 automatic paid usage, $20 reserve intact).

That said, this pot has no natural ceiling, so the harness enforces one:

- every task carries `budget_usd`, passed to the provider as a hard cap
- the dispatcher tracks real spend from `HarnessResult.cost_usd`
- `--max-spend` caps a whole session and aborts before starting a task that
  could exceed it

Start with `--max-spend 5` until you have seen what a task actually costs.
