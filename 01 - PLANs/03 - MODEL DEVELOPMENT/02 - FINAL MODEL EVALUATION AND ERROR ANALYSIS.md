# 02 - FINAL MODEL EVALUATION AND ERROR ANALYSIS

## Purpose and scope

Retrain the single CV-selected pipeline on its eligible full training pool, evaluate it on the untouched text test set, and preserve results and error evidence.

This task covers final retraining using the frozen selected configuration, final text-test predictions and metrics, inference-failure accounting, review of every false positive and false negative, and preservation of development and evaluation evidence.

Do not reopen model selection, hyperparameter tuning, representation selection, or the decision threshold. Packaging and application/system evaluation belong to later plans.

## 1. Inputs and prerequisites

Use:

- `selection/selected_config.json` and the approved selection rationale from [Hyperparameter Tuning and Model Selection](01%20-%20HYPERPARAMETER%20TUNING%20AND%20MODEL%20SELECTION.md).
- The input-preparation component and approved policy from [Data Preprocessing and Model Inputs](../02%20-%20DATA%20PREPROCESSING%20AND%20MODEL%20INPUTS.md).
- The reusable component from [Model Training](00%20-%20MODEL%20TRAINING.md).
- Saved train/test records and assignments from [Data Split and Experiment Design](../01%20-%20DATA%20SPLIT%20AND%20EXPERIMENT%20DESIGN.md).
- Preparation provenance and audit information.
- Existing training histories, CV results, and comparison reports.

Before final training, verify that the selected model, checkpoint revision, data condition, representation, training settings, duration, seed, and threshold are frozen.

Resolve any incomplete configuration before accessing test records. Do not invent missing settings or infer them from test performance.

## 2. Output structure

```text
03 - MODEL DEVELOPMENT/final-evaluation/
├── README.md
├── evaluation_protocol.md
├── final_training/
│   └── <run_id>/
│       └── Existing training-run artifact structure
├── test_predictions.csv
├── metrics.json
├── error_analysis.csv
├── evaluation_report.md
└── figures/
```

| Artifact | Purpose |
|---|---|
| `README.md` | Explain files, reproducible evaluation, and evidence locations. |
| `evaluation_protocol.md` | Record the frozen pipeline, dataset identities, metric rules, failure handling, and execution conditions. |
| `final_training/` | Preserve the final training configuration, environment, per-epoch history, per-update progress logs, final weights, and any failed/interrupted-attempt evidence. |
| `test_predictions.csv` | Account for every assigned test sample, including successful predictions and failures. |
| `metrics.json` | Store combined/source-specific metrics, counts, denominator rules, and completion rate. |
| `error_analysis.csv` | Preserve every false positive and false negative with traceable evidence and review notes. |
| `evaluation_report.md` | Present final results, development-evidence references, errors, failures, and limitations. |
| `figures/` | Store evaluation figures derived from saved evidence. |

Keep weights and generated sample-level evidence outside Git in documented persistent storage. Reference existing development artifacts rather than copying them.

## 3. Freeze the evaluation protocol

Evaluate one CV-selected app pipeline: retrain on **role-marked whole conversations**, then test **role-free whole conversations**. Preserve this intentional distinction; role-free CV results selected the app candidate.

Record:

- Model, checkpoint/tokenizer revisions, and input configuration.
- Selected training-data condition, training/inference representations and marker conditions, with separate preprocessing identities.
- Training settings, duration, and seed **67**.
- Decision threshold **0.5**.
- Dataset/assignment identities and eligible training membership.
- Evaluation environment and artifact locations.
- Metric definitions and failure-reporting rules.

Reuse the tuning plan's metric conventions:

- `Not Scam = 0`, `Scam = 1`.
- Scam is the positive class.
- Confusion-matrix order `[Not Scam, Scam]`, with true labels as rows.
- Undefined metrics on nonempty subsets are reported as zero with an explanatory flag.
- Empty subsets have zero support and unavailable metrics.

No final-test confidence intervals are required. Preserve CV mean ± sample SD separately as development evidence; do not describe it as uncertainty around the final test score.

## 4. Perform final retraining

1. Initialize from the selected **original pretrained checkpoint**, with a fresh classification head and training state.
2. Retrieve the eligible full training pool: primary records for primary-only training, or both sources for combined-data training.
3. Apply the approved whole-conversation **role-marked training** input procedure.
4. Fit any approved data-derived transformation only on that eligible training pool.
5. Record and freeze its fitted state before test inference.
6. Train for the duration selected through CV, using the frozen settings.
7. Preserve the final weights, configuration, per-epoch history, per-update progress logs, and any failed/interrupted-attempt evidence. If final training is interrupted or fails before completion, preserve that attempt and rerun the full fit from the original pretrained checkpoint with fresh state and a new run ID, following Plan 03/00; do not resume the interrupted fit.

Resolve final-run warmup steps from the approved warmup rule and final training membership, not by copying a CV fold's step count. If that rule is insufficiently specified, obtain clarification before training; do not select a new schedule from test results.

Reuse the existing batching, precision, loss, optimizer, and interruption-handling procedures. A planned epoch extension is not part of this frozen final-training run.

