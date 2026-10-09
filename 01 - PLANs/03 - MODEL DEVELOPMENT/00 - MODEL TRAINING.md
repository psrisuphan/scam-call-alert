# 00 - MODEL TRAINING

## Purpose and scope

Implement a reproducible procedure for fine-tuning the four candidate models using the approved partitions and input-preparation pipeline.

This task covers initialization, classification loss, optimizer, batching, precision, training and validation execution, progress recording, planned epoch extension, and interruption handling. Hyperparameter search, experiment comparisons, selection rules, final test evaluation, and application packaging belong to later plans.

## 1. Inputs and prerequisites

Read and consume the outputs of:

- [Data Preparation](../00%20-%20DATA%20PREPARATION.md): audited labels, provenance, and source-format findings.
- [Data Split and Experiment Design](../01%20-%20DATA%20SPLIT%20AND%20EXPERIMENT%20DESIGN.md): saved partitions, folds, and training data conditions.
- [Data Preprocessing and Model Inputs](../02%20-%20DATA%20PREPROCESSING%20AND%20MODEL%20INPUTS.md): shared component and approved input configuration.

Required implementation inputs:

```text
02 - DATASETs/prepared/
├── preparation_report.md
├── record_audit.csv
└── splits/
    ├── 0 - train/dataset.csv
    ├── split_assignments.csv
    └── split_report.md

03 - MODEL DEVELOPMENT/input-preparation/
├── README.md
├── preprocessing_config.json
├── preprocessing_report.md
└── Shared input-preparation component
```

Verify preceding completion checks and resolve documented source-role parsing and length-policy checkpoints. Review actual class counts for each applicable training subset.

Develop the training component and perform feasibility checks using an explicitly owner-approved diagnostic configuration. Its numeric settings remain an implementation confirmation checkpoint; do not guess them or rely on undocumented defaults. Diagnostic scores must not select the model.

Comparative experiments require approved configurations and comparison rules from the later Hyperparameter Tuning and Model Selection plan. This avoids requiring the completed tuning task before implementing its reusable training procedure.

Do not load the final test set in this task.

## 2. Outputs

```text
03 - MODEL DEVELOPMENT/
└── training/
    ├── README.md
    ├── training_report.md
    ├── Shared training component
    └── runs/
        └── <run_id>/
            ├── run_config.json
            ├── environment.json
            ├── training_history.csv
            ├── validation_predictions.csv
            ├── run_summary.json
            ├── run_attempts.jsonl
            ├── attempt_failures.jsonl
            ├── attempt_evidence/
            │   └── <attempt_id>/
            │       ├── attempt_state.json
            │       ├── optimizer_progress.jsonl
            │       ├── training_history.csv (when failure is caught)
            │       └── validation_predictions.csv (when failure is caught)
            └── checkpoints/
```

