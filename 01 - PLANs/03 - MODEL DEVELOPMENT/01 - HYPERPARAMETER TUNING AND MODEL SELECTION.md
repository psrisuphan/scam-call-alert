# 01 - HYPERPARAMETER TUNING AND MODEL SELECTION

## Purpose and scope

Compare the four approved transformer candidates using **primary-only training** first, tune learning rate and training duration, and select the best-supported model/configuration using cross-validation evidence. After that candidate is selected, run one matched five-fold comparison for that candidate/configuration using primary + supplemental training to assess whether the supplemental data helps. Main training uses marked whole conversations; app selection uses role-free whole-conversation validation, with paired marked validation as a diagnostic. The WangchanBERTa comparison runs first; the other three candidates follow after its results and a candidate-specific length/input review.

This task owns initial-versus-tuned comparisons, primary-only cross-candidate comparison, a single post-selection primary-only versus primary + supplemental comparison for the selected candidate/configuration, configuration ranking, final candidate selection, and marker-removal diagnostics. The data-condition follow-up uses the same selected model, hyperparameters, folds, seed, validation membership, and common epoch as its primary-only baseline; it does not retune the supplemental condition. This time-bounded design does not establish whether supplemental data would help the other three candidates. The five caller-only training comparisons were dropped on 2026-10-10 because of the remaining project time; Plan 02 and its caller-only preparation instructions/artifacts remain unchanged. Record these implementation-time scope decisions in the training report and this protocol.

Reuse the existing training and input-preparation components. Do not redefine dataset membership, label mapping, tokenization, loss, or optimizer family. Final retraining and text-test evaluation belong to the next plan. Packaging, STT selection, application integration, and final system measurements remain separate.

## 1. Inputs and prerequisites

Use:

- [Plan 01](../01%20-%20DATA%20SPLIT%20AND%20EXPERIMENT%20DESIGN.md)'s saved training pool, fold assignments, and data conditions.
- [Plan 02](../02%20-%20DATA%20PREPROCESSING%20AND%20MODEL%20INPUTS.md)'s approved input-preparation component and configuration.
- [Model Training](00%20-%20MODEL%20TRAINING.md)'s reusable training component, diagnostic report, and run artifacts.
- The four approved checkpoints with pinned revisions.

Before comparative experiments, proceed in these stages:

1. For the WangchanBERTa primary-only slice, verify preceding completion checks and its source-role parsing, marker-condition, full-context windowing, execution, memory, runtime, output-integrity, and persistent-storage evidence. Obtain owner approval for the slice's exact warmup amount, finite maximum epoch budget, slice-specific time/storage budget, and launch authorization. This slice covers max and mean pooling, the three approved learning rates, and five saved folds. Record the scope and gates in `experiment_protocol.md`.
2. After the WangchanBERTa primary-only results are reviewed, inspect the other three candidates' training-only length evidence and input compatibility. Define and approve their input strategy before their comparisons; do not assume WangchanBERTa's window size or pooling rule applies to them. Compare all three using primary-only training and the approved learning-rate/fold procedure. Complete diagnostics and obtain owner approval of persistent capacity, combined time/storage feasibility, and launch authorization before those runs.
3. Select the best-supported candidate and configuration from the completed primary-only cross-candidate results. Then compare its existing primary-only CV results with exactly one matched primary + supplemental five-fold CV configuration. Keep model, learning rate, pooling/input method, seed, folds, validation membership, and common epoch fixed; change only the training-data condition. Do not run supplemental comparisons for the unselected candidates or retune the supplemental condition. Use this evidence to decide the selected candidate's final training-data condition, and document the limitation that the supplemental-data effect was not tested on the other candidates.

Neither stage authorizes changing the approved search grid or methods. WangchanBERTa-only results are preliminary and cannot select or freeze the final model. **Do not load the final test set during this task.**

## 2. Outputs and their purposes

Store selection artifacts under:

```text
03 - MODEL DEVELOPMENT/selection/
├── README.md
├── experiment_protocol.md
├── search_space.json
├── experiment_manifest.csv
├── cv_results.csv
├── comparison_report.md
└── selected_config.json
```

