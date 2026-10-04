# 01 - DATA SPLIT AND EXPERIMENT DESIGN

## Purpose and scope

Create reproducible train/test and cross-validation partitions from Plan 00's prepared records. Define the data conditions for comparing primary-only training against primary + supplemental training.

This task determines record membership and verifies partition integrity. Preprocessing, model training, tuning, selection criteria, and evaluation metrics belong to later plans.

## 1. Inputs and prerequisites

Use these files under `02 - DATASETs/prepared/`:

- `prepared.csv`
- `source_manifest.csv`
- `preparation_report.md`
- `record_audit.csv`

Verify that sample IDs are unique, preparation checks are complete, and review cases are resolved. Read any confirmed conversation relationships recorded by [Plan 00](00%20-%20DATA%20PREPARATION.md).

## 2. Output structure

Keep runnable code in `02 - DATASETs/scripts/`, separate from input/output data:

```text
02 - DATASETs/scripts/
├── README.md
├── 1.download.py
├── 2.prepare.py
├── 3.test_prepare.py
├── 4.split.py
└── 5.test_split.py
```

Follow [the script guide](../02%20-%20DATASETs/scripts/README.md). Steps 1-3 acquire and verify Plan 00 inputs; step 4 creates this plan\'s approved splits; step 5 checks them and their reproduction. Keep source metadata, approvals, and `split_config.json` in the dataset folder. No model-oriented preprocessing belongs in these scripts.

```text
02 - DATASETs/prepared/
├── prepared.csv
├── source_manifest.csv
├── preparation_report.md
├── record_audit.csv
├── README.md
└── splits/
    ├── 0 - train/
    │   └── dataset.csv
    ├── 1 - test/
    │   └── dataset.csv
    ├── split_assignments.csv
    └── split_report.md
```

| Output | Purpose |
|---|---|
| `0 - train/dataset.csv` | Training pool for cross-validation and later final training. Retains Plan 00's six-column schema. |
| `1 - test/dataset.csv` | Held-out records reserved for final evaluation. Retains the same schema. |
| `split_assignments.csv` | Authoritative record of sample, group, train/test, and validation-fold membership. |
| `split_report.md` | Input provenance, algorithms, settings, achieved allocation, and verification results. |
| Updated `README.md` | Explain the files, loading procedure, and relationship to the canonical dataset. |

Track the required inputs, updated README, and split outputs at these paths in the private project repository. Teammates must be able to inspect them after cloning, without first running scripts. Source licenses and public-sharing limits still apply; keep review scratch files and executed notebooks ignored.

Retain `prepared.csv`. Train/test CSVs are derived copies and must not be edited independently. Use UTF-8 and properly quoted CSV fields to preserve multiline transcripts.

## 3. Determine whether groups are required

One complete conversation is already one record. Use ordinary stratification when conversations are independent.

Apply group constraints only when Plan 00 confirms relationships such as multiple versions, paraphrases, or segments of the same underlying conversation.

- Keep confirmed related records in one group.
- Treat connected relationships as one group.
- Assign unrelated conversations their own individual group IDs.
- Do not infer a group solely from shared source, category, or wording.
- Document group construction and its evidence.

If related groups exist, obtain owner confirmation of the group-aware holdout procedure and its achieved allocation before freezing the split. Do not invent an allocation rule or break groups to improve ratios.

## 4. Create the 80/20 train/test split

The test set represents unseen conversations from the selected simulated-data sources. It does not establish performance on real calls or unseen scam categories.

### Default: independent conversations

For each source separately:

1. Order records consistently by `sample_id`.
2. Perform a shuffled, binary-label-stratified split using seed **67** and a target test fraction of **20%**.
3. Combine the two source-specific training subsets into the training pool.
4. Combine the two source-specific test subsets into the final test set.
5. Record the resulting source and class counts, including whole-record rounding.

### Conditional: confirmed related groups

Use the owner-approved group-aware procedure across the relevant records, including groups spanning sources.

Target approximately 80/20 within each source and preserve binary class proportions as closely as feasible. Group separation takes priority over exact ratios. Report deviations and their causes.

For both approaches, select the split using only assignment constraints, not model performance.

## 5. Create five cross-validation folds

Use only the training pool.

| Record relationships | Method |
|---|---|
| Independent conversations | **Stratified K-Fold** |
| Confirmed related groups | **Stratified Group K-Fold** |

Procedure:

1. Order training records consistently by `sample_id`.
2. Create **five folds**, stratifying by the binary label.
3. Use shuffling and seed **67** where supported.
4. Assign each record to one validation fold, numbered **0–4**.
5. Where groups exist, keep every group within one fold.
6. Save the assignments and reuse them across all models and training conditions.

Each training record serves as validation once and training in the other four folds. Source-specific fold proportions are not guaranteed by binary-label stratification; document their actual counts. Group-aware stratification may only approximate class balance when group sizes or compositions constrain allocation.