| Output | Purpose |
|---|---|
| `README.md` | Explain configuration, starting, intentionally extending, and inspecting runs; document interruption handling, persistent storage, and retention. |
| `training_report.md` | Record feasibility findings, checks, failures, and owner-approved implementation adjustments. |
| Shared component | Execute the training/validation procedure for supplied configurations; code filenames and libraries remain flexible. |
| `run_config.json` | Preserve resolved settings, checkpoint revisions, preprocessing identity, dataset/assignment checksums, and actual training/validation membership identity. |
| `environment.json` | Record actual hardware, runtime/OS, package versions, device backend, precision, and reproducibility settings. |
| `training_history.csv` | Store completed-epoch or diagnostic-limit training loss, configured validation metrics, learning rate, optimizer-update/sample counts, timing, resource snapshots, and model-snapshot references. |
| `validation_predictions.csv` | Preserve sample-level probabilities and true labels at each evaluation point for later comparisons. |
| `attempt_evidence/<attempt_id>/optimizer_progress.jsonl` | Append and flush scalar progress after every optimizer update: epoch progress fraction (`conversations_processed_in_epoch / training-record count`), update counts, conversations processed, training loss to date, actual learning rate, elapsed time, and resource snapshots. Include the final partial accumulation group. The fraction lets reviewers inspect progress around points such as 0.1, 0.2, and 0.3 epoch at the nearest actual optimizer update; do not interpolate missing points. It contains no model or optimizer state and is not a recovery checkpoint. |
| `attempt_evidence/<attempt_id>/attempt_state.json` | Track whether an attempt is running or ended, its target, and last completed epoch so an abrupt runtime loss remains identifiable. For the latest optimizer update before an abrupt loss, use the flushed `optimizer_progress.jsonl`; a still-running record does not authorize resumption. |
| `attempt_evidence/<attempt_id>/training_history.csv` and `validation_predictions.csv` | When a fit fails or is interrupted and Python can finalize the attempt, preserve its partial history and available validation predictions without overwriting evidence from another attempt. Completed epochs remain in the run-level files. |
| `run_summary.json` | Distinguish completed, interrupted, and failed runs; record progress, timing, artifact locations, and reasons. A process that terminates abruptly may remain marked as running; use its flushed progress log and last completed epoch as evidence, and do not invent a termination cause. |
| `run_attempts.jsonl` and `attempt_failures.jsonl` | Append per-invocation summaries and startup/load failures so approved epoch extensions and failures remain traceable. |
| `checkpoints/` | Hold verified epoch-end state only for explicitly approved epoch extensions and model snapshots required for duration selection. Failed or interrupted fits are not resumed. |

Assign each independent run a unique ID; never overwrite another run. Record model, data condition, training representation/marker condition, validation representation/marker conditions, fold, seed, classification-head settings, optimizer parameter groups, and all resolved training settings in the configuration. A membership checksum may identify saved ordered sample-ID lists, but the actual membership must remain recoverable.

Keep generated `training/runs/` contents outside Git, including prediction CSVs and JSON logs, not only model weights. Add the appropriate ignore rule during implementation. Track reusable code and human-readable documentation; store large artifacts in documented persistent storage.

## 3. Environment and feasibility

Prefer **Google Colab Free**; use local computing as the fallback after compatibility, memory, and runtime checks.

Available local devices:

- PC: RX 6600 XT, 8 GB VRAM, 24 GB system memory, Windows/Linux.
- MacBook Air M2: 8 GB unified memory.
- Lenovo laptop: Ryzen AI 7 CPU; remaining specifications are not established.

Do not assume a specific Colab GPU or uninterrupted session. Record actual resources. Keep required epoch snapshots and run evidence outside the temporary runtime and verify persistent access.

For each candidate, use training-only records to:

1. Load the pinned checkpoint and matching tokenizer.
2. Prepare inputs using the approved policy, including representative long inputs within that policy.
3. Complete forward, loss, backward, and optimizer-update operations.
4. Check finite loss, valid outputs, memory use, and processing time.
5. Verify the integrity and persistent readback of the run outputs and required model snapshots. Any state restoration is limited to an explicitly approved epoch extension after the prior target completed successfully; it is not used to continue an interrupted fit.

Diagnostic states must not initialize comparative runs. Feasibility checks assess execution, not predictive superiority. Full fine-tuning remains conditional on these checks; if infeasible, document the issue and obtain an agreed resolution before experiments or task completion.

## 4. Candidate checkpoints

| Candidate | Confirmed checkpoint |
|---|---|
| WangchanBERTa | `airesearch/wangchanberta-base-att-spm-uncased` |
| PhayaThaiBERT | `clicknext/phayathaibert` |
| HPLT 3.0 GPT-BERT Thai | `HPLT/hplt_gpt_bert_base_3_0_tha_Thai` |
| XLM-RoBERTa-base | `FacebookAI/xlm-roberta-base` |

Resolve and record exact revisions before experiments; reuse each candidate's revision and matching tokenizer across runs. Use compatible sequence-classification implementations with two output scores. Record the classification-head architecture/settings rather than assuming heads are identical across candidates.

HPLT requires its documented custom implementation; verify compatibility and record the code revision. Checkpoint-specific preparation remains governed by Plan 02. Do not substitute a checkpoint or an unrelated task-fine-tuned variant without confirmation.