| Artifact | Purpose |
|---|---|
| `README.md` | Explain the files, run retrieval, comparison procedure, and persistent evidence locations. |
| `experiment_protocol.md` | Record questions, controls, approved budget, metric definitions, selection rules, checkpoints, and deviations. |
| `search_space.json` | Record searched values, fixed settings, approved epoch opportunities, and their rationale. |
| `experiment_manifest.csv` | Map each planned run to its configuration, training artifacts, execution state, failures, and append-only retry-attempt history. |
| `cv_results.csv` | Store per-fold, per-epoch metrics and aggregate results for completed comparable configurations. |
| `comparison_report.md` | Present comparisons, learning curves, variability, computational costs, selection rationale, and limitations. |
| `selected_config.json` | Freeze the selected model, data condition, training/inference representations and marker conditions, training settings, duration, threshold, and preprocessing policy. |

Keep training histories, sample-level predictions, and checkpoints in their existing training-run locations. Reference them rather than creating duplicate copies.

Generated sample-level evidence and model artifacts remain outside Git in documented persistent storage. Reusable instructions and suitable aggregate reports may be tracked.

### Required traceability

The experiment manifest identifies experiment ID, run ID, configuration ID, checkpoint/revision, training-data condition, training representation/marker condition, validation representation/marker condition, input/windowing policy, maximum content tokens, overlap, pooling method where applicable, fold, training seed, experiment purpose (initial reference or search), execution state, artifact location, and failure reason.

CV results identify configuration, data condition, training representation/marker condition, validation representation/marker condition, input/windowing policy, pooling method where applicable, per-conversation chunk counts, fold, epoch, evaluated subset, sample/class counts, metric values, undefined-metric flags, and timing. Aggregate rows must be distinguishable from individual-fold rows.

## 3. Experiment scope and budget

### Main comparison and staged execution

The primary cross-candidate comparison retains all four approved models, **primary-only training**, the three approved learning-rate candidates, five saved validation folds, seed **67**, and matched marked/role-free validation. The WangchanBERTa comparison adds two full-context aggregation variants: class-wise max pooling and class-wise mean pooling. Both train on role-marked whole conversations and validate on the same role-marked/role-free records. The supplemental condition is assessed only after primary-only candidate selection, on the selected candidate/configuration, in a paired five-fold comparison with the same settings and validation records.

The immediate WangchanBERTa matrix is:

```text
2 pooling methods × 1 training-data condition (primary-only) × 3 learning rates × 5 folds
= 30 independent training runs
```

Execute it in this order:

1. Run the WangchanBERTa slice first. Before launch, satisfy its feasibility, slice budget, exact warmup and finite epoch-budget approvals, persistent-storage checks, and owner launch authorization. This slice-specific approval does not establish whole-project feasibility.
2. Review and report the WangchanBERTa primary-only results as preliminary evidence. They cannot by themselves freeze/select the final candidate or establish cross-model superiority.
3. Review the remaining candidates' length evidence and agree their input policies, then complete their diagnostics and a combined feasibility/persistent-capacity review for the primary-only comparison. Only then run it.
4. Review the reconciled primary-only evidence and select the best-supported candidate/configuration through human review. After selection, run the matched supplemental-data five-fold comparison for that candidate/configuration only. Decide whether to use primary-only or primary + supplemental for final retraining based on this paired CV evidence, then freeze the final candidate and data condition. Do not use the supplemental follow-up to claim that other candidates would not benefit from supplemental data.

Within the WangchanBERTa primary-only pilot, both pooling variants use the same approved learning-rate grid, training procedure, epoch opportunities, and common-fold rules. Each pooling/learning-rate combination is an independent configuration, initialized from the original pinned checkpoint. Epoch extensions continue the matching run from its verified saved state; they are not separate configurations. Later models require their own reviewed input identity and primary-only run matrix before execution.

The primary-only candidate-ranking stage comprises 30 WangchanBERTa fold fits and 45 fits for the other three models when each uses the three approved learning rates and five folds (75 fits total). After one candidate/configuration is selected, the supplemental-data check adds five fits for that selected configuration (80 fits total before retries or approved epoch extensions). Candidate-specific diagnostics may reveal an input incompatibility; resolve it and record any approved scope impact before generating the affected configurations.

