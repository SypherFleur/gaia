# Institution Data Egress

Organization policy centralizes institutional egress decisions:

- `allow_private_text_egress`
- `allow_private_image_egress`
- `allow_private_document_egress`
- `allow_exact_location_egress`
- `allow_research_data_egress`
- `allow_external_model_egress`

The Tool Gateway and Model Gateway consult organization policy before remote execution. Sovereign defaults disable private and external-model egress.

Uploaded institutional documents are untrusted content. Their text cannot alter system policy, enable tools, request secrets, or bypass organization policy.

Public source records may be shared where appropriate. Private datasets, annotations, notes, project collections, and organization-specific reviews remain tenant scoped.

