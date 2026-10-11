# Standalone Thai STT Comparison Report

## Scope and limitations

The owner approved a standalone STT comparison because the official selected Scam classifier bundle was unavailable. This benchmark loads no classifier. It measures transcription CER, processing/loading time, process CPU/RSS, and PyTorch MPS allocation where applicable. It does not establish combined classifier/STT compatibility, whole-system resource demand, or streaming/warning latency; Application Integration still owns the combined check with the official classifier.

The four candidates were evaluated on the same 35 complete clips (456.06 seconds; 7.60 minutes) from Google FLEURS Thai `th_th` `dev`, revision `70bb2e84b976b7e960aa89f1c648e09c59f894dd`. FLEURS is read speech based on parallel sentences, not spontaneous call audio. These results do not establish performance on scam-call conversations.

## Execution and measurement

The comparison ran on a MacBook Air M2 (macOS 27.0.1, arm64, 8 GiB unified memory; Python 3.12.15). Each candidate ran in a fresh process, with one untimed warm-up and three complete repetitions over the same 35 clips. All 420 attempted transcriptions succeeded (35 × 4 × 3); no clip failures or missing rows were recorded. Standard Whisper decoding was used; Wav2Vec2 used the pinned PyThaiASR checkpoint with language model disabled; Typhoon used the pinned PyThaiASR FastConformer RNN-T ONNX files.

Process CPU and RSS were sampled every 0.5 seconds during timed inference. CPU is a percentage of one logical core and may exceed 100% when multiple cores are used. Peak RSS is the maximum sampled process resident set size. For MPS candidates, `torch.mps.driver_allocated_memory()` is shown separately; it includes framework/allocator memory and is non-additive with RSS. Apple Silicon shares physical memory between CPU and GPU. Typhoon's encoder and decoder both reported `CoreMLExecutionProvider` with `CPUExecutionProvider` fallback; MPS allocation is not applicable. The sampler adds small measurement overhead and may miss shorter peaks; these measurements do not represent system-wide GPU utilization.

CER is corpus CER per repetition using the shared project normalization. Means and SDs are across three repetitions (`ddof=1`). RTF is summed successful-path processing time divided by successfully scored audio duration; it is an offline batch measure.

| Candidate | CER mean ± SD (pp) | Mean RTF ± SD | Load (s) | CPU mean / peak (%) | Peak process RSS (GB) | Peak MPS allocation (GiB) |
|---|---:|---:|---:|---:|---:|---:|
| PyThaiASR / Wav2Vec2 large XLSR Thai | **13.55 ± 0.00** | **0.028 ± 0.001** | 4.13 | 10.1 / 25.5 | 0.464 | 3.104 |
| Whisper small multilingual | 22.13 ± 0.00 | 0.272 ± 0.002 | 5.13 | 30.3 / 38.3 | 0.662 | 1.382 |
| Whisper base multilingual | 37.72 ± 0.26 | 0.126 ± 0.004 | 2.59 | 33.3 / 42.7 | 0.420 | 1.089 |
| Typhoon ASR Real-Time (CoreML + CPU fallback) | 69.73 ± 0.00 | 0.089 ± 0.015 | 7.28 | 262.9 / 410.6 | 4.018 | N/A |

`pp` means percentage points. CPU peak reflects the maximum sampled process CPU percent, not a system-wide utilization value. Typhoon's CPU percentage above 100% indicates multi-core process activity. Its lower offline RTF does not offset its much higher CER on this particular subset. The high process RSS and CPU profile should be considered in later device integration, but cannot be directly added to or compared as total system memory with the MPS allocator figures.

## Interpretation and owner selection

The owner selected **PyThaiASR + Wav2Vec2 Thai** for Application Integration. It had the lowest CER (13.55%) and fastest mean batch RTF (0.028) among the four tested candidates, with stable identical transcripts across the three repetitions. This makes it the strongest measured quality-and-processing-speed choice on this subset. The selection is based on observed project results, not a claim that Wav2Vec2 is universally superior.

The tradeoff is memory: Wav2Vec2 showed the highest PyTorch MPS driver allocation among the three MPS candidates (3.104 GiB). The MPS figure and process RSS are non-additive, and this standalone benchmark did not load the Scam classifier. The selection is therefore **owner-confirmed for integration, pending the required combined compatibility/resource check**. It must not be treated as final app-freeze approval until that check passes. If it fails, preserve the evidence and discuss a change with the owner rather than silently replacing the candidate.

The alternatives were not selected for these measured results: Whisper small had lower CER than Whisper base but higher CER and slower mean processing than Wav2Vec2; Whisper base was also slower and had substantially higher CER; Typhoon had 69.73% CER and the highest standalone CPU/RSS despite a batch RTF below 1. These comparisons apply only to this small FLEURS read-speech subset and pinned implementations.

## Evidence files

The aggregate candidate/repetition table is tracked in `stt_metrics.csv`; the owner-selected integration configuration is recorded in `stt_config.json`. The detailed completed run is stored outside Git at `~/Library/Application Support/scam-call-alert/application-development/stt/runs/stt-20261011-four-candidate-resources/`:

- `comparison_manifest.json`, `candidate_configs.execution-snapshot.json`, `typhoon_model_identity.json`, and `worker_statuses.json`: execution identity and provenance.
- `transcription_results.jsonl`: all per-clip references, hypotheses, timings, and statuses.
- `candidate_runtime.json` and `candidates/*/resource_samples.csv`: load/provider/resource summaries and 0.5-second process samples.
- `scores/metrics.csv`, `scores/per_clip_scores.csv`, and `scores/common_clip_metrics.csv`: CER, timing, resource summaries, coverage and pairwise common-clip evidence.

The earlier three-candidate quality/timing-only run remains preserved at `~/Library/Application Support/scam-call-alert/application-development/stt/runs/stt-20261011-standalone/`; it was not overwritten and is not the source for the resource results above.

Dataset attribution: Conneau et al. (2022), [FLEURS: Few-shot Learning Evaluation of Universal Representations of Speech](https://arxiv.org/abs/2205.12446). FLEURS is distributed under CC BY 4.0; source and attribution details are recorded in the dataset selection manifest.
