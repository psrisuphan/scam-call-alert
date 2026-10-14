# Application and local-service interface contract

This file records requirements already fixed by Plan 04/01 and Plan 03/03. It does not freeze transport, endpoint, encoding, timing, or context settings that remain owner-confirmation checkpoints.

## Audio/session input

Every progressive update is associated with a unique `session_id`, chronological sequence number, audio range, and availability time. Recorded mode submits only audio already reached by playback; microphone mode submits only newly captured audio. The service must detect and preserve evidence of missing, duplicate, stale, or interrupted updates. Audio-range units, chunk encoding, and transport remain to be resolved during development compatibility checks.

One active session is allowed. End/replay creates a new session identity. Results from an ended or older session must not update the current transcript, prediction, or notification. Pause prevents new playback progression/audio delivery; explicit End cancels pending work where possible. Natural completion drains the permitted audio tail and required accepted requests under an owner-confirmed timeout.

## Transcript

The app maintains one chronological, role-free transcript. Completed-window text is displayed while recognition is running; corrections revise their existing segment and preserve prior versions. The complete transcript is kept separately from predictive context. No Caller/Receiver tags, source labels, references, or assumed speaker attribution are inserted.

Segment boundaries, revision identity, and exact window-to-segment reconciliation are still confirmation checkpoints. Word-level timestamps are not required.

## Classifier request and response

The classifier accepts a `request_id` and nonempty chronological role-free `transcript`, then returns the matching request ID, model version, status, Scam/Not Scam label, both class probabilities, threshold, warnings, and stable error information as defined in the Plan 03/03 inference contract. The current development adapter uses the owner-approved interim PhayaThaiBERT artifact, with an explicit unevaluated-model warning; the official handoff has a separate loader. A failure or unavailable model is never converted to Not Scam.

The app displays the latest accepted label and errors separately. It shows class scores only in experiment evidence, not as user-facing risk percentages. The first accepted Scam prediction posts the approved system warning once per session; later Not Scam results do not remove the retained warning.

## Queue and cancellation behavior

Only one classifier request runs at a time. If newer updates arrive during a request, the service processes the latest eligible context rather than queueing every intermediate version, while retaining skipped-update evidence. It never silently discards audio. Queue bounds, update interval, timeout values, retry limit, and delay indicator require owner confirmation from development evidence.

The diagnostic client reports `analysis_backlog_seconds` as unsubmitted native audio plus accepted host audio awaiting recognition. `analysis_delayed` becomes true at the configured diagnostic delay threshold; transitions emit `analysis_delay_shown` / `analysis_delay_cleared`. This measures audio backlog, not total end-to-end latency or classifier processing duration. The UI hides the delay indicator after terminal states. These settings remain pending owner confirmation for experiments.

## Not yet frozen

The diagnostic API below is implemented. Its numeric/window/context settings remain pending owner confirmation; it is not a frozen experiment contract.

## Diagnostic HTTP API

The host listens on loopback port 8765. Android uses `http://10.0.2.2:8765`. JSON is UTF-8. The app's native service handles transport while backgrounded.

| Route | Purpose |
|---|---|
| `GET /health` | Loaded component identities, configuration hash and diagnostic configuration. |
| `GET /recordings` | Eligible development/diagnostic recording identities and durations, without labels. |
| `GET /recordings/<id>` | Download the verified source WAV for playback; this does not authorize future audio entering STT. |
| `POST /sessions` | Create a fresh session with `mode`, `approach`, optional `save` and `recording_id`. Only one active/finishing session is permitted. |
| `POST /sessions/<id>/audio` | Recorded-mode PCM16 little-endian, 16 kHz mono bytes. Query fields: `seq`, integer `start`/`end` sample offsets, `available_ms` (audio position), `available_monotonic_ms` (native observed availability time). External uploads are rejected for direct-host microphone sessions. |
| `GET /sessions/<id>` | Transcript/version, segments, latest prediction, retained warning, queues, failures and completion state. Saved terminal snapshots remain accessible after host restart; interrupted sessions are not resumed as complete. |
| `POST /sessions/<id>/finish` | Natural end: drain new audio only, final segments and accepted predictions. |
| `POST /sessions/<id>/cancel` | Explicit Stop; reject late results and clear unsaved microphone content. |
| `POST /sessions/<id>/save` | Explicit evidence opt-in; preserve prior accepted audio/events and future evidence. |
| `POST /sessions/<id>/retry` | Explicit retry of the exact failed classifier input/version. |
| `POST /sessions/<id>/interrupt` | Preserve a native interruption reason; never turn it into Not Scam. |
| `POST /sessions/<id>/events` | Native playback/capture start, background release, resources, posting/observation and failure evidence. |

