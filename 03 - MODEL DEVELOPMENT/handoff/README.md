# Model handoff and local inference

This directory implements the local inference contract and checked bundle manifest for Plan 03/03. The component accepts already recognized, chronological, role-free text. It does not transcribe audio, parse source speaker markers, build app context, or modify the frozen classifier.

## Current state

The interface and synthetic checks are implemented, but this is **not yet a usable evaluated bundle or completed handoff**. `artifact_manifest.json` is an explicit `not_packaged` marker and intentionally fails release validation. There is no CV-selected configuration, final evaluated weights, final evaluation identity, selected model/tokenizer bundle, resolved local-host compatibility record, or owner-approved parity tolerance in the workspace. Plan 03/03 prerequisites and compatibility gates therefore remain open. No pretrained/project weights were downloaded and no dataset examples were accessed; one test saves a random tiny model only in a temporary directory to verify byte-preserving package/load behavior. Do not label synthetic checks as project model parity or performance evidence.

When the authorized final model artifacts exist, store the bundle in the project-approved persistent location (generated model bundles and sample-level parity inputs should be ignored by Git). The manifest, source, contract and aggregate report belong in the tracked handoff directory; keep secrets out of either location.

## API and CLI

`LocalClassifier` receives the evaluated model, matching tokenizer, approved input-preparation config, candidate key, and artifact version. Model construction is injected so the inference code does not create a fresh head or silently select another checkpoint. The supported bundle loader validates a nested native `model/` export through `training.trainer.load_model_for_inference`; it loads the exact pre-evaluation HF artifact and its inner checksum manifest without touching optimizer/recovery state. Model, tokenizer, and the exact shared `input-preparation/inputs.py` used in final training load from the bundle. Tokenizer class, padding/truncation sides, special-token count, checkpoint identity and token-ID bounds are checked against the frozen contract. Every tokenizer ID must fit the unchanged model embeddings; unused embedding rows in approved Camembert checkpoints are allowed. No checkpoint-cache dependency or downloads occur.

Once a real, validated bundle is present, run a local newline-delimited JSON client:

```sh
python "03 - MODEL DEVELOPMENT/handoff/inference.py" \
  --bundle "/persistent/path/to/evaluated-bundle" --device cpu
```

Send one request JSON object per line on standard input. The process writes one response object per line. `--device` is passed to the loaded model/tensors (for example `cpu` or `cuda:0`); supported devices and resource requirements must be measured on the intended host. A bundle load failure does not trigger model substitution: valid requests receive `E_MODEL_UNAVAILABLE` with null prediction fields. The CLI is a local development interface, not the mobile application or a network server.

Python clients can call `LocalClassifier.predict(request)` directly. `assemble_bundle(source_model_dir, bundle_dir, identity, preprocessing_config_source=..., evaluation_dir=..., review_audit_path=...)` verifies the pre-evaluation native export, copies it byte-for-byte under `model/`, copies the frozen input config and byte-identical shared preparation component under `runtime/inputs.py`, and derives provenance from the actual final-evaluation metrics, protocol, report, completion marker and independent review audit. It verifies that the current shared component matches the implementation hash recorded by final training. It requires complete outcome coverage and a completed audit documenting every false positive and false negative before release. It refuses to overwrite a bundle directory. `load_local_bundle(bundle_dir, device=...)` verifies both outer and nested manifests before loading. Never pass a training recovery checkpoint (`latest.pt`) as inference weights.

## Bundle manifest

`bundle_manifest.py` provides `build_manifest(bundle_dir, identity, files)`, `write_manifest(...)` and `validate_manifest(...)`. Bundle assembly derives evaluation identity from the completed evaluation directory and review audit, binding the exact evaluated weights/native manifest, selected config, preprocessing config, metrics, report, completion marker and audit checksums. The required file list includes the exact nested evaluated export (including its native artifact manifest/model config/tokenizer assets) and approved preprocessing config. Every file is listed; unmanifested files are rejected. Paths are relative to the bundle and escaping paths/symlinks are rejected.

An empty evaluation identity yields `pending_parity`; the loader refuses it. A populated identity yields `ready_for_parity`, which means only that the bundle is tied to the recorded final-evaluation artifact and is ready for development parity checks. It does **not** mean parity passed or application handoff completed. The loader requires `ready_for_parity`, valid outer and native artifact checksums, the exact pre-evaluation model directory copied byte-for-byte, and matching checkpoint/tokenizer/config identities. Quantized, converted, fallback or unpinned artifacts are rejected by this workflow.

Do not use the manifest helper to bless arbitrary artifacts: only use output from the final-evaluated training run and its approved evaluation record. Record license source URLs and any license restrictions in the identity/model card. Keep the model bundle in persistent storage and preserve a recoverable path/identity.

## Verification

Run the synthetic component/manifest checks with the project environment:

```sh
python -m unittest discover -s "03 - MODEL DEVELOPMENT/handoff/tests" -v
```

The tests use fake logits, synthetic manifests and a random tiny classifier with the already-cached Wangchan tokenizer. They cover request/response shape, role-free shared-preparation invocation, fixed threshold behavior, stable failure codes, truncation notice, manifest checksums/tamper detection, exact-byte native-model packaging/loading, adapter mapping, and synthetic live-trace comparison. They do not load any pretrained classifier weights, access a project dataset example, assess intended-host runtime, or establish parity/performance for the selected project model.

Real development parity must use only designated development fixtures and the exact role-free whole-conversation evaluation path. For training-pool examples, call `training_pool_fixtures` with rows returned by `inputs.load_partition('train_pool')`, selected sample IDs and the frozen assignment file; it verifies every ID is in the saved training split and returns assignment-checksum provenance. It reads no final-test transcripts. For independent development examples, record their separate non-test provenance. Wrap the approved `FinalEvaluationPredictor` with `FinalEvaluationAdapter`; it maps that evaluator's text argument and trace field names without recomputing the reference. `run_live_parity` calls that reference and the packaged classifier against the same fixtures, capturing preparation, masks, batching and outputs from each live path; it does not accept manually supplied predictions as its source. It verifies both predictor artifact versions against the recorded final evaluation and bundle identities. First require explicit owner approval of `atol`, reviewer and reference; the runner refuses an unapproved tolerance before executing any predictions. Compare exact prepared text, unpadded token IDs, attention masks, padded inputs, batching, and labels, then compare both class probabilities to the approved tolerance. Record model/report checksums, package fingerprint, development-fixture provenance and actual environment. Investigate every label mismatch; unresolved differences block handoff. Never use final-test records to debug packaging or choose tolerance.

The prerequisites and acceptance checklist remain in [Plan 03/03](../../01%20-%20PLANs/03%20-%20MODEL%20DEVELOPMENT/03%20-%20MODEL%20FREEZE%20AND%20APP%20HANDOFF.md). Do not mark that plan Finished until its real-bundle, host-compatibility, parity and client-invocation checks pass.
