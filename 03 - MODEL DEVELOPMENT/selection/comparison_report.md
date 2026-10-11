# Primary-only model comparison: current evidence

## Scope and status

The approved primary-only comparison contains 75 fold fits: six WangchanBERTa configurations (two pooling methods × three learning rates × five folds) and 45 fits for the other three candidates. The six WangchanBERTa configurations are now complete: 30/30 fold fits finished three epochs. PhayaThaiBERT at LR `3e-5` has also completed and passed independent five-fold verification (35 verified completed fits in total). The other 40 fits are not yet fully verified: HPLT at LR `3e-5` was observed complete across five folds, and XLM-R at that LR was observed complete for fold 0 before runtime loss; their independent verification remains pending. XLM-R fold 1 was last observed running. The remaining learning-rate configurations have not been executed. After the four-candidate comparison and reviewed candidate selection, one matched five-fold primary + supplemental follow-up may be run for that candidate/configuration. The held-out test set has not been opened.

These results are development cross-validation evidence for WangchanBERTa and one PhayaThaiBERT reference configuration. Role-free validation Scam F1 is the selection metric; role-marked validation is diagnostic. Scores below summarize fold-level metrics as mean ± sample SD (denominator 4), unless marked as a single mean. They do not select the final candidate before the other models are compared and are not final-test performance.

## PhayaThaiBERT reference configuration (2026-10-11)

The primary-only LR `3e-5` configuration completed saved folds 0–4 at three epochs, seed 67, effective batch 16, microbatch 4 × accumulation 4, T4 FP16, and the existing Plan 02 510-token fixed-prefix policy. AdamW settings and threshold 0.5 are unchanged. Warmup is `ceil(0.10 * ceil(fold_train_count / 16) * 3)`, 16 updates in each fold. Validation includes both sources and both marker conditions.

| Common epoch | Role-free Scam F1 mean ± sample SD | Role-marked diagnostic F1 mean ± sample SD |
|---|---:|---:|
| 1 | 0.955559 ± 0.024674 | 0.965340 ± 0.031972 |
| 2 | 0.976796 ± 0.012884 | 0.979067 ± 0.013556 |
| 3 | 0.976003 ± 0.011300 | 0.976410 ± 0.013856 |

Epoch 2 has the highest observed role-free mean for this configuration. It is not a final duration/configuration selection: the other learning rates and candidates remain incomplete. Compare common epochs, not each fold's individually best epoch. PhayaThaiBERT's fixed-prefix input differs from WangchanBERTa's approved full-context pooling; this comparison does not isolate the effect of that difference or establish statistical superiority.

[The retained verification export](phaya_primary_reference_verification.json) contains fold/epoch metrics, sample counts, run IDs, artifact hashes, snapshot hashes, timing, and overflow-retry counts; it contains no sample IDs, transcript text, or sample-level predictions. Its SHA-256 is `5660ae87e27b0927b8ac2df4e434701a27e7a791ca4f52d5cf473c9cd633a8cc`. Remote verification recomputed metrics from predictions, checked exact validation membership and finite normalized probabilities, and verified the new snapshots; fold 0 reuses its previously verified snapshots. Five-fold sample SD uses denominator 4. All 1,164 validation conversations are covered once per marker condition at each epoch.

The five successful fits took 97.16 minutes in total; folds 1–4 took 83.47 minutes. Individual durations ranged from 11.95 to 31.56 minutes. This excludes the additional independent verification pass and is not a measured runtime for other candidates. Folds 1 and 2 each recorded one FP16 overflow replay; all fits completed. A preceding fold-0 attempt without terminal completion evidence remains preserved and is not scored.

Persistent roots under `scam-call-alert/model-development/comparison-slices/`:
- Fold 0: `remaining-primary-first-fit-20261011T044510Z`.
- Folds 1–4: `phaya-primary-reference-remaining-20261011T051518Z`; five-fold verification is in `evidence/phaya-primary-lr3e-05-fivefold-verification.json`.

