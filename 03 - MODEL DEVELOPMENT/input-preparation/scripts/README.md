# Prepare training inputs

Continue after [dataset steps 1-5](../../../02%20-%20DATASETs/scripts/README.md). Run from the repository root.

| Step | Script | Purpose |
|---|---|---|
| 6 | `6.inspect_models.py` | Verify pinned model documentation and cache matching tokenizers. No model weights. |
| 7 | `7.measure_lengths.py` | Measure full training lengths without cutting text. |
| 8 | `8.export_inputs.py` | Save readable training text and unpadded inputs using approved limits. |
| 9 | `9.test_inputs.py` | Check saved inputs, folds, masks, labels, and exact reproduction. |

Use these pinned dependencies for each command:

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

For a checkout without exports, run step 8 without `--output` before step 9. Tests also rebuild exports in a temporary folder.

## Review and training

Open `../prepared/training_text.csv` to compare original, full-conversation, and caller-only text. These readable representations are before model-specific space handling and length limits.

The eight JSONL files hold actual model inputs, without permanent padding. Each line separates `inputs` from label, ID, source, group, and saved validation fold. Use only `inputs` as predictive features. The manifest binds files to data, assignments, code, configuration, and model revisions. Changed dependencies require a new export and verification.

Select fold membership using the shared `inputs.load_partition` component and join exported records by `sample_id`. Validation is identical for both data conditions; primary-only filters training only. Dynamic padding remains a batch operation.

Only training-pool records are exported. The final test is not processed here. Split seed 67 and all saved assignments are unchanged. Model training uses a separately recorded seed and requires approved diagnostics and hardware/model checks under its own plan.

No model weights, training, augmentation, resampling, or final-test evaluation are included. Source sharing limits still apply in this private repository.
