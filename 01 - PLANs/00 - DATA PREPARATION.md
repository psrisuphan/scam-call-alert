# 00 - DATA PREPARATION

## Purpose and scope

Obtain the two datasets specified in the proposal and produce valid, labeled, traceable conversation records ready for splitting.

This task covers acquisition, source inspection, conversion to the confirmed CSV structure, label mapping, record integrity checks, duplicate handling, and documentation. Preserve dialogue content, speaker markers, and turn order.

**Preprocessing boundary:** this task does not fit preprocessing on the dataset, generate augmented samples, resample classes, or select processing rules using model performance. Plan 01 establishes the 80/20 train/test split and cross-validation within the 80% training pool. Plan 02 (`DATA PREPROCESSING AND MODEL INPUTS`) defines approved preprocessing procedures. Plan 03 (model development) executes learned preprocessing and training-only operations within each cross-validation training fold. Validation and final test records receive only the applicable frozen transformations. Fixed record-integrity rules below apply before splitting; do not remove difficult examples based on predictions.

## 1. Directory and output structure

```text
02 - DATASETs/
├── raw/
│   └── Original dataset files in their downloaded formats
└── processed/
    ├── prepared.csv
    ├── README.md
    ├── source_manifest.csv
    ├── preparation_report.md
    └── record_audit.csv
```

| Location or file | Purpose and required contents |
|---|---|
| `raw/` | Original downloads, unchanged and distinguishable by source. |
| `prepared.csv` | One retained conversation per row using the schema in section 4. Intermediate input to Plan 01. |
| `README.md` | Directory/file descriptions, current preparation stage, completed operations, deferred operations, and next task. |
| `source_manifest.csv` | Source URL, download date, available version, local source-file path, checksum and its algorithm, license information, and original record count for each source file. Record unavailable information explicitly. |
| `preparation_report.md` | Rules and rationale, source-field mapping, identifier convention, label definitions, findings, before/after counts, limitations, and completion-check results. |
| `record_audit.csv` | Every exclusion, repair, duplicate removal, relationship finding, and flagged review case, including reasons, evidence, and disposition. |

Do not overwrite raw files. Record source-version changes and preserve their relationship to prior preparation. Use UTF-8 and correctly quoted CSV fields for commas, quotation marks, and multiline content.

Audit entries must identify the affected `sample_id`, source file and record locator, action/reason, supporting evidence, recovery attempt if applicable, related or retained representative IDs if applicable, review status, reviewer and final decision if applicable. Repair entries must include sufficient before/after information to reproduce the change. Multiple audit entries may refer to one sample; audit-entry counts are not sample counts.

## 2. Obtain and preserve the datasets

Collect the sources linked in the Full Proposal, preserving original formats in `raw/`:

