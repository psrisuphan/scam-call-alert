"""Pinned real adapters; no reference text, labels, or fallback predictions."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[3]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class Wav2VecAdapter:
    def __init__(self, cache):
        config = json.loads((ROOT / "04 - APPLICATION DEVELOPMENT/stt/stt_config.json").read_text())
        candidate = config["selected_candidate"]
        snapshot = Path(cache) / "models--airesearch--wav2vec2-large-xlsr-53-th/snapshots" / candidate["checkpoint_revision"]
        if file_hash(snapshot / "pytorch_model.bin") != candidate["checkpoint_weight_sha256"]:
            raise ValueError("STT weight checksum differs from the approved candidate")
        runner = load_module("stt_runtime_adapter", ROOT / "04 - APPLICATION DEVELOPMENT/stt/run_stt_comparison.py")
        self.asr = runner.load_wav2vec2_pythaiasr(candidate["inference"]["device"], snapshot)
        self.version = candidate["checkpoint_revision"]
        self.lock = threading.Lock()

    def recognize(self, pcm):
        import numpy as np
        import torch
        import psutil
        audio = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768
        before = time.perf_counter()
        lock_wait_started = time.perf_counter()
        self.lock.acquire()
        lock_wait_seconds = time.perf_counter() - lock_wait_started
        try:
          with torch.inference_mode():
            # Exact PyThaiASR default greedy path; additionally retain CTC frames
            # for acoustic overlap ownership. No language model or text rewrite.
            preprocess_started = time.perf_counter()
            dataset = self.asr.prepare_dataset({"speech": audio, "sampling_rate": 16000})
            values = self.asr.processor(dataset["input_values"][0], return_tensors="pt", padding=True).to(self.asr.device)
            preprocessing_seconds = time.perf_counter() - preprocess_started
            forward_started = time.perf_counter()
            logits = self.asr.model(values.input_values).logits
            forward_dispatch_seconds = time.perf_counter() - forward_started
            sync_started = time.perf_counter()
            ids = torch.argmax(logits, dim=-1)[0].cpu().tolist()
            forward_sync_copy_seconds = time.perf_counter() - sync_started
            decode_started = time.perf_counter()
            text = self.asr.processor.decode(ids)
            decode_seconds = time.perf_counter() - decode_started
            ratio = self.asr.model.config.inputs_to_logits_ratio / 16000
        finally:
            self.lock.release()
        return {"text": text, "frames": ids,
                "times": [(i + 0.5) * ratio for i in range(len(ids))],
                "resources": {"processing_seconds": time.perf_counter() - before,
                              "lock_wait_seconds": lock_wait_seconds,
                              "preprocessing_seconds": preprocessing_seconds,
                              "forward_dispatch_seconds": forward_dispatch_seconds,
                              "forward_sync_copy_seconds": forward_sync_copy_seconds,
                              "decode_seconds": decode_seconds,
                              "process_rss_bytes": psutil.Process().memory_info().rss,
                              "mps_driver_allocated_bytes": torch.mps.driver_allocated_memory(),
                              "mps_current_allocated_bytes": torch.mps.current_allocated_memory()}}

    def decode(self, frames):
        if not frames:
            return "", []
        value = self.asr.processor.decode(frames, output_char_offsets=True)
        return value["text"], value["char_offsets"]


class InterimClassifier:
    """Owner-approved interim app fixture: the final-trained, not yet test-evaluated model.

    Loads through the same identity-checked pipeline and role-free reference
    path used by the passed Mac compatibility check. Outputs are app-development
    evidence only until Plans 03/02 and 03/03 complete.
    """
    WARNINGS = ["INTERIM_UNEVALUATED_FINAL_MODEL"]

    def __init__(self, model_dir, device):
        self.evaluation = load_module("interim_final_evaluation", ROOT / "03 - MODEL DEVELOPMENT/final-evaluation/evaluation.py")
        self.pipeline, artifact = self.evaluation.load_pipeline(
            Path(model_dir), ROOT / "03 - MODEL DEVELOPMENT/selection/selected_config.json",
            ROOT / "03 - MODEL DEVELOPMENT/input-preparation/preprocessing_config.json", device=device,
            completion_record_path=ROOT / "03 - MODEL DEVELOPMENT/selection/selection_completion.json")
        self.tokenizer, self.inputs = self.pipeline.tokenizer, self.pipeline.inputs
        self.config, self.model_key = self.pipeline.input_config, self.pipeline.model_key
        self.run_id = artifact["run_id"]
        self.model_version = self.pipeline.model_weights_sha256

    def predict(self, request):
        request_id = request.get("request_id") if isinstance(request, dict) else None
        def error(code, message):
            return {"request_id": request_id, "model_version": self.model_version, "status": "error",
                    "label": None, "probabilities": None, "threshold": self.pipeline.threshold,
                    "warnings": self.WARNINGS, "error": {"code": code, "message": message}}
        if not isinstance(request, dict) or set(request) != {"request_id", "transcript"}:
            return error("E_INVALID_REQUEST", "Expected exactly request_id and transcript.")
        if not isinstance(request_id, str) or not request_id.strip():
            return error("E_INVALID_REQUEST", "request_id must be a nonempty string.")
        transcript = request["transcript"]
        if not isinstance(transcript, str) or not transcript.strip():
            return error("E_TRANSCRIPT_INVALID", "transcript must be nonempty text.")
        try:
            trace = self.evaluation.predict_with_trace(transcript, self.pipeline)
        except Exception:
            return error("E_INFERENCE_FAILED", "Interim model preprocessing or inference failed.")
        probabilities = {"Not Scam": trace["p_not_scam"], "Scam": trace["p_scam"]}
        return {"request_id": request_id, "model_version": self.model_version, "status": "success",
                "label": trace["predicted_label"], "probabilities": probabilities,
                "threshold": trace["threshold"], "warnings": self.WARNINGS, "error": None}


class ClassifierAdapter:
    def __init__(self, bundle, kind, device):
        self.kind = kind
        self.lock = threading.Lock()
        self.device = device
        self.last_cache_cleanup = {}
        if kind == "interim":
            self.model = InterimClassifier(bundle, device)
            self.tokenizer, self.inputs = self.model.tokenizer, self.model.inputs
            self.config, self.model_key = self.model.config, self.model.model_key
        elif kind == "official":
            component = load_module("official_classifier", ROOT / "03 - MODEL DEVELOPMENT/handoff/inference.py")
            self.model = component.load_local_bundle(bundle, device=device)
            self.tokenizer, self.inputs = self.model.tokenizer, component._shared_inputs_module()
            self.config, self.model_key = self.model.config, self.model.model_key
        else:
            raise ValueError("Explicit interim or official adapter required")
        self.version = self.model.model_version

    def predict(self, request):
        with self.lock:
            try:
                prediction = self.model.predict(request)
            except Exception:
                # Preserve the model failure if cache cleanup also fails.
                try:
                    self._release_mps_cache()
                except Exception:
                    pass
                raise
            self._release_mps_cache()
            return prediction

    def _release_mps_cache(self):
        if not str(self.device).startswith('mps'):
            self.last_cache_cleanup = {'cache_cleanup': 'not_applicable'}
            return
        import torch
        before_driver = torch.mps.driver_allocated_memory()
        before_current = torch.mps.current_allocated_memory()
        sync_started = time.perf_counter()
        torch.mps.synchronize()
        sync_seconds = time.perf_counter() - sync_started
        cleanup_started = time.perf_counter()
        torch.mps.empty_cache()
        cleanup_seconds = time.perf_counter() - cleanup_started
        self.last_cache_cleanup = {
            'mps_driver_allocated_bytes': before_driver,
            'mps_current_allocated_bytes': before_current,
            'synchronize_seconds': sync_seconds,
            'empty_cache_seconds': cleanup_seconds,
            'mps_driver_allocated_bytes_after_cleanup': torch.mps.driver_allocated_memory(),
            'mps_current_allocated_bytes_after_cleanup': torch.mps.current_allocated_memory(),
        }

    def assemble(self, text):
        budget = self.config["models"][self.model_key]["verified_config_limit"]
        def count(value):
            prepared = self.inputs.checkpoint_prepare_text(value, self.model_key, self.config)
            return len(self.tokenizer(prepared, add_special_tokens=True, truncation=False, verbose=False)["input_ids"])
        if count(text) <= budget:
            return text, {"omitted_prefix_characters": 0, "token_budget": budget}
        # Keep actual source text, never decode special/checkpoint marker tokens
        # back into dialogue. Search real Unicode suffix boundaries then verify.
        low, high = 0, len(text)
        while low < high:
            mid = (low + high) // 2
            if count(text[mid:]) <= budget:
                high = mid
            else:
                low = mid + 1
        while low < len(text) and count(text[low:]) > budget:
            low += 1
        return text[low:], {"omitted_prefix_characters": low, "token_budget": budget}
