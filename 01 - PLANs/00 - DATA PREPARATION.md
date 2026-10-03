# 00 - Data preparation

## Goal

Build traceable, reviewed Thai call datasets for binary Scam vs Not Scam classification. Keep primary and supplemental sources separate so we can run controlled experiments comparing primary-only training against primary-plus-supplemental training. One sample equals one complete phone dialogue. The classifier takes conversation text as its only input.

Course references:
- Chapter 2: slides 29, 32-44, 46-54, 62-70 (dataset quality, inspection, organization, and labeling)
- Lab 1: Task 1 (inspection, distributions, quality issues) and Task 2 (before-and-after checks)
- Chapter 6: slides 15-18 (group splits and data leakage prevention)

## Status checklist

- [x] Download raw sources and pin revisions, versions, and SHA-256 checksums.
- [x] Build and run `02 - DATASETs/inspection.ipynb` end-to-end.
- [x] Log source row counts, category distributions, sample calls, and quality flags.
- [x] Create review queues, candidate duplicate groups, and labeling guidelines.
- [x] Deduplicate exact text copies and link related call templates into split groups.
- [x] Export versioned dataset files (`02 - DATASETs/processed/v1/`) with full decision logs.
- [x] Verify final row counts, label balance, provenance fields, and zero pending decisions.

Section 00 is complete for dataset version v1. The prepared pool has 1,440 conversations: 1,273 primary and 167 supplemental. We excluded 38 rows with logged reasons (19 duplicate copies, 13 ambiguous Unknow calls, 5 corrupted texts, and 1 truncated dialogue).

See [the presentation findings report](../02%20-%20DATASETs/reports/data_preparation_findings_v1.md) for full counts, category tables, and presentation slide talking points.

## Raw inputs

| Source | Role | Raw rows | Categories and distribution | Source labels |
| --- | --- | ---: | --- | --- |
| Scam Dialogue Thai Translated (Primary) | Primary | 1,280 | 8 categories (160 rows each) | 640 Scam (1), 640 Not Scam (0) |
| Thai Call Center Call Log (Supplemental) | Supplemental | 198 | Scam 73, General 49, Official 37, Verification-call 26, Unknow 13 | 5 text categories |

Raw source files remain read-only in `02 - DATASETs/raw/`. Source URLs, commit hashes, and file checksums are recorded in `02 - DATASETs/sources.json`.

Use column `translated dialogue` for primary text and column `Text` for supplemental text.

## Automated inspection findings

[See the detailed inspection report](../02%20-%20DATASETs/reports/data_quality_v1.md).

| Check | Count | Note |
| --- | ---: | --- |
| Missing or blank text | 0 | All 1,478 raw rows contain text |
| Exact duplicate groups | 12 | 32 total rows; 20 redundant copies (18 in Kaggle Scam, 1 in Kaggle Unknow, 1 in Primary) |
| Exact duplicate label conflicts | 0 | Same-text rows share the same source label |
| Near-duplicate candidate pairs | 46 | Character 3-5 gram TF-IDF cosine similarity >= 0.90 |
| Near-duplicate label conflicts | 0 | No high-similarity pairs had opposing labels |
| Cross-source duplicate pairs | 0 | Primary and supplemental sources share no identical texts |
| Repeated source IDs in Kaggle CSV | 6 | IDs `00101`, `00130`, and `00140` appear twice each |
| Rows with no Thai characters | 21 | Punctuation-only placeholders or pure English text |
| Short text under 100 characters | 104 | Short OTP messages, alerts, or quick chats |
| Rows with control or replacement characters | 5 | Encoding artifacts (`\ufffd`) |

Flags identify rows needing manual review. A flag does not automatically mean a row is defective.

Because Kaggle reused three ID numbers across different conversations, source `Id` cannot serve as a unique primary key. We assign zero-based row indices (`kaggle_000000` through `kaggle_000197`) and keep the original `Id` string as metadata.

Standardizing line endings (`\r\n` to `\n`) and stripping edge whitespace changed zero characters across the raw datasets.

## Five quality dimensions

1. Completeness: Zero empty rows. Five corrupted rows and one truncated dialogue were excluded.
2. Accuracy: Source labels were verified. Primary balanced classes were retained. Supplemental categories were mapped (Scam to 1; General, Official, and Verification-call to 0). Ambiguous Unknow calls were excluded.
3. Consistency: Schemas, field names, and binary labels (0 and 1) are standardized. Unique IDs use row indices. Exact duplicates were pruned to one representative.
4. Representativeness: Both datasets contain synthetic dialogues. Translated scenarios include western government agencies (IRS, SSA, FTC) that do not represent Thai call patterns.
5. Reliability: All raw downloads are pinned by revision hash and SHA-256 checksum.

## Data preparation rules

Follows `02 - DATASETs/labeling_guideline.md`:
- Target labels: `0 = Not Scam`, `1 = Scam`.
- Supplemental mapping: `Scam` (73 rows) -> `1`; `General` (49), `Official` (37), and `Verification-call` (26) -> `0`.
- Ambiguous data: `Unknow` (13 rows) excluded due to ambiguous labels and incomplete content.
- Duplicate data: 18 redundant Scam copies pruned in Kaggle; 1 redundant copy pruned in Primary (`hf_001143`).
- Corrupted/truncated data: 5 rows with `\ufffd` and 1 truncated row in Primary excluded.

## Prepared dataset outputs (v1)

Stored in `02 - DATASETs/processed/v1/`:
- `primary.jsonl`: 1,273 records (634 Scam, 639 Not Scam)
- `supplemental.jsonl`: 167 records (55 Scam, 112 Not Scam)
- `decisions.jsonl`: audit log for all 1,478 raw rows
- `exclusions.jsonl`: 38 excluded rows with reason codes
- `groups.jsonl`: split groups linking related call templates (14 multi-sample groups)
- `summary.json`: row counts and checksums

Summary report: `02 - DATASETs/reports/preparation_v1.json`.
Detailed presentation report: `02 - DATASETs/reports/data_preparation_findings_v1.md`.

To rebuild the dataset:
```bash
uv run --no-project --with pyarrow==25.0.1 python '02 - DATASETs/prepare.py'
```
The script refuses to overwrite an existing `v1/` directory. To test the build cleanly, use `02 - DATASETs/test_prepare.py`.

## Evidence files

- Inspection notebook: `02 - DATASETs/inspection.ipynb`
- Executed notebook (local): `02 - DATASETs/inspection.executed.ipynb`
- Quality metrics: `02 - DATASETs/reports/inspection_v1.json`
- Inspection report: `02 - DATASETs/reports/data_quality_v1.md`
- Row-level decision log: `02 - DATASETs/processed/v1/decisions.jsonl`
- Automated unit test: `02 - DATASETs/test_prepare.py`