**Existing-tooling migration notice:** the current selection `search_space.json`, generated manifests, and selector/reporting implementation were built for the superseded all-model/two-condition matrix. They are not authorization to launch that matrix. Update and verify the implementation to generate the primary-only cross-candidate stage and the single post-selection supplemental comparison before preparing further configs. Preserve existing run evidence and do not regenerate frozen split assignments.

### Representation boundary

Main selection uses role-free whole-conversation results. Marked validation is diagnostic only. Caller-only training is not part of the current model-development experiments because the owner dropped its five-run comparison to preserve time; leave Plan 02's prepared caller-only data unchanged. Paired marker validation adds inference/storage cost, not duplicated training. Include it in budget diagnostics.

### Staged budget approvals

Measure runtime and storage during diagnostics. Before the WangchanBERTa slice, obtain owner approval for its finite maximum epoch budget, exact comparative warmup rule, persistent capacity for the six primary-only WangchanBERTa configurations and expected fresh reruns, and a slice-specific runtime/storage estimate. This estimate covers 30 fits, both validation marker conditions, per-conversation chunk metadata, epoch snapshots and approved extensions. It is a bounded slice budget only; do not describe it as whole-project feasibility.

Give all WangchanBERTa configurations comparable epoch opportunities under the approved budget. Before the remaining candidate experiments, complete their input-policy review and diagnostics, then obtain owner approval of persistent capacity and a combined time/storage estimate in `experiment_protocol.md`. That estimate must include the approved candidate-specific run counts, both validation marker conditions, epoch extensions, selected-weight and approved epoch-end-state retention, likely fresh reruns after interruption/failure, final retraining/evaluation, downloads/checkpoint transfer/restarts, local inference/STT compatibility, recording/reference preparation, 36 first-pass development playback runs plus any owner-approved targeted repeats (up to the former 108-run maximum), 36 final runs, offline diagnostics, integration and submission/rehearsal time. Clearly mark later-work estimates; do not assume uninterrupted Colab access or demonstrated simultaneous compute. Revisit the same estimate at recording-duration and application-runtime checkpoints without using final scores to adjust scope.

Retain all four candidates, the primary-only cross-candidate comparison, the approved learning-rate/fold coverage, and both WangchanBERTa pooling methods. Supplemental-data training is limited to one matched five-fold follow-up for the candidate/configuration selected from primary-only results. This owner-approved scope reduction is based on the remaining project time; it means potential supplemental-data benefits for the other candidates will remain unmeasured. Caller-only fits are also excluded by the owner-approved scope reduction. Do not further reduce the candidate, learning-rate, fold, or WangchanBERTa pooling coverage without owner approval. If diagnostics show an approved stage cannot fit, present runtime/storage evidence, alternatives, and their risks for owner review before changing scope.

For development recordings with duration sum D_dev and final recordings D_test, first-pass normal-speed playback alone is 3 × D_dev + 3 × D_test; repeating m nominated context approaches twice on every development recording adds 2 × m × D_dev (m = 1, 2 or 3); preparation, processing after playback, pauses, repeats and setup are additional. Record actual persistent capacity and checkpoint-write/retrieval overhead alongside compute time. Reserve time for application and presentation work before approving the matrix. Owners approve a documented scope/resource change if estimates do not fit; agents must not reduce runs/candidates/folds automatically.

Before final candidate sign-off and text-test access, use development/diagnostic artifacts to demonstrate candidate inference on the intended local computer and check coexistence with the proposed STT components: load the classifier with each component in turn, execute a representative development audio window and classifier request, and record supported backends, memory, execution failures and runtime. Pin tested implementations/revisions; do not silently substitute components. These checks need not score transcription quality. This is an execution/memory preflight supporting the existing practicality decision, not formal STT ranking or final-system evaluation. Formal STT comparison still uses the evaluated bundle in Plan 04/00; final-weight parity remains Plan 03/03. If compatibility is unknown or inadequate, obtain an agreed resolution before freezing the candidate rather than discovering a required reselection from final results.

Include the Model Training plan's class-specific truncation exposure in this review while retaining approved input artifacts and methods.

No additional classical baseline or extra-seed runs are included.

## 4. Initial reference and search settings

Use a small **Grid Search**, evaluating every approved learning-rate value.

