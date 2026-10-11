# Speech-to-text evaluation materials

This directory holds the reproducible code and tracked instructions for Plan 04/00. The Thai STT comparison uses Google FLEURS `th_th` development (`dev`) data at revision `70bb2e84b976b7e960aa89f1c648e09c59f894dd`. FLEURS distributes this corpus under CC BY 4.0; cite Conneau et al. (2022) and retain attribution in outputs. The dataset is read speech built from parallel FLoRes sentences, so results do not establish accuracy on spontaneous calls.

## Prepare the common comparison subset

The preparation script verifies the pinned source-file checksums, applies the approved seed-67 complete-clip sampling rule to reach at least 7.5 minutes (450 seconds), extracts only selected audio, checks each WAV against the source sample count and format, and writes the audio manifest and full selection inventory. The subset is frozen before any candidate is run. The three repetitions remain unchanged; they characterize run-to-run execution variability, not additional speech-sample coverage.

The source files and prepared audio are stored outside the Git checkout under:

`~/Library/Application Support/scam-call-alert/application-development/stt/fleurs-th-dev-70bb2e84/`

Keep the official source files (`dev.tsv`, `dev.tar.gz`) in this directory. The approved subset is written to the sibling directory `selected-7m30s/`. A previously prepared `selected-15m/` directory is superseded; do not use it for candidate evaluation.

```sh
python3 "04 - APPLICATION DEVELOPMENT/stt/prepare_fleurs_subset.py" \
  --source-dir "$HOME/Library/Application Support/scam-call-alert/application-development/stt/fleurs-th-dev-70bb2e84" \
  --output-dir "$HOME/Library/Application Support/scam-call-alert/application-development/stt/fleurs-th-dev-70bb2e84/selected-7m30s" \
  --tracked-manifest "04 - APPLICATION DEVELOPMENT/stt/audio_manifest.csv"
```

Outputs:

- The tracked `audio_manifest.csv` binds each selected recording, both source transcript fields, selection order, duration and audio checksum.
- `selection_manifest.json` records source revision/checksums, license/attribution, sampling procedure, selected and unselected IDs, validation checks and counts.
- `audio/` contains the selected original WAV files.

`requirements-macos-arm64.lock` pins the prepared Mac environment. `candidate_configs.json` records exact checkpoint/software identities and the approved standalone scope. One-clip smoke checks are compatibility diagnostics only, not benchmark results.

## Run the approved standalone comparison

The owner approved a standalone STT comparison because the official selected classifier bundle is not yet available. Do not load the provisional WangchanBERTa app fixture. This run measures transcription quality (CER), model loading and per-clip/repetition timing, failures, standalone process CPU/RSS and PyTorch MPS driver-allocated memory where applicable. Typhoon records the actual ONNX Runtime encoder/decoder providers and process RSS; the PyTorch MPS metric is not applicable. The classifier remains unloaded. The combined classifier/STT compatibility and resource check remains required during Application Integration once the official classifier is available.

The runner requires the explicit `--standalone` flag and refuses to overwrite a run directory. Before benchmarking, it downloads only the required Typhoon ONNX files from the revision pinned in `candidate_configs.json` and records SHA-256 checksums. The worker initializes PyThaiASR `FastConformerRNNT` with those explicit local file paths so the package does not fall back to mutable default download URLs. It launches one fresh subprocess per candidate, so resource readings are isolated from previously loaded candidates. Each process loads one candidate, performs one untimed warm-up, and then processes all 35 clips for three full repetitions using the documented inference settings. Per-clip outputs and resource samples are flushed during execution. A failed or incomplete run is not silently restarted or scored as complete.

```sh
STT_ROOT="$HOME/Library/Application Support/scam-call-alert/application-development/stt"
HF_HOME="$STT_ROOT/huggingface-cache" \
HF_HUB_CACHE="$STT_ROOT/huggingface-cache" \
"$STT_ROOT/env/bin/python" "04 - APPLICATION DEVELOPMENT/stt/run_stt_comparison.py" \
  --standalone \
  --output-dir "$STT_ROOT/runs/stt-20261011-four-candidate-resources"
```

When all attempts finish, score the preserved JSONL into a new directory outside Git:

```sh
"$STT_ROOT/env/bin/python" "04 - APPLICATION DEVELOPMENT/stt/score_stt_results.py" \
  --results "$STT_ROOT/runs/stt-20261011-four-candidate-resources/transcription_results.jsonl" \
  --audio-manifest "04 - APPLICATION DEVELOPMENT/stt/audio_manifest.csv" \
  --candidate-runtime "$STT_ROOT/runs/stt-20261011-four-candidate-resources/candidate_runtime.json" \
  --output-dir "$STT_ROOT/runs/stt-20261011-four-candidate-resources/scores"
```

Keep source audio and detailed per-clip/resource sample outputs in the documented Application Support directory, not Git. The aggregate `scores/metrics.csv` is also copied into the tracked `stt_metrics.csv` summary to match the plan output; the full scored tables remain in persistent external run storage. The top-level run contains one subdirectory per candidate, each with `transcription_results.jsonl`, `candidate_runtime.json`, and append-during-run `resource_samples.csv`; top-level merged results, `worker_statuses.json`, `comparison_manifest.json`, `candidate_runtime.json`, and `typhoon_model_identity.json` support scoring and audit. Report every candidate, repetition, denominator, failure and limitation. The owner selected PyThaiASR + Wav2Vec2 Thai for integration; keep it marked pending until the deferred official-classifier compatibility and resource check passes. `stt_config.json` records the selected candidate and this gate; a failed gate requires owner discussion before changing candidates.
