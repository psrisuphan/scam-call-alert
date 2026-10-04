# Data preparation report

Preparation version: csv-v2. Canonical CSV preparation follows Plan 00 on main. The earlier JSONL v1 is superseded.

## Rules and provenance

Primary: translated dialogue -> transcript; source label 0 -> Not Scam, 1 -> Scam.
Supplemental: Text -> transcript; Type = Scam -> Scam, all other confirmed categories -> Not Scam.
Original labels are preserved as CSV values. Unknow means not labeled Scam by the source; benignity is not independently verified.
IDs are zero-based raw-row IDs (hf_000000 / kaggle_000000), assigned before filtering, never renumbered.
Primary source_record_id is the source file plus #row=N. Supplemental uses original Id; audit row locators disambiguate repeated IDs.
Transcripts are unchanged, including speaker markers, internal whitespace, punctuation, and replacement characters.
Exact comparison normalizes line endings and trims whole-text edges only. Primary, then lowest source row wins.
Three supplemental Id values repeat across different conversations. Stable sample IDs and source row locators prevent collisions.
Short calls, silence/audio-complaint logs, and English-only text are retained when readable; none is excluded merely for length, language, or Unknow category.
No labels conflict among exact copies. Every input has one final disposition; no repairs occurred.

## Review and relationships

Bukutsu approved the candidate method and six integrity dispositions in the conversation ('yea'). Details are tracked in preparation_decisions.json.
Character 3-5 gram TF-IDF, case preserved; cosine >= 0.90; brute-force coverage across both raw sources.
Candidate matching normalizes line endings and edge whitespace only. The audit vectorizer is discarded, not used for model preprocessing.
Each candidate was compared in context by the coding assistant. Reviews record evidence and reviewer identity; they do not claim independent human verification.
Candidate pairs: 46. Confirmed related: 46.
Changed spans for each reviewed pair are preserved in preparation_decisions.json; audit entries identify both related records.
Confirmed relationships appear in record_audit.csv in both directions. Plan 01 constructs connected groups among retained IDs and obtains approval of its holdout procedure.
Lexical detection can miss paraphrases or find coincidental overlap. No assertion is made that all related conversations were found.

## Before and after counts

| Source | Input | Retained | Excluded | Duplicate removals | Scam | Not Scam |
|---|---:|---:|---:|---:|---:|---:|
| primary | 1280 | 1276 | 3 | 1 | 637 | 639 |
| supplemental | 198 | 179 | 0 | 19 | 55 | 124 |

| Source | Project label | Input | Retained |
|---|---|---:|---:|
| primary | Scam | 640 | 637 |
| primary | Not Scam | 640 | 639 |
| supplemental | Scam | 73 | 55 |
| supplemental | Not Scam | 125 | 124 |

| Source | Original category | Input | Retained | Project label |
|---|---|---:|---:|---|
| primary | Genuine insurance sales calls | 160 | 160 | Not Scam |
| primary | Legitimate delivery confirmation calls | 160 | 160 | Not Scam |
| primary | Legitimate telemarketing calls | 160 | 160 | Not Scam |
| primary | Refund scams | 160 | 158 | Scam |
| primary | Reward scams | 160 | 160 | Scam |
| primary | Social security number scams | 160 | 160 | Scam |
| primary | Technical support scams | 160 | 159 | Scam |
| primary | Wrong number calls | 160 | 159 | Not Scam |
| supplemental | General | 49 | 49 | Not Scam |
| supplemental | Official | 37 | 37 | Not Scam |
| supplemental | Scam | 73 | 55 | Scam |
| supplemental | Unknow | 13 | 12 | Not Scam |
| supplemental | Verification-call | 26 | 26 | Not Scam |

## Checks and limitations

Accounting: 1478 = 1455 retained + 3 excluded + 20 duplicate removals.
Validation: unique IDs, labels, raw-content preservation, CSV roundtrip, audit accounting, source hashes, review completeness, and deterministic reproduction are checked by test_prepare.py.
Three truncated primary calls are excluded; three readable calls with replacement characters are retained unchanged by owner approval.
Both datasets are simulated. Foreign scenarios and translated dialogue do not establish real-call performance.
Primary license is undeclared; supplemental is CC BY-NC-ND 4.0. Prepared data stays local and ignored. Distribution rights require separate confirmation.
Splitting, tokenization, augmentation, resampling, learned preprocessing, and model selection have not occurred.

## Build provenance

prepare.py SHA-256: bdd86016097420563fa498f96d3fa18af80914fe49ada211a6e41d73c721372f
Decisions SHA-256: a2675de30e1d8afc2583bd7aba3aa1068851520c723bf47dcdbde7a7ab56df0e
Dependencies: pyarrow 25.0.1; scikit-learn 1.9.1.
