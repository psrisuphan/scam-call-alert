# Final training and text evaluation

This directory contains tooling, templates and the final-run protocol. Importing `evaluation.py` does not load a dataset, model weights, or the test partition.

Coworker continuation instructions: [COWORKER_HANDOFF.md](COWORKER_HANDOFF.md). The compatibility-transfer archive and checksum sidecar are listed in the owner's [Google Drive handoff folder](https://drive.google.com/drive/folders/1FwMMh3IlETobUeF5DY6HPcWUX_WgZ0SA?usp=drive_link). The Drive copy has not been independently downloaded/checksum-verified; verify it after download. Model files are not downloaded by Git and the provenance blocker must clear before the Mac check.

## Verified replacement final training

The replacement `phaya-final-replacement-primary-epoch2-20261012T050936Z` completed two epochs and 128 optimizer updates on all 1,021 primary records. Its final checkpoint and original-format inference export have been transferred from runtime-local disk and independently verified on the owner's local computer. No validation or held-out inference ran.

Persistent owning directory (Git ignored):
`03 - MODEL DEVELOPMENT/final-evaluation/final_training/phaya-final-replacement-primary-epoch2-20261012T050936Z/`.

Execution/source/approval snapshots and verification:
`final_training/phaya-final-replacement-primary-epoch2-20261012T050936Z-execution/`, including `persistent-verification.json` and `training-source.zip`.

All 18 run files, approximately 7.79 GB, passed byte-count/SHA-256 transfer checks and independent local readback. The copied completed summary's artifact hashes, epoch-2/128-update checkpoint recovery identity and inference manifest were revalidated locally. This establishes owner-local persistence, not a completed Drive/cloud backup.

Final model.safetensors SHA-256: `af64d3a917d5db82bc9dfe794c8f29125bbf13ad9060f726c75ac001f99d838b`.
Training losses: epoch 1 `0.19045969620018643`, epoch 2 `0.0006572449280302078`; these are training losses, not performance scores. Recorded run duration was 269.68 seconds, excluding transfer/independent verification.

The next turn should read these persistent records, not infer readiness from a runtime's presence. Selection-completion provenance/report reconciliation, the coworker's Mac execution check, separate test authorization, error review and official handoff remain pending. The final model is trained and recoverable, not yet held-out evaluated or released.

## Previous failed-persistence run

The owner-authorized fresh run `phaya-final-primary-epoch2-20261012T024607Z` used 1,021 primary conversations, two epochs, 128 optimizer updates, 20 warmup updates, seed 67, effective batch 16 and T4 FP16, without validation. The saved summary reports completed training and no failure, but fresh-runtime recovery found no checkpoint weights or model.safetensors anywhere in the persistent final-evaluation area. The saved training history also fails its summary-bound checksum and contains only epoch 1. The run is unusable as a final model despite its completed computation summary. Preserve the original evidence; do not treat the summary or export manifest as proof that weights persisted.

Persistent execution evidence: `/content/drive/MyDrive/scam-call-alert/model-development/final-evaluation/execution-20261012T024607Z/`. Its `configs/`, `evidence/` and `runs/` directories preserve the launch configuration, source archive, approval/report snapshots, setup log, progress and training artifacts outside Git.

The run was launched directly through the reusable trainer. Its original run config lacks the selection-completion binding required by the evaluation/parity tooling below. Preserve the original config, checkpoint identity and evidence. This provenance mismatch must be resolved before using `load_pipeline`, drafting final-test authorization or releasing the Mac compatibility workflow through that path. Do not invent a verified completion record, weaken the guard or retrain automatically.

Recovery evidence is preserved at execution-20261012T024607Z/evidence/recovery-inspection-20261012.json under the persistent execution root. A read-only search of that final-evaluation area found no .pt, .safetensors, .bin or .tmp weight candidates. This establishes missing artifacts in the inspected location, not an exhaustive search of other accounts or Drive trash. Replacement training and any changed persistence procedure require explicit owner confirmation before execution.

Mac classifier/STT compatibility remains pending coworker verification. No held-out test inference has run, and separate test authorization is still required.

## Gate sequence

