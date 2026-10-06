# 01 - MOBILE EMULATOR PROTOTYPE AND INTEGRATION

## Purpose and scope

Build a React Native application with Expo on an Android emulator, connecting progressive audio input, speech recognition, the frozen Scam classifier, live transcripts and real system notification banners.

Support live microphone mode through the emulator and recorded conversation mode simulating a call with prepared audio. Compare three text-context approaches on development recordings, obtain owner confirmation of the selected approach, and freeze the integration for Plan 05.

This plan owns application integration and development comparison. Classifier training/tuning, STT selection and final system evaluation belong to their respective plans. The classifier's marked training provenance remains unchanged; app inputs are chronological role-free text.

The simulated-call interface, microphone mode and background monitoring are owner-approved extensions to the proposal's prepared-audio prototype. They do not provide cellular-call interception, call blocking or physical-phone performance evidence. Planning approval alone does not authorize implementation.

## 1. Verify prerequisites

Obtain Plan 02's shared unlabeled preparation component; Model Freeze and App Handoff's evaluated classifier bundle, manifest and inference contract; STT Evaluation's selected adapter/configuration; and saved conversation identities, related-record groups and train/test assignments.

Verify revisions/checksums. Preserve weights, tokenizer, preprocessing, label mapping and threshold 0.5. Do not silently substitute components. STT and classification run on the approved local computer; resolve prerequisite host/backend compatibility checkpoints before integration measurements.

## 2. Establish architecture and permissions

Use React Native + Expo on an Android emulator, with a development build supporting the required native audio and background services.

| Component | Responsibility |
|---|---|
| Emulator application | Audio controls, microphone capture, progressive delivery, transcript/result display and notifications. |
| Local service | STT, transcript reconciliation, context assembly and invocation of the frozen classifier. |

Keep the endpoint configurable and verify actual connectivity; emulator localhost does not automatically reach the computer. Pin actual application/runtime dependencies. Request microphone and notification permissions through visible user interaction. Start monitoring while the application is visible, then support continued operation when backgrounded.

Configure appropriate foreground services and their ongoing monitoring notification, separately from the Scam alert. Verify audio delivery, communication, analysis and notifications while backgrounded; recording/playback alone does not prove pipeline continuity. Do not rely solely on JavaScript timers. Resolve unsupported behavior with the owner rather than silently weakening requirements.

## 3. Implement two modes and isolated sessions

Allow one active session at a time; switching modes requires ending it.

| Mode | Behavior |
|---|---|
| Live microphone | Start/Stop monitoring; computer microphone forwarded through emulator host-audio input; progressive capture and analysis. |
| Recorded conversation | Clearly identified simulated incoming call with Answer/Decline; answering starts sequential playback and analysis; Play/Pause and End/Stop, elapsed time and total duration. |

Both show live transcript, current result and retained warning. Recorded playback has no seeking during an active session. Microphone mode hears surrounding speech, not telephone-call internal audio.

Assign a distinct session ID per attempt/replay. Reset transcript, context, prediction and warning state between sessions. Reject obsolete-session results; notification taps resolve to their originating session rather than another conversation.

## 4. Pause, complete and cancel

- Pause stops playback progression and new audio delivery; processing already underway may finish.
- Natural recording completion drains pending analysis with Finishing analysis displayed; permit and record warnings arriving after playback ends.
- Explicit End/Stop stops input, cancels pending work where possible and rejects later responses/alerts. Replay starts a new session.

## 5. Supply progressive audio and bounded STT windows

Use a shared progressive audio contract. Microphone supplies newly captured audio; recorded mode supplies only audio already reached in playback. Future audio must never enter recognition or classification.

Identify updates by session ID, sequence number, audio range and availability timestamp. Detect missing, duplicate and stale updates; process chronologically. Preserve interruption evidence.

Use bounded STT windows with overlap. Through development compatibility checks, obtain owner confirmation of window duration, overlap, required conversion, reconciliation and treatment of missing/interrupted audio before formal experiments. Preserve raw window outputs and source identities. Do not assume every STT engine supplies reliable word timestamps. Avoid overlap duplication without deleting legitimate repeated speech.

