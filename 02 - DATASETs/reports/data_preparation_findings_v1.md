# Data preparation findings report (v1)

> Historical JSONL v1 work, superseded by [the CSV preparation report](preparation_csv_v2.md). These counts and rules are not the current handoff. See [reconciliation](stage00_reconciliation.md).

Prepared for Scam Call Alert (Stage 00).

## 1. Executive summary

We audited 1,478 raw dialogues across two datasets and prepared 1,440 clean conversations (1,273 primary and 167 supplemental).

Key findings:
- Both datasets contained zero blank text fields, but deeper inspection revealed repeated dialogues, ID collisions, corrupted characters, and ambiguous labels.
- In the primary dataset, we pruned 1 exact duplicate dialogue and 6 corrupted or truncated texts, retaining 1,273 balanced dialogues across all 8 categories.
- In the supplemental dataset, we followed the proposal's label mapping and cleaning rules: Scam remained Scam (1), and General, Official, and Verification-call mapped to Not Scam (0). We excluded the 13 Unknow calls as ambiguous and pruned 18 duplicate Scam dialogues, retaining 167 clean calls.
- High-similarity call templates were clustered into 14 groups to prevent near-duplicate leakage across future train and test splits.

---

## 2. Dataset counts and label mapping

### Raw datasets

| Dataset | Raw rows | Categories and distribution | Source labels |
| --- | ---: | --- | --- |
| Scam Dialogue Thai Translated (Primary) | 1,280 | 8 categories (160 rows each) | 640 Scam (1), 640 Not Scam (0) |
| Thai Call Center Call Log (Supplemental) | 198 | Scam 73, General 49, Official 37, Verification-call 26, Unknow 13 | 5 text categories |

Source files are stored read-only in `02 - DATASETs/raw/` with hashes recorded in `sources.json`.

Text columns used:
- Primary: `translated dialogue` (the downloaded Parquet uses this column name; the upstream README reference to `thai_dialogue` is an error in their documentation).
- Supplemental: `Text`.

### Label mapping rules

- Primary dataset: Retains source labels (`1 = Scam`, `0 = Not Scam`).
- Supplemental dataset:
  - `Scam` (73 rows) maps to `1 = Scam`.
  - Non-scam categories (`General` 49, `Official` 37, `Verification-call` 26) map to `0 = Not Scam` (112 total rows).
  - `Unknow` (13 rows) has ambiguous labels and incomplete dialogues, and is excluded.

---

## 3. Data cleaning and exclusion results

We applied the data preparation rules to manage duplicates, remove incomplete texts, and exclude ambiguous labels.

| Source | Raw rows | Excluded rows | Retained rows | Final Scam (1) | Final Not Scam (0) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Primary | 1,280 | 7 | 1,273 | 634 | 639 |
| Supplemental | 198 | 31 | 167 | 55 | 112 |
| Total | 1,478 | 38 | 1,440 | 689 | 751 |

### Primary dataset category retention

| Category | Raw count | Retained count | Excluded | Exclusion reason |
| --- | ---: | ---: | ---: | --- |
| Social security number scams | 160 | 159 | 1 | 1 corrupted (`\ufffd` bytes in `hf_000083`) |
| Refund scams | 160 | 157 | 3 | 3 corrupted (`hf_000191`, `hf_000286`, `hf_000308`) |
| Technical support scams | 160 | 159 | 1 | 1 truncated mid-sentence (`hf_000439`) |
| Reward scams | 160 | 159 | 1 | 1 corrupted (`hf_000567`) |
| Legitimate delivery confirmation calls | 160 | 160 | 0 | None |
| Genuine insurance sales calls | 160 | 160 | 0 | None |
| Legitimate telemarketing calls | 160 | 160 | 0 | None |
| Wrong number calls | 160 | 159 | 1 | 1 exact duplicate (`hf_001143` == `hf_001138`) |
| Primary total | 1,280 | 1,273 | 7 | 1 duplicate, 5 corrupted, 1 truncated |

### Supplemental dataset category retention

| Category | Raw count | Retained count | Excluded | Exclusion reason |
| --- | ---: | ---: | ---: | --- |
| Scam | 73 | 55 | 18 | 18 redundant exact duplicate copies pruned |
| General | 49 | 49 | 0 | None |
| Official | 37 | 37 | 0 | None |
| Verification-call | 26 | 26 | 0 | None |
| Unknow | 13 | 0 | 13 | 13 ambiguous or incomplete calls excluded |
| Supplemental total | 198 | 167 | 31 | 18 duplicates, 13 ambiguous Unknow |

All exclusions are documented row-by-row in `02 - DATASETs/processed/v1/exclusions.jsonl`.

---

## 4. Key inspection findings

### 4.1 Missing value checks were insufficient
All 1,478 raw rows had populated text strings. However, several dialogues contained only placeholders (such as "..." in Kaggle rows 00013 and 00025) or cut off mid-sentence. Checking character counts and reading text samples caught issues that blank-field filters missed.

### 4.2 Exact duplicate dialogues
- In Kaggle: The raw CSV repeated identical dialogues multiple times in the 00101 to 00130 ID range. For example, the delivery parcel scam dialogue was repeated 6 times, and the fake bank account alert dialogue was repeated 3 times. We kept the first instance and pruned the 18 duplicate copies.
- In Hugging Face: Dialogue `hf_001143` was identical to `hf_001138`. We kept `hf_001138` and pruned `hf_001143`.

