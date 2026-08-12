# Season Confidence

Season uses categorical confidence:

```text
HIGH
MODERATE
LOW
PROVISIONAL
```

No fake numerical precision is generated.

## Factors

Confidence reflects:

- crop biology known;
- cultivar known;
- location precision;
- climate/environment context availability;
- forecast horizon;
- soil and moisture evidence semantics;
- regulatory status;
- user constraints.

Sentinel `RESTRICTED` or `UNRESOLVED` sourcing constraints make affected plans provisional. Unknown cultivar lowers confidence but does not cause GAIA to invent cultivar-specific thresholds.

## Evidence Semantics

SSURGO and regional/model-derived moisture context must not become exact field moisture. Season recommends measurement when actual sensor/user-measured data is absent.

