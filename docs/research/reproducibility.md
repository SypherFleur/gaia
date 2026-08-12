# Reproducibility

`ResearchRun` answers what task was executed. `ReproducibilityBundle` answers what exactly produced the result.

Bundles include:

- source records;
- provider versions;
- context snapshot;
- input hashes;
- model versions;
- prompt versions and hashes;
- tool versions;
- deterministic calculation versions;
- evidence records;
- output hashes;
- environment metadata.

Bundles do not include hidden chain-of-thought. They include reproducible inputs, tool evidence, versions, and outputs.

Historical runs keep their original prompt hashes, model versions, dataset-version IDs, and output hashes. Updating a prompt or dataset later must not mutate historical provenance.