Native `playback_started`/`capture_started` signals establish the host scheduler origin. The host receipt time and the native timing origin are logged separately. No latency is obtained by subtracting the two clocks. Audio is rejected before its start signal. Exactly repeated audio/range/availability metadata is idempotent; differing duplicate/missing ranges fail. Native retries retain the original bytes and observation time.

The owner-approved direct-host path starts real Mac CoreAudio capture after the app's valid capture_started event. It supplies 16 kHz mono PCM16 LE directly to the same ordered session input, without Android AudioRecord, emulator injection or a native FIR conversion. CoreAudio performs conversion while leaving the Mac hardware setting unchanged. Capture configuration and code identities describe the active path; previous 96→16 and 48→16 native diagnostic filters remain historical evidence in integration_checks.md, not active interface requirements.

Microphone availability uses host monotonic callback-receipt observations and actual captured sample ranges. Native UI/control timestamps remain separate; do not subtract them from host times. The host capture closes on Stop, interruption, capture failure or session lease expiry. Queued audio is discarded on cancellation; unsaved session content is cleared. No capture starts on Decline, and external PCM cannot compete with the physical microphone source.

In diagnostic mode only, `/health` also exposes active microphone signal levels,
sample/processing counts, recognized-character counts and execution errors.
It does not return speech text or audio in that summary. Ending an unsaved
microphone session clears signal/content state; service tests check this cleanup.

Loaded `classifier_device` and `stt_device` are included in component identities before the runtime configuration hash is calculated. Device allocations are evidence conditions: the owner-approved CPU-classifier/MPS-STT feasibility test is distinct from the earlier MPS/MPS context screen.

An unsaved microphone failure retains only non-content diagnostic counts, signal levels, processing timing and capture status; audio, transcript, CTC frames and prediction content are still cleared. Diagnostic-only `POST /diagnostics/inference-order` uses generated silence and neutral input outside sessions, reports timing/memory/output hashes, and rejects concurrent session starts. It does not replace live capture or provide comparison metrics.

## Diagnostic window and segment behavior

The draft uses 5-second STT windows with 1-second overlap. It keeps the selected model's ordinary PyThaiASR preprocessing and greedy CTC argmax decoding. Overlap is joined at the encoder-frame midpoint and decoded chronologically; no fuzzy suffix deletion is performed. Encoder positions are approximate acoustic frame coordinates, not verified word timestamps. Raw window text/frames, transcript versions and source ranges are retained in saved evidence.

The independent host scheduler closes segments every 4 seconds after its registered native-start signal. It runs even while classification is busy. Newly recognized content forms a segment at that boundary; overlap corrections keep their existing segment association. Empty updates do not create segments. Latest waits on revision-only updates; recent/accumulated may reclassify changed input. Natural completion forces the remaining short segment to close without manufacturing a duplicate prediction. Pending classifier requests coalesce after segmentation, so skipped requests cannot change segment membership.

Context assembly counts tokens through the matching shared preparation/tokenizer. The draft retains a source-text Unicode suffix within the model's actual budget and logs omitted prefix characters. Complete transcripts remain visible. The exact boundary convention, durations, interval, recent count, limits, timeouts and retry behavior require owner confirmation before formal experiments.

CTC frame/stride reconstruction follows the principle in [Hugging Face's Wav2Vec2 chunking explanation](https://huggingface.co/blog/asr-chunking). That source supports overlapping acoustic context and frame reconstruction; it does not establish superiority of these exact 5/1-second settings, this midpoint convention, or the Thai application's performance.
