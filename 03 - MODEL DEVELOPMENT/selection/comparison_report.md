# Primary-only model comparison: current evidence

## Current owner decision (2026-10-11)

The owner approved stopping comparative training and selecting **PhayaThaiBERT, LR 3e-5, common epoch 2, primary-only**. The remaining 30 fits and the matched supplemental comparison are omitted by approved scope reduction. The 45 completed fold fits remain development evidence; no omitted fit is scored. See Plan 03/01's amendment for the authoritative revised scope.

PhayaThaiBERT's epoch-2 role-free Scam F1 is 0.976796 ± 0.012884, versus XLM-R's 0.973643 ± 0.005730. The selected model has the highest observed mean, but the small lead does not prove superiority; XLM-R has lower fold SD and mixed-runtime execution. Unequal learning-rate tuning limits the comparison. No five-fold supplemental effect was measured. The single local supplemental fold is not selection evidence.

Selection was approved by the owner; the task is not yet complete. Required report reconciliation and local classifier/STT compatibility remain before freezing selected_config.json. One fresh full-primary final retraining run is still required by Plan 03/02. The held-out test remains closed.

## Post-selection verification findings (2026-10-11)

A read-only SSH check independently matched prediction SHA-256 values and recomputed combined-source, source-specific and available chunk-count aggregates for 13 Drive-hosted PhayaThaiBERT/HPLT/XLM-R fits (18,162 prediction rows). Both local CPU XLM-R prediction files also matched their recorded SHA-256 values. Detailed aggregate evidence is retained outside Git in .colab-cli/cloud-training/selection-prediction-reconciliation.log. This check is not a new full membership/snapshot verification.

The two WangchanBERTa slice directories recorded in the manifest were absent from the currently mounted MyDrive. Consequently none of its 30 prediction files could be retrieved there in this pass. This is an access/location mismatch, not proof of deletion or invalid metrics. Preserve prior verification and completion records; pause final evidence reconciliation until the owning storage/location is resolved. Do not fabricate the missing breakdowns.

The selected STT configuration targets MacBook Air M2/MPS. This Linux laptop cannot demonstrate that host's combined compatibility. The STT owning plan also records a deferred official-classifier integration check; reconcile its timing with Plan 03/01's prefreeze requirement before claiming that gate passed.

Downstream final-evaluation code still requires a legacy 120+5-fit completion record, inconsistent with the approved reduced scope. That path must be corrected and tested with owner-confirmed requirements before final training. No selected_config.json was falsely marked frozen and no test set was opened.

## Historical scope and status

The following status notes preserve earlier reporting states; they do not override the current owner decision or the later verified HPLT/XLM-R results.

The approved primary-only comparison contains 75 fold fits: six WangchanBERTa configurations (two pooling methods × three learning rates × five folds) and 45 fits for the other three candidates. The six WangchanBERTa configurations are now complete: 30/30 fold fits finished three epochs. PhayaThaiBERT LR `3e-5` is also verified across five folds (35 verified fits total). HPLT LR `3e-5` folds 0–4 and XLM-R LR `3e-5` fold 0 were observed completed but still await independent verification; XLM-R fold 1 was last observed running before runtime loss. The other learning-rate configurations remain pending. After the four-candidate comparison and reviewed candidate selection, one matched five-fold primary + supplemental follow-up may be run for that candidate/configuration. The held-out test set has not been opened.

These results are development cross-validation evidence for WangchanBERTa and one PhayaThaiBERT reference configuration. Role-free validation Scam F1 is the selection metric; role-marked validation is diagnostic. Scores below summarize fold-level metrics as mean ± sample SD (denominator 4), unless marked as a single mean. They do not select the final candidate before the other models are compared and are not final-test performance.

## Completed configurations: epoch 3

WangchanBERTa fits used primary-only role-marked whole-conversation training, saved folds 0–4, seed 67, effective batch 16 conversations, three epochs, WangchanBERTa full-context windows (508 content tokens, stride 381, overlap 127), the listed pooling method, one unweighted conversation-level cross-entropy loss, and paired role-free/role-marked whole-conversation validation at threshold 0.5. Runtime was Colab Tesla T4 with FP16. Each validation fold contains the combined validation population from both sources, even though training used primary data only. PhayaThaiBERT uses the same saved folds and training settings, with its approved 510-token fixed prefix instead of full-context windows, LR `3e-5`, and microbatch 4 × accumulation 4. Its warmup is 16 updates per fold.