1. Freeze `selection/selected_config.json` from the owner-approved PhayaThaiBERT decision (LR 3e-5, two epochs, primary-only), recording limitations and pending Mac compatibility separately.
2. Create `selection/selection_completion.json` with 45 completed main fits, 30 excluded main fits, zero caller-only fits and zero matched supplemental fits. Bind the owner-approved reduction through `scope_approval` (status, reference, path and SHA-256). Do not describe inaccessible coworker evidence as newly verified. Plan 03/01 records the owner-approved timing change: the coworker checks final classifier/STT compatibility on Mac after final training, before test access.
3. Obtain separate owner approval for fresh full-pool training. The record binds the selection completion checksum, selected config checksum, exact selected CV run ID/config checksum, final run ID, persistent training directory, full-pool warmup value/rule reference, reviewer/date, and exact trainer approved-settings digest. Preview the digest with `prepare-final-config --print-settings-digest` and a draft approval record; that option prints only and writes no config. `prepare-final-config` verifies the selected CV run, frozen model/data/LR/training/runtime settings, saved train-pool assignments, and recalculates warmup using the approved rule over the full selected training pool. It writes a no-validation config only when the approved settings digest matches.
4. Run `train-final --authorized-final-training` only after the owner has explicitly authorized the training launch. The training component must export `model.safetensors` before evaluation.
5. Require the coworker's passed Mac compatibility record, using development audio and the pinned selected STT alongside final classifier weights. Obtain a separate final-test authorization record bound to that record (`mac_compatibility.path` and `.sha256`), selected config, saved assignments, test CSV, preprocessing config, selection completion, final run ID, exact model weights and artifact manifest. `infer-test --authorized-test-execution` verifies those identities before loading test records. The output directory must exactly match the authorization record.
6. Document evidence, observed error category, explanation, uncertainty, and possible future investigation for every FP/FN in `error_analysis.csv`. Tool-populated rows remain `pending_review`; an authorized project worker/agent or owner may complete the evidence review. Only consequential changes to labels or methods require owner confirmation.

Do not run any of the gated training or final-test commands until the corresponding owner approvals and plan checkpoints are resolved. A CLI flag alone is not authorization.

## Coworker Mac execution check

`check_mac_compatibility.py` prepares the deferred development-only check. It requires the verified final export, resolved selection-completion provenance and exact pinned STT snapshot; it does not bypass the current provenance blocker. Run it only after those prerequisites are ready, in the established Mac environment with PyThaiASR 2.3.0 and the pinned STT dependencies.

Choose a representative clip from the already frozen FLEURS development subset, not final audio. For example:

```sh
python "03 - MODEL DEVELOPMENT/final-evaluation/check_mac_compatibility.py" \
  --model-dir /persistent/final-run/final_model \
  --selected-config /persistent/evidence/selected_config.json \
  --completion-record /persistent/evidence/selection_completion.json \
  --input-config "03 - MODEL DEVELOPMENT/input-preparation/preprocessing_config.json" \
  --stt-snapshot /persistent/hub/snapshots/3155938c549b23eee16b1d4b55dcb161b7fe4bcf \
  --data-dir /persistent/fleurs-dev-subset \
  --audio-filename 16752839512371888944.wav \
  --classifier-device mps \
  --output-dir /persistent/mac-compatibility-unique-run
```

Paths are placeholders for the coworker's persistent storage. The classifier backend is explicitly selected for the execution check; it is not deployment approval. The selected STT remains MPS with no language model. Do not silently switch backends if it fails.

The script verifies MacBook Air/Apple M2 identity, pinned package/checkpoint weights and development-audio checksum. It keeps both models resident, transcribes the development clip, then sends the resulting transcript through the shared classifier path. It preserves loading/execution time, sampled memory, transcript/classifier trace, identities and failures in a new output directory outside Git. Serial numbers and hardware UUIDs are excluded.

Only actual successful execution writes a passed `mac_compatibility.json`. A failed run retains its evidence and exits nonzero. This is not STT quality ranking, packaged parity acceptance, test authorization or an app feasibility guarantee. Return the record and its referenced execution/resource files, not only a success message.

Local pipeline loading now resolves warmup from the frozen, checksum-bound training membership instead of requiring the original Colab dataset path. This supports relocation without copying datasets into an inference bundle; the separate selection-completion and final-test guards remain enforced.

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