## 5. Retrieve records and prepare inputs

For fold `k`, use saved fold `k` for validation and the other four for training. Apply the primary-only or primary + supplemental training condition exactly as Plan 01 specifies; both use the same validation records.

Main runs train on `whole_conversation` + `role_marked`; the limited caller-only comparison trains on `caller_only` + `role_marked`. Source roles must follow Plan 02 approval rules. Consume its formatting, tokenizer, length and padding instructions without redefining them.

Fit any approved data-derived transformation only on eligible fold-training records. Apply its frozen state to validation. Preserve IDs as separate traceability metadata; never include IDs, source categories, or labels in predictive text.

Do not regenerate folds. The tuning plan determines the executed model/data/representation combinations and comparison budget.

### Class-specific length exposure

Before comparative training, verify the authoritative training-only length report/configuration identities and report marked whole-conversation truncation by model, source and class. At the reviewed fixed limits, the current report shows primary Scam affected-record rates of 40.00% (WangchanBERTa), 30.00% (PhayaThaiBERT), 0.98% (HPLT), and 27.45% (XLM-R), versus approximately 0–1% for primary Not Scam. These are record fractions, not fractions of spoken content lost or measured prediction damage; role-free training-pool whole conversations fit the current limits.

Retain the approved marked training and fixed-prefix policy. Record this as an explicit methodological limitation, not proof that the policy is optimal. Present the class-specific exposure in the owner-reviewed diagnostic/budget report before comparative training. Record affected counts and retained/dropped token estimates in the feasibility report; inspect only training-pool evidence. Do not regenerate finished input artifacts, change markers/budgets, or add role-free-training experiments without separate approval. Report marker-removal and caller comparisons as potentially confounded by retained content, as the selection plan already requires.

If the approved length policy uses multiple windows per conversation, resolve training-label handling, loss weighting, and conversation-level aggregation with the owner before training. Window construction belongs to Plan 02. Do not independently split windows or assume every window contains evidence for the conversation label.

## 6. Initialize independent runs

For each new fold, configuration, or repetition:

1. Set and record the training seed before model initialization and data-loading randomness.
2. Reload the original pretrained checkpoint.
3. Initialize a fresh two-class head.
4. Create fresh optimizer and configured scheduler state.
5. Fit any approved learned preprocessing on that run's eligible training subset.

Use **67 as the initial training seed**, recorded separately from split seed 67. The component accepts other seeds; repeat counts and seed comparisons belong to the tuning plan.

Never carry learned weights, optimizer state, or fitted transformations between independent runs. A planned epoch extension may continue from its same run's verified epoch-end state only when the preceding approved target completed successfully and the extension is authorized by Plan 03/01. If a fit fails or is interrupted before its approved target completes, preserve that attempt and its evidence, then rerun the full fit from the original pretrained checkpoint with a fresh head, optimizer, scheduler, scaler, and random state, using a new run ID and the same approved configuration and data membership. Do not resume the failed/interrupted fit. Record deterministic settings and unavoidable limitations; identical numerical results across environments are not guaranteed.

## 7. Full fine-tuning

Train the pretrained transformer weights and fresh classification head. Frozen encoders and parameter-efficient adaptation are alternatives, not the confirmed initial method.

If full fine-tuning is infeasible, seek confirmation before changing adaptation methods or removing candidates.

## 8. Classification loss

Use **unweighted cross-entropy** on the two raw class scores, with `Not Scam = 0` and `Scam = 1`.

The lecture's binary cross-entropy expression is:

\[
L=-\frac{1}{n}\sum_{i=1}^{n}\left[y_i\log(p_i)+(1-y_i)\log(1-p_i)\right]
\]

Here `y_i` is the true binary label, `p_i` is the predicted Scam probability, and `n` is the number of conversations averaged. Two-class softmax gives `P(Not Scam) = 1 - p_i`, so ordinary cross-entropy has the same per-sample expression.

Use a numerically stable implementation accepting raw scores; do not manually log rounded probabilities. Average reported classification losses by conversation count, including smaller final batches.

