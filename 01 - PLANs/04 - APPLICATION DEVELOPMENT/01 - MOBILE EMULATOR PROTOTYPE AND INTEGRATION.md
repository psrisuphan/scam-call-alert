# 01 - MOBILE EMULATOR PROTOTYPE AND INTEGRATION

## Purpose and scope

Build a React Native application with Expo on an Android emulator, connecting progressive audio input, speech recognition, the frozen Scam classifier, live transcripts and real system notification banners.

Build and verify recorded conversation mode first, including progressive playback, live transcript and background warnings. Implement and verify live microphone mode afterward as a mandatory experimental demo feature. Both modes must work in the frozen application; deadline prioritization does not make microphone mode optional. Compare three text-context approaches on development recordings, obtain owner confirmation of the selected approach, and freeze the integration for Plan 05.

This plan owns application integration and development comparison. Classifier training/tuning, STT selection and final system evaluation belong to their respective plans. The classifier's marked training provenance remains unchanged; app inputs are chronological role-free text.

The simulated-call interface, microphone mode and background monitoring are owner-approved extensions to the proposal's prepared-audio prototype. They do not provide cellular-call interception, call blocking or physical-phone performance evidence. Planning approval alone does not authorize implementation.

## 1. Verify prerequisites

For early application wiring only, use the owner-approved provisional WangchanBERTa bundle and adapter documented in Plan 03/03. Treat it as a replaceable development fixture: do not use its predictions, scores, or runtime as selection, parity, context-comparison, or system-evaluation evidence. Do not access final-test records. Before formal context comparison, replace it with Plan 03/03's selected and final-evaluated bundle and repeat affected integration checks. Owner-approved interim replacement (2026-10-14): the app service now uses the final-trained, not yet test-evaluated PhayaThaiBERT model through the `interim` adapter recorded in Plan 03/03, after a passed Mac compatibility check. The same development-only restrictions apply. Replace it with the evaluated official bundle before formal context comparison or system evaluation.

The remaining prerequisites are Plan 02's shared unlabeled preparation component; STT Evaluation's selected adapter/configuration; and saved conversation identities, related-record groups and train/test assignments. The official evaluated classifier bundle, manifest and inference contract remain mandatory before formal context comparison, freezing the integration, or Plan 05.

Verify revisions/checksums. Preserve weights, tokenizer, preprocessing, label mapping and threshold 0.5. Do not silently substitute components. STT and classification run on the approved local computer; resolve prerequisite host/backend compatibility checkpoints before integration measurements.

## 2. Establish architecture and permissions

Use React Native + Expo on an Android emulator, with a development build supporting the required native audio and background services.

| Component | Responsibility |
|---|---|
| Emulator application | Recorded playback controls, live microphone-session controls, progressive status/polling, transcript/result display and notifications. |
| Local service | Session-bound Mac microphone capture, STT, transcript reconciliation, context assembly and invocation of the frozen classifier. |

Keep the endpoint configurable and verify actual connectivity; emulator localhost does not automatically reach the computer. Pin actual application/runtime dependencies. Request microphone and notification permissions through visible user interaction. Start monitoring while the application is visible, then support continued operation when backgrounded.

Configure an Android foreground service and its ongoing monitoring notification, separately from the Scam alert. Choose a declared service type and permissions that match the actual Android work; do not request Android microphone access when the Mac host owns capture. Verify host microphone delivery, communication, analysis and notifications while backgrounded; recording/playback alone does not prove pipeline continuity. Do not rely solely on JavaScript timers. Resolve unsupported behavior with the owner rather than silently weakening requirements.

## 3. Implement two modes and isolated sessions

Allow one active session at a time; switching modes requires ending it.

| Mode | Behavior |
|---|---|
| Live microphone | Start opens a clearly identified simulated incoming-call confirmation. Accept starts a host session and obtains any required macOS microphone permission; Decline cancels before capture/session creation. The local service captures the Mac microphone and sends newly available audio directly to the existing STT/classifier pipeline. Stop ends monitoring and host capture. |
| Recorded conversation | Clearly identified simulated incoming call with Answer/Decline; answering starts sequential playback and analysis; Play/Pause and End/Stop, elapsed time and total duration. |

