# STT Comparison Protocol

This protocol records the approved four-candidate standalone comparison for Plan 04/00. It does not replace the plan.

## Dataset and fixed subset

- Source: Google FLEURS Thai `th_th`, `dev`, repository revision `70bb2e84b976b7e960aa89f1c648e09c59f894dd`.
- Subset: 35 complete clips selected in seed-67 shuffled order; 456.06 seconds total (7.60 minutes).
- Reference: FLEURS `raw_transcription`; preserve `transcription` as source metadata.
- FLEURS is read speech based on parallel sentences, not spontaneous calls.

## Candidate inference and process isolation

- Host: MacBook Air M2, macOS 27.0.1, arm64, 8 GiB unified memory; Python 3.12.15.
- Candidates: Whisper base multilingual, Whisper small multilingual, pinned PyThaiASR Wav2Vec2 XLSR Thai, and Typhoon ASR Real-Time FastConformer RNN-T via PyThaiASR ONNX.
- A fresh process runs each candidate. It loads the model, performs one untimed warm-up, then processes the frozen 35 clips in manifest order for three repetitions. No classifier is loaded.
- Whisper uses the standard `openai-whisper` transcription defaults. Wav2Vec2 uses the pinned local snapshot and PyThaiASR with language model disabled. Typhoon uses the pinned ONNX snapshot at revision `04af3e7b6d822cb2807bc539301669d4f84691e7`; file checksums are recorded in `candidate_configs.json` and the run identity.
- Record Typhoon's actual encoder and decoder ONNX Runtime providers. Provider choice does not establish which system hardware units execute every operation.
- Preserve each transcription/failure as JSONL immediately. Preserve resource samples every 0.5 seconds to CSV while timed inference proceeds.

## Resource measurements

- Record process RSS before model load, after model load, after warm-up, and peak sampled RSS during timed inference. RSS is a process-level measure, not all system memory pressure.
- Sample process CPU utilization at a fixed 0.5-second interval during all timed repetitions; report arithmetic mean and maximum sampled CPU percent. Values can exceed 100% when a process uses multiple cores.
- For PyTorch MPS candidates, also sample `torch.mps.driver_allocated_memory()` and report its pre-load, post-load, post-warm-up, and sampled peak values separately from RSS. It is a backend allocation indicator, includes allocator/framework allocations, and is non-additive with RSS. Apple Silicon uses unified physical memory.
- Typhoon reports process RSS and the actual ONNX Runtime provider; PyTorch MPS allocation is not applicable.
- The sampler adds small measurement overhead; 0.5-second polling can miss shorter peaks. No classifier is loaded, so these figures do not represent combined app demand or system-wide GPU utilization.

## Timing and scoring

- Keep audio file reading separate from model processing. Processing time includes transcription and output decoding, with MPS synchronization at boundaries for PyTorch candidates.
- Primary quality metric: corpus CER, calculated from summed character substitutions, deletions and insertions divided by summed normalized reference code points.
- Scoring-only normalization: Unicode NFC; remove whitespace and Unicode punctuation; lowercase ASCII letters; retain Thai marks and digits; do not change number forms. Preserve original references and hypotheses.
- Report per-clip results, per-repetition CER, successful-path real-time factor, completion/failure coverage, and mean/sample SD across three repetitions. Batch RTF does not establish streaming or warning latency.
- Empty references have undefined per-clip CER; execution failures receive no invented transcript or CER.

## Reproduction and evidence

Store run-level evidence outside Git under `~/Library/Application Support/scam-call-alert/application-development/stt/runs/stt-20261011-four-candidate-resources/`. The run includes each isolated candidate's raw rows, resource samples and summaries plus merged results, provider/model identity, worker statuses and scoring outputs. The earlier three-candidate run remains preserved as historical quality/timing-only evidence and is not overwritten.