Initially use no class weights. Review actual training-subset counts after preparation. If exclusions materially change balance, obtain confirmation before changing the loss. Any approved frequency-derived weights use only the applicable training subset.

## 9. AdamW optimization

Use **AdamW** for all candidates. Its weight decay discourages large weights, connecting to lecture regularization, but differs from adding an L2 penalty to the loss:

- L2 adds a squared-weight penalty to the objective.
- AdamW applies weight decay separately from the loss-gradient update.

These are not equivalent under Adam. Do not add the lecture's L2 term automatically on top of AdamW.

The tuning plan supplies learning rate, weight decay, scheduler policy, and other required settings. Record resolved values and exactly which parameters receive decay. The approved diagnostic configuration supplies these values for feasibility checks.

## 10. Batching and gradient accumulation

Shuffle training records each epoch using the recorded random state. Use deterministic validation retrieval. Do not augment, oversample, or undersample. Apply Plan 02's dynamic padding.

Allow gradient accumulation when the intended batch does not fit directly. On one device, for full accumulation groups:

\[
B_{\mathrm{effective}}=B_{\mathrm{microbatch}}\times A
\]

`A` is the accumulation-step count. Record all three values.

- Normalize gradients by the actual number of conversations in the accumulated group.
- Process the final incomplete group without dropping records or misweighting its loss.
- Update the optimizer after the group; advance a configured scheduler according to optimizer updates, not microbatches.
- Preserve the configured effective batch size when adjusting microbatch size for memory.

If preservation is impossible, discuss the change rather than silently modifying the experiment. Accumulation does not promise numerically identical results to a single larger batch. Effective batch-size candidates belong to tuning.

## 11. Numerical precision

Resolve during feasibility checks:

1. Prefer BF16 mixed precision when supported by hardware and model.
2. Otherwise use stable FP16 mixed precision with gradient scaling.
3. Use FP32 when mixed precision is unsupported or unstable.

Record precision/scaling settings and resolve numerical failures before comparisons. Keep the resolved policy consistent for repeated runs of the same setup; disclose necessary model/environment differences. Precision is distinct from learning rate and is not selected by test scores.

## 12. Training and validation execution

For each epoch:

1. Train on the eligible fold-training records.
2. Record training loss and progress.
3. Validate in evaluation mode without gradients or parameter updates.
4. Evaluate the same frozen epoch weights on corresponding marked and role-free validation text; record loss, metrics and probabilities separately. No updates occur between conditions.
5. Save and verify the epoch-end model snapshot required for duration selection. Save epoch-end training state only when needed for an explicitly approved Plan 03/01 epoch extension; do not create or use within-epoch recovery state as an interruption fallback.

Validation must not update model weights, optimizer state, or fitted preprocessing. Produce one conversation-level prediction per validation record per marker condition per evaluation point; reject missing/duplicate IDs within each condition and non-finite probabilities. Role-free whole-conversation scores govern main selection; marked scores are diagnostic.

The tuning plan owns epoch limits, metric definitions, early stopping, and checkpoint-selection rules. This component executes those rules. Diagnostic validation may record loss/probabilities without ranking configurations.

## 13. Progress for reporting

`training_history.csv` records training representation/marker condition and validation representation/marker condition, epoch, evaluation point, optimizer-update count, conversations processed, training/validation loss, configured metrics, learning rate, elapsed time, resource snapshot, and model-snapshot reference. Distinguish partial progress from a completed-epoch aggregate; do not label an incomplete epoch as complete. The per-attempt JSONL progress log records flushed scalar progress after each optimizer update, including the fraction of the training epoch processed, cumulative epoch training loss, processed conversations, actual learning rate, elapsed time, and resource readings. The fraction is measured at actual optimizer-update boundaries, so a requested decile is represented by its nearest logged update without interpolation. This log gives within-epoch training progress; validation metrics remain at their configured evaluation points. It contains no model/optimizer state, sample text, or labels.

`validation_predictions.csv` records run ID, training representation/marker condition, validation representation/marker condition, evaluation point, sample ID, source identity, true label, and both class probabilities. Preserve these records and history for later learning curves and comparisons.