Owner-approved interface refinement: use a restrained phone-call layout, circular accept/decline controls and icon-led actions with accessible labels. The microphone incoming-call screen is confirmation within the demo app, not an actual cellular call. Preserve live transcripts, current classification, retained warnings, failure feedback and opt-in evidence saving.

The owner additionally requested a Liquid Glass-inspired visual treatment, particularly for the live transcript panel: use a translucent, rounded material with restrained highlights and readable text. On the Android emulator this is an inspired implementation, not Apple's native Liquid Glass engine. Audio, classification, evaluation and permission behavior remain governed by this plan.

Owner-approved copy simplification: remove the repeated simulated-call caption, the bottom Not Scam disclaimer and redundant explanatory sentences from call screens. Mode names and the recorded-call entry action identify the source/confirmation flow. Preserve the main warning, classification, processing/failure state, transcript and accessible action labels. The Not Scam limitation remains documented; removing its repeated screen caption does not establish safety.

Both show live transcript, current result and retained warning. Recorded playback has no seeking during an active session. Microphone mode hears surrounding speech, not telephone-call internal audio.

Assign a distinct session ID per attempt/replay. Reset transcript, context, prediction and warning state between sessions. Reject obsolete-session results; notification taps resolve to their originating session rather than another conversation.

## 4. Pause, complete and cancel

- Pause stops playback progression and new audio delivery; processing already underway may finish.
- Natural recording completion enters a finishing state: flush the remaining unprocessed audio tail, including a short final window with only the required already-available overlap. Do not decode an overlap-only window when no new audio remains. Reconcile its output, close any final short text segment containing new recognized speech, and process the latest eligible pending context after recognition settles. If that exact eligible context/version has already been classified, do not manufacture another prediction. Preserve revision-only behavior: no new latest-segment prediction without new speech; recent/accumulated may use changed eligible context. Wait for required accepted requests to finish, then record completion. Permit and record after-playback warnings.
- Configure an owner-confirmed completion timeout from development evidence, recorded with other timeouts; on expiry preserve unfinished work and mark interruption/failure, never successful Not Scam. Missing audio ranges or unfinished required work prevent complete-run status. Explicit Stop bypasses this drain and remains cancellation.
- Explicit End/Stop stops input, cancels pending work where possible and rejects later responses/alerts. Replay starts a new session.

## 5. Supply progressive audio and bounded STT windows

Use a shared progressive audio contract. Microphone supplies newly captured audio; recorded mode supplies only audio already reached in playback. Future audio must never enter recognition or classification.

Identify updates by session ID, sequence number, audio range and availability timestamp. Detect missing, duplicate and stale updates; process chronologically. Preserve interruption evidence.

Use bounded STT windows with overlap. Through development compatibility checks, obtain owner confirmation of window duration, overlap, required conversion, reconciliation and treatment of missing/interrupted audio before formal experiments. Preserve raw window outputs and source identities. Do not assume every STT engine supplies reliable word timestamps. Avoid overlap duplication without deleting legitimate repeated speech.

Owner-approved development diagnostic (2026-10-13): test native microphone capture at 96 kHz and anti-alias conversion to the existing 16 kHz mono PCM16 contract before transport. Direct Mac microphone/STT testing recognized the owner's known Thai sentence; emulator captures at lower rates have returned silence, while the 96 kHz probe received sustained signal. Mac emulator logs also showed CoreAudio conversion errors. This is a measured workaround candidate, not a proven general Android defect. Record its filter settings, delay, capture/output sample counts and functional results in the prototype configuration and integration checks. Preserve the Mac hardware setting, selected STT checkpoint/decoder, recorded mode and model settings. This approval authorizes the diagnostic, not formal experiment settings or app freeze; verify the integrated path before claiming microphone mode works.

