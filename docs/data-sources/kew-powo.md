# Kew POWO / WCVP

Purpose: first-class global Botanist source family for plant-name and global taxonomy context from Royal Botanic Gardens, Kew resources such as Plants of the World Online and WCVP.

Runtime status: documented-only by default. GAIA includes a read-only adapter boundary and provider registry record, but normal alpha does not fabricate Kew data when the public endpoint is unavailable or access terms need review.

Provider id: `kew-powo`

Billing: free/public-web class only. No paid API, overage path, telemetry, storage service, or credentialed account is enabled.

Terms and rights: Kew attribution and no-implied-endorsement constraints are preserved in provider metadata and source provenance. Dataset-specific licenses and traffic limits must be reviewed before enabling live use.

GAIA semantics:

- Kew global taxonomy is not local cultivation suitability.
- Kew output does not imply Kew endorsement of GAIA results.
- Kew calls must flow through Botanist and Tool Gateway.
- Model training on Kew data is not enabled.

Implementation boundary:

- adapter: `packages.botany.live_adapters.KewPOWOApiAdapter`
- tool: `packages.botany.tools.KewPOWOTaxonomyTool`
- registry provider: `kew-powo`
- default mode: `disabled`

