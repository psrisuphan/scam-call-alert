# Model Development Implementation Notes

This document records implementation decisions and evidence that a collaborator or a fresh agent session needs to continue model development consistently. The approved plans remain authoritative. It does not authorize changing a planned method, launch a run, or replace the approval gates in the plans.

## Read these first

1. [Plan 03/00 — Model Training](../01%20-%20PLANs/03%20-%20MODEL%20DEVELOPMENT/00%20-%20MODEL%20TRAINING.md)
2. [Plan 03/01 — Hyperparameter Tuning and Model Selection](../01%20-%20PLANs/03%20-%20MODEL%20DEVELOPMENT/01%20-%20HYPERPARAMETER%20TUNING%20AND%20MODEL%20SELECTION.md)
3. [Plan 02 — Data Preprocessing and Model Inputs](../01%20-%20PLANs/02%20-%20DATA%20PREPROCESSING%20AND%20MODEL%20INPUTS.md)
4. The current training and selection component READMEs and the applicable owner-approved run configuration.
5. [WangchanBERTa reproduction guide](selection/WANGCHANBERTA%20REPRODUCTION%20GUIDE.md) for all six completed WangchanBERTa configurations, settings, scores, and persistent evidence locations.

The local `IMPLEMENTATION HANDOFF.md` and `EXECUTION CHECKPOINTS.md` are session aids and are deliberately not tracked. The [training implementation report](training/training_report.md) provides the detailed diagnostic/run history, truncation table, and verification record. Use this document for the durable cross-candidate guidance; use each run's configuration, history, predictions, and verification evidence for exact execution provenance.

## Owner-approved comparison sequence

The owner approved this time-bounded sequence on 2026-10-10:

1. Compare all four candidates using **primary-only training** and the approved validation folds. This is the cross-candidate comparison used to select the candidate/configuration.
2. After reviewing those results, run one matched five-fold **primary + supplemental** comparison for the selected candidate/configuration only. Keep the model, selected settings, seed, folds, validation membership, marker conditions, and common epoch fixed; change only the training-data condition. Do not retune this follow-up or run it for the other candidates.
3. Use the paired results to decide the selected model's final training-data condition. Do not claim the supplemental-data effect is known for the other three candidates.

The approved learning-rate grid is `2e-5`, `3e-5`, and `5e-5` (with `3e-5` as the initial reference); seed is `67`, and the approved fold count is five. The planned first pass is 75 primary-only fold fits: 30 WangchanBERTa fits (two pooling methods × three learning rates × five folds) and 45 fits for the other three candidates (three learning rates × five folds each). The selected candidate's one supplemental comparison adds five fits, for 80 planned fits before approved retries or epoch extensions. All six WangchanBERTa configurations (30 fold fits) are now complete; they are included in—not additional to—the 30.

The previous search implementation encoded an all-model/two-data-condition matrix. It has now been replaced in the tracked selection workflow with the Plan 03/01 primary-only-first sequence. `selection/workflow.py` was used for the original five-fold aggregate import; it does not launch training or access the final test set. The manifest now records all 30 completed WangchanBERTa fold runs and their Drive artifact identities; the other 45 candidate fits remain blocked/pending. Do not rerun the manifest-generation or original-export import commands against the current files because they would erase newer completion/results data. The matched five-fold supplemental comparison is deferred until one primary-only candidate/configuration is selected. See `selection/comparison_report.md`, `selection/cv_results.csv`, and the reproduction guide for current scores and provenance.

## WangchanBERTa full-context implementation finding

Plan 02's prepared prefix inputs remain unchanged. A training-only length review found that the 510-token WangchanBERTa prefix limit would truncate 209 of 1,164 marked whole-conversation training records (204/510 primary Scam, 5/511 primary Not Scam, and 0/143 supplemental). The estimated content beyond those prefixes is 11,865 tokens, including 11,723 from primary Scam records. These are exposure counts, not a measure of semantic loss or model impact.

To preserve the full conversation in the WangchanBERTa experiment, retrieve full untruncated training text from Plan 02's `prepared/training_text.csv`, joined and checked by `sample_id`, source, label, and saved fold. Do not use the already-truncated JSONL text as the chunk source. Plan 02 remains intact. For this WangchanBERTa path:

- Use ordered windows of up to 508 content tokens plus two special tokens, with stride 381 (127 content-token overlap); continue until the final token is covered.
- Keep one label, fold, and loss contribution per conversation. Do not treat chunks as independent samples.
- Train separate class-wise max-logit-pooling and mean-logit-pooling variants. Compute one unweighted cross-entropy loss from the pooled two-class conversation logits.
- Keep effective batch size at 16 conversations and record per-conversation chunk counts and token coverage.
- Train on role-marked whole conversations. Use role-free whole-conversation validation for selection and paired role-marked validation as a diagnostic; threshold is 0.5.

This windowing choice is an approved WangchanBERTa implementation policy, not evidence that it is optimal or a default for the other tokenizers. For PhayaThaiBERT, HPLT, and XLM-RoBERTa, review each tokenizer's training-only length evidence and compatibility before the comparison. Preserve the Plan 02 inputs unless their owning plan is changed with owner confirmation. Do not assume the WangchanBERTa token limit, windowing, or pooling is appropriate for another candidate. Verify HPLT's pinned custom implementation/revision as required by Plan 03/00.

