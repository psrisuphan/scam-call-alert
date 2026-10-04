# Model input preparation

Stage 02 is complete under [Plan 02](../../01%20-%20PLANs/02%20-%20DATA%20PREPROCESSING%20AND%20MODEL%20INPUTS.md). Speaker handling, checkpoint preparation, and fixed prefix limits are approved. Completed training-only outputs are included for the private project handoff.

## Review the data

- [prepared/training_text.csv](prepared/training_text.csv): original transcript, formatted full conversation, and caller-only text for all 1,164 training records. Includes readable/numeric labels and saved fold membership as metadata.
- `prepared/<model>.<representation>.jsonl`: eight files of actual unpadded model inputs, one for each model/representation pair.
- [prepared/manifest.json](prepared/manifest.json): file hashes, data/assignment/configuration identities, code hashes, dependencies, and model revisions.
- [preprocessing_report.md](preprocessing_report.md): decisions, checks, coverage, and limitations.
- [token_length_report.json](token_length_report.json): full-length summaries by model, representation, source, and label.

The readable CSV is before model-specific space handling and truncation. JSONL files reflect the approved model preparation and length limits. Original dataset files and seed-67 assignments remain unchanged. No final-test inputs are exported.

## Reproduce

Follow [numbered scripts 6-9](scripts/README.md), after [dataset scripts 1-5](../../02%20-%20DATASETs/scripts/README.md). Included exports are never overwritten. The tests rebuild them separately and compare every file.

The shared library `inputs.py` is imported by scripts and later training code; it is not a numbered runnable step. Configuration and pinned model documentation are recorded in `preprocessing_config.json`. Tokenizer assets use the normal Hugging Face cache; model weights are not downloaded.

## Component use

Import `inputs` from this directory:

```python
from inputs import load_config, load_partition, load_tokenizer, tokenized_record, pad_batch

config = load_config()
training = load_partition("fold_train", fold=0, condition="primary_only", config=config)
validation = load_partition("fold_validation", fold=0, condition="primary_only", config=config)
tokenizer = load_tokenizer("wangchanberta", config, local_files_only=True)
item = tokenized_record(training[0], "whole_conversation", "wangchanberta", config, tokenizer)
batch = pad_batch([item], tokenizer)
```

The source filter applies only to training. Both data conditions share validation. Assignment/training hashes, one-to-one membership, and source identity are checked.

The component returns model `inputs`, numeric `label`, `sample_id`, and `configuration_id` separately. JSONL exports also carry source, group, split, and fold metadata. Pass only `inputs` as model features; labels are targets. Join cached items to selected records by `sample_id` and reject a stale manifest. Dynamic padding occurs only when forming a batch.

Final-test loading requires `allow_final_test=True` for the later evaluation workflow. It was not invoked on project test data in this task; loader tests use invented fixtures.

## Approved policy and remaining limits

- WangchanBERTa: 510 tokens.
- PhayaThaiBERT: 510 tokens.
- HPLT: 512 tokens.
- XLM-RoBERTa: 512 tokens.

Limits include special tokens. Keep the beginning and required special tokens; cut the excess at the end. These fixed settings apply across folds, both representations, and later final evaluation. They are checkpoint bounds or an owner-approved resource budget, not fitted percentiles.

Six speaker variants, one hash-bound boundary recovery, and three known empty trailing turns are approved. Minimal space-marker preparation for the two Thai models preserves repeated words, characters, and numbers. Native tokenizer normalization still applies.

Prefix cutting can remove late scam demands. WangchanBERTa's 510 limit exceeds its documented pretraining length of 416. All caller-only training inputs fit; some whole-conversation inputs are cut. Model-forward compatibility, hardware requirements, and performance remain untested.

The data handoff is ready for [model training](../../01%20-%20PLANs/03%20-%20MODEL%20DEVELOPMENT/00%20-%20MODEL%20TRAINING.md). That stage must obtain diagnostic-setting approval and run model/hardware feasibility checks before experiments. No augmentation, resampling, learned preprocessing, model training, tuning, or final-test evaluation has occurred.

Source licenses and public-sharing restrictions still apply to all exported text and inputs.
