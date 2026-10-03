# 02 - DATA PREPROCESSING AND MODEL INPUTS

## Purpose and scope

Implement and document a shared procedure that converts Plan 01's assigned conversation records into inputs compatible with each candidate model.

This task covers speaker formatting, transcript representation, label encoding, model-specific tokenization, length handling, dynamic padding, configuration, and input checks.

It preserves existing split assignments. Training, tuning, representation comparison, model selection, and final test evaluation belong to later plans.

## 1. Inputs and prerequisites

Use:

```text
02 - DATASETs/prepared/
├── preparation_report.md
├── record_audit.csv
└── splits/
    ├── 0 - train/dataset.csv
    ├── 1 - test/dataset.csv
    ├── split_assignments.csv
    └── split_report.md
```

Verify that [Plan 01](01%20-%20DATA%20SPLIT%20AND%20EXPERIMENT%20DESIGN.md)'s checks are complete. Read [Plan 00](00%20-%20DATA%20PREPARATION.md)'s source-format and speaker documentation.

Keep canonical and split CSVs unchanged. Use training-pool records for design inspection and preparation checks. The final test file is an input to the later evaluation workflow, not data to inspect during this task.

## 2. Outputs

```text
03 - MODEL DEVELOPMENT/
└── input-preparation/
    ├── README.md
    ├── preprocessing_config.json
    ├── preprocessing_report.md
    └── Shared input-preparation component
```

| Output | Purpose |
|---|---|
| `README.md` | Explain configuration, component usage, partition retrieval, and input checks. |
| `preprocessing_config.json` | Record approved role mappings, representations, label encoding, checkpoint/tokenizer revisions, length policy, and padding settings. |
| `preprocessing_report.md` | Record source-format findings, training-pool token lengths, approved decisions, checks, and limitations. |
| Shared component | Provide reusable record-to-model-input conversion for training and later evaluation. |

Code filenames and libraries are flexible. The behavior below is required. Optional caches must remain separate from canonical data.

## 3. Retrieve assigned records

The shared component must:

1. Load the requested split CSV and assignments.
2. Join by `sample_id`; verify one-to-one membership and matching source identity.
3. Consume Plan 01's saved fold membership exactly.
4. Retrieve fold training or validation records as requested.
5. Apply the primary-only source filter only to training records when that condition is requested.
6. Preserve sample IDs throughout conversion.

Do not regenerate splits or folds. Provide an explicit final-test loading mode, but do not invoke it during this task.

## 4. Map speaker roles

Use the neutral roles `Caller` and `Receiver`.

Map roles using documented source meaning, not the target label or an assumption that the first speaker is the caller. Replace label-revealing names such as `Scammer` with neutral markers.

Keep source labels, categories, IDs, and audit information out of model text.

If roles cannot be established reliably:

- Record affected samples and the ambiguity.
- Ask the project owner to confirm handling.
- Do not fabricate roles, silently discard turns, or produce unreliable caller-only inputs.

Record confirmed source-role mappings in the configuration.

## 5. Produce two representations

### Whole conversation

Retain both speakers in original order:

```text
[Caller]: …
[Receiver]: …
[Caller]: …
```

### Caller only

Retain caller turns in their original order:

```text
[Caller]: …
[Caller]: …
```

Use one turn per line, followed by a colon and one separating space. Preserve the text within each turn.

Whole conversation is the main representation; caller-only is the approved ablation representation. Prepare both here. Later plans determine comparison execution and budget.

## 6. Preserve meaning

Apply structural formatting and documented checkpoint-specific preparation only.

Preserve Thai and mixed-language text, numbers, punctuation, negations, turn boundaries, and conversational content.

Do not apply stop-word removal, stemming, automatic spelling correction, or dialogue rewriting by default. Never overwrite the original transcripts.

Document the transformation sequence. If a checkpoint requirement conflicts with the agreed formatting, present the conflict for confirmation before proceeding.

## 7. Encode labels

Use:

```text
Not Scam → 0
Scam     → 1
```

Generate numeric labels during input preparation; retain readable labels in the CSVs.

Provide the inverse mapping for prediction decoding. Reject unexpected values rather than guessing an encoding. Keep labels separate from tokenized text.

## 8. Use matching pretrained tokenizers

For each candidate checkpoint:

1. Verify its official input-preparation requirements.
2. Use the corresponding pretrained tokenizer.
3. Apply documented model-specific preparation.
4. Let the tokenizer add required special tokens.
5. Treat speaker markers as ordinary text; do not add new vocabulary tokens.
6. Record checkpoint/tokenizer identifiers, revisions, and settings.

Do not train or adapt a tokenizer on project data in the initial pipeline.

A shared procedure does not mean a shared tokenizer: each model receives its compatible representation.

## 9. Resolve length handling

Using only training-pool records:

