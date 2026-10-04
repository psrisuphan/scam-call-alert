# Prepared conversations

prepared.csv is the canonical six-column CSV. source_manifest.csv records versions, hashes, retrieval dates, licenses, and counts. record_audit.csv records each disposition and review with source locators. preparation_report.md records the Stage 00 snapshot before splitting.

Canonical data and preparation provenance remain unchanged. Acquisition, label mapping, integrity review, duplicate handling, and relationship review are complete.

## Frozen splits

splits/0 - train/dataset.csv is the training pool; splits/1 - test/dataset.csv is the final holdout. Both keep the canonical schema.

splits/split_assignments.csv records stable group_id, split, and cv_fold. Test records have blank cv_fold. splits/split_report.md records provenance, counts, algorithms, checks, and limitations.

Join by sample_id with one-to-one membership and matching source identity. Fold k validates on train records with cv_fold=k; train on the other folds. Primary-only filters only fold training to primary, never validation. Primary + supplemental uses both sources. All models reuse these assignments.

Canonical prepared.csv remains unchanged. Derived CSVs must not be edited independently. Preparation changes invalidate the split and require regenerated, verified artifacts.

Raw sources and prepared outputs are tracked for the private project handoff. See [the numbered script guide](../scripts/README.md) to verify or reproduce them. Do not redistribute the datasets publicly without confirming source rights.

Next: Plan 02. Use the training pool only for input-design inspection; do not inspect final test text to design preprocessing. No model-oriented preprocessing has occurred.
