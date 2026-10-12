"""Development-only final classifier + pinned STT execution check on Mac M2.

Does not load dataset partitions, score STT, authorize tests, or change models.
"""
from __future__ import annotations
import argparse
import csv
import importlib.metadata
import importlib.util
import json
import math
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STT_DIR = ROOT / "04 - APPLICATION DEVELOPMENT/stt"
CHECKPOINT = "airesearch/wav2vec2-large-xlsr-53-th"
REVISION = "3155938c549b23eee16b1d4b55dcb161b7fe4bcf"


def validate_host(system, machine, hardware):
    if system != "Darwin" or machine != "arm64":
        raise ValueError("Run on the coworker's Apple Silicon Mac, not Linux or an emulated host.")
    if hardware.get("machine_name") != "MacBook Air" or hardware.get("chip_type") != "Apple M2":
        raise ValueError("Expected MacBook Air with Apple M2; preserve findings and ask before changing host.")


def validate_stt(config, package_version):
    candidate = config["selected_candidate"]
    if (candidate["checkpoint"] != CHECKPOINT or candidate["checkpoint_revision"] != REVISION
            or candidate["package_version"] != package_version or package_version != "2.3.0"
            or candidate["inference"]["device"] != "mps"
            or candidate["inference"]["language_model"] is not False):
        raise ValueError("STT implementation/revision/settings differ from the pinned selected configuration.")
    return candidate


