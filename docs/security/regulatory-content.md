# Regulatory Content Security

Regulatory sources are authoritative evidence, but retrieved text is untrusted input.

## Injection Boundary

Retrieved regulatory pages cannot:

- override GAIA system instructions;
- enable providers;
- change Cost Firewall settings;
- invoke tools;
- leak credentials;
- weaken tenant isolation;
- lower location privacy;
- create model-generated citations or source IDs.

Sentinel uses deterministic rule objects and stored provenance, not model memory, for movement status.

## Privacy

Remote regulatory tools receive only administrative and zone context needed for matching. Exact private coordinates are not sent when the egress policy denies them, and audit logs do not store unnecessary private farm coordinates.

## Freshness

Regulatory checks use `REGULATORY_CURRENT` cache policy. Stale content may be shown as context, but stale or unavailable currentness cannot support `ALLOWED`.

## Read-Only Scope

Phase 8 performs read-only decision support. It does not file permits, submit reports, contact regulators, pay fees, or perform calendar scheduling.