| Configuration | Role-free Scam F1 (mean ± SD) | Role-marked Scam F1 (mean ± SD) | Role-free precision / recall | Role-free Macro-F1 | Role-free accuracy | Role-free validation loss |
|---|---:|---:|---:|---:|---:|---:|
| Max, LR 2e-5 | 0.960559 ± 0.005358 | 0.972219 ± 0.008171 | 0.933601 / 0.989156 | 0.961324 | 0.961340 | 0.074191 |
| Mean, LR 2e-5 | 0.951139 ± 0.013833 | 0.965792 ± 0.008262 | 0.908517 / 0.998198 | 0.951033 | 0.951040 | 0.098871 |
| Max, LR 3e-5 | 0.961599 ± 0.008594 | 0.971681 ± 0.005055 | 0.932402 / 0.992776 | 0.962194 | 0.962206 | 0.084124 |
| Mean, LR 3e-5 | 0.954449 ± 0.009765 | 0.964989 ± 0.006088 | 0.913000 / 1.000000 | 0.954472 | 0.954477 | 0.114466 |
| Max, LR 5e-5 | **0.962344 ± 0.013827** | 0.969942 ± 0.010419 | 0.936988 / 0.989189 | 0.963060 | 0.963075 | 0.097962 |
| Mean, LR 5e-5 | 0.954162 ± 0.008099 | 0.965638 ± 0.008470 | 0.916932 / 0.994595 | 0.954473 | 0.954477 | 0.128064 |
| PhayaThaiBERT, LR 3e-5 | **0.976003 ± 0.011300** | 0.976410 ± 0.013856 | 0.965163 / 0.987355 | 0.976779 | 0.976809 | 0.060712 |
| HPLT Thai, LR 3e-5 | 0.941220 ± 0.030459 | 0.959621 ± 0.010196 | 0.998000 / 0.891777 | 0.946958 | 0.947614 | 0.332635 |
| XLM-RoBERTa, LR 3e-5 | 0.970691 ± 0.012578 | 0.968865 ± 0.010702 | 0.983721 / 0.958477 | 0.972400 | 0.972514 | 0.170987 |

Across all four candidates evaluated on primary-only 5-fold CV, **PhayaThaiBERT** achieves the highest role-free Scam F1 mean (`0.976003` at epoch 3, `0.976796` at epoch 2), followed closely by **XLM-RoBERTa** (`0.970691` at epoch 3, `0.973643` at epoch 2), **WangchanBERTa** (`0.962344` at epoch 3), and **HPLT Thai** (`0.941220` at epoch 3).

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
| PhayaThaiBERT, LR 3e-5 | 0.955559 ± 0.024674 | **0.976796 ± 0.012884** | **0.976003 ± 0.011300** |
| HPLT Thai, LR 3e-5 | 0.503603 ± 0.178756 | 0.724400 ± 0.275895 | 0.941220 ± 0.030459 |
| XLM-RoBERTa, LR 3e-5 | 0.955164 ± 0.031624 | 0.973643 ± 0.005730 | 0.970691 ± 0.012578 |

The complete metric record—including precision, recall, Macro-F1, accuracy, train/validation loss, both marker conditions, and epoch-level entries—is in [`cv_results.csv`](cv_results.csv). It contains per-fold metrics for epochs 1–3 for the five newly completed configurations, epoch-3 per-fold metrics for the initial configuration, and epoch 1–3 aggregates for all six WangchanBERTa configurations. PhayaThaiBERT adds 30 per-fold rows and six aggregate rows for epochs 1–3 and both marker conditions. Its training-loss fields are blank pending retrieval of verified histories.

## Reporting still required before completing Plan 03/01

This result note records the completed configurations' focus metrics and the supporting aggregate metrics currently imported. It is **not yet the complete Plan 03/01 comparison report**. The tracked result table does not yet include performance stratified by conversation chunk count, source-stratified scores, per-fold training/inference runtime, undefined-metric flags, or confusion counts. Those fields are required for the planned comparison and should be derived from the persistent per-sample predictions and run histories before candidate selection/completion. Do not infer chunk-stratified behavior or runtime from the aggregate Scam F1 table.

