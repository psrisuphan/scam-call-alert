# Coworker handoff: verified final training, pending Mac check

Read [the plans README](../../01%20-%20PLANs/README.md), Plan 03/01's approved scope/timing amendment, [Plan 03/02](../../01%20-%20PLANs/03%20-%20MODEL%20DEVELOPMENT/02%20-%20FINAL%20MODEL%20EVALUATION%20AND%20ERROR%20ANALYSIS.md), and [the final-evaluation README](README.md) before continuing.

This is a development/compatibility handoff. It is not the evaluated-model release required by Plan 03/03. Plans 03/01–03/03 remain Planned.

## What is complete

- Owner-selected PhayaThaiBERT, LR 3e-5, common epoch 2, primary-only. Preserve the approved reduced search: 45 completed fits, 30 excluded fits, no matched supplemental follow-up.
- Exactly one authorized replacement final fit completed after the first fit's persistence failure. It started fresh from the pinned pretrained checkpoint, used all 1,021 primary records and completed two epochs/128 updates without validation.
- All 18 replacement run files, approximately 7.79 GB, passed bounded SSH transfer checks, independent local readback and checkpoint/export identity checks.
- The owner's local persistent copies, not an active Colab session, now hold the recoverable model. No Drive/cloud backup is verified.
- Covered local checks: 113 tests plus 13 subtests passed. The deployed training/selection archive passed 71 tests. Nine additional real-tokenizer handoff checks were blocked by the absent pinned WangchanBERTa tokenizer, not passed.
- The held-out text/audio remains unopened. No final score or Mac compatibility result is claimed.

## Exact model identity

| Field | Frozen value |
|---|---|
| Final run | phaya-final-replacement-primary-epoch2-20261012T050936Z |
| Pretrained checkpoint | clicknext/phayathaibert |
| Revision | a81ece95beb7a24271905d30c23887d343193c62 |
| Final model.safetensors SHA-256 | af64d3a917d5db82bc9dfe794c8f29125bbf13ad9060f726c75ac001f99d838b |
| Selected config SHA-256 | 53824363fce53b915fba658892f742d0bbb61f0bed6646086b5393712dfcb88b |
| Training | Primary-only, role-marked whole conversation; two epochs; seed 67 |
| Inference | Role-free whole conversation; approved 510-total-token fixed prefix |
| Threshold | Scam probability >= 0.5 |
| Training batch/precision | Effective 16 = microbatch 4 × accumulation 4; T4 FP16 |
| Warmup | 20 updates, from the approved initial three-epoch horizon |

Use the final model, not a CV fold or the provisional WangchanBERTa app fixture. Do not quantize, change precision/model format, tune the threshold or change preprocessing without the owning approval.

## Artifact transfer

Weights are intentionally outside Git. Pulling this repository does not download them.

Download `mac-compatibility-transfer.tar.gz` and `mac-compatibility-transfer.tar.gz.sha256` from the owner's [Google Drive handoff folder](https://drive.google.com/drive/folders/1FwMMh3IlETobUeF5DY6HPcWUX_WgZ0SA?usp=drive_link).

Both files were visible in the folder listing on 2026-10-12: the archive displayed as 1.1 GB and the checksum sidecar as 100 bytes. The Drive copy has not been independently downloaded and checksum-verified by the agent. Verify the downloaded archive before extraction using the command below. Listing visibility is not proof of byte integrity, and does not change the remaining provenance/compatibility/test gates.

The verified owner-local originals remain in the Git-ignored directory:

`03 - MODEL DEVELOPMENT/final-evaluation/final_training/phaya-final-replacement-primary-epoch2-20261012T050936Z-execution/`.

Archive SHA-256: `3eda11ba892c59d52c3985ecce8262d728dcdec2a01a5b0105dd7658bf5b9054` (1,180,831,911 bytes). The archived members were independently streamed back and checked against their original SHA-256 values.

The archive contains:
- The exact native `final_model/` files and checksum manifest.
- The neighboring original run config, summary, history and environment. Keep them unchanged.
- Frozen selection/configuration snapshots and the owner's persistence-verification record.

It excludes optimizer checkpoints, dataset CSVs, raw prediction transcripts, CLI credentials and operational debug logs. The full checkpoints/evidence remain with the owner. This is a private project transfer, not permission for public redistribution; resolve licenses before broader sharing.

On Mac, verify the archive before extraction:

```sh
shasum -a 256 -c mac-compatibility-transfer.tar.gz.sha256
mkdir mac-compatibility-transfer
tar -xzf mac-compatibility-transfer.tar.gz -C mac-compatibility-transfer
```

Use a private location outside the checkout. The extracted run directory is `mac-compatibility-transfer/phaya-final-replacement-primary-epoch2-20261012T050936Z/`; its sibling `*-execution/` directory contains the evidence snapshots. Verify the run's `final_model/model.safetensors` against the hash above and the files against `artifact_manifest.json`. An archive checksum alone does not certify compatibility.

## First blocker: selection provenance

The original frozen replacement run config does not contain the selection-completion binding required by `evaluation.load_pipeline`. The selection report still has missing/evidence-limited breakdowns, including inaccessible coworker WangchanBERTa artifacts and Phaya CV training-loss fields.

Do not invent `complete_verified`, mutate the original run config, or remove the guard. Resolve reporting and a separately traceable provenance linkage with the owner before using the shared evaluation/parity pipeline. The archive is recoverable training evidence, but the Mac execution command remains blocked until this is resolved. Owner acceptance of an access limitation is not proof that missing files were verified.

If the WangchanBERTa directories are available in your account, provide their persistent location and existing artifact identities for reconciliation. Preserve the existing evidence and do not rerun training.

## Mac check after that blocker clears

Use the coworker's MacBook Air M2 and the selected STT:
- PyThaiASR 2.3.0.
- airesearch/wav2vec2-large-xlsr-53-th.
- Revision 3155938c549b23eee16b1d4b55dcb161b7fe4bcf.
- MPS, no language model, 16 kHz mono float32 audio.
- A clip from the existing frozen FLEURS development subset, never final audio.

Use the established STT environment and pinned dependencies under `04 - APPLICATION DEVELOPMENT/stt/`. Follow the command in [README.md](README.md#coworker-mac-execution-check), substituting your actual private paths and resolved completion record. The classifier backend is explicit; do not silently fall back or substitute STT.

Return the complete output directory:
- `mac_compatibility.json`.
- Referenced `development_execution.json` with its checksum.
- `resource_samples.csv`.
- Any failures, including a failed run rather than only a success message.

A real pass demonstrates one development execution with both models resident. It does not establish STT ranking, numerical parity acceptance, end-to-end accuracy or an approved deployment configuration.

## Remaining sequence

1. Resolve selection reporting/provenance without changing predictive settings.
2. Verify transferred artifacts and execute the Mac check using development audio.
3. Obtain separate owner authorization bound to the passed check and exact final model before any test access.
4. Evaluate the frozen text pipeline once; retain every outcome/failure and review every FP/FN.
5. Complete Plan 03/03's evaluated bundle, local execution approval and development parity under an owner-approved tolerance.
6. Mark each plan Finished only when its completion criteria verify.

Do not start additional fits, resume the failed run, regenerate frozen assignments, inspect test data for debugging or commit weights/sample-level evidence.
