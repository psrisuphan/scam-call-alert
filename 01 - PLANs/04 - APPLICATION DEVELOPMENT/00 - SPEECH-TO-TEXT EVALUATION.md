# 00 - SPEECH-TO-TEXT EVALUATION

## Purpose and scope

Compare three pretrained STT models on the same Thai speech recordings and select one for application integration. Measure transcription errors, processing time, resources and failures. Use pretrained weights and standard inference settings without STT training, fine-tuning or parameter optimization; experimental training and tuning remain focused on the Scam classifier.

Application Integration owns incremental audio scheduling, transcript revisions, context comparisons and active audio-to-classification operation. Plan 05 owns final system evaluation. This component comparison does not establish streaming or warning performance.

## 1. Establish prerequisites and candidates

| Candidate | Comparison purpose |
|---|---|
| Whisper base, multilingual | Smaller Whisper model for quality and efficiency comparison. |
| Whisper small, multilingual | Measure whether a larger Whisper model improves transcription enough to justify its resource use. |
| `airesearch/wav2vec2-large-xlsr-53-th`, through PyThaiASR | Compare a Thai-finetuned model from another architecture. |

Explicitly select the Wav2Vec2 checkpoint through PyThaiASR; the package's default model must not silently replace it. Do not use English-only Whisper variants.

Pin checkpoint revisions, inference implementations and package versions. Record effective standard decoding settings and execution precision; wrappers may have different defaults. Retain standard behavior without a parameter search, optional language-model addition or corrective postprocessing experiment. Use transcription without translation, reference-text prompts or scam-specific hints. Resolve any required departure from standard behavior with the owner before proceeding.

Check documented candidate training data for overlap with the chosen evaluation material. Record known overlap and unavailable provenance; do not guarantee that public benchmark audio is unseen.

Obtain the classifier bundle and local-service identities from Model Freeze and App Handoff before the formal shared-host comparison. Dataset preparation can precede this dependency, but measurements requiring the classifier loaded cannot substitute an arbitrary classifier.

## 2. Prepare the shared comparison subset

Use GigaSpeech 2's Thai development split, which provides professionally prepared reference transcripts.

1. Record dataset version and access conditions.
2. Establish a stable ordering of eligible clip IDs.
3. Shuffle using seed 67; record the shuffle implementation/version.
4. Select complete clips until total audio duration reaches or slightly exceeds 15 minutes.
5. Save membership, selection procedure, exact duration and clip count before running candidates.
6. Use the same selected clips for every candidate and repetition.

Preserve original audio and references. Apply only model-required conversions, such as sample rate, channel count or format, recording settings and derived checksums. No additional denoising or augmentation is planned.

Document eligibility and missing/unusable audio or reference records before freezing membership. Do not silently replace difficult clips after observing model results. Unresolved data problems require review before freezing the subset. Retain available source identities and describe source coverage; random clip sampling does not guarantee independent speakers or recordings.

Fifteen minutes is a practical project budget, not a statistically guaranteed sample size. Conclusions concern this development subset, not all Thai speech or scam calls.

## 3. Establish the execution environment

Run STT on the same local computer intended to host the classifier; hosted transcription APIs are excluded.

Before the measured comparison:

1. Confirm the computer, OS and supported execution backend through compatibility checks.
2. Verify that the candidate and classifier can remain loaded together.
3. Keep the classifier loaded but idle.
4. Run one STT candidate at a time and process one clip at a time.
5. Record hardware, software, memory conditions and differences between candidate backends.

Do not assume GPU support. If a candidate cannot run under the intended arrangement, preserve evidence and obtain confirmation before replacing it or changing the environment. Record the actual runtime implementation so timing is understood as model-plus-implementation performance.

## 4. Execute and preserve the comparison

For each candidate:

1. Measure loading separately.
2. Perform one untimed warm-up using a fixed, documented development clip.
3. Process the complete subset three times, with fresh transcription rather than cached predictions.
4. Preserve each clip's output, timing, resource measurements and failures immediately after completion or failure.

Keep the model loaded between timed repetitions. Record clip order and reset transcript context between independent clips. Preserve each run under a distinct identity, including interrupted attempts and resumed-work provenance. Do not overwrite original evidence.

