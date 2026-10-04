# Model input preparation

Follow [Plan 02](../../01%20-%20PLANs/02%20-%20DATA%20PREPROCESSING%20AND%20MODEL%20INPUTS.md). Use the current four-condition generation; earlier two-condition exports were replaced with owner approval. Canonical data, source parsing decisions, seed-67 splits and approved token limits are unchanged.

## Files and identities

- `preprocessing_config.json`: label mapping, source-role rules/approvals, four conditions, pinned tokenizers, fixed limits and frozen source identities.
- `inputs.py`: authoritative retrieval, dataset rendering, unlabeled text preparation, verified export loading and dynamic padding.
- `preprocessing_report.md`: decisions, coverage, checks and limitations.
- `token_length_report.json`: untruncated training-only lengths by model, representation, marker condition, source and class.
- `prepared/training_text.csv`: unchanged original transcripts plus four readable conditions before checkpoint preparation/truncation; IDs, readable/numeric labels, source and fold are metadata.
- `prepared/<model>.<representation>.<marker_condition>.jsonl`: sixteen files, each covering the same 1,164 training records. Predictive fields are only inside `inputs`; labels, IDs, source, group, fold, condition identity, frozen padding contract and notices remain separate.
- `prepared/manifest.json`: file checksums and dataset/configuration/code/dependency/tokenizer provenance.

Representation is `whole_conversation` or `caller_only`; marker condition is `role_marked` or `role_free`. Marked text uses `[Caller]: …` / `[Receiver]: …`. Role-free rendering removes source structure and preserves selected spoken content/order. Remove markers before tokenization and truncation. Spoken role-like words are preserved.

## Retrieve training and validation inputs

```python
from inputs import load_config, load_partition, load_prepared, load_tokenizer, pad_batch

config = load_config()
training = load_partition("fold_train", fold=0, condition="primary_only", config=config)
validation = load_partition("fold_validation", fold=0, condition="primary_only", config=config)
train_items = load_prepared(training, "whole_conversation", "wangchanberta", config,
                            marker_condition="role_marked")
validation_items = load_prepared(validation, "whole_conversation", "wangchanberta", config,
                                 marker_condition="role_free")
tokenizer = load_tokenizer("wangchanberta", config, local_files_only=True)
batch = pad_batch(train_items[:2], tokenizer)
```

Saved assignments determine membership. The source filter applies only to training; validation is identical for both source conditions. `load_prepared` verifies provenance and membership, preserves requested order, and rejects final-test/modified records. Pass only `batch["inputs"]` as predictive features and `batch["labels"]` as targets. Batches must share a configuration identity. Each generated item carries a `padding_contract` outside predictive fields: pinned checkpoint/revision, tokenizer class, padding token/side, truncation side, special-token count and added-vocabulary identity. Batch assembly checks the supplied tokenizer against every contract and rejects incompatible or modified settings. Inputs must be unpadded, with matching field lengths and all-one attention masks; dynamic padding then follows the longest item.

For on-demand dataset conversion, use `tokenized_record(record, representation, model, config, tokenizer, marker_condition=...)`. Its default is marked for compatibility, but callers should explicitly select their condition. Training/selection decisions belong to model-development plans: marked whole-conversation training, paired marked/role-free validation, role-free selection and limited marked caller-only ablation.

## Ordinary unlabeled STT text

```python
from inputs import prepare_text

item = prepare_text("ไม่ส่ง OTP 111111\nกรุณาติดต่อธนาคาร", "wangchanberta", config, tokenizer)
inference_batch = pad_batch([item], tokenizer)
```

`prepare_text` defaults to role-free whole conversation and requires no label, source, sample ID, roles or assignments. It does not identify speakers, parse source prefixes or filter caller speech. The dataset adapter renders its research condition first, then calls this same checkpoint preparation/tokenization. Do not pass canonical source transcripts directly to the STT interface expecting it to strip their structure.

It returns model `inputs`, `configuration_id`, `padding_contract`, representation/marker metadata and `notices`: original/prepared token counts, dropped count and truncation flag. No prediction is made. Empty/non-text inputs are rejected. Native tokenizer normalization still applies; the two Thai checkpoints use the owner-approved space-marker preparation.

## Final evaluation boundary

No final-test export is created or project test transcript loaded here. Later authorized evaluation must call `load_partition("test", allow_final_test=True, config=config)`, then the dataset adapter for role-free whole conversations. The explicit gate, frozen test checksum, assignments and source/label checks protect that path. Training-only prepared exports cannot serve test records. Never tune settings from final-test inputs/results.

## Length, reproduction and limitations

Fixed inclusive limits are WangchanBERTa 510, PhayaThaiBERT 510, HPLT 512 and XLM-RoBERTa 512. Keep the beginning and required special tokens; cut excess at the end. No augmentation, resampling, learned transformations or tokenizer adaptation is performed. Length reports are descriptive, not fitted policies.

Follow [scripts 6–9](scripts/README.md) after dataset steps 1–5. Export and length-report commands refuse to overwrite completed generations; generate separately and verify first. Identity changes require new artifacts. The replacement exception is recorded in the configuration/report and Plan 02.

Marked training and role-free app inference intentionally differ; paired validation measures this sensitivity without proving marked-training superiority. Caller-only uses privileged source roles and is not an app interface. Prefix truncation can remove late scam demands. Model weights, forward compatibility, hardware feasibility, training and app integration are later tasks. With `local_files_only=True`, the loader opens the exact cached revision snapshot to avoid tokenizer-library metadata requests. Cache assets once with step 6; subsequent preparation and checks can run with `HF_HUB_OFFLINE=1`. Load tokenizers through this shared loader: conversion rejects a mismatched checkpoint or expanded vocabulary. Source licenses still govern sharing.
