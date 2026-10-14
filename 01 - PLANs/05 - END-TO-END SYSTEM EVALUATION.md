# 05 - END-TO-END SYSTEM EVALUATION

## Owner-approved scope change — October 14, 2026

The owner instructed omitting this formal evaluation because of the deadline and the demonstrated working application. Do not execute the reserved 12-recording/36-run final workload or paired-reference diagnostics unless the owner later authorizes restoring this scope. Preserve the original protocol below and its outcome/timing definitions already reused by development summaries.

Plan 06 must disclose that formal end-to-end system evaluation was not performed. Existing app functional checks and the provisional development context comparison remain their original evidence types; they do not substitute for final system accuracy, user-visible warning latency, reliability or scam-prevention evidence. This decision does not waive final text-model evaluation or authorize final-test access.

## Purpose and scope

Evaluate the frozen recorded-audio → STT → classifier → warning pipeline in the Android emulator. Measure conversation-level prediction quality, warning behavior, processing time, resources and failures.

Live microphone mode is demonstration-only. Its functional checks belong to Plan 04/01; it contributes no formal accuracy or latency results here. This plan does not select/tune models, thresholds, context settings or app behavior, intercept cellular calls or establish physical-phone performance. Planning approval alone does not authorize implementation.

## 1. Verify and freeze prerequisites

Obtain evaluated classifier weights and frozen preprocessing/tokenizer; selected STT adapter/configuration; approved application build/contracts; selected context approach and resolved Plan 04/01 settings; reserved recording manifest and complete verified reference transcripts; and development comparison/selection rationale.

Verify versions/checksums and preserve threshold 0.5, chronological role-free inputs, reconciliation, context assembly and warning persistence. Marked training and caller-only research remain provenance, not app role attribution. Resolve missing recorded-mode prerequisites before evaluation. Use the final application build released after both mandatory modes pass Plan 04 functional checks. These measurements use recorded mode only; microphone functionality contributes no formal accuracy/latency results. Do not change the application build during final evaluation.

Reuse Plan 04/01's 12 reserved test conversations: 6 Scam and 6 Not Scam. Do not regenerate membership or select from prediction results. Record source, related-group ID, duration and human/AI conditions. Keep variants in their underlying conversation's partition. Text-test-derived audio is another condition, not an independent dataset. Neither text-test error findings nor final audio results may guide recording selection or app settings.

## 2. Freeze workload, schedule and conditions

Only the selected context approach is evaluated.

| Condition | Runs per recording | Total |
|---|---:|---:|
| Foreground | 1 | 12 |
| Background | 2 | 24 |
| Total | 3 | 36 |

Save a seed-67 shuffled schedule of all recording/condition/repetition assignments before execution; record the algorithm/version. One conversation at a time, normal-speed sequential playback. Reset session, transcript, context and notification state between runs. Preserve the schedule when resuming; repetitions are not independent conversations.

### Foreground

Keep the app visible. Observe transcript, classification and in-app warning behavior.

### Background

Verify notification permission/channel settings beforehand. Initialize session/native services while visible, keeping recorded audio at position zero with no STT/classification input released. Confirm the app has entered background and services remain active, then release playback/audio delivery and set playback-start time. Keep emulator screen on at the home screen throughout playback/drain; record transition/readiness/release events. Use the development-verified Plan 04 sequence; do not change integration during final runs. Failed readiness is an assigned-run failure, not silent reassignment or discarded evidence.

A Scam prediction/alert before the confirmed transition and audio release indicates an invalid staged start or stale-session bug; preserve it as a protocol/integration failure, not valid background evidence. Any premature warning still remains a foreground event within its background-assigned run, not a background banner. Preserve their assigned condition and actual event state; do not silently reassign/replace runs. Report early-warning cases separately. Denied permission/suppression scenarios belong to Plan 04 functional checks, not additional final-performance conditions. Record unexpected notification suppression without changing settings from final results.

## 3. Separate startup and warm-up

Measure app/service/model loading separately. Perform one untimed development-recording warm-up exercising STT and classification; clear its session/transcript/notifications. Keep models loaded during measured runs.

Record service restarts and repeat development warm-up before continuing. Never warm up on final recordings. Document actual hardware/backend, emulator profile, versions and measurement conditions; use the Plan 04 workload/compatibility checkpoints rather than inventing settings.

## 4. Execute and preserve every assigned run

