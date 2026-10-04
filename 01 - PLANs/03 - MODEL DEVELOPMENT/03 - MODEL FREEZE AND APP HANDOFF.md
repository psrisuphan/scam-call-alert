# 03 - MODEL FREEZE AND APP HANDOFF

## Purpose and scope

Package the selected and evaluated classifier as a reproducible local inference service for the mobile emulator application. Preserve evaluated model behavior, preprocessing, label mapping and threshold.

This task does not retrain, select configurations, tune thresholds, select STT, build the application or perform final system evaluation.

## Prerequisites

Obtain the selected configuration/final evaluated weights; matching tokenizer/model implementation/pinned revisions; frozen role-free preprocessing/length policy/fitted state; label mapping/threshold; final text-evaluation report/artifact identities; and development fixtures from the training pool or independent development examples.

Inputs are chronological role-free conversation text. Caller/receiver attribution and caller-only mode are not required.

## Outputs

Under `03 - MODEL DEVELOPMENT/handoff/`:

| Output | Purpose |
|---|---|
| `README.md` | Installation, loading, invocation, artifact locations and compatibility-check reproduction. |
| `artifact_manifest.json` | Required files, versions, checksums, dependencies, source revisions, licenses and runtime requirements. |
| `inference_contract.md` | Requests, responses, errors, preprocessing responsibility and client/service boundaries. |
| `parity_report.md` | Development fixtures, conditions, tolerance, results and resolved differences. |
| `model_card.md` | Intended use, development/evaluation evidence, threshold, data limitations and deployment constraints. |
| Versioned model bundle | Evaluated weights, tokenizer, required code, preprocessing state, label map and decision configuration. |
| Local inference component | Load the bundle and classify supplied text under the contract. |

Code filenames and backend/library choices remain flexible within required behavior. Keep weights/generated sample evidence outside Git in verified persistent storage; track instructions/manifests/contracts/approved aggregate reports. Include no credentials.

## 1. Establish local execution compatibility

Host classifier inference as a local service on an owner computer. Colab is preferred for training, not the assumed app backend.

Using development inputs:

1. Identify proposed computer, OS and backend.
2. Verify selected-model/custom-code compatibility.
3. Measure loading requirements, memory and inference runtime.
4. Verify invocation by a development client.
5. Record environment and findings.

Do not assume GPU support. Obtain owner confirmation of the specific execution configuration after compatibility checks. Emulator connectivity belongs to Application Integration; STT placement/mobile framework remain separate decisions.

If original-model execution is infeasible, record evidence/proposed alternative and obtain approval before changing host arrangement, model format or numerical precision.

## 2. Assemble the frozen bundle

1. Identify exact weights evaluated by Final Model Evaluation.
2. Include matching tokenizer/model configuration.
3. Include required custom code and pinned dependencies.
4. Preserve role-free policy, length handling and fitted preprocessing state.
5. Preserve label mapping and threshold 0.5.
6. Record revisions/checksums/licenses/attribution.
7. Verify loading without undocumented notebook state or environment assumptions.

Initially use original evaluated artifacts; no quantization or format conversion is approved. Dataset/optimizer recovery state is not an inference dependency; preserve it separately under owning plans.

Conversion/precision changes need an approved development compatibility/parity protocol. Final-test results must not determine conversion settings.

## 3. Share preprocessing between development and inference

Provide a shared text-preparation entry point accepting transcript text plus frozen preprocessing configuration/required fitted state. It must not require labels, source membership or split assignments for inference.

Dataset preparation and service use the same underlying conversion. Dataset metadata remains in its wrapper for provenance. The service owns approved conversion, tokenization, length handling, inference, class mapping and threshold application.

The application supplies chronological role-free text. It does not independently tokenize, insert roles, change preprocessing or adjust threshold. Application Integration owns segment scheduling, context assembly, transcript revisions, stale results and warning persistence. The service classifies supplied text per request.

