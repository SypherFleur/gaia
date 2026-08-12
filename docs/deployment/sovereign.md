# Sovereign Deployment

GAIA Sovereign is a deployment profile using the same codebase.

Suggested configuration:

```text
GAIA_DEPLOYMENT_MODE=sovereign
GAIA_ALLOW_EXTERNAL_MODEL_EGRESS=false
GAIA_ALLOW_PRIVATE_DOCUMENT_EGRESS=false
GAIA_ALLOW_PRIVATE_IMAGE_EGRESS=false
GAIA_TELEMETRY_MODE=disabled
```

Sovereign defaults:

- private text/image/document egress disabled;
- exact-location egress disabled;
- research-data egress disabled;
- external model egress disabled;
- telemetry disabled;
- local model providers preferred/required;
- remote providers can be disabled without preventing core boot.

Air-gapped readiness is architectural in Phase 11, not a polished installer. Future offline deployments should preload models, migrations, source snapshots, jurisdiction packs, fixture/local providers, and any approved institutional datasets.

