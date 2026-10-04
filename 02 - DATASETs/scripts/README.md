# Reproduce the datasets

Run from the repository root. Install Python and [uv](https://docs.astral.sh/uv/getting-started/installation/) first.

## Run order

| Order | Script | What it does |
|---|---|---|
| 1 | `1.download.py` | Download missing raw sources or verify files already included. |
| 2 | `2.prepare.py` | Create the canonical CSV, source manifest, audit, report, and README. |
| 3 | `3.test_prepare.py` | Check prepared records and rebuild them in a temporary folder. |
| 4 | `4.split.py` | Create the approved train/test split and five validation folds. |
| 5 | `5.test_split.py` | Check saved splits and rebuild them in a temporary folder. |

Raw files and completed outputs are included in this private repository. The scripts use paths relative to their location, not the shell's current directory. Settings and review decisions remain in the dataset folder.

## Check the included files

These commands do not replace the included data:

```bash
python '02 - DATASETs/scripts/1.download.py'
uv run --no-project --with pyarrow==25.0.1 --with scikit-learn==1.9.1 python '02 - DATASETs/scripts/3.test_prepare.py'
uv run --no-project --with scikit-learn==1.9.1 python '02 - DATASETs/scripts/5.test_split.py'
```

The tests reproduce the outputs in temporary folders and compare them with the included files. All 17 tests must pass.

## Rebuild from raw files

Scripts 2 and 4 refuse to overwrite completed outputs. Rebuild in a separate folder so the included data stays safe:

```bash
work=$(mktemp -d)
cp -R '02 - DATASETs' "$work/"
mv "$work/02 - DATASETs/prepared" "$work/expected-prepared"

python "$work/02 - DATASETs/scripts/1.download.py"
uv run --no-project --with pyarrow==25.0.1 --with scikit-learn==1.9.1 python "$work/02 - DATASETs/scripts/2.prepare.py"
uv run --no-project --with pyarrow==25.0.1 --with scikit-learn==1.9.1 python "$work/02 - DATASETs/scripts/3.test_prepare.py"
uv run --no-project --with scikit-learn==1.9.1 python "$work/02 - DATASETs/scripts/4.split.py"
uv run --no-project --with scikit-learn==1.9.1 python "$work/02 - DATASETs/scripts/5.test_split.py"

diff -r "$work/expected-prepared" "$work/02 - DATASETs/prepared" &&
  echo "Rebuilt files: $work/02 - DATASETs/prepared"
```

An empty `diff` means the rebuilt files match. Keep the temporary folder if you want to inspect it.

For candidate review only, run script 2 with `--review-only`. Its scratch files remain ignored; that mode does not create final data or approve decisions.

## What stays unchanged

The layout change does not alter raw downloads, conversations, labels, audit decisions, or saved split assignments. Reports were refreshed to name the moved scripts and record their new checksums. `.gitattributes` preserves raw/prepared bytes and script/config line endings across platforms.

Source or decision changes require renewed review and verified downstream regeneration. Do not edit derived CSVs independently.

## Sharing limits

The primary source has no declared license. The supplemental source declares CC BY-NC-ND 4.0. Source links, attribution, licenses, and original metadata are kept in `../sources.json` and `../raw/`. Prepared outputs document conversion, label mapping, exclusions, and duplicate removal.

Including the data here is for the requested private project handoff. It does not establish permission for public redistribution or commercial use. Confirm source rights before sharing beyond the project.

Stage 02 is separate and is not included in this change.