Owner-approved workaround test and conditional integration (2026-10-14): the conversion diagnostic, cold hardware-rate test and same-thread recorder check did not establish sustained app capture. Test a local live-microphone bridge using the verified Mac CoreAudio capture path and the emulator's official `injectAudio` API, with authenticated localhost access. It supplies newly captured real microphone audio to Android's virtual microphone; Android capture, progressive transport, the selected STT and classifier remain in the pipeline. No prerecorded or reference text may replace live input. If the bridge passes, integrate it with Accept/Start and Stop/cancellation, record source/configuration identities and failures, and retain the existing opt-in evidence policy. Native host-audio forwarding remains the proposed original path; document the observed limitation and actual bridge path rather than claiming it was fixed. Do not run the helper as an unbounded independent microphone recorder or expose unauthenticated/network-accessible emulator control. Preserve the original Mac hardware setting. This remains emulator-demo evidence and does not freeze formal experiment settings or prove physical cellular-call capture.

Owner-approved architecture change (2026-10-14; supersedes the conditional `injectAudio` integration above): production-path tests showed the isolated Mac bridge continued capturing and forwarding while Android's 48 kHz `AudioRecord` supplied zeros during the live session. A standalone native probe could receive signal in a separate diagnostic, but it did not establish sustained integrated capture. The owner approved direct Mac microphone → selected STT → the same temporary classifier → emulator display/system notification. Keep Android's Accept/Start, Stop/cancel, session UI, native polling/background operation and warning notifications. After the native `capture_started` event establishes the session clock, start the bounded Mac CoreAudio input and deliver only newly captured, chronologically available audio to the existing host session/STT pipeline. Use the verified sounddevice capture contract: mono PCM16 at 16 kHz, `change_device_parameters=False`, CoreAudio `conversion_quality="max"`; preserve the Mac's original 96 kHz hardware setting. Android live microphone mode must not open `AudioRecord` or depend on emulator host-microphone forwarding or `injectAudio`. Ask for host microphone permission through the platform's visible permission flow. Stop, cancellation, disconnect and overflow must close capture, reject late results and follow the existing session failure/privacy rules. Do not replace live input with prerecorded audio or reference text. Keep opt-in evidence saving, selected STT decoding, classifier/model settings, recorded mode, context behavior and notification content unchanged. This is an owner-approved development/demo architecture change; it does not freeze formal experiment settings or establish physical cellular-call capture.

Keep recognized text role-free. Do not insert Caller/Receiver markers, extract an assumed caller, substitute references or rewrite dialogue. Required windowing does not authorize changing frozen STT decoding or adding recognition optimization.

## 6. Maintain live transcripts and revisions

Maintain one reconciled chronological transcript. Display completed-window text and Transcribing while recognition runs; word-by-word output is not required.

Append genuinely new speech. Corrections update the existing segment rather than becoming new speech. Preserve transcript versions, source-window relationships and exact versions used for predictions. Subsequent predictions use corrected context; earlier predictions and any warning remain preserved.

Keep the complete transcript visible independently of predictive context limits. Reopening the app shows current transcript/result/warning. Audio-window timestamps and transcript versions support tracing; word-level timestamps are not required for classification.

## 7. Display classifications and real warnings

Show Analyzing before a usable prediction, then the latest accepted Scam/Not Scam result. Keep both class scores in experiment evidence, not displayed risk percentages. Display errors separately; Not Scam does not guarantee safety.

First accepted Scam prediction posts one system notification per session:

- Title: **ระวัง! สายนี้อาจเป็นมิจฉาชีพ**
- Message: **บทสนทนานี้อาจเป็นการหลอกลวง อย่าเพิ่งให้ข้อมูลส่วนตัวหรือโอนเงิน**

Tapping opens the associated transcript/result. Retain the in-app warning **ระวัง! สายนี้อาจเป็นมิจฉาชีพ** throughout the session, without a redundant second sentence. Later Not Scam results do not erase it. Log further Scam predictions without repeated banners.

Owner-approved wording change (2026-10-14): the in-app warning and notification title/message were changed from English to natural Thai so they match the Thai interface. They replace "Caution! Possible scam detected" and "This conversation may be a scam. Be cautious before sharing personal information or transferring money." Meaning, trigger rules, timing and once-per-session behaviour are unchanged. Notification evidence recorded before this change used the English wording.

Request notification permission, configure the warning channel and verify actual emulator banner behavior. Record posting separately from observed display. Permission denial, channel settings and suppression are explicit conditions; posting time is not confirmed banner-display time. Do not invent unavailable display measurements. The continuing foreground-service notice is distinct from this warning.