### 4.3 Template variants and split grouping
Character 3-5 gram TF-IDF cosine similarity (threshold >= 0.90) identified 46 high-similarity candidate pairs. These calls use the same script template with small changes in phone numbers, names, or amounts.

We retained unique variants and linked related templates into 14 groups (`groups.jsonl`). When splitting train and test sets in stage 01, dialogues sharing a `group_id` must remain in the same partition. This prevents evaluation scores from inflating due to near-duplicate test samples.

### 4.4 Kaggle ID collisions
Kaggle reused IDs `00101`, `00130`, and `00140` across different rows. ID `00130` appeared once as a Scam call and once as a General chat. ID `00140` appeared once as an OTP message and once as a General chat.

We assigned sequential zero-based project IDs (`kaggle_000000` through `kaggle_000197`) and retained the original `Id` string as a metadata field.

### 4.5 Encoding corruption and truncation
Five primary dialogues contained unicode replacement characters (`\ufffd`). Checking the English source Parquet file showed the corruption existed upstream before translation. Dialogue `hf_000439` cut off mid-sentence in both English ("Why should") and Thai ("ทำไมควร"). We excluded these 6 defective rows.

### 4.6 Dialogue length differences
Retained character length distributions:
| Source | Minimum characters | Median characters | Maximum characters | Rows < 100 chars |
| --- | ---: | ---: | ---: | ---: |
| Primary | 277 | 1,298 | 2,294 | 0 |
| Supplemental | 33 | 103 | 704 | 64 |

Primary dialogues are multi-turn scripts averaging roughly 1,300 characters. Supplemental calls are short call logs averaging roughly 100 characters. We will test supplemental data as an ablation set during model training.

### 4.7 Text normalization
We normalized line endings (`\r\n` to `\n`) and trimmed edge whitespace. Zero characters changed across the retained dataset. We preserved all original speaker tags (`[Call]`, `[User]`, `ผู้โทร:`, `ผู้รับ:`), URLs, phone numbers, and punctuation.

---

## 5. Quality evaluation across course dimensions

1. Completeness: Zero blank fields. Pruned 5 corrupted texts, 1 truncated text, and 13 incomplete Unknow rows.
2. Accuracy: Primary source labels are balanced and retained. Supplemental categories mapped cleanly (Scam to 1; General, Official, Verification-call to 0). Ambiguous Unknow calls were excluded.
3. Consistency: Uniform JSONL schema and binary integer labels (0 and 1). Kaggle ID collisions resolved using row indices. 19 exact duplicates pruned.
4. Representativeness: Both datasets contain synthetic calls. Primary dialogues reflect western government agencies translated into Thai. Models trained on these datasets evaluate prototype architectures, not live carrier detection rates.
5. Reliability: All raw downloads are pinned by commit hash and SHA-256 checksums. Build scripts run deterministically and prevent overwriting existing versions.

---

## 6. Verification and test results

The preparation script and outputs passed all validation checks:
- Raw SHA-256 checksums match source files.
- 1,478 total decisions logged: 1,440 retained and 38 excluded.
- Zero exact duplicate texts remain in the retained pool.
- All retained labels are valid integers (0 or 1).
- Every retained conversation belongs to exactly one group in `groups.jsonl`.
- Reproduction in an isolated sandbox created byte-identical files.
- Modifying raw input bytes immediately triggers a checksum error.

Run verification suite:
```bash
uv run --no-project --with pyarrow==25.0.1 python '02 - DATASETs/test_prepare.py'
```

---

## 7. Artifacts created in Stage 00

| File | Description |
| --- | --- |
| `02 - DATASETs/prepare.py` | Deterministic dataset build script |
| `02 - DATASETs/test_prepare.py` | Verification test suite |
| `02 - DATASETs/inspection.ipynb` | Automated inspection notebook |
| `02 - DATASETs/labeling_guideline.md` | Data preparation rules and category mappings |
| `02 - DATASETs/processed/v1/primary.jsonl` | 1,273 clean primary dialogues |
| `02 - DATASETs/processed/v1/supplemental.jsonl` | 167 clean supplemental dialogues |
| `02 - DATASETs/processed/v1/decisions.jsonl` | Audit log for all 1,478 raw rows |
| `02 - DATASETs/processed/v1/exclusions.jsonl` | 38 excluded rows with reasons |
| `02 - DATASETs/processed/v1/groups.jsonl` | Split groups for template clusters |
| `02 - DATASETs/processed/v1/summary.json` | Row counts and build checksums |
| `02 - DATASETs/reports/preparation_v1.json` | Metrics summary |

---

## 8. Presentation talking points

1. **Raw data overview:** We collected 1,280 dialogues from Scam Dialogue Thai Translated and 198 logs from Thai Call Center Call Log. While all rows contained text, deeper inspection showed duplicates, ID collisions, and corrupted lines.
2. **Category mapping:** In the supplemental data, Scam mapped to Scam (1), while General (49), Official (37), and Verification-call (26) mapped to Not Scam (0).
3. **Handling duplicates and ambiguous calls:** We pruned 18 duplicate Scam rows in Kaggle and 1 duplicate in Hugging Face. We excluded the 13 Unknow calls due to ambiguous labels and silent/incomplete text.
4. **Data leakage prevention:** We identified 14 template families and grouped them so similar calls will not be split between training and testing.
5. **Prepared dataset totals:** 1,440 total clean conversations (1,273 primary and 167 supplemental), yielding 689 Scam and 751 Not Scam dialogues.
