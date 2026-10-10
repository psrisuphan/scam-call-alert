# Model selection artifacts

This directory records the Plan 03/01 primary-only candidate comparison. Read [Plan 03/01](../../01%20-%20PLANs/03%20-%20MODEL%20DEVELOPMENT/01%20-%20HYPERPARAMETER%20TUNING%20AND%20MODEL%20SELECTION.md) before generating or executing experiments. The final test set is outside this workflow and must remain unopened.

## Current experiment order

1. Compare all approved candidates using primary-only training: 30 WangchanBERTa fits (two pooling methods × three learning rates × five folds), plus 45 fits for the other three candidates (three learning rates × five folds each), 75 total.
2. Select a candidate/configuration using the approved CV evidence and review process.
3. Run one matched five-fold primary + supplemental follow-up for that selected candidate/configuration only. Do not run supplemental comparisons for the unselected candidates.

The earlier selector and generated 120-row matrix encoded a superseded protocol. The tracked workflow has been migrated; do not use any old 120-row manifests or commands from prior local handoffs.

## Tracked files

- `search_space.json`: approved primary-only scope, fixed settings, candidate-specific WangchanBERTa pooling methods, and fit counts.
- `workflow.py`: safe manifest generation and import of a verified aggregate export. It does not train models, read test data, or import sample-level predictions. Unresolved launch gates keep unstarted rows blocked.
- `runtime.py`: focused metric aggregation and saved-fold membership validation used by the training runner. It contains no experiment-launch CLI.
- `experiment_manifest.csv`: 75 planned primary-only fit rows; completed fits keep their original run IDs and source artifact hashes.
- `cv_results.csv`: imported fold-level and aggregate validation metrics. It contains no transcript text or row-level predictions.
- `comparison_report.md`: interpretation and provenance of the currently imported results.
- `WANGCHANBERTA REPRODUCTION GUIDE.md`: completed-run settings, score provenance, reuse rules, and fresh-clone reproducibility limits.
- `tests/`: regression checks for the scope and import safeguards.

Training histories, sample-level predictions, checkpoints, and raw run directories stay in their approved persistent storage locations outside Git. Manifest artifact references point there. The verified export checksum and per-run artifact checksums preserve provenance; the committed metrics table is a compact, reproducible summary, not a substitute for those source artifacts.

## Safe workflow commands

From the repository root:

```bash
python3 "03 - MODEL DEVELOPMENT/selection/workflow.py" manifest
python3 "03 - MODEL DEVELOPMENT/selection/workflow.py" import-verified-export \
  --export /path/to/epoch3_cv_results.json
```

Manifest generation replaces the prior obsolete matrix with the approved 75 primary-only rows. Importing the existing WangchanBERTa export marks only its five completed rows and writes the score table; it does not execute or repeat training. The importer validates the exact configuration, run IDs, folds, status, marker conditions, and checksum formats and records the export checksum. It refuses unexpected settings or incomplete fold coverage.

The imported export contains per-fold metrics and artifact hashes, but not sample-level predictions. `cv_results.csv` therefore reports the verified fold metrics available in that export; full prediction-level re-aggregation remains possible from the persistent run artifacts and must retain their identities. Do not describe this imported summary as a complete row-level reconstruction.

The current WangchanBERTa result is development validation evidence for one configuration only. It is not a final selection and is not a test-set score. No new run is authorized by this import step.