1. Verify recording/configuration identities.
2. Start a fresh session and follow its assigned display condition.
3. Perform fresh STT/classification without cached transcripts/predictions.
4. Supply only audio already reached in playback.
5. Follow Plan 04's end-of-stream procedure: flush short remaining audio, reconcile final transcript, handle eligible final context and drain accepted requests within the frozen completion timeout. Do not stop merely because the playback timer ended. Preserve timeout/missing-range/unfinished-work failures separately.
6. Preserve outputs, timing, resources, failures and human warning observation.

Reuse Plan 04's text segments and revision-only rules, not assumed word timestamps or independent recognition per classification interval. Preserve raw STT and reconciled transcript versions, including legitimate repeated speech and corrections.

For every update retain conversation/session/evaluation/run/attempt/segment/request identities; audio cutoff/range/availability; raw output and reconciled version; exact selected predictive text; omissions/token lengths; both class scores/label/threshold; completion/receipt/render/posting events; queues/skips/revisions; and failures/interruptions. Retain artifact identities so evidence joins are reproducible.

## 5. Distinguish prediction from warning delivery

### Conversation classification

Any completed Scam prediction from a valid request belonging to this run and using only released audio is a classification detection event; on a Not Scam conversation it is a false positive. Stale/foreign-session, malformed or premature outputs, and outputs rejected under explicit cancellation/timeout rules, remain technical evidence and must not inflate detection or false-positive coverage. Preserve service-only results separately from app-received results; classifier detection never implies successful user warning. A completed eligible run has accounted for all available audio, final tail/transcript handling and required requests, with no interruption/failure or completion timeout; it must have at least one usable prediction. Such a run without a Scam event receives Not Scam. Audio successfully transcribed as empty is retained as recognition evidence, not an invented prediction; an entire run with no usable classifier input is unresolved. Failed/interrupted runs without Scam events remain unresolved. Preserve events before failure without presenting the run as fully completed.

Never copy full-conversation labels onto early segments for segment-level accuracy. Distinguish service prediction, app receipt and user-visible output; they may fail independently.

### Warning behavior

Verify frozen one-banner-per-session behavior and retained in-app warning. Separately record Scam prediction, app receipt, notification posting, foreground in-app rendering and human-observed system banner. Further Scam predictions need not create more banners.

Human observation uses visible/not visible/uncertain, recording actual foreground/background state. Screen recording is not mandatory. Posting is not evidence of visible display. Distinguish observed delivery failure, suppression and uncertainty; uncertain does not automatically mean not visible. Record warnings during playback, only afterward or never, and early events before background transition.

## 6. Measure timing with valid clocks

| Measurement | Boundary |
|---|---|
| First Scam result received | Playback start → first Scam result received by app. |
| Foreground warning | Playback start → first in-app warning render. |
| Background notification posting | Playback start → first Scam posting event; record actual app state. |
| Update latency | Audio availability → corresponding app receipt/display, identifying boundary. |
| Component duration | Local STT, preparation and classifier execution. |
| Startup | Defined launch/load start → ready. |

Use coherent monotonic clocks within components. Do not subtract unsynchronized host/emulator timestamps. Retain host completion for tracing but do not call app receipt exact classifier completion. Synchronize asynchronous device work where necessary for component duration.

No exact background banner-display latency is claimed. Human observation establishes visibility, not a precise timestamp. Measure foreground rendering and background posting separately; do not pool them under one warning-latency label. Preserve audio position separately from elapsed time, especially with pauses. Not Scam Scam-events are false-positive/false-warning timings. No trust-time research or earliest-evidence annotation is required.

## 7. Report conditions, denominators and variation

Report each condition separately: Scam Precision/Recall/F1, macro-F1, Accuracy and raw confusion matrices; class/source and recording counts; completion/interruptions/failures; detection/confirmed-warning coverage; false positives/false warnings; timings/resources.

Classification metrics use all completed eligible runs in that condition, with raw counts and explicit denominator; do not weight confusion matrices to force equal conversation contributions. Reuse approved undefined-metric conventions (numeric zero with reason/flag), distinguishing genuine zero and execution failure. Preserve incomplete-run detection events separately from completed-run scores.

### Coverage and per-conversation reporting

Foreground has one assigned run per conversation; background has two. Report individual outcomes and per-conversation completion counts. Average per-conversation detected-run/false-positive-run proportions using assigned runs, keeping failures in coverage denominators; conversations receive equal weight for coverage. Preserve confirmed-visible/not-visible/uncertain observations separately and state denominator. Foreground events before background transition do not count as confirmed background-banner visibility.

