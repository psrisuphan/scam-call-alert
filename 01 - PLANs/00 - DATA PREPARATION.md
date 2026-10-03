# 00 - Data preparation plan

## Objective

Acquire, inspect, clean, and format the raw Thai phone dialogue datasets into versioned, traceable JSONL files for binary Scam vs Not Scam classification.

Course references:
- Chapter 2: slides 29, 32-44, 46-54, 62-70 (dataset management, quality dimensions, inspection, and labeling)
- Lab 1: Task 1 (inspection, distributions, quality issues) and Task 2 (before-and-after checks)
- Chapter 6: slides 15-18 (group splits and data leakage prevention)

Proposal references:
- Section 4: Data and Dataset (Scam Dialogue Thai Translated and Thai Call Center Call Log)
- Section 4.1: Label mapping
- Section 5: Data Preparation pipeline step ("จัดการข้อมูลซ้ำหรือไม่สมบูรณ์ หากพบ label ที่กำกวมให้ไม่นำมาใช้")
- Section 7.1: Task 1 responsibility (Data Scientist, Member 1)

---

## Inputs

1. **Primary source:** Scam Dialogue Thai Translated (Hugging Face `thirdExec/scam-dialogue-thai-translated`, commit `e814ce89`).
   - 1,280 dialogues across 8 categories (160 each; 640 Scam, 640 Not Scam).
   - Text column: `translated dialogue`.
2. **Supplemental source:** Thai Call Center Call Log (Kaggle `jxxn03x/thai-call-center-call-log-dataset`, version 1).
   - 198 logs across 5 categories (Scam 73, General 49, Official 37, Verification-call 26, Unknow 13).
   - Text column: `Text`.

---

## Step-by-step execution plan

### Step 1: Data acquisition and checksum verification
1. Download raw Parquet and CSV files using public endpoints.
2. Extract the Kaggle CSV from its archive.
3. Validate SHA-256 hashes against `sources.json` before touching the data.
4. Keep all raw files read-only in `02 - DATASETs/raw/`.

Execution command:
```bash
python '02 - DATASETs/download.py'
```

### Step 2: Quality inspection and flagging
1. Run automated inspection across all 1,478 raw dialogues.
2. Check for empty strings, null values, or placeholder texts ("...").
3. Check for replacement characters (`\ufffd`) and non-standard control bytes.
4. Measure character length distributions and flag texts under 100 characters.
5. Check for pure English texts or missing Thai characters.
6. Check for ID collisions in the raw files.
7. Log all aggregate counts and flagged rows into `reports/inspection_v1.json`.

Execution command:
```bash
uv run --no-project --with pyarrow==25.0.1 --with scikit-learn==1.9.1 python -m ipykernel install --user
# Run 02 - DATASETs/inspection.ipynb end-to-end
```

### Step 3: Duplicate and template detection
1. **Exact duplicates:** Match strings by collapsing internal whitespace while preserving lettercase and punctuation. For identical texts sharing the same label, keep the earliest row and mark redundant copies for pruning.
2. **Near duplicates:** Extract character 3-5 gram TF-IDF features and compute pairwise cosine similarity. Pairs with similarity >= 0.90 represent template variants.
3. **Leakage prevention:** Cluster near-duplicate pairs into connected `group_id` components. Save these clusters to `groups.jsonl` so stage 01 can keep related calls in the same split partition.

### Step 4: Label mapping and ambiguity handling
Follow the labeling rules defined in the proposal:
1. **Primary labels:** Retain source labels (`1 = Scam`, `0 = Not Scam`).
2. **Supplemental labels:**
   - Map `Scam` (73 raw) to `1 = Scam`.
   - Map non-scam categories (`General` 49, `Official` 37, `Verification-call` 26) to `0 = Not Scam`.
3. **Ambiguity pruning:** Exclude the 13 `Unknow` category calls because their labels are ambiguous and their dialogues consist of silence or audio complaints.
4. **Defect pruning:** Exclude 5 dialogues with `\ufffd` replacement characters, 1 dialogue cut off mid-sentence, and 19 redundant exact duplicate copies.

### Step 5: Dataset generation and provenance logging
1. Generate clean JSONL files in `02 - DATASETs/processed/v1/`.
2. Assign sequential zero-based IDs (`hf_000000` to `hf_001279`, `kaggle_000000` to `kaggle_000197`).
3. Normalize line endings (`\r\n` to `\n`) and trim edge whitespace. Preserve all original speaker tags, phone numbers, URLs, and punctuation.
4. Write row-level audit records to `decisions.jsonl` and log all excluded dialogues to `exclusions.jsonl`.
5. Enforce overwrite protection: abort if target directory exists.

Execution command:
```bash
uv run --no-project --with pyarrow==25.0.1 --with scikit-learn==1.9.1 python '02 - DATASETs/prepare.py'
```

### Step 6: Automated verification and testing
1. Assert record counts match expected totals: exactly 1,440 retained rows (1,273 primary, 167 supplemental) and 38 excluded rows.
2. Assert zero duplicate texts in retained data.
3. Assert all retained labels are valid integers (0 or 1).
4. Assert every retained dialogue belongs to exactly one group in `groups.jsonl`.
5. Test reproduction in an isolated temporary sandbox to verify byte-identical output.
6. Test tamper detection to verify that altering raw bytes causes an immediate failure.

Execution command:
```bash
uv run --no-project --with pyarrow==25.0.1 --with scikit-learn==1.9.1 python '02 - DATASETs/test_prepare.py'
```

---

## Deliverables and artifacts

| Artifact | Location | Purpose |
| --- | --- | --- |
| Download script | `02 - DATASETs/download.py` | Fetch and hash-check raw data |
| Inspection notebook | `02 - DATASETs/inspection.ipynb` | Exploratory data analysis and quality flags |
| Preparation script | `02 - DATASETs/prepare.py` | Deterministic clean dataset build |
| Verification test suite | `02 - DATASETs/test_prepare.py` | Automated tests and sandbox reproduction |
| Primary clean dataset | `02 - DATASETs/processed/v1/primary.jsonl` | 1,273 primary dialogues |
| Supplemental clean dataset | `02 - DATASETs/processed/v1/supplemental.jsonl` | 167 supplemental dialogues |
| Decision audit log | `02 - DATASETs/processed/v1/decisions.jsonl` | Full provenance for all 1,478 raw rows |
| Exclusion log | `02 - DATASETs/processed/v1/exclusions.jsonl` | 38 excluded records with reason codes |
| Split groups | `02 - DATASETs/processed/v1/groups.jsonl` | 14 multi-row template clusters for Stage 01 |
| Findings report | `02 - DATASETs/reports/data_preparation_findings_v1.md` | Detailed report and presentation slides |

---

## Stop condition

Stage 00 is complete when:
- `processed/v1/` contains 1,273 primary and 167 supplemental clean records.
- All unit tests in `test_prepare.py` pass.
- No dataset splitting or model training has occurred.
