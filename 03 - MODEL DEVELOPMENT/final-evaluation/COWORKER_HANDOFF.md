# Coworker handoff: final training and evaluation evidence

Current continuation (2026-10-14): Mac compatibility and authorized held-out text evaluation are complete; see [evaluation_report.md](evaluation_report.md) and [README.md](README.md). All 291 assignments have outcomes, seven prediction errors have reviewed evidence, and one role-normalization execution failure remains disclosed. Original weights and settings were unchanged. Official bundle/parity/release remains a separate Plan 03/03 task. The transfer/check sequence below is retained historical context; do not repeat training, compatibility checks or held-out inference from its former pending instructions. Read task states only in the plans README.

Read [the plans README](../../01%20-%20PLANs/README.md), Plan 03/01's approved scope/timing amendment, [Plan 03/02](../../01%20-%20PLANs/03%20-%20MODEL%20DEVELOPMENT/02%20-%20FINAL%20MODEL%20EVALUATION%20AND%20ERROR%20ANALYSIS.md), and [the final-evaluation README](README.md) before continuing.

This is an evidence handoff. It is not the packaged model release required by Plan 03/03.

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

## Selection provenance: resolved

The selection-completion record `03 - MODEL DEVELOPMENT/selection/selection_completion.json` is completed and verified against the owner-approved scope reduction (45 completed fits, 30 unrun excluded, 0 caller-only, 0 supplemental). The shared evaluation pipeline (`evaluation.load_pipeline`) resolves this record directly, verified without mutating original run configurations.

Accepted limitations remain documented in the completion record: unequal LR tuning coverage, omitted supplemental comparison, inaccessible raw coworker WangchanBERTa prediction files from currently mounted paths, and small observed lead over XLM-R. If the WangchanBERTa directories are available in your account, provide their persistent location and artifact identities for further reconciliation.

## Mac check

Use the coworker's MacBook Air M2 and the selected STT:
- PyThaiASR 2.3.0.
- airesearch/wav2vec2-large-xlsr-53-th.
- Revision 3155938c549b23eee16b1d4b55dcb161b7fe4bcf.
- MPS, no language model, 16 kHz mono float32 audio.
- A clip from the existing frozen FLEURS development subset, never final audio.

Use the established STT environment and pinned dependencies under `04 - APPLICATION DEVELOPMENT/stt/`. Follow the command in [README.md](README.md#coworker-mac-execution-check), substituting your actual private paths. The completion record defaults to `03 - MODEL DEVELOPMENT/selection/selection_completion.json`. The classifier backend is explicit; do not silently fall back or substitute STT.

Return the complete output directory:
- `mac_compatibility.json`.
- Referenced `development_execution.json` with its checksum.
- `resource_samples.csv`.
- Any failures, including a failed run rather than only a success message.

A real pass demonstrates one development execution with both models resident. It does not establish STT ranking, numerical parity acceptance, end-to-end accuracy or an approved deployment configuration.

## Remaining sequence

1. Selection reporting and provenance are resolved in `selection_completion.json`.
2. Verify transferred artifacts and execute the Mac check using development audio.
3. Obtain separate owner authorization bound to the passed check and exact final model before any test access.
4. Evaluate the frozen text pipeline once; retain every outcome/failure and review every FP/FN.
5. Complete Plan 03/03's evaluated bundle, local execution approval and development parity under an owner-approved tolerance.
6. Mark each plan Finished only when its completion criteria verify.

Do not start additional fits, resume the failed run, regenerate frozen assignments, inspect test data for debugging or commit weights/sample-level evidence.
