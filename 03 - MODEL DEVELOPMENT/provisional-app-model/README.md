# Provisional WangchanBERTa app-development model

This directory holds the owner-approved temporary model path for beginning app/service integration before all four candidate comparisons and official model selection finish. It does not replace Plan 03/03's selected, final-evaluated handoff.

## Approved checkpoint

- Run: `wangchan-primary-max-lr5e-05-fold-0`
- Fold: 0; epoch: 3
- Model: pinned WangchanBERTa revision `b81d38df6b4755dbedec0bfea863c9956cbb963e`
- Training: primary-only, role-marked whole conversations, seed 67, LR `5e-5`, effective batch 16, three epochs
- Input policy: complete conversation in ordered 508-content-token windows, stride 381 (127-token overlap), two special tokens, class-wise max-logit pooling
- Provisional-only CV reference: role-free Scam F1 `0.948498` for this fold at epoch 3; six-fold-config mean ± sample SD was `0.962344 ± 0.013827` for the config. These values are context, not an app evaluation or final selection.

Fold 0 is one fold-trained model, not a full-train refit or the final candidate. It is used solely to wire real model loading/inference to the app and run functional smoke checks. Never use its scores or timing for candidate selection, parity acceptance, context comparison, Plan 05, or final reporting. Do not access final-test samples.

## Artifact and storage

The source epoch snapshot is retrieved from the verified Drive run folder in the manifest. Its expected SHA-256 is `167652863c3b1c844ce8697ea97c77edd5f52cefc01b05a695992e64902c6600`; the local retrieval was independently checked against the training history. Exported weights, tokenizer, and generated bundle go under the ignored `runtime-artifacts/` directory. Keep a persistent copy under `scam-call-alert/model-development/provisional-app-model/` in Drive. Do not commit these binary/model artifacts.

The complete bundle archive is [in the approved Drive folder](https://drive.google.com/drive/folders/1yehlVmJmlI6yhJ6XMh2ZLn8uJdxUQHXF) as [`provisional-wangchanberta-app-bundle.zip`](https://drive.google.com/file/d/1G7nJA8i01KBszmltQsKfzXTcmvtUFOMF/view?usp=drivesdk) (424,150,252 bytes; SHA-256 `2a00eeb00f3e5b7251e688ba06d2370e89372a20e1a3002021b7ed1e546e3af3`). The local model weight file SHA-256 is `c10305ea83d3c44573974d6e7598721966983199ed2b086fa969a3c101fa5b55`.

`export_provisional_bundle.py` validates the selected run row, exact source-snapshot hash, pinned checkpoint/revision, expected hyperparameters, output nonexistence, label order, and serialized checksums. It downloads the pinned base checkpoint/config only to construct the matching model class, then strictly replaces every state tensor with the verified trained epoch snapshot. It exports the tokenizer at the same pinned revision. It does not retrain or read any dataset records. Preserve the generated bundle manifest and checksums.

## Development inference

Run the newline-delimited JSON service from the project root:

```sh
python "03 - MODEL DEVELOPMENT/provisional-app-model/inference.py" \
  --bundle "03 - MODEL DEVELOPMENT/provisional-app-model/runtime-artifacts/wangchan-primary-max-lr5e-05-fold-0-epoch-3" \
  --device cpu
```

Request fields are `request_id` and chronological role-free `transcript`. The service applies the frozen Wangchan text conversion and the run's full-context windowing/pooling before returning `Scam` / `Not Scam` and both scores. This is deliberately different from the official handoff's Plan 02 prefix-only runtime, because the provisional model was trained and validated with overlapping windows. Do not silently route it through the official handoff loader.

This adapter is for development wiring and functional checks only. It is not a substitute for selected-model packaging, official parity, local-host compatibility acceptance, STT/context screening, or end-to-end evaluation. Replace it with the official model bundle and rerun affected integration checks before those later gates.

## Export and verification

Install the Plan 02 tokenizer requirements and PyTorch in the project environment, then export from the verified snapshot:

```sh
python "03 - MODEL DEVELOPMENT/provisional-app-model/export_provisional_bundle.py" \
  --snapshot "03 - MODEL DEVELOPMENT/provisional-app-model/runtime-artifacts/source-epoch-003.safetensors" \
  --output "03 - MODEL DEVELOPMENT/provisional-app-model/runtime-artifacts/wangchan-primary-max-lr5e-05-fold-0-epoch-3"
```

The local bundle directory is ignored by Git. The script refuses overwrite. Verify a synthetic-text CLI response and all bundle checksums before connecting it to the app. A synthetic smoke check establishes loader/contract operation only, not prediction quality.