Processing time covers required per-clip preparation, transcription and output decoding after audio is read into memory. Measure audio-reading time separately. Include required conversion and device transfer in the processing boundary rather than silently omitting them. Synchronize asynchronous device work where necessary.

Standard decoding may produce different transcripts across repetitions, including Whisper's default temperature fallback. Preserve all predictions and report CER for each repetition; never select the best repetition. Record runtime randomness controls where applicable without modifying the standard decoding policy.

## 5. Calculate transcription quality

Use Character Error Rate (CER) as the primary accuracy metric; WER is not required.

`CER = (substitutions + deletions + insertions) / reference character count`

Apply identical scoring-only normalization to references and hypotheses:

- Unicode NFC normalization.
- Remove whitespace and Unicode punctuation.
- Lowercase English letters.
- Preserve Thai letters, vowels, tone marks and digits.
- Preserve number forms: do not convert digits to words or vice versa.

Count Unicode code points after normalization, not grapheme clusters or model tokens. Document the exact normalization procedure and implementation version. Retain original references/hypotheses alongside scoring copies. Scoring normalization must not alter the transcript supplied to the classifier.

For each repetition, sum edit counts across scored clips and divide by summed reference character counts. Retain per-clip edit counts, denominators and CER; do not substitute the mean of clip CERs for corpus CER. Repetitions do not create additional independent audio samples.

### Empty outputs and failures

- A successful empty hypothesis against a nonempty reference counts as deletions.
- Execution failure remains a failure without an invented transcript or CER.
- An empty normalized reference has undefined individual CER and is reported separately, with output retained.
- Report completed, failed and scored clip counts and scored audio duration.
- If candidates fail on different clips, also compare their common successfully scored clips, explicitly reporting coverage.
- CER can exceed 100% because of insertions; do not cap it.

These normalization rules reduce formatting penalties but can hide meaningful punctuation differences, such as decimal separators. Preserved number forms can penalize equivalent spoken/written expressions. Inspect original examples and document these limitations. Do not claim direct comparability with published CER using different normalization.

## 6. Summarize runtime and resources

Record per-clip processing times, each subset repetition's elapsed processing time, loading time, failures, peak RAM/VRAM and CPU/GPU use where measurable. Record classifier-only memory baseline and combined STT/classifier peak, distinguishing total memory from additional STT demand.

For each repetition, successful-path real-time factor is:

`sum of successful clip processing seconds / sum of those clips' audio seconds`

Report failed attempts and their elapsed time separately, alongside total attempted runtime. Do not divide successful processing time by the duration of failed clips. Identify unavailable measurements explicitly.

Report mean and sample standard deviation (ddof=1) across the three timed repetitions for comparable runtime summaries, retaining every run and its completion coverage. Explain incomplete runs; do not present reduced-work runs as equivalent full-subset timings. SD is unavailable with fewer than two comparable observations.

RTF below 1 means processing is faster than the measured audio duration. It does not prove streaming, incremental response time or early warnings. The classifier is idle during this benchmark; active combined operation belongs to Application Integration.

## 7. Review, select and hand off

Present CER for all repetitions, completion coverage, runtime, resources and representative errors together. The owner confirms the final choice using measured tradeoffs; no numerical cutoff or automatic winner is imposed.

Document why the selected model is suitable and why alternatives were not selected. Freeze model identity, inference implementation, versions, standard settings, required audio conversion and output contract.

Provide a reusable adapter producing chronological recognized text without Caller/Receiver markers or caller extraction. References are scoring evidence and must never replace recognized words in the inference path. Verify compatibility with the shared unlabeled input-preparation contract from Plan 02 and Model Freeze and App Handoff.

Selection establishes the preferred STT component. Application Integration must verify incremental operation while the classifier is active. A failure there requires evidence and owner-approved revision; it does not authorize silent replacement or reconfiguration of STT. This plan does not prescribe incremental chunking or context settings.

## 8. Keep audio purposes distinct

| Purpose | Audio policy |
|---|---|
| STT comparison | Selected GigaSpeech 2 Thai development recordings. |
| Application development | Human or AI recordings derived from classifier training conversations. |
| Final system evaluation | Reserved recordings derived from classifier test conversations. |
| Presentation demo | Any permitted audio source, with provenance and rehearsal use recorded. |