The CSV adds all 30 fold/epoch/marker metric rows and six aggregate rows. Training-loss fields are blank because the retained export does not contain them; retrieve verified histories before filling them. Source-specific metrics, confusion counts, undefined-metric flags, and inference timing still need their owning artifacts. Nothing was filled from assumed values.

## HPLT/XLM-R execution observations and interruption

The owner authorized a bounded LR `3e-5` reference queue for HPLT then XLM-R, five folds each, using their existing 512-token prefixes and the same approved training settings. Artifacts were written directly to `comparison-slices/other-models-primary-reference-20261011T074624Z`.

Monitoring observed HPLT folds 0–4 and XLM-R fold 0 with completed terminal summaries. XLM-R fold 1 was last observed in epoch 3 at optimizer update 129; folds 2–4 were not observed started. The session then disappeared. These observations are recorded separately from verified metrics; inspect preserved summaries, predictions and snapshot hashes before scoring them or deciding which fits must be rerun. No HPLT/XLM-R scores have been imported.

A replacement T4 request repeatedly returned HTTP 503, including six spaced retries over 30 minutes. CPU allocation succeeded in a diagnostic availability probe, then was released. The response does not establish a cooldown, rate limit, regional capacity issue, or the reason the original runtime disappeared. No hardware/precision substitution or new fit was launched. Zero compute units alone is not proof of failed allocation: earlier T4 sessions worked with that balance.

The full comparison, combined downstream feasibility review, local inference/STT preflight, missing reporting breakdowns, supplemental follow-up, and final evaluation remain unfinished. Do not resume a fit interrupted before its target; preserve evidence and restart from the pinned pretrained checkpoint with a new run ID after checking its actual saved terminal state.

## WangchanBERTa completed configurations: epoch 3

All fits used primary-only role-marked whole-conversation training, saved folds 0–4, seed 67, effective batch 16 conversations, three epochs, WangchanBERTa full-context windows (508 content tokens, stride 381, overlap 127), the listed pooling method, one unweighted conversation-level cross-entropy loss, and paired role-free/role-marked whole-conversation validation at threshold 0.5. Runtime was Colab Tesla T4 with FP16. Each validation fold contains the combined validation population from both sources, even though training used primary data only.

| Configuration | Role-free Scam F1 (mean ± SD) | Role-marked Scam F1 (mean ± SD) | Role-free precision / recall | Role-free Macro-F1 | Role-free accuracy | Role-free validation loss |
|---|---:|---:|---:|---:|---:|---:|
| Max, LR 2e-5 | 0.960559 ± 0.005358 | 0.972219 ± 0.008171 | 0.933601 / 0.989156 | 0.961324 | 0.961340 | 0.074191 |
| Mean, LR 2e-5 | 0.951139 ± 0.013833 | 0.965792 ± 0.008262 | 0.908517 / 0.998198 | 0.951033 | 0.951040 | 0.098871 |
| Max, LR 3e-5 | 0.961599 ± 0.008594 | 0.971681 ± 0.005055 | 0.932402 / 0.992776 | 0.962194 | 0.962206 | 0.084124 |
| Mean, LR 3e-5 | 0.954449 ± 0.009765 | 0.964989 ± 0.006088 | 0.913000 / 1.000000 | 0.954472 | 0.954477 | 0.114466 |
| Max, LR 5e-5 | **0.962344 ± 0.013827** | 0.969942 ± 0.010419 | 0.936988 / 0.989189 | 0.963060 | 0.963075 | 0.097962 |
| Mean, LR 5e-5 | 0.954162 ± 0.008099 | 0.965638 ± 0.008470 | 0.916932 / 0.994595 | 0.954473 | 0.954477 | 0.128064 |

Max pooling at LR 5e-5 has the highest epoch-3 role-free Scam F1 mean among these six WangchanBERTa settings; max pooling at LR 2e-5 has the lowest observed role-free Scam F1 SD. These are descriptive comparisons within this candidate, not a final selection: the approved review considers focus-metric performance together with fold variability, and the other three candidates have not been compared yet. Role-marked scores are diagnostic and do not determine selection.

### Role-free Scam F1 by epoch

