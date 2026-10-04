# Stage 00 reconciliation with main

## Current state

The PR branch includes main through `d74766e`. Main's plans are preserved unchanged. Stage 00 remains Planned until its completion checks and owner review pass. The previous 1,440-row JSONL output is historical, not the canonical input to Stage 01.

## Required implementation changes

- Produce `prepared/prepared.csv` with exactly `sample_id, source_dataset, source_record_id, original_label, label, transcript`.
- Produce `source_manifest.csv`, `record_audit.csv`, `preparation_report.md`, and `README.md` alongside it.
- Preserve original transcripts. Normalize line endings and edge whitespace only in the duplicate comparison copy.
- Compare duplicates across both sources; prefer primary, then the lowest stable source locator.
- Map all supplemental categories except Scam to Not Scam, including Unknow. Do not exclude a row merely for that category.
- Preserve source labels and locators; log every disposition and relationship with evidence.
- Replace the legacy tests with CSV schema, raw-content preservation, provenance, accounting, review-gate, and reproduction checks.
- Rebuild counts and reports after resolving review cases. Do not reuse the historical counts as expected results.

## Owner checkpoints

### Near-duplicate detection proposal

Use character 3-5 gram TF-IDF, preserving case, and cosine similarity >= 0.90 to generate candidates across all input conversations, including cross-source pairs. Compare every pair via brute-force radius search. Preserve internal whitespace in candidate text; use only line-ending normalization and edge trimming.

This captures small wording substitutions, but can miss paraphrases and can flag independent calls with shared wording. Corpus-dependent TF-IDF weights make candidates dependent on the pinned input version. Similarity is evidence for review, not grounds for deletion or automatic group confirmation.

The earlier detector collapsed internal whitespace and automatically formed 14 families. Those families are not owner-confirmed. Obtain approval of the revised method before rerunning it, then review candidate relationships separately. Record reviewer, evidence, and final decisions in the audit.

### Primary source integrity cases

Both the Thai and English source fields contain these defects. No missing content was recovered; do not generate repairs.

| Sample | Evidence | Proposed disposition |
|---|---|---|
| hf_000083 | Replacement characters between otherwise readable text and the requested personal details | Retain unchanged unless owner judges the conversation unusable |
| hf_000191 | Replacement characters in a readable question; conversation has a readable ending | Retain unchanged unless owner judges the conversation unusable |
| hf_000567 | Replacement character in a readable gift-card conversation; readable ending | Retain unchanged unless owner judges the conversation unusable |
| hf_000286 | English ends "Just stay on the line and" followed by replacement characters; Thai also ends abruptly | Exclude as unrecoverably truncated |
| hf_000308 | English ends "Let's just get the refund processed now and" followed by replacement characters; Thai also ends abruptly | Exclude as unrecoverably truncated |
| hf_000439 | English ends "Why should"; Thai ends "ทำไมควร" | Exclude as unrecoverably truncated |

The historical script excluded all six automatically. The current plan requires review of uncertain usability. These proposed actions remain pending owner confirmation.

## Merge gate

Do not merge this PR as completed Stage 00 until the mandatory approvals, revised CSV implementation, candidate review, and verification are complete. No splitting, tokenization, augmentation, resampling, learned preprocessing, or model selection has occurred.
