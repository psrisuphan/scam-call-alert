# Development parity report

## Current status

**Not run; real parity is blocked by missing approved prerequisites.** The synthetic contract/manifest tests do not call a project checkpoint and are not model-parity evidence.

Unavailable at this handoff implementation pass:

- Human-reviewed selected configuration and final evaluated weights/artifact identity.
- Final model's pre-evaluation inference-only export and final text-evaluation record binding the exact weight checksum.
- Owner-confirmed intended local host/device and observed runtime/resource compatibility.
- Owner-approved numerical `atol` (including the approval reference).
- Development-only parity fixtures from the role-free whole-conversation evaluation path.

No final-test records or results were accessed to implement or validate this component. No model weights were downloaded. No label, metric or prediction claim is made.

## Required run record

When prerequisites resolve, replace this section with an aggregate report containing:

| Item | Required evidence |
|---|---|
| Reference | Final evaluation artifact/run identity and exact inference weight/config checksums. |
| Package | Manifest identity, package code revision, all file checksums, dependency versions and tokenizer/checkpoint revisions. |
| Host | OS/runtime, actual CPU/GPU backend/device, memory and load/inference timing conditions. |
| Fixtures | Development/training-pool provenance, fixture count and stable anonymized fixture IDs; no final-test examples. |
| Conditions | Identical role-free prepared text, unpadded input IDs, attention masks, one-request batch/padding setup, model eval mode and label order. |
| Decision | Owner-approved `atol`, reviewer/reference, exact label agreement, probability max absolute difference and all failures. |
| Outcome | Pass only if all exact fields/labels match, both scores meet approved tolerance, loading repeats reproducibly, and no mismatch remains unresolved. |

`parity.run_live_parity` enforces owner approval and artifact/environment/fixture provenance before invoking either predictor. It requires unique stable fixture IDs and a `predict_with_trace` interface on both the exact final-evaluation reference path and packaged path. The traces contain checkpoint-prepared text, unpadded IDs/mask, actual dynamically padded model inputs, batch settings and response. It compares all exact fields, both labels and finite normalized class scores; the frozen 0.5 decision rule must agree. In `comparison_context`, `packaged_manifest_sha256` is the canonical SHA-256 artifact fingerprint returned as the bundle `model_version` (hash of canonical identity and file entries), not the SHA-256 of pretty-printed manifest bytes. Preserve the actual manifest-file checksum separately if useful. Preserve sample-level parity inputs/results in the approved persistent ignored location; keep only this aggregate report and approval references in Git. Do not use parity to adjust threshold or choose a different model. If parity differs, preserve evidence and resolve the cause under the model/handoff plans before proceeding.
