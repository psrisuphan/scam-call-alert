# Datasets

Stage 00 is complete under [the data preparation plan](../01%20-%20PLANs/00%20-%20DATA%20PREPARATION.md). The canonical output is `prepared/prepared.csv`, with 1,455 conversations: 1,276 primary and 179 supplemental.

## Files

- `raw/`: unchanged downloaded Parquet, archive, and CSV.
- `sources.json`: pinned source revisions, checksums, license information, and original counts.
- `scripts/1.download.py`: download missing sources, extract the supplemental CSV, and verify hashes. Existing raw files are never overwritten.
- `scripts/2.prepare.py`: build the six-column CSV and its provenance, audit, report, and README.
- `preparation_decisions.json`: input-bound owner approvals and contextual relationship reviews, including changed spans and reviewer identities.
- `scripts/3.test_prepare.py`: integrity, review-gate, CSV, reproduction, duplicate, and download tests.
- `scripts/4.split.py` and `split_config.json`: approved seed-67 group-aware holdout and five CV folds, bound to preparation hashes and approved allocation.
- `scripts/5.test_split.py`: frozen membership, group boundaries, derived-record equality, review gates, and reproducible split checks.
- `inspection.ipynb`: read-only source inspection and candidate-review checks.
- `prepared/`: included canonical output, documentation, and frozen split artifacts (1,164 training / 291 test).
- [CSV preparation report](prepared/preparation_report.md): findings and build provenance. `reports/preparation_csv_v2.md` is a matching tracked copy.

Pinned raw files and the required prepared/split outputs are included in this private repository. Teammates can inspect the complete handoff after cloning. Review scratch files, historical JSONL outputs, and executed notebooks remain ignored. See [the numbered script guide](scripts/README.md) for verification and a safe full rebuild.

## Reproduce

Run from the repository root:

```bash
python '02 - DATASETs/scripts/1.download.py'
uv run --no-project --with pyarrow==25.0.1 --with scikit-learn==1.9.1 python '02 - DATASETs/scripts/3.test_prepare.py'
uv run --no-project --with scikit-learn==1.9.1 python '02 - DATASETs/scripts/5.test_split.py'
```

These checks reproduce outputs in temporary folders without replacing included files. For a full rebuild, use the script guide and run steps 1-5 in a separate folder. Preparation and splitting refuse to overwrite completed output files. Source or decision changes require renewed review, versioned preparation, and downstream regeneration.

For candidate inspection without finalizing data:

```bash
uv run --no-project --with pyarrow==25.0.1 --with scikit-learn==1.9.1 python '02 - DATASETs/scripts/2.prepare.py' --review-only
```

This writes local review files to `review/plan00/`. It does not approve relationships or create a final dataset.

## Schema and decisions

`prepared.csv` has exactly these columns:

`sample_id, source_dataset, source_record_id, original_label, label, transcript`

Labels are `Scam` and `Not Scam`. Numeric model encoding belongs to Plan 02. Transcripts preserve source content, speaker markers, whitespace, and turn order.

Supplemental `Unknow` maps to `Not Scam` under the owner-confirmed plan. This means not labeled Scam by the source; it does not independently verify benignity. Twelve of its thirteen raw rows remain after one exact duplicate removal.

Exact comparison normalizes line endings and trims whole-text edges only. It preserves internal whitespace and punctuation. Representative preference is primary source, then lowest raw row.

Three unrecoverably truncated primary calls are excluded. Three readable calls with replacement characters are retained unchanged by owner approval. No text repairs occurred.

All 46 candidate pairs were reviewed in context by the coding assistant and recorded as related variants. Similarity alone did not determine the disposition. The detector may miss other relationships. Plan 01 constructs groups from the audit and obtains approval of the group-aware holdout procedure.

## Handoff

Prepared files include `source_manifest.csv`, `record_audit.csv`, `preparation_report.md`, and `README.md`. Audit rows preserve source file and zero-based row locators, including repeated supplemental IDs.

Stage 01 is complete. See [the split report](prepared/splits/split_report.md) for source/class allocation, folds, provenance, and limitations.

For a separate rebuild folder with prepared inputs but no saved splits:

```bash
uv run --no-project --with scikit-learn==1.9.1 python '02 - DATASETs/scripts/4.split.py'
uv run --no-project --with scikit-learn==1.9.1 python '02 - DATASETs/scripts/5.test_split.py'
```

Saved assignments are authoritative. Join by `sample_id` and check matching source identity. Fold validation uses `cv_fold = k`; fold training uses the other folds. Primary-only filters training records only, never validation. All models and both data conditions reuse these assignments.

Stage 02 uses the training pool for input design. No augmentation, resampling, learned preprocessing, model selection, or training has occurred. Continue with [Plan 02](../01%20-%20PLANs/02%20-%20DATA%20PREPROCESSING%20AND%20MODEL%20INPUTS.md).

## Limitations and history

Both sources contain simulated conversations. Primary translation includes foreign scenarios. Neither preparation nor future holdout evaluation establishes performance on real calls.

The primary license is undeclared; the supplemental license is CC BY-NC-ND 4.0. Including files for the requested private project handoff does not establish permission for public redistribution or commercial use. Confirm source rights before sharing beyond the project. Source cards and metadata remain under `raw/`; URLs, versions, and licenses remain in `sources.json`.

The earlier `processed/v1/` JSONL build and v1 reports used different rules and are superseded. They must not be used for Stage 01. [Reconciliation notes](reports/stage00_reconciliation.md) record the changes and approvals.
