# Model Development Implementation Notes

This document records implementation decisions and evidence that a collaborator or a fresh agent session needs to continue model development consistently. The approved plans remain authoritative. It does not authorize changing a planned method, launch a run, or replace the approval gates in the plans.

## Read these first

1. [Plan 03/00 — Model Training](../01%20-%20PLANs/03%20-%20MODEL%20DEVELOPMENT/00%20-%20MODEL%20TRAINING.md)
2. [Plan 03/01 — Hyperparameter Tuning and Model Selection](../01%20-%20PLANs/03%20-%20MODEL%20DEVELOPMENT/01%20-%20HYPERPARAMETER%20TUNING%20AND%20MODEL%20SELECTION.md)
3. [Plan 02 — Data Preprocessing and Model Inputs](../01%20-%20PLANs/02%20-%20DATA%20PREPROCESSING%20AND%20MODEL%20INPUTS.md)
4. The current training and selection component READMEs and the applicable owner-approved run configuration.
5. [WangchanBERTa reproduction guide](selection/WANGCHANBERTA%20REPRODUCTION%20GUIDE.md) for the completed configuration's exact settings, source identity, and persistent evidence locations.

The local `IMPLEMENTATION HANDOFF.md` and `EXECUTION CHECKPOINTS.md` are session aids and are deliberately not tracked. The [training implementation report](training/training_report.md) provides the detailed diagnostic/run history, truncation table, and verification record. Use this document for the durable cross-candidate guidance; use each run's configuration, history, predictions, and verification evidence for exact execution provenance.

## Owner-approved comparison sequence

The owner approved this time-bounded sequence on 2026-10-10:

1. Compare all four candidates using **primary-only training** and the approved validation folds. This is the cross-candidate comparison used to select the candidate/configuration.
2. After reviewing those results, run one matched five-fold **primary + supplemental** comparison for the selected candidate/configuration only. Keep the model, selected settings, seed, folds, validation membership, marker conditions, and common epoch fixed; change only the training-data condition. Do not retune this follow-up or run it for the other candidates.
3. Use the paired results to decide the selected model's final training-data condition. Do not claim the supplemental-data effect is known for the other three candidates.

The approved learning-rate grid is `2e-5`, `3e-5`, and `5e-5` (with `3e-5` as the initial reference); seed is `67`, and the approved fold count is five. The planned first pass is 75 primary-only fold fits: 30 WangchanBERTa fits (two pooling methods × three learning rates × five folds) and 45 fits for the other three candidates (three learning rates × five folds each). The selected candidate's one supplemental comparison adds five fits, for 80 planned fits before approved retries or epoch extensions. One WangchanBERTa configuration is already complete, so it is included in—not additional to—the 30.

The previous search implementation encoded an all-model/two-data-condition matrix. It has now been replaced in the tracked selection workflow with the Plan 03/01 primary-only-first sequence. `selection/workflow.py` generates the approved 75-fit primary-only manifest and imports the existing WangchanBERTa five-fold aggregate export by its original run IDs and artifact hashes; it does not launch training or access the final test set. The existing 2e-5/max-pooling folds are marked complete and must not be rerun. Remaining rows stay blocked while launch gates are unresolved. The matched five-fold supplemental comparison is deferred until one primary-only candidate/configuration is selected. See `selection/comparison_report.md` and `selection/cv_results.csv` for the current scores and imported-evidence limits.

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

## First completed five-fold configuration

The first verified full-context comparative configuration is `wangchanberta__primary_only__lr-2e-05__pool-max`. It completed five folds at epoch 3 (maximum approved for this run: 4; no extension was run) with:

- WangchanBERTa, primary-only training, role-marked whole conversations.
- Learning rate `2e-5`, seed `67`, effective batch size `16` conversations, three epochs, warmup equal to 10% of planned optimizer updates rounded up.
- FP16 on a Colab Tesla T4; overlapping 508-content-token windows at stride 381; class-wise max pooling; one conversation-level unweighted cross-entropy loss.
- Paired role-free and role-marked validation; the held-out test set was not accessed.