Keep recording variants of an underlying conversation in the same development/final partition. Final audio remains unused for rehearsals or debugging until final evaluation is complete. Test-derived audio is another input condition, not an independent dataset.

Application Integration specifies conversation recording counts, references and incremental handling. Verify references against actual speech rather than assuming a script exactly matches a recording. Identify human and synthetic recording conditions separately when reporting results. Demo examples without reliable labels demonstrate behavior but do not establish accuracy.

## 9. Outputs and storage

Store the following under `04 - APPLICATION DEVELOPMENT/stt/`:

| Output | Purpose |
|---|---|
| `README.md` | File purposes, persistent artifact locations and reproduction instructions. |
| `audio_manifest.csv` | Dataset identity, selected clip IDs, source identities where available, paths, checksums and durations; preparation exclusions are also accounted for. |
| `stt_protocol.md` | Frozen sampling, normalization, scoring, timing, resources and failure procedures. |
| `candidate_configs.json` | Checkpoint and inference implementation versions, effective defaults and execution identities. |
| `transcription_results.jsonl` | Per-clip/run original references, predictions, scoring copies/counts, timings, resource evidence and failures. |
| `stt_metrics.csv` | Quality, completion, runtime and resource summaries with denominators and measurement conditions. |
| `stt_report.md` | Comparison, representative error analysis, limitations and owner-confirmed selection rationale. |
| `stt_config.json` | Selected reproducible configuration for integration. |
| Comparison/scoring code | Reproduce selection, transcription, measurement, scoring and reports. |
| Reusable STT adapter | Load the selected model and return actual recognized text under its documented contract. |

Code filenames and libraries remain flexible within the required behavior. Track code, instructions, configuration identities, manifests and aggregate reports. Keep audio, weights and detailed generated sample results outside Git in documented persistent storage, including sample excerpts if sensitive. Record artifact paths/checksums and preserve recovery evidence; do not rely solely on temporary caches. Include no credentials.

## 10. Completion criteria

Complete when dataset membership and candidate identities are reproducible; selected clips and repetitions are accounted for; CER follows the documented normalization/aggregation; timing/resources/failures have explicit boundaries and denominators; the owner has confirmed selection; the adapter supplies compatible role-free text; and required evidence, runnable code and instructions are available for Application Integration.

Actual host compatibility must be demonstrated during implementation. Plan approval alone does not establish memory fit, transcription quality or near-real-time performance.

## References and rationale

- [Strong Idea](../../00%20-%20DOCUMENTs/Strong%20Idea/Phoebe_strongidea.pdf), PDF p. 1, §2: Whisper and PyThaiASR candidates, Thai support and low latency.
- [Full Proposal](../../00%20-%20DOCUMENTs/Full%20Proposal/Phoebe_FullProposal.pdf), PDF pp. 1, 3–4, §§2.4–3, 6.3, 7.1–7.2: prepared Thai audio, transcription, classification and near-real-time emulator prototype.
- [Pattern Recognition L06_Experimental Design and System Evaluation.pdf](../course-lecture-sheets/Pattern%20Recognition%20L06_Experimental%20Design%20and%20System%20Evaluation.pdf), PDF pp. 19, 43, 45–50: reproducibility, conditions, component/system boundaries, resource measurement and performance tradeoffs. Page references are PDF pages, not printed slide numbers.
- [GigaSpeech 2 dataset card](https://huggingface.co/datasets/speechcolab/gigaspeech2/blob/main/README.md): professionally transcribed development data and Thai CER evaluation.
- [Whisper documentation](https://github.com/openai/whisper) and [transcription implementation](https://github.com/openai/whisper/blob/main/whisper/transcribe.py): candidate sizes and default decoding/fallback behavior; pin actual versions for execution.
- [PyThaiASR documentation](https://github.com/PyThaiNLP/pythaiasr) and [Thai Wav2Vec2 model card](https://huggingface.co/airesearch/wav2vec2-large-xlsr-53-th): explicit supported checkpoint and documented training/inference provenance.

CER avoids introducing a Thai word-segmentation policy. One common subset and host support comparable results; three repetitions describe runtime variation. Subset duration, seed, repetitions, normalization and owner selection are project conventions, not settings prescribed by the lectures. General speech performance does not establish scam-dialogue performance; application and final-system evidence remain necessary.
