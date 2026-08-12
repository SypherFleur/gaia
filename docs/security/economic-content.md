# Economic Content Security

Economic reports are untrusted retrieved content. Provider text cannot:

- invoke tools;
- alter system, Sentinel, or Cost Firewall policy;
- reveal credentials;
- override source metadata;
- create trusted source IDs;
- introduce model-generated prices or production values.

Mercator sends public administrative geography to economic providers where possible. Exact private coordinates are not required for NASS/AMS fixture-backed Phase 10 economics and are not included in provider payloads.

Public economic statistics may be reused, but assembled `MercatorContext` records are tenant/workspace scoped because they can be linked to private crop plans, workspaces, or annotations.

No commercial market-data provider can run automatically in Phase 10. Any paid source must be documented for future review and remain disabled.