## 8. Schedule processing and bound queues

One classification request runs at a time. If updates arrive during it, next classify the latest eligible version instead of queuing every intermediate version. Record skipped update IDs, delays and exact inputs.

Construct text segments at approved update boundaries independently of request skipping; skipped requests must not alter segmentation. Boundaries with no genuinely new recognized speech are logged but do not create empty segments that evict recent context. Revision-only updates modify existing segments and follow section 10. Paused playback adds no future audio or synthetic text segments. Confirm update interval, maximum queued-audio duration, request/completion timeouts, retry limits and delay indicator from development evidence before experiments.

At the queue limit, pause recorded playback until processing catches up; stop microphone mode with Analysis cannot keep up. Never silently discard audio. Automatic pauses/interrupted runs are not uninterrupted normal-speed evidence; preserve their counts and conditions.

## 9. Prepare controlled recordings and references

| Set | Membership | Purpose |
|---|---|---|
| Development | 12 training conversations: 6 Scam, 6 Not Scam | Integration checks and context comparison. |
| Reserved final | 12 test conversations: 6 Scam, 6 Not Scam | Handoff to Plan 05. |

Select before app experiments using saved assignments, class-balanced sampling, seed 67 and a recorded reproducible algorithm. Cover both sources where eligible; at most one conversation per related-record group within a set. Keep all variants with their underlying conversation's partition.

Preserve selection order, exclusions and replacements. Insufficient eligible membership needs review. Never replace recordings because predictions are poor. Human/AI recordings are allowed; record underlying IDs, recording method, applicable generation settings, checksums and duration. Describe source/recording coverage and synthetic conditions; class balance and small sample size limit generalization.

### Recording scripts and fidelity

Construct each recording script using Plan 02's approved whole-conversation role-free source rendering before checkpoint-specific preparation, tokenization or truncation. Record only spoken dialogue in original order; source Caller/Receiver/Scammer/Victim prefixes, target labels, sample/source IDs, categories and commentary are not spoken. Preserve legitimate spoken names or role-like words. Do not generate audio from decoded token exports or inject checkpoint space-marker characters into speech.

Use the shared source parser/rendering component rather than independently interpreting prefixes. Preserve script/configuration identity, source ID, full untruncated spoken content and checksums. Speaker instructions or voice assignment may exist separately for recording, but must not enter audio or classifier text. Human/TTS generation must not invent/paraphrase dialogue or encode target labels through added introductions. Record a stable recording procedure across classes/partitions and disclose differing recording conditions.

Verify actual speech against the script before freezing recordings. Missing/altered spoken content or unresolved structural roles require evidence and owner disposition, not automatic inherited-label approval or replacement based on predictions. Final-recording fidelity checks may use their source/reference content for preparation, never model outputs for tuning. Reference copies describe actual speech; they do not repair audio sent to STT.

### Workload checkpoint

Estimate duration and projected workload before generation, then verify against completed audio. Feed the measured durations, generation/reference-verification effort, playback repetitions and post-playback processing into the combined feasibility estimate owned by Model Selection. If impractical, present evidence for owner approval before changing counts, repetitions or conversation content; do not silently shorten recordings.

### Reference preparation

Verify complete reference transcripts against actual speech. Utterance/word alignment is not required for the deadline-focused scope. Plan 05 performs a separate offline full-conversation STT/reference diagnostic after measured playback, not per-update reference classification. The application still uses only audio already available; removing diagnostic alignment does not authorize future text in live predictions. Preserve any existing alignment as optional evidence without requiring new annotation.

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

### Owner-approved provisional first-pass screening exception (2026-10-14)

To support the approaching deadline, the owner explicitly approved development screening with the current final-trained but not yet test-evaluated PhayaThaiBERT interim artifact documented in Plan 03/03. This narrowly supersedes the official-bundle prerequisite for this first pass only. Use the unchanged weights and inference settings; no held-out conversations, reference substitution, threshold/model tuning or final-system claims are authorized. Repeat affected compatibility/comparison checks if the eventual official bundle differs. Other official-bundle and final-evaluation gates remain in force.

