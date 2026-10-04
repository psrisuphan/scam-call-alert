# Datasets

Stage 00 is complete under [the data preparation plan](../01%20-%20PLANs/00%20-%20DATA%20PREPARATION.md). The canonical output is `prepared/prepared.csv`, with 1,455 conversations: 1,276 primary and 179 supplemental.

## Files

- `raw/`: unchanged downloaded Parquet, archive, and CSV.
- `sources.json`: pinned source revisions, checksums, license information, and original counts.
- `download.py`: download missing sources, extract the supplemental CSV, and verify hashes. Existing raw files are never overwritten.
- `prepare.py`: build the six-column CSV and its provenance, audit, report, and README.
- `preparation_decisions.json`: input-bound owner approvals and contextual relationship reviews, including changed spans and reviewer identities.
- `test_prepare.py`: integrity, review-gate, CSV, reproduction, duplicate, and download tests.
- `inspection.ipynb`: read-only source inspection and candidate-review checks.
- `prepared/`: local canonical output and its documentation. Split directories contain placeholders only.
- [CSV preparation report](reports/preparation_csv_v2.md): tracked aggregate findings and build provenance.

Raw files, prepared files, review transcripts, and executed notebooks stay local and ignored by Git. The source manifest, scripts, decisions, and aggregate reports make the build reproducible.

## Reproduce

Run from the repository root:

```bash
python '02 - DATASETs/download.py'
uv run --no-project --with pyarrow==25.0.1 --with scikit-learn==1.9.1 python '02 - DATASETs/prepare.py'
uv run --no-project --with pyarrow==25.0.1 --with scikit-learn==1.9.1 python '02 - DATASETs/test_prepare.py'
```

Preparation refuses to overwrite completed output files. Preserve an existing preparation before rebuilding. Source or decision changes require renewed review, versioned preparation, and downstream regeneration.

For candidate inspection without finalizing data:

```bash
uv run --no-project --with pyarrow==25.0.1 --with scikit-learn==1.9.1 python '02 - DATASETs/prepare.py' --review-only
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

Splitting, tokenization, augmentation, resampling, learned preprocessing, and model selection have not occurred. Continue with [Plan 01](../01%20-%20PLANs/01%20-%20DATA%20SPLIT%20AND%20EXPERIMENT%20DESIGN.md).

## Limitations and history

Both sources contain simulated conversations. Primary translation includes foreign scenarios. Neither preparation nor future holdout evaluation establishes performance on real calls.

The primary license is undeclared; the supplemental license is CC BY-NC-ND 4.0. Confirm distribution rights separately before sharing prepared records.

The earlier `processed/v1/` JSONL build and v1 reports used different rules and are superseded. They must not be used for Stage 01. [Reconciliation notes](reports/stage00_reconciliation.md) record the changes and approvals.