| Dataset | Role | Proposal description |
|---|---|---|
| [Scam Dialogue Thai Translated](https://huggingface.co/datasets/thirdExec/scam-dialogue-thai-translated) | Primary | 1,280 conversations; eight types with 160 each; 640 Scam and 640 Not Scam. Simulated English dialogue translated into Thai. |
| [Thai Call Center Call Log Dataset](https://www.kaggle.com/datasets/jxxn03x/thai-call-center-call-log-dataset) | Supplemental | 198 samples: Scam 73, General 49, Official 37, Verification-call 26, Unknow 13. Simulated Thai dialogue. |

These are proposal counts, not verified download results. Populate `source_manifest.csv`. Compare actual counts/categories against proposal section 4. If they differ, document the discrepancy and ask the project owner which version to use before proceeding. If access or download fails, report the blocker; do not substitute another dataset.

Keep the source identity throughout preparation to support the later primary-only versus supplemental-data comparison. Both datasets are simulated; preparation does not establish their representativeness of real calls.

## 3. Inspect source structure

For each source, identify conversation fields, label fields/encoding, original record identifiers, speaker/turn representation, missing or apparently truncated content, and metadata identifying related conversations or variants.

Document the source-to-output field mapping. Obtain project-owner confirmation for mappings that require interpreting or reconstructing source content. Preserve meaningful source relationship metadata in the audit information for Plan 01. Do not discard it merely because it is outside the six core columns.

Limit inspection here to integrity, provenance, labels, and relationships needed for a valid split. Analysis that drives model/preprocessing selection is deferred to training data after splitting.

## 4. Create the shared CSV records

One conversation is one CSV row, even when its transcript contains multiple lines.

| Column | Definition |
|---|---|
| `sample_id` | Unique, stable project ID assigned before exclusions or duplicate handling. Do not renumber retained records after cleaning. |
| `source_dataset` | Source dataset identifier. |
| `source_record_id` | Original record ID; otherwise a documented source-file and row locator. Preserve access to the exact original record. |
| `original_label` | Exact original value, including numeric values or original spelling. Document any decoding separately. |
| `label` | Project target: exactly `Scam` or `Not Scam`. |
| `transcript` | Conversation preserving source speaker markers, content, and turn order. |

Document the stable ID convention and source locator ordering before processing. Re-running preparation against the same raw files and decisions must reproduce IDs and dispositions. Do not standardize speaker markers, truncate conversations, or encode model inputs here. Numeric binary-label encoding will be decided in Plan 02.

CSV and these columns are project decisions confirmed in discussion; they are not a format mandated by the proposal or lectures. They provide a simple shared representation with traceability.

## 5. Apply the confirmed label mapping

| Source | Original category | Project label |
|---|---|---|
| Primary | Source's Scam category | `Scam` |
| Primary | Source's Not Scam category | `Not Scam` |
| Supplemental | `Scam` | `Scam` |
| Supplemental | Every other existing category, including `Unknow` | `Not Scam` |

For the supplemental source, `Not Scam` means **not labeled Scam by the source**. Its inclusion of `Unknow` is explicitly confirmed by the project owner; it does not independently verify that every mapped record is benign. Preserve this limitation in the report.

Missing, unreadable, or unexpected labels are integrity issues. Flag them for owner review rather than inventing a mapping. Do not change labels to match model predictions.

## 6. Handle invalid or incomplete records

Apply these confirmed rules consistently:

1. Exclude empty or unreadable transcripts.
2. Exclude demonstrably truncated conversations if missing content cannot be recovered from the original source.
3. A short conversation alone is not evidence of incompleteness.
4. Repair only recoverable source/parsing errors. Never generate missing dialogue.
5. If many records are affected, investigate the source or parsing cause and report the extent before applying a new repair policy. No numerical trigger has been prescribed; report the counts and cause rather than inventing one.
6. Flag uncertain truncation or usability for review under section 9.

For **every excluded sample**, log its ID, source locator, detailed reason, supporting evidence, and any recovery attempt. Log every repair with reproducible before/after information. Explain defects using actual evidence; do not infer missing content solely from transcript length.

## 7. Handle exact duplicates

Compare transcripts within each source and across both sources. Create a comparison copy by standardizing line endings and trimming whitespace at the beginning/end of the whole transcript. Preserve punctuation, internal whitespace, speaker markers, and turn order. This comparison copy must not replace the stored transcript.

For identical comparison copies:

- **Same binary label:** retain one representative, preferring the primary dataset, then the lowest source locator under the documented stable ordering.
- **Conflicting binary labels:** hold the records out for owner review; do not arbitrarily choose a label or representative.

Log each removed copy and its retained representative. Preserve all source references, including cross-source duplicates. Document that primary preference may reduce the supplemental pool. Exact duplication is assessed by conversation content, not merely matching record IDs.

This conservative method avoids altering meaningful text. Formatting variants it misses may be examined in near-duplicate review.

## 8. Review near duplicates

After inspecting source structure, propose a reproducible candidate-detection method: representation, comparison rule, any threshold, and candidate-generation coverage. Explain its rationale and tradeoffs, and obtain owner confirmation before applying it. The exact method is deliberately unresolved until source inspection; workers must not silently select it.

Review candidates using these rules:

- Retain distinct conversations; high similarity alone does not justify deletion.
- Record confirmed related variants and their relationships for Plan 01's grouping discussion.
- Flag uncertain relationships for owner review.
- Document candidate pairs, evidence, review outcomes, and method limitations in the audit/report.

Do not claim that no related variants exist merely because the detector found none. Do not assume that topic or source identity alone defines a split group.

## 9. Resolve flagged cases

For label conflicts, uncertain truncation, unexpected labels, or uncertain relationships:

1. Record evidence and a proposed action in the audit.
2. Ask the project owner or designated teammate to decide.
3. Record the reviewer, final decision, and rationale.
4. Apply the approved disposition.

Continue unaffected work. Do not finalize `prepared.csv` while flagged cases remain unresolved. A worker or AI agent must not invent ground truth or new handling rules to clear the queue.

## 10. Validate and document

Before handoff, verify:

- Each retained record has a unique, nonempty ID and traceable raw source.
- Labels contain only `Scam` and `Not Scam` and follow the confirmed mapping.
- Transcripts satisfy the eligibility rules and preserve source content/order except logged repairs.
- Exact duplicates follow the confirmed representative rule.
- Every exclusion, repair, removal, and review decision has an audit entry.
- All flagged cases are resolved; confirmed relationships are available for Plan 01.
- CSV can be read back without losing multiline transcripts or changing record counts.

Reconcile unique input records as: **input = retained + excluded for integrity/review reasons + removed as duplicates**. Give each non-retained record one final disposition so totals do not double-count it. Repairs and relationship flags are additional attributes, not extra records or removal categories.

Report counts before/after preparation by source, original category, and binary label. Report exclusion reasons, duplicates, repairs, review outcomes, relationship findings, and limitations. Preserve source attribution for removed cross-source copies in the audit.

In `README.md`, state the actual completed operations and explicitly state that splitting, tokenization, augmentation, resampling, learned preprocessing, and model selection have not occurred. Explain each file and direct the next worker to Plan 01.

## Completion and handoff

Complete this task only when all checks pass, documentation is complete, and owner review is resolved. Deliver `prepared.csv`, the source manifest, audit, report, and README. The source mapping and near-duplicate method approval checkpoints are mandatory implementation steps.

Plan 01 creates the train/test files and CV assignments. After it verifies that every prepared record is assigned exactly once to train or test, remove the intermediate `prepared.csv` to avoid duplicate record storage. Preserve the documentation and audit, and update the README to reflect the new stage. Any later source/preparation change requires a documented version and reconsideration of affected split assignments.

## References and rationale

- [Full Proposal](../00%20-%20DOCUMENTs/Full%20Proposal/Phoebe_FullProposal.docx), sections 4, 5, and 7.1: source roles/counts, binary labels, preparation, and duplicate/incomplete-record handling. The owner-confirmed `Unknow` mapping resolves its handling for this task.
- [L02 - Dataset Management and Data Quality](course-lecture-sheets/Pattern%20Recognition%20L02_Dataset%20Management%20and%20Data%20Quality_final.pdf), PDF pp. 44, 48-54, 62-68: source reliability, labels, duplicates, leakage, raw preservation, documentation, and versioning.
- [L03 - Data Preprocessing and Feature Engineering](course-lecture-sheets/Pattern%20Recognition%20L03_Data%20Preprocessing%20and%20Feature%20Engineering_final.pdf), PDF pp. 14-15 and 43: related-record separation and fitting transformations only on training data.

Lecture references support the principles; the CSV schema, conservative duplicate comparison, review workflow, and output lifecycle are confirmed project implementation decisions. The lectures do not prescribe these exact filenames or rules. Lecture PDFs are local ignored materials and are not distributed with Git.
