# Movement Decisions

`MovementRequest` captures the user's movement facts:

- origin and destination location or country;
- planned date;
- species and optional cultivar;
- plant part;
- live-plant and soil-attached flags;
- growing media, quantity, purpose, and personal/commercial context.

If required facts are missing, Sentinel returns `UNRESOLVED` instead of guessing.

## Output

`MovementDecision` contains:

- `status`: `ALLOWED`, `CONDITIONAL`, `RESTRICTED`, or `UNRESOLVED`;
- applicable jurisdictions and active zones;
- applicable rules;
- conditions, permits, treatments, inspection, and reporting context;
- unresolved questions;
- conflicts;
- freshness;
- source record IDs;
- authority statement.

## Precedence

Sentinel combines all applicable current rules. The most restrictive applicable status controls:

```text
ALLOWED < CONDITIONAL < RESTRICTED < UNRESOLVED
```

Examples:

- No matching current rule and all required sources are current: `ALLOWED`.
- Federal certificate plus state treatment requirement: `CONDITIONAL`.
- Quarantine live-tree movement restriction: `RESTRICTED`.
- stale provider, unavailable current source, conflict, missing species, or unknown destination: `UNRESOLVED`.

## Exceptions

Exceptions remain attached to rules and are evaluated before a rule is applied. A rule that loses exceptions is unsafe because it can over-restrict or over-permit movement.

## Wording

GAIA must not say it legally approves a shipment. User-facing text should name the authorities and retrieval time, for example:

```text
Based on current Texas Department of Agriculture and USDA APHIS sources retrieved at [time], this movement appears conditional on...
GAIA is not the legal authority.
```

## Escalation

Vision suspected regulated pest hypotheses and Genesys legal shipment questions route to Sentinel. Vision does not declare a regulated disease, and Genesys accession availability never becomes legal movement permission.

