#!/usr/bin/env python3
"""Newline-delimited JSON inference for the temporary app-wiring model."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_bundle(bundle: Path, device: str):
    bundle = bundle.resolve()
    manifest_path = bundle / "provisional_bundle_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "provisional_app_wiring_only":
        raise ValueError("This loader accepts only the explicitly provisional app-wiring bundle")
    if manifest.get("inference", {}).get("window_pooling") != "class-wise max of raw two-class logits, then softmax":
        raise ValueError("Unexpected provisional inference policy")
    for relative, expected in manifest.get("files", {}).items():
        path = (bundle / relative).resolve()
        if bundle not in path.parents or path.is_symlink() or not path.is_file() or sha256(path) != expected:
            raise ValueError(f"Bundle file is missing or changed: {relative}")
    runtime = bundle / "runtime"
    sys.path.insert(0, str(runtime))
    import inputs
    import full_context
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    config = inputs.load_config(runtime / "preprocessing_config.json")
    tokenizer = AutoTokenizer.from_pretrained(bundle / "model", local_files_only=True,
                                               use_fast=True, trust_remote_code=False)
    model = AutoModelForSequenceClassification.from_pretrained(
        bundle / "model", local_files_only=True, use_safetensors=True, trust_remote_code=False)
    if model.config.id2label != {0: "Not Scam", 1: "Scam"}:
        raise ValueError("Bundle class order is not the approved Not Scam=0, Scam=1 order")
    model.to(device)
    model.eval()
    identity = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    return manifest, identity, config, tokenizer, model, full_context, inputs, torch


class ProvisionalClassifier:
    def __init__(self, bundle: Path, device: str):
        (self.manifest, self.model_version, self.config, self.tokenizer,
         self.model, self.full_context, self.inputs, self.torch) = load_bundle(bundle, device)
        self.device = device

    def predict(self, request: dict):
        request_id = request.get("request_id") if isinstance(request, dict) else None
        def error(code, message):
            return {"request_id": request_id, "model_version": self.model_version,
                    "status": "error", "label": None, "probabilities": None,
                    "threshold": 0.5, "warnings": ["PROVISIONAL_APP_WIRING_ONLY"],
                    "error": {"code": code, "message": message}}
        if not isinstance(request, dict) or set(request) != {"request_id", "transcript"}:
            return error("E_INVALID_REQUEST", "Expected exactly request_id and transcript.")
        if not isinstance(request_id, str) or not request_id.strip():
            return error("E_INVALID_REQUEST", "request_id must be a nonempty string.")
        transcript = request["transcript"]
        if not isinstance(transcript, str) or not transcript.strip():
            return error("E_TRANSCRIPT_INVALID", "transcript must be nonempty text.")
        try:
            prepared = self.inputs.checkpoint_prepare_text(transcript, "wangchanberta", self.config)
            content_ids = self.tokenizer(prepared, add_special_tokens=False, padding=False,
                                         truncation=False, verbose=False)["input_ids"]
            windows = [self.full_context.add_special_tokens(self.tokenizer, ids)
                       for ids in self.full_context.make_windows(content_ids)]
            logits = []
            with self.torch.inference_mode():
                for start in range(0, len(windows), 8):
                    batch = self.tokenizer.pad(windows[start:start + 8], padding=True, return_tensors="pt")
                    batch = {key: value.to(self.device) for key, value in batch.items()}
                    result = self.model(**batch).logits.float()
                    if result.ndim != 2 or result.shape[1] != 2:
                        raise ValueError("Expected two logits per window")
                    logits.append(result.cpu())
            window_logits = self.torch.cat(logits, dim=0)
            conversation_logits = window_logits.max(dim=0).values.unsqueeze(0)
            scores = self.torch.softmax(conversation_logits, dim=-1)[0].tolist()
            if len(scores) != 2 or not all(math.isfinite(float(x)) for x in scores):
                raise ValueError("Model returned invalid class scores")
            if abs(sum(scores) - 1.0) > 1e-6:
                raise ValueError("Model class scores do not sum to one")
        except Exception:
            return error("E_INFERENCE_FAILED", "Provisional model preprocessing or inference failed.")
        probabilities = {"Not Scam": float(scores[0]), "Scam": float(scores[1])}
        return {"request_id": request_id, "model_version": self.model_version,
                "status": "success",
                "label": "Scam" if probabilities["Scam"] >= 0.5 else "Not Scam",
                "probabilities": probabilities, "threshold": 0.5,
                "warnings": ["PROVISIONAL_APP_WIRING_ONLY", "FULL_CONTEXT_OVERLAPPING_WINDOWS"],
                "error": None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--device", default="cpu", choices=("cpu", "mps", "cuda"))
    args = parser.parse_args()
    classifier = ProvisionalClassifier(args.bundle, args.device)
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = classifier.predict(request)
        except Exception:
            response = {"request_id": None, "model_version": classifier.model_version,
                        "status": "error", "label": None, "probabilities": None,
                        "threshold": 0.5, "warnings": ["PROVISIONAL_APP_WIRING_ONLY"],
                        "error": {"code": "E_INVALID_REQUEST", "message": "Input line is not valid JSON."}}
        print(json.dumps(response, ensure_ascii=False, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
