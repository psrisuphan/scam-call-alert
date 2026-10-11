# WangchanBERTa run reproduction and handoff

This guide records the six completed WangchanBERTa primary-only configurations (30 fold fits) so collaborators can reuse their identities, settings, and results without repeating them. Follow [Plan 03/00](../../01%20-%20PLANs/03%20-%20MODEL%20DEVELOPMENT/00%20-%20MODEL%20TRAINING.md), [Plan 03/01](../../01%20-%20PLANs/03%20-%20MODEL%20DEVELOPMENT/01%20-%20HYPERPARAMETER%20TUNING%20AND%20MODEL%20SELECTION.md), and the approved implementation notes first. This record documents completed work; it does not authorize a new run or a method change.

## Shared configuration identity

| Setting | Completed value |
|---|---|
| Candidate | WangchanBERTa, `airesearch/wangchanberta-base-att-spm-uncased` |
| Pinned checkpoint revision | `b81d38df6b4755dbedec0bfea863c9956cbb963e` |
| Training data condition | Primary only |
| Representation and training markers | Whole conversation, role marked |
| Input policy | Full-context windows; `wangchan_full_context_v1` |
| Content window / stride / overlap | 508 / 381 / 127 tokens; special tokens added per window |
| Pooling configurations | Class-wise max and arithmetic mean of window logits |
| Loss | One unweighted two-class cross-entropy per conversation after pooling |
| Learning rates | `2e-5`, `3e-5`, `5e-5` |
| Epoch target | 3 completed for all fits; no epoch-4 extension |
| Cross-validation | Saved folds 0–4, seed 67 |
| Effective batch size | 16 conversations |
| Optimizer | AdamW; approved Plan 03/01 settings |
| Warmup | 10% of planned optimizer updates, rounded up |
| Validation | Same saved fold records; paired role-free and role-marked inputs; threshold 0.5 |
| Runtime | Google Colab T4, FP16 |

Each fold was initialized from the pinned pretrained checkpoint with fresh classifier/optimizer state. Full untruncated conversation text was joined to Plan 02 data by sample ID and verified; chunks were not treated as independent samples. Training used role-marked inputs. Validation covered the combined primary and supplemental validation records; role-free is the model-selection condition and role-marked is diagnostic. The held-out test partition was not used.

## Completed results to reuse

All values below are epoch-3 fold means ± sample SD (five folds). Use [`cv_results.csv`](cv_results.csv) for the full epoch-by-epoch metrics for both marker conditions and [`comparison_report.md`](comparison_report.md) for interpretation.

| Pooling | LR | Role-free Scam F1 | Role-marked Scam F1 |
|---|---:|---:|---:|
| Max | 2e-5 | 0.960559 ± 0.005358 | 0.972219 ± 0.008171 |
| Mean | 2e-5 | 0.951139 ± 0.013833 | 0.965792 ± 0.008262 |
| Max | 3e-5 | 0.961599 ± 0.008594 | 0.971681 ± 0.005055 |
| Mean | 3e-5 | 0.954449 ± 0.009765 | 0.964989 ± 0.006088 |
| Max | 5e-5 | 0.962344 ± 0.013827 | 0.969942 ± 0.010419 |
| Mean | 5e-5 | 0.954162 ± 0.008099 | 0.965638 ± 0.008470 |

These remain one candidate's CV evidence, not final test performance or a selection among the four candidates. The best mean and lowest SD are not the same configuration; review both according to the approved selection guidance after the other candidates are available.

## Evidence locations and identity

The manifest row for each fold is authoritative for its run ID, persistent artifact location, and SHA-256 values for run config, history, and predictions. The initial max/LR `2e-5` configuration is under:

```text
scam-call-alert/model-development/comparison-slices/
  wangchanberta-fullcontext-20261010-pilot1/repairs/overflow-fix-20261010-v1/
```

The other five configurations are under:

```text
scam-call-alert/model-development/comparison-slices/
  wangchan-primary-remaining-20261010/runs/
```

Use the exact per-fold folder names in `experiment_manifest.csv`; check stored files against their recorded hashes before reuse. Keep sample-level predictions and model weights in approved Drive storage, not Git. The original configuration's source export SHA-256 is `0596c22980f8cadc4ac43031a15d88cd098a0e871d2a8156ff230404c6bf10c3`; the executed trainer source SHA-256 was `49753b7d6c1a9465c4e5434fbb43a6da9e0c152f82136f2244a66eb9578fcb24`. The newer 25-run group has per-run config/history/prediction hash values in the manifest and summary records; config and history files were checksum-verified before import. Prediction hash values were retained from summaries but the prediction files were not independently downloaded and rehashed for this documentation pass. These runs did not use the original aggregate export.

## Do not rerun these configurations

All 30 WangchanBERTa folds are complete and represented in the approved 75-fit primary-only matrix. Reuse their existing run IDs and evidence. Do not generate new run IDs to replace or improve these scores. If an artifact is missing or fails checksum verification, report the specific missing evidence and recover it from the listed Drive location; do not silently rerun or overwrite it.

A new stochastic execution may not reproduce identical weights or scores even with the same nominal seed and settings. The original run artifacts are the authority for these results. The other three candidate model comparisons are still pending; do not select the overall candidate from WangchanBERTa-only results.

## Reproduction boundaries

The reusable training runner, full-context implementation, input loader, selection aggregation dependency, run template, and pinned tokenizer dependencies are in the implementation handoff. A fresh clone can prepare a new, separately approved configuration only after the required Plan 03 gates are resolved. Record its code commit and file hashes with that new run.

Run configs, environment records, histories, sample-level predictions, checkpoints, and source archives remain in approved persistent Drive storage. They are not duplicated in Git. No bit-for-bit replay is promised. For any separately authorized future execution, retain the approved config, checkpoint/input/fold identities, runtime package/device record, random seeds, and new run artifacts; report runtime nondeterminism as appropriate.
