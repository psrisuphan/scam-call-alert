# Data quality inspection report (v1)

Historical initial inspection snapshot. Its flags and detector settings are superseded by the CSV preparation. For current counts and decisions, read [the CSV preparation report](preparation_csv_v2.md).

## Raw dataset counts

| Source | Raw rows | Excluded | Label corrections |
| --- | ---: | ---: | ---: |
| Primary (Hugging Face) | 1,280 | 0 | 0 |
| Supplemental (Kaggle) | 198 | 0 | 0 |
| Total | 1,478 | 0 | 0 |

This inspection run only checks quality issues and generates review queues. It does not delete rows or change labels.

## Automated inspection summary

- Exact duplicate groups: 12 groups, containing 20 redundant copies. [Review exact duplicate groups](../review/inspection_001/exact_duplicates.md).
- Exact label conflicts: 0. Same-text calls share the same source label.
- Near-duplicate candidate pairs: 46 pairs (character 3-5 gram TF-IDF cosine similarity >= 0.90). [Review near-duplicate pairs](../review/inspection_001/near_duplicate_candidates.md).
- Near-duplicate label conflicts: 0.
- Cross-source matches: 0. The two datasets share no identical or near-duplicate texts.
- Formatting changes: 0 rows affected by line-ending and whitespace trim checks.
- Review queue: 270 rows (72 primary, 198 supplemental).

| Flag | Flagged rows | Review target |
| --- | ---: | --- |
| control_or_replacement_character | 5 | [Replacement characters in text](../review/inspection_001/control_or_replacement_character.md) |
| duplicate_source_id | 6 | [Kaggle ID collisions: 00101, 00130, 00140](../review/inspection_001/duplicate_source_id.md) |
| exact_duplicate | 32 | [Identical conversation texts](../review/inspection_001/exact_duplicate.md) |
| near_duplicate_candidate | 47 | [High-similarity call templates](../review/inspection_001/near_duplicate_candidate.md) |
| no_thai_characters | 21 | [Pure English or placeholder texts](../review/inspection_001/no_thai_characters.md) |
| short_text_under_100_characters | 104 | [Short texts, OTPs, or quick alerts](../review/inspection_001/short_text_under_100_characters.md) |
| unresolved_label | 13 | [Unknow category calls in Kaggle CSV](../review/inspection_001/unresolved_label.md) |

Flags overlap across rows. A flag signals a need for inspection, not a confirmed defect.

Review links:
- [All supplemental conversations](../review/inspection_001/review_all_supplemental.md)
- [Primary category sample conversations](../review/inspection_001/primary_category_sample.md)
- [Review queue data file](../review/inspection_001/review_queue.jsonl)
- [Labeling guidelines](../labeling_guideline.md)

## Evaluation against five quality dimensions

1. Completeness: Automated checks confirmed zero blank cells. Manual inspection is required to catch cut-off sentences or missing context.
2. Accuracy: Source labels remain intact during inspection. The 13 Unknow rows were later excluded as ambiguous and incomplete during preparation.
3. Consistency: Source schemas are uniform. Kaggle ID collisions mean row index must be used for unique keys.
4. Representativeness: Both datasets contain synthetic dialogues. Translated scenarios include western government agencies (IRS, SSA, FTC) that do not represent Thai call patterns.
5. Reliability: All raw downloads are pinned by commit hash and SHA-256 checksum. License terms must be confirmed before distributing derivatives.

## Next steps

1. Resolve all pending review items using `labeling_guideline.md`.
2. Connect near-duplicate templates into `group_id` clusters to prevent data leakage during splitting.
3. Export clean dataset version v1 using `prepare.py`.
4. Keep the TF-IDF audit vectorizer isolated. Fit tokenizers and feature extractors inside training folds only.

## Evidence files

- Inspection notebook: `02 - DATASETs/inspection.ipynb`
- Executed notebook: `02 - DATASETs/inspection.executed.ipynb`
- Summary metrics: `02 - DATASETs/reports/inspection_v1.json`
- Review batches: `02 - DATASETs/review/inspection_001/`