The run prediction artifacts include chunk counts, content-token counts, per-sample inference timings, marker condition, source, and probabilities, and the histories include epoch timing/resource snapshots. Their hash references are preserved in the manifest. The 25 newer prediction files were not independently downloaded and rehashed during this review, so verify their recorded SHA-256 before aggregating them. Until that evidence is checked and the missing breakdowns are reported, treat the current report as a result summary rather than the final comparison deliverable.

## Execution pending verification

The owner-authorized HPLT then XLM-R LR `3e-5` queue used saved folds 0–4, the approved 512-token prefixes, and the same training settings. Monitoring observed HPLT's five folds and XLM-R fold 0 completed, XLM-R fold 1 at epoch 3/update 129, and folds 2–4 not yet started. These are last observations, not proof of terminal state after runtime loss. The manifest records each run separately; no unverified scores are imported.

Persistent slice: `scam-call-alert/model-development/comparison-slices/other-models-primary-reference-20261011T074624Z`. Inspect saved summaries and verify artifact hashes before scoring or retrying. Preserve an interrupted fit and restart fresh with a new run ID; never resume it. Replacement T4 allocation returned HTTP 503 through six spaced retries over 30 minutes. The cause of the runtime loss/allocation failure is unconfirmed; no alternate hardware or precision was used for training. Combined downstream feasibility and local inference/STT preflight remain unresolved.

## Provenance and interpretation

The original max-pooling LR 2e-5 configuration remains tied to its verified aggregate export and original five run IDs. The other five configurations were imported from their 25 completed per-fold run records. For those 25 runs, each `run_summary.json` was checked against the SHA-256 recorded for its `run_config.json` and `training_history.csv`; those config and history files matched. Run IDs and config/history/prediction hash values are recorded in [`experiment_manifest.csv`](experiment_manifest.csv). The prediction hash values are retained from run summaries but the prediction files were not independently downloaded and rehashed for this documentation pass. The five new configurations share the persistent Drive root `scam-call-alert/model-development/comparison-slices/wangchan-primary-remaining-20261010/runs/`. The original configuration's artifacts are under `scam-call-alert/model-development/comparison-slices/wangchanberta-fullcontext-20261010-pilot1/repairs/overflow-fix-20261010-v1/`. The manifest contains the exact per-run paths and hashes. Raw histories, sample-level predictions, checkpoints, and model weights remain in persistent Drive, not Git.

The new run summaries, configs, and histories were checksum-verified before metric import. `cv_results.csv` is a compact aggregate evidence table, not a replacement for the Drive run records. No transcript text or sample-level predictions were copied into Git.

PhayaThaiBERT's five-fold verification is stored at `scam-call-alert/model-development/comparison-slices/phaya-primary-reference-remaining-20261011T051518Z/evidence/phaya-primary-lr3e-05-fivefold-verification.json` (SHA-256 `5660ae87e27b0927b8ac2df4e434701a27e7a791ca4f52d5cf473c9cd633a8cc`). It recomputed metrics from sample predictions, checked exact validation membership and finite normalized probabilities, and verified the new epoch snapshots; fold 0 reuses its prior snapshot verification. The manifest retains all run/config/history/prediction hashes. Fold 0 is under `remaining-primary-first-fit-20261011T044510Z`; folds 1–4 are under `phaya-primary-reference-remaining-20261011T051518Z`. The earlier unverified fold-0 attempt remains in its attempt history and is not scored.

PhayaThaiBERT's successful fits took 97.16 minutes total (11.95–31.56 minutes per fold), excluding independent verification. Folds 1 and 2 each recorded one FP16 overflow replay; all five fits completed. Epoch 2 has the highest observed role-free mean for this configuration. This does not select the final candidate, establish superiority, or isolate the effect of fixed-prefix versus full-context input.

These are development CV results from the approved validation folds, not final-test estimates. Do not infer performance beyond this dataset, use final-test data for tuning, or call WangchanBERTa the selected candidate yet. Continue the remaining candidates under their existing Plan 03 gates, reuse these 30 completed fits, then compare all four candidates using the approved role-free condition and fold variability.
