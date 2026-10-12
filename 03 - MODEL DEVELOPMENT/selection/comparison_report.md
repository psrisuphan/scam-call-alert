# Primary-only model comparison: current evidence

## Current owner decision (2026-10-11)

The owner approved stopping comparative training and selecting **PhayaThaiBERT, LR 3e-5, common epoch 2, primary-only**. The remaining 30 fits and the matched supplemental comparison are omitted by approved scope reduction. The 45 completed fold fits remain development evidence; no omitted fit is scored. See Plan 03/01's amendment for the authoritative revised scope.

PhayaThaiBERT's epoch-2 role-free Scam F1 is 0.976796 ± 0.012884, versus XLM-R's 0.973643 ± 0.005730. The selected model has the highest observed mean, but the small lead does not prove superiority; XLM-R has lower fold SD and mixed-runtime execution. Unequal learning-rate tuning limits the comparison. No five-fold supplemental effect was measured. The single local supplemental fold is not selection evidence.

Selection was approved by the owner; Plan 03/01 is not yet complete. The selected predictive configuration is frozen in selected_config.json. The owner-approved timing amendment assigns final classifier/STT compatibility to the coworker on MacBook Air M2 after final training and before held-out access. The first final fit completed computation but failed persistence; preserve its evidence. After explicit approval of persistence repair and one fresh replacement fit, phaya-final-replacement-primary-epoch2-20261012T050936Z completed two epochs/128 updates and its weights, checkpoint and run evidence were independently verified in owner-local persistent storage. See final-evaluation/README.md for locations and hashes. The held-out test remains closed.

## Post-selection verification findings (2026-10-11)

A read-only SSH check independently matched prediction SHA-256 values and recomputed combined-source, source-specific and available chunk-count aggregates for 13 Drive-hosted PhayaThaiBERT/HPLT/XLM-R fits (18,162 prediction rows). Both local CPU XLM-R prediction files also matched their recorded SHA-256 values. Detailed aggregate evidence is retained outside Git in .colab-cli/cloud-training/selection-prediction-reconciliation.log. This check is not a new full membership/snapshot verification.

The two WangchanBERTa slice directories recorded in the manifest were absent from the currently mounted MyDrive. Consequently none of its 30 prediction files could be retrieved there in this pass. This is an access/location mismatch, not proof of deletion or invalid metrics. The owner accepted proceeding with this access limitation; preserve prior verification and completion records without fabricating the missing breakdowns.

The selected STT configuration targets MacBook Air M2/MPS. This Linux laptop cannot demonstrate that host's combined compatibility. Plan 03/01's owner-approved timing amendment permits final retraining before the coworker check, but compatibility remains pending and blocks held-out access.

The final-evaluation guard has been updated and tested for 45 completed fits and 30 owner-approved exclusions. The authorized final run was launched directly through the reusable trainer with frozen settings and hash-bound selected configuration/report evidence. Its original run config does not include the selection-completion binding required by evaluation.py. Preserve that config and resolve the provenance integration before using the shared evaluation/parity pipeline; do not bypass the gate or claim selection complete. No test set was opened.

## Available source and marker breakdowns (2026-10-12)

These tables reuse the earlier hash-verified aggregate recomputation for 13 Drive fits and freshly rehash/recompute the two local CPU XLM-R prediction files. They cover all five folds for PhayaThaiBERT, HPLT and XLM-R at LR 3e-5, with both marker conditions. All combined-source fold metrics across epochs 1–3 agree with the existing cv_results.csv to within 1e-10.

This reporting pass does not reverify full fold membership or checkpoint snapshots. WangchanBERTa's 30 prediction files remain inaccessible, so its source/chunk breakdowns are not supplied. No new experiment or held-out inference was performed.

### Source-specific role-free results

Use each configuration's selected common epoch: PhayaThaiBERT 2, HPLT 3, XLM-R 2. F1 is the arithmetic mean ± sample SD of five fold scores; other score columns are fold means. Counts and confusion cells are sums over the five validation folds, not the denominator of the mean-fold scores. Confusion order is [Not Scam, Scam], true rows and predicted columns.

