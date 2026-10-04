# Label and record review

Follow [Plan 00](../01%20-%20PLANs/00%20-%20DATA%20PREPARATION.md). One sample is one source conversation. Copy its transcript unchanged and keep its original label.

## Mapping

| Source | Original value | Project label |
|---|---|---|
| Primary | 1 | Scam |
| Primary | 0 | Not Scam |
| Supplemental | Scam | Scam |
| Supplemental | General, Official, Verification-call, Unknow | Not Scam |

The supplemental negative class means not labeled Scam by its source. Unknow is included by owner confirmation, without an independent benignity claim. Unexpected or missing labels require owner review.

## Integrity

Exclude empty/unreadable or demonstrably unrecoverable truncated conversations. Short text, English-only content, or a silence/audio complaint alone does not establish incompleteness.

Owner-approved dispositions are recorded in `preparation_decisions.json`: retain hf_000083, hf_000191, and hf_000567 unchanged; exclude hf_000286, hf_000308, and hf_000439. The approvals bind to source and transcript hashes.

## Duplicates and relationships

Compare exact copies using line-ending normalization and whole-text edge trimming only. Preserve internal whitespace, punctuation, speaker markers, and turn order. Retain primary first, then the lowest source row. Conflicting labels require owner review.

The approved near-duplicate screen uses case-preserving character 3-5 gram TF-IDF cosine similarity >= 0.90 across all raw conversations. Review the full dialogue and changed spans before recording a relationship. Retain distinct variants. Shared topic or source alone is insufficient.

Record evidence, reviewer, and decision for every candidate. Uncertain cases remain pending for owner review. The build refuses incomplete or stale reviews. Do not label assistant review as independent human verification.
