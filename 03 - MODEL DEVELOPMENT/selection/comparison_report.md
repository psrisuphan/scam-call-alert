# Primary-only model comparison: current evidence

## Scope and status

The approved protocol compares the four candidates with primary-only training: 30 WangchanBERTa fits (max/mean pooling × three learning rates × five folds) plus 45 fits for the other candidates. One selected candidate/configuration may later receive a matched five-fold primary + supplemental follow-up. No test-set data was used.

The current evidence covers **one of 15 configurations**: WangchanBERTa, 2e-5 learning rate, class-wise max pooling, seed 67, effective batch 16, three epochs, and folds 0–4. It is an early result, not cross-candidate selection or final-test performance. The existing five folds were imported by run identity; no training was repeated.

## Epoch-3 validation scores

Scam is the positive class. Each fold evaluates both marker conditions on the combined validation records. SD is the sample standard deviation across five fold scores (denominator 4).

| Validation input | Scam precision (mean) | Scam recall (mean) | Scam F1 (mean ± sample SD) | Macro-F1 (mean) | Accuracy (mean) | Validation loss (mean) |
|---|---:|---:|---:|---:|---:|---:|
| Role-free (selection condition) | 0.933601 | 0.989156 | **0.960559 ± 0.005358** | 0.961324 | 0.961340 | 0.074191 |
| Role-marked (diagnostic) | 0.964572 | 0.980147 | 0.972219 ± 0.008171 | 0.973324 | 0.973372 | 0.056321 |

The exported aggregate trajectory across the three completed epochs was:

| Epoch | Role-free Scam F1 (mean ± sample SD) | Role-free train loss | Role-free validation loss | Role-marked Scam F1 (mean ± sample SD) | Role-marked validation loss |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.962286 ± 0.011756 | 0.356845 | 0.095214 | 0.970477 ± 0.014520 | 0.076315 |
| 2 | 0.962402 ± 0.009112 | 0.006811 | 0.072650 | 0.972474 ± 0.008387 | 0.053534 |
| 3 | 0.960559 ± 0.005358 | 0.000999 | 0.074191 | 0.972219 ± 0.008171 | 0.056321 |

| Marker condition | Fold Scam F1 scores (folds 0–4) |
|---|---|
| Role-free | 0.951965, 0.964912, 0.965217, 0.960699, 0.960000 |
| Role-marked | 0.959276, 0.977578, 0.977974, 0.968889, 0.977376 |

Fold validation counts were 233, 233, 233, 233, and 232 (total 1,164). Fold class counts were 122 Not Scam and 111 Scam for folds 0–3; fold 4 contained 122 Not Scam and 110 Scam. `cv_results.csv` includes the exported epoch aggregates for epochs 1–3 and fold-level metrics at epoch 3. The underlying export has no per-fold epoch 1–2 or sample rows, so the report does not claim a regenerated prediction-level aggregate.

## Provenance and interpretation

The importer validated the export status, settings, five fold IDs, per-run run-config/history/prediction SHA-256 values, and three completed epochs. The export SHA-256 is `0596c22980f8cadc4ac43031a15d88cd098a0e871d2a8156ff230404c6bf10c3`. The run artifacts and raw sample predictions remain in persistent Drive at the artifact locations referenced in `experiment_manifest.csv`; they are not committed to Git. `cv_results.csv` is the compact per-fold and aggregate metric table.

These are development CV results from the validation folds, not final-test estimates. The model-selection condition is role-free whole-conversation Scam F1; marked-condition scores are diagnostic and do not override it. Do not infer generalization beyond this dataset or use these results as a final model choice. Continue the remaining approved primary-only configurations under the current gates, reusing the five completed fits without rerunning them.
