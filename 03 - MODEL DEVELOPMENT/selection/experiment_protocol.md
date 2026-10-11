# Model selection protocol and approved reduction

Follow Plan 03/01 and its owner-approved 2026-10-11 amendment. No new comparative training is authorized.

## Approved scope and candidate

The owner approved stopping comparative training because the remaining compute/time cost was unaffordable:

- Retain 45 completed fold fits: 30 WangchanBERTa fits and five reference fits each for PhayaThaiBERT, HPLT and XLM-R.
- Omit the 30 remaining learning-rate fits and the matched supplemental-data comparison.
- Select PhayaThaiBERT, LR 3e-5, common epoch 2, primary-only.
- Retain one fresh final retraining run under Plan 03/02 after selection completion and its execution gates.

The selected configuration has the highest recorded five-fold role-free Scam F1 mean: 0.976796, sample SD 0.012884. XLM-R at epoch 2 has mean 0.973643 and SD 0.005730. The small difference does not prove superiority. The owner accepted PhayaThaiBERT's higher observed mean despite higher variability.

Learning-rate tuning coverage is unequal. PhayaThaiBERT, HPLT and XLM-R were tested only at 3e-5; XLM-R includes CPU FP32 and T4 FP16 runs. No matched five-fold supplemental effect was measured. The isolated supplemental fold does not establish a benefit.

## Selected settings

- Whole-conversation role-marked training; role-free app inference and selection validation.
- Seed 67; effective batch 16; microbatch 4 with accumulation 4.
- Selected duration: two epochs. No additional comparative epoch extension.
- Existing AdamW settings, linear warmup then constant learning rate, threshold 0.5.
- Approved warmup convention: ceil(0.10 × ceil(eligible training count / 16) × 3), using the initial three-epoch horizon.
- PhayaThaiBERT pinned checkpoint and tokenizer, existing 510-total-token fixed prefix and frozen preprocessing identities.

Paired role-marked validation remains diagnostic. Duration selection uses a common epoch across all five folds, not each fold's best epoch. Rank using unrounded mean role-free Scam F1; retain the plan's exact-tie rules and supporting evidence.

## Evidence and unresolved checks

Run identities, persistent locations and hashes are in experiment_manifest.csv. Existing metrics remain in cv_results.csv and comparison_report.md. The manifest identifies unrun fits as excluded by approved reduction, never completed or zero-scored.

A read-only check verified prediction hashes and recomputed aggregates for 13 Drive-hosted reference fits. Both local CPU XLM-R prediction hashes also matched. The detailed check is retained outside Git in .colab-cli/cloud-training/selection-prediction-reconciliation.log; it is not a replacement for full membership/snapshot verification.

The recorded WangchanBERTa slice directories are absent from the currently mounted account. The shared notebook confirms the coworker's MyDrive paths but does not expose the completed run folders. The owner requested leaving retrieval unresolved and moving to next-section preparation. Preserve prior aggregate/verification provenance and disclose missing access; do not invent source/chunk breakdowns or mark retrieval successful.

Local classifier/STT compatibility on the intended MacBook Air M2 remains unresolved. Its timing conflicts with the STT plan's deferred official-classifier integration check; no timing change has been approved. The final-evaluation implementation also retains an obsolete 120+5-fit completion guard and must not launch under that guard.

Do not freeze missing settings/checks, mark Plan 03/01 Finished, or access held-out data until the applicable completion requirements are resolved. Final training and test execution require their own approval records.

## Abandoned overnight preparation

The owner initially requested a complete overnight T4 queue, then approved the reduction above. That queue never launched.

The remaining 30-fit estimate was 7.86 allocated GPU hours, based on complete reference-fit times: PhayaThaiBERT 19.43 minutes (five fits), HPLT 11.10 minutes (five), XLM-R 16.62 minutes (three T4 fits), multiplied by ten remaining fits per model. Observed minimum/maximum scenarios totaled 6.31–10.06 hours, not confidence bounds. Independent verification, setup and interrupted-fit reruns would be additional.

SSH T4 and persistent Drive write/read/hash checks passed; current quota exceeded the proposed 300 GB allowance. This was bounded training feasibility, not completed downstream feasibility. Local regressions passed 64 tests and 13 subtests. Preflight/estimate records remain under ignored .colab-cli/cloud-training/. No credentials belong in tracked evidence.

## Preservation and handoff

Keep histories, sample-level predictions, checkpoints, weights, source identities and partial/failed attempts in their owning persistent locations outside Git. Do not overwrite completed runs or regenerate frozen assignments/legacy manifests. An interrupted fit is not resumed; preserve it and obtain authorization for any fresh rerun.

After remaining selection requirements pass, freeze selected_config.json and hand it to Plan 03/02. Do not substitute CV weights for the required fresh full-pool final model. Keep the held-out test closed during preparation.
