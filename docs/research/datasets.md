# Datasets

Institutional datasets are not assumed public.

`Dataset` records owner, source, license, rights status, sensitivity, schema reference, version, and content hash. Sensitivity values are `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, and `RESTRICTED`.

`DatasetVersion` records immutable content and schema hashes. Historical `ResearchRun` records reference exact dataset-version IDs so a later upload cannot silently change an old experiment.

Dataset deletion is policy-controlled. Historical provenance may retain hashes and dataset-version references without exposing deleted private content.

