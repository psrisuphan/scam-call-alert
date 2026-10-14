# Final training protocol and held-out evaluation

This document records frozen training settings and evaluation boundaries. The first authorized final run failed persistence despite its completed computation summary; the approved replacement completed two epochs and its artifacts were verified in owner-local persistent storage. Selection provenance and Mac compatibility subsequently verified. The owner-authorized held-out evaluation `phaya-final-heldout-20261014T195035Z-15182dca` accounts for all 291 assignments, with 290 predictions and one execution failure. Its exact executed protocol, authorization, runtime identities and original evidence are preserved in the Git-ignored `evaluations/<evaluation_id>/` directory; this summary does not replace them. See `evaluation_report.md` for results and limitations.

## Approved candidate decision

PhayaThaiBERT (clicknext/phayathaibert), revision a81ece95beb7a24271905d30c23887d343193c62; primary-only; LR 3e-5; two epochs; seed 67; threshold 0.5. Train role-marked whole conversations and infer role-free whole conversations using the frozen 510-total-token prefix policy. Preserve the existing AdamW, batch, precision and preprocessing settings.

The owner approved omitting the remaining 30 comparative fits and supplemental comparison. The owner subsequently requested leaving coworker artifact retrieval unresolved and moving to the next section. This is recorded as an evidence-access limitation; it does not make the missing WangchanBERTa breakdowns verified.

## Training-only preparation

Frozen training assignments contain 1,021 eligible primary conversations. Effective batch 16 gives 64 updates per epoch and 128 updates for two epochs. The existing warmup convention uses the initial three-epoch horizon: ceil(0.10 × 64 × 3) = 20 warmup updates. Do not replace it with a two-epoch horizon without owner approval.

Final training must initialize fresh from the original pinned pretrained checkpoint, use no validation set/checkpoint selection, and retain required evidence in configured persistent storage. Do not use a CV fold's weights as the final model. A separate final-run approval must bind the complete settings/source/input identities and storage.

## Outstanding boundaries

- selected_config.json and selection_completion.json are frozen and verified. Selection reporting accounts for the approved 45 completed and 30 excluded fits with accepted evidence-access limitations. evaluation.load_pipeline resolves selection_completion.json directly without mutating original training configs.
- Owner-approved timing change: the coworker checks final classifier/STT compatibility on MacBook Air M2 after final training and before any held-out access. That gate remains pending, not passed.
- The final-evaluation guard now accounts for 45 completed fits and 30 approved exclusions, with zero caller-only and supplemental fits. It requires hash-bound scope approval. Final-test authorization also requires hash-bound passed Mac compatibility evidence matching selected configuration and final weights.
- Coworker WangchanBERTa run files remain unavailable at the mounted paths; retain existing aggregates and prior verification provenance with that limitation.
- Final-test inference requires separate authorization after final training and all frozen artifact identities verify.

## Verified replacement final-run evidence

Owner-approved persistence repair: Plan 03/02 records one fresh replacement fit using local staging and bounded verified transfer. The failed run below was preserved; no resume, CV-weight substitution or additional search occurred.

Replacement run: phaya-final-replacement-primary-epoch2-20261012T050936Z.
Persistent owner-local output: final_training/phaya-final-replacement-primary-epoch2-20261012T050936Z/.
Verification/source/approval evidence: sibling phaya-final-replacement-primary-epoch2-20261012T050936Z-execution/.

The replacement completed two epochs, 128 contiguous optimizer updates, 1,021 training records and zero validation records. It used the same pinned pretrained revision and selected settings, including 20 warmup updates, seed 67, microbatch 4 × accumulation 4 and T4 FP16. Final weights are the completed epoch-2 weights. Run duration was 269.68 seconds, excluding independent verification and persistence transfer.

All 18 required run files (7,792,893,010 bytes in total) were checksum/byte-count verified during transfer, independently read back, then the final checkpoint/export identities were revalidated locally. The previous epoch checkpoint and original failed-run evidence were retained. Weights and sample-ID-bearing configurations remain Git ignored. No cloud-backup completion is claimed.

Final model.safetensors SHA-256: af64d3a917d5db82bc9dfe794c8f29125bbf13ad9060f726c75ac001f99d838b.
Training loss by epoch: 0.19045969620018643, 0.0006572449280302078. No validation/test metric is inferred from these losses.

Selection completion is verified and recorded in selection_completion.json. Mac compatibility and separate held-out authorization remain required gates before any final-test access. No final-test record was loaded.

## Previous final-run evidence

Run ID: phaya-final-primary-epoch2-20261012T024607Z.

Persistent execution root: /content/drive/MyDrive/scam-call-alert/model-development/final-evaluation/execution-20261012T024607Z/.

The retrieved training summary records two completed epochs, 128 optimizer updates, 1,021 training records, zero validation records, no failure/interruption and 1,926.97 seconds elapsed through checkpoint finalization. This is observed run evidence, not an independently verified inference export or a model performance result.

Summary-bound hashes:
- run_config.json: ba0584987ab945f0771319f7d56f54932f37766ca5c66d927a2dc11bec067f21
- training_history.csv: 9e0935886f79bb60ec85d1070f2f4f9ae13b4cfff2f0249c6527434e475486af
- validation_predictions.csv (header only expected): 675ba4b6d1b0c161ee8b2073e9ce298a74684923cefc1ace01a5f49ac3a96d1f

These hashes were retrieved from the summary. Fresh-runtime checksum verification matched run_config.json and validation_predictions.csv, but training_history.csv instead has SHA-256 51dfe66c7ea5870a75e2826453d656056b7647f544400f624bc4a2c1343e1752 and contains only epoch 1. The persistent progress log also stops at update 64, despite the summary and attempt state recording 128. The export manifest references model.safetensors (SHA-256 af764642e92b3002ec6e8f1a62a1bcb0410b856ccbc2a3d33d3104869e1962d7), but that file is absent. No checkpoint or alternate weight file was found within the inspected persistent final-evaluation area. Therefore export verification failed on missing artifacts; do not use this run for evaluation or claim weights are recoverable.

Detailed recovery findings are preserved in execution-20261012T024607Z/evidence/recovery-inspection-20261012.json. Keep the original summary, manifest, history and progress unchanged. The observations show incomplete persistence; the exact Drive failure mechanism is not established. A replacement fit or storage-procedure change requires owner confirmation before affected work. The deployed archive was checksum-verified before setup, and its training/selection suite passed 65 tests remotely. The training run retained an immutable snapshot of the selected configuration and comparison report used at launch.

## Tooling verification

The earlier combined local training, selection and final-evaluation suite passed 83 tests and 13 subtests. After adding Mac-check guards and dataset-independent frozen-warmup verification, the targeted training/selection/final-evaluation/synthetic-handoff suite passed 113 tests and 13 subtests after the local-staging safety tests; git diff --check also passed. An expanded handoff run had nine setup errors because the pinned WangchanBERTa tokenizer was absent from both checked local caches. Those real-tokenizer checks are blocked, not passed. The earlier final-evaluation-only check covered 16 tests. These checks verify covered implementation behavior, not completed selection, final-artifact integrity or held-out inference. No test CSV was opened.