Retain each failed/interrupted attempt's summary, per-update progress log, completed and partial epoch history, available validation predictions, logs, resource measurements, and failure reason under its unique run ID and attempt ID. On an abrupt runtime loss, the last flushed progress and completed-epoch history remain available even if Python cannot write a terminal failure reason. A model snapshot is not automatically the selected best checkpoint.

## 14. Interruption handling, planned extensions, and retention

### Current owner-approved interruption policy

Do not resume a fit that failed or was interrupted before its approved target completed. Preserve its run configuration, environment, flushed per-update progress, completed and partial epoch history, available validation predictions, summary, logs, resource readings, and failure/interruption reason; start a full fresh fit from the original pinned pretrained checkpoint using a new unique run ID, fresh model head and training state, and the same approved settings and data membership. Keep the failed attempt visible in reports, but do not score it as a completed run or overwrite it. If the runtime disappears before a terminal status can be written, retain the attempt as `running`, inspect its available progress evidence, and record the termination cause only when supported by runtime evidence.

This policy was approved by the project owner on 2026-10-09 after implementation attempts failed to verify a usable mid-epoch continuation and consumed substantial project time. In the recorded diagnostic, `latest.pt` was unreadable, `previous.pt` had no remaining batches, the same-run resume failed, and a follow-up restore-only trainer smoke returned an error. Therefore, mid-epoch recovery is not a working/verified implementation path for this project and is dropped from the active workflow. This is a project feasibility/time decision, not a claim that recovery is universally impossible. A successful fit may use its verified epoch-end training state for a separately approved, planned epoch extension under Plan 03/01. That planned extension is not interruption recovery. Keep epoch model snapshots needed for duration selection and verify their identities/checksums. Persistent storage is required for run evidence and planned snapshots, but a mid-epoch state-restore test is not a completion gate.

### Original proposed recovery procedure (superseded; retained for traceability)

Save after every epoch. Use periodic within-epoch recovery when needed for Colab interruptions; choose and record the interval based on measured runtime, not predictive scores.

Recovery state includes:

- Model weights/configuration and any fitted preprocessing state.
- Optimizer and configured scheduler state.
- Precision-scaling state where applicable.
- Random states, epoch, optimizer-update count, and supported data-order position/state.
- Run configuration and input identities.

Save at completed optimizer-update boundaries unless pending accumulated gradients are also preserved. Verify configuration, assignments, preprocessing, and runtime compatibility before restoring.

If exact mid-epoch recovery is unsupported, restore the last complete epoch and document repeated work; never silently skip records. Record environment changes; recovery across different hardware need not reproduce an uninterrupted run exactly.

Verify each new recovery checkpoint before replacing the previous one. Saving every epoch does not require retaining every large recovery checkpoint forever. Retain additional model checkpoints according to later selection rules, while preserving history and predictions. Recovery retention must never delete artifacts required for selection.

### Historical diagnostic recovery investigation

The owner-approved WangchanBERTa diagnostic run `diagnostic-wangchanberta-owner-approved-retry-20261009T104528Z-1791542728829738267` could not verify continuation of unprocessed training batches because neither available checkpoint provided a usable mid-epoch recovery case. The diagnostic used 32 training records and a two-update cap with an effective batch size of 16, so both updates consumed the entire diagnostic slice. Its `latest.pt` failed checkpoint-container verification (`BadZipFile`), and the same-run resume attempt failed while loading that file. A follow-up `--restore-only` trainer smoke also returned an error and produced no successful state-restoration report. The fallback `previous.pt` remained unchanged and passed read-only deserialization (`SHA-256: e6c0c958664a95aa5472d07f9471ce25d0c1333cca6281b7b7ccdf73d08a0e5`), but its saved progress was epoch 1, incomplete, cursor 32 of 32. It had no remaining batches to consume after restoration. The separate clone-based continuation check was not completed, so checkpoint readback and the Drive publication probe do not count as verified training resumption.

