# Training feasibility and implementation report

## Remaining-candidate checkpoint (2026-10-11)

PhayaThaiBERT LR `3e-5` has completed and passed five-fold verification at epochs 1–3. Role-free Scam F1 mean ± sample SD: epoch 1 `0.955559 ± 0.024674`, epoch 2 `0.976796 ± 0.012884`, epoch 3 `0.976003 ± 0.011300`. Settings, identities, limitations and persistent paths are recorded in [the comparison report](../selection/comparison_report.md) and [verification export](../selection/phaya_primary_reference_verification.json). This is one reference configuration; Plans 03/00 and 03/01 remain Planned.

The owner approved candidate-specific fixed prefixes (Phaya 510, HPLT/XLM-R 512), three initial epochs with finite maximum four, warmup `ceil(0.10 * ceil(train_count/16) * 3)`, T4 FP16, and microbatch 4 × accumulation 4 after bounded training-only diagnostics. Extensions require separate approval. Whole-conversation role-marked training and paired validation retain seed 67, effective batch 16 and the original optimizer/threshold settings. Diagnostics must not select models.

Two previously local, owner-approved compatibility fixes are now tracked:
- Exact pinned PhayaThaiBERT/XLM-R unused masked-LM keys, plus XLM-R unused pooler keys, are allowed after checkpoint ID, revision, model type and architecture checks. Missing/mismatched backbone weights and unrelated keys still fail; HPLT receives no new exception.
- Checkpoint publication verification returns identity/update metadata rather than retaining full loaded model and optimizer tensors. Checkpoint contents, verification checks, extension behavior and the fresh-restart interruption policy are unchanged.

The tracked trainer matches the executed trainer SHA-256 `d44342cfb5024fdf88de15229f86943b47ee53602714ffe9c9ed4af994725cbd`. Training-only bundle SHA-256 was `5e1449bde3f206a415afe896082f4eced78089daa814a26c1f445f3c3cc95996`. The current local regression run passed 64 tests and 13 subtests; this checks implementation behavior, not uninterrupted Colab availability.

HPLT's five LR `3e-5` folds and XLM-R fold 0 were observed completed, but independent verification remains pending after runtime disappearance. XLM-R fold 1 was last observed running; inspect preserved evidence before assigning its terminal status or starting a fresh fit. The original queue slice is `comparison-slices/other-models-primary-reference-20261011T074624Z`. Subsequent T4 allocation returns HTTP 503; its cause is unconfirmed. No final test was opened or candidate selected, and existing WangchanBERTa evidence was preserved.

The earlier checkpoints below retain their historical evidence. Their pending counts and unverified-compatibility statements describe those checkpoints, not this update.


## Earlier checkpoint — WangchanBERTa primary-only configurations (2026-10-11)

All six approved WangchanBERTa settings are complete: max/mean pooling × learning rates `2e-5`, `3e-5`, and `5e-5`, five saved folds each (30 fits total), three epochs per fit. The original max/LR 2e-5 set was completed and verified earlier; the remaining 25 fits have now completed and their run summaries were verified against the stored run-config and training-history SHA-256 values before the metrics were added. Prediction hash values are recorded, but the prediction files were not independently downloaded and rehashed for this documentation pass. The 75-row matrix therefore has 30 completed WangchanBERTa rows and 45 other-candidate rows still blocked/pending.

The epoch-3 role-free validation Scam F1 mean ± sample SD was: max/LR 2e-5 `0.960559 ± 0.005358`; mean/LR 2e-5 `0.951139 ± 0.013833`; max/LR 3e-5 `0.961599 ± 0.008594`; mean/LR 3e-5 `0.954449 ± 0.009765`; max/LR 5e-5 `0.962344 ± 0.013827`; mean/LR 5e-5 `0.954162 ± 0.008099`. The role-marked diagnostic scores and epoch 1–3 trajectories are in `../selection/comparison_report.md` and `../selection/cv_results.csv`; per-run IDs, Drive locations, and hashes are in `../selection/experiment_manifest.csv`.