## 6. Define the experiment data conditions

For validation fold `k`:

| Condition | Training records | Validation records |
|---|---|---|
| Primary only | Primary-source training-pool records outside fold `k` | All training-pool records in fold `k` |
| Primary + supplemental | Records from both sources outside fold `k` | The same records in fold `k` |

Both conditions share validation assignments. Preserve source identity so later evaluation can retrieve primary-source, supplemental-source, and combined subsets.

Do not create different splits for individual models or data conditions. Where groups exist, no member of a validation group may enter either training condition.

## 7. Save assignments and provenance

`split_assignments.csv` contains:

| Column | Definition |
|---|---|
| `sample_id` | Join key to the prepared record. |
| `source_dataset` | Source identity, matching `prepared.csv`. |
| `group_id` | Confirmed relationship group or unique individual-record group. |
| `split` | Exactly `train` or `test`. |
| `cv_fold` | Integer `0`–`4` for training records; blank for test records. |

In `split_report.md`, record:

- Prepared-file checksum and source versions.
- Group construction and evidence.
- Split/fold algorithms, settings, implementation versions, and seed.
- Counts and proportions by source and binary label for train, test, and each fold.
- Deviations, owner-approved adjustments, and verification results.

Saved assignments are authoritative; a seed alone does not guarantee identical results across implementations. Document a stable group-ID convention and do not renumber groups after saving assignments.

## 8. Verify partition integrity

Require:

- Every prepared record appears exactly once in train or test.
- Train/test sample IDs are disjoint.
- Confirmed groups never cross train/test or validation-fold boundaries.
- Every training record has exactly one valid fold assignment.
- Test records have no CV-fold assignment.
- Both classes occur in the training pool, test set, and each CV training/validation subset.
- Both classes occur in every primary-only training subset.
- Derived records exactly match their canonical records by `sample_id`.
- Source-specific counts, including empty subsets, are documented.

If valid partitions cannot be formed, report the conflict and proposed adjustment for owner confirmation. Do not silently change fold count, relax groups, or choose a split based on model scores. Related-group allocation deviations require the approval described in section 3.

## 9. Document and hand off

Update `prepared/README.md` with the output definitions and retrieval rules:

- Fold validation: training records with `cv_fold = k`.
- Fold training: training records with `cv_fold ≠ k`.
- Primary-only fold training: apply the primary-source filter to fold training.
- Final test: records assigned `split = test`.

Join records and assignments by `sample_id`, checking one-to-one membership and matching source identities. State that model-oriented preprocessing has not been performed. Pass the data files, assignments, and documentation to the subsequent plans.

Any preparation change requires regenerating and verifying affected split artifacts. Complete this task only after integrity checks pass, required approvals are recorded, and all output files and documentation agree.

## References and rationale

| Decision | Why selected |
|---|---|
| Stratified 80/20 per source | Preserves binary class proportions while ensuring both sources contribute to the holdout. Plain random splitting does not explicitly control class proportions. |
| Conditional group constraints | Prevent related-record leakage when evidence establishes dependence; avoids unnecessary grouping of independent conversations. |
| Five CV folds | Balances training-data usage, validation size, and computational cost. Two folds use less training data per run; ten require twice as many fits per configuration. |
| Shared assignments | Keeps evaluation records consistent across models and training conditions. |
| Seed and saved membership | Makes the partition reproducible and auditable. |

Supporting sources:

- [Full Proposal](../00%20-%20DOCUMENTs/Full%20Proposal/Phoebe_FullProposal.docx), sections 4.2, 6.2, and 7.1: 80/20, cross-validation, grouping, and shared splits.
- [L03 - Data Preprocessing and Feature Engineering](course-lecture-sheets/Pattern%20Recognition%20L03_Data%20Preprocessing%20and%20Feature%20Engineering_final.pdf), PDF pp. 14–15 and 43: stratification, group separation, and leakage prevention.
- [L05 - Model Selection and Hyperparameter Tuning](course-lecture-sheets/Pattern%20Recognition%20L05_Model%20Selection%20%26%20Hyperparameter%20Tuning.pdf), PDF pp. 13, 15, and 17: fold counts, Stratified K-Fold, and validation-strategy considerations.
- [L06 - Experimental Design and System Evaluation](course-lecture-sheets/Pattern%20Recognition%20L06_Experimental%20Design%20and%20System%20Evaluation.pdf), PDF pp. 11 and 19: fair comparisons and reproducibility.
- [Scikit-learn cross-validation guide](https://scikit-learn.org/stable/modules/cross_validation.html): Stratified K-Fold and Stratified Group K-Fold behavior and limitations. This supports the method definitions; no particular library is mandated.

Five folds and seed 67 are confirmed project choices. The lectures do not prescribe those exact values. The grouped holdout method remains an explicit, source-dependent approval checkpoint. Lecture PDFs are local ignored materials and may be unavailable in a fresh clone.