| Setting | Initial reference | Search or fixed rule |
|---|---|---|
| Learning rate | `3e-5` | Search `2e-5`, `3e-5`, `5e-5` |
| Initial duration | 3 epochs | Extend by 1 epoch within the approved budget |
| Effective batch size | 16 | Fixed |
| Optimizer | AdamW | Fixed |
| Weight decay | 0.01 | Ordinary trainable weights; zero for biases and normalization parameters |
| AdamW betas | 0.9, 0.999 | Fixed |
| AdamW epsilon | `1e-8` | Fixed |
| Gradient clipping | Global norm 1.0 | Fixed |
| Schedule | Linear warmup, then constant | Fixed |
| Dropout | Checkpoint-configured values | Retain; explicitly record newly created head settings |
| Training seed | 67 | Fixed; no extra-seed experiments |
| Scam threshold | 0.5 | Fixed |

Each learning rate is an independent configuration. Initialize every new fold/configuration from the original pretrained checkpoint with fresh training state.

Memory-driven microbatch and accumulation adjustments must preserve effective batch size 16. Apply clipping after accumulation and any FP16 gradient unscaling, before the optimizer update.

### Warmup checkpoint

Confirm and obtain owner approval of the exact comparative warmup rule during WangchanBERTa-specific diagnostics, before the 30-fit primary-only slice. Define its optimizer-update steps from the initial three-epoch duration for each eligible training subset. Check the other candidates' compatibility during their later diagnostics; any model-specific adjustment requires owner approval before that candidate's fits and must preserve comparable opportunities. Resolve and approve the selected candidate's supplemental-data fit budget after primary-only candidate selection and before that five-fold comparison.

Keep those warmup steps unchanged when extending the corresponding run. After warmup, retain its selected learning rate.

Document all resolved settings explicitly. Numerical instability or model-specific incompatibility requires an explained, approved adjustment.

### Why these choices

A small grid fits the limited search space and makes every configuration traceable. Fixing supporting settings controls the comparison and limits cost.

BERT's published fine-tuning ranges support the learning-rate values and three-epoch starting point as historical guidance. They do not establish optimal settings for these datasets or checkpoints.

## 5. Validation metrics

Use **Scam as the positive class**, with `Not Scam = 0` and `Scam = 1`.

For each saved validation fold:

1. Evaluate its records from both sources combined under both marker conditions, using the corresponding dialogue representation.
2. Compute binary Scam F1 separately for each condition.
3. Retain source-specific results and condition identities separately.

Rank main configurations using the arithmetic mean of the five combined-source **role-free whole-conversation** fold Scam F1 scores. All main duration/configuration tie rules and human app selection use this condition. Marked-condition scores must not override it.

Report individual fold scores; mean and **sample SD**, using denominator `5 − 1`; Scam precision and recall; macro-F1 and accuracy; confusion matrices and class/sample counts; source-specific results; and training/validation loss curves.

Scam F1 balances missed scams and false warnings. Macro-F1 provides equal-class context. Micro-F1 over both classes equals accuracy for this single-label task.

### Reporting rules

- Compute metrics from conversation-level predictions, not an average of batch metrics.
- Use confusion-matrix order `[Not Scam, Scam]`, with true labels as rows.
- For an undefined metric on a nonempty evaluated subset, report zero and flag the reason.
- For an empty source subset, report zero support and unavailable metrics.
- Failed or incomplete runs are not fabricated as zero-scoring predictions.
- Keep mean-fold metrics distinct from pooled out-of-fold metrics.
- Fold SD describes partition variation; it is not a confidence interval or evidence of robustness across training seeds.

## 6. Epoch experiments and configuration selection

Start each run with three epochs, then extend by one epoch within the approved budget.

At every epoch, retain training/validation losses, validation metrics and sample-level probabilities, learning rate and optimizer-update progress, runtime, resources, and checkpoint references. The training component also flushes scalar progress after optimizer updates so a failed or abruptly terminated attempt leaves its latest observed update/loss/resource evidence; these records do not contain restorable model state.

Compare each configuration at a **common epoch across all five folds**.

### Duration selection

For each model/learning-rate/input-pooling configuration in the primary-only comparison, and for the selected candidate's single matched supplemental-data follow-up:

1. Select the epoch with the highest mean role-free whole-conversation validation Scam F1.
2. If means tie exactly, select the earlier epoch.

Do not combine individually selected best epochs from different folds into a common-epoch result.

### Configuration selection

Within each model's primary-only results, rank each input-pooling configuration by:

