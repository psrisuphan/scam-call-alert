# 02 - DATA PREPROCESSING AND MODEL INPUTS

## Purpose and scope

Implement and document a shared procedure that converts Plan 01's assigned conversation records into inputs compatible with each candidate model.

This task covers documented source-role parsing, whole-conversation/caller-only representations and marked/role-free conditions, label encoding, model-specific tokenization, length handling, dynamic padding, configuration, and input checks.

It preserves existing split assignments. Training, tuning, model selection, and final test evaluation belong to later plans.

The owner approved restoring marked training, paired marked/role-free validation and a limited caller-only comparison. Existing marked exports may be reused only after verifying content/configuration/provenance; they are not role-free inputs. Preserve existing evidence and generate missing conditions with distinct identities before declaring this task complete. Existing recorded owner approvals for fixed token budgets and content-preserving checkpoint preparation remain applicable unless a demonstrated conflict requires renewed confirmation. Recompute descriptive coverage for role-free text; do not reopen those approvals merely because generic checkpoints appear below.

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
    ├── token_length_report.json
    ├── inputs.py
    ├── scripts/
    │   ├── README.md
    │   ├── 6.inspect_models.py
    │   ├── 7.measure_lengths.py
    │   ├── 8.export_inputs.py
    │   └── 9.test_inputs.py
    └── prepared/
        ├── training_text.csv
        ├── manifest.json
        └── <model>.<representation>.<marker_condition>.jsonl