Caller-only training comparisons were dropped by the owner on 2026-10-10 because of the remaining project time. Plan 02's caller-only prepared data remains unchanged; it is not an active model-selection experiment. Do not add an LSTM to the current candidate comparison.

## Completed WangchanBERTa five-fold configurations

All six WangchanBERTa primary-only configurations are complete: max and mean pooling at learning rates `2e-5`, `3e-5`, and `5e-5`, five folds each, three epochs per fit. Their settings and complete epoch-level validation metrics are in `selection/WANGCHANBERTA REPRODUCTION GUIDE.md` and `selection/cv_results.csv`; `selection/experiment_manifest.csv` is authoritative for run IDs, Drive paths, and hashes. The concise result interpretation is in `selection/comparison_report.md`.

At epoch 3, role-free Scam F1 (mean ± sample SD across folds) was: max/LR 2e-5 `0.960559 ± 0.005358`; mean/LR 2e-5 `0.951139 ± 0.013833`; max/LR 3e-5 `0.961599 ± 0.008594`; mean/LR 3e-5 `0.954449 ± 0.009765`; max/LR 5e-5 `0.962344 ± 0.013827`; mean/LR 5e-5 `0.954162 ± 0.008099`. Role-marked diagnostic Scam F1 is in the report/CSV. The best mean score and lowest SD occur in different settings; these six results do not select an overall candidate because the other three models remain to be compared. All are CV validation results, not final-test estimates. The test set remains unopened.

The aggregate results currently recorded satisfy the focus-metric summary, but they do not yet satisfy every reporting field in Plan 03/01: chunk-count/source breakdowns, per-fold runtime/inference timing, undefined-metric flags, and confusion counts remain to be reconciled from the run histories and sample-level predictions before candidate selection/completion. Verify prediction files against manifest hashes before aggregating; the 25 new prediction files have not yet been independently downloaded and rehashed. The comparison report marks this limitation explicitly.

The original max/LR 2e-5 configuration retains its original aggregate-export provenance. The other 25 fits' run summaries, configs, and histories were checked by hash before importing metrics; their run IDs and config/history/prediction hashes are in the manifest. Detailed run evidence remains in Drive under the paths recorded there. All 30 completed fits must be reused, not rerun or overwritten.

## Execution lessons to carry forward

- An FP16 WangchanBERTa attempt stopped at update 35 in epoch 1 because gradients became nonfinite while loss remained finite. The reviewed GradScaler path lowered its scale and replayed the same accumulated group; a later overflow at update 89 was handled the same way, and the five-fold configuration completed. Synthetic regression checks passed locally and in Colab. Apply this only through the reviewed trainer implementation and verify numerical behavior for each candidate/runtime; do not infer that all models or hardware will behave identically.
- Mid-epoch recovery was not made reliable for this project. The owner dropped resume-after-interruption to avoid further delay. Preserve partial per-update/epoch evidence and failure reason, then restart the failed fit from the original pretrained checkpoint with unchanged approved inputs/settings and a new run ID. Do not resume the failed fit. A separately approved extension after a successfully completed target epoch is distinct and follows Plan 03/00–03/01.
- The training process records scalar progress after optimizer updates, including processed-conversation fraction, updates, loss, learning rate, elapsed time, and resource observations. These records support progress review and reporting but do not contain model/optimizer state and cannot recover training.
- Keep the final test set closed throughout diagnostics, tuning, input-policy decisions, and candidate selection. Fold validation includes the saved validation population even when a run's training condition is primary-only; report training and validation data conditions precisely.
- Preserve failed attempts, fresh reruns, partial metrics, histories, resource/time evidence, predictions, and artifact identities. Do not overwrite the prior attempt or present execution failures as zero model scores.
- Store checkpoints, weights, sample-level predictions, transcript-bearing material, and detailed run evidence in the approved persistent storage, outside Git. Track this aggregate implementation note and suitable aggregate reports; never copy secrets or held-out transcript content here.

## Next collaborator actions

1. Reuse the 30 completed WangchanBERTa fits and their existing IDs; do not rerun them. The full results and Drive provenance are recorded in the selection report, CSV, manifest, and reproduction guide.
2. Read Plan 03/00 and 03/01 and resolve the applicable gates for the other candidate-specific diagnostics/input policies and resource budgets before launching those candidate comparisons. Do not run the old Colab notebooks, fixed-prefix diagnostic generator, caller-only templates, legacy two-condition matrix commands, or the current workflow regeneration/import commands on the completed manifest/results.
3. Complete comparable primary-only CV evidence for the other three candidates, then review all four candidates using the approved selection guidance. Only after that selection, run the selected candidate's matched supplemental-data comparison.
4. Keep final retraining, held-out evaluation, model packaging, app/system evaluation, and reporting within their own approved plans and gates.

If a requested step conflicts with an approved plan, stop that affected step, show the evidence and downstream impact, and obtain explicit owner confirmation before changing the plan or proceeding with a deviation.