The owner also approved using the twelve existing TTS development recordings provisionally while human speech-versus-script fidelity verification remains pending. Preserve their membership, audio/script hashes and `pending_human_verification` status; do not certify fidelity from checksums or STT output. Label the entire comparison as provisional screening, and do not freeze a final context choice or treat its scores as validated until fidelity is checked and unresolved discrepancies receive owner disposition. Preserve original results when addressing discrepancies rather than silently replacing recordings or favorable runs.

The owner subsequently declined human verification for this comparison and instructed completing it immediately. Human review is therefore not a prerequisite to executing or delivering this provisional comparison; do not repeatedly request it. Retain the unverified fidelity status and disclose its effect on interpretation. This instruction does not establish verified spoken content or approve a formal integration freeze/final-system claim.

Owner-approved demo choice (2026-10-14): use **bounded accumulated context** for the demo, retaining newest text within the approved matching 510-token budget. The completed screen accounts for 36 attempts: 27 completed and 9 preserved infrastructure/automation failures, without retries. On the same eight completed recordings across all approaches, Scam F1 was 0.889 accumulated, 0.750 recent and 0.727 latest. Accumulated detected four of five Scam recordings with zero false warnings on three Not Scam recordings; recent detected three of five, and latest produced two false warnings. This supports the provisional demo choice, not statistical superiority or generalization. Keep the small, training-derived, synthetic, unverified-fidelity and interim-model limitations in the referenced `04 - APPLICATION DEVELOPMENT/prototype/context_comparison_report.md`. The choice does not authorize final-test access or the formal Plan 05 release; verify the chosen approach with the current model in both modes and background before claiming demo readiness.

Owner-approved runtime feasibility test (2026-10-14): test PhayaThaiBERT on **CPU**, keeping the selected STT on **MPS**, and adopt this split for the demo only if functional verification passes. Both models on MPS stalled during actual live capture: a first five-second STT window remained unfinished after 14.952 seconds, with 318,400 samples accepted and none processed before overload. Releasing unused GPU cache improved a neutral-input diagnostic but did not resolve that live failure. Preserve the same weights, FP32 precision, preprocessing, context, threshold, audio windows, queue limit and timeouts; do not replace speech or discard audio. Verify live transcript, classification, foreground/background warning behavior and Stop cleanup, then recorded-mode regression. Record device allocation and current runtime identities with the new evidence. Keep the original MPS/MPS screen and failed checks intact; do not overwrite its resource/timing measurements or claim the CPU/MPS split has equivalent measured performance before checking. This approval does not authorize final-test access or formal release.

Demo runtime decision under that conditional approval: use **CPU classifier / MPS STT**, with emulator-first startup. The live acoustic check and full-sample recorded short-tail regression support this choice; preserve the specific checks, missing live session identity, notification-posting versus display distinction and emulator recovery limitations in `04 - APPLICATION DEVELOPMENT/prototype/integration_checks.md`. Do not reinterpret these functional checks as a new accuracy comparison or formal integration freeze.

Approved screening settings: 5-second STT windows, 1-second overlap, 4-second segment/update interval, recent context of 3 segments, bounded accumulated context retaining newest text within the matching 510-token budget, queued-audio limit 20 seconds, request timeout 30 seconds, completion timeout 120 seconds and zero automatic retries. Preserve the existing reconciliation, context-boundary convention, threshold and model configuration. Run all 12 development recordings under each of the three approaches once, in the saved rotating order, foreground and at normal playback speed. The approved first-pass workload is 36 assigned runs with approximately 40 minutes 51 seconds of audio, plus processing, session setup and completion waits. Additional repetitions and final selection still require owner review.

Record the current APK, source/configuration/STT/model identities and assigned-run/session/attempt mapping before execution. Use fresh recognition and classification for every run; a host-only replay or cached transcript does not substitute for the Android app run. Preserve all failures, automatic pauses, missing observations and unfinished work with their original assigned identities. Report completed-run metrics separately from all-assigned completion/detection/warning coverage and retain the small, training-derived, synthetic and unverified-fidelity limitations.

