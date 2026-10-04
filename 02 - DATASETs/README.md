# Datasets

> Historical JSONL v1 work. It does not meet the current Stage 00 plan and is not an approved handoff. The plan requires CSV outputs, `Unknow` mapped to `Not Scam`, conservative exact matching, and owner-reviewed relationships. See [reconciliation](reports/stage00_reconciliation.md).

Raw downloads, inspection logs, review queues, and prepared splits for Scam Call Alert.

Raw files in `raw/` and processed outputs in `processed/` are excluded from Git via `.gitignore`. Source metadata (`sources.json`) and summary reports (`reports/`) remain tracked.

## Directory structure

```text
02 - DATASETs/
├── README.md
├── sources.json
├── prepare.py
├── test_prepare.py
├── inspection.ipynb
├── labeling_guideline.md
├── raw/
│   ├── scam-dialogue-thai-translated/
│   │   ├── README.md
│   │   ├── pipeline.yaml
│   │   ├── source-metadata.json
│   │   └── data/train-00000-of-00001.parquet
│   └── thai-call-center-call-log/
│       ├── Dataset.csv
│       ├── source-metadata.json
│       └── thai-call-center-call-log-dataset.zip
├── processed/
│   └── v1/
│       ├── primary.jsonl
│       ├── supplemental.jsonl
│       ├── decisions.jsonl
│       ├── exclusions.jsonl
│       ├── groups.jsonl
│       └── summary.json
├── reports/
│   ├── inspection_v1.json
│   ├── data_quality_v1.md
│   ├── preparation_v1.json
│   └── data_preparation_findings_v1.md
└── review/
    ├── decisions_v1.json
    └── inspection_001/
```

## Current status

Prepared dataset v1 is ready under `processed/v1/`:
- Primary source: 1,273 conversations (634 Scam, 639 Not Scam)
- Supplemental source: 167 conversations (55 Scam, 112 Not Scam)
- Excluded rows: 38 conversations (19 duplicate copies, 13 ambiguous Unknow calls, 5 corrupted texts, 1 truncated dialogue)
- No train/test split has been generated yet

See [the data preparation findings report](reports/data_preparation_findings_v1.md) for full counts, category breakdowns, and presentation slides.

## Primary dataset

- Source: [thirdExec/scam-dialogue-thai-translated](https://huggingface.co/datasets/thirdExec/scam-dialogue-thai-translated)
- Revision: `e814ce89312fbc3eefdd8b941035f633540dab13`
- Raw file: `raw/scam-dialogue-thai-translated/data/train-00000-of-00001.parquet`
- Size: 1,280 rows (640 label 1, 640 label 0) across 8 categories (160 rows each)
- Text column: `translated dialogue` (Thai conversation text)
- Metadata columns: `dialogue` (English), `type` (English category), `label` (binary), `translated type` (Thai category)

Upstream code note: The upstream Hugging Face README references `thai_dialogue` and `thai_type`. The downloaded Parquet file uses `translated dialogue` and `translated type`. Our pipeline uses `translated dialogue`.

The upstream Parquet split is named `train`, but it holds the complete 1,280-row dataset. It is not our project split.

License note: The Hugging Face dataset card lists no license. Check reuse and distribution terms before sharing derived model weights or processed texts.

## Supplemental dataset

- Source: [jxxn03x/thai-call-center-call-log-dataset](https://www.kaggle.com/datasets/jxxn03x/thai-call-center-call-log-dataset)
- Version: `1`
- Raw file: `raw/thai-call-center-call-log/Dataset.csv` (extracted from `thai-call-center-call-log-dataset.zip`)
- Size: 198 rows (Kaggle description states 195; the CSV has 198)
- Columns: `Id`, `Text`, `Type`

| Category | Raw count | Retained in v1 |
| --- | ---: | ---: |
| Scam | 73 | 55 |
| General | 49 | 49 |
| Official | 37 | 37 |
| Verification-call | 26 | 26 |
| Unknow | 13 | 0 |
| Total | 198 | 167 |

Duplicate IDs in source: IDs `00101`, `00130`, and `00140` each appear twice. The project assigns unique IDs based on row index (`kaggle_000000` through `kaggle_000197`) and keeps the original `Id` string as a separate column.

License note: Kaggle lists CC BY-NC-ND 4.0. Keep attribution and non-commercial terms in mind.

## Downloading raw data

Run from repository root:

```bash
mkdir -p '02 - DATASETs/raw/scam-dialogue-thai-translated/data' \
         '02 - DATASETs/raw/thai-call-center-call-log'

curl -fL 'https://huggingface.co/datasets/thirdExec/scam-dialogue-thai-translated/resolve/e814ce89312fbc3eefdd8b941035f633540dab13/data/train-00000-of-00001.parquet' \
  -o '02 - DATASETs/raw/scam-dialogue-thai-translated/data/train-00000-of-00001.parquet'

curl -fL 'https://www.kaggle.com/api/v1/datasets/download/jxxn03x/thai-call-center-call-log-dataset?datasetVersionNumber=1' \
  -o '02 - DATASETs/raw/thai-call-center-call-log/thai-call-center-call-log-dataset.zip'

python - <<'PY'
from pathlib import Path
from zipfile import ZipFile

folder = Path('02 - DATASETs/raw/thai-call-center-call-log')
with ZipFile(folder / 'thai-call-center-call-log-dataset.zip') as archive:
    (folder / 'Dataset.csv').write_bytes(archive.read('Dataset.csv'))
PY
```

File hashes are verified against `sources.json`.

## Inspection and preparation workflow

1. Run automated inspection:
   ```bash
   uv run --no-project --with pyarrow==25.0.1 --with scikit-learn==1.9.1 python -m ipykernel install --user
   ```
   Run `inspection.ipynb` end-to-end. Output metrics write to `reports/inspection_v1.json`.
2. Generate prepared v1:
   ```bash
   uv run --no-project --with pyarrow==25.0.1 python '02 - DATASETs/prepare.py'
   ```
   Outputs write to `processed/v1/`. The script fails if the directory already exists.
3. Run verification tests:
   ```bash
   uv run --no-project --with pyarrow==25.0.1 python '02 - DATASETs/test_prepare.py'
   ```

## Split guidelines for section 01

The project proposal specifies an 80/20 train/test split with cross-validation on the training set.

Split rules:
- Respect `group_id`: all conversations sharing a `group_id` must stay in the same split partition.
- Maintain label balance across splits.
- Primary and supplemental sets will be tested separately and combined in ablation runs.

## Version history

| Version | Date | Status |
| --- | --- | --- |
| Source snapshot | 2026-10-03 | Raw downloads pinned and verified with SHA-256 |
| Inspection v1 | 2026-10-03 | Automated checks, duplicate detection, and review queue generation |
| Prepared v1 | 2026-10-03 | 1,440 retained rows, 38 exclusions, 14 related groups, clean decision logs |

Contact: Project team Phoebe (Kasetsart University).
