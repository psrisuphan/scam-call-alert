# Prepare training inputs

Continue after [dataset steps 1-5](../../../02%20-%20DATASETs/scripts/README.md). Run from the repository root.

| Step | Script | Purpose |
|---|---|---|
| 6 | `6.inspect_models.py` | Verify pinned model documentation and cache matching tokenizers. No model weights. |
| 7 | `7.measure_lengths.py` | Measure full training lengths for all four conditions without cutting text. |
| 8 | `8.export_inputs.py` | Save four readable conditions and sixteen unpadded model-input files. |
| 9 | `9.test_inputs.py` | Check saved inputs, folds, masks, labels, and exact reproduction. |

For a fresh checkout without generated outputs, use these pinned dependencies for each command. In the current checkout, outputs already exist: run step 9 to verify them, or use separate output paths to regenerate steps 7–8.

```bash
uv run --no-project --with transformers==4.57.6 --with tokenizers==0.22.2 --with huggingface-hub==0.36.2 --with sentencepiece==0.2.2 --with protobuf==7.36.2 python '03 - MODEL DEVELOPMENT/input-preparation/scripts/6.inspect_models.py'
uv run --no-project --with transformers==4.57.6 --with tokenizers==0.22.2 --with huggingface-hub==0.36.2 --with sentencepiece==0.2.2 --with protobuf==7.36.2 python '03 - MODEL DEVELOPMENT/input-preparation/scripts/7.measure_lengths.py'
uv run --no-project --with transformers==4.57.6 --with tokenizers==0.22.2 --with huggingface-hub==0.36.2 --with sentencepiece==0.2.2 --with protobuf==7.36.2 python '03 - MODEL DEVELOPMENT/input-preparation/scripts/9.test_inputs.py'
```

Completed exports are included under `../prepared/`. Script 8 refuses to replace them. To reproduce an export separately:

```bash
work=$(mktemp -d)
uv run --no-project --with transformers==4.57.6 --with tokenizers==0.22.2 --with huggingface-hub==0.36.2 --with sentencepiece==0.2.2 --with protobuf==7.36.2 python '03 - MODEL DEVELOPMENT/input-preparation/scripts/8.export_inputs.py' --output "$work/prepared"
diff -r '03 - MODEL DEVELOPMENT/input-preparation/prepared' "$work/prepared"
```

For a checkout without exports, run step 8 without `--output` before step 9. Step 7 also refuses to overwrite an existing report; use `--output "$work/token_length_report.json"` for separate regeneration. Tests also rebuild exports in a temporary folder.

## Review and training

Open `../prepared/training_text.csv` to compare original text and the marked/role-free versions of full-conversation and caller-only text. These readable representations are before model-specific space handling and length limits.

The sixteen JSONL files hold actual model inputs, without permanent padding. Each line separates `inputs` from label, ID, source, group, and saved validation fold. Use only `inputs` as predictive features. The manifest binds files to data, assignments, code, configuration, marker conditions and model revisions. Use `inputs.load_prepared` to reject stale exports and retrieve selected records. Changed dependencies require a new export and verification.

Select fold membership using `inputs.load_partition`, then retrieve verified exports using `inputs.load_prepared`; it checks identities and joins by `sample_id`. Validation is identical for both data conditions; primary-only filters training only. Dynamic padding remains a batch operation.

Only training-pool records are exported. The final test is not processed here. Split seed 67 and all saved assignments are unchanged. Model training uses a separately recorded seed and requires approved diagnostics and hardware/model checks under its own plan.

No model weights, training, augmentation, resampling, or final-test evaluation are included. Source sharing limits still apply in this private repository.

## Verify a separately generated replacement

With the same pinned dependencies, generate the length report with step 7's `--output` and exports with step 8's `--output`. Run step 9 with `SCAM_INPUT_CHECK_EXPORT` pointing to that prepared directory and `SCAM_INPUT_CHECK_LENGTHS` to that report. Defaults verify the current project outputs. Tests rebuild in temporary storage and compare every file.

Step 9 checks all sixteen combinations, dataset/STT parity, role-free collisions, metadata separation, lengths, truncation, dynamic padding, frozen retrieval and stale-artifact rejection. Synthetic test fixtures are used; project held-out transcripts are not loaded. Main training inputs remain marked; role-free inputs support paired validation and later inference.

After step 6 caches the pinned tokenizer assets, steps 7–9 support `HF_HUB_OFFLINE=1`. The shared loader uses the exact local revision snapshot and does not query model metadata. No model weights are needed.

Batch-padding regression checks also reject the wrong checkpoint (including another tokenizer with the same pad ID/class), changed padding token/side or truncation side, added vocabulary, missing padding contracts and invalid unpadded masks/field lengths. Contract fields are metadata; only `inputs` reach the model.
