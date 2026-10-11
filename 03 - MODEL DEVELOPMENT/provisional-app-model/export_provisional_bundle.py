#!/usr/bin/env python3
"""Export one verified WangchanBERTa CV epoch as an app-wiring-only bundle."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "03 - MODEL DEVELOPMENT/provisional-app-model"
TRAIN_DIR = ROOT / "03 - MODEL DEVELOPMENT/training"
INPUT_DIR = ROOT / "03 - MODEL DEVELOPMENT/input-preparation"
SELECTION_DIR = ROOT / "03 - MODEL DEVELOPMENT/selection"
EXPECTED = {
    "run_id": "wangchan-primary-max-lr5e-05-fold-0",
    "configuration_id": "wangchanberta__primary_only__lr-5e-05__pool-max",
    "model_key": "wangchanberta",
    "checkpoint": "airesearch/wangchanberta-base-att-spm-uncased",
    "checkpoint_revision": "b81d38df6b4755dbedec0bfea863c9956cbb963e",
    "data_condition": "primary_only",
    "training_representation": "whole_conversation",
    "training_marker_condition": "role_marked",
    "input_policy": "wangchan_full_context_v1",
    "max_content_tokens": "508",
    "overlap_tokens": "127",
    "pooling_method": "max",
    "fold": "0",
    "training_seed": "67",
    "learning_rate": "5e-05",
    "epochs_completed": "3",
}
EXPECTED_SNAPSHOT_SHA256 = "167652863c3b1c844ce8697ea97c77edd5f52cefc01b05a695992e64902c6600"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def manifest_run() -> dict[str, str]:
    path = SELECTION_DIR / "experiment_manifest.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        rows = [row for row in csv.DictReader(stream) if row.get("run_id") == EXPECTED["run_id"]]
    if len(rows) != 1:
        raise ValueError("Expected exactly one completed manifest row for the provisional run")
    row = rows[0]
    for key, expected in EXPECTED.items():
        if row.get(key) != expected:
            raise ValueError(f"Manifest mismatch for {key}: {row.get(key)!r} != {expected!r}")
    if row.get("execution_state") != "completed":
        raise ValueError("The provisional source run is not marked completed")
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    snapshot = args.snapshot.resolve()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite an existing provisional bundle: {output}")
    if not snapshot.is_file() or snapshot.is_symlink():
        raise FileNotFoundError("A regular verified epoch snapshot is required")
    row = manifest_run()
    snapshot_sha = sha256(snapshot)
    if snapshot_sha != EXPECTED_SNAPSHOT_SHA256:
        raise ValueError(f"Snapshot SHA-256 mismatch: {snapshot_sha}")

    sys.path.insert(0, str(TRAIN_DIR))
    sys.path.insert(0, str(INPUT_DIR))
    import torch
    from safetensors.torch import load_file
    from trainer import build_model
    import inputs

    input_config_path = INPUT_DIR / "preprocessing_config.json"
    input_config = inputs.load_config(input_config_path)
    model_config = input_config["models"]["wangchanberta"]
    if (model_config["checkpoint"] != EXPECTED["checkpoint"]
            or model_config["revision"] != EXPECTED["checkpoint_revision"]
            or input_config["label_to_id"] != {"Not Scam": 0, "Scam": 1}):
        raise ValueError("Pinned preprocessing config/checkpoint/label mapping differs")
    model = build_model("wangchanberta", EXPECTED["checkpoint"], EXPECTED["checkpoint_revision"],
                        local_files_only=False)
    state = load_file(str(snapshot), device="cpu")
    model.load_state_dict(state, strict=True)
    tokenizer = inputs.load_tokenizer("wangchanberta", input_config, local_files_only=False)
    model.eval()

    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        model_dir = stage / "model"
        runtime_dir = stage / "runtime"
        model_dir.mkdir()
        runtime_dir.mkdir()
        model.save_pretrained(model_dir, safe_serialization=True)
        tokenizer.save_pretrained(model_dir)
        shutil.copy2(input_config_path, runtime_dir / "preprocessing_config.json")
        shutil.copy2(INPUT_DIR / "inputs.py", runtime_dir / "inputs.py")
        shutil.copy2(TRAIN_DIR / "full_context.py", runtime_dir / "full_context.py")
        input_copy = runtime_dir / "inputs.py"
        full_context_copy = runtime_dir / "full_context.py"
        files = {
            str(path.relative_to(stage)): sha256(path)
            for path in sorted(stage.rglob("*")) if path.is_file()
        }
        expected_labels = {0: "Not Scam", 1: "Scam"}
        if model.config.id2label != expected_labels or model.config.num_labels != 2:
            raise ValueError(f"Unexpected exported class mapping: {model.config.id2label!r}")
        try:
            package_versions = {name: importlib.metadata.version(name)
                                for name in ("torch", "transformers", "tokenizers", "safetensors",
                                             "huggingface-hub", "sentencepiece", "protobuf")}
        except importlib.metadata.PackageNotFoundError as exc:
            raise RuntimeError(f"Missing runtime package: {exc}") from exc
        manifest = {
            "schema_version": 1,
            "bundle_id": "provisional-wangchan-max-lr5e-05-fold-0-epoch-3",
            "status": "provisional_app_wiring_only",
            "approved_scope": "application service wiring and functional smoke checks only",
            "prohibited_uses": ["candidate selection", "model parity acceptance", "context comparison",
                                "Plan 05 system evaluation", "final-test inference", "final reporting"],
            "source_run_id": EXPECTED["run_id"],
            "configuration_id": row["configuration_id"],
            "fold": 0,
            "epoch": 3,
            "source_epoch_snapshot_sha256": snapshot_sha,
            "checkpoint": {"id": EXPECTED["checkpoint"], "revision": EXPECTED["checkpoint_revision"]},
            "training": {"data_condition": "primary_only", "representation": "whole_conversation",
                         "marker_condition": "role_marked", "seed": 67, "learning_rate": 5e-5,
                         "effective_batch_size": 16, "epochs": 3, "pooling_method": "max",
                         "input_policy": "wangchan_full_context_v1"},
            "inference": {"representation": "whole_conversation", "marker_condition": "role_free",
                          "preprocessing": "shared Plan 02 checkpoint_prepare_text",
                          "window_content_tokens": 508, "window_step_tokens": 381,
                          "overlap_tokens": 127, "max_total_tokens": 510,
                          "window_pooling": "class-wise max of raw two-class logits, then softmax",
                          "label_to_id": {"Not Scam": 0, "Scam": 1}, "threshold": 0.5},
            "cv_context_not_selection": {"fold_role_free_scam_f1_epoch_3": 0.9484978540772532,
                                          "config_mean_scam_f1_epoch_3": 0.962344,
                                          "config_sample_sd_scam_f1_epoch_3": 0.013827},
            "runtime_versions": package_versions,
            "runtime_source_hashes": {"inputs.py": sha256(input_copy),
                                      "full_context.py": sha256(full_context_copy),
                                      "preprocessing_config.json": sha256(runtime_dir / "preprocessing_config.json")},
            "files": files,
        }
        (stage / "provisional_bundle_manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")

        # Reload the serialized HF bundle and compare every tensor to the verified source snapshot.
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        reloaded = AutoModelForSequenceClassification.from_pretrained(
            model_dir, local_files_only=True, use_safetensors=True, trust_remote_code=False)
        saved_state = reloaded.state_dict()
        if set(saved_state) != set(state) or any(not torch.equal(saved_state[k].cpu(), state[k].cpu()) for k in state):
            raise RuntimeError("Serialized bundle does not exactly reproduce the verified epoch state")
        reloaded_tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True, use_fast=True)
        if type(reloaded_tokenizer).__name__ != type(tokenizer).__name__:
            raise RuntimeError("Serialized tokenizer class changed")
        del reloaded, saved_state, state, model
        os.replace(stage, output)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    print(json.dumps({"status": "exported_provisional_only", "bundle": str(output),
                      "manifest": str(output / "provisional_bundle_manifest.json"),
                      "source_snapshot_sha256": snapshot_sha,
                      "model_weights_sha256": files.get("model/model.safetensors"),
                      "file_count": len(files)}, indent=2))


if __name__ == "__main__":
    main()