Role-free Scam F1 by fold: `0.951965, 0.964912, 0.965217, 0.960699, 0.960000`; mean `0.960559`, sample SD `0.005358`. Role-marked Scam F1 mean was `0.972219`, sample SD `0.008171`. Role-marked supporting results were macro-F1 `0.973324 ± 0.007689`, accuracy `0.973372 ± 0.007662`, training loss `0.000999 ± 0.000257`, and validation loss `0.056321 ± 0.017067`. These are development-CV validation results for one configuration, not final-test results, not the completed WangchanBERTa search, and not a cross-candidate selection.

Persistent Drive evidence is under `scam-call-alert/model-development/comparison-slices/wangchanberta-fullcontext-20261010-pilot1/repairs/overflow-fix-20261010-v1/evidence/results-epoch3/` (`epoch3_cv_results.json` and `.md`). The verifier marked this configuration `verified_five_fold_epoch3`. Consult the files in that persistent location for per-fold artifacts, hashes, and complete provenance; this summary is not a substitute for them.

## Execution lessons to carry forward

- An FP16 WangchanBERTa attempt stopped at update 35 in epoch 1 because gradients became nonfinite while loss remained finite. The reviewed GradScaler path lowered its scale and replayed the same accumulated group; a later overflow at update 89 was handled the same way, and the five-fold configuration completed. Synthetic regression checks passed locally and in Colab. Apply this only through the reviewed trainer implementation and verify numerical behavior for each candidate/runtime; do not infer that all models or hardware will behave identically.
- Mid-epoch recovery was not made reliable for this project. The owner dropped resume-after-interruption to avoid further delay. Preserve partial per-update/epoch evidence and failure reason, then restart the failed fit from the original pretrained checkpoint with unchanged approved inputs/settings and a new run ID. Do not resume the failed fit. A separately approved extension after a successfully completed target epoch is distinct and follows Plan 03/00–03/01.
- The training process records scalar progress after optimizer updates, including processed-conversation fraction, updates, loss, learning rate, elapsed time, and resource observations. These records support progress review and reporting but do not contain model/optimizer state and cannot recover training.
- Keep the final test set closed throughout diagnostics, tuning, input-policy decisions, and candidate selection. Fold validation includes the saved validation population even when a run's training condition is primary-only; report training and validation data conditions precisely.
- Preserve failed attempts, fresh reruns, partial metrics, histories, resource/time evidence, predictions, and artifact identities. Do not overwrite the prior attempt or present execution failures as zero model scores.
- Store checkpoints, weights, sample-level predictions, transcript-bearing material, and detailed run evidence in the approved persistent storage, outside Git. Track this aggregate implementation note and suitable aggregate reports; never copy secrets or held-out transcript content here.

## Next collaborator actions

1. Confirm the current workspace/source and persistent Drive artifacts are accessible; retrieve the completed WangchanBERTa evidence and preserve its identities.
2. Read Plan 03/00 and 03/01, then use `selection/workflow.py` for the approved primary-only manifest and verified-result import. The trainer/selection source and regression suite are in the implementation handoff; do not use the old Colab notebooks, fixed-prefix diagnostic generator, caller-only templates, or legacy two-condition matrix commands. The complete 75-fit matrix still waits on its documented runtime and owner-approval gates.
3. Continue the remaining WangchanBERTa primary-only learning-rate/pooling configurations under their existing owner-approved gates. Review and approve the subsequent candidate-specific diagnostics/input policies and resource gates before running the other three candidates.
4. Reconcile comparable primary-only CV evidence for all four candidates before human-reviewed candidate selection. Only then run the selected candidate's matched supplemental-data comparison.
5. Keep final retraining, held-out evaluation, model packaging, app/system evaluation, and reporting within their own approved plans and gates.

If a requested step conflicts with an approved plan, stop that affected step, show the evidence and downstream impact, and obtain explicit owner confirmation before changing the plan or proceeding with a deviation.