Plan 02 documents this unlabeled interface without changing its preprocessing methods or fitting boundaries.

## 4. Define the inference contract

### Request

| Field | Requirement |
|---|---|
| `request_id` | Required tracing identifier, never a predictive feature. |
| `transcript` | Required nonempty chronological role-free text. |

Representation/settings are fixed by the artifact. No caller-only option or role fields. Do not inject reference words into STT input.

### Response

Return the same fields on success/failure:

| Field | Purpose |
|---|---|
| `request_id` | Associate response with request; null if malformed without usable ID. |
| `model_version` | Model/preprocessing identity when available; otherwise null. |
| `status` | success or error. |
| `label` | Scam/Not Scam on success; null on failure. |
| `probabilities` | Both class scores keyed by Scam/Not Scam on success; null on failure. |
| `threshold` | 0.5 when decision configuration is available; otherwise null. |
| `warnings` | Processing notices; empty list when none. |
| `error` | Null on success; stable code and readable message on failure. |

Scam score >= 0.5 means Scam, under the approved rule. Scores are model outputs, not validated risk guarantees. Processing notices (e.g. approved truncation) are distinct from the app's Scam warning.

### Failures

Define errors for missing/malformed fields, empty/unusable transcript, unavailable model/artifacts, preprocessing/length-policy failure, inference failure and invalid output. Failures never become Not Scam. Do not silently substitute models/configurations.

## 5. Verify packaged inference parity

Use training-pool or independent development fixtures, never final-test debugging samples.

1. Require identical prepared text and unpadded token IDs.
2. Compare masks/outputs with identical batching/padding.
3. Verify class order, evaluation mode, weights, preprocessing state and threshold.
4. Require matching labels.
5. Compare class scores within documented numerical tolerance.
6. Verify reproducible loading and success/error responses.

Select and obtain owner confirmation of exact tolerance during compatibility checks before acceptance. Record provenance, inputs, artifacts, environments, settings and differences. Investigate every label mismatch; do not change threshold to conceal it. Unresolved differences block handoff. Retain evidence under owning storage/ignore rules.

## 6. Document intended use and limitations

Model card: Thai prepared dialogue; role-free chronology/length policy; simulated/translated limitations; supplemental Not Scam mapping is not independently verified benign content; false alarms/misses/context loss; CV evidence separate from final text-test results; local requirements/dependencies; and STT/partial-context behavior requiring later evaluation.

Do not claim calibrated risk, proven prevention, live-phone operation or physical-phone performance. STT accuracy, context selection, warning timing and final audio-to-warning measurements belong to later plans.

## 7. Completion and application handoff

Complete when artifacts/identities are recoverable; original evaluated model runs on approved local configuration; unlabeled interface is documented; contract/responsibilities are explicit; development parity meets approved tolerance/labels; compatibility checkpoints are resolved; development-client invocation is reproducible; and app worker receives bundle/contract/manifest/instructions/parity report/model card.

Completion does not require app/emulator implementation. Application Integration verifies emulator connectivity/behavior. Handoff does not certify end-to-end quality; Plan 05 evaluates the frozen integrated system.

## References and rationale

- [Full Proposal](../../00%20-%20DOCUMENTs/Full%20Proposal/Phoebe_FullProposal.docx), §§2.4–2.5, 7.1–7.2: emulator, prepared audio, classification and warning.
- [L06](../course-lecture-sheets/Pattern%20Recognition%20L06_Experimental%20Design%20and%20System%20Evaluation.pdf), PDF p. 19, pp. 45–48: reproducibility, component/system separation, actual-host resources and failure-aware measurement.
- Approved preprocessing/training/selection/final-evaluation plans define preserved behavior. Record actual selected-model implementation/dependency/license references in manifest.
- Shared preprocessing and response conventions are practical choices supporting reproducibility; lectures do not prescribe their exact structure.