The reusable training component must support an explicit final-training mode without a validation set. There is **no validation-based checkpoint selection in this final run**. Mark validation fields unavailable; do not fabricate validation predictions or metrics. Use the completed selected duration's weights.

Do not use test loss for early stopping, reuse a CV fold's trained weights as the final model, or introduce an unapproved validation split or ensemble.

## 5. Execute final test inference

After final training and preprocessing are frozen:

1. Load the unchanged saved test records.
2. Verify their membership against saved assignments.
3. Render whole-conversation role-free input before frozen checkpoint preparation/tokenization/length handling. Verify unchanged test content by checksum or canonical-row equality when loading is authorized.
4. Run in evaluation mode without gradients or learning.
5. Produce one conversation-level outcome per assigned sample.
6. Apply:

```text
Scam probability ≥ 0.5 → Scam
Otherwise             → Not Scam
```

For successful predictions, preserve evaluation/run and final-artifact identity, sample ID and source, true label, both class probabilities, predicted label, and threshold.

For failures, preserve sample identity, execution state, and failure reason. Leave unavailable prediction fields empty; never invent a class.

Verify coverage, unique IDs, valid probabilities and unchanged model/configuration identity. Do not add marked-test comparisons or a caller-only final model; diagnostics belong to CV.

## 6. Report metrics and failures

Report combined and source-specific:

- Scam precision, recall, and F1.
- Macro-F1 and accuracy.
- Confusion-matrix counts.
- Assigned, successful, and failed sample counts.
- True class counts for assigned and successfully evaluated records.
- Completion rate:

```text
successful predictions / all assigned test samples
```

Compute classification metrics on successful predictions and state their denominator. Report failure counts by source and reason so missing predictions cannot silently improve the apparent result.

Retain both test sources even when final training uses primary-only data.

A genuine execution-bug correction must preserve the original evidence, correction explanation, and a distinct corrected-run identity. Do not change predictive settings to improve test scores or conceal failed attempts.

Do not invent a numeric success target. Preserve disappointing results as well as favorable ones.

## 7. Preserve and review every prediction error

Create one error-analysis record for every successful prediction that is:

- **False negative:** Scam predicted as Not Scam.
- **False positive:** Not Scam predicted as Scam.

Record:

- Sample ID, source, and prediction-artifact reference.
- True/predicted labels and Scam probability.
- Traceable transcript or excerpt evidence.
- Relevant input-length or structural-marker parsing findings.
- Observed error category.
- Review explanation, evidence, and uncertainty.
- Potential future investigation.

Categories may include ambiguous source labels, translated wording, missing context, mixed language, length-related information loss, or structural parsing defects. Use categories supported by observations; do not assume they explain an error.

Keep technical inference failures separately from classification errors.

Preserve every misclassified sample internally. Selection of examples for the main report or appendix belongs to the reporting plan.

**Do not change labels or retune this experiment from test errors.** Any later development cycle must be identified separately.

## 8. Preserve development evidence

Retain and reference:

- Every CV fold's metrics and mean ± sample SD.
- Per-epoch losses, metrics, and predictions.
- Initial-versus-tuned comparisons.
- Model/data comparisons, paired marked/role-free validation and the five-run caller-only comparison. Preserve superseded experiments separately with old input identities clearly identified.
- Configurations, per-epoch history, per-update progress logs, timing/resources, failures, interruptions, fresh-rerun records, and reasons.
- Final training history and final-test evidence.

Decide main-report versus appendix inclusion later. Do not discard useful evidence merely because it is absent from the current report.

Keep CV selection results and final-test results clearly labeled.

## 9. Completion and handoff

Complete when:

- The selected pipeline is retrained on its eligible full training pool.
- Final weights and preprocessing are identifiable and recoverable.
- Every assigned test sample has a recorded outcome.
- Metrics and denominators are reproducible.
- Every false positive and false negative is preserved and reviewed.
- Failures and corrections remain visible.
- Development evidence and limitations are retained.

Hand off the evaluated weights, tokenizer, frozen preprocessing, configuration, artifact identities, and evaluation report to [Model Freeze and App Handoff](03%20-%20MODEL%20FREEZE%20AND%20APP%20HANDOFF.md).

Do not switch models because another candidate might perform better on the test set.

## References and rationale

- [Full Proposal](../../00%20-%20DOCUMENTs/Full%20Proposal/Phoebe_FullProposal.docx), §§4.3, 6.3 and 7.1: simulated-data limitations, evaluation metrics, and reporting.
- [L05 - Model Selection & Hyperparameter Tuning](../course-lecture-sheets/Pattern%20Recognition%20L05_Model%20Selection%20%26%20Hyperparameter%20Tuning.pdf), PDF pp. 35–37: performance/variability considerations, final retraining, untouched test evaluation, and no test-driven retuning.
- [L06 - Experimental Design and System Evaluation](../course-lecture-sheets/Pattern%20Recognition%20L06_Experimental%20Design%20and%20System%20Evaluation.pdf), PDF pp. 19, 23, 32–35 and 42–43: reproducibility, metric definitions, error analysis, and source-specific performance.
- Approved input-preparation, training, and tuning plans provide the authoritative methods reused here.

Final results describe performance on the selected simulated-data test set. They do not establish real-call accuracy, calibrated risk probabilities, or end-to-end audio performance. Lecture materials remain local and ignored.
