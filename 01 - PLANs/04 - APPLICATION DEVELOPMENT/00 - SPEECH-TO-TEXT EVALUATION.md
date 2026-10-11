# 00 - SPEECH-TO-TEXT EVALUATION

## Purpose and scope

Compare four pretrained STT models on the same Thai speech recordings and select one for application integration. Measure transcription errors, processing time, standalone CPU/process-memory use and failures. Use pretrained weights and standard inference settings without STT training, fine-tuning or parameter optimization; experimental training and tuning remain focused on the Scam classifier.

Application Integration owns incremental audio scheduling, transcript revisions, context comparisons and active audio-to-classification operation. Plan 05 owns final system evaluation. This component comparison does not establish streaming or warning performance.

## 1. Establish prerequisites and candidates

### Owner-approved dataset substitution (2026-10-11)

Replace the previously planned GigaSpeech 2 Thai development subset with FLEURS Thai (`th_th`) `dev` partition from the public Hugging Face dataset repository. The owner approved this substitution because GigaSpeech 2 requires researcher-requested gated access, which was not available, while FLEURS is publicly hosted under CC BY 4.0. Preserve attribution and cite the FLEURS paper. Use only `dev` for candidate comparison; do not use FLEURS `test` to select an STT candidate. If a dataset loader calls this partition `validation`, record that alias while retaining `dev` as the source split identity.

FLEURS consists of read speech based on parallel FLoRes sentences, not spontaneous phone conversation. It provides a common, reference-transcribed benchmark for comparing these STT candidates, but its CER and runtime results do not establish accuracy on scam calls or natural conversational audio. Record this domain limitation in the comparison report and presentation materials.

### Owner-approved evaluation-set reduction (2026-10-11)

Use a 7.5-minute target (450 seconds) rather than the original 15-minute target to reduce the remaining evaluation workload before the project deadline. Select complete clips in the already approved seed-67 shuffled order until cumulative duration reaches or slightly exceeds 450 seconds. Freeze the subset before running any STT candidate and use exactly the same clips for all candidates and repetitions. Keep the planned three repetitions; repeating fixed clips measures execution variability but does not increase speech-sample coverage. Report the smaller-set limitation when interpreting CER and candidate differences.

### Owner-approved standalone comparison scope (2026-10-11)

The original comparison required the official selected Scam classifier loaded but idle on the same host and included combined resource measurements. Because the official classifier bundle was unavailable, the owner approved a standalone STT comparison. The initial three-candidate run therefore measured CER, loading/processing timing and failures without collecting resources; that run remains historical evidence. The owner later approved the standalone resource-profile expansion below. No Scam classifier is loaded for either standalone run, and neither establishes combined application compatibility. The loaded-classifier compatibility/resource check remains required during Application Integration before app freeze. The provisional WangchanBERTa fixture is not used.

### Owner-approved candidate and resource-profile expansion (2026-10-11)

Add Typhoon ASR Real-Time as a fourth candidate because its FastConformer RNN-T architecture is specifically designed for streaming Thai ASR. Run the PyThaiASR 2.3.0 `typhoon_asr` ONNX implementation, pin the model repository revision and file checksums, and record the actual ONNX Runtime execution provider. CoreML is available on the Mac, but verify which provider the model actually uses. Model-card and paper benchmark claims use their own data and text normalization and are not directly comparable with this project's CER.

Repeat all four candidates on the same MacBook Air M2, frozen 35-clip FLEURS subset and three-repetition protocol. Repeat the original three because their earlier run did not collect resource measurements; preserve that run and its evidence. Keep the classifier unloaded.

For each candidate, use a fresh process so its resource baseline is not affected by a previously loaded candidate. Record process RSS before model load, after load/warm-up, and peak during timed inference. Sample process CPU utilization during timed inference at a fixed 0.5-second interval and report its mean and peak; process CPU percentage can exceed 100% when multiple cores are used. For PyTorch MPS candidates, additionally record PyTorch MPS driver-allocated memory before load, after warm-up and peak during inference. Keep this MPS value separate from process RSS: it includes MPS allocator/framework allocations, and Apple Silicon shares physical memory between CPU and GPU rather than providing separate VRAM. For Typhoon, record the selected ONNX Runtime provider and mark the PyTorch MPS metric not applicable. These measurements describe each standalone STT process, not full-app CPU/memory pressure or classifier-plus-STT demand.