Do not pool all three as equivalent repetitions. A conversation with one versus two completed background runs can contribute different amounts to successful-path classification scores; disclose this through counts, rather than hiding failures.

### Timing and resource summaries

Within each condition summarize contributing repetitions per conversation, then report mean, sample SD (ddof=1) and median across contributing conversations. Calls receive equal weight for timing. Foreground has no within-conversation repetition SD; SD is unavailable with fewer than two observations.

Use observed-event times only, never zero for undetected/unobserved events. Include contributing conversation/run counts. For update latency, aggregate updates → run → conversation → condition, preserving update counts. Summarize comparable resources with conditions and availability explicit. SD is descriptive, not a confidence interval or robustness claim; no high percentiles required.

## 8. Preserve interruptions and retries

Automatic playback pauses, connection faults and other interruptions remain assigned-run evidence. Keep predictions/warnings and interruption reason/duration; include in completion/failure coverage and report timing separately from uninterrupted normal-speed runs.

Never silently replace an assigned failure with a successful retry. Retries have distinct attempt IDs, purpose and separate reporting; original assigned outcomes remain recoverable. A detected Scam before interruption remains an event, not full completion. Wrong predictions alone do not authorize retries with altered settings.

## 9. Run offline full-conversation reference diagnostics

After measured playback/analysis completes, classify the complete reconciled STT transcript and the complete verified reference transcript using the same frozen classifier, preprocessing, threshold and full-conversation prefix-length policy. This is a separately identified whole-conversation diagnostic, not a replay of the selected incremental context approach.

1. Retrieve each completed run's final reconciled transcript and its recording's verified reference.
2. Prepare both as role-free whole conversation, recording prepared inputs, token lengths/truncation and identities.
3. Preserve paired predictions, agreement, errors and diagnostic metrics separately from actual application outcomes.
4. Report pairing coverage/failures; incomplete audio/transcripts are not silently treated as complete-conversation inputs.

An identical reference input may have one versioned diagnostic prediction reused for that recording's run pairs; disclose reuse. Formal system runs still require fresh STT/classification. This diagnostic occurs outside application latency measurements and does not inject future reference words into real-time predictions.

Utterance/word timestamps and per-update reference alignment are not required. Do not claim this diagnostic measures incremental warning degradation or changes to the selected context's early detection. It helps examine classification differences for full recognized versus reference text under the diagnostic policy; recognition errors and length/preparation effects may both contribute.

Reference never replaces STT in the app or informs model/context/threshold adjustments. Any optional transcription scoring reuses STT Evaluation's frozen rules; no new scoring policy is selected from final outcomes.

## 10. Measure resources and review errors

Record host/backend/emulator/software identities, CPU/GPU use where measurable, peak RAM/VRAM, artifact storage, duration/token lengths, queues/skips/omissions/failures and measurement tools. Identify unavailable measurements. Separate host computation from emulator load and cold startup from warm runs; do not claim physical-phone resources.

Preserve/review false positives, false negatives and warning-delivery problems. Distinguish classifier mistakes, integration faults and uncertain observations. Explanations separate evidence from hypotheses; labels/configurations cannot be edited to improve final results. No fixed accuracy/latency acceptance target is imposed.

## 11. Correct genuine evaluation bugs with approval

Pause affected work; preserve originals; explain evidence, proposed correction and downstream effects; obtain owner confirmation before frozen-system changes; keep corrected attempts/evaluations separately; disclose final-audio reuse.

Repeated evaluation after correction is not untouched confirmation of an adaptively improved system. Wrong predictions do not authorize model/STT/threshold/context/label changes. Never overwrite original attempts.

## 12. Outputs, identities and persistent storage

Store tracked instructions/code/approved reports under project-root `05 - SYSTEM EVALUATION/`, distinct from the plans directory. Organize evaluation sessions and detailed attempts as follows; generated evidence stays outside Git, locally ignored or in documented persistent storage.

```text
05 - SYSTEM EVALUATION/
├── README.md
├── Evaluation/analysis code
└── evaluations/
    └── <evaluation_id>/
        ├── artifact_manifest.json
        ├── system_protocol.md
        ├── run_schedule.csv
        ├── system_runs.csv
        ├── warning_observations.csv
        ├── conversation_summary.csv
        ├── paired_predictions.csv
        ├── system_metrics.json
        ├── system_report.md
        ├── figures/
        └── runs/
            └── <run_id>/
                └── <attempt_id>/
                    └── Original detailed update/event/resource evidence
```

