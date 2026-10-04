# Model input preparation

Stage 02 is complete locally under [Plan 02](../../01%20-%20PLANs/02%20-%20DATA%20PREPROCESSING%20AND%20MODEL%20INPUTS.md). Speaker handling, checkpoint preparation, and fixed prefix limits are approved and checked across the full training pool. See [the report](preprocessing_report.md).

## Files

- `inputs.py`: one-to-one split retrieval, approved speaker formatting and boundary recovery, whole-conversation and caller-only representations, readable/numeric labels, guarded tokenizer conversion, and dynamic padding.
- `preprocessing_config.json`: pinned checkpoint revisions, tokenizer metadata, dependency versions, split hashes, confirmed settings, and owner approval references.
- `inspect_models.py`: verify official documentation hashes and download matching tokenizer assets. No model weights or remote code.
- `measure_lengths.py`: measure full training lengths without truncation or final-test loading.
- `token_length_report.json`: aggregate distributions and estimated coverage by model, representation, source, and label. No transcripts or individual token sequences.
- `test_inputs.py`: loader, representations, content/order, approval gates, training-pool checks, length-report checks, and full-training-pool tokenization and padding checks, plus invented-text failure tests.

## Verify

Run from the repository root:

```bash
uv run --no-project --with transformers==4.57.6 --with tokenizers==0.22.2 --with huggingface-hub==0.36.2 --with sentencepiece==0.2.2 --with protobuf==7.36.2 python '03 - MODEL DEVELOPMENT/input-preparation/inspect_models.py'
uv run --no-project --with transformers==4.57.6 --with tokenizers==0.22.2 --with huggingface-hub==0.36.2 --with sentencepiece==0.2.2 --with protobuf==7.36.2 python '03 - MODEL DEVELOPMENT/input-preparation/measure_lengths.py'
uv run --no-project --with transformers==4.57.6 --with tokenizers==0.22.2 --with huggingface-hub==0.36.2 --with sentencepiece==0.2.2 --with protobuf==7.36.2 python '03 - MODEL DEVELOPMENT/input-preparation/test_inputs.py'
```

Tokenizers use the normal Hugging Face cache outside this repository. No project token cache is created.

## Component use

Import `inputs` from this directory. `load_partition` supports `train_pool`, `fold_train`, `fold_validation`, and explicit `test` mode. Supply `fold=0..4` for fold partitions.

```python
from inputs import load_config, load_partition, load_tokenizer, tokenized_record, pad_batch

config = load_config()
training = load_partition("fold_train", fold=0, condition="primary_only", config=config)
validation = load_partition("fold_validation", fold=0, condition="primary_only", config=config)
tokenizer = load_tokenizer("wangchanberta", config, local_files_only=True)
item = tokenized_record(training[0], "whole_conversation", "wangchanberta", config, tokenizer)
batch = pad_batch([item], tokenizer)
```

The source filter applies only to training. Validation is shared across both conditions. Assignment and training-file hashes must match configuration; CSV membership and source identity are checked.

Final test requires `allow_final_test=True` for the later evaluation workflow. It has not been loaded for design inspection. The test-loader mechanism is tested with invented fixtures only.

`tokenized_record` returns model `inputs`, numeric `label`, `sample_id`, and `configuration_id` separately. It refuses pending approvals. Configuration identity includes model and representation. `pad_batch` pads only to the longest sequence in the current batch, keeps IDs/labels outside model text, and rejects mixed configurations.

## Approved handling and length policy

The owner approved all six translated/named speaker mappings, the hash-bound hf_000424 boundary recovery, and preservation of the three known empty trailing turns. All 1,164 training records now produce both representations. Source CSVs and split membership are unchanged.

WangchanBERTa and PhayaThaiBERT use approved minimal space-marker preparation without repetition removal. This deliberately differs from full upstream normalization.

`checkpoint_text` provides the same approved text preparation to measurement and production conversion. Measurement uses matching pinned tokenizers, with special tokens, no padding, and no truncation. Tokenizers must already be cached by `inspect_models.py`.

Approved limits including special tokens: WangchanBERTa 510, PhayaThaiBERT 510, HPLT 512, XLM-RoBERTa 512. All use fixed prefix truncation: keep the beginning and required special tokens, cutting the excess at the end. Apply the same settings across folds, both representations, and later final evaluation. Values come from checkpoint bounds or an owner-approved resource budget, not a fitted percentile.

WangchanBERTa at 510 retains more training context than 416 but exceeds its documented pretraining length. Prefix truncation may remove late scam demands. All caller-only training inputs fit; some whole-conversation inputs are cut. These limits affect only model-input copies, not stored transcripts.

No project token sequences are written to disk. All 1,164 records have been checked with all four tokenizers and both representations, including exact prefix/special-token handling and dynamic padding. Model-forward execution and performance remain untested. The next task is [model training](../../01%20-%20PLANs/03%20-%20MODEL%20DEVELOPMENT/00%20-%20MODEL%20TRAINING.md).

No augmentation, resampling, learned preprocessing, model training, tuning, or final test evaluation has occurred.