Use each candidate's documented practical backend on this Mac and record it: verified MPS for PyTorch candidates and PyThaiASR ONNX with its actual provider for Typhoon. Interpret results as model-plus-runtime-plus-backend performance, not architecture-only comparisons. Dataset, CER, timing, repetition, failure-accounting and owner-selection rules remain unchanged. The official-classifier combined compatibility/resource check remains in Application Integration.

| Candidate | Comparison purpose |
|---|---|
| Whisper base, multilingual | Smaller Whisper model for quality and efficiency comparison. |
| Whisper small, multilingual | Measure whether a larger Whisper model improves transcription enough to justify its resource use. |
| `airesearch/wav2vec2-large-xlsr-53-th`, through PyThaiASR | Compare a Thai-finetuned model from another architecture. |
| Typhoon ASR Real-Time (`typhoon_asr` through PyThaiASR) | Add a Thai streaming-oriented FastConformer RNN-T candidate and measure its subset quality, timing and standalone resources under the same protocol. |

Explicitly select the Wav2Vec2 checkpoint through PyThaiASR; the package's default model must not silently replace it. Do not use English-only Whisper variants.

Pin checkpoint revisions, inference implementations and package versions. Record effective standard decoding settings and execution precision; wrappers may have different defaults. Retain standard behavior without a parameter search, optional language-model addition or corrective postprocessing experiment. Use transcription without translation, reference-text prompts or scam-specific hints. Resolve any required departure from standard behavior with the owner before proceeding.

Check documented candidate training data for overlap with the chosen evaluation material. Record known overlap and unavailable provenance; do not guarantee that public benchmark audio is unseen.

Use the standalone scope approved above for this comparison. The official classifier bundle and local-service identities remain prerequisites for the deferred combined model/STT compatibility and resource check in Application Integration. Do not substitute the provisional app fixture for the selected model.

## 2. Prepare the shared comparison subset

Use the official `data/th_th/dev.tsv` and `data/th_th/audio/dev.tar.gz` files from FLEURS. Pin the repository revision before selection; the revision observed for this approved source on 2026-10-11 is `70bb2e84b976b7e960aa89f1c648e09c59f894dd`. The `dev.tsv` at that revision has 439 rows; verify and record the count and file checksums against the pinned revision. Per the official FLEURS loader schema, column 3 is `raw_transcription`, column 4 is `transcription`, column 2 is the WAV filename, column 6 is the sample count, and column 7 is gender. Preserve both transcript fields and use `raw_transcription` as the scored reference; apply the same project scoring normalization to every candidate and reference. Do not switch reference fields between candidates.

1. Record the dataset revision, config (`th_th`), source split (`dev`), license and attribution.
2. Establish a stable ordering of eligible clip IDs.
3. Shuffle using seed 67; record the shuffle implementation/version.
4. Select complete clips until total audio duration reaches or slightly exceeds 7.5 minutes (450 seconds), as recorded in the owner-approved evaluation-set reduction above.
5. Save membership, selection procedure, exact duration and clip count before running candidates.
6. Use the same selected clips for every candidate and repetition.

Preserve selected audio and both source reference fields. Apply only model-required conversions, such as sample rate, channel count or format, recording settings and derived checksums. No additional denoising or augmentation is planned. Keep audio and detailed sample results outside Git in documented persistent storage; include FLEURS attribution and citation in the tracked dataset manifest/report.

Document eligibility and missing/unusable audio or reference records before freezing membership. Do not silently replace difficult clips after observing model results. Unresolved data problems require review before freezing the subset. Retain available source identities and describe source coverage; random clip sampling does not guarantee independent speakers or recordings.

The 7.5-minute subset is a practical project budget, not a statistically guaranteed sample size. Conclusions concern this FLEURS read-speech development subset, not spontaneous Thai speech, all Thai speech, or scam calls.

## 3. Establish the execution environment

Run STT on the selected MacBook Air M2; hosted transcription APIs are excluded. No Scam classifier is loaded during the standalone comparison. Record the actual host, OS, software versions and supported execution backend. Application Integration must later verify that the selected STT and official classifier can coexist on the host and gather combined resource evidence before freezing the app.

Before the standalone measured comparison:

1. Confirm the computer, OS and supported execution backend through compatibility checks.
2. Verify that the candidate can run on the selected backend.
3. Run one STT candidate per fresh process and process one clip at a time.
4. Record hardware/software versions and the actual backend/provider for each candidate.