| Model | Epoch | Source | N (Not Scam / Scam) | Scam F1 mean ± SD | Precision | Recall | Macro-F1 | Accuracy | Pooled confusion [[TN, FP], [FN, TP]] |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| PhayaThaiBERT | 2 | primary | 1021 (511 / 510) | 1.000000 ± 0.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | [[511, 0], [0, 510]] |
| PhayaThaiBERT | 2 | supplemental | 143 (99 / 44) | 0.740857 ± 0.115665 | 0.701190 | 0.803968 | 0.803358 | 0.824758 | [[82, 17], [9, 35]] |
| HPLT | 3 | primary | 1021 (511 / 510) | 0.982466 ± 0.033737 | 0.998000 | 0.969193 | 0.983511 | 0.983587 | [[510, 1], [16, 494]] |
| HPLT | 3 | supplemental | 143 (99 / 44) | 0.000000 ± 0.000000 | 0.000000 | 0.000000 | 0.409351 | 0.693816 | [[99, 0], [44, 0]] |
| XLM-R | 2 | primary | 1021 (511 / 510) | 0.998039 ± 0.002685 | 0.998058 | 0.998039 | 0.998014 | 0.998015 | [[510, 1], [1, 509]] |
| XLM-R | 2 | supplemental | 143 (99 / 44) | 0.632677 ± 0.111945 | 0.790130 | 0.571429 | 0.751333 | 0.810812 | [[90, 9], [18, 26]] |

At the selected PhayaThaiBERT epoch, all 26 role-free validation errors are in the supplemental source: 17 false positives and 9 false negatives. Primary-source fold F1 is 1.0, while supplemental-source mean-fold F1 is 0.740857. The combined-source mean therefore hides a substantial source difference. This is CV selection evidence on the saved datasets, not proof of real-call robustness or a measured benefit from supplemental training. HPLT's epoch-3 role-free predictions classify every supplemental record as Not Scam, missing all 44 supplemental Scam records; its undefined precision is explicitly flagged below.

### Fold-level source support and Scam F1

| Model | Fold | Epoch | Primary N (Not Scam / Scam) | Primary F1 | Supplemental N (Not Scam / Scam) | Supplemental F1 |
|---|---:|---:|---:|---:|---:|---:|
| PhayaThaiBERT | 0 | 2 | 201 (102 / 99) | 1.000000 | 32 (20 / 12) | 0.750000 |
| PhayaThaiBERT | 1 | 2 | 202 (100 / 102) | 1.000000 | 31 (22 / 9) | 0.666667 |
| PhayaThaiBERT | 2 | 2 | 208 (104 / 104) | 1.000000 | 25 (18 / 7) | 0.933333 |
| PhayaThaiBERT | 3 | 2 | 201 (99 / 102) | 1.000000 | 32 (23 / 9) | 0.640000 |
| PhayaThaiBERT | 4 | 2 | 209 (106 / 103) | 1.000000 | 23 (16 / 7) | 0.714286 |
| HPLT | 0 | 3 | 201 (102 / 99) | 0.994975 | 32 (20 / 12) | 0.000000 |
| HPLT | 1 | 3 | 202 (100 / 102) | 1.000000 | 31 (22 / 9) | 0.000000 |
| HPLT | 2 | 3 | 208 (104 / 104) | 0.922280 | 25 (18 / 7) | 0.000000 |
| HPLT | 3 | 3 | 201 (99 / 102) | 0.995074 | 32 (23 / 9) | 0.000000 |
| HPLT | 4 | 3 | 209 (106 / 103) | 1.000000 | 23 (16 / 7) | 0.000000 |
| XLM-R | 0 | 2 | 201 (102 / 99) | 1.000000 | 32 (20 / 12) | 0.727273 |
| XLM-R | 1 | 2 | 202 (100 / 102) | 0.995074 | 31 (22 / 9) | 0.625000 |
| XLM-R | 2 | 2 | 208 (104 / 104) | 1.000000 | 25 (18 / 7) | 0.666667 |
| XLM-R | 3 | 2 | 201 (99 / 102) | 0.995122 | 32 (23 / 9) | 0.700000 |
| XLM-R | 4 | 2 | 209 (106 / 103) | 1.000000 | 23 (16 / 7) | 0.444444 |

### Paired marker diagnostics

These are combined-source, matching-fold/weight/epoch comparisons. Delta is role-free minus marked fold F1, summarized as mean ± sample SD. It does not establish superiority of marked training and can include retained-content differences after marker removal.

| Model | Epoch | Role-free F1 mean ± SD | Marked F1 mean ± SD | Paired delta mean ± SD |
|---|---:|---:|---:|---:|
| PhayaThaiBERT | 2 | 0.976796 ± 0.012884 | 0.979067 ± 0.013556 | -0.002271 ± 0.008743 |
| HPLT | 3 | 0.941220 ± 0.030459 | 0.959621 ± 0.010196 | -0.018401 ± 0.033402 |
| XLM-R | 2 | 0.973643 ± 0.005730 | 0.971818 ± 0.006558 | +0.001825 ± 0.002499 |

