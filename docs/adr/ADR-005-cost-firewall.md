# ADR-005: Cost Firewall

Status: Accepted

## Context

Protocol Two sets an initial total cash budget of USD 20, a development spend target of USD 0, and a committed monthly infrastructure target of USD 0.

## Decision

All providers and model/tool calls must be governed by cost policy. Automatic paid model usage, paid API usage, infrastructure upgrades, storage upgrades, and overage billing are disabled by default.

## Consequences

- Provider failure or quota exhaustion must degrade gracefully rather than spend money.
- Tests must prove paid providers cannot execute when disabled.
- Manual paid usage requires future explicit approval governance.