1. Highest mean role-free whole-conversation validation Scam F1.
2. Lower fold SD when means tie exactly.
3. Fewer epochs if still tied.
4. Lower learning rate if still tied.

Use unrounded values for tie detection. The last rule is a reproducibility convention, not an optimality claim.

For the WangchanBERTa primary-only pilot, compare max-pooling and mean-pooling configurations on matched folds, learning rates, and common epochs. Report each method's Scam F1 mean, sample SD, fold scores, supporting metrics, runtime, and results stratified by conversation chunk count. Treat both methods as separate configurations; do not assume either is preferable or pool their results together. Carry the selected WangchanBERTa method into the supplemental-data follow-up only if WangchanBERTa is the primary-only selected candidate.

Keep all results, including non-improvements. CV used for tuning and epoch selection is selection evidence, not an unbiased final performance estimate.

## 7. Planned epoch extensions and interruption evidence

Follow Plan 03/00's owner-approved interruption policy. A fit interrupted or failed before its approved target completes is preserved as an incomplete attempt, including its scalar progress log, partial epoch history, available validation outputs, and failure evidence; rerun the full fit from the original pretrained checkpoint with fresh training state and a new run ID. Keep each failed attempt and reason in the manifest's attempt history; do not resume it or count it as a completed fold. If abrupt runtime loss leaves the attempt marked `running`, inspect and preserve its available progress without inventing a cause.

An explicitly approved epoch-budget extension after a run has completed its current target may continue from that same run's verified epoch-end state. This is a planned experiment extension, not recovery from a failed/interrupted fit. Preserve configuration and input identity checks and do not recalculate warmup during an extension.

Preserve each completed epoch's model weights until the configuration's five-fold duration selection is complete. Afterwards, retain selected weights and any latest completed epoch-end state still required for an already approved extension; retain all histories and predictions for reporting. Model-only selection snapshots support duration selection and are not optimizer-resume state.

Check storage feasibility during diagnostics for epoch snapshots, any state needed for an approved extension, histories, predictions, and expected rerun overhead. If the retention or persistent-storage rule cannot be supported, obtain approval for a documented alternative.

Record interruptions, failures, fresh reruns, planned extensions, and environment changes.

## 8. Compare tuning and data effects

### Initial versus tuned

For each model's primary-only results, compare the three-epoch `3e-5` reference against its selected configuration using identical folds and metric definitions. The supplemental-data follow-up is not a separately tuned search.

Report changes in F1, SD, supporting metrics, duration, and cost—even when tuning does not improve results.

### Selected-candidate supplemental-data comparison

After selecting the best-supported model/configuration from the primary-only cross-candidate results, run the same selected configuration across the same five folds using primary + supplemental training. Keep the candidate, learning rate, pooling/input method, seed, epoch opportunity, validation records, validation marker conditions, and metric definitions matched; change only the eligible training-data condition. Reuse the completed primary-only fold evidence as the paired baseline where its run identity and artifacts verify. Do not independently tune the supplemental condition or run it for the other candidates.

Report per-fold and mean/sample-SD Scam F1, supporting metrics, training/validation loss, source-specific validation results, and the paired fold differences (combined minus primary-only). Preserve all outcomes, including no improvement. This estimates the effect of adding supplemental records for the selected candidate/configuration under the tested settings only; it does not establish an effect for other candidates, hyperparameters, pooling methods, or a generally larger data regime.

### Marker-removal and dialogue-content diagnostics

For matching weights/fold/epoch/population, report marked versus role-free metrics and paired fold differences (role-free minus marked), with mean/sample SD and token-length/truncation exposure. Remove markers before tokenization/truncation. Do not claim this establishes superiority of marked training; changes may include differences in retained content.

For the WangchanBERTa pooling comparison, compare max and mean using matched fold, learning rate, epoch, marker condition, and validation membership under primary-only training. Report paired fold differences in Scam F1, mean/sample SD, supporting metrics, training/inference runtime, and chunk-count-stratified behavior. Retain all results, including non-improvements. Do not describe pooling differences as a cross-model comparison or as evidence that one strategy is universally better.

## 9. Final candidate selection and threshold

