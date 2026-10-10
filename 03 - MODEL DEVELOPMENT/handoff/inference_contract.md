# Local inference contract

## Request

The request is a JSON object with exactly:

| Field | Requirement |
|---|---|
| `request_id` | Required nonempty string used for tracing only; never a model feature. |
| `transcript` | Required nonempty string containing chronological, role-free text. |

The service rejects extra fields, including labels, source/speaker identifiers, caller-only options, and client-provided threshold/model settings. It does not inspect or remove source transcript prefixes. It preserves recognized spoken content/order and delegates approved checkpoint preparation, tokenization, fixed-prefix truncation and padding to the shared input component.

## Response

Every response has exactly the fields below. Success probabilities follow `Not Scam=0`, `Scam=1`; `Scam probability >= 0.5` returns `Scam`. A probability is a model score, not a calibrated or validated risk guarantee.

| Field | Success | Failure |
|---|---|---|
| `request_id` | Same ID as request | Usable ID, otherwise `null` |
| `model_version` | SHA-256 fingerprint of canonical manifest identity plus declared file/checksum entries (not a hash of JSON formatting) | `null` if the bundle/model is unavailable; otherwise the loaded bundle identity |
| `status` | `success` | `error` |
| `label` | `Scam` or `Not Scam` | `null` |
| `probabilities` | Both readable class names and scores | `null` |
| `threshold` | `0.5` | `0.5` when the fixed decision rule is available |
| `warnings` | Empty list or processing notice | Empty list or processing notice when preparation completed |
| `error` | `null` | `{code, message}` |

Warnings are processing notices, currently `TRUNCATED_TO_APPROVED_LIMIT` when the shared frozen prefix policy drops tokens. They are distinct from the app's Scam warning.

## Stable errors

| Code | Meaning |
|---|---|
| `E_INVALID_REQUEST` | Request is not an object with exactly the required fields, or request ID is missing/invalid. |
| `E_TRANSCRIPT_INVALID` | Transcript is not nonempty text. |
| `E_MODEL_UNAVAILABLE` | No verified frozen model/tokenizer bundle could be loaded. |
| `E_PREPROCESSING_FAILED` | Shared frozen text preparation failed. |
| `E_INFERENCE_FAILED` | Model execution/device operation failed. |
| `E_INVALID_OUTPUT` | Output is not exactly one finite, normalized pair of class scores. |

Failure responses never encode `Not Scam`. There is no silent fallback model, threshold change, or precision conversion. Human-readable messages are for diagnosis; clients should branch on the stable code. Raw transcripts and per-sample evidence should not be written to service logs by default.

## Responsibilities

The component accepts one transcript per request and classifies that supplied text. The client owns audio/STT, context-window assembly, transcript revisions, request freshness, and warning persistence. The app supplies no labels or speaker attribution. Model selection, threshold tuning, STT choices, and system evaluation are outside this interface.

The supported CLI reads newline-delimited JSON locally. It is a development invocation surface; mobile emulator networking, app integration, and any HTTP protocol require their own approved application plan and are not implemented here.