def select_audio(manifest, filename, data_dir):
    with Path(manifest).open(newline="", encoding="utf-8") as stream:
        matches = [r for r in csv.DictReader(stream) if r["audio_filename"] == filename]
    if len(matches) != 1:
        raise ValueError("Choose exactly one clip from the frozen FLEURS development manifest.")
    row = matches[0]
    base = Path(data_dir).resolve()
    audio = (base / row["audio_path"]).resolve()
    if base not in audio.parents or audio.name != filename:
        raise ValueError("Development audio path is outside the supplied audio directory.")
    return audio, row


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--selected-config", required=True, type=Path)
    parser.add_argument("--completion-record", required=True, type=Path)
    parser.add_argument("--input-config", required=True, type=Path)
    parser.add_argument("--stt-snapshot", required=True, type=Path)
    parser.add_argument("--data-dir", required=True, type=Path, help="Existing frozen FLEURS development subset.")
    parser.add_argument("--audio-filename", required=True)
    parser.add_argument("--classifier-device", required=True, choices=("cpu", "mps"))
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    output = args.output_dir.resolve()
    if output == ROOT or ROOT in output.parents:
        parser.error("Store execution evidence outside the project checkout.")
    output.mkdir(parents=True, exist_ok=False)
    record = {"schema_version": 1, "status": "failed", "host": "MacBook Air M2",
        "audio_partition": "development", "stt_checkpoint": CHECKPOINT,
        "stt_checkpoint_revision": REVISION, "classifier_backend": args.classifier_device,
        "stt_backend": "mps", "execution_evidence": [], "failures": [],
        "test_access": False, "limitations": [
            "One development audio clip is execution evidence, not STT ranking or end-to-end accuracy.",
            "No numerical parity tolerance or deployment configuration is approved by this check.",
        ]}
    sampler = None
    started = time.perf_counter()
    try:
        hardware = json.loads(subprocess.check_output(
            ["system_profiler", "SPHardwareDataType", "-json"], text=True))["SPHardwareDataType"][0]
        validate_host(platform.system(), platform.machine(), hardware)
        record["environment"] = {"system": platform.platform(), "python": sys.version,
            "hardware": {k: hardware.get(k) for k in ("machine_name", "chip_type", "physical_memory")},
            "packages": {name: importlib.metadata.version(name) for name in ("torch", "transformers", "pythaiasr")}}
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import evaluation
        stt_config = evaluation.read_json(STT_DIR / "stt_config.json")
        candidate = validate_stt(stt_config, importlib.metadata.version("pythaiasr"))
        record["stt_config_sha256"] = evaluation.sha256(STT_DIR / "stt_config.json")
        record["selected_config_sha256"] = evaluation.sha256(args.selected_config)
        snapshot = args.stt_snapshot.resolve()
        if snapshot.name != REVISION:
            raise ValueError("STT snapshot directory must identify the exact pinned revision.")
        if evaluation.sha256(snapshot / "pytorch_model.bin") != candidate["checkpoint_weight_sha256"]:
            raise ValueError("STT snapshot weights differ from the selected STT checksum.")
        audio, row = select_audio(STT_DIR / "audio_manifest.csv", args.audio_filename, args.data_dir)
        if evaluation.sha256(audio) != row["audio_sha256"]:
            raise ValueError("Development audio checksum differs from the frozen manifest.")
        record["audio"] = {"filename": audio.name, "sha256": row["audio_sha256"],
            "manifest_sha256": evaluation.sha256(STT_DIR / "audio_manifest.csv")}
        import torch
        import numpy as np
        import soundfile as sf
        if not torch.backends.mps.is_available():
            raise ValueError("Selected STT requires working MPS; no silent CPU fallback.")
        audio_array, rate = sf.read(audio, dtype="float32")
        if rate != 16000 or audio_array.ndim != 1 or not len(audio_array) or not np.isfinite(audio_array).all():
            raise ValueError("Development audio must already be finite 16 kHz mono float32; no silent conversion.")
        record["audio"]["duration_seconds"] = len(audio_array) / rate
        spec = importlib.util.spec_from_file_location("selected_stt_execution", STT_DIR / "run_stt_comparison.py")
        stt = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stt)
        sampler = stt.ResourceSampler(output / "resource_samples.csv", torch, True)
        sampler.start()
        sampler.snapshot("before_classifier_load")
        load_start = time.perf_counter()
        pipeline, artifact = evaluation.load_pipeline(args.model_dir, args.selected_config, args.input_config,
            device=args.classifier_device, completion_record_path=args.completion_record)
        stt.sync_device(torch, args.classifier_device)
        record["classifier_load_seconds"] = time.perf_counter() - load_start
        record["model_safetensors_sha256"] = pipeline.model_weights_sha256
        record["final_run_id"] = artifact["run_id"]
        sampler.snapshot("classifier_loaded")
        load_start = time.perf_counter()
        recognizer = stt.load_wav2vec2_pythaiasr("mps", snapshot)
        stt.sync_device(torch, "mps")
        record["stt_load_seconds"] = time.perf_counter() - load_start
        sampler.snapshot("both_models_loaded")
        start = time.perf_counter()
        transcript, _, usable = stt.transcribe(stt.WAV2VEC_CANDIDATE, recognizer, audio_array)
        stt.sync_device(torch, "mps")
        if not usable or not isinstance(transcript, str) or not transcript.strip():
            raise ValueError("STT did not produce a usable development transcript.")
        record["stt_seconds"] = time.perf_counter() - start
        sampler.snapshot("stt_executed_classifier_still_loaded")
        start = time.perf_counter()
        prediction = evaluation.predict_with_trace(transcript, pipeline)
        stt.sync_device(torch, args.classifier_device)
        if (prediction["predicted_label"] not in ("Scam", "Not Scam")
                or not all(math.isfinite(prediction[k]) and 0 <= prediction[k] <= 1 for k in ("p_not_scam", "p_scam"))
                or abs(prediction["p_not_scam"] + prediction["p_scam"] - 1) > 1e-5):
            raise ValueError("Classifier output is invalid.")
        record["classifier_seconds"] = time.perf_counter() - start
        sampler.snapshot("classifier_executed_stt_still_loaded")
        trace_path = output / "development_execution.json"
        trace_path.write_text(json.dumps({"transcript": transcript, "classifier_trace": prediction},
            ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        record["execution_evidence"] = [{"path": str(trace_path), "sha256": evaluation.sha256(trace_path),
            "condition": "both models resident; STT then classifier on development audio"}]
        record["status"] = "passed"
    except Exception as exc:
        record["failures"].append({"type": type(exc).__name__, "message": str(exc)})
    finally:
        if sampler is not None:
            record["resources"] = sampler.stop()
        record["elapsed_seconds"] = time.perf_counter() - started
        (output / "mac_compatibility.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": record["status"], "evidence": str(output / "mac_compatibility.json"),
        "failures": record["failures"]}, ensure_ascii=False))
    return 0 if record["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