Start with one fresh run of each approach per development recording: 12 conversations × 3 approaches = 36 assigned first-pass runs. This is development screening, not evidence of repeated-run stability. If results are ambiguous, failures obscure a comparison, or decoding/runtime variation could change the choice, present first-pass evidence and remaining time budget to the owner before repeating promising approaches. For each nominated approach, repeat all 12 recordings twice more, retaining the first run, for three runs per recording. Nominate approaches and freeze the repeat schedule before extra runs; do not cherry-pick only favorable conversations. At most all three approaches receive these repeats, returning to the former 108-run maximum unless another scope change is approved. Keep the app visible throughout all formal context-comparison runs, so display condition is controlled rather than silently importing Plan 05's 1/2 allocation. One session/approach at a time; same recordings, normal playback speed, STT configuration and update interval; loaded models, startup separate; fresh recognition/classification; reset state; rotate and record approach order. Preserve every run, including failures/interruptions. STT may vary between repetitions; do not assume identical text.

Use the agreed conversation-level outcome, failure and timing conventions from Plan 05 for development summaries, without performing final evaluation. Present Scam F1/Precision/Recall, false warnings, misses, warning coverage/timing, queue/processing delays, resources and failures. Keep the comparable one-run first-pass table for all three approaches separate from any repeated-approach table; do not compare their pooled run counts as equal-strength evidence. First-pass timing SD is across contributing conversations, not within-conversation repetition SD. Retain all extra runs, sample SD where defined and observation counts; repetitions are not independent conversations. A single-pass choice has greater uncertainty and can select a worse context policy; do not promise unchanged performance. Use development-only repeats/owner review when that risk matters within the available budget. Do not label every early segment from its whole-conversation label or assign zero time to undetected events.

Preserve coherent monotonic timing and distinguish audio position from elapsed time, local component duration, classifier completion, client receipt, notification posting and observed warning display. Do not subtract unsynchronized computer/emulator clocks. Identify foreground in-app versus background system-warning conditions; unavailable observations stay unavailable.

These recordings are training-derived and may have been seen by the final classifier. Their scores support development policy selection, not unseen generalization or universal superiority of one context. Keep this limitation in the comparison report and final presentation. No new holdout or training experiment is introduced.

Owner selects the approach from measured tradeoffs; record rationale. Verify the selected approach in background mode on development audio, including continuous analysis and actual notification permission/channel behavior, before freezing the final integration. Use the background-start sequence defined below and exercise natural completion/short-tail drain and overload/failure handling. These are additional functional acceptance checks, not an expanded quantitative comparison or permission to tune from final audio. If checks require settings/approach changes, obtain approval and rerun affected development evidence before freezing.

For background evaluation, initialize session/services while visible with recorded audio held at position zero. After confirming the app is backgrounded and the native services remain active, release playback/audio delivery and start the timing origin. Abort/log failure if this sequence cannot be established; do not analyze a foreground audio prefix and call it a background run. Preserve normal Answer-to-play behavior for the interactive foreground demo; the evaluation harness records its different staged start.

Freeze the selected approach/settings and background compatibility before Plan 05. Unscripted microphone demos are functional evidence unless separately approved for quantitative evaluation. Final audio cannot guide selection.

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
| Verified reference transcripts | Complete actual spoken content for offline full-conversation diagnostics; timing alignment optional. |
| Application/service code | Runnable two-mode application and adapters; filenames flexible. |
| `integration_checks.md` | Functional checks, results, corrections and limitations. |
| `context_comparison_report.md` | Approach comparison and owner selection rationale. |
| Development run evidence | Assigned run IDs/conditions, raw/reconciled transcripts and versions, exact predictive inputs, predictions, omissions, timestamps, queues, resources and failures. |

Record audio/segment/session/request/repetition identities and artifact/configuration checksums so evidence can be joined. Preserve partial/interrupted runs promptly and document recovery; never overwrite original evidence or rely only on caches. Code/transport libraries remain flexible within required behavior.

Track code, instructions, configurations, manifests and approved aggregate reports. Audio and detailed sample evidence stay outside Git in documented persistent storage; no credentials or sensitive excerpts in tracked reports.

Live mic sessions are not permanently saved by default. Provide an explicit Save session evidence option. Without it, content remains temporary and is cleared after the session; service logs must not silently retain audio/transcripts. Saved evidence includes audio, transcript versions, predictions, times and failures. Controlled experiments always preserve required evidence.

