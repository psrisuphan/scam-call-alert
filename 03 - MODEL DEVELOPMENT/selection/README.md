# Model selection artifacts

This directory records the Plan 03/01 primary-only candidate comparison. Read [Plan 03/01](../../01%20-%20PLANs/03%20-%20MODEL%20DEVELOPMENT/01%20-%20HYPERPARAMETER%20TUNING%20AND%20MODEL%20SELECTION.md) before generating or executing experiments. The final test set is outside this workflow and must remain unopened.

## Current approved reduction

The owner approved stopping comparative training on 2026-10-11: retain 45 completed fits, omit the remaining 30 fits and matched supplemental comparison, and select PhayaThaiBERT at LR 3e-5, common epoch 2, primary-only. See `experiment_protocol.md` and Plan 03/01's amendment. Selection completion and local compatibility remain unresolved; no final model has been trained or test set opened. The historical full-grid sequence below must not launch.

## Historical experiment order

1. Compare all approved candidates using primary-only training: 30 WangchanBERTa fits (two pooling methods × three learning rates × five folds), plus 45 fits for the other three candidates (three learning rates × five folds each), 75 total.
2. Select a candidate/configuration using the approved CV evidence and review process.
3. Run one matched five-fold primary + supplemental follow-up for that selected candidate/configuration only. Do not run supplemental comparisons for the unselected candidates.

The earlier selector and generated 120-row matrix encoded a superseded protocol. The tracked workflow has been migrated; do not use any old 120-row manifests or commands from prior local handoffs.

## Tracked files

- `search_space.json`: approved primary-only scope, fixed settings, candidate-specific WangchanBERTa pooling methods, and fit counts.
- `workflow.py`: original manifest generation and import of the initial verified aggregate export. It does not train models, read test data, or import sample-level predictions. Its current manifest generation/import behavior is unsafe for the now-completed rows; see the warning below and do not run it on current tracked files.
- `runtime.py`: focused metric aggregation and saved-fold membership validation used by the training runner. It contains no experiment-launch CLI.
- `experiment_manifest.csv`: 75 planned primary-only fit rows; completed fits keep their original run IDs and source artifact hashes.
- `cv_results.csv`: imported fold-level and aggregate validation metrics. It contains no transcript text or row-level predictions.
- `comparison_report.md`: interpretation and provenance of the currently imported results.
- `WANGCHANBERTA REPRODUCTION GUIDE.md`: completed-run settings, score provenance, reuse rules, and fresh-clone reproducibility limits.
- `tests/`: regression checks for the scope and import safeguards.

Shared Drive root: [Scam Call Alert project artifacts](https://drive.google.com/drive/folders/1SVPzz_CZw6eOnAEmzgzh2W6Y8M9Ne3lC?usp=sharing). Anonymous access to the root and its `model-development` listing was checked; access to individual nested artifacts was not checked. This link does not establish model redistribution permission or artifact integrity.

Training histories, sample-level predictions, checkpoints, and raw run directories stay in their approved persistent storage locations outside Git. Manifest artifact references point there. The original export checksum and per-run artifact hashes preserve provenance; for the 25 newer runs, config/history hashes were checked before metric import while prediction hashes are recorded but the prediction files were not independently downloaded and rehashed. The committed metrics table is a compact summary, not a substitute for source artifacts.

## Workflow command warning

The commands below document the original workflow implementation. **Do not run them against the current tracked manifest/results.** `manifest` regenerates all 75 rows and would erase completed run identities; `import-verified-export` only imports the original max-pooling LR 2e-5 export and rewrites the result CSV for that configuration. The completed configurations have been recorded from verified run evidence. Upgrade and review the importer before using it again on current data.

## Original workflow commands (historical)

From the repository root:

```bash
python3 "03 - MODEL DEVELOPMENT/selection/workflow.py" manifest
python3 "03 - MODEL DEVELOPMENT/selection/workflow.py" import-verified-export \
  --export /path/to/epoch3_cv_results.json
```

Manifest generation replaces the prior obsolete matrix with the approved 75 primary-only rows. Importing the existing WangchanBERTa export marks only its five completed rows and writes the score table; it does not execute or repeat training. The importer validates the exact configuration, run IDs, folds, status, marker conditions, and checksum formats and records the export checksum. It refuses unexpected settings or incomplete fold coverage.

For the initial configuration, the imported export contains fold metrics and artifact hashes but not sample-level predictions. For the other five configurations, metrics were imported from the verified run histories and their run summaries. The repository tables are aggregate development evidence, not a complete row-level reconstruction; full re-aggregation requires the persistent Drive artifacts and their recorded identities.

The six completed WangchanBERTa configurations and PhayaThaiBERT LR `3e-5` reference are development validation evidence, not final selection or test-set scores. HPLT/XLM-R monitoring observations remain separate from verified results. Full verification exports, predictions and weights stay in persistent Drive; the manifest retains their identities. The full results and provenance are in `comparison_report.md`, `cv_results.csv`, `experiment_manifest.csv`, and `WANGCHANBERTA REPRODUCTION GUIDE.md`. No new run is authorized by this import step.