1. Measure token lengths for each tokenizer and both representations, including special tokens.
2. Verify documented checkpoint input limits.
3. Report distributions and counts exceeding proposed limits.
4. Recommend a length policy with its information-loss and implementation tradeoffs.
5. Obtain owner confirmation before applying it.

Do not silently truncate or exclude valid conversations. Test data must not determine the policy.

If chunking is proposed, Plan 02 defines window construction. Implementation must wait until the relevant model-development plans resolve window-label handling and prediction aggregation.

Record the approved policy in configuration and apply it consistently to subsequent training, validation, and final-evaluation inputs.

## 10. Provide dynamic padding

Tokenize records without permanently padding them to a global maximum. When batches are assembled:

- Pad to the longest prepared input in that batch.
- Follow the approved length policy.
- Use checkpoint-compatible padding tokens and padding side.
- Produce attention masks and other checkpoint-required fields.

Batch size, training order, and sampling strategy belong to model training.

## 11. Preserve the sample population

The initial pipeline uses:

- No text augmentation.
- No oversampling or undersampling.

Use Plan 01's documented class counts. Do not add, duplicate, or discard conversations to balance classes.

Any later change requires confirmation and must be confined to the applicable training subset. Class-weighted loss belongs to model training.

## 12. Component interface

The component accepts:

- Data and assignment locations.
- Requested partition or fold.
- Training data condition.
- `whole_conversation` or `caller_only`.
- Approved checkpoint/tokenizer configuration.

It returns:

- Model-required input fields.
- Numeric labels.
- Sample IDs and configuration identity as separate traceability metadata.

Prevent metadata from becoming predictive input.

The initial transformations use fixed formatting and pretrained tokenizers. If learned transformations are approved later, fit them only on the applicable training subset and apply their frozen state to validation/test inputs.

## 13. Optional caches

Caching is optional. Prefer caching unpadded tokenized records; padding remains a batch operation.

Identify caches by input records/content version, representation, configuration, tokenizer revision, and length policy. Invalidate them when any dependency changes.

Keep partition membership identifiable. Never expose test caches to training or tuning. Any later learned transformation also requires identification of its fitted training subset and version.

## 14. Validate and document

Use training-pool examples to verify:

- Records match saved assignments.
- IDs remain traceable.
- Both-speaker order and content are preserved.
- Caller-only inputs contain only confirmed caller turns.
- No label-revealing markers or metadata enter text.
- Label encoding and decoding agree.
- Model/tokenizer configurations match.
- Length handling follows the approved policy.
- Padding and masks are valid.
- No augmentation or resampling occurred.
- Source CSVs remain unchanged.

Provide reusable checks for later final evaluation. Do not access the held-out test set to redesign the pipeline in this task.

Document the interface, approved settings, checks, and remaining limitations.

## Completion and handoff

Complete this task when speaker handling and length policies are resolved, both representations are supported by the shared component, checks pass, and documentation enables reproducible use.

Hand off the component, configuration, report, and README to model development. Do not execute training or the speaker-input comparison here.

## References and rationale

- [Full Proposal](../00%20-%20DOCUMENTs/Full%20Proposal/Phoebe_FullProposal.docx), section 5: consistent speaker/transcript formatting, preserved dialogue content/order, and model-specific tokenizers.
- [L03 - Data Preprocessing and Feature Engineering](course-lecture-sheets/Pattern%20Recognition%20L03_Data%20Preprocessing%20and%20Feature%20Engineering_final.pdf), PDF p. 7 and pp. 21, 24, 27, 43: consistent representations, sampling tradeoffs, meaning-preserving augmentation, training-only augmentation, and leakage prevention.
- [L06 - Experimental Design and System Evaluation](course-lecture-sheets/Pattern%20Recognition%20L06_Experimental%20Design%20and%20System%20Evaluation.pdf), PDF pp. 9–11: controlled comparison supporting the speaker-input ablation.
- [AI-in-the-Loop authors' project](https://supreme-lab.github.io/ai-in-the-loop/) and [cited paper](https://petsymposium.org/popets/2026/popets-2026-0006.pdf): multi-turn scam-dialogue research context; these do not establish that both-speaker input outperforms caller-only.
- Official documentation for each selected checkpoint/tokenizer must be verified and recorded during implementation for preparation, limits, special tokens, and padding.

Whole-conversation input preserves receiver context; caller-only removes that context and reduces input content. Their relative performance remains an experimental question. Conservative text preservation avoids deleting or rewriting potentially meaningful scam cues. Matching tokenizers preserve checkpoint compatibility. Dynamic padding reduces unnecessary padded positions compared with padding every input to a global maximum. No augmentation avoids unverified meaning/label changes; no resampling preserves the limited observed records. These are design rationales, not guarantees of better performance.

The exact speaker syntax, label codes, padding choice, and no-augmentation/no-resampling policy are confirmed project decisions. Source-role interpretation and length handling require the documented implementation checkpoints. Lecture PDFs are local ignored materials and may be unavailable in a fresh clone.