Keep recognized text role-free. Do not insert Caller/Receiver markers, extract an assumed caller, substitute references or rewrite dialogue. Required windowing does not authorize changing frozen STT decoding or adding recognition optimization.

## 6. Maintain live transcripts and revisions

Maintain one reconciled chronological transcript. Display completed-window text and Transcribing while recognition runs; word-by-word output is not required.

Append genuinely new speech. Corrections update the existing segment rather than becoming new speech. Preserve transcript versions, source-window relationships and exact versions used for predictions. Subsequent predictions use corrected context; earlier predictions and any warning remain preserved.

Keep the complete transcript visible independently of predictive context limits. Reopening the app shows current transcript/result/warning. Audio-window timestamps and transcript versions support tracing; word-level timestamps are not required for classification.

## 7. Display classifications and real warnings

Show Analyzing before a usable prediction, then the latest accepted Scam/Not Scam result. Keep both class scores in experiment evidence, not displayed risk percentages. Display errors separately; Not Scam does not guarantee safety.

First accepted Scam prediction posts one system notification per session:

- Title: **Caution! Possible scam detected**
- Message: **This conversation may be a scam. Be cautious before sharing personal information or transferring money.**

Tapping opens the associated transcript/result. Retain the in-app message **Scam risk detected during this session**. Later Not Scam results do not erase it. Log further Scam predictions without repeated banners.

Request notification permission, configure the warning channel and verify actual emulator banner behavior. Record posting separately from observed display. Permission denial, channel settings and suppression are explicit conditions; posting time is not confirmed banner-display time. Do not invent unavailable display measurements. The continuing foreground-service notice is distinct from this warning.

## 8. Schedule processing and bound queues

One classification request runs at a time. If updates arrive during it, next classify the latest eligible version instead of queuing every intermediate version. Record skipped update IDs, delays and exact inputs.

Construct text segments at approved update boundaries independently of request skipping; skipped requests must not alter segmentation. Confirm update interval, maximum queued-audio duration, timeouts, retry limits and delay indicator from development evidence before experiments.

At the queue limit, pause recorded playback until processing catches up; stop microphone mode with Analysis cannot keep up. Never silently discard audio. Automatic pauses/interrupted runs are not uninterrupted normal-speed evidence; preserve their counts and conditions.

## 9. Prepare controlled recordings and references

| Set | Membership | Purpose |
|---|---|---|
| Development | 12 training conversations: 6 Scam, 6 Not Scam | Integration checks and context comparison. |
| Reserved final | 12 test conversations: 6 Scam, 6 Not Scam | Handoff to Plan 05. |

Select before app experiments using saved assignments, class-balanced sampling, seed 67 and a recorded reproducible algorithm. Cover both sources where eligible; at most one conversation per related-record group within a set. Keep all variants with their underlying conversation's partition.

Preserve selection order, exclusions and replacements. Insufficient eligible membership needs review. Never replace recordings because predictions are poor. Human/AI recordings are allowed; record underlying IDs, recording method, applicable generation settings, checksums and duration. Describe source/recording coverage and synthetic conditions; class balance and small sample size limit generalization.

### Workload checkpoint

Estimate duration and projected workload before generation, then verify against completed audio. If impractical, present evidence for owner approval before changing counts, repetitions or conversation content; do not silently shorten recordings.

### Reference preparation

Verify text against actual speech and add utterance start/end times. At a diagnostic cutoff include only utterances completed by that time. This prevents future-reference leakage but omits already-spoken portions of unfinished utterances; differences cannot be attributed solely to STT errors. Word-level alignment is not required and would need separate approval. Utterance timing is not earliest-scam-evidence annotation.

Prepare/check reserved audio for fidelity, without using it for debugging, context selection or rehearsal before final evaluation. Text-test-derived audio is another condition, not an independent dataset. Membership, labels and references must not be revised from prediction results.

## 10. Define contexts and revision-only behavior

| Approach | Predictive input |
|---|---|
| Latest segment | Newly recognized speech assigned since the preceding update boundary. |
| Recent context | Latest fixed number of text segments, including the newest. |
| Bounded accumulated context | All recognized speech so far, retaining newest content when the budget is exceeded. |