```

| Output | Purpose |
|---|---|
| `README.md` | Explain configuration, component usage, partition retrieval, and input checks. |
| `preprocessing_config.json` | Record source-role parsing rules, representations and marker conditions, label encoding, checkpoint/tokenizer revisions, length policy, and padding settings. |
| `preprocessing_report.md` | Record source-format findings, training-pool token lengths, approved decisions, checks, and limitations. |
| Shared component | Provide reusable record-to-model-input conversion for training and later evaluation. |

Keep executable scripts in `scripts/`, numbered 6-9 after dataset steps 1-5, with [a short reproduction guide](../03%20-%20MODEL%20DEVELOPMENT/input-preparation/scripts/README.md). The shared `inputs.py` library remains beside configuration for import by scripts and training code.

Include completed training-only readable text and unpadded model-input exports under `prepared/` in the private project repository. Preserve original text for comparison in `training_text.csv`. Store labels, IDs, source, group, and saved fold separately from predictive input fields. The manifest must bind exports to input/configuration/code versions, dependencies, and tokenizer revisions. Do not overwrite completed exports; regenerate separately and verify exact reproduction. Owner-approved exception (2026-10-04): replace the superseded two-condition generation after separately generating and verifying the four-condition replacement; keep only the generation satisfying this plan at the current paths. Do not change canonical records or assignments. Source licenses still govern sharing.

No final-test export is created during this task. Exporting the full training pool does not fit a learned rule or change membership. Fold training, validation, and source filtering must still follow saved assignments. Model weights and model execution belong to subsequent plans.

Code filenames and libraries are flexible beyond this agreed layout. The behavior below is required. Optional caches must remain separate from canonical data.

## 3. Retrieve assigned records

The shared component must:

1. Load the requested split CSV and assignments.
2. Join by `sample_id`; verify one-to-one membership and matching source identity.
3. Consume Plan 01's saved fold membership exactly.
4. Retrieve fold training or validation records as requested.
5. Apply the primary-only source filter only to training records when that condition is requested.
6. Preserve sample IDs throughout conversion.

Do not regenerate splits or folds. Provide an explicit final-test loading mode, but do not invoke it during this task.

## 4. Parse documented source roles

Use source roles to prepare marked training and paired validation inputs. The app consumes role-free whole-conversation text. This replaces the earlier role-free-training-only scope; caller-only is a limited research comparison, not the app interface.

Identify prefixes/role fields from documented source meaning, not target labels or first-speaker assumptions. Map to neutral Caller/Receiver roles for marked rendering and caller selection. Do not delete spoken names/role-like words. Unknown roles or ambiguous boundaries require owner confirmation; never silently discard turns or records. Label-revealing Scammer/Victim markers must not enter predictive text.

Record source-format parsing and rendering rules in configuration. Ambiguous structural boundaries require owner confirmation before applying a new parsing rule. Keep labels, categories, IDs, and audit metadata out of predictive text.

Canonical and split CSVs retain their original transcripts; this change applies only during model-input preparation.

Separate source parsing/rendering from shared checkpoint preparation/tokenization. The dataset adapter constructs the chosen representation/marker condition; the service supplies already role-free text. Do not apply source-prefix detection to STT text, fabricate speaker boundaries, or delete spoken role-like words.

## 5. Produce two representations and two marker conditions

Support `whole_conversation` (both speakers) and `caller_only` (confirmed caller turns), preserving chronological order. Each supports `role_marked` and `role_free`. Marked format is one turn per line: `[Caller]: …` or `[Receiver]: …`; caller-only includes only Caller turns. Role-free rendering removes structural prefixes but retains the selected spoken content and source-turn separators. For example:

```text
ข้อความที่พูดในช่วงแรก
ข้อความตอบกลับ
ข้อความที่พูดต่อมา
```

STT inference supplies recognized text in chronological order without requiring known speaker turns, speaker identifiers, or caller/receiver attribution. Preserve its spoken text and ordering through the same compatible input-preparation procedure; do not invent source-style turns from speaker assumptions.

Construct representations and marker conditions before checkpoint preparation, tokenization and truncation; do not strip marker tokens from already-truncated inputs. Main training uses marked whole conversations; caller-only training uses marked caller speech. Each validates with and without markers. App inference uses only role-free whole dialogue; no caller attribution is required there.

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
5. Render only approved neutral prefixes for marked conditions; treat them as ordinary text, not new vocabulary tokens. Role-free conditions add no markers.
6. Record checkpoint/tokenizer identifiers, revisions, and settings.

Do not train or adapt a tokenizer on project data in the initial pipeline.

A shared procedure does not mean a shared tokenizer: each model receives its compatible representation.

## 9. Resolve length handling

Using only training-pool records:

1. Measure token lengths for each tokenizer, representation and marker condition, including special tokens.
2. Verify documented checkpoint input limits.
3. Report distributions and counts exceeding proposed limits.
4. Recommend a length policy with its information-loss and implementation tradeoffs.
5. Obtain owner confirmation before applying it.

Do not silently truncate or exclude valid conversations. Test data must not determine the policy.

Distinguish fixed design settings from rules learned from project data:

- A fixed limit chosen from documented checkpoint constraints and an owner-approved resource budget may be shared across folds. Training-pool length summaries describe coverage; they must not silently become fitted parameters.
- A data-derived rule, such as a token-length percentile, must be derived separately from each fold's eligible training records, excluding validation records and any source excluded by the training condition. Apply that frozen rule to the fold's validation inputs. For later final training, derive it from the eligible full training pool and freeze it before test evaluation.
- Comparing length strategies using prediction scores belongs to the tuning plan and uses validation results, never final test results.

Record whether the approved policy is fixed or data-derived. For a data-derived policy, save the fitted value and training-subset identity for each run; do not reuse one globally fitted value across CV folds.

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

Provide an unlabeled text-preparation entry point accepting transcript text and frozen preprocessing configuration/required fitted state. It returns model-required inputs and processing notices without requiring labels, source membership or split assignments. The dataset wrapper and local inference service call the same underlying conversion; dataset labels and provenance remain separate metadata. Preserve all approved conversion, length and training-only fitting boundaries.

The dataset wrapper interface follows below.

The component accepts:

- Data and assignment locations.
- Requested partition or fold.
- Training data condition.
- Requested `whole_conversation` or `caller_only` representation and `role_marked` or `role_free` marker condition.
- Approved checkpoint/tokenizer configuration.

It returns:

- Model-required input fields.
- Numeric labels, separate from predictive input.
- Sample IDs and configuration identity as separate traceability metadata.

Prevent metadata from becoming predictive input.

The initial transformations use fixed formatting and pretrained tokenizers. If learned transformations are approved later, fit them only on the applicable training subset and apply their frozen state to validation/test inputs.

## 13. Optional caches

Caching is optional. Prefer caching unpadded tokenized records; padding remains a batch operation.

Identify caches by input records/content version, representation, marker condition, configuration, tokenizer revision, and length policy. Invalidate them when any dependency changes.

Keep partition membership identifiable. Never expose test caches to training or tuning. Any later learned transformation also requires identification of its fitted training subset and version.

## 14. Validate and document

Use training-pool examples to verify:

- Records match saved assignments.
- IDs remain traceable.
- Whole-conversation content/order is preserved; caller-only contains only documented caller turns in order.
- Marked conditions use neutral roles; paired role-free conditions remove only structural prefixes without deleting spoken words.
- No label-revealing markers or metadata enter text.
- Label encoding and decoding agree.
- Model/tokenizer configurations match.
- Length handling follows the approved policy.
- Padding and masks are valid.
- No augmentation or resampling occurred.
- Source CSVs remain unchanged.

Check development records for identical role-free text created by structural-marker removal. Record IDs and evidence; similarity alone does not authorize deletion. If collisions reveal previously missed related conversations, pause affected work and obtain owner confirmation before revising preparation or assignments. Do not automatically delete records, regenerate splits, or inspect held-out test content during this task.

Provide reusable checks for later final evaluation. Do not access the held-out test set to redesign the pipeline in this task.

Document the interface, approved settings, checks, and remaining limitations.

## Completion and handoff

Complete when source parsing/length policies are resolved, all four dataset conditions and the unlabeled role-free inference interface are supported, checks pass and documentation enables reproducible use.

Hand off the component, configuration, report, and README to model development. Do not execute training or model comparisons here.

## References and rationale

- [Full Proposal](../00%20-%20DOCUMENTs/Full%20Proposal/Phoebe_FullProposal.docx), section 5: consistent speaker/transcript formatting, preserved dialogue content/order, and model-specific tokenizers.
- [L03 - Data Preprocessing and Feature Engineering](course-lecture-sheets/Pattern%20Recognition%20L03_Data%20Preprocessing%20and%20Feature%20Engineering_final.pdf), PDF p. 7 and pp. 21, 24, 27, 43: consistent representations, sampling tradeoffs, meaning-preserving augmentation, training-only augmentation, and leakage prevention.
- [L06 - Experimental Design and System Evaluation](course-lecture-sheets/Pattern%20Recognition%20L06_Experimental%20Design%20and%20System%20Evaluation.pdf), PDF pp. 9–11: consistent preprocessing and controlled comparisons.
- [L05 - Model Selection and Hyperparameter Tuning](course-lecture-sheets/Pattern%20Recognition%20L05_Model%20Selection%20%26%20Hyperparameter%20Tuning.pdf), PDF pp. 32–33: consistent pipelines and fitting preprocessing separately within each CV training portion.
- L06, PDF p. 18: fit data-dependent transformations within each training split, then transform validation/test inputs with the frozen result.
- [AI-in-the-Loop authors' project](https://supreme-lab.github.io/ai-in-the-loop/) and [cited paper](https://petsymposium.org/popets/2026/popets-2026-0006.pdf): multi-turn scam-dialogue research context; these do not establish that both-speaker input outperforms caller-only.
- Official documentation for each selected checkpoint/tokenizer must be verified and recorded during implementation for preparation, limits, special tokens, and padding.

Marked training preserves available source-role information. Role-free validation measures the intentional training/inference mismatch because ordinary app STT does not provide reliable Caller/Receiver attribution. The diagnostic measures sensitivity to marker removal, not superiority of marked training; separate training would be needed to establish that. Caller-only tests dialogue-content effects with privileged source roles and cannot establish app feasibility. Conservative text preservation avoids deleting or rewriting potentially meaningful scam cues. Matching tokenizers preserve checkpoint compatibility. Dynamic padding reduces unnecessary padded positions compared with padding every input to a global maximum. No augmentation avoids unverified meaning/label changes; no resampling preserves the limited observed records. These are design rationales, not guarantees of better performance.

Representation/marker conditions, label codes, padding choice, and no-augmentation/no-resampling policy are confirmed project decisions. Source structural-marker parsing and length handling require the documented implementation checkpoints. Lecture PDFs are local ignored materials and may be unavailable in a fresh clone.
