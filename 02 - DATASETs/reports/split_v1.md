# Split report

## Procedure and approval

Bukutsu approved the procedure and previewed allocation in the conversation: 'yep all good'.
Sort sample_id; use scikit-learn StratifiedGroupKFold with n_splits=5, shuffle=True, random_state=67.
Holdout stratifies on source_dataset + label. The first returned fold is test; the other four form the training pool. No alternate folds or seeds were searched.
Within the training pool, use five StratifiedGroupKFold folds stratified on binary label, shuffle=True, random_state=67.
Confirmed relationships and exact-copy links form connected components across the complete raw-ID audit, then are projected onto retained records.
Stable group IDs are group_ plus the minimum raw sample_id in the component; unrelated records are singleton groups. IDs are not renumbered.
Related multi-record groups: 14; retained members: 37; largest: 7.
Group separation takes priority over ratios. This input contains no cross-source related groups; the implementation also connects cross-source evidence.
Assignment CSV is authoritative. It is reused for all models and both training data conditions.

## Provenance

scikit-learn version: 1.9.1; seed: 67.
split.py SHA-256: 4fe0680a7c7f120e74c22b1a7fac0ceb2493ff6d4a732402b4ce13a1b7456cc9
split_config.json SHA-256: 97f87411af6ed92b4251ae2332ceb06d7f58322f6f0eccc2c84098db310ad5fe
prepared.csv SHA-256: e86f7424839a083580f0dce4d813efc0330963b98fce1c1efa04d3ab5b0c6e5d
record_audit.csv SHA-256: e3e852292a6001984406ae75ef42d4ef30160d2331f24e64691a4a56f2ca9405
source_manifest.csv SHA-256: 944356837ae3c0a70405f6139657d3f1a0e3d9c3e16924c61071eb94e923d670
preparation_report.md SHA-256: 7061620d9c4ebe9f8d4d84a01f4928667354e1ebae0f976e7c6cfd740e84d4ca
Source: primary; file: raw/scam-dialogue-thai-translated/data/train-00000-of-00001.parquet; version: e814ce89312fbc3eefdd8b941035f633540dab13; SHA-256: 84c5190cf0e584262c156e49d1b801c61f611c542a472d75f188c52ca33b580e.
Source: supplemental; file: raw/thai-call-center-call-log/thai-call-center-call-log-dataset.zip; version: 1; SHA-256: df47b5c2075619ac41adfc68f016def1c5591af8b9bd8a77a6b6ce9d8f928f61.
Source: supplemental; file: raw/thai-call-center-call-log/Dataset.csv; version: 1; SHA-256: 615fde01d5704da4ff2c5d5f39d1729e108cac40598d518b487480337cbca992.

## Allocations

Scam and Not Scam percentages use the total in each row. Source shares use the full prepared source population, including for fold rows.

| Partition | Source | Scam | Not Scam | Total | Scam % | Not Scam % | Share of that source |
|---|---|---:|---:|---:|---:|---:|---:|
| train | primary | 510 | 511 | 1021 | 49.95% | 50.05% | 80.02% |
| train | supplemental | 44 | 99 | 143 | 30.77% | 69.23% | 79.89% |
| test | primary | 127 | 128 | 255 | 49.80% | 50.20% | 19.98% |
| test | supplemental | 11 | 25 | 36 | 30.56% | 69.44% | 20.11% |
| fold 0 validation | primary | 99 | 102 | 201 | 49.25% | 50.75% | 15.75% |
| fold 0 validation | supplemental | 12 | 20 | 32 | 37.50% | 62.50% | 17.88% |
| fold 0 training | primary | 411 | 409 | 820 | 50.12% | 49.88% | 64.26% |
| fold 0 training | supplemental | 32 | 79 | 111 | 28.83% | 71.17% | 62.01% |
| fold 1 validation | primary | 102 | 100 | 202 | 50.50% | 49.50% | 15.83% |
| fold 1 validation | supplemental | 9 | 22 | 31 | 29.03% | 70.97% | 17.32% |
| fold 1 training | primary | 408 | 411 | 819 | 49.82% | 50.18% | 64.18% |
| fold 1 training | supplemental | 35 | 77 | 112 | 31.25% | 68.75% | 62.57% |
| fold 2 validation | primary | 104 | 104 | 208 | 50.00% | 50.00% | 16.30% |
| fold 2 validation | supplemental | 7 | 18 | 25 | 28.00% | 72.00% | 13.97% |
| fold 2 training | primary | 406 | 407 | 813 | 49.94% | 50.06% | 63.71% |
| fold 2 training | supplemental | 37 | 81 | 118 | 31.36% | 68.64% | 65.92% |
| fold 3 validation | primary | 102 | 99 | 201 | 50.75% | 49.25% | 15.75% |
| fold 3 validation | supplemental | 9 | 23 | 32 | 28.12% | 71.88% | 17.88% |
| fold 3 training | primary | 408 | 412 | 820 | 49.76% | 50.24% | 64.26% |
| fold 3 training | supplemental | 35 | 76 | 111 | 31.53% | 68.47% | 62.01% |
| fold 4 validation | primary | 103 | 106 | 209 | 49.28% | 50.72% | 16.38% |
| fold 4 validation | supplemental | 7 | 16 | 23 | 30.43% | 69.57% | 12.85% |
| fold 4 training | primary | 407 | 405 | 812 | 50.12% | 49.88% | 63.64% |
| fold 4 training | supplemental | 37 | 83 | 120 | 30.83% | 69.17% | 67.04% |

## Verification and use

Every canonical ID appears once in train/test; IDs are disjoint; related groups never cross holdout or validation-fold boundaries.
Each training record validates exactly once; test records have no fold. Both classes occur in every training/validation subset, including primary-only fold training.
Derived rows match canonical records exactly. Canonical preparation files remain unchanged. test_split.py checks these invariants, boundary failures, and deterministic rebuild.
For fold k, both conditions validate on all training-pool records with cv_fold=k.
Primary-only trains on primary-source records with cv_fold!=k; primary + supplemental trains on all records with cv_fold!=k.
Retrieve final test only for later final evaluation. Use one-to-one joins by sample_id and verify source_dataset equality.

## Limitations

Primary test fraction is 255/1276 (19.98%); supplemental is 36/179 (20.11%). Whole-record rounding and unbroken groups constrain exact source proportions. Owner approved these deviations.
CV stratifies on binary label, not source; per-source validation counts vary and are listed above, including zeros if any.
scikit-learn group shuffling is restricted to groups with similar class distributions; it is not an unrestricted shuffle. Saved membership, pinned implementation, and hashes establish reproducibility.
Confirmed relationships come from lexical candidate detection and contextual assistant review. Undetected relationships remain possible.
The test set represents these simulated sources, not real calls or unseen scam categories.
No tokenization, augmentation, resampling, learned preprocessing, model selection, or training has occurred.