Corrections remain attached to existing segments. On revision-only updates, latest-segment waits for new speech; recent/accumulated approaches reclassify at the next scheduled boundary if their predictive input changes. Log classification/skipping reasons. Empty contexts must not produce fabricated predictions.

Confirm exact segmentation/revision rules and recent-context count using development evidence before formal comparison. No word timestamps are required; preserve text-version and audio-availability identities. Do not assume STT windows equal classification intervals.

### Separate assembly from frozen preprocessing

Host-side application context assembly selects predictive text that fits the frozen classifier budget, accounting for checkpoint preparation and special tokens through the authoritative shared component/matching tokenizer. Obtain owner confirmation of exact newest-text boundary handling. Keep the complete transcript and record omitted content.

Classifier invocation retains unchanged Plan 02 preprocessing and its prefix-truncation policy; this is application context selection, not a training/evaluation preprocessing change. The emulator must not independently tokenize or modify preprocessing. Bounded accumulated input loses older evidence and may converge with recent-context input; disclose this.

## 11. Compare and select using development evidence

Run each approach three times per development recording: 108 assigned runs. One session/approach at a time; same recordings, normal playback speed, STT configuration and update interval; loaded models, startup separate; fresh recognition/classification; reset state; rotate and record approach order. Preserve every run, including failures/interruptions. STT may vary between repetitions; do not assume identical text.

Use the agreed conversation-level outcome, failure and timing conventions from Plan 05 for development summaries, without performing final evaluation. Present Scam F1/Precision/Recall, false warnings, misses, warning coverage/timing, queue/processing delays, resources, individual repetitions and descriptive variation. Preserve mean/sample SD and applicable contributing counts; repetitions are not independent conversations. Do not label every early segment from its whole-conversation label or assign zero time to undetected events.

Preserve coherent monotonic timing and distinguish audio position from elapsed time, local component duration, classifier completion, client receipt, notification posting and observed warning display. Do not subtract unsynchronized computer/emulator clocks. Identify foreground in-app versus background system-warning conditions; unavailable observations stay unavailable.

Owner selects the approach from measured tradeoffs; record rationale and freeze settings before Plan 05. Unscripted microphone demos are functional evidence unless separately approved for quantitative evaluation. Final audio cannot guide selection.

## 12. Handle failures and retries

- Permission/capture failure: prevent start or stop the affected session.
- Connection/STT failure: pause recorded playback; stop microphone capture and mark interruption.
- Classifier failure: retain transcript/earlier warning, show classification unavailable and allow explicit retry.

Bind retries to exact input/transcript version; reject duplicate/stale responses and preserve original attempts separately. Never turn failures into Not Scam, silently substitute components or resume as though missing audio was analyzed. Verify missing/unreadable audio, invalid/empty transcript, unavailable model, malformed response and host disconnect under these rules.

## 13. Outputs and storage

Store implementation/instructions under `04 - APPLICATION DEVELOPMENT/prototype/` (the project-root implementation directory, distinct from this plans directory).

| Output | Purpose |
|---|---|
| `README.md` | Setup, launch, reproduction, file purposes and persistent artifact locations. |
| `architecture.md` | Components, responsibilities and actual execution environment. |
| `interface_contract.md` | Audio updates, revisions, sessions, cancellation and errors. |
| `integration_config.json` | Frozen versions, endpoint, timing/context settings, queue limits and notification rules. |
| `audio_manifest.csv` | Recording membership, source/group IDs, provenance, checksums and partitions. |
| Timed reference artifacts | Verified speech content and utterance alignment. |
| Application/service code | Runnable two-mode application and adapters; filenames flexible. |
| `integration_checks.md` | Functional checks, results, corrections and limitations. |
| `context_comparison_report.md` | Approach comparison and owner selection rationale. |
| Development run evidence | Assigned run IDs/conditions, raw/reconciled transcripts and versions, exact predictive inputs, predictions, omissions, timestamps, queues, resources and failures. |