All reported source subsets are nonempty. Undefined precision is reported as zero and flagged below. Execution failures were zero in the 15 verified prediction files. This pass does not establish measured inference latency: available inference_seconds fields for these prefix-model artifacts are blank, and the earlier aggregate value 0 represents missing timing rather than zero-time inference.

Required WangchanBERTa source/chunk breakdowns, complete runtime/loss-curve reporting and class-specific truncation discussion remain outstanding or evidence-limited. Plan 03/01 is not marked Finished.

Evidence: manifest prediction hashes, the existing remote reconciliation log and the freshly verified local prediction hashes. Detailed derived evidence is stored outside Git at /content/drive/MyDrive/scam-call-alert/model-development/final-evaluation/execution-20261012T024607Z/evidence/reporting-breakdown-evidence.json (SHA-256 97d96aaa2de65cfd009fe5bd96a2dc2d891a742aa3775d4fba8a899503cc3abf); it contains aggregate counts only. The final-run launch retained an immutable copy of the earlier comparison report, so this reporting update does not rewrite the launched configuration or its bound report snapshot.

### Undefined metrics at the reported epochs

| Model | Fold | Epoch | Marker | Subset | Flag and reason |
|---|---:|---:|---|---|---|
| HPLT | 0 | 3 | role_free | source:supplemental | precision = 0: no predicted Scam |
| HPLT | 0 | 3 | role_marked | source:supplemental | precision = 0: no predicted Scam |
| HPLT | 1 | 3 | role_free | source:supplemental | precision = 0: no predicted Scam |
| HPLT | 2 | 3 | role_free | source:supplemental | precision = 0: no predicted Scam |
| HPLT | 2 | 3 | role_marked | source:supplemental | precision = 0: no predicted Scam |
| HPLT | 3 | 3 | role_free | source:supplemental | precision = 0: no predicted Scam |
| HPLT | 3 | 3 | role_marked | source:supplemental | precision = 0: no predicted Scam |
| HPLT | 4 | 3 | role_free | source:supplemental | precision = 0: no predicted Scam |
| HPLT | 4 | 3 | role_marked | source:supplemental | precision = 0: no predicted Scam |

## Available run cost and loss trajectories (2026-10-12)

These figures reuse the existing five-fold verification records; each run/config/history/prediction identity is matched to the current manifest. Elapsed time is the recorded completed-run duration, including that run's I/O and setup behavior, not isolated GPU compute. Downloads, other attempts and independent verification may be outside these durations. Mixed hardware and differing storage conditions prevent a controlled speed comparison.

| Model | Fold | Runtime | Recorded elapsed minutes |
|---|---:|---|---:|
| PhayaThaiBERT | 0 | T4 FP16 | 13.69 |
| PhayaThaiBERT | 1 | T4 FP16 | 11.95 |
| PhayaThaiBERT | 2 | T4 FP16 | 17.85 |
| PhayaThaiBERT | 3 | T4 FP16 | 22.10 |
| PhayaThaiBERT | 4 | T4 FP16 | 31.56 |
| PhayaThaiBERT total | 5 folds | T4 FP16 | 97.16 |
| HPLT | 0 | T4 FP16 | 9.54 |
| HPLT | 1 | T4 FP16 | 11.17 |
| HPLT | 2 | T4 FP16 | 11.50 |
| HPLT | 3 | T4 FP16 | 11.25 |
| HPLT | 4 | T4 FP16 | 12.02 |
| HPLT total | 5 folds | T4 FP16 | 55.49 |
| XLM-R | 0 | T4 FP16 | 16.75 |
| XLM-R | 1 | T4 FP16 | 16.35 |
| XLM-R | 2 | T4 FP16 | 16.77 |
| XLM-R | 3 | CPU FP32 | 47.65 |
| XLM-R | 4 | CPU FP32 | 51.85 |
| XLM-R total | 5 folds | Mixed T4/CPU | 149.36 |

### Loss trajectories

Each cell is training loss / role-free validation loss / marked validation loss, at the common epoch shown. Validation losses and WangchanBERTa training losses are fold means from the existing aggregate rows. HPLT/XLM-R training-loss means are recomputed from their five-fold verification records, whose hashes are listed below. “Unavailable” means the recorded field is absent, not zero. CV losses are development evidence and do not select checkpoints in the final no-validation fit.