## 14. Completion and ordered handoff

Verify both modes for no future-input leakage; foreground/background capture, communication and analysis; transcripts/reconciliation; classifier/display agreement; permission and real notification behavior; pause/completion/cancellation/replay; queues, disconnections/retries/failures; session isolation; and required evidence/reproducible launch.

Complete when compatibility checks pass, recording scripts exclude structural metadata and preserve verified spoken content, short-tail/final-update completion is verified, runtime settings/identities are recoverable, owner selects the context approach, selected-background checks pass and the frozen application/reserved recording package are ready for Plan 05. This does not establish physical-phone/cellular-call performance or proven prevention.

Develop recorded mode first, then complete mandatory microphone capture/transcript/classification/notification and background functional checks. Freeze the final application build after both modes pass their checks, including recorded-mode regression checks after microphone integration. Only then release the application to Plan 05. Final quantitative evaluation still uses recorded mode exclusively; microphone mode has functional/demo evidence, not accuracy or latency scores.

Before affected final-system evaluation, review Plan 05 in workflow order for consistency with this plan's text segments/revisions, full-conversation offline diagnostics and system-notification outcomes. The owner requested that Plan 05 be reviewed afterward; this plan does not silently amend or override its measurement requirements. Resolve and record approved downstream updates before affected execution.

## Implementation confirmation checkpoints

Actual host/backend; pinned app/runtime versions; STT window/overlap and reconciliation; segment/revision boundaries; end-of-stream flush and completion timeout; staged background-start compatibility; update interval; recent-context count; newest-text overflow boundaries; queue limits; request timeouts/retries; and measurement availability require documented development evidence and owner confirmation before affected experiments. Do not invent defaults or derive settings from final audio. Actual runtime fit and uninterrupted operation must be demonstrated, not presumed from approval.

## References and rationale

- [Full Proposal](../../00%20-%20DOCUMENTs/Full%20Proposal/Phoebe_FullProposal.pdf), PDF pp. 1, 3–4, §§2.4–3, 6.3 and 7.1–7.2: Thai audio, transcription, classification, warnings, emulator and measured latency. Mic/background design is the approved project extension, not a capability established by this proposal.
- [Pattern Recognition L06_Experimental Design and System Evaluation.pdf](../course-lecture-sheets/Pattern%20Recognition%20L06_Experimental%20Design%20and%20System%20Evaluation.pdf), PDF pp. 19, 43, 45–50: reproducibility, controlled conditions, component/system distinction, latency, actual-host resources and failure-aware reporting. These are PDF pages, not printed slide numbers.
- [React Native guidance](https://reactnative.dev/docs/environment-setup) and [Expo development builds](https://docs.expo.dev/develop/development-builds/introduction/): framework/native integration. Existing team experience supports the practical framework choice; it does not prove superiority.
- [Android emulator controls](https://developer.android.com/studio/run/emulator-extended-controls): host microphone input; [telephony emulation](https://developer.android.com/studio/run/emulator-console#telephony-emulation): simulated cellular calls have no call audio.
- [Expo audio](https://docs.expo.dev/versions/latest/sdk/audio/) and [Android service requirements](https://developer.android.com/develop/background-work/services/fgs/service-types): capture/playback and background execution; verify actual pinned-version behavior.
- [Expo notifications](https://docs.expo.dev/versions/latest/sdk/notifications/) and [Android notification guidance](https://developer.android.com/develop/ui/views/notifications/time-sensitive): system notifications, permissions and display conditions.

Shared progressive input supports consistent integration; bounded overlapping STT windows avoid repeatedly decoding an entire growing call but require verified reconciliation. Three text contexts compare information coverage against runtime/context loss. Persistent one-per-session warnings avoid alert spam and preserve earlier risk indications. Controlled recordings permit reproducible comparison; unscripted speech supports interactive demonstration. Source limitations, synthetic audio and small samples constrain claims.

Recording counts, seed, repetitions, scheduling, segmentation and warning persistence are confirmed project conventions, not exact lecture-prescribed settings. Training/preprocessing and STT-selection procedures remain in their owning plans.