First review all candidate results under primary-only training using mean validation Scam F1, fold SD and individual scores, source-specific behavior, training cost and development inference latency, and practical input requirements. Include the WangchanBERTa max-versus-mean evidence as an input-method comparison; do not let the WangchanBERTa pilot alone select the final candidate. After a candidate/configuration is selected, review its matched supplemental-data comparison to choose the final training-data condition. This secondary comparison does not reopen ranking among the four candidates.

**Final candidate selection requires human review and a written rationale.**

An absolute F1 difference of **0.05** is a discussion guideline for considering a performance–stability tradeoff. It is not an automatic cutoff, proof of equivalence, or a rule that lower SD always wins.

Approve the final model using the primary-only cross-candidate comparison, then approve its final training-data condition using the selected candidate's matched supplemental-data comparison. Freeze the candidate, selected configuration, and data condition before final retraining and without final-test access. The app representation remains whole conversation and role-free, not a selectable caller-only mode. Freeze `training_representation=whole_conversation`, `training_marker_condition=role_marked`, `inference_representation=whole_conversation`, and `inference_marker_condition=role_free`, with separate preprocessing identities.

Use:

```text
Scam probability ≥ 0.5 → Scam
Otherwise             → Not Scam
```

Any later threshold experiment requires owner approval, a validation-only protocol, and documented results. Freeze the threshold before final testing.

Record development timing with its host and workload. Detailed final system measurements belong to later plans. Do not describe model probabilities as calibrated confidence.

## 10. Completion and handoff

Complete when:

- Required comparisons are complete or an approved scope change is documented.
- All five folds and approved epoch opportunities are accounted for.
- Results, per-epoch histories, failures/interruption reasons, fresh reruns, planned extensions, and report evidence are traceable.
- The final candidate and representation have been reviewed and approved.
- The selected candidate's matched supplemental-data comparison is complete, or its exclusion is explicitly owner-approved and documented; the final training-data condition is decided before final retraining.
- Selected settings and threshold are frozen without final-test access.
- The comparison report explains tradeoffs and limitations, including both validation marker conditions and, for the WangchanBERTa pilot, the max-versus-mean pooling comparison and chunk-count-stratified results.

Hand off `selected_config.json` and supporting evidence to [Final Model Evaluation and Error Analysis](02%20-%20FINAL%20MODEL%20EVALUATION%20AND%20ERROR%20ANALYSIS.md).

Record the selected preprocessing policy here. Any approved learned preprocessing is fitted on the eligible full training pool during final retraining, then frozen before test inference.

Do not execute final retraining or test evaluation in this task.

## References and rationale

- [Full Proposal](../../00%20-%20DOCUMENTs/Full%20Proposal/Phoebe_FullProposal.docx), §§4.2, 6.1–6.3 and 7.1: split/CV workflow, candidates, comparisons, metrics, and practical constraints.
- [L05 - Model Selection & Hyperparameter Tuning](../course-lecture-sheets/Pattern%20Recognition%20L05_Model%20Selection%20%26%20Hyperparameter%20Tuning.pdf), PDF pp. 20, 23–29, 32–37: validation-only tuning, grid-search cost, train-only fitting, performance/variability/cost selection, and final retraining before test.
- [L06 - Experimental Design and System Evaluation](../course-lecture-sheets/Pattern%20Recognition%20L06_Experimental%20Design%20and%20System%20Evaluation.pdf), PDF pp. 11–12, 18–19, 23, 32–35 and 40: fair comparisons, reproducibility, leakage prevention, metric averaging, and validation-based threshold decisions.
- [BERT, Appendix A.3](https://aclanthology.org/N19-1423.pdf), PDF pp. 13–14: historical fine-tuning settings.
- [AdamW paper](https://arxiv.org/abs/1711.05101): decoupled weight decay differs from adding L2 to Adam's loss.
- [Official AdamW documentation](https://docs.pytorch.org/docs/2.14/generated/torch.optim.AdamW.html) and [Transformers training documentation](https://huggingface.co/docs/transformers/main_classes/trainer): optimizer starting values, clipping, and decay-group conventions.
- [Official F1 definitions](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.f1_score.html): binary/averaged F1 and undefined-metric handling.

Exact filenames, tie rules, SD convention, experiment scope, and approval checkpoints are project decisions. The references support their principles and starting conventions, not a claim that every choice is lecture-mandated or optimal. Lecture PDFs remain local and ignored.