| Configuration | Epoch 1 | Epoch 2 | Epoch 3 |
|---|---|---|---|
| wangchanberta__primary_only__lr-2e-05__pool-max | 0.356845 / 0.095214 / 0.076315 | 0.006811 / 0.072650 / 0.053534 | 0.000999 / 0.074191 / 0.056321 |
| wangchanberta__primary_only__lr-5e-05__pool-mean | 0.233290 / 0.114917 / 0.096357 | 0.009231 / 0.137733 / 0.120603 | 0.000435 / 0.128064 / 0.112587 |
| wangchanberta__primary_only__lr-3e-05__pool-mean | 0.306901 / 0.079662 / 0.062399 | 0.002643 / 0.103134 / 0.085432 | 0.000330 / 0.114466 / 0.098954 |
| wangchanberta__primary_only__lr-2e-05__pool-mean | 0.356243 / 0.087122 / 0.070421 | 0.008029 / 0.097881 / 0.077077 | 0.000942 / 0.098871 / 0.077957 |
| wangchanberta__primary_only__lr-5e-05__pool-max | 0.239419 / 0.082534 / 0.091263 | 0.006430 / 0.098667 / 0.084077 | 0.000163 / 0.097962 / 0.083660 |
| wangchanberta__primary_only__lr-3e-05__pool-max | 0.300181 / 0.070831 / 0.058447 | 0.002737 / 0.081808 / 0.068940 | 0.000761 / 0.084124 / 0.067894 |
| phayathaibert__primary_only__lr-3e-05 | Unavailable / 0.109804 / 0.089634 | Unavailable / 0.057255 / 0.051603 | Unavailable / 0.060712 / 0.054939 |
| hplt__primary_only__lr-3e-05 | 0.353872 / 1.059247 / 0.428600 | 0.066975 / 0.568592 / 0.416763 | 0.039440 / 0.332635 / 0.338482 |
| xlmr__primary_only__lr-3e-05 | 0.448065 / 0.134856 / 0.112678 | 0.015295 / 0.157309 / 0.171759 | 0.003046 / 0.170987 / 0.199370 |

PhayaThaiBERT training-loss fields remain unavailable in the currently retrieved CV reporting records; do not invent them. The training-only token-length report remains the authoritative truncation evidence. These tables do not replace the missing WangchanBERTa source/chunk breakdowns or measured per-request inference latency.

Evidence snapshots used here:
- .colab-cli/cloud-training/phaya-fivefold-verification.json (SHA-256 5660ae87e27b0927b8ac2df4e434701a27e7a791ca4f52d5cf473c9cd633a8cc).
- .colab-cli/cloud-training/hplt-fivefold-verification.json (SHA-256 6abc47afb2732770b983781990f63cb5b776fc974031bc0cbf877d417f88b1fe).
- .colab-cli/local-training/xlmr-primary-lr3e-05-fivefold-verification.json (SHA-256 6b54ce3f8de14b707d42fb32d63ec9190258e2033ebbce9dea3671810fad1256).

### Class-specific prefix truncation exposure

Reuse the approved training-only token-length report, without reading test data or changing the input policy. Counts below are role-marked whole-conversation primary records exceeding each approved total-token prefix budget; token loss is not measured semantic or prediction loss.

| Model | Budget | Primary Not Scam exceeding / N | Primary Scam exceeding / N |
|---|---:|---:|---:|
| PhayaThaiBERT | 510 | 3 / 511 (0.59%) | 153 / 510 (30.00%) |
| HPLT | 512 | 0 / 511 (0.00%) | 5 / 510 (0.98%) |
| XLM-R | 512 | 1 / 511 (0.20%) | 140 / 510 (27.45%) |

PhayaThaiBERT truncation exposure is much higher for primary Scam records (30%) than Not Scam records (0.59%). This is a known input limitation, even though its selected-epoch primary CV scores are perfect. The report cannot establish how much this affects prediction or later STT/partial-context inputs. Supplemental records do not exceed these prefix budgets in the role-marked training-pool report. WangchanBERTa uses its separately approved full-context windows; its earlier prefix length report is not evidence of content loss in those windowed runs.

Source: input-preparation/token_length_report.json (SHA-256 b2b79fabd9b46dc7aa8d67a582240ec2a530ec57b17a6eaac7ecdf1fc5e96e4d), marked training-pool subsets only. Paired role-free content retention remains a separate diagnostic, not inferred from these counts.

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
