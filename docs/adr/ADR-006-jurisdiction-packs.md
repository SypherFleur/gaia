# ADR-006: Jurisdiction Packs

Status: Accepted

## Context

Plant movement, quarantine, pest alerts, and local agriculture guidance are jurisdiction-dependent and change over time.

## Decision

Jurisdiction-specific logic will be delivered through versioned jurisdiction packs with resolver, movement-rule, pest-alert, and source-list interfaces. Initial priority is U.S. federal plus Texas, then Florida and Singapore.

## Consequences

- Sentinel can combine origin, destination, federal, and quarantine-specific rules.
- Current source freshness is required for high-risk regulatory guidance.
- County differences alone cannot determine legal movement status.

