# 01 - HYPERPARAMETER TUNING AND MODEL SELECTION

## Purpose and scope

Compare the four approved transformer candidates, tune learning rate and training duration, and select the final model and training-data condition using cross-validation evidence. The representation is fixed to role-free whole-conversation text.

This task owns initial-versus-tuned comparisons, primary-only versus primary + supplemental training comparisons, configuration ranking, and final candidate selection.

Reuse the existing training and input-preparation components. Do not redefine dataset membership, label mapping, tokenization, loss, or optimizer family. Final retraining and text-test evaluation belong to the next plan. Packaging, STT selection, application integration, and final system measurements remain separate.

## 1. Inputs and prerequisites

Use:

- [Plan 01](../01%20-%20DATA%20SPLIT%20AND%20EXPERIMENT%20DESIGN.md)'s saved training pool, fold assignments, and data conditions.
- [Plan 02](../02%20-%20DATA%20PREPROCESSING%20AND%20MODEL%20INPUTS.md)'s approved input-preparation component and configuration.
- [Model Training](00%20-%20MODEL%20TRAINING.md)'s reusable training component, diagnostic report, and run artifacts.
- The four approved checkpoints with pinned revisions.

Before comparative experiments:

1. Verify preceding completion checks.
2. Resolve structural-marker removal and input-length checkpoints.
3. Verify each candidate's execution, recovery, memory, runtime, and persistent-storage requirements.
4. Obtain approval of the exact warmup amount and finite maximum epoch budget.
5. Record the complete experiment protocol.

**Do not load the final test set during this task.**

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
| `experiment_manifest.csv` | Map each planned run to its configuration, training artifacts, execution state, and failures. |
| `cv_results.csv` | Store per-fold, per-epoch metrics and aggregate results for completed comparable configurations. |
| `comparison_report.md` | Present comparisons, learning curves, variability, computational costs, selection rationale, and limitations. |
| `selected_config.json` | Freeze the selected model, data condition, representation, training settings, duration, threshold, and preprocessing policy. |

Keep training histories, sample-level predictions, and checkpoints in their existing training-run locations. Reference them rather than creating duplicate copies.

Generated sample-level evidence and model artifacts remain outside Git in documented persistent storage. Reusable instructions and suitable aggregate reports may be tracked.

### Required traceability

The experiment manifest identifies experiment ID, run ID, configuration ID, checkpoint/revision, training-data condition, representation, fold, training seed, experiment purpose (initial reference or search), execution state, artifact location, and failure reason.

CV results identify configuration, condition, representation, fold, epoch, evaluated subset, sample/class counts, metric values, undefined-metric flags, and timing. Aggregate rows must be distinguishable from individual-fold rows.

## 3. Experiment scope and budget

### Main comparison

Evaluate all four candidates with role-free whole-conversation input, both approved training-data conditions, three learning-rate candidates, the same five saved validation folds, and training seed **67**.

The main matrix contains:

```text
4 models × 2 data conditions × 3 learning rates × 5 folds
= 120 independent training runs
```

Epoch extensions continue these runs from their matching saved state; they are not separate learning-rate configurations. Reuse the matching initial-reference results from this matrix instead of repeating identical runs.

### Representation boundary

All comparisons use role-free whole-conversation text. The owner removed the caller-only ablation to match ordinary STT inference without role attribution. No additional five-run speaker comparison is required.

### Budget checkpoint

Measure runtime and storage during diagnostics. Before the full comparison, obtain owner approval of a finite maximum epoch budget that accounts for Colab availability and the deadline.

Give configurations comparable epoch opportunities within that budget. If the agreed matrix becomes infeasible, document the issue and obtain approval before reducing scope or changing methods.

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

Confirm the exact warmup amount during diagnostics, before comparative experiments. Define its optimizer-update steps from the initial three-epoch duration for each eligible training subset.

Keep those warmup steps unchanged when extending the corresponding run. After warmup, retain its selected learning rate.

Document all resolved settings explicitly. Numerical instability or model-specific incompatibility requires an explained, approved adjustment.

### Why these choices

A small grid fits the limited search space and makes every configuration traceable. Fixing supporting settings controls the comparison and limits cost.

BERT's published fine-tuning ranges support the learning-rate values and three-epoch starting point as historical guidance. They do not establish optimal settings for these datasets or checkpoints.

## 5. Validation metrics

Use **Scam as the positive class**, with `Not Scam = 0` and `Scam = 1`.

For each saved validation fold:

1. Evaluate its records from both sources combined.
2. Compute binary Scam F1.
3. Retain source-specific results separately.

Rank configurations using the arithmetic mean of the five combined-source fold Scam F1 scores.

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

At every epoch, retain training/validation losses, validation metrics and sample-level probabilities, learning rate and optimizer-update progress, runtime, and checkpoint references.

Compare each configuration at a **common epoch across all five folds**.

### Duration selection

For each model/data-condition/learning-rate configuration:

1. Select the epoch with the highest mean validation Scam F1.
2. If means tie exactly, select the earlier epoch.

Do not combine individually selected best epochs from different folds into a common-epoch result.

### Configuration selection

Within each model and data condition, rank configurations by:

1. Highest mean validation Scam F1.
2. Lower fold SD when means tie exactly.
3. Fewer epochs if still tied.
4. Lower learning rate if still tied.

Use unrounded values for tie detection. The last rule is a reproducibility convention, not an optimality claim.

Keep all results, including non-improvements. CV used for tuning and epoch selection is selection evidence, not an unbiased final performance estimate.

## 7. Recovery and evidence retention

Follow the Model Training plan's recovery procedure:

- Save verified recovery state every epoch.
- Use within-epoch recovery intervals based on diagnostic runtime.
- Save to persistent storage.
- Verify new recovery checkpoints before replacing previous ones.
- Resume only the same run with matching configuration and input identities.

Preserve each epoch's model weights until the configuration's five-fold duration selection is complete. Afterwards, retain selected weights and necessary recovery state; retain all histories and predictions for reporting.

Model-only selection snapshots are not complete recovery checkpoints.

Check storage feasibility during diagnostics. If the retention rule cannot be supported, obtain approval for a documented alternative.

Record interruptions, failures, repeated work, and environment changes.

## 8. Compare tuning and data effects

### Initial versus tuned

For each model and data condition, compare the three-epoch `3e-5` reference against the selected configuration using identical folds and metric definitions.

Report changes in F1, SD, supporting metrics, duration, and cost—even when tuning does not improve results.

### Training-data conditions

Give primary-only and combined-data training the same grid and epoch opportunities, with identical validation records.

Report both matching-setting comparisons, showing the effect of adding supplemental data under those settings, and separately tuned comparisons, showing each condition's best result found within the approved search.

## 9. Final candidate selection and threshold

Review all candidate results using mean validation Scam F1, fold SD and individual scores, source-specific behavior, training cost and development inference latency, and practical input requirements.

**Final candidate selection requires human review and a written rationale.**

An absolute F1 difference of **0.05** is a discussion guideline for considering a performance–stability tradeoff. It is not an automatic cutoff, proof of equivalence, or a rule that lower SD always wins.

Approve the final model and data condition using the completed role-free whole-conversation comparisons. The input representation is fixed, not a selection dimension.

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
- Results, failures, recovery events, and report evidence are traceable.
- The final candidate and representation have been reviewed and approved.
- Selected settings and threshold are frozen without final-test access.
- The comparison report explains tradeoffs and limitations.

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