These are CV development results only. Role-free validation remains the selection condition; role-marked is diagnostic. Validation folds include the combined validation population even though these fits trained on primary data only. The other three candidate comparisons remain pending, so no final candidate has been selected. The held-out test set remains unopened. Reuse all 30 completed fits; do not repeat or overwrite them.


## Checkpoint 01 — completed full-context feasibility diagnostics (2026-10-10)

**Scope and interpretation.** The separately owner-approved WangchanBERTa full-context max/mean runs were bounded two-update feasibility diagnostics: fold 0, 32 longest marked training conversations, effective batch 16, seed 67, learning rate 3e-5, zero warmup for this diagnostic only, fp16, and a Colab Tesla T4. Each reports zero completed epochs and exactly two optimizer updates. This is not a CV comparison, model selection, a complete training schedule, or final performance evidence. The held-out test set was never opened (`held_out_test_opened=false`). At the time of Checkpoint 01, no comparative 60-fit pilot had launched; verified results for the later repaired first configuration are recorded below.

**Source and input identity.** Active notebook: [WangchanBERTa comparison slice](https://colab.research.google.com/drive/1b9Q7PalOg7hA6ndsHiFQJyldJBkkiPWB). Slice: `wangchanberta-fullcontext-20261010-pilot1`. Training-only source archive SHA-256: `0d816d0a2500e4f76bfcc462335f59d33238554a944c4829e842ba983bcaa23c`. Verified training input CSV SHA-256: `763abee35dd052b248d18dc78b5888b94062f75cdfeb7756ad3ce5683e2119d4`; saved assignments SHA-256: `4f7a1e012f8a4883a15d8e99ab38f5da4d10a07cb0335ec09cbcee0bd914147a`.

| Pooling | Run ID | Runtime profile SHA-256 | Approved-settings SHA-256 | Run status |
|---|---|---|---|---|
| Max | `diagnostic-wangchanberta-full-context-max-wangchanberta-fullcontext-20261010-pilot1` | `4eb077cee3858581ca99663335285f6f4303bc75c7e65bd2f689918d3f169b85` | `163ea77ee1c382ff0585732c6dccfd93c13636d9c75b23a79f7f8bc3323d3fc1` | completed; 2 updates; 0 epochs |
| Mean | `diagnostic-wangchanberta-full-context-mean-wangchanberta-fullcontext-20261010-pilot1` | `63fab874b87bdc27d10b3a534882e6fb490139d1a795a8eeb3c05cd9d48fb1ee` | `26f16ad5e890540968ef9ad5e880009c9308c20fd2eaa34da4acdeead2727dc4` | completed; 2 updates; 0 epochs |

Each run selected the 32 longest marked conversations from the fold-0 training pool and evaluated the saved fold-0 validation set (`n=233`) for both role-marked and role-free input. The outcomes were identical across all four pooling/marker combinations:

| Pooling / validation markers | Train loss | Validation loss | Precision | Recall | Scam F1 | Macro F1 | Accuracy | TN | FP | FN | TP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Max / role-marked | 0.5526 | 1.2584 | 0.4764 | 1.0000 | 0.6453 | 0.3227 | 0.4764 | 0 | 122 | 0 | 111 |
| Max / role-free | 0.5526 | 1.1413 | 0.4764 | 1.0000 | 0.6453 | 0.3227 | 0.4764 | 0 | 122 | 0 | 111 |
| Mean / role-marked | 0.5388 | 1.2846 | 0.4764 | 1.0000 | 0.6453 | 0.3227 | 0.4764 | 0 | 122 | 0 | 111 |
| Mean / role-free | 0.5388 | 1.1580 | 0.4764 | 1.0000 | 0.6453 | 0.3227 | 0.4764 | 0 | 122 | 0 | 111 |

All 233 validation records were predicted Scam after only two updates. These metrics are not meaningful final performance and must not be interpreted as evidence of model quality or used to select a pooling method.

| Pooling | Total elapsed | Training loop | Peak RSS | CUDA allocated / reserved | `latest.pt` bytes | `latest.pt` SHA-256 |
|---|---:|---:|---:|---:|---:|---|
| Max | 47.1 s | 23.1 s | 3.60 GiB | 2.22 / 2.24 GiB | 1,263,382,347 | `d4a69178d9e4a8262d1602a1921d40a49ed9fa5ec6f5caf3957c7fda3c79758f` |
| Mean | 41.0 s | 20.6 s | 3.53 GiB | 2.22 / 2.24 GiB | 1,263,382,347 | `bdf9121b4bdd1c9c986f98d7bd9e0beb8fa2f8d89da144e5d8de02a8b1d72ea1` |

The passing verifier record is `/content/drive/MyDrive/scam-call-alert/model-development/comparison-slices/wangchanberta-fullcontext-20261010-pilot1/full-context-diagnostic-verification-1791581652896557595.json`, SHA-256 `895b1515e7c6ba9a8e546591a97e47f9172237b0a8613d7fdf4cb6606a9b2694`.

**Attempt history and validation.** The first launch attempt stopped before training because the comparison cell mutated nested approved profile settings through a shallow payload copy. The profiles were safely reloaded from Drive and revalidated; no run artifacts existed for that stopped attempt. After the local notebook deep-copy fix, both approved runs completed. The first evidence-verifier invocation then stopped on a missing `math` import; after adding the import, the verifier-only rerun passed. The local notebook source contains both fixes, and its 16 structure tests pass. Earlier fixed-prefix runs, checkpoint/restore failures, and publication probes remain preserved as historical evidence; they are not the current full-context diagnostic outcomes.

**Checkpoint boundary and next step.** Checkpoint 01's WangchanBERTa feasibility diagnostic is archived. Plan 03/00 remains `Planned`; no task status changed. At Checkpoint 01, comparative execution still required feasibility/budget and persistent-storage evidence, owner approval for comparative warmup and a finite maximum epoch budget, and explicit launch authorization. The later owner-authorized repair launch is recorded below; the original checkpoint evidence remains unchanged. Do not reuse these two-update scores for selection or open the held-out test set for tuning.

**Read-only Drive quota observation for CP02 preflight (2026-10-10).** In authenticated Chrome, the Google Drive Storage page at `drive.google.com/drive/quota` showed 9.75 GB of 5 TB used and 4.99 TB available account-wide. The page was opened read-only; no files or settings were changed. This is account-wide quota, not a per-folder measurement, and does not by itself satisfy the pilot's storage/capacity estimate. Model-only epoch snapshot sizes and total retention/rerun storage remain to be estimated after finite epoch and retry assumptions are approved. The current diagnostic `latest.pt` files are each 1,263,382,347 bytes, as recorded above.


## CP03 — FP16 overflow repair and first-configuration results (2026-10-10)

The first WangchanBERTa full-context FP16/T4 attempt stopped at update 35 in epoch 1 (about 68% of the epoch): loss was finite at 0.454, but gradients were nonfinite. The reviewed repair lets GradScaler lower its scale and retries the same accumulated group, restoring pre-group CPU/CUDA RNG state for replay. It records overflow evidence, advances counters only for actual optimizer steps, and caps retries at eight; nonfinite logits/loss still fail immediately. The local and Colab synthetic regression suites each passed 22 checks. In repaired fold 0, an overflow at update 89 in epoch 2 lowered scale from 65536 to 32768 and replayed the 16-conversation accumulation group; the fit then reached its target.

The selection verifier returned `verified_five_fold_epoch3` for configuration `wangchanberta__primary_only__lr-2e-05__pool-max`. Folds 0–4 each completed target epoch 3 of maximum 4; no epoch-4 extension was run. Settings and procedure: WangchanBERTa; primary-only training; role-marked, whole-conversation examples; learning rate 2e-5; seed 67; effective batch 16; three epochs; warmup equal to 10% of planned optimizer updates, rounded up; FP16 on a Colab T4; complete overlapping 508-content-token windows with stride 381 (127-token overlap); class-wise max pooling; and one unweighted cross-entropy loss per conversation. Each fold was validated on the saved paired role-free and role-marked conditions. Role-free is the selection condition; role-marked is diagnostic. The scam threshold is 0.5. The held-out test set was not accessed.

Epoch-3 validation covers the combined primary and supplemental validation records in each saved fold, even though training was primary-only. Counts below are from the frozen fold assignments and training labels: fold 0 n=233 (201 primary, 32 supplemental; 122 Not Scam, 111 Scam); fold 1 n=233 (202, 31; 122, 111); fold 2 n=233 (208, 25; 122, 111); fold 3 n=233 (201, 32; 122, 111); fold 4 n=232 (209, 23; 122, 110). Role-free Scam F1 by fold was 0.951965, 0.964912, 0.965217, 0.960699, and 0.960000 (mean 0.960559, sample SD 0.005358). Role-marked Scam F1 was 0.959276, 0.977578, 0.977974, 0.968889, and 0.977376 (mean 0.972219, sample SD 0.008171). Role-marked supporting aggregates (mean ± sample SD) were macro-F1 0.973324 ± 0.007689, accuracy 0.973372 ± 0.007662, training loss 0.000999 ± 0.000257, and validation loss 0.056321 ± 0.017067. These are development validation results, not final-test estimates.

At the time this CP03 section was written, this was one of six WangchanBERTa primary-only configuration combinations (1/6), with five still to run; CP04 above records their later completion. It is not the complete WangchanBERTa comparison and does not establish a final model-selection result. Plan 03/00 remains `Planned`. The isolated repair evidence is at `/content/drive/MyDrive/scam-call-alert/model-development/comparison-slices/wangchanberta-fullcontext-20261010-pilot1/repairs/overflow-fix-20261010-v1`; verified epoch-3 exports are `evidence/results-epoch3/epoch3_cv_results.json` and `evidence/results-epoch3/epoch3_cv_results.md` within that directory. Per-run config/history/prediction hashes are recorded in the JSON export and summaries. The fresh source ZIP SHA-256 is `28c16846a4957b9129595886c5e24fb016c95eb5fdb2538cec5b1b8057f75c9f`; trainer SHA-256 is `49753b7d6c1a9465c4e5434fbb43a6da9e0c152f82136f2244a66eb9578fcb24` (prior approved trainer `9ab71c8662be36eb9766ef4f7110364071d6fa93ad43cd34e1d20f455f8c6a37`). The verifier status applies only to this five-fold epoch-3 configuration. Earlier failed attempts and their evidence remain preserved.

**Owner-approved comparison-scope revision (2026-10-10).** Compare all four candidates using primary-only training first. WangchanBERTa retains its two pooling methods, three learning rates, and five folds (30 fold fits); the other three candidates use the approved three learning rates and five folds each (45 fold fits), for 75 primary-only fits. After selecting the best-supported candidate/configuration from those results, run one matched primary + supplemental comparison for that candidate/configuration across the same five folds (five additional fits; 80 total before retries/extensions). Hold the selected settings and validation membership fixed and change only the training-data condition. Do not run supplemental comparisons for the other models or retune the supplemental condition. This means the possible benefit of supplemental data for the three unselected candidates remains unknown. The completed configuration above is 1/6 of the WangchanBERTa primary-only portion of this revised plan. At the time of this CP03 note, the prior selection implementation still needed updating before further configs were generated. This historical statement is superseded by CP04: the tracked search space now represents the primary-only sequence, while its legacy manifest/import commands must not be rerun against current results. See the current status section at the top of this report.

## WangchanBERTa full-context implementation (2026-10-10)

Implemented a separate reusable development path for the owner-approved full-context WangchanBERTa comparison. It reads only Plan 02's manifest-bound training-pool `training_text.csv`, verifies selected rows' source, label and fold by `sample_id`, applies the frozen Wangchan text preparation, and creates complete 508-content-token windows at stride 381 with independently added special tokens. It retains one label and fold per conversation. The training runner pools each conversation's two raw logits by the configured class-wise `max` or arithmetic `mean`, then applies one unweighted cross-entropy per conversation. The effective batch remains 16 conversations. Run identity records per-conversation chunk/token counts and pooling/window settings; validation predictions carry chunk count, content-token count and timed inference. A selection utility reports metrics, errors, failures and runtime by chunk count.

The earlier one-time fixed-prefix diagnostic and its restore investigation remain historical evidence. Separately, the owner-approved full-context max/mean two-update feasibility diagnostics have now completed and are archived below. They establish that both pooling paths execute under the bounded diagnostic settings; they are not CV comparisons, model selection, or a completed training schedule. As of Checkpoint 01, no comparative 60-fit pilot had run. The subsequently launched repair configuration is documented below.

The implementation addresses the documented prefix exposure (Plan 03/00: 209/1,164 marked whole-conversation training records exceed 510 tokens: 204/510 primary Scam, 5/511 primary Not Scam and 0/143 supplemental; estimated 11,865 removed content tokens, of which 11,723 are primary Scam). These figures quantify exposure to truncation, not semantic loss or predictive impact. The window choice uses 508 content tokens plus two special tokens and quarter-window overlap (127 tokens); it is a project policy to compare, not an established optimum. Max pooling is motivated as one candidate for localized evidence and mean pooling as its smoothing alternative; neither is presumed superior. The bounded two-update feasibility diagnostics are summarized at the top of this report. At Checkpoint 01 they did not constitute comparative CV results or establish whole-schedule capacity. CP03 below records verified epoch-3 results for one five-fold configuration; it is 1 of 6 WangchanBERTa primary-only configuration combinations, not the full cross-candidate comparison or a model-selection conclusion.

The pilot is currently WangchanBERTa-only. Other candidates retain their approved Plan 02 prefix inputs pending their own length review and owner approval. No LSTM was added. The five caller-only fits are inactive following owner approval on 2026-10-10; Plan 02 caller-only preparation evidence remains unchanged.

## State

**Owner-approved policy update (2026-10-09):** The attempted mid-epoch recovery did not become a working/verified implementation path: `latest.pt` was unreadable, `previous.pt` ended at the diagnostic slice's final cursor, same-run resume failed, and a follow-up restore-only smoke returned an error. The owner decided to drop mid-epoch recovery for this project. Preserve every failed/interrupted attempt's partial metrics, predictions, timing/resource readings, logs and summary, then rerun the full fit from fresh initialization with the same approved settings/data membership and a new run ID. The earlier proposal and failure evidence remain below for traceability. Each current training attempt now records flushed scalar progress after optimizer updates and complete/partial epoch evidence; retries use a new run ID and preserve the previous attempt. Only a separately approved epoch extension after a successfully completed target may continue from its verified epoch-end state. This policy does not discard or combine training histories.

Reusable training code and configuration/artifact schemas are implemented. The first real WangchanBERTa attempt stopped during pretrained-key validation before any optimizer update. After a narrowly scoped compatibility patch passed its 14-test Colab regression suite, the earlier fixed-prefix diagnostic completed exactly two optimizer updates; its then-required same-run restore smoke failed because `checkpoints/latest.pt` was not a readable PyTorch ZIP archive. That restore issue is historical and no longer blocks Checkpoint 01. The newer full-context max/mean diagnostic pair and its actual outcomes are recorded in the current section at the top of this report. A later read-only `torch.load` of `previous.pt` fully deserialized it, matched its `run_identity` to the saved `run_config.json`, and found the required recovery fields: 2 optimizer updates, epoch 1, incomplete epoch, 201 model tensors, and 201 optimizer state entries. The read-only result was saved and read back from Drive as `previous_checkpoint_load_verification.json` (SHA-256 `23224e6195878bd2acc4df44c475b3d68c1c44348c88ee63aad0d1675dffd8ab`); the inspected `previous.pt` SHA-256 is `e6c0c958664a95aa5472d07f9471ce25d0c1333cca6281b7b7ccdf73d08a0e5b`. This establishes that the previous slot contains a structurally complete checkpoint for this run, but no trainer resume or model/optimizer state application succeeded, and no persistent-runtime restart was tested. The completed pre-restore summary, failed post-restore summary, checkpoint hashes, inspection evidence, and restore error are preserved in the persistent Drive run directory and ignored local session checkpoint. Plan 03/00 remains `Planned`. The restore failure is no longer a gate; the two-update diagnostic is not evidence that the full training schedule completed.

## Implemented procedure

- Reuses saved split assignments and Plan 02's verified prepared exports. Training entry points do not call the test loader.
- Supports fresh two-class sequence-classification initialization for each candidate, rejects incomplete/mismatched pretrained backbone loads, and records load diagnostics with run-specific evidence.
- Implements unweighted cross-entropy, AdamW parameter groups, explicit schedule/precision configuration, effective-batch-preserving accumulation, frozen `inputs.pad_batch` enforcement, paired marker-condition validation, per-update scalar progress logging, per-epoch history/prediction recording, and resource snapshots. Mid-epoch recovery writes and failed-run resume are disabled. Checkpoint state is saved only at completed epoch boundaries for an explicitly approved extension after successful completion. Synthetic tests verify fresh-rerun guards and progress preservation; they do not establish recovery from an interrupted fit.
- Supports final full-training-pool mode without validation-based selection or test access.
- Keeps run evidence under an ignored `runs/` location configured by the owner for persistent storage.

## Required owner/runtime gates

**Historical prelaunch gate context.** The requirements and no-start language in this section describe the state before the CP03 repair execution. CP03 supersedes the no-start status only for `wangchanberta__primary_only__lr-2e-05__pool-max`, which completed its five folds at epoch 3. Under the owner-approved 2026-10-10 scope revision, five WangchanBERTa primary-only configurations remain, followed by primary-only comparisons for the other three candidates and one selected-candidate supplemental-data comparison. These stages remain subject to their applicable approved gates; this result does not authorize changed methods or settings.

### Mounted-Drive probe update

A historical same-session mounted-Drive probe verified a scratch copy and publication/readback of `previous.pt`, but it did not test trainer resume or runtime restart/remount. That recovery probe is retained as historical evidence only and is not an active gate. The owner does not require another model launch solely to repair the post-run restore smoke; review the preserved completed diagnostic evidence against Checkpoint 01's revised gate. Plan 03/00 remains `Planned`.

1. The owner-approved full-context max and mean diagnostics each completed exactly two optimizer updates using training-only records. The Colab T4 runtime and mounted Drive storage were verified. Their profile, input, run, metric, timing, memory, checkpoint and verification-record identities are listed at the top of this report. These are execution-feasibility diagnostics only, not CV comparisons or model selection. The earlier restore smoke failure remains historical evidence and is not a current gate.
2. Verify frozen input/configuration/assignment identities at run start. The class-specific truncation report above already uses training-pool evidence; include it and measured runtime/storage in the owner-reviewed budget report before comparative training.
3. For all four candidates, measure pinned model/tokenizer loading, representative long-input forward/loss/backward/update, memory/runtime, precision stability, and persistent readback/integrity of required run outputs and model snapshots. Trainer restoration of an interrupted fit is not required. HPLT custom implementation compatibility is unverified.
4. For comparative execution, resolve the exact warmup amount and finite maximum epoch budget and obtain approval of the combined time/storage estimate before launching the matrix.

No model-specific retention/storage measurement has been made. Available Drive capacity must be measured; do not assume it is adequate for epoch snapshots, state needed for an approved planned extension, histories/predictions or final artifacts. Measure actual serialized sizes/write overhead and confirm persistent retrieval before approving the matrix. Include practical fresh-rerun overhead in the time estimate.

For the remaining comparative configurations, do not launch until their applicable gates pass; do not change full fine-tuning or candidates. Do not use the two-update diagnostic scores for selection. Their observed predictions and metrics are retained below as execution evidence only; do not infer results from package availability or model cards.

## Training-pool marked whole-conversation truncation exposure

Source: `token_length_report.json`; population 1164; scope: Full training pool only. No final-test file is loaded.

Affected count is the number of records exceeding the fixed input budget. Token loss is the report's estimated dropped content tokens, not semantic or predictive loss.

| Model | Source/class | Records | Affected count | Affected (%) | Estimated dropped content tokens |
|---|---|---:|---:|---:|---:|
| wangchanberta | primary:Scam | 510 | 204 | 40.00% | 11723 |
| wangchanberta | primary:Not Scam | 511 | 5 | 0.98% | 142 |
| wangchanberta | supplemental:Scam | 44 | 0 | 0.00% | 0 |
| wangchanberta | supplemental:Not Scam | 99 | 0 | 0.00% | 0 |
| phayathaibert | primary:Scam | 510 | 153 | 30.00% | 7185 |
| phayathaibert | primary:Not Scam | 511 | 3 | 0.59% | 63 |
| phayathaibert | supplemental:Scam | 44 | 0 | 0.00% | 0 |
| phayathaibert | supplemental:Not Scam | 99 | 0 | 0.00% | 0 |
| hplt | primary:Scam | 510 | 5 | 0.98% | 130 |
| hplt | primary:Not Scam | 511 | 0 | 0.00% | 0 |
| hplt | supplemental:Scam | 44 | 0 | 0.00% | 0 |
| hplt | supplemental:Not Scam | 99 | 0 | 0.00% | 0 |
| xlmr | primary:Scam | 510 | 140 | 27.45% | 5618 |
| xlmr | primary:Not Scam | 511 | 1 | 0.20% | 22 |
| xlmr | supplemental:Scam | 44 | 0 | 0.00% | 0 |
| xlmr | supplemental:Not Scam | 99 | 0 | 0.00% | 0 |

These are record fractions and token-count estimates, not fractions of spoken content lost or measured prediction damage. The fixed-prefix policy remains as approved. Do not inspect or load held-out test transcripts for this report.

## Verification performed

- The current offline suite passed **61 tests and 11 subtests** across the training runner, selection runner, Colab notebook structure, and related regressions. It verifies per-update progress records, the actual LR used before scheduler advancement, partial epoch evidence on a caught interruption, atomic attempt-state writes, rejection of failed-run resume, fresh-retry and stale-running guards, approved completed-epoch extension behavior, selection artifact handling, and notebook structure. These are synthetic/local checks; they do not establish a Colab restart/resume or real interrupted-fit recovery.
- Before the current full-context run, four fixed-prefix diagnostic config files were generated in temporary test storage and validated against the explicit owner-approved settings digest. That earlier preflight created no project run folder; it is historical and separate from the completed full-context runs recorded above.
- The first WangchanBERTa attempt loaded the pinned checkpoint and failed before optimizer updates because the loader rejected the checkpoint's expected masked-LM head. The narrowly scoped compatibility patch passed 14 Colab regression tests. The historical fixed-prefix diagnostic completed two optimizer updates, but its then-required restore smoke could not load `latest.pt`. The separate full-context max/mean diagnostic pair later completed and is documented in the current checkpoint section above. A subsequent read-only `torch.load` of `previous.pt` succeeded and its identity matched the run config; it reports 201 model tensors and 201 optimizer state entries. The read-back verification record `previous_checkpoint_load_verification.json` has SHA-256 `23224e6195878bd2acc4df44c475b3d68c1c44348c88ee63aad0d1675dffd8ab`, and the inspected checkpoint has SHA-256 `e6c0c958664a95aa5472d07f9471ce25d0c1333cca6281b7b7ccdf73d08a0e5b`. No trainer state application, successful resume, or persistent-runtime restart has been demonstrated. No final-test transcript content was loaded. See the ignored session note and persistent run artifacts for both attempts, patch provenance, summaries, hashes, inspection evidence, and restore failure. The revised publisher/fallback code has passed synthetic local checks only; its recovery behavior remains historical implementation evidence, not an active project requirement. Plan 03/00 remains `Planned`; this WangchanBERTa feasibility checkpoint does not satisfy all plan completion criteria or authorize other candidate diagnostics.