Do not assume GPU support. If a candidate cannot run on the selected backend, preserve evidence and obtain confirmation before replacing it or changing the environment. Record the actual runtime implementation so timing is understood as model-plus-implementation performance.

## 4. Execute and preserve the comparison

For each candidate:

1. Measure loading separately.
2. Perform one untimed warm-up using a fixed, documented development clip.
3. Process the complete subset three times, with fresh transcription rather than cached predictions.
4. During timed inference, sample process CPU and memory at the approved interval; preserve each clip's output, timing, resource samples and failures immediately.

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

Record per-clip processing times, each subset repetition's elapsed processing time, loading time, backend/provider and failures. For the approved standalone resource profile, report process CPU mean/peak and process RSS before load, after load/warm-up and peak during inference. Record the 0.5-second CPU/memory sampling interval. Process CPU percentage can exceed 100% across cores. For MPS-backed PyTorch candidates, also report `torch.mps.driver_allocated_memory()` before load, after warm-up and peak; it includes MPS driver's cached allocator and framework allocations. Keep it separate from process RSS because Apple Silicon shares physical memory between CPU and GPU. Typhoon reports the ONNX Runtime execution provider; the PyTorch MPS metric is not applicable. No classifier is loaded, so these measurements describe the isolated STT process and do not represent combined app use, other applications' host consumption, or system-wide accelerator utilization. Application Integration still measures compatibility and resource demand with the official classifier active.

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
| STT comparison | Seeded subset of FLEURS Thai `dev` recordings. |
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
| `stt_protocol.md` | Frozen sampling, normalization, scoring, timing, scope limitations and failure procedures. |
| `candidate_configs.json` | Checkpoint and inference implementation versions, effective defaults and execution identities. |
| `transcription_results.jsonl` | Per-clip/run original references, predictions, scoring copies/counts, timings and failures. |
| `stt_metrics.csv` | Quality, completion, timing, process CPU/memory and available backend-memory summaries with denominators and measurement conditions. |
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
- [FLEURS Thai data files](https://huggingface.co/datasets/google/fleurs/tree/70bb2e84b976b7e960aa89f1c648e09c59f894dd/data/th_th), [dataset card](https://huggingface.co/datasets/google/fleurs), and [official loader schema](https://huggingface.co/datasets/google/fleurs/blob/d74c1f182ca32a92215e33f39aa25543ae5a5647/fleurs.py): public `th_th` development files, fields, licensing, sampling rate and dataset limitations.
- [FLEURS paper](https://arxiv.org/abs/2205.12446): dataset construction and multilingual benchmark design.
- [Whisper documentation](https://github.com/openai/whisper) and [transcription implementation](https://github.com/openai/whisper/blob/main/whisper/transcribe.py): candidate sizes and default decoding/fallback behavior; pin actual versions for execution.
- [PyThaiASR documentation](https://github.com/PyThaiNLP/pythaiasr) and [Thai Wav2Vec2 model card](https://huggingface.co/airesearch/wav2vec2-large-xlsr-53-th): supported model implementations and documented training/inference provenance.
- [Typhoon ASR Real-Time model card](https://huggingface.co/typhoon-ai/typhoon-asr-realtime), [paper](https://arxiv.org/abs/2601.13044), and [PyThaiASR ONNX integration](https://github.com/PyThaiNLP/pythaiasr): streaming-oriented Thai FastConformer RNN-T candidate. Published metrics are not directly comparable where dataset, normalization, runtime or hardware differ.
- [Apple Metal unified-memory description](https://developer.apple.com/documentation/metal/mtldevice/hasunifiedmemory) and [PyTorch MPS driver allocation API](https://docs.pytorch.org/docs/main/generated/torch.mps.driver_allocated_memory.html): interpret Apple GPU memory as shared physical memory and MPS allocation as a separate, non-additive backend diagnostic.

CER avoids introducing a Thai word-segmentation policy. One common subset and host support comparable results; three repetitions describe runtime variation. FLEURS avoids the unavailable GigaSpeech access gate and offers a reference-transcribed Thai benchmark, but its read-speech/parallel-sentence design is less representative of spontaneous call audio. Standalone resource results describe each STT process on this host; they do not establish combined app memory fit or final-classifier performance. Subset duration, seed, repetitions, normalization, resource sampling interval and owner selection are project conventions, not settings prescribed by the lectures. General speech performance does not establish scam-dialogue performance; application and final-system evidence remain necessary.
