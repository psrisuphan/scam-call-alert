#!/usr/bin/env python3
"""Run the Plan 04/00 standalone four-candidate STT comparison."""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import os
import platform
import threading
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import soundfile as sf


ROOT = Path(__file__).resolve().parents[2]
WAV2VEC_REPOSITORY = "airesearch/wav2vec2-large-xlsr-53-th"
WAV2VEC_REVISION = "3155938c549b23eee16b1d4b55dcb161b7fe4bcf"
WHISPER_CANDIDATES = (
    ("whisper-base-multilingual", "base"),
    ("whisper-small-multilingual", "small"),
)
WAV2VEC_CANDIDATE = "wav2vec2-large-xlsr-53-th"
TYPHOON_CANDIDATE = "typhoon-asr-realtime"
RESOURCE_INTERVAL_SECONDS = 0.5


class ResourceSampler:
    """Sample an isolated worker's CPU, RSS and optional MPS allocation."""

    def __init__(self, output: Path, torch_module, mps_applicable: bool, interval: float = RESOURCE_INTERVAL_SECONDS):
        import psutil
        self.process = psutil.Process()
        self.output = output
        self.torch = torch_module
        self.mps_applicable = mps_applicable
        self.interval = interval
        self.samples: list[dict[str, Any]] = []
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.started = time.perf_counter()
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.fields = ["elapsed_seconds", "phase", "process_cpu_percent", "process_rss_bytes", "pytorch_mps_driver_allocated_bytes"]
        with self.output.open("x", encoding="utf-8", newline="") as stream:
            csv.DictWriter(stream, fieldnames=self.fields).writeheader()

    def _mps_bytes(self):
        try:
            if self.mps_applicable and self.torch.backends.mps.is_available():
                return int(self.torch.mps.driver_allocated_memory())
        except Exception:
            pass
        return None

    def snapshot(self, phase: str, cpu_percent: float | None = None):
        row = {
            "elapsed_seconds": round(time.perf_counter() - self.started, 4),
            "phase": phase,
            "process_cpu_percent": cpu_percent,
            "process_rss_bytes": self.process.memory_info().rss,
            "pytorch_mps_driver_allocated_bytes": self._mps_bytes(),
        }
        self.samples.append(row)
        with self.output.open("a", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=self.fields)
            writer.writerow(row)
            stream.flush()
            os.fsync(stream.fileno())

    def _sample_loop(self):
        self.process.cpu_percent(None)
        while not self.stop_event.wait(self.interval):
            self.snapshot("timed_inference", self.process.cpu_percent(None))

    def start(self):
        self.started = time.perf_counter()
        self.process.cpu_percent(None)
        self.thread = threading.Thread(target=self._sample_loop, daemon=True)
        self.thread.start()

    def stop(self):
        if self.thread is not None:
            self.stop_event.set()
            self.thread.join()
        self.snapshot("timed_inference_end", self.process.cpu_percent(None))
        timed = [r for r in self.samples if r["phase"] in {"timed_inference", "timed_inference_end"}]
        cpu = [r["process_cpu_percent"] for r in timed if r["process_cpu_percent"] is not None]
        rss = [r["process_rss_bytes"] for r in timed]
        mps = [r["pytorch_mps_driver_allocated_bytes"] for r in timed if r["pytorch_mps_driver_allocated_bytes"] is not None]
        return {
            "sampling_interval_seconds": self.interval,
            "cpu_mean_percent": sum(cpu) / len(cpu) if cpu else None,
            "cpu_peak_percent": max(cpu) if cpu else None,
            "inference_peak_process_rss_bytes": max(rss) if rss else None,
            "inference_peak_pytorch_mps_driver_allocated_bytes": max(mps) if mps else None,
            "sample_count": len(self.samples),
            "timed_inference_sample_count": len(timed),
            "resource_samples_file": str(self.output),
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sync_device(torch_module, device: str) -> None:
    if device.startswith("mps"):
        torch_module.mps.synchronize()
    elif device.startswith("cuda"):
        torch_module.cuda.synchronize(device)


def load_wav2vec2_pythaiasr(device: str, snapshot_dir: Path):
    """Load the planned PyThaiASR model from the exact pinned local snapshot."""
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
    from pythaiasr import ASR

    for component in (Wav2Vec2Processor, Wav2Vec2ForCTC):
        original = component.from_pretrained.__func__

        def pinned_loader(cls, model_name, *args, _original=original, **kwargs):
            if model_name == WAV2VEC_REPOSITORY:
                model_name = str(snapshot_dir)
            return _original(cls, model_name, *args, **kwargs)

        component.from_pretrained = classmethod(pinned_loader)
    recognizer = ASR(model=WAV2VEC_REPOSITORY, device=device, lm=False)
    recognizer.model.eval()
    return recognizer


def load_candidate(candidate_id: str, device: str, model_cache: Path):
    if candidate_id in {item[0] for item in WHISPER_CANDIDATES}:
        import whisper

        model_name = dict(WHISPER_CANDIDATES)[candidate_id]
        model = whisper.load_model(model_name, device=device, download_root=str(model_cache))
        model.eval()
        return model
    if candidate_id == WAV2VEC_CANDIDATE:
        snapshot = (
            Path(os.environ["HF_HUB_CACHE"])
            / "models--airesearch--wav2vec2-large-xlsr-53-th"
            / "snapshots"
            / WAV2VEC_REVISION
        )
        if not (snapshot / "pytorch_model.bin").is_file():
            raise FileNotFoundError(f"Pinned Wav2Vec2 snapshot unavailable: {snapshot}")
        return load_wav2vec2_pythaiasr(device, snapshot)
    if candidate_id == TYPHOON_CANDIDATE:
        from pythaiasr.typhoon import FastConformerRNNT
        model_dir = Path(os.environ["TYPHOON_MODEL_DIR"])
        return FastConformerRNNT(
            device="auto",
            encoder_path=str(model_dir / "encoder-fastconformer-quran-ar.onnx"),
            decoder_path=str(model_dir / "decoder_joint-fastconformer-quran-ar.onnx"),
            vocab_path=str(model_dir / "tokenizer" / "vocab.json"),
        )
    raise ValueError(f"Unknown candidate: {candidate_id}")


def transcribe(candidate_id: str, model, audio):
    import torch

    if candidate_id in {item[0] for item in WHISPER_CANDIDATES}:
        result = model.transcribe(audio, verbose=None)
        return result["text"], result.get("language"), bool(result.get("segments"))
    with torch.inference_mode():
        if candidate_id == TYPHOON_CANDIDATE:
            text = model.transcribe(audio, sample_rate=16_000)
            if isinstance(text, dict):
                text = text.get("text", "")
        else:
            text = model(audio, sampling_rate=16_000)
    return text, "th", bool(text)


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def validate_inputs(data_dir: Path, manifest_path: Path):
    with manifest_path.open(encoding="utf-8", newline="") as stream:
        audio_rows = list(csv.DictReader(stream))
    if len(audio_rows) != 35 or len({row["audio_filename"] for row in audio_rows}) != 35:
        raise ValueError("Frozen STT manifest must contain the approved 35 unique selected clips.")
    required = {"audio_filename", "audio_path", "audio_sha256", "duration_seconds", "raw_transcription", "transcription"}
    missing = required - set(audio_rows[0])
    if missing:
        raise ValueError(f"Frozen audio manifest lacks required fields: {sorted(missing)}")
    for row in audio_rows:
        audio_file = (data_dir / row["audio_path"]).resolve()
        if not audio_file.is_file() or sha256_file(audio_file) != row["audio_sha256"]:
            raise ValueError(f"Selected audio file missing or checksum mismatch: {row['audio_filename']}")
    return audio_rows


def write_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_worker(args, candidate_id: str, output_dir: Path, audio_rows, model_cache: Path):
    import torch
    output_dir.mkdir(parents=True, exist_ok=False)
    run_id = f"stt-standalone-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    data_dir = args.data_dir.expanduser().resolve()
    sampler = ResourceSampler(output_dir / "resource_samples.csv", torch, candidate_id != TYPHOON_CANDIDATE)
    process = sampler.process
    pre_load_rss = process.memory_info().rss
    pre_load_mps = sampler._mps_bytes()
    sampler.snapshot("before_model_load")
    load_start = time.perf_counter()
    summary = {"candidate_id": candidate_id, "comparison_mode": "standalone_without_classifier"}
    try:
        model = load_candidate(candidate_id, args.device, model_cache)
        sync_device(torch, args.device)
        load_seconds = time.perf_counter() - load_start
        summary.update({"load_status": "success", "load_seconds": load_seconds,
                        "pre_model_load_process_rss_bytes": pre_load_rss,
                        "post_model_load_process_rss_bytes": process.memory_info().rss,
                        "pre_model_load_mps_driver_allocated_bytes": pre_load_mps,
                        "post_model_load_mps_driver_allocated_bytes": sampler._mps_bytes()})
    except Exception as exc:
        summary.update({"load_status": "failure", "load_seconds": time.perf_counter()-load_start,
                        "pre_model_load_process_rss_bytes": pre_load_rss,
                        "pre_model_load_mps_driver_allocated_bytes": pre_load_mps,
                        "load_error": f"{type(exc).__name__}: {exc}"})
        write_json(output_dir / "candidate_runtime.json", [summary])
        print(f"{candidate_id} failed during load: {exc}", flush=True)
        return 0

    result_path = output_dir / "transcription_results.jsonl"
    warmup = audio_rows[0]
    warmup_audio = None
    try:
        warmup_audio, sample_rate = sf.read(str(data_dir / warmup["audio_path"]), dtype="float32", always_2d=False)
        if sample_rate != 16_000 or getattr(warmup_audio, "ndim", 1) != 1:
            raise ValueError("Warm-up clip did not match mono 16 kHz input format.")
        transcribe(candidate_id, model, warmup_audio)
        sync_device(torch, args.device)
        warmup_status, warmup_error = "success", None
    except Exception as exc:
        warmup_status, warmup_error = "failure", f"{type(exc).__name__}: {exc}"
    if warmup_audio is not None:
        del warmup_audio
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()
    sampler.snapshot("after_warmup")
    post_warmup_sample = sampler.samples[-1]
    if candidate_id == TYPHOON_CANDIDATE:
        provider = {"encoder": model.encoder_session.get_providers(), "decoder": model.decoder_session.get_providers()}
    else:
        provider = {"pytorch_device": args.device}
    sampler.start()
    for repetition in range(1, 4):
        print(f"{candidate_id}: repetition {repetition}/3", flush=True)
        for row in audio_rows:
            audio = None
            audio_read_seconds = processing_seconds = 0.0
            record = {"run_id": run_id, "candidate_id": candidate_id, "repetition": repetition,
                      "clip_id": row["audio_filename"], "audio_sha256": row["audio_sha256"],
                      "audio_duration_seconds": float(row["duration_seconds"]),
                      "reference_raw_transcription": row["raw_transcription"],
                      "reference_normalized_transcription": row["transcription"]}
            try:
                t0 = time.perf_counter()
                audio, sample_rate = sf.read(str(data_dir / row["audio_path"]), dtype="float32", always_2d=False)
                audio_read_seconds = time.perf_counter() - t0
                if sample_rate != 16_000 or getattr(audio, "ndim", 1) != 1:
                    raise ValueError("Audio input did not match verified mono 16 kHz format.")
                sync_device(torch, args.device)
                t0 = time.perf_counter()
                hypothesis, language, has_output = transcribe(candidate_id, model, audio)
                sync_device(torch, args.device)
                processing_seconds = time.perf_counter() - t0
                record.update({"status":"success", "audio_read_seconds":audio_read_seconds,
                               "processing_seconds":processing_seconds, "hypothesis_raw_transcription":hypothesis,
                               "detected_language":language, "decoded_output_present":has_output})
            except Exception as exc:
                record.update({"status":"failure", "audio_read_seconds":audio_read_seconds,
                               "processing_seconds":processing_seconds, "error":f"{type(exc).__name__}: {exc}"})
            append_jsonl(result_path, record)
            if audio is not None:
                del audio
        print(f"Finished {candidate_id}, repetition {repetition}/3", flush=True)
    resource_summary = sampler.stop()
    summary.update({"warmup_status":warmup_status, "warmup_error":warmup_error, "backend_or_provider":provider,
                    "post_warmup_process_rss_bytes":post_warmup_sample["process_rss_bytes"],
                    "post_warmup_mps_driver_allocated_bytes":post_warmup_sample["pytorch_mps_driver_allocated_bytes"]})
    summary.update(resource_summary)
    if candidate_id == TYPHOON_CANDIDATE:
        summary["inference_peak_pytorch_mps_driver_allocated_bytes"] = None
        summary["mps_metric_status"] = "not_applicable_to_onnx_runtime_candidate"
    write_json(output_dir / "candidate_runtime.json", [summary])
    if candidate_id == TYPHOON_CANDIDATE:
        try:
            model.encoder_session = None
            model.decoder_session = None
        except Exception:
            pass
    del model
    gc.collect()
    print(f"Completed candidate worker: {candidate_id}", flush=True)


def run(args) -> None:
    default_root = Path.home() / "Library/Application Support/scam-call-alert/application-development/stt"
    cache_root = default_root / "huggingface-cache"
    os.environ.setdefault("HF_HOME", str(cache_root))
    os.environ.setdefault("HF_HUB_CACHE", str(cache_root))
    os.environ.setdefault("TYPHOON_MODEL_DIR", str(default_root / "typhoon-asr-realtime"))
    if not args.standalone:
        raise ValueError("Pass --standalone to confirm that no classifier is loaded.")
    data_dir = args.data_dir.expanduser().resolve()
    root_output = args.output_dir.expanduser().resolve()
    model_cache = args.model_cache.expanduser().resolve()
    manifest_path = args.audio_manifest.expanduser().resolve()
    if args.device != "mps":
        raise ValueError("This approved comparison host is the MacBook Air M2; use its verified MPS backend.")
    import torch
    if not torch.backends.mps.is_available():
        raise RuntimeError("PyTorch reports MPS unavailable on the comparison host.")
    audio_rows = validate_inputs(data_dir, manifest_path)

    if args.candidate_id:
        if root_output.exists():
            raise FileExistsError(f"Refusing to overwrite existing candidate output: {root_output}")
        run_worker(args, args.candidate_id, root_output, audio_rows, model_cache)
        return

    if root_output.exists():
        raise FileExistsError(f"Refusing to overwrite existing run directory: {root_output}")
    root_output.mkdir(parents=True)
    from huggingface_hub import snapshot_download
    typhoon_repo = "wannaphong/typhoon-asr-realtime-onnx"
    config_path = Path(__file__).with_name("candidate_configs.json")
    candidate_config = json.loads(config_path.read_text(encoding="utf-8"))
    typhoon_config = next(item for item in candidate_config["candidates"] if item["id"] == TYPHOON_CANDIDATE)
    revision = typhoon_config["checkpoint_revision"]
    typhoon_dir = Path(snapshot_download(
        repo_id=typhoon_repo, revision=revision,
        allow_patterns=["encoder-fastconformer-quran-ar.onnx", "decoder_joint-fastconformer-quran-ar.onnx",
                        "tokenizer/vocab.json", "export_metadata.json"],
        cache_dir=str(cache_root),
    ))
    os.environ["TYPHOON_MODEL_DIR"] = str(typhoon_dir)
    typhoon_files = [typhoon_dir / "encoder-fastconformer-quran-ar.onnx",
                     typhoon_dir / "decoder_joint-fastconformer-quran-ar.onnx",
                     typhoon_dir / "tokenizer/vocab.json", typhoon_dir / "export_metadata.json"]
    if not all(path.is_file() for path in typhoon_files):
        raise FileNotFoundError("Pinned Typhoon ONNX snapshot lacks expected model/vocabulary/metadata files.")
    typhoon_identity = {"repo_id":typhoon_repo, "revision":revision,
                        "files":{str(p.relative_to(typhoon_dir)):sha256_file(p) for p in typhoon_files}}
    write_json(root_output / "typhoon_model_identity.json", typhoon_identity)
    (root_output / "candidate_configs.execution-snapshot.json").write_bytes(config_path.read_bytes())
    inventory = json.loads((data_dir / "selection_manifest.json").read_text(encoding="utf-8"))
    write_json(root_output / "comparison_manifest.json", {
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "status":"running",
        "comparison_mode":"standalone_without_classifier",
        "host":{"device":"MacBook Air M2", "platform":platform.platform(),
                "python":platform.python_version(), "torch":torch.__version__,
                "execution":"one fresh subprocess per candidate"},
        "dataset":{"identity":inventory, "audio_manifest_sha256":sha256_file(manifest_path)},
        "candidate_configs_sha256":sha256_file(config_path), "typhoon_model_identity":typhoon_identity,
        "note":"This manifest is created before model workers start so interrupted runs retain their pinned configuration and dataset identity."})

    candidates = [candidate for candidate, _ in WHISPER_CANDIDATES] + [WAV2VEC_CANDIDATE, TYPHOON_CANDIDATE]
    statuses = []
    common = ["--standalone", "--data-dir", str(data_dir), "--audio-manifest", str(manifest_path),
              "--model-cache", str(model_cache), "--device", args.device, "--ffmpeg-version", args.ffmpeg_version]
    for candidate_id in candidates:
        worker_dir = root_output / "candidates" / candidate_id
        worker_dir.parent.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["TYPHOON_MODEL_DIR"] = str(typhoon_dir)
        command = [sys.executable, str(Path(__file__).resolve()), *common,
                   "--candidate-id", candidate_id, "--output-dir", str(worker_dir)]
        print(f"Starting fresh isolated process for {candidate_id}", flush=True)
        proc = subprocess.run(command, check=False, env=env)
        statuses.append({"candidate_id":candidate_id, "return_code":proc.returncode})
    combined = root_output / "transcription_results.jsonl"
    summaries = []
    with combined.open("w", encoding="utf-8") as target:
        for candidate_id in candidates:
            worker_dir = root_output / "candidates" / candidate_id
            result = worker_dir / "transcription_results.jsonl"
            if result.exists():
                target.write(result.read_text(encoding="utf-8"))
            summary = worker_dir / "candidate_runtime.json"
            if summary.exists():
                summaries.extend(json.loads(summary.read_text(encoding="utf-8")))
            else:
                summaries.append({"candidate_id":candidate_id, "load_status":"worker_failed_without_summary"})
    write_json(root_output / "candidate_runtime.json", summaries)
    write_json(root_output / "worker_statuses.json", statuses)
    ffmpeg_path = shutil.which("ffmpeg")
    ffmpeg_version = args.ffmpeg_version
    if ffmpeg_path and ffmpeg_version == "auto":
        result = subprocess.run([ffmpeg_path, "-version"], check=False, capture_output=True, text=True)
        ffmpeg_version = result.stdout.splitlines()[0] if result.stdout else "unavailable"
    from importlib.metadata import version
    packages = {}
    for name in ("openai-whisper", "pythaiasr", "transformers", "torch", "torchaudio", "soundfile", "onnxruntime", "psutil", "huggingface-hub"):
        try: packages[name] = version(name)
        except Exception: packages[name] = "not-installed"
    inventory = json.loads((data_dir / "selection_manifest.json").read_text(encoding="utf-8"))
    config_path = Path(__file__).with_name("candidate_configs.json")
    write_json(root_output / "comparison_manifest.json", {
        "run_id":f"stt-standalone-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "created_utc":datetime.now(timezone.utc).isoformat(), "comparison_mode":"standalone_without_classifier",
        "host":{"device":"MacBook Air M2", "platform":platform.platform(), "python":platform.python_version(),
                "torch":torch.__version__, "system_memory_bytes":__import__("psutil").virtual_memory().total,
                "execution":"one fresh subprocess per candidate", "ffmpeg_path":ffmpeg_path,
                "ffmpeg_version":ffmpeg_version, "package_versions":packages},
        "dataset":{"identity":inventory, "audio_manifest_sha256":sha256_file(manifest_path)},
        "candidate_configs_sha256":sha256_file(config_path), "typhoon_model_identity":typhoon_identity,
        "worker_statuses":statuses,
        "note":"No classifier loaded. Candidate process RSS/CPU and MPS allocation are standalone process measurements. No cross-clip transcript context retained; combined app resources are deferred to Application Integration."})
    print(f"Four-candidate comparison evidence saved under {root_output}", flush=True)

def main() -> None:
    default_root = Path.home() / "Library/Application Support/scam-call-alert/application-development/stt"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--standalone", action="store_true", help="Confirm this run excludes the classifier and combined-resource measurements.")
    parser.add_argument("--data-dir", type=Path, default=default_root / "fleurs-th-dev-70bb2e84/selected-7m30s")
    parser.add_argument("--audio-manifest", type=Path, default=ROOT / "04 - APPLICATION DEVELOPMENT/stt/audio_manifest.csv")
    parser.add_argument("--model-cache", type=Path, default=default_root / "whisper-cache")
    parser.add_argument("--output-dir", type=Path, required=True, help="New ignored persistent run directory")
    parser.add_argument("--device", default="mps")
    parser.add_argument("--candidate-id", choices=[*(item[0] for item in WHISPER_CANDIDATES), WAV2VEC_CANDIDATE, TYPHOON_CANDIDATE])
    parser.add_argument("--ffmpeg-version", default="auto")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
