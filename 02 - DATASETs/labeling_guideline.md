# Label review guideline (v1)

> Historical JSONL v1 work. It does not meet the current Stage 00 plan and is not an approved handoff. The plan requires CSV outputs, `Unknow` mapped to `Not Scam`, conservative exact matching, and owner-reviewed relationships. See [reconciliation](reports/stage00_reconciliation.md).

Data preparation rules and category mappings for dataset version v1.

## Unit of classification

Each sample is one complete phone call dialogue in chronological order.

Labels:
- `1 = Scam`: Phone dialogues showing deceit to obtain money, banking credentials, sensitive personal information, or one-time passcodes.
- `0 = Not Scam`: Ordinary phone conversations, customer service calls, delivery confirmations, or official notifications without deceptive requests.
- Exclude: Calls with ambiguous labels, incomplete dialogue, encoding corruption, or pure placeholder text.

## Source handling and label mapping

### Primary dataset (Scam Dialogue Thai Translated)
- Source labels are binary (`1 = Scam`, `0 = Not Scam`).
- 8 categories with 160 calls each (1,280 raw calls).
- Retained 1,273 clean calls:
  - 1 redundant exact duplicate pruned (`hf_001143` == `hf_001138`).
  - 5 corrupted texts with `\ufffd` bytes excluded (`hf_000083`, `hf_000191`, `hf_000286`, `hf_000308`, `hf_000567`).
  - 1 dialogue cut off mid-sentence excluded (`hf_000439`).

### Supplemental dataset (Thai Call Center Call Log)
- 198 raw calls across 5 categories.
- Category mapping:
  - `Scam` (73 raw): Mapped to `1 = Scam`. 18 exact duplicate copies pruned, retaining 55 unique Scam dialogues.
  - `General` (49 raw): Mapped to `0 = Not Scam`. All 49 retained.
  - `Official` (37 raw): Mapped to `0 = Not Scam`. All 37 retained.
  - `Verification-call` (26 raw): Mapped to `0 = Not Scam`. All 26 retained.
  - `Unknow` (13 raw): Excluded as ambiguous and incomplete dialogues.
- Retained: 167 clean calls (55 Scam, 112 Not Scam).

## Decision values in audit logs

Recorded in `processed/v1/decisions.jsonl`:

| Decision | Meaning |
| --- | --- |
| `keep` | Included in prepared dataset (`final_label` = 0 or 1) |
| `exclude` | Removed from prepared dataset (`final_label` = null) |

Exclusion reason codes:
- `ambiguous_label`: The 13 `Unknow` category dialogues.
- `exact_duplicate`: Redundant identical dialogue texts (18 in Kaggle, 1 in Hugging Face).
- `source_corruption`: Replacement characters (`\ufffd`) in source text.
- `incomplete_source`: Dialogue cut off mid-sentence.

## Duplicate and split group handling

1. Exact duplicates: Matched by collapsing internal whitespace while preserving lettercase and punctuation. Keep the first occurrence; link duplicates via `duplicate_of`.
2. Near duplicates: Screened using character 3-5 gram TF-IDF cosine similarity >= 0.90. Clustered under shared `group_id` keys so they remain in the same split partition during stage 01.
3. Kaggle ID collisions: Kaggle reused IDs `00101`, `00130`, and `00140`. Unique conversation IDs use sequential zero-based row indices (`kaggle_000000` through `kaggle_000197`).

## Text normalization

- Strip leading and trailing whitespace.
- Normalize line endings (`\r\n` to `\n`).
- Preserve all speaker labels, phone numbers, URLs, account numbers, and punctuation.
