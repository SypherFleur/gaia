# Research Runs

A `ResearchProject` groups institutional work around a question or protocol. It is not university-specific; it can represent extension, NGO, government, grower, or internal analysis work.

A `ResearchRun` records:

- project;
- initiating user;
- task/query;
- input bundle hash;
- context bundle ID;
- model run IDs;
- tool run IDs;
- evidence synthesis IDs;
- guidance plan IDs;
- dataset-version IDs;
- output bundle hash;
- status.

Statuses are `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`, and `REVIEW_REQUIRED`. Current execution may be synchronous; the status model exists for reproducibility and auditability.

Human review is stored separately and never rewrites the original run output.