This is a logical layout: README/manifest record actual persistent locations when evidence is external. References to canonical recordings/bundles avoid duplication. Independent evaluations have new IDs; each retry has a distinct attempt ID. Run IDs identify saved schedule assignments.

| Output | Purpose |
|---|---|
| `README.md` | File purposes, execution/analysis reproduction and artifact retrieval. |
| `artifact_manifest.json` | Bind evaluation protocol/schedule, frozen components, recording/reference identities, file checksums and persistent locations. |
| `system_protocol.md` | Frozen workload/conditions, clocks, resource tools, pairing and denominator rules. |
| `run_schedule.csv` | Seed-67 recording/condition/repetition assignments. |
| `system_runs.csv` | Derived assigned-run and identified-attempt outcomes, times, interruptions, failures/resources. |
| `warning_observations.csv` | Human visibility observations, actual app state and event/evidence links. |
| `conversation_summary.csv` | Condition-specific per-conversation outcomes/completion and summaries. |
| `paired_predictions.csv` | Separate offline full-conversation STT/reference inputs, predictions, pairing coverage and reuse identities. |
| `system_metrics.json` | Derived aggregate scores/counts/denominators and undefined flags. |
| `system_report.md` | Results/errors/conditions/limitations and original/corrected evidence disclosure. |
| Evaluation/analysis code | Reproduce execution logging, joins, metrics and diagnostics. |
| `figures/` | Derived visual results. |
| `runs/<run_id>/<attempt_id>/` | Original transcript/input/output/event/failure/resource evidence, including `update_predictions.jsonl`; filenames flexible beyond documented identities. |

Persist individual evidence promptly before producing aggregates. Generate summaries/metrics/figures from originals; regeneration must not overwrite original run evidence. Store corrected report generations separately with provenance if interpretation/code changes. Preserve required partial-run recovery and checksums; do not rely on temporary caches.

Track code, instructions, artifact/configuration identities, schedule and approved aggregate reports. Detailed sample CSV/JSONL, audio/transcripts and observations containing sample evidence stay outside Git in documented persistent storage. Include no credentials/sensitive excerpts. Preserve human observations as original evidence even if aggregate tables are regenerated.

## 13. Completion and reporting handoff

Complete when frozen prerequisites and 36 assignments are accounted for; condition/state and all predictions/observations/failures are traceable; timing clocks/boundaries valid; classification denominators and call-weighted coverage/timing explicit; diagnostics/limitations documented; original evidence survives retries/corrections; and results are ready for Plan 06.

Keep development selection separate from final results. Formal scores apply only to these prerecorded conversations and measured conditions. Microphone demo functionality, cellular-call operation, physical-phone performance, victim trust-building time, delay from first scam evidence and financial-loss prevention are not established by these results.

## References and rationale

- [Full Proposal](../00%20-%20DOCUMENTs/Full%20Proposal/Phoebe_FullProposal.pdf), PDF pp. 3–4, §§6.3 and 7.1–7.2: quality, latency and recorded emulator evaluation.
- [Pattern Recognition L06_Experimental Design and System Evaluation.pdf](course-lecture-sheets/Pattern%20Recognition%20L06_Experimental%20Design%20and%20System%20Evaluation.pdf), PDF pp. 19, 43, 45–50: reproducibility, condition-specific performance, component/system boundaries, latency, resources, failures and reporting. These are PDF pages, not printed slide numbers.
- Approved model plans supply metric conventions/frozen classifier behavior; STT Evaluation supplies recognition/scoring configuration; Application Integration supplies recording membership, runtime policy and selected context. Reuse their artifacts without repeating selection.

Recorded inputs permit reproduction; foreground/background separation tests different display conditions; human visibility confirmation avoids unsupported exact banner timestamps; coherent local clocks avoid cross-device timing errors. Completed-run scores plus all-assigned coverage expose failure effects. Small balanced test-derived recordings/synthetic conditions constrain claims; correlated repetitions do not enlarge independent sample count.

Twelve recordings, three runs, the 1/2 condition allocation, seed, warm-up, human observation, summary rules and artifact layout are owner-approved project conventions. Lectures guide the principles, not these exact settings. Runtime-dependent prerequisites remain explicit checkpoints in their owning plans.
