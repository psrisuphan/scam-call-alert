# WangchanBERTa run reproduction and handoff

This guide records the completed WangchanBERTa primary-only configuration so a collaborator can identify its method and evidence without repeating it. Follow [Plan 03/00](../../01%20-%20PLANs/03%20-%20MODEL%20DEVELOPMENT/00%20-%20MODEL%20TRAINING.md), [Plan 03/01](../../01%20-%20PLANs/03%20-%20MODEL%20DEVELOPMENT/01%20-%20HYPERPARAMETER%20TUNING%20AND%20MODEL%20SELECTION.md), and the approved implementation notes first. This is documentation, not authorization to launch a run or change an approved method.

## Completed configuration identity

| Setting | Completed value |
|---|---|
| Candidate | WangchanBERTa, `airesearch/wangchanberta-base-att-spm-uncased` |
| Pinned checkpoint revision | `b81d38df6b4755dbedec0bfea863c9956cbb963e` |
| Training data condition | Primary only |
| Representation and training markers | Whole conversation, role marked |
| Input policy | Full-context windows; `wangchan_full_context_v1` |
| Content window / stride / overlap | 508 / 381 / 127 tokens; special tokens added per window |
| Conversation aggregation | Class-wise max pooling of window logits |
| Loss | One unweighted two-class cross-entropy per conversation after pooling |
| Learning rate | `2e-5` |
| Epoch target completed | 3; no epoch-4 extension |
| Cross-validation | Saved folds 0–4, seed 67 |
| Effective batch size | 16 conversations |
| Optimizer | AdamW; approved Plan 03/01 settings |
| Warmup | 10% of planned optimizer updates, rounded up |
| Validation | Same saved fold records, evaluated role-free and role-marked; threshold 0.5 |
| Runtime | Google Colab T4, FP16 |

Each fold was initialized from the pinned pretrained checkpoint with fresh classifier/optimizer state. Conversation IDs and saved fold membership were retained; chunks were not treated as independent samples. Training used full untruncated prepared conversations from Plan 02, joined and verified by sample ID. The held-out test partition was not used.

## Results to reuse

Use the original scores in [`cv_results.csv`](cv_results.csv) and their interpretation in [`comparison_report.md`](comparison_report.md). The epoch-3 role-free Scam F1 scores for folds 0–4 are `0.951965`, `0.964912`, `0.965217`, `0.960699`, and `0.960000`; mean and sample SD are `0.960559 ± 0.005358`. The role-marked diagnostic is `0.972219 ± 0.008171`. Aggregate role-free metrics for epochs 1–3 are also in the CSV. They are development-validation results for this configuration, not test-set scores or a final candidate selection.

The manifest row for each fold is authoritative for its run ID, persistent artifact location, and SHA-256 values for run config, history, predictions, and source export. The source export SHA-256 is `0596c22980f8cadc4ac43031a15d88cd098a0e871d2a8156ff230404c6bf10c3`. The source export and per-run files are in the project Drive folder:

```text
scam-call-alert/model-development/comparison-slices/
  wangchanberta-fullcontext-20261010-pilot1/repairs/overflow-fix-20261010-v1/
```

Its aggregate export is under `evidence/results-epoch3/epoch3_cv_results.json`; per-run configs, histories, and sample-level predictions are in the `runs/` subfolder identified in `experiment_manifest.csv`. Check each stored file against the manifest hash before using it. Keep these sample-level artifacts and model weights in approved Drive storage, not Git.

## Do not rerun this configuration

The five completed folds are already included in the 75-fit primary-only comparison. Reuse them by their original run IDs. Do not regenerate them with a new run ID to replace or improve their scores. If an artifact is missing or fails checksum verification, report the specific missing evidence and recover it from the listed Drive location; do not silently rerun or overwrite it.

To reproduce the reported score, recompute or inspect the verified original predictions and export. Training the same configuration again is a new stochastic execution and may not produce numerically identical weights or scores, even with the same nominal seed and settings. Do not present a rerun as the source of the committed result.

## Reproduction boundaries

The reusable training runner, full-context implementation, input loader, selection aggregation dependency, run template, pinned tokenizer dependencies, and regression tests are included in the implementation handoff. A fresh clone can prepare and run a **new, separately approved** configuration after the required Plan 03 gates are resolved. It must use a checkout whose commit and file hashes are recorded with that run.

The original run's complete per-fold configs, environments, histories, sample-level predictions, checkpoints, and source archive remain in the approved Drive folder above. They are not duplicated in Git. Use the manifest's original run IDs and SHA-256 values to retrieve and verify those exact files. The source archive's SHA-256 is `0596c22980f8cadc4ac43031a15d88cd098a0e871d2a8156ff230404c6bf10c3`; the executed trainer source SHA-256 was `49753b7d6c1a9465c4e5434fbb43a6da9e0c152f82136f2244a66eb9578fcb24`. Do not substitute a new run for missing original evidence or present a rerun as the source of the committed scores.

The historical Colab notebooks described a fixed-prefix diagnostic or a superseded 60-fit matrix; neither is an active workflow. Use the Python training entry point and current manifest/import workflow documented in the training and selection READMEs. A Colab runtime must preserve its installed PyTorch and record the actual package/device versions. Git source plus the Drive run records make the process auditable; they do not promise bit-for-bit reconstruction of model weights or scores.

No exact bit-for-bit reproducibility claim is made. For a repeated execution, retain the approved config, pinned source/checkpoint/input identities, fold assignments, runtime package/device record, random seeds, and new run artifacts; compare it as a separate run and document any runtime nondeterminism.