This records the CV trajectory for every configuration, preserving the epoch-1 and epoch-2 results as well as the common epoch-3 endpoint. Each cell is mean ± sample SD across the five validation folds.

| Configuration | Epoch 1 | Epoch 2 | Epoch 3 |
|---|---:|---:|---:|
| Max, LR 2e-5 | 0.962286 ± 0.011756 | 0.962402 ± 0.009112 | 0.960559 ± 0.005358 |
| Mean, LR 2e-5 | 0.963719 ± 0.017411 | 0.951871 ± 0.011702 | 0.951139 ± 0.013833 |
| Max, LR 3e-5 | 0.965391 ± 0.010423 | 0.962522 ± 0.011987 | 0.961599 ± 0.008594 |
| Mean, LR 3e-5 | 0.960739 ± 0.011521 | 0.954277 ± 0.014013 | 0.954449 ± 0.009765 |
| Max, LR 5e-5 | 0.963573 ± 0.014052 | 0.962344 ± 0.013827 | 0.962344 ± 0.013827 |
| Mean, LR 5e-5 | 0.956217 ± 0.012712 | 0.954202 ± 0.011530 | 0.954162 ± 0.008099 |

The complete metric record—including precision, recall, Macro-F1, accuracy, train/validation loss, both marker conditions, and epoch-level entries—is in [`cv_results.csv`](cv_results.csv). It contains per-fold metrics for epochs 1–3 for the five newly completed configurations, epoch-3 per-fold metrics for the initial configuration, and epoch 1–3 aggregates for all six configurations.

## Reporting still required before completing Plan 03/01

This result note records the six configurations' focus metrics and the supporting aggregate metrics currently imported. It is **not yet the complete Plan 03/01 comparison report**. The tracked result table does not yet include performance stratified by conversation chunk count, source-stratified scores, per-fold training/inference runtime, undefined-metric flags, or confusion counts. Those fields are required for the planned comparison and should be derived from the persistent per-sample predictions and run histories before candidate selection/completion. Do not infer chunk-stratified behavior or runtime from the aggregate Scam F1 table.

The run prediction artifacts include chunk counts, content-token counts, per-sample inference timings, marker condition, source, and probabilities, and the histories include epoch timing/resource snapshots. Their hash references are preserved in the manifest. The 25 newer prediction files were not independently downloaded and rehashed during this review, so verify their recorded SHA-256 before aggregating them. Until that evidence is checked and the missing breakdowns are reported, treat the current report as a result summary rather than the final comparison deliverable.

## Provenance and interpretation

The original max-pooling LR 2e-5 configuration remains tied to its verified aggregate export and original five run IDs. The other five configurations were imported from their 25 completed per-fold run records. For those 25 runs, each `run_summary.json` was checked against the SHA-256 recorded for its `run_config.json` and `training_history.csv`; those config and history files matched. Run IDs and config/history/prediction hash values are recorded in [`experiment_manifest.csv`](experiment_manifest.csv). The prediction hash values are retained from run summaries but the prediction files were not independently downloaded and rehashed for this documentation pass. The five new configurations share the persistent Drive root `scam-call-alert/model-development/comparison-slices/wangchan-primary-remaining-20261010/runs/`. The original configuration's artifacts are under `scam-call-alert/model-development/comparison-slices/wangchanberta-fullcontext-20261010-pilot1/repairs/overflow-fix-20261010-v1/`. The manifest contains the exact per-run paths and hashes. Raw histories, sample-level predictions, checkpoints, and model weights remain in persistent Drive, not Git.

The new run summaries, configs, and histories were checksum-verified before metric import. `cv_results.csv` is a compact aggregate evidence table, not a replacement for the Drive run records. No transcript text or sample-level predictions were copied into Git.

These are development CV results from the approved validation folds, not final-test estimates. Do not infer performance beyond this dataset, use final-test data for tuning, or call WangchanBERTa the selected candidate yet. Continue the remaining candidates under their existing Plan 03 gates, reuse these 30 completed fits, then compare all four candidates using the approved role-free condition and fold variability.
