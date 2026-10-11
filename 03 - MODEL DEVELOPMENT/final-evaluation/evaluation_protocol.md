# Final evaluation preparation draft

This document records preparation only. It is not a completed selection record, owner-approved final-run configuration, test authorization or final result. No final training/test inference has run.

## Approved candidate decision

PhayaThaiBERT (clicknext/phayathaibert), revision a81ece95beb7a24271905d30c23887d343193c62; primary-only; LR 3e-5; two epochs; seed 67; threshold 0.5. Train role-marked whole conversations and infer role-free whole conversations using the frozen 510-total-token prefix policy. Preserve the existing AdamW, batch, precision and preprocessing settings.

The owner approved omitting the remaining 30 comparative fits and supplemental comparison. The owner subsequently requested leaving coworker artifact retrieval unresolved and moving to the next section. This is recorded as an evidence-access limitation; it does not make the missing WangchanBERTa breakdowns verified.

## Training-only preparation

Frozen training assignments contain 1,021 eligible primary conversations. Effective batch 16 gives 64 updates per epoch and 128 updates for two epochs. The existing warmup convention uses the initial three-epoch horizon: ceil(0.10 × 64 × 3) = 20 warmup updates. Do not replace it with a two-epoch horizon without owner approval.

Final training must initialize fresh from the original pinned pretrained checkpoint, use no validation set/checkpoint selection, and retain required evidence in configured persistent storage. Do not use a CV fold's weights as the final model. A separate final-run approval must bind the complete settings/source/input identities and storage.

## Outstanding boundaries

- Complete/freeze selected_config.json and the selection completion record without falsely approving unresolved compatibility or verification.
- Resolve local classifier/STT compatibility on the intended MacBook Air M2 host and the timing conflict with the STT plan's deferred integration check.
- The legacy final-evaluation README/code still require 120 main fits plus five caller-only fits. This is incompatible with the approved reduced scope. Pause those commands until the guard is corrected and tested against evidence-bound scope.
- Coworker WangchanBERTa run files remain unavailable at the mounted paths; retain existing aggregates and prior verification provenance with that limitation.
- Final-test inference requires separate authorization after final training and all frozen artifact identities verify.

## Verification to date

The existing synthetic final-evaluation suite passed 16 tests locally. This verifies covered implementation behavior, not completed selection, real final training or held-out inference. No test CSV was opened for this preparation.
