# Final training and text evaluation

This directory contains only tooling and clearly marked templates. No final training or test inference has been performed. Importing `evaluation.py` does not load a dataset, model weights, or the test partition.

## Gate sequence

1. Freeze `selection/selected_config.json` from the main 120-fit matrix and approved candidate decision.
2. Complete Plan 03/01 section 8's five fresh caller-only fits and create `selection/selection_completion.json`. This binds the verified full 125-fit comparison and caller evidence; main candidate selection is not reopened.
3. Obtain separate owner approval for fresh full-pool training. The record binds the selection completion checksum, selected config checksum, exact selected CV run ID/config checksum, final run ID, persistent training directory, full-pool warmup value/rule reference, reviewer/date, and exact trainer approved-settings digest. Preview the digest with `prepare-final-config --print-settings-digest` and a draft approval record; that option prints only and writes no config. `prepare-final-config` verifies the selected CV run, frozen model/data/LR/training/runtime settings, saved train-pool assignments, and recalculates warmup using the approved rule over the full selected training pool. It writes a no-validation config only when the approved settings digest matches.
4. Run `train-final --authorized-final-training` only after the owner has explicitly authorized the training launch. The training component must export `model.safetensors` before evaluation.
5. Obtain a separate final-test authorization record bound to selected config, saved assignments, test CSV, preprocessing config, selection completion, final run ID, exact model weights and artifact manifest. `infer-test --authorized-test-execution` verifies those identities before loading test records. The output directory must exactly match the authorization record.
6. Document evidence, observed error category, explanation, uncertainty, and possible future investigation for every FP/FN in `error_analysis.csv`. Tool-populated rows remain `pending_review`; an authorized project worker/agent or owner may complete the evidence review. Only consequential changes to labels or methods require owner confirmation.

Do not run any of the gated training or final-test commands until the corresponding owner approvals and plan checkpoints are resolved. A CLI flag alone is not authorization.

## Commands

The files `final_training_approval.template.json` and `final_test_authorization.template.json` show the required approval schemas. `draft-approval` can prefill identities known from the selected config, selection-completion evidence, CV run, final artifact, preprocessing config, and saved input metadata; generated drafts remain `template_unapproved` and final-test authorization remains false. The final-training draft can be passed to `prepare-final-config --print-settings-digest` after an owner reference, run ID, persistent path, and the exact CV source are filled in. The printed digest is then copied into the owner-signed approval record. No config is written by this digest-preview option.

```text
python "03 - MODEL DEVELOPMENT/final-evaluation/evaluation.py" draft-approval \
  --kind final-training --cv-run-config /persistent/path/selected-fold/run_config.json \
  --final-run-id owner-chosen-run-id --persistent-runs /persistent/path/training/runs \
  --output /persistent/path/final-training-approval.draft.json
```

Prepare the final config from one of the five selected CV fold run configs:

```text
python "03 - MODEL DEVELOPMENT/final-evaluation/evaluation.py" prepare-final-config \
  --cv-run-config /persistent/path/selected-cv-fold/run_config.json \
  --final-training-approval /owner-approved/final-training.json \
  --completion-record "03 - MODEL DEVELOPMENT/selection/selection_completion.json" \
  --output /persistent/path/final-training-config.json
```

Launch only after human authorization:

```text
python "03 - MODEL DEVELOPMENT/final-evaluation/evaluation.py" train-final \
  --config /persistent/path/final-training-config.json \
  --authorized-final-training
```

The exported model is evaluated with the shared role-free whole-conversation preparation and batching path. The same `predict_with_trace` path is exposed as `FinalEvaluationPredictor` for development-only live parity checks. Its `model_version` is derived from the verified run ID and artifact-manifest SHA-256. The response and trace carry request identity, prepared text, unpadded IDs/mask, padded model inputs, batching metadata, probabilities, label, and threshold.

For local development parity after transferring a final run from persistent/cloud storage, `load_pipeline(..., completion_record_path=...)` accepts an explicitly supplied local copy of the selection-completion record only when its SHA-256 matches the frozen final-training config. It does not rewrite that config or substitute different selection evidence; the default path remains the recorded path for final evaluation in its original environment.

Test evaluation requires a separate explicit authorization and writes exactly these artifacts directly into the authorized output directory:

- `evaluation_protocol.md`: checksums and execution settings for the authorized evaluation.
- `test_predictions.csv`: one outcome per assigned test ID, including per-record execution failures.
- `metrics.json`: valid JSON combined and fixed primary/supplemental source metrics, support, completion counts, and failure reasons; empty subsets have `null` metrics.
- `error_analysis.csv`: every FP/FN with transcript evidence and required human-review fields left pending.
- `evaluation_report.md`: counts, metrics, artifact identity and limitations.

Sample-level evidence contains transcripts and must remain in the approved persistent location outside Git. Final metric reporting uses successful predictions as the classification denominator and all assigned test IDs for completion rate. Execution failures are never relabeled as FP/FN. The frozen threshold is 0.5. The saved `model.safetensors` checksum is recorded before any model packaging or handoff conversion.

`evaluation_protocol.template.md` and `evaluation_report.template.md` are unexecuted planning aids. They are not final evidence and must not be represented as results.
