# Development context screen (provisional)

This is a first-pass, development-only screening result. Recording fidelity is unverified; the owner declined human verification. The owner selected an approach for bounded demo use; formal integration freeze and final system evaluation are separate gates.

- Assigned: 36; complete: 27; failed/cancelled: 9
- Model: `interim` / `af64d3a917d5db82bc9dfe794c8f29125bbf13ad9060f726c75ac001f99d838b`
- Configuration: `e4531cf451b1df94295d5f5a413bab0508c19edc303fc8750bfe4b938f11390b`

| Approach | Assigned | Complete | Failed/cancelled | Coverage (n/assigned) | Scam P | Scam R | Scam F1 | Macro F1 | Accuracy | False warnings | Missed Scam | Assigned source counts | Completed source counts | True Scam host event timing n / mean ± sample SD (s) | False-warning host event timing n / mean ± sample SD (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|
| latest | 12 | 10 | 2 | 10/12 | 0.714 | 0.833 | 0.769 | 0.670 | 0.700 | 2 | 1 | {'primary': 6, 'supplemental': 6} | {'primary': 6, 'supplemental': 4} | 5 / 34.182 ± 19.459 | 2 / 70.445 ± 22.716 |
| recent | 12 | 9 | 3 | 9/12 | 1.000 | 0.600 | 0.750 | 0.775 | 0.778 | 0 | 2 | {'primary': 6, 'supplemental': 6} | {'primary': 5, 'supplemental': 4} | 3 / 28.363 ± 22.935 | 0 / NA ± NA |
| accumulated | 12 | 8 | 4 | 8/12 | 1.000 | 0.800 | 0.889 | 0.873 | 0.875 | 0 | 1 | {'primary': 6, 'supplemental': 6} | {'primary': 5, 'supplemental': 3} | 4 / 31.002 ± 20.785 | 0 / NA ± NA |

## Run identities

- APK SHA-256: `d9b94c7ae2ffd8e3c090a14bf1aa75a450a207ffba97ae26ccb269ec89f4d8d3`; installed APK SHA-256: `d9b94c7ae2ffd8e3c090a14bf1aa75a450a207ffba97ae26ccb269ec89f4d8d3`
- Artifact manifest SHA-256: `4dcef8c4868134f7a31e3ce2f92406ea7c450cf86fa09cf7c3562b3ddc5bba7b`; attempt ledger SHA-256: `7f8934a6d390c5a52e1f9a4271bdd7144f70aea5b8a6bf66734ec3233373d624`
- Aggregate code SHA-256: `6700959eae61885e7d0e0b4a34c76c7de16e6e80afffaaf3276865abac12c714`; schedule SHA-256: `0539167f8ffe637e5495a34d62760792103df64b8eceb97bf1a750ea97997967`
- The APK hash is constant across the 36 starts. Four exact runtime source snapshots were recorded, differing only in `service/context_comparison_harness.py`; the other listed app source hashes are unchanged. This reflects harness revisions during recovery, so results retain per-run source identity and should be read with that caveat. Full file-by-file hashes and assignment mapping are in the JSON. This postprocessing code was not part of the recorded APK/source identity.

## Matched completed recordings

This secondary comparison restricts the same first-pass results to recording IDs with a usable completed run for all three approaches. It does not add runs; approach metrics and timing denominators are recalculated on that shared subset.

Matched recording IDs: `['development-00', 'development-02', 'development-03', 'development-04', 'development-05', 'development-06', 'development-07', 'development-08']`. Matched set composition by unique recording: `{'Scam': 5, 'Not Scam': 3}` by true label and `{'primary': 5, 'supplemental': 3}` by source. All approaches share these IDs; failures outside this subset remain in the full assigned-run tables.

| Approach | Matched recordings | Completed / matched | Scam P | Scam R | Scam F1 | Macro F1 | Accuracy | False warnings | Missed Scam | Assigned source counts | Completed source counts | True Scam timing n / mean ± sample SD (s) | False-warning timing n / mean ± sample SD (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|
| latest | 8 | 8/8 | 0.667 | 0.800 | 0.727 | 0.564 | 0.625 | 2 | 1 | {'primary': 5, 'supplemental': 3} | {'primary': 5, 'supplemental': 3} | 4 / 31.476 ± 21.356 | 2 / 70.445 ± 22.716 |
| recent | 8 | 8/8 | 1.000 | 0.600 | 0.750 | 0.750 | 0.750 | 0 | 2 | {'primary': 5, 'supplemental': 3} | {'primary': 5, 'supplemental': 3} | 3 / 28.363 ± 22.935 | 0 / NA ± NA |
| accumulated | 8 | 8/8 | 1.000 | 0.800 | 0.889 | 0.873 | 0.875 | 0 | 1 | {'primary': 5, 'supplemental': 3} | {'primary': 5, 'supplemental': 3} | 4 / 31.002 ± 20.785 | 0 / NA ± NA |

## Provisional screening signal

On the matched completed subset, accumulated has the highest Scam F1 and is tied with recent for the fewest observed false warnings (zero each). Treat this only as a provisional screening signal: the shared subset contains 8 recordings (5 Scam, 3 Not Scam), all first-pass comparisons are one run per recording and approach, and recording/script fidelity was not human-verified. Failures exclude all valid Supplemental Not Scam examples in the accumulated arm, so its zero observed false warnings are especially weak evidence. This result alone does not establish a formal integration freeze.


## Owner-approved demo choice

The owner approved **accumulated context** for provisional demo use on 2026-10-14, retaining `newest eligible source text` within a 510-token budget. Approval basis: Matched 8 completed recordings: Scam F1 latest 0.7272727273, recent 0.75, accumulated 0.8888888889. Source: `01 - PLANs/04 - APPLICATION DEVELOPMENT/01 - MOBILE EMULATOR PROTOTYPE AND INTEGRATION.md section 11`; immutable selection sidecar SHA-256: `d44f822771c42ebee98bd2f5d4271617fc79db94f49ab8588ac9881cd4f1ea7d`.
The choice is bound here to the recorded `interim` model `af64d3a917d5db82bc9dfe794c8f29125bbf13ad9060f726c75ac001f99d838b` and configuration `e4531cf451b1df94295d5f5a413bab0508c19edc303fc8750bfe4b938f11390b`. Formal release approved: `false`; final-test access authorized: `false`. Demo selection does not complete current-model microphone/background acceptance, official packaging, or formal Plan 05 release.

## Undefined metric flags

Undefined classification metrics are stored as numeric zero with `metric_defined: false` and a reason in the JSON. A zero with a true flag is an observed zero score.

- **latest:** no undefined metrics.
- **recent:** no undefined metrics.
- **accumulated:** no undefined metrics.

## Assigned run accounting

Every frozen assignment appears once in the JSON. Failed runs remain in coverage denominators and are excluded from classification metrics; early Scam events on failed runs are retained as execution evidence only.

| Assigned run | Approach | Recording | Status | Exclusion reasons | Harness error |
|---|---|---|---|---|---|
| first-pass-01-recent | recent | development-01 | harness_failure | attempt_not_complete, snapshot_not_complete, error_present, timeout_status_unrecorded, sample_count_or_format_mismatch | ADB command failed: shell  |
| first-pass-01-accumulated | accumulated | development-01 | harness_failure | attempt_not_complete, snapshot_not_complete, error_present, timeout_status_unrecorded, sample_count_or_format_mismatch | App must be on the home screen before each assigned run |
| first-pass-09-latest | latest | development-09 | harness_failure | attempt_not_complete, snapshot_not_complete, error_present, timeout_status_unrecorded, sample_count_or_format_mismatch | Android control not found/clickable: จำลองสายเข้า |
| first-pass-09-recent | recent | development-09 | harness_failure | attempt_not_complete, snapshot_not_complete, error_present, timeout_status_unrecorded, sample_count_or_format_mismatch | Android control not found/clickable: จำลองสายเข้า |
| first-pass-09-accumulated | accumulated | development-09 | harness_failure | attempt_not_complete, snapshot_not_complete, error_present, timeout_status_unrecorded, sample_count_or_format_mismatch | ADB command failed: shell  |
| first-pass-10-accumulated | accumulated | development-10 | harness_failure | attempt_not_complete, snapshot_not_complete, error_present, timeout_status_unrecorded, sample_count_or_format_mismatch | Android control not found/clickable: เริ่ม Session ใหม่ |
| first-pass-11-accumulated | accumulated | development-11 | harness_failure | attempt_not_complete, snapshot_not_complete, error_present, timeout_status_unrecorded, sample_count_or_format_mismatch | ADB command failed: shell  |
| first-pass-11-latest | latest | development-11 | harness_failure | attempt_not_complete, snapshot_not_complete, error_present, timeout_status_unrecorded, sample_count_or_format_mismatch | Recording row tap left the home screen; refusing to accept a call |
| first-pass-11-recent | recent | development-11 | harness_failure | attempt_not_complete, snapshot_not_complete, error_present, timeout_status_unrecorded, sample_count_or_format_mismatch | Android control not found/clickable: บทสนทนาที่บันทึกไว้ |

## Per-approach confusion matrices

### latest

Rows are actual labels; columns are predicted labels. Incomplete cases are unresolved and excluded from the matrix, with assigned denominator and coverage shown above.

| Actual \ Predicted | Scam | Not Scam |
|---|---:|---:|
| Scam | 5 | 1 |
| Not Scam | 2 | 2 |

### recent

Rows are actual labels; columns are predicted labels. Incomplete cases are unresolved and excluded from the matrix, with assigned denominator and coverage shown above.

| Actual \ Predicted | Scam | Not Scam |
|---|---:|---:|
| Scam | 3 | 2 |
| Not Scam | 0 | 4 |

### accumulated

Rows are actual labels; columns are predicted labels. Incomplete cases are unresolved and excluded from the matrix, with assigned denominator and coverage shown above.

| Actual \ Predicted | Scam | Not Scam |
|---|---:|---:|
| Scam | 4 | 1 |
| Not Scam | 0 | 3 |

## Resource and timing notes

Per-assignment host CPU, RSS and MPS allocation; STT window and classifier request durations; derived queue high-water; native Android PSS and cumulative CPU-time observations; notification-posted client elapsed/audio position; pause observations; prediction events; and UI evidence references are retained in the machine-readable aggregate JSON alongside each session's original event log. Android CPU time is not utilization. Notification posting is not banner visibility or render latency. Detection timing summaries omit undetected cases and report `n`; sample SD is unavailable for fewer than two observations. No source audio or transcript text is copied into this report.

## Limitations

- Only the frozen 36 development first-pass assignments are included; no held-out records are accessed.
- All 36 assignments were attempted once with no retries: 27 completed and 9 ended in ADB, emulator/UI navigation, or app-state harness failures. Failures are execution coverage gaps, not classifier errors; no unattempted assignments remain.
- The classifier is the owner-approved interim PhayaThaiBERT adapter. The official evaluated model handoff/manifest is still not packaged, and this model has not been evaluated on final-test data; this result is not formal context-comparison or model-selection evidence.
- Classification metrics use only assignments with both terminal states complete, no error or harness timeout, and exact expected source and processed sample counts; all assigned cases remain in the coverage denominator.
- Conversation outcomes use any valid Scam prediction on a usable completed run; Not Scam requires a usable completed run with a valid prediction.
- The matched-completed comparison includes only recording IDs with usable completed runs for all three approaches; its denominators are shown separately.
- True Scam event timing is reported for actual Scam cases with a Scam prediction; false-warning event timing is reported for actual Not Scam cases with a Scam prediction. These use host-monotonic classification-completion events relative to host session creation, not client receipt or exact banner/render latency. They exclude nondetections and report n and sample SD.
- System banner visibility is not assessed by the harness; screenshots/UI hierarchy document app warning rendering for later visual review.
- Host CPU/RSS/MPS values come only from host resource_sample events. STT processing duration comes from stt_completed.resources.processing_seconds; classifier duration pairs classification_started/completed by request ID using host monotonic elapsed time. Android process PSS and cumulative CPU-time maxima use native_resource_sample client observations where present; CPU time is not CPU utilization.
- Queue high-water is a derived sample-range backlog (accepted end sample minus latest completed STT end sample divided by sample rate), and is reported only when accepted audio ranges are valid and contiguous. It is not a native queue measurement.
- Notification posting uses the first native notification_posted client observation's client_elapsed_ms and audio_position_ms. These are separate playback elapsed/audio-position values; neither is banner visibility or render latency. Missing values stay null.
- Human audio/script fidelity is unverified; the owner declined human verification. The approved accumulated choice is for bounded demo use only; formal integration freeze and final-system claims remain unauthorized.