Record audio/segment/session/request/repetition identities and artifact/configuration checksums so evidence can be joined. Preserve partial/interrupted runs promptly and document recovery; never overwrite original evidence or rely only on caches. Code/transport libraries remain flexible within required behavior.

Track code, instructions, configurations, manifests and approved aggregate reports. Audio and detailed sample evidence stay outside Git in documented persistent storage; no credentials or sensitive excerpts in tracked reports.

Live mic sessions are not permanently saved by default. Provide an explicit Save session evidence option. Without it, content remains temporary and is cleared after the session; service logs must not silently retain audio/transcripts. Saved evidence includes audio, transcript versions, predictions, times and failures. Controlled experiments always preserve required evidence.

## 14. Completion and ordered handoff

Verify both modes for no future-input leakage; foreground/background capture, communication and analysis; transcripts/reconciliation; classifier/display agreement; permission and real notification behavior; pause/completion/cancellation/replay; queues, disconnections/retries/failures; session isolation; and required evidence/reproducible launch.

Complete when compatibility checks pass, runtime settings/identities are recoverable, owner selects the context approach and the frozen application/reserved recording package are ready for Plan 05. This does not establish physical-phone/cellular-call performance or proven prevention.

Before affected final-system evaluation, review Plan 05 in workflow order for consistency with this plan's text segments/revisions, conservative references and system-notification outcomes. The owner requested that Plan 05 be reviewed afterward; this plan does not silently amend or override its measurement requirements. Resolve and record approved downstream updates before affected execution.

## Implementation confirmation checkpoints

Actual host/backend; pinned app/runtime versions; STT window/overlap and reconciliation; segment/revision boundaries; update interval; recent-context count; newest-text overflow boundaries; queue limits; timeouts/retries; and measurement availability require documented development evidence and owner confirmation before affected experiments. Do not invent defaults or derive settings from final audio. Actual runtime fit and uninterrupted operation must be demonstrated, not presumed from approval.

## References and rationale

- [Full Proposal](../../00%20-%20DOCUMENTs/Full%20Proposal/Phoebe_FullProposal.pdf), PDF pp. 1, 3–4, §§2.4–3, 6.3 and 7.1–7.2: Thai audio, transcription, classification, warnings, emulator and measured latency. Mic/background design is the approved project extension, not a capability established by this proposal.
- [Pattern Recognition L06_Experimental Design and System Evaluation.pdf](../course-lecture-sheets/Pattern%20Recognition%20L06_Experimental%20Design%20and%20System%20Evaluation.pdf), PDF pp. 19, 43, 45–50: reproducibility, controlled conditions, component/system distinction, latency, actual-host resources and failure-aware reporting. These are PDF pages, not printed slide numbers.
- [React Native guidance](https://reactnative.dev/docs/environment-setup) and [Expo development builds](https://docs.expo.dev/develop/development-builds/introduction/): framework/native integration. Existing team experience supports the practical framework choice; it does not prove superiority.
- [Android emulator controls](https://developer.android.com/studio/run/emulator-extended-controls): host microphone input; [telephony emulation](https://developer.android.com/studio/run/emulator-console#telephony-emulation): simulated cellular calls have no call audio.
- [Expo audio](https://docs.expo.dev/versions/latest/sdk/audio/) and [Android service requirements](https://developer.android.com/develop/background-work/services/fgs/service-types): capture/playback and background execution; verify actual pinned-version behavior.
- [Expo notifications](https://docs.expo.dev/versions/latest/sdk/notifications/) and [Android notification guidance](https://developer.android.com/develop/ui/views/notifications/time-sensitive): system notifications, permissions and display conditions.

Shared progressive input supports consistent integration; bounded overlapping STT windows avoid repeatedly decoding an entire growing call but require verified reconciliation. Three text contexts compare information coverage against runtime/context loss. Persistent one-per-session warnings avoid alert spam and preserve earlier risk indications. Controlled recordings permit reproducible comparison; unscripted speech supports interactive demonstration. Source limitations, synthetic audio and small samples constrain claims.

Recording counts, seed, repetitions, scheduling, segmentation and warning persistence are confirmed project conventions, not exact lecture-prescribed settings. Training/preprocessing and STT-selection procedures remain in their owning plans.