The recovery investigation could not produce a working continuation: the readable checkpoint had no remaining batches, and the latest checkpoint was unreadable. The failure applies to this implementation attempt; it does not establish that recovery is universally impossible. It records why the owner chose not to spend further project time pursuing the method. The original proposal above remains for traceability only and is superseded by the current interruption policy. The failed resume/restore probes are historical evidence and are not required to be repaired or repeated.

## Completion and handoff

Complete when all four candidates support the approved training procedure, required epoch snapshots and run evidence are traceable and persist, interruption handling follows the owner-approved fresh-run policy, documentation is sufficient, and checks establish:

- Saved folds, membership, source filters, and representations are respected.
- Independent runs initialize fresh state.
- Validation performs no learning; test records remain inaccessible to this workflow.
- Loss, optimizer, batching, precision, and input preparation follow approved instructions.
- Predictions, history, model snapshots, and artifacts are traceable and persist outside temporary runtimes.

Unresolved candidate infeasibility requires an agreed resolution before completion. No predictive score threshold or completed tuning search is required here.

Hand off the component, README, feasibility report, and artifact specification to Hyperparameter Tuning and Model Selection. Final evaluation reuses the procedure for selected final training; application packaging remains separate.

## References and rationale

- [Full Proposal](../../00%20-%20DOCUMENTs/Full%20Proposal/Phoebe_FullProposal.docx), sections 5-6.1 and 7.1: candidate models and training workflow.
- [L04 - Classical Machine Learning Models](../course-lecture-sheets/Pattern%20Recognition%20L04_Classical%20Machine%20Learning%20Models.pdf), PDF pp. 18-21: probabilities, BCE calculation, parameter updates, and regularization. This supports the concepts, not a claim that the lecture prescribes AdamW or transformer fine-tuning.
- [L05 - Model Selection and Hyperparameter Tuning](../course-lecture-sheets/Pattern%20Recognition%20L05_Model%20Selection%20%26%20Hyperparameter%20Tuning.pdf), PDF pp. 13-15, 29, 32-33, and 36: folds, resource budgets, train-only fitting, and selected final retraining before test evaluation.
- [L06 - Experimental Design and System Evaluation](../course-lecture-sheets/Pattern%20Recognition%20L06_Experimental%20Design%20and%20System%20Evaluation.pdf), PDF pp. 11-12 and 19: fair comparisons, variation across seeds, and reproducible records. Lecture materials remain local and ignored.
- [BERT paper](https://aclanthology.org/N19-1423/): pretrained adaptation with a task output layer; not evidence that full fine-tuning wins on this dataset.
- [AdamW paper](https://arxiv.org/abs/1711.05101): decoupled weight decay differs from L2 with Adam; its reported experiments do not establish superiority on this task.
- [Cross-entropy documentation](https://docs.pytorch.org/docs/2.14/generated/torch.nn.CrossEntropyLoss.html): stable loss from raw classification scores.
- [Gradient accumulation](https://huggingface.co/docs/accelerate/usage_guides/gradient_accumulation) and [mixed precision](https://docs.pytorch.org/docs/2.14/amp.html): resource-handling mechanisms; these specific techniques are supported by official documentation rather than explicitly prescribed in the cited lectures.
- [Colab FAQ](https://research.google.com/colaboratory/faq.html): variable resources and temporary runtimes.
- Official model cards: [WangchanBERTa](https://huggingface.co/airesearch/wangchanberta-base-att-spm-uncased), [PhayaThaiBERT](https://huggingface.co/clicknext/phayathaibert), [HPLT Thai](https://huggingface.co/HPLT/hplt_gpt_bert_base_3_0_tha_Thai), [XLM-RoBERTa-base](https://huggingface.co/FacebookAI/xlm-roberta-base).

Full fine-tuning offers task adaptation without introducing adapter design as another comparison variable, at higher memory cost than frozen encoders or parameter-efficient methods. Unweighted loss avoids unverified class/cost weighting; actual balance is reviewed before experiments. AdamW provides a common optimizer family while allowing model-specific values under later fair tuning rules. Accumulation and supported mixed precision address limited resources without silently changing the intended experiment. None guarantees better prediction scores.
