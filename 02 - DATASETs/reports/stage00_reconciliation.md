# Stage 00 reconciliation with main

The PR includes main through `d74766e`. Its plans are preserved; only Stage 00's task state changes to Finished after implementation and verification.

## Changes applied

- Replaced the JSONL handoff with `prepared/prepared.csv` and the four required supporting files.
- Preserved original transcripts and stable source locators.
- Changed exact comparison to line endings and whole-text edge trimming only, across both sources.
- Mapped Unknow to Not Scam. Twelve unique rows remain; one exact copy is removed.
- Replaced automatic template grouping with a candidate screen and recorded contextual reviews. Plan 01 determines split groups.
- Rebuilt tests for schema, unchanged source content, accounting, review gates, reproduction, and download integrity.

## Owner decisions

Bukutsu replied "yea" to the proposed candidate method and six integrity dispositions:

- Character 3-5 gram TF-IDF, case preserved, cosine >= 0.90; candidate matching normalizes line endings and edge whitespace only.
- Retain readable damaged calls hf_000083, hf_000191, and hf_000567 unchanged.
- Exclude unrecoverably truncated calls hf_000286, hf_000308, and hf_000439.

Source mappings follow the owner-confirmed plan without reconstructing content. Approvals and evidence bind to raw hashes in `preparation_decisions.json`.

The coding assistant reviewed all 46 candidate pairs using contextual text comparisons and changed spans. All show related variants: small wording/closing changes in wrong-number dialogues, or bank/amount substitutions in otherwise matching scam sequences. None was deleted for similarity. Reviewer identity and limits are recorded; this is not independent human verification.

## Result

1,478 raw records = 1,455 retained + 3 integrity exclusions + 20 exact duplicate removals.

The retained pool has 1,276 primary and 179 supplemental calls (692 Scam, 763 Not Scam). See [the current report](preparation_csv_v2.md) for category counts, provenance, and limitations.

The earlier 1,440-row JSONL output is superseded and remains local for history. Its counts and automatic group assignments must not be used downstream.

Ten verification tests pass. Splitting, tokenization, augmentation, resampling, learned preprocessing, and model selection have not occurred.
