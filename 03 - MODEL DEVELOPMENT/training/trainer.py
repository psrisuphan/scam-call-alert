"""Reusable fine-tuning runner for the Scam Call Alert project.

Importing this module does not import torch/transformers and cannot load the
held-out test partition. Run configurations must resolve every numeric and
runtime setting explicitly; see README.md before preparing an approved file.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import random
import resource
import shutil
import socket
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRAINING_DIR = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "03 - MODEL DEVELOPMENT/input-preparation"
CONFIG_TEMPLATE = TRAINING_DIR / "run_config.template.json"
CP01_RECORDED_TRAINER_SHA256 = "22578e136d33ebae07374152c8bcbaaa75e51790184f1788b2b9f2dc3aa3b726"
CP01_RESTORE_RUN_ID = "diagnostic-wangchanberta-owner-approved-retry-20261009T104528Z-1791542728829738267"
CP01_RESTORE_MODEL_ID = "airesearch/wangchanberta-base-att-spm-uncased"
CP01_RESTORE_MODEL_REVISION = "b81d38df6b4755dbedec0bfea863c9956cbb963e"
CP01_RESTORE_PREVIOUS_SHA256 = "e6c0c958664a95aa5472d07f9471ce25d0c1333cca6281b7b7ccdf73d08a0e5b"
CP01_RESTORE_APPROVAL_REFERENCE = (
    "Owner approval (2026-10-08): learning rate 3e-5, effective batch 16, "
    "training seed 67, approved AdamW settings, warmup 0, and two optimizer "
    "updates using training records; execution-feasibility only, no comparative selection.")
SUPPORTED_MODELS = ("wangchanberta", "phayathaibert", "hplt", "xlmr")
LABEL_NAMES = {0: "Not Scam", 1: "Scam"}
HISTORY_FIELDS = ["run_id", "model", "data_condition", "training_representation",
    "training_marker_condition", "validation_representation", "validation_marker_condition",
    "configuration_id", "fold", "seed", "epoch", "evaluation_point", "optimizer_updates",
    "conversations_processed", "validation_conversations", "training_loss", "validation_loss", "scam_precision",
    "scam_recall", "scam_f1", "macro_f1", "accuracy", "elapsed_seconds",
    "attempt_epoch_loop_seconds", "learning_rate", "checkpoint_reference", "checkpoint_sha256",
    "resource_snapshot_json", "status"]
PREDICTION_FIELDS = ["run_id", "model", "data_condition", "training_representation",
    "training_marker_condition", "validation_representation", "validation_marker_condition",
    "configuration_id", "fold", "seed", "epoch", "evaluation_point", "sample_id", "source_dataset",
    "true_label", "prob_not_scam", "prob_scam", "execution_state", "failure_reason", "elapsed_seconds",
    "chunk_count", "content_token_count", "inference_seconds", "pooling_method"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_completed_run_artifact_hashes(run_dir: Path) -> dict[str, str]:
    """Verify a completed summary binds its persisted config and raw CSV evidence."""
    run_dir = Path(run_dir).resolve()
    summary_path = run_dir / "run_summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(f"Completed run summary is missing: {summary_path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    expected_names = ("run_config.json", "training_history.csv", "validation_predictions.csv")
    hashes = summary.get("artifact_sha256")
    if summary.get("status") != "completed" or not isinstance(hashes, dict):
        raise ValueError("Run summary is not completed or does not bind artifact checksums")
    for name in expected_names:
        path = run_dir / name
        if not path.is_file() or not hashes.get(name) or sha256_file(path) != hashes[name]:
            raise ValueError(f"Completed run artifact checksum mismatch: {name}")
    return hashes


def canonical_hash(value) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def approved_settings_payload(config):
    keys = ("mode", "model", "checkpoint", "data", "fold", "training", "validation",
            "optimizer", "schedule", "precision", "selection", "evaluation")
    return {key: config[key] for key in keys if key in config}


def approved_settings_digest(config) -> str:
    """Digest the exact approved behavior/settings recorded in a run config."""
    return canonical_hash(approved_settings_payload(config))


def configuration_id(config) -> str:
    payload = json.loads(json.dumps(approved_settings_payload(config)))
    payload.pop("mode", None)
    payload.pop("fold", None)
    payload.get("training", {}).pop("epochs", None)
    return canonical_hash(payload)


def recovery_identity(run_config) -> str:
    payload = json.loads(json.dumps(run_config))
    payload.pop("configuration_id", None)
    payload.pop("epoch_extensions", None)
    payload.get("training", {}).pop("epochs", None)
    payload.get("approval", {}).pop("approved_settings_sha256", None)
    return canonical_hash(payload)


def _require(mapping, path, expected_type=None):
    current = mapping
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"Missing required configuration field: {path}")
        current = current[part]
    type_ok = (type(current) in expected_type) if isinstance(expected_type, tuple) else (type(current) is expected_type)
    if current is None or (expected_type and not type_ok):
        raise ValueError(f"Configuration field {path} must be explicitly set")
    return current


def validate_config(config: dict, *, require_diagnostic_approval=True) -> dict:
    """Validate fully resolved values; no experiment defaults are supplied."""
    if not isinstance(config, dict):
        raise ValueError("Run configuration must be a JSON object")
    if config.get("schema_version") != 1:
        raise ValueError("Unsupported run configuration schema_version")
    run_id = _require(config, "run_id", str)
    if not run_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in run_id):
        raise ValueError("run_id must be a nonempty filesystem-safe identifier")
    mode = _require(config, "mode", str)
    if mode not in ("diagnostic", "comparative", "final_training"):
        raise ValueError("mode must be diagnostic, comparative, or final_training")
    approval = config.get("approval")
    if not isinstance(approval, dict) or approval.get("status") != "owner_approved" or not approval.get("reference"):
        raise ValueError("A recorded owner approval reference is required before execution")
    if require_diagnostic_approval and mode == "diagnostic" and not approval.get("diagnostic_numeric_settings"):
        raise ValueError("Diagnostic numeric settings require explicit owner approval")
    approved_digest = approval.get("approved_settings_sha256")
    if not approved_digest or approved_digest != approved_settings_digest(config):
        raise ValueError("approved_settings_sha256 is absent or does not match the resolved run settings")
    model = _require(config, "model", str)
    if model not in SUPPORTED_MODELS:
        raise ValueError("Unknown candidate model")
    if mode != "final_training":
        fold = _require(config, "fold", int)
        if fold not in range(5):
            raise ValueError("fold must be one of the saved folds 0-4")
    elif config.get("fold") is not None:
        raise ValueError("final_training uses the full training pool, not a CV fold")
    if config.get("partition") == "test" or config.get("data", {}).get("partition") == "test":
        raise ValueError("The training component cannot be configured with a test partition")
    if _require(config, "data.condition", str) not in ("primary_only", "primary_plus_supplemental"):
        raise ValueError("Unsupported training data condition")
    if _require(config, "training.representation", str) != "whole_conversation":
        raise ValueError("Caller-only fits are inactive under the 2026-10-10 owner-approved scope")
    if _require(config, "training.marker_condition", str) != "role_marked":
        raise ValueError("Training must use the approved role_marked inputs")
    window_policy = config.get("training", {}).get("window_policy")
    pooling_method = config.get("training", {}).get("pooling_method")
    if window_policy is not None:
        if (window_policy != "wangchan_full_context_v1" or model != "wangchanberta"
                or config["training"]["representation"] != "whole_conversation"
                or pooling_method not in ("max", "mean")):
            raise ValueError("Full-context windowing is approved only for WangchanBERTa whole-conversation max/mean runs")
        _require(config, "training.gradient_checkpointing", bool)
    elif pooling_method is not None:
        raise ValueError("Pooling requires the approved WangchanBERTa full-context window policy")
    elif config.get("training", {}).get("gradient_checkpointing") is True:
        raise ValueError("Gradient checkpointing is currently configurable only for the WangchanBERTa full-context path")
    if mode != "final_training":
        if _require(config, "validation.representation", str) not in ("whole_conversation", "caller_only"):
            raise ValueError("Unsupported validation representation")
        if config["validation"]["representation"] != config["training"]["representation"]:
            raise ValueError("Validation representation must match the corresponding training representation")
        if _require(config, "validation.marker_conditions", list) != ["role_marked", "role_free"]:
            raise ValueError("Validation must evaluate paired role_marked and role_free conditions")
    else:
        if config.get("validation") not in (None, {"enabled": False}):
            raise ValueError("Final training must disable validation-based selection")
    for field, typ in (("training.seed", int),
                       ("training.effective_batch_size", int), ("training.microbatch_size", int),
                       ("training.accumulation_steps", int),
                       ("optimizer.learning_rate", (int, float)), ("optimizer.weight_decay", (int, float)),
                       ("optimizer.beta1", (int, float)), ("optimizer.beta2", (int, float)),
                       ("optimizer.epsilon", (int, float)), ("optimizer.gradient_clip_norm", (int, float)),
                       ("schedule.warmup_updates", int)):
        val = _require(config, field)
        if isinstance(typ, tuple):
            if type(val) not in typ:
                raise ValueError(f"{field} must be explicitly numeric")
        elif type(val) is not typ:
            raise ValueError(f"{field} has the wrong type")
        if isinstance(val, (int, float)) and not isinstance(val, bool) and val <= 0 and field not in ("optimizer.weight_decay", "schedule.warmup_updates"):
            raise ValueError(f"{field} must be positive")
    if config["training"]["microbatch_size"] * config["training"]["accumulation_steps"] != config["training"]["effective_batch_size"]:
        raise ValueError("microbatch_size × accumulation_steps must preserve effective_batch_size")
    if mode == "diagnostic":
        limit = _require(config, "training.optimizer_updates_limit", int)
        if limit != 2 or not config["approval"].get("diagnostic_numeric_settings"):
            raise ValueError("Diagnostic update limit and owner-approved numeric settings are required")
        if config["optimizer"]["learning_rate"] != 3e-5:
            raise ValueError("The approved diagnostic learning rate is 3e-5")
        _require(config, "diagnostic_sample_selection.strategy", str)
        if config["diagnostic_sample_selection"]["strategy"] != "longest_by_prepared_tokens":
            raise ValueError("Diagnostic selection must use approved training-only long inputs")
        if config["training"]["seed"] != 67 or config["training"]["effective_batch_size"] != 16:
            raise ValueError("Approved diagnostics use the explicitly confirmed seed and effective batch")
        if config["schedule"]["warmup_updates"] != 0:
            raise ValueError("This approved diagnostic uses zero warmup; this does not resolve comparison warmup")
    else:
        _require(config, "training.epochs", int)
        if config["training"]["epochs"] <= 0:
            raise ValueError("training.epochs must be positive")
    precision = _require(config, "precision.mode", str)
    if precision not in ("auto", "bf16", "fp16", "fp32"):
        raise ValueError("precision.mode must explicitly select auto/bf16/fp16/fp32")
    if precision == "auto" and not config["precision"].get("auto_policy_approved"):
        raise ValueError("The BF16→FP16→FP32 auto policy needs explicit approval in this config")
    if _require(config, "evaluation.scam_threshold", (int, float)) != 0.5:
        raise ValueError("The approved Scam threshold is fixed at 0.5")
    if config["optimizer"].get("name") != "AdamW":
        raise ValueError("The approved optimizer is AdamW")
    if mode in ("comparative", "final_training"):
        fixed = {"weight_decay": 0.01, "beta1": 0.9, "beta2": 0.999,
                 "epsilon": 1e-8, "gradient_clip_norm": 1.0}
        if any(config["optimizer"].get(key) != value for key, value in fixed.items()):
            raise ValueError("Comparative/final optimizer settings differ from the approved tuning plan")
        if config["schedule"].get("name") != "linear_warmup_then_constant":
            raise ValueError("The approved schedule is linear warmup then constant")
    _require(config, "paths.data", str)
    _require(config, "paths.input_config", str)
    _require(config, "paths.input_exports", str)
    _require(config, "paths.persistent_runs", str)
    if not _require(config, "checkpoint.revision", str):
        raise ValueError("Pinned checkpoint revision is required")
    if model == "hplt":
        code_revision = _require(config, "checkpoint.custom_code_revision", str)
        if code_revision != config["checkpoint"]["revision"]:
            raise ValueError("HPLT model and custom-code revisions must match the pinned checkpoint revision")
    if mode == "comparative":
        if config["approval"].get("selection_protocol_approved") is not True or not config["approval"].get("selection_protocol_reference"):
            raise ValueError("Comparative runs require the approved Plan 03/01 protocol reference")
        maximum = _require(config, "selection.max_epochs", int)
        if maximum < 3 or config["training"]["epochs"] < 3 or config["training"]["epochs"] > maximum:
            raise ValueError("Comparative epoch target must be within the owner-approved finite maximum")
        rate = config["optimizer"]["learning_rate"]
        if rate not in (2e-5, 3e-5, 5e-5):
            raise ValueError("Comparative learning rate must be one of the approved grid values")
        if config["training"]["seed"] != 67 or config["training"]["effective_batch_size"] != 16:
            raise ValueError("Comparative runs must follow the approved seed and effective batch size")
        if config["training"]["representation"] == "caller_only":
            raise ValueError("Caller-only comparative fits are inactive under the 2026-10-10 owner-approved scope")
    if mode == "final_training":
        if config["training"]["epochs"] < 3:
            raise ValueError("Final duration must come from the approved CV selection (at least three epochs)")
        if config["training"]["seed"] != 67 or config["training"]["effective_batch_size"] != 16:
            raise ValueError("Final retraining must use the selected seed and effective batch")
        if config["training"]["representation"] != "whole_conversation":
            raise ValueError("Final training uses the selected whole-conversation app representation")
        if config["optimizer"]["learning_rate"] not in (2e-5, 3e-5, 5e-5):
            raise ValueError("Final learning rate must match the selected approved CV configuration")
        if _require(config, "selection.final_candidate_approved", bool) is not True:
            raise ValueError("Final training requires written human candidate approval")
        _require(config, "selection.selected_config_sha256", str)
        _require(config, "selection.selection_report_sha256", str)
        _require(config, "selection.warmup_conversion_reference", str)
    _require(config, "runtime.device", str)
    if not config["runtime"]["device"].startswith(("cuda", "mps", "cpu")):
        raise ValueError("runtime.device must explicitly select cuda, mps, or cpu")
    _require(config, "paths.persistent_storage_verified", bool)
    _require(config, "paths.storage_verification_reference", str)
    if config["paths"]["persistent_storage_verified"] is not True:
        raise ValueError("Persistent storage must be mounted and verified before execution")
    if not Path(config["paths"]["persistent_runs"]).expanduser().is_absolute():
        raise ValueError("persistent_runs must be an explicit absolute path")
    return config


def load_config(path: Path) -> dict:
    return validate_config(json.loads(Path(path).read_text(encoding="utf-8")))


def resolve_precision(torch, device, requested):
    """Resolve approved precision policy against the actual device; never downgrade silently."""
    if requested == "fp32":
        return "fp32"
    if requested == "bf16":
        if device.type == "cuda" and not torch.cuda.is_bf16_supported():
            raise RuntimeError("Requested BF16 is unsupported by the current CUDA device")
        if device.type == "mps":
            raise RuntimeError("BF16 is not enabled for this MPS path; resolve precision in the approved config")
        return "bf16"
    if requested == "fp16":
        if device.type == "mps":
            raise RuntimeError("FP16 gradient scaling on MPS is not yet verified by this component; use an approved FP32 diagnostic or verify the backend first")
        if device.type != "cuda":
            raise RuntimeError("FP16 mixed precision is unsupported on the selected device")
        return "fp16"
    if requested == "auto":
        if device.type == "cuda" and torch.cuda.is_bf16_supported():
            return "bf16"
        if device.type == "cuda":
            return "fp16"
        return "fp32"
    raise ValueError("Unknown precision policy")


def seed_everything(seed, torch):
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def get_records(config, input_module):
    """Retrieve saved fold/full-pool membership. This function never requests test."""
    data_path = Path(config["paths"]["data"])
    input_config = input_module.load_config(config["paths"]["input_config"])
    approved_checkpoint = input_config["models"][config["model"]]
    if (config["checkpoint"]["id"] != approved_checkpoint["checkpoint"]
            or config["checkpoint"]["revision"] != approved_checkpoint["revision"]):
        raise ValueError("Run checkpoint identity differs from the frozen Plan 02 model identity")
    if config["mode"] == "final_training":
        training_records = input_module.load_partition("train_pool", data=data_path,
            condition=config["data"]["condition"], config=input_config)
        validation_records = []
    else:
        fold = config["fold"]
        training_records = input_module.load_partition("fold_train", data=data_path, fold=fold,
            condition=config["data"]["condition"], config=input_config)
        validation_records = input_module.load_partition("fold_validation", data=data_path, fold=fold,
            condition="primary_plus_supplemental", config=input_config)
    if not training_records or (config["mode"] != "final_training" and not validation_records):
        raise ValueError("Resolved training or validation membership is empty")
    train_ids = {row["sample_id"] for row in training_records}
    val_ids = {row["sample_id"] for row in validation_records}
    if train_ids & val_ids:
        raise ValueError("Training and validation membership overlap")
    mode = config["training"]["representation"]
    full_context = config.get("training", {}).get("window_policy") == "wangchan_full_context_v1"
    if full_context:
        from full_context import load_full_text_inputs
        full_tokenizer = input_module.load_tokenizer(config["model"], input_config,
            local_files_only=bool(config.get("runtime", {}).get("local_files_only", False)))
        train, window_manifest = load_full_text_inputs(training_records, model=config["model"],
            representation=mode, marker_condition="role_marked", fold=config["fold"],
            input_config=input_config, input_dir=config["paths"]["input_exports"], tokenizer=full_tokenizer,
            input_module=input_module)
    else:
        train = input_module.load_prepared(training_records, mode, config["model"], input_config,
            marker_condition="role_marked", folder=Path(config["paths"]["input_exports"]))
    validation = {}
    if validation_records:
        val_mode = config["validation"]["representation"]
        for marker in config["validation"]["marker_conditions"]:
            if full_context:
                from full_context import load_full_text_inputs
                validation[marker], _ = load_full_text_inputs(validation_records, model=config["model"],
                    representation=val_mode, marker_condition=marker, fold=config["fold"],
                    input_config=input_config, input_dir=config["paths"]["input_exports"], tokenizer=full_tokenizer,
                    input_module=input_module, validation=True)
            else:
                validation[marker] = input_module.load_prepared(validation_records, val_mode,
                    config["model"], input_config, marker_condition=marker,
                    folder=Path(config["paths"]["input_exports"]))
    if not full_context:
        verify_rows(training_records, train)
        for marker, rows in validation.items():
            verify_rows(validation_records, rows)
    if config["mode"] == "diagnostic":
        requested = config["training"]["optimizer_updates_limit"] * config["training"]["effective_batch_size"]
        ordered = sorted(train, key=lambda item: (-(item.get("content_token_count") or item["notices"]["prepared_token_count"]), item["sample_id"]))
        train = ordered[:min(requested, len(ordered))]
        if len(train) < requested:
            raise ValueError("Not enough assigned training records to fill approved diagnostic updates")
        train_ids = {item["sample_id"] for item in train}
    # The data and assignment files are hashed and membership remains explicit in run_config.
    membership = {"training_sample_ids": sorted(train_ids),
                  "validation_sample_ids": sorted(val_ids)}
    if full_context:
        membership["window_policy"] = {"name": "wangchan_full_context_v1", "pooling_method": config["training"]["pooling_method"],
            "training_chunk_counts": {row["sample_id"]: row["chunk_count"] for row in train},
            "training_content_token_counts": {row["sample_id"]: row["content_token_count"] for row in train},
            "validation_chunk_counts": {marker: {row["sample_id"]: row["chunk_count"] for row in rows}
                                        for marker, rows in validation.items()},
            "validation_content_token_counts": {marker: {row["sample_id"]: row["content_token_count"] for row in rows}
                                                 for marker, rows in validation.items()}}
    return training_records, validation_records, train, validation, input_config, membership


def verify_rows(records, prepared):
    expected = {r["sample_id"]: r for r in records}
    actual = {r["sample_id"]: r for r in prepared}
    if len(actual) != len(prepared) or set(actual) != set(expected):
        raise ValueError("Prepared input membership differs from assigned records")
    for sample_id, item in actual.items():
        if item["label"] not in (0, 1) or item["source_dataset"] != expected[sample_id]["source_dataset"]:
            raise ValueError("Prepared label/source metadata differs from assigned records")
        if item.get("split") != "train":
            raise ValueError("Training component received a non-training prepared record")


def resource_snapshot(torch, device):
    """Capture host RSS and accelerator peak allocation where supported."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    # macOS reports bytes; Linux reports KiB.
    rss = int(usage.ru_maxrss if platform.system() == "Darwin" else usage.ru_maxrss * 1024)
    snapshot = {"process_peak_rss_bytes": rss, "device_type": device.type}
    if device.type == "cuda" and torch.cuda.is_available():
        snapshot.update({"cuda_peak_allocated_bytes": int(torch.cuda.max_memory_allocated(device)),
                         "cuda_peak_reserved_bytes": int(torch.cuda.max_memory_reserved(device))})
    elif device.type == "mps" and hasattr(torch, "mps") and hasattr(torch.mps, "current_allocated_memory"):
        snapshot["mps_current_allocated_bytes"] = int(torch.mps.current_allocated_memory())
        if hasattr(torch.mps, "driver_allocated_memory"):
            snapshot["mps_driver_allocated_bytes"] = int(torch.mps.driver_allocated_memory())
    return snapshot


def describe_environment(torch, device, precision):
    packages = {}
    for package in ("torch", "transformers", "tokenizers", "huggingface-hub", "sentencepiece", "protobuf"):
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = None
    result = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "hostname": socket.gethostname(),
        "platform": platform.platform(), "python": sys.version, "packages": packages,
        "device": str(device), "device_type": device.type, "precision": precision,
        "cuda_available": torch.cuda.is_available(),
        "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "mps_available": bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())}
    return result


def build_model(model_key, checkpoint, revision, *, local_files_only=False):
    """Load base checkpoint into a fresh two-score sequence-classification head."""
    from transformers import AutoConfig, AutoModelForSequenceClassification
    extra = {"revision": revision, "local_files_only": local_files_only,
             "token": False, "trust_remote_code": model_key == "hplt"}
    config = AutoConfig.from_pretrained(checkpoint, **extra)
    config.num_labels = 2
    config.id2label = {0: "Not Scam", 1: "Scam"}
    config.label2id = {"Not Scam": 0, "Scam": 1}
    # from_pretrained creates a new classification head on each independent run;
    # resume paths load state from that run's verified checkpoint instead.
    model, loading = AutoModelForSequenceClassification.from_pretrained(
        checkpoint, config=config, ignore_mismatched_sizes=True, output_loading_info=True, **extra)
    if getattr(model.config, "num_labels", None) != 2:
        raise RuntimeError("Loaded model does not expose exactly two class scores")
    head_terms = {"classifier", "classification_head", "pre_classifier", "sequence_summary", "logits_proj", "score"}
    roots = [name for name, _ in model.named_modules() if name and
             name.lower().split(".")[-1] in head_terms]
    top_roots = [name for name in roots if not any(name.startswith(other + ".") for other in roots)]
    if not top_roots:
        raise RuntimeError("Could not identify a supported fresh sequence-classification head")
    allow_wangchan_checkpoint_extras = is_approved_wangchan_checkpoint(
        model_key, checkpoint, revision, config)
    validate_pretrained_loading_info(model_key, loading, top_roots,
                                     allow_wangchan_checkpoint_extras=allow_wangchan_checkpoint_extras,
                                     approved_extra_keys=approved_candidate_extra_keys(model_key, checkpoint, revision, config))
    for name, module in model.named_modules():
        if any(name == root or name.startswith(root + ".") for root in top_roots):
            if not list(module.children()):
                model._init_weights(module)
    model._scam_reinitialized_head_modules = top_roots
    model._scam_loading_info = {key: loading.get(key, [])
        for key in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")}
    if loading.get("error_msgs"):
        raise RuntimeError("Pretrained loading reported errors: " + "; ".join(loading["error_msgs"]))
    if not all(parameter.requires_grad for name, parameter in model.named_parameters()
               if not any(name == root or name.startswith(root + ".") for root in top_roots)):
        raise RuntimeError("Full fine-tuning requires every backbone parameter to be trainable")
    return model


WANGCHANBERTA_PRETRAINING_HEAD_KEYS = frozenset({
    "lm_head.bias",
    "lm_head.dense.weight",
    "lm_head.dense.bias",
    "lm_head.layer_norm.weight",
    "lm_head.layer_norm.bias",
    "lm_head.decoder.weight",
})

# Transformers 4.57.6's RobertaForSequenceClassification builds
# RobertaModel(add_pooling_layer=False) and feeds sequence_output to its task
# classifier, so these checkpoint pooler parameters are not used by this model.
# Keep the exception exact and apply it only to unexpected keys for the pinned
# WangchanBERTa masked-LM checkpoint/revision.
WANGCHANBERTA_UNUSED_POOLER_KEYS = frozenset({
    "roberta.pooler.dense.bias",
    "roberta.pooler.dense.weight",
})


def is_approved_wangchan_checkpoint(model_key, checkpoint, revision, model_config):
    """Bind narrowly unused checkpoint extras to the frozen WangchanBERTa base."""
    if model_key != "wangchanberta":
        return False
    pinned_config_path = INPUT_DIR / "preprocessing_config.json"
    try:
        pinned_config = json.loads(pinned_config_path.read_text(encoding="utf-8"))
        expected = pinned_config["models"]["wangchanberta"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return False
    architectures = getattr(model_config, "architectures", None) or []
    return (checkpoint == expected.get("checkpoint")
            and revision == expected.get("revision")
            and getattr(model_config, "model_type", None) == "camembert"
            and "RobertaForMaskedLM" in architectures)


def approved_candidate_extra_keys(model_key, checkpoint, revision, model_config):
    """Allow only observed unused task weights for two exact pinned MLM bases."""
    expected_architectures = {
        "phayathaibert": ("camembert", "CamembertForMaskedLM"),
        "xlmr": ("xlm-roberta", "XLMRobertaForMaskedLM"),
    }
    if model_key not in expected_architectures:
        return frozenset()
    frozen = json.loads((INPUT_DIR / "preprocessing_config.json").read_text())
    expected = frozen["models"][model_key]
    model_type, architecture = expected_architectures[model_key]
    if (checkpoint != expected["checkpoint"] or revision != expected["revision"]
            or getattr(model_config, "model_type", None) != model_type
            or architecture not in (getattr(model_config, "architectures", None) or [])):
        return frozenset()
    unused = frozenset({
        "lm_head.bias", "lm_head.dense.bias", "lm_head.dense.weight",
        "lm_head.layer_norm.bias", "lm_head.layer_norm.weight",
    })
    if model_key == "xlmr":
        unused |= WANGCHANBERTA_UNUSED_POOLER_KEYS
    return unused


def validate_pretrained_loading_info(model_key, loading, classification_head_roots,
                                     *, allow_wangchan_checkpoint_extras=False,
                                     approved_extra_keys=frozenset()):
    """Reject incomplete backbone loads; allow only exact unused keys for the pinned Wangchan checkpoint."""
    def is_classification_head_key(key):
        return any(key == root or key.startswith(root + ".")
                   for root in classification_head_roots)

    def is_known_wangchan_checkpoint_extra(key):
        # This exception is enabled only after checking the exact frozen
        # checkpoint/revision and its CamemBERT masked-LM architecture.
        return (model_key == "wangchanberta" and allow_wangchan_checkpoint_extras
                and key in (WANGCHANBERTA_PRETRAINING_HEAD_KEYS | WANGCHANBERTA_UNUSED_POOLER_KEYS))

    bad_missing = [key for key in loading.get("missing_keys", [])
                   if not is_classification_head_key(key)]
    bad_unexpected = [key for key in loading.get("unexpected_keys", [])
                      if not is_classification_head_key(key)
                      and not is_known_wangchan_checkpoint_extra(key)
                      and key not in approved_extra_keys]
    bad_mismatched = [item[0] for item in loading.get("mismatched_keys", [])
                      if not is_classification_head_key(item[0])]
    if bad_missing or bad_unexpected or bad_mismatched:
        raise RuntimeError("Pretrained backbone loading was incomplete or mismatched: " + json.dumps({
            "missing_backbone": bad_missing, "unexpected_backbone": bad_unexpected,
            "mismatched_backbone": bad_mismatched}))


def adamw_parameter_groups(model, weight_decay):
    decay, no_decay = [], []
    for name, parameter in model.named_parameters():
        if not parameter.requires_grad:
            continue
        lowered = name.lower()
        if name.endswith(".bias") or "norm" in lowered or "normalization" in lowered:
            no_decay.append(parameter)
        else:
            decay.append(parameter)
    groups = []
    if decay:
        groups.append({"params": decay, "weight_decay": weight_decay, "group_name": "decay"})
    if no_decay:
        groups.append({"params": no_decay, "weight_decay": 0.0, "group_name": "no_decay"})
    if not groups:
        raise ValueError("No trainable parameters")
    return groups


def optimizer_group_names(model):
    groups = {"decay": [], "no_decay": []}
    for name, parameter in model.named_parameters():
        if parameter.requires_grad:
            lowered = name.lower()
            category = "no_decay" if name.endswith(".bias") or "norm" in lowered or "normalization" in lowered else "decay"
            groups[category].append(name)
    return groups


def pad_collate(items, tokenizer, torch, input_module=None):
    # Always enforce the authoritative frozen tokenizer/configuration/mask contract.
    if input_module is None:
        raise ValueError("Authoritative inputs.pad_batch module is required")
    padded = input_module.pad_batch(items, tokenizer)
    tensors = {key: torch.as_tensor(value) for key, value in padded["inputs"].items()}
    return {"inputs": tensors, "labels": torch.tensor(padded["labels"], dtype=torch.long),
        "sample_ids": [item["sample_id"] for item in items],
        "sources": [item["source_dataset"] for item in items]}


def pad_window_collate(items, tokenizer, torch):
    """Flatten windows for the encoder while retaining one label and owner per conversation."""
    flat, owners = [], []
    for owner, item in enumerate(items):
        windows = item.get("windows")
        if not windows:
            raise ValueError("Full-context conversation has no windows")
        flat.extend(windows)
        owners.extend([owner] * len(windows))
    padded = tokenizer.pad(flat, padding="longest", return_attention_mask=True, return_tensors=None)
    return ({"inputs": {key: torch.as_tensor(value) for key, value in padded.items()},
             "labels": torch.tensor([item["label"] for item in items], dtype=torch.long),
             "sample_ids": [item["sample_id"] for item in items],
             "sources": [item["source_dataset"] for item in items]}, owners)


def pool_window_logits(window_logits, owners, conversation_count, method):
    from full_context import pool_logits
    return pool_logits(window_logits, owners, conversation_count, method)


def batches(items, batch_size, *, shuffle, seed, epoch):
    order = list(range(len(items)))
    if shuffle:
        random.Random(seed + epoch).shuffle(order)
    for start in range(0, len(order), batch_size):
        yield [items[i] for i in order[start:start + batch_size]]


def amp_context(torch, device, precision):
    if precision == "fp32":
        return torch.autocast(device_type=device.type, enabled=False)
    dtype = torch.bfloat16 if precision == "bf16" else torch.float16
    return torch.autocast(device_type=device.type, dtype=dtype)


def metrics_from_predictions(labels, preds):
    tp = sum(y == 1 and p == 1 for y, p in zip(labels, preds))
    fp = sum(y == 0 and p == 1 for y, p in zip(labels, preds))
    fn = sum(y == 1 and p == 0 for y, p in zip(labels, preds))
    tn = sum(y == 0 and p == 0 for y, p in zip(labels, preds))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    p0 = tn / (tn + fn) if tn + fn else 0.0
    r0 = tn / (tn + fp) if tn + fp else 0.0
    f10 = 2 * p0 * r0 / (p0 + r0) if p0 + r0 else 0.0
    return {"scam_precision": precision, "scam_recall": recall, "scam_f1": f1,
        "macro_f1": (f10 + f1) / 2, "accuracy": (tn + tp) / len(labels),
        "confusion_matrix": [[tn, fp], [fn, tp]], "undefined_metrics": {
            "scam_precision": tp + fp == 0, "scam_recall": tp + fn == 0,
            "not_scam_precision": tn + fn == 0, "not_scam_recall": tn + fp == 0}}


def _write_csv(path, fields, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _append_attempt_progress(path: Path, event: dict) -> None:
    """Append flushed scalar observability only; this is not a recovery checkpoint."""
    with Path(path).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()


def _atomic_write_json(path: Path, value: dict) -> None:
    """Flush a temporary JSON record and atomically replace the destination."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp.open("w", encoding="utf-8") as stream:
            stream.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
            stream.flush()
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _atomic_torch_save(payload, destination, torch):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(destination.name + f".{uuid.uuid4().hex}.tmp")
    try:
        torch.save(payload, temp)
        # Verify deserialization before atomically replacing the latest checkpoint.
        loaded = torch.load(temp, map_location="cpu", weights_only=False)
        if loaded.get("run_identity") != payload.get("run_identity"):
            raise RuntimeError("Checkpoint verification identity mismatch")
        os.replace(temp, destination)
    finally:
        temp.unlink(missing_ok=True)


def _verify_recovery_checkpoint(path, expected, torch):
    """Load a recovery file and verify the run/update identity it claims to hold."""
    loaded = torch.load(path, map_location="cpu", weights_only=False)
    if (not isinstance(loaded, dict)
            or loaded.get("run_identity") != expected.get("run_identity")
            or ("optimizer_updates" in expected
                and loaded.get("optimizer_updates") != expected.get("optimizer_updates"))):
        raise RuntimeError(f"Recovery checkpoint verification failed: {path}")
    # Publication/rollback callers need identity metadata only. Retaining full
    # model/optimizer tensors for latest and previous can exhaust Colab host RAM.
    return {"run_identity": loaded["run_identity"],
            "optimizer_updates": loaded.get("optimizer_updates")}


def load_recovery_checkpoint(run_dir, expected_run_identity, torch):
    """Load latest recovery state, falling back to previous only when needed."""
    state, slot, _failures = load_recovery_checkpoint_with_evidence(run_dir, expected_run_identity, torch)
    return state, slot


def load_recovery_checkpoint_with_evidence(run_dir, expected_run_identity, torch,
                                          *, expected_slot_sha256=None, rejected_slots=None):
    """Select a recovery slot and retain per-slot validation failures for read-only reports."""
    checkpoint_dir = Path(run_dir) / "checkpoints"
    required = {"run_identity", "model", "optimizer", "scheduler", "epoch",
        "optimizer_updates", "rng"}
    failures = []
    expected_slot_sha256 = expected_slot_sha256 or {}
    rejected_slots = rejected_slots or {}
    for slot in ("latest", "previous"):
        path = checkpoint_dir / f"{slot}.pt"
        if slot in rejected_slots:
            failures.append(f"{slot}: skipped before deserialization: {rejected_slots[slot]}")
            continue
        try:
            if slot in expected_slot_sha256:
                expected_sha256 = expected_slot_sha256[slot]
                actual_sha256 = sha256_file(path)
                if actual_sha256 != expected_sha256:
                    raise ValueError(f"SHA-256 mismatch (expected {expected_sha256}, got {actual_sha256})")
            state = torch.load(path, map_location="cpu", weights_only=False)
            if not isinstance(state, dict):
                raise ValueError("checkpoint root is not an object")
            if state.get("run_identity") != expected_run_identity:
                raise ValueError("run identity mismatch")
            missing = required - set(state)
            if missing:
                raise ValueError(f"checkpoint is missing required state fields: {sorted(missing)}")
            return state, slot, failures
        except Exception as exc:
            failures.append(f"{slot}: {type(exc).__name__}: {exc}")
    raise RuntimeError("Cannot resume: neither recovery checkpoint is valid (" + "; ".join(failures) + ")")


class RecoveryPublishError(RuntimeError):
    """Publication and rollback both failed; retain the verified backup for recovery."""


def _publish_recovery_staging(staging, destination, backup, expected, torch,
                              *, backup_expected=None):
    """Publish into an absent name and verify it; restore from backup on failure."""
    destination = Path(destination)
    backup = Path(backup) if backup is not None else None
    # Drive/FUSE may behave differently when rename replaces a large existing
    # file. Remove the old name only after a verified recovery copy/slot exists.
    try:
        destination.unlink(missing_ok=True)
    except Exception as exc:
        if backup is not None and backup.is_file():
            raise RecoveryPublishError(
                f"Could not clear {destination} for publication; preserve backup at {backup}: {exc}") from exc
        raise
    try:
        os.replace(staging, destination)
        _verify_recovery_checkpoint(destination, expected, torch)
    except Exception as publish_error:
        try:
            destination.unlink(missing_ok=True)
            if backup is not None and backup.is_file():
                # Copy, rather than consume, the backup. If restoration itself
                # is unreadable on persistent storage, retain the backup file.
                shutil.copy2(backup, destination)
                _verify_recovery_checkpoint(destination, backup_expected or expected, torch)
        except Exception as restore_error:
            backup_note = f"; preserve backup at {backup}" if backup is not None else ""
            raise RecoveryPublishError(
                f"Recovery publication failed and rollback could not be verified{backup_note}: "
                f"{restore_error}") from publish_error
        raise


def save_recovery(run_dir, payload, torch, *, latest=True):
    ckpt_dir = Path(run_dir) / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    if not latest:
        raise ValueError("Recovery rotation always updates the verified latest checkpoint")
    latest_path = ckpt_dir / "latest.pt"
    previous_path = ckpt_dir / "previous.pt"
    staging = ckpt_dir / f"recovery.{uuid.uuid4().hex}.tmp"
    previous_staging = ckpt_dir / f"previous.{uuid.uuid4().hex}.tmp"
    latest_backup = ckpt_dir / f"latest-backup.{uuid.uuid4().hex}.tmp"
    latest_before = None
    previous_before = None
    previous_stage_ready = False
    retain_latest_backup = False
    retain_previous_backup = False
    try:
        torch.save(payload, staging)
        _verify_recovery_checkpoint(staging, payload, torch)

        # Snapshot the current slots before changing either authoritative name.
        # A malformed latest file must never displace a valid previous checkpoint.
        if latest_path.is_file():
            try:
                latest_before = _verify_recovery_checkpoint(latest_path,
                    {"run_identity": payload.get("run_identity")}, torch)
            except Exception:
                latest_before = None
            if latest_before is not None:
                shutil.copy2(latest_path, latest_backup)
                _verify_recovery_checkpoint(latest_backup, latest_before, torch)
                shutil.copy2(latest_path, previous_staging)
                _verify_recovery_checkpoint(previous_staging, latest_before, torch)
                previous_stage_ready = True
        if previous_path.is_file():
            try:
                previous_before = _verify_recovery_checkpoint(previous_path,
                    {"run_identity": payload.get("run_identity")}, torch)
            except Exception:
                previous_before = None
        if latest_before is not None and previous_before is None:
            # Ensure a standard recovery slot exists before removing the old
            # latest name for publication, including on the first rotation.
            _publish_recovery_staging(previous_staging, previous_path, None,
                latest_before, torch)
            previous_before = latest_before
            previous_stage_ready = False
        if latest_before is None and previous_before is not None:
            # Latest is missing/unreadable. Keep the known-good previous slot
            # untouched and retain a verified copy for rollback of latest.
            shutil.copy2(previous_path, latest_backup)
            _verify_recovery_checkpoint(latest_backup, previous_before, torch)

        try:
            _publish_recovery_staging(staging, latest_path, latest_backup,
                payload, torch, backup_expected=latest_before or previous_before)
        except RecoveryPublishError:
            retain_latest_backup = True
            raise

        # Rotate only after the new latest has passed verification at its final
        # destination. Keep a backup of the existing previous slot so a failed
        # destination check cannot destroy the last known-good previous file.
        if previous_stage_ready:
            previous_backup = ckpt_dir / f"previous-backup.{uuid.uuid4().hex}.tmp"
            try:
                if previous_path.is_file():
                    shutil.copy2(previous_path, previous_backup)
                    if previous_before is None:
                        previous_backup.unlink(missing_ok=True)
                    else:
                        _verify_recovery_checkpoint(previous_backup, previous_before, torch)
                try:
                    _publish_recovery_staging(previous_staging, previous_path,
                        previous_backup if previous_backup.is_file() else None,
                        latest_before, torch, backup_expected=previous_before)
                except RecoveryPublishError:
                    retain_previous_backup = True
                    raise
            finally:
                if not retain_previous_backup:
                    previous_backup.unlink(missing_ok=True)
    finally:
        staging.unlink(missing_ok=True)
        previous_staging.unlink(missing_ok=True)
        if not retain_latest_backup:
            latest_backup.unlink(missing_ok=True)
    return str(latest_path)


def save_epoch_model(run_dir, model, epoch):
    """Persist a verified model-only epoch snapshot for cross-fold duration selection."""
    from safetensors.torch import save_file, load_file
    snapshot_dir = Path(run_dir) / "epoch_models"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    path = snapshot_dir / f"epoch-{epoch:03d}.safetensors"
    if path.exists():
        raise FileExistsError(f"Epoch model snapshot already exists: {path}")
    temp = snapshot_dir / f".{path.name}.{uuid.uuid4().hex}.tmp"
    try:
        state = {key: value.detach().to(device="cpu").contiguous()
                 for key, value in model.state_dict().items()}
        save_file(state, str(temp))
        check = load_file(str(temp), device="cpu")
        if set(check) != set(state) or any(not torch_equal_cpu(check[key], value) for key, value in state.items()):
            raise RuntimeError("Epoch model snapshot verification failed")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)
    return str(path), sha256_file(path)


def torch_equal_cpu(left, right):
    import torch
    return torch.equal(left, right)


def prune_epoch_model_snapshots(run_dir, selected_config_path):
    """Prune unselected epoch weights only after this fold is in a frozen selection.

    Histories/predictions and latest/previous recovery checkpoints are never
    changed. The pruning ledger retains each removed snapshot checksum so old
    history references remain auditable after their model bytes are removed.
    """
    run_dir = Path(run_dir).resolve()
    selected_path = Path(selected_config_path).resolve()
    selected = json.loads(selected_path.read_text(encoding="utf-8"))
    if selected.get("status") != "frozen_by_human_approval":
        raise ValueError("Epoch snapshots can only be pruned after human-frozen model selection")
    run_config_path = run_dir / "run_config.json"
    if not run_config_path.is_file():
        raise FileNotFoundError("Run config is required to bind selected-fold provenance")
    run_config = json.loads(run_config_path.read_text(encoding="utf-8"))
    selected_runs = selected.get("selection_artifacts", {}).get("selected_cv_runs", [])
    if (not isinstance(selected_runs, list) or len(selected_runs) != 5
            or {row.get("fold") for row in selected_runs if isinstance(row, dict)} != set(range(5))
            or len({row.get("run_id") for row in selected_runs if isinstance(row, dict)}) != 5):
        raise ValueError("Frozen selection must bind five distinct CV run configs, one per saved fold")
    selected_run = next((row for row in selected_runs
                         if row.get("run_id") == run_config.get("run_id")), None)
    if selected_run is None:
        raise ValueError("This run is not one of the five selected configuration folds")
    config_hash = sha256_file(run_config_path)
    if selected_run.get("run_config_sha256") != config_hash or selected_run.get("fold") != run_config.get("fold"):
        raise ValueError("Frozen selection does not bind this exact run config/fold")
    if (run_config.get("mode") != "comparative"
            or run_config.get("model") != selected.get("model_key")
            or run_config.get("data", {}).get("condition") != selected.get("data_condition")
            or run_config.get("optimizer", {}).get("learning_rate") != selected.get("learning_rate")
            or run_config.get("training", {}).get("representation") != "whole_conversation"
            or run_config.get("training", {}).get("marker_condition") != "role_marked"
            or selected.get("training_representation") != "whole_conversation"
            or selected.get("training_marker_condition") != "role_marked"
            or selected.get("inference_representation") != "whole_conversation"
            or selected.get("inference_marker_condition") != "role_free"
            or selected.get("threshold") != 0.5):
        raise ValueError("Run config is not the frozen selected model/data/LR configuration")
    selected_epoch = selected.get("selected_duration_epochs")
    if type(selected_epoch) is not int or selected_epoch < 1:
        raise ValueError("Frozen selection must identify its common selected duration")
    ledger_path = run_dir / "epoch_snapshot_pruning.json"
    snapshot_dir = run_dir / "epoch_models"
    keep = snapshot_dir / f"epoch-{selected_epoch:03d}.safetensors"
    if not keep.is_file() or keep.is_symlink():
        raise FileNotFoundError(f"Selected epoch model snapshot is missing: {keep}")
    history_path = run_dir / "training_history.csv"
    with history_path.open("r", encoding="utf-8", newline="") as stream:
        history = list(csv.DictReader(stream))
    selected_rows = [row for row in history if int(row["epoch"]) == selected_epoch
                     and row.get("validation_marker_condition") == "role_free"
                     and row.get("status") == "completed_epoch"]
    if not selected_rows or any(Path(row["checkpoint_reference"]).resolve() != keep.resolve()
                                 or row.get("checkpoint_sha256") != sha256_file(keep)
                                 for row in selected_rows):
        raise ValueError("Selected epoch history/checksum does not identify the frozen snapshot")
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        if (ledger.get("selected_config_sha256") != sha256_file(selected_path)
                or ledger.get("run_config_sha256") != config_hash
                or ledger.get("retained_snapshot", {}).get("sha256") != sha256_file(keep)):
            raise ValueError("Existing pruning ledger belongs to a different selection or snapshot")
        for entry in ledger.get("pruned_snapshots", []):
            path = run_dir / entry["path"]
            if path.is_symlink():
                raise ValueError("Epoch snapshots may not be symlinks")
            if path.exists():
                if sha256_file(path) != entry["sha256"]:
                    raise ValueError("A previously pruned snapshot changed; preserve evidence")
                path.unlink()
        return ledger
    removed = []
    for path in sorted(snapshot_dir.glob("epoch-*.safetensors")):
        if path == keep:
            continue
        if path.is_symlink():
            raise ValueError("Epoch snapshots may not be symlinks")
        removed.append({"path": str(path.relative_to(run_dir)), "sha256": sha256_file(path),
                        "size_bytes": path.stat().st_size})
    ledger = {"schema_version": 1, "selected_config_path": str(selected_path),
        "selected_config_sha256": sha256_file(selected_path), "selected_configuration_id": selected.get("configuration_id"),
        "selected_duration_epochs": selected_epoch, "run_id": run_config["run_id"],
        "fold": run_config["fold"], "run_config_sha256": config_hash,
        "retained_snapshot": {"path": str(keep.relative_to(run_dir)), "sha256": sha256_file(keep)},
        "pruned_snapshots": removed}
    # Record the audit ledger before deletion so interruption can be resumed safely.
    ledger_path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for entry in removed:
        (run_dir / entry["path"]).unlink()
    return ledger


def prune_epoch_model_snapshots_for_cv_run(run_dir, selection_evidence, configuration_id):
    """Prune one CV run after its five-fold common duration is fully selected.

    The selection CLI invokes this only on an explicit pruning command. The
    aggregate is recomputed from normalized sample predictions before any
    snapshot is removed; all five run configs, epoch histories, summaries and
    model snapshot checksums are independently verified here.
    """
    required = ("schema_version", "cv_results_path", "cv_results_sha256",
                "normalized_predictions_path", "normalized_predictions_sha256",
                "experiment_manifest_path", "experiment_manifest_sha256",
                "selection_protocol_reference")
    if not isinstance(selection_evidence, dict) or any(not selection_evidence.get(key) for key in required):
        raise ValueError("Selection evidence must identify result, prediction, manifest checksums and protocol approval")
    if selection_evidence.get("schema_version") != 1:
        raise ValueError("Unsupported selection evidence schema")
    if not isinstance(configuration_id, str) or not configuration_id or any(
            char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in configuration_id):
        raise ValueError("configuration_id must be a safe approved matrix identifier")
    paths = {name: Path(selection_evidence[key]).resolve() for name, key in (
        ("results", "cv_results_path"), ("predictions", "normalized_predictions_path"),
        ("manifest", "experiment_manifest_path"))}
    expected_hashes = {"results": selection_evidence["cv_results_sha256"],
                       "predictions": selection_evidence["normalized_predictions_sha256"],
                       "manifest": selection_evidence["experiment_manifest_sha256"]}
    for name, path in paths.items():
        if not path.is_file() or sha256_file(path) != expected_hashes[name]:
            raise ValueError(f"Selection {name} file is missing or its SHA-256 differs from approval evidence")

    # Use the owning selection aggregator, not a duplicate metric implementation.
    selection_path = ROOT / "03 - MODEL DEVELOPMENT/selection/runtime.py"
    spec = importlib.util.spec_from_file_location("scam_selection_for_snapshot_prune", selection_path)
    selection = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load the owning selection aggregate implementation")
    spec.loader.exec_module(selection)
    import argparse
    import tempfile as tempfile_module
    with tempfile_module.TemporaryDirectory(prefix="scam-prune-verify-") as tmp:
        recomputed = Path(tmp) / "cv_results.csv"
        selection.aggregate(argparse.Namespace(predictions=str(paths["predictions"]), output=str(recomputed)))
        if sha256_file(recomputed) != expected_hashes["results"]:
            raise ValueError("CV results do not reproduce exactly from normalized predictions")

    results = list(csv.DictReader(paths["results"].open("r", encoding="utf-8", newline="")))
    eligible_by_epoch = {}
    for marker in ("role_free", "role_marked"):
        rows = [row for row in results if row.get("row_type") == "aggregate"
            and row.get("configuration_id") == configuration_id
            and row.get("training_representation") == "whole_conversation"
            and row.get("training_marker_condition") == "role_marked"
            and row.get("validation_representation") == "whole_conversation"
            and row.get("validation_marker_condition") == marker
            and row.get("subset") == "combined" and row.get("source_dataset") == "all"]
        if not rows:
            raise ValueError(f"No aggregate results for {configuration_id}/{marker}")
        for row in rows:
            if (row.get("complete_five_folds") != "true" or int(row.get("n_failed", "-1")) != 0
                    or not row.get("scam_f1_mean")):
                continue
            epoch = int(row["epoch"])
            eligible_by_epoch.setdefault(epoch, {})[marker] = float(row["scam_f1_mean"])
    complete_epochs = [epoch for epoch, metrics in eligible_by_epoch.items()
                       if set(metrics) == {"role_free", "role_marked"}]
    if not complete_epochs:
        raise ValueError("No complete five-fold paired marker-condition epochs are eligible for duration selection")
    # Same Plan 03/01 rule: maximize unrounded role-free mean F1; exact ties go earlier.
    selected_epoch = min(complete_epochs,
        key=lambda epoch: (-eligible_by_epoch[epoch]["role_free"], epoch))

    manifest_rows = list(csv.DictReader(paths["manifest"].open("r", encoding="utf-8", newline="")))
    matching = [row for row in manifest_rows if row.get("configuration_id") == configuration_id
                and row.get("training_representation") == "whole_conversation"]
    if len(matching) != 5 or {int(row.get("fold", -1)) for row in matching} != set(range(5)):
        raise ValueError("Pruning requires exactly five whole-conversation manifest runs, one per fold")
    matching.sort(key=lambda row: int(row["fold"]))
    configs, run_config_refs, checkpoint_refs = [], [], []
    for row in matching:
        if row.get("execution_state") != "completed" or not row.get("artifact_location") or not row.get("run_id"):
            raise ValueError(f"All five configuration runs must be completed before pruning: {row.get('run_id')}")
        fold_dir = Path(row["artifact_location"]).resolve()
        config_path = fold_dir / "run_config.json"
        summary_path = fold_dir / "run_summary.json"
        history_path = fold_dir / "training_history.csv"
        if not config_path.is_file() or not summary_path.is_file() or not history_path.is_file():
            raise FileNotFoundError(f"Incomplete run evidence for fold {row['fold']}")
        config = json.loads(config_path.read_text(encoding="utf-8"))
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("status") == "completed":
            verify_completed_run_artifact_hashes(fold_dir)
            if summary.get("artifact_sha256", {}).get("run_config.json") != sha256_file(config_path):
                raise ValueError(f"Completed fold {row['fold']} summary does not bind the current run config")
        recorded_protocol = config.get("approval", {}).get("selection_protocol_reference")
        if (config.get("approval", {}).get("selection_protocol_approved") is not True
                or recorded_protocol != selection_evidence["selection_protocol_reference"]):
            raise ValueError(f"Fold {row['fold']} does not bind the same approved selection protocol")
        if (config.get("run_id") != row["run_id"] or config.get("mode") != "comparative"
                or config.get("selection", {}).get("grid_configuration_id") != configuration_id
                or config.get("model") != row.get("model_key")
                or config.get("data", {}).get("condition") != row.get("data_condition")
                or int(config.get("fold", -1)) != int(row["fold"])
                or float(config.get("optimizer", {}).get("learning_rate", -1)) != float(row["learning_rate"])):
            raise ValueError(f"Run config differs from the approved selection manifest: fold {row['fold']}")
        if summary.get("status") != "completed":
            raise ValueError(f"Fold {row['fold']} does not have a completed training summary")
        max_epochs = int(config.get("selection", {}).get("max_epochs", 0))
        configured_epochs = int(config.get("training", {}).get("epochs", 0))
        completed_epochs = int(summary.get("epochs_completed", 0))
        if max_epochs < 3 or configured_epochs != max_epochs or completed_epochs != max_epochs:
            raise ValueError(f"Fold {row['fold']} has not completed its full approved epoch budget")
        _assert_all_run_attempts_completed(fold_dir, max_epochs, row["run_id"])

        # A previously written pruning ledger is the only acceptable proof that
        # a recovery checkpoint is already absent. Never silently discard a
        # missing .pt file from an incomplete/failed/unrecorded run.
        recovery_dir = fold_dir / "checkpoints"
        expected_recovery = ("latest.pt", "previous.pt")
        recovery_ledger_path = fold_dir / f"epoch_snapshot_pruning-{configuration_id}.json"
        prior_pruned_recovery = {}
        prior_inventory = {}
        if recovery_ledger_path.is_symlink():
            raise ValueError(f"Existing pruning ledger may not be a symlink: {recovery_ledger_path}")
        if recovery_ledger_path.exists() and not recovery_ledger_path.is_file():
            raise ValueError(f"Existing pruning ledger is not a regular file: {recovery_ledger_path}")
        if recovery_ledger_path.is_file():
            try:
                prior_ledger = json.loads(recovery_ledger_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"Malformed existing pruning ledger for fold {row['fold']}") from exc
            if prior_ledger.get("configuration_id") != configuration_id:
                raise ValueError(f"Existing pruning ledger has a different configuration for fold {row['fold']}")
            for item in prior_ledger.get("pruner_checkpoint_inventory", []):
                rel = item.get("path")
                if (not isinstance(item.get("run_id"), str) or type(item.get("fold")) is not int
                        or rel not in {f"checkpoints/{name}" for name in expected_recovery}
                        or not isinstance(item.get("sha256"), str) or len(item["sha256"]) != 64
                        or type(item.get("size_bytes")) is not int or item["size_bytes"] < 0):
                    raise ValueError(f"Invalid checkpoint inventory provenance for fold {row['fold']}")
                prior_inventory[(item["run_id"], item["fold"], rel)] = item
            for item in prior_ledger.get("pruned_recovery_checkpoints", []):
                rel = item.get("path")
                if rel not in {f"checkpoints/{name}" for name in expected_recovery}:
                    raise ValueError(f"Unexpected recovery checkpoint in pruning ledger for fold {row['fold']}")
                if (not isinstance(item.get("sha256"), str) or len(item["sha256"]) != 64
                        or type(item.get("size_bytes")) is not int or item["size_bytes"] < 0):
                    raise ValueError(f"Invalid recovery checkpoint provenance for fold {row['fold']}")
                prior_pruned_recovery[rel] = item
        for name in expected_recovery:
            checkpoint_path = recovery_dir / name
            rel = f"checkpoints/{name}"
            inventory_key = (config["run_id"], int(row["fold"]), rel)
            recorded = prior_inventory.get(inventory_key)
            if checkpoint_path.is_symlink():
                raise ValueError(f"Recovery checkpoint may not be a symlink: {checkpoint_path}")
            if checkpoint_path.exists():
                if not checkpoint_path.is_file():
                    raise ValueError(f"Recovery checkpoint is not a regular file: {checkpoint_path}")
                current_ref = {"run_id": config["run_id"], "fold": int(row["fold"]),
                    "path": rel, "sha256": sha256_file(checkpoint_path),
                    "size_bytes": checkpoint_path.stat().st_size}
                if recorded is not None and current_ref != recorded:
                    raise ValueError(f"Recovery checkpoint differs from its pruning inventory: {checkpoint_path}")
                checkpoint_refs.append(recorded or current_ref)
            elif rel in prior_pruned_recovery and recorded is not None:
                if prior_pruned_recovery[rel] != recorded:
                    raise ValueError(f"Pruned checkpoint record differs from inventory: {checkpoint_path}")
                checkpoint_refs.append(recorded)
            else:
                raise FileNotFoundError(f"Missing recovery checkpoint without a pruning ledger: {checkpoint_path}")
        unexpected_pt = [path for path in recovery_dir.glob("*.pt")
                         if path.name not in expected_recovery]
        if unexpected_pt:
            raise ValueError(f"Unknown checkpoint files prevent safe pruning in fold {row['fold']}: {unexpected_pt}")
        configs.append(config)
        run_config_refs.append({"run_id": config["run_id"], "fold": int(config["fold"]),
                                "path": str(config_path), "sha256": sha256_file(config_path)})
    current = Path(run_dir).resolve()
    current_index = next((i for i, row in enumerate(matching)
                          if Path(row["artifact_location"]).resolve() == current), None)
    if current_index is None:
        raise ValueError("Current run directory is not one of the five selected configuration folds")
    shared_fields = ("configuration_id", "model", "checkpoint", "data", "training", "optimizer", "schedule", "precision")
    reference_config = configs[0]
    for config in configs[1:]:
        for key in shared_fields:
            left, right = reference_config.get(key), config.get(key)
            if key == "training":
                left, right = dict(left), dict(right)
                left.pop("epochs", None); right.pop("epochs", None)
            if left != right:
                raise ValueError(f"Fold configs do not share frozen {key} settings")
        if config.get("selection", {}).get("max_epochs") != reference_config.get("selection", {}).get("max_epochs"):
            raise ValueError("Fold configs have different approved epoch budgets")
    component_names = ("training_component_sha256", "input_component_sha256",
                       "input_manifest_sha256", "preprocessing_config_sha256", "assignments_sha256")
    component_refs = []
    for config in configs:
        identities = config.get("identities", {})
        values = {name: identities.get(name) for name in component_names}
        if any(not isinstance(value, str) or len(value) != 64 for value in values.values()):
            raise ValueError("Every fold must record complete training and input component checksums")
        component_refs.append({"fold": config["fold"], **values})
    if any({name: row[name] for name in component_names} !=
           {name: component_refs[0][name] for name in component_names}
           for row in component_refs[1:]):
        raise ValueError("Five fold runs do not share identical frozen component/input identities")
    data_dir = Path(reference_config["paths"]["data"]).resolve()
    if any(Path(config["paths"]["data"]).resolve() != data_dir for config in configs):
        raise ValueError("Five fold run configs do not share the same authoritative training data path")
    selection._validate_normalized_membership(paths["predictions"],
        data_dir / "split_assignments.csv", data_dir / "0 - train/dataset.csv", matching)
    normalized_rows = list(csv.DictReader(paths["predictions"].open("r", encoding="utf-8-sig", newline="")))
    for config in configs:
        expected_ids = config.get("identities", {}).get("validation_sample_ids")
        if not isinstance(expected_ids, list) or not expected_ids or len(expected_ids) != len(set(expected_ids)):
            raise ValueError(f"Fold {config['fold']} lacks an exact saved validation ID list")
        run_rows = [row for row in normalized_rows if row.get("run_id") == config["run_id"]
                    and row.get("configuration_id") == configuration_id]
        for epoch in range(1, int(config["training"]["epochs"]) + 1):
            for marker in ("role_free", "role_marked"):
                ids = [row.get("sample_id") for row in run_rows
                       if int(row.get("epoch", -1)) == epoch
                       and row.get("validation_marker_condition") == marker]
                if len(ids) != len(expected_ids) or set(ids) != set(expected_ids):
                    raise ValueError(f"Fold {config['fold']} epoch {epoch} {marker} rows do not match its saved validation IDs")
    current_config = configs[current_index]
    if sha256_file(current / "run_config.json") != run_config_refs[current_index]["sha256"]:
        raise ValueError("Current run config changed during pruning validation")
    current_snapshots = current / "epoch_models"
    retained = current_snapshots / f"epoch-{selected_epoch:03d}.safetensors"
    if not retained.is_file() or retained.is_symlink():
        raise FileNotFoundError(f"Selected duration snapshot is missing: {retained}")
    with (current / "training_history.csv").open("r", encoding="utf-8", newline="") as stream:
        history = list(csv.DictReader(stream))
    matching_history = [row for row in history if int(row["epoch"]) == selected_epoch
        and row.get("validation_marker_condition") in {"role_free", "role_marked"}
        and row.get("status") == "completed_epoch"]
    if {row.get("validation_marker_condition") for row in matching_history} != {"role_free", "role_marked"}:
        raise ValueError("Selected common epoch lacks paired validation history for the current fold")
    snapshot_sha = sha256_file(retained)
    if any(Path(row.get("checkpoint_reference", "")).resolve() != retained.resolve()
            or row.get("checkpoint_sha256") != snapshot_sha for row in matching_history):
        raise ValueError("Selected epoch history does not bind the retained model snapshot")
    ledger_path = current / f"epoch_snapshot_pruning-{configuration_id}.json"
    provenance = {"schema_version": 1, "configuration_id": configuration_id,
        "selected_duration_epochs": selected_epoch, "selection_protocol_reference": selection_evidence["selection_protocol_reference"],
        "cv_results": {"path": str(paths["results"]), "sha256": expected_hashes["results"]},
        "normalized_predictions": {"path": str(paths["predictions"]), "sha256": expected_hashes["predictions"]},
        "experiment_manifest": {"path": str(paths["manifest"]), "sha256": expected_hashes["manifest"]},
        "run_config_refs": run_config_refs,
        "component_hashes": {"pruner_training_component_sha256": sha256_file(Path(__file__)),
            "recorded_training_component_sha256": current_config.get("identities", {}).get("training_component_sha256"),
            "input_component_sha256": current_config.get("identities", {}).get("input_component_sha256"),
            "input_manifest_sha256": current_config.get("identities", {}).get("input_manifest_sha256"),
            "preprocessing_config_sha256": current_config.get("identities", {}).get("preprocessing_config_sha256"),
            "assignments_sha256": current_config.get("identities", {}).get("assignments_sha256"),
            "all_folds": component_refs},
        "selected_fold": current_config["fold"],
        "pruner_checkpoint_inventory": checkpoint_refs,
        "retained_snapshot": {"path": str(retained.relative_to(current)), "sha256": snapshot_sha}}
    if ledger_path.exists():
        old = json.loads(ledger_path.read_text(encoding="utf-8"))
        if {key: value for key, value in old.items()
                if key not in {"pruned_snapshots", "pruned_recovery_checkpoints"}} != provenance:
            raise ValueError("Existing per-configuration pruning ledger differs from current verified evidence")
        removed = old.get("pruned_snapshots", [])
        for item in removed:
            path = current / item["path"]
            if path.is_symlink():
                raise ValueError("Snapshot ledger points to a symlink")
            if path.exists():
                if sha256_file(path) != item["sha256"]:
                    raise ValueError("A pruned snapshot changed since its ledger was written")
                path.unlink()
        removed_recovery = old.get("pruned_recovery_checkpoints", [])
        for item in removed_recovery:
            path = current / item["path"]
            if path.is_symlink():
                raise ValueError("Recovery checkpoint ledger points to a symlink")
            if path.exists():
                if not path.is_file() or path.stat().st_size != item["size_bytes"] or sha256_file(path) != item["sha256"]:
                    raise ValueError("A pruned recovery checkpoint changed since its ledger was written")
                path.unlink()
        return old
    removed = []
    for path in sorted(current_snapshots.glob("epoch-*.safetensors")):
        if path == retained:
            continue
        if path.is_symlink():
            raise ValueError("Epoch snapshots may not be symlinks")
        removed.append({"path": str(path.relative_to(current)), "sha256": sha256_file(path),
                        "size_bytes": path.stat().st_size})
    recovery_removed = [item for item in checkpoint_refs
        if item["run_id"] == current_config["run_id"] and item["fold"] == current_config["fold"]]
    ledger = {**provenance, "pruned_snapshots": removed,
              "pruned_recovery_checkpoints": recovery_removed}
    ledger_path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for item in removed:
        (current / item["path"]).unlink()
    for item in recovery_removed:
        path = current / item["path"]
        if path.is_symlink() or not path.is_file() or path.stat().st_size != item["size_bytes"] or sha256_file(path) != item["sha256"]:
            raise ValueError(f"Recovery checkpoint changed after pruning ledger was written: {path}")
        path.unlink()
    return ledger


def _assert_all_run_attempts_completed(run_dir, approved_max_epochs, run_id):
    """Refuse checkpoint deletion if this run contains any failed or incomplete attempt."""
    run_dir = Path(run_dir)
    attempt_root = run_dir / "attempt_evidence"
    if attempt_root.is_symlink() or not attempt_root.is_dir():
        raise ValueError(f"Run {run_id} has no safe attempt-evidence directory")
    state_paths = sorted(attempt_root.glob("*/attempt_state.json"))
    if not state_paths:
        raise ValueError(f"Run {run_id} has no attempt-state evidence")
    observed_attempts = {}
    for state_path in state_paths:
        if state_path.is_symlink() or not state_path.is_file():
            raise ValueError(f"Run {run_id} has unsafe attempt-state evidence: {state_path}")
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Run {run_id} has malformed attempt-state evidence: {state_path}") from exc
        target = state.get("target_epochs") if isinstance(state, dict) else None
        if (not isinstance(state, dict) or state.get("status") != "completed" or type(target) is not int or target < 1
                or target > approved_max_epochs
                or int(state.get("last_completed_epoch", -1)) != target):
            raise ValueError(f"Run {run_id} has a failed or incomplete attempt; recovery checkpoints are retained")
        attempt_ref = str(state_path.resolve())
        observed_attempts[attempt_ref] = state

    attempts_path = run_dir / "run_attempts.jsonl"
    if attempts_path.is_symlink() or not attempts_path.is_file():
        raise ValueError(f"Run {run_id} lacks safe run-attempt history")
    try:
        attempts = [json.loads(line) for line in attempts_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Run {run_id} has malformed run-attempt history") from exc
    if len(attempts) != len(observed_attempts):
        raise ValueError(f"Run {run_id} attempt-state and run-attempt histories disagree")
    if any(not isinstance(attempt, dict) for attempt in attempts):
        raise ValueError(f"Run {run_id} has malformed run-attempt entries")
    for attempt in attempts:
        state_ref = attempt.get("attempt_state")
        state = observed_attempts.get(str(Path(state_ref).resolve())) if isinstance(state_ref, str) else None
        target = state.get("target_epochs") if isinstance(state, dict) else None
        if (state is None or attempt.get("run_id") != run_id or attempt.get("status") != "completed"
                or type(target) is not int or target < 1 or target > approved_max_epochs
                or int(attempt.get("epochs_completed", -1)) != target):
            raise ValueError(f"Run {run_id} has a failed or incomplete invocation; recovery checkpoints are retained")

    failures_path = run_dir / "attempt_failures.jsonl"
    if failures_path.is_symlink():
        raise ValueError(f"Run {run_id} has unsafe startup-failure evidence")
    if failures_path.exists():
        if not failures_path.is_file():
            raise ValueError(f"Run {run_id} has invalid startup-failure evidence")
        failure_lines = [line for line in failures_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for line in failure_lines:
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Run {run_id} has malformed startup-failure evidence") from exc
            if not isinstance(record, dict):
                raise ValueError(f"Run {run_id} has malformed startup-failure evidence")
        if failure_lines:
            raise ValueError(f"Run {run_id} records a failed startup invocation; recovery checkpoints are retained")


def export_model(run_dir, output_dir=None):
    """Export a completed run as native inference-only HF files plus checksums.

    Final-evaluation callers must invoke this before opening the test set and
    evaluate these exact bytes. This function never reads dataset records.
    """
    import torch
    run_dir = Path(run_dir).resolve()
    run_config = json.loads((run_dir / "run_config.json").read_text(encoding="utf-8"))
    if run_config.get("mode") != "final_training":
        raise ValueError("Only final_training runs may be exported as the frozen inference bundle")
    summary_path = run_dir / "run_summary.json"
    if not summary_path.exists() or json.loads(summary_path.read_text(encoding="utf-8")).get("status") != "completed":
        raise ValueError("Final training must be completed before model export")
    source = run_dir / "checkpoints/latest.pt"
    state = torch.load(source, map_location="cpu", weights_only=False)
    if state.get("run_identity") != recovery_identity(run_config):
        raise ValueError("Recovery checkpoint does not match run_config.json")
    destination = (Path(output_dir) if output_dir else run_dir / "final_model").resolve()
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise FileExistsError("Inference export destination is nonempty; preserve it and choose a new path")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = destination.with_name(destination.name + f".staging-{uuid.uuid4().hex}")
    stage.mkdir()
    try:
        model = build_model(run_config["model"], run_config["checkpoint"]["id"],
            run_config["checkpoint"]["revision"], local_files_only=True)
        model.load_state_dict(state["model"])
        model.save_pretrained(stage, safe_serialization=True)
        sys.path.insert(0, str(INPUT_DIR))
        import inputs
        input_cfg = inputs.load_config(run_config["paths"]["input_config"])
        tokenizer = inputs.load_tokenizer(run_config["model"], input_cfg, local_files_only=True)
        tokenizer.save_pretrained(stage)
        files = {str(path.relative_to(stage)): sha256_file(path)
                 for path in sorted(stage.rglob("*")) if path.is_file()}
        if "model.safetensors" not in files and not any(name.startswith("model-") and name.endswith(".safetensors") for name in files):
            raise RuntimeError("Inference export did not produce safetensors weights")
        manifest = {"schema_version": 1, "run_id": run_config["run_id"],
        "configuration_id": run_config["configuration_id"], "model": run_config["model"],
        "checkpoint_id": run_config["checkpoint"]["id"],
        "checkpoint_revision": run_config["checkpoint"]["revision"],
        "custom_code_revision": run_config["checkpoint"].get("custom_code_revision"),
        "preprocessing_config_sha256": run_config["identities"]["preprocessing_config_sha256"],
        "assignments_sha256": run_config["identities"]["assignments_sha256"],
        "training_membership_sha256": run_config["identities"]["training_membership_sha256"],
        "training_seed": run_config["training"]["seed"],
        "training_data_condition": run_config["data"]["condition"],
        "training_representation": run_config["training"]["representation"],
        "training_marker_condition": run_config["training"]["marker_condition"],
        "num_labels": int(model.config.num_labels), "id2label": model.config.id2label,
        "label2id": model.config.label2id,
        "head_modules": [name for name, _ in model.named_modules() if name and
            any(term in name.lower().split(".")[-1] for term in
                ("classifier", "classification_head", "pre_classifier", "sequence_summary", "logits_proj", "score"))],
        "dropout_config": {key: value for key, value in model.config.to_dict().items()
            if "dropout" in key.lower()}, "files": files}
        (stage / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        verify_model_artifact(stage)
        if destination.exists():
            destination.rmdir()
        os.replace(stage, destination)
    except Exception:
        failed = stage.with_name(stage.name.replace(".staging-", ".failed-"))
        if stage.exists():
            os.replace(stage, failed)
        raise
    return destination


def verify_model_artifact(model_dir):
    model_dir = Path(model_dir).resolve()
    manifest_path = model_dir / "artifact_manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("Inference artifact manifest is missing or a symlink")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("num_labels") != 2:
        raise ValueError("Unsupported inference artifact manifest or class count")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Inference artifact manifest has no file checksum list")
    for name, digest in files.items():
        rel = Path(name)
        path = model_dir / rel
        if rel.is_absolute() or ".." in rel.parts or path.is_symlink() or model_dir not in path.resolve().parents:
            raise ValueError(f"Unsafe inference artifact path: {name}")
        if not path.is_file() or sha256_file(path) != digest:
            raise ValueError(f"Inference artifact checksum mismatch: {name}")
    if any(path.is_symlink() for path in model_dir.rglob("*")):
        raise ValueError("Inference artifact may not contain symlinks")
    observed = {str(path.relative_to(model_dir)) for path in model_dir.rglob("*")
        if path.is_file() and path.name != "artifact_manifest.json"}
    if observed != set(files):
        raise ValueError("Inference artifact contains unmanifested or missing files")
    if "model.safetensors" not in files and not any(name.startswith("model-") and name.endswith(".safetensors") for name in files):
        raise ValueError("Inference artifact has no safetensors weights")
    required = {"config.json", "tokenizer_config.json"}
    tokenizer_assets = ("tokenizer.json", "sentencepiece.bpe.model", "spiece.model", "vocab.json")
    if not required.issubset(files) or not any(name in files for name in tokenizer_assets):
        raise ValueError("Inference artifact is missing model or tokenizer configuration files")
    expected_mapping = {"0": "Not Scam", "1": "Scam"}
    if {str(k): v for k, v in manifest.get("id2label", {}).items()} != expected_mapping:
        raise ValueError("Inference artifact label mapping differs from the frozen project mapping")
    for field in ("run_id", "configuration_id", "checkpoint_id", "checkpoint_revision",
                  "preprocessing_config_sha256", "assignments_sha256", "training_membership_sha256"):
        if not manifest.get(field):
            raise ValueError(f"Inference artifact manifest is missing {field}")
    if manifest.get("model") not in SUPPORTED_MODELS:
        raise ValueError("Inference artifact references an unknown model")
    if manifest["model"] == "hplt" and manifest.get("custom_code_revision") != manifest.get("checkpoint_revision"):
        raise ValueError("HPLT custom code and checkpoint revisions differ")
    config_data = json.loads((model_dir / "config.json").read_text(encoding="utf-8"))
    config_id2label = {str(k): v for k, v in config_data.get("id2label", {}).items()}
    config_label2id = config_data.get("label2id", {})
    if config_data.get("num_labels", len(config_id2label)) != 2:
        raise ValueError("Saved inference config does not describe two labels")
    if config_id2label != {"0": "Not Scam", "1": "Scam"} or config_label2id != {"Not Scam": 0, "Scam": 1}:
        raise ValueError("Saved inference config label mapping differs from the frozen project mapping")
    return manifest


def load_model_for_inference(model_dir):
    """Load a verified exported artifact without optimizer/training state."""
    manifest = verify_model_artifact(model_dir)
    from transformers import AutoModelForSequenceClassification
    model = AutoModelForSequenceClassification.from_pretrained(
        model_dir, local_files_only=True, trust_remote_code=manifest["model"] == "hplt",
        token=False, use_safetensors=True)
    if model.config.num_labels != 2:
        raise ValueError("Loaded inference model does not have two scores")
    if {str(k): v for k, v in model.config.id2label.items()} != {"0": "Not Scam", "1": "Scam"}:
        raise ValueError("Loaded inference model label mapping differs")
    model.eval()
    return model, manifest


def environment_rng_state(torch, device_type=None):
    state = {"python": random.getstate(), "torch": torch.get_rng_state()}
    try:
        import numpy as np
        state["numpy"] = np.random.get_state()
    except ImportError:
        pass
    if torch.cuda.is_available():
        state["cuda"] = torch.cuda.get_rng_state_all()
    if device_type == "mps":
        if not (hasattr(torch.mps, "get_rng_state") and hasattr(torch.mps, "set_rng_state")):
            raise RuntimeError("MPS RNG state APIs are unavailable; exact recovery is unsupported")
        state["mps"] = torch.mps.get_rng_state()
    return state


def restore_rng_state(state, torch):
    random.setstate(state["python"])
    torch.set_rng_state(state["torch"])
    if "numpy" in state:
        import numpy as np
        np.random.set_state(state["numpy"])
    if "cuda" in state and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(state["cuda"])
    if "mps" in state:
        torch.mps.set_rng_state(state["mps"])


def apply_recovery_state(state, model, optimizer, scheduler, scaler, torch):
    """Apply one verified recovery payload using the same path for resume and verification."""
    model.load_state_dict(state["model"])
    optimizer.load_state_dict(state["optimizer"])
    scheduler.load_state_dict(state["scheduler"])
    scaler.load_state_dict(state.get("scaler", {}))
    for label, expected, actual in (
            ("model", state["model"], model.state_dict()),
            ("optimizer", state["optimizer"], optimizer.state_dict()),
            ("scheduler", state["scheduler"], scheduler.state_dict()),
            ("scaler", state.get("scaler", {}), scaler.state_dict())):
        if not _state_values_equal(expected, actual, torch):
            raise RuntimeError(f"Restored {label} state differs from the selected checkpoint")
    restore_rng_state(state["rng"], torch)
    epoch = state["epoch"]
    epoch_complete = state.get("epoch_complete", True)
    return {
        "start_epoch": epoch if epoch_complete else epoch - 1,
        "optimizer_updates": state["optimizer_updates"],
        "next_batch_cursor": 0 if epoch_complete else state["next_batch_cursor"],
        "epoch_loss_sum": 0.0 if epoch_complete else state["epoch_loss_sum"],
        "epoch_conversations_processed": (0 if epoch_complete
            else state["epoch_conversations_processed"]),
        "history": state.get("history", []),
        "predictions": state.get("predictions", []),
        "epoch_complete": epoch_complete,
        "rng": state["rng"],
    }


def _artifact_tree_sha256(root):
    """Hash every regular file under root; refuse symlinks to keep read-only evidence bounded."""
    root = Path(root)
    hashes = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RuntimeError(f"Restore-only verification refuses symlinked run artifact: {path}")
        if path.is_file():
            hashes[path.relative_to(root).as_posix()] = sha256_file(path)
    return hashes


def validate_restore_only_request(config, *, resume, extend_to_epoch):
    if not resume or extend_to_epoch is not None:
        raise ValueError("Restore-only verification requires --resume without epoch extension")
    training = config.get("training", {})
    optimizer = config.get("optimizer", {})
    microbatch = training.get("microbatch_size")
    if (config.get("run_id") != CP01_RESTORE_RUN_ID
            or config.get("mode") != "diagnostic"
            or config.get("model") != "wangchanberta"
            or config.get("checkpoint", {}).get("id") != CP01_RESTORE_MODEL_ID
            or config.get("checkpoint", {}).get("revision") != CP01_RESTORE_MODEL_REVISION
            or config.get("checkpoint", {}).get("custom_code_revision") is not None
            or config.get("data", {}).get("condition") != "primary_plus_supplemental"
            or config.get("fold") != 0
            or training.get("representation") != "whole_conversation"
            or training.get("marker_condition") != "role_marked"
            or training.get("seed") != 67
            or training.get("epochs") != 1
            or training.get("optimizer_updates_limit") != 2
            or training.get("effective_batch_size") != 16
            or type(microbatch) is not int
            or microbatch not in (1, 2, 4, 8, 16)
            or training.get("accumulation_steps") != (16 // microbatch if microbatch else None)
            or training.get("recovery_interval_updates") != 1
            or config.get("diagnostic_sample_selection", {}).get("strategy") != "longest_by_prepared_tokens"
            or config.get("diagnostic_sample_selection", {}).get("source") != "eligible fold_train records, marked whole-conversation prepared tokens"
            or config.get("diagnostic_sample_selection", {}).get("sample_count") != 32
            or config.get("diagnostic_sample_selection", {}).get("tie_break") != "ascending sample_id"
            or config.get("validation", {}).get("representation") != "whole_conversation"
            or config.get("validation", {}).get("marker_conditions") != ["role_marked", "role_free"]
            or optimizer.get("name") != "AdamW"
            or optimizer.get("learning_rate") != 3e-5
            or optimizer.get("weight_decay") != 0.01
            or optimizer.get("beta1") != 0.9
            or optimizer.get("beta2") != 0.999
            or optimizer.get("epsilon") != 1e-8
            or optimizer.get("gradient_clip_norm") != 1.0
            or config.get("schedule", {}).get("name") != "linear_warmup_then_constant"
            or config.get("schedule", {}).get("warmup_updates") != 0
            or config.get("precision", {}).get("mode") != "auto"
            or config.get("precision", {}).get("auto_policy_approved") is not True
            or config.get("evaluation", {}).get("scam_threshold") != 0.5
            or config.get("approval", {}).get("diagnostic_numeric_settings") is not True
            or config.get("approval", {}).get("status") != "owner_approved"
            or config.get("approval", {}).get("reference") != CP01_RESTORE_APPROVAL_REFERENCE
            or config.get("approval", {}).get("selection_protocol_approved") is not False
            or config.get("runtime", {}).get("device") != "cuda"):
        raise ValueError("Restore-only request differs from the exact approved CP01 run, checkpoint, or diagnostic settings")


def validate_cp01_previous_checkpoint(run_dir):
    checkpoint_path = Path(run_dir) / "checkpoints" / "previous.pt"
    if checkpoint_path.is_symlink() or not checkpoint_path.is_file():
        raise FileNotFoundError("The exact CP01 previous.pt checkpoint is missing or symlinked")
    actual_sha256 = sha256_file(checkpoint_path)
    if actual_sha256 != CP01_RESTORE_PREVIOUS_SHA256:
        raise ValueError("previous.pt SHA-256 differs from the reviewed CP01 checkpoint")
    return actual_sha256


def restore_only_step_evidence():
    return {
        "forward_calls": 0,
        "backward_calls": 0,
        "optimizer_steps": 0,
        "explicit_scheduler_steps": 0,
        "scheduler_constructor_initialization": (
            "LambdaLR construction may perform its standard implicit initialization; "
            "the checkpoint scheduler state is then loaded and verified."),
    }


def _restore_only_report(state, selected_slot, slot_failures, progress, run_dir,
                         artifacts_before, torch, device_type):
    artifacts_after = _artifact_tree_sha256(run_dir)
    history_hash = canonical_hash(progress["history"])
    predictions_hash = canonical_hash(progress["predictions"])
    observed_rng = environment_rng_state(torch, device_type)
    rng_matches = all(
        key in observed_rng and _state_values_equal(value, observed_rng[key], torch)
        for key, value in progress["rng"].items())
    return {
        "status": "restore_verified" if artifacts_before == artifacts_after and rng_matches else "restore_mismatch",
        "run_id": state["run_config"].get("run_id"),
        "checkpoint_slot": selected_slot,
        "checkpoint_slot_failures_before_selection": slot_failures,
        "previous_checkpoint_sha256": artifacts_before.get("checkpoints/previous.pt"),
        "checkpoint_run_identity_sha256": state["run_identity"],
        "recorded_training_component_sha256": state.get("run_config", {}).get("identities", {}).get("training_component_sha256"),
        "verification_training_component_sha256": sha256_file(Path(__file__)),
        "epoch": state["epoch"],
        "epoch_complete": progress["epoch_complete"],
        "optimizer_updates": progress["optimizer_updates"],
        "next_batch_cursor": progress["next_batch_cursor"],
        "epoch_loss_sum": progress["epoch_loss_sum"],
        "epoch_conversations_processed": progress["epoch_conversations_processed"],
        "history_count": len(progress["history"]),
        "history_sha256": history_hash,
        "prediction_count": len(progress["predictions"]),
        "predictions_sha256": predictions_hash,
        "model_tensor_count": sum(torch.is_tensor(value) for value in state["model"].values()),
        "optimizer_state_entry_count": len(state["optimizer"].get("state", {})),
        "state_application_verified": {"model": True, "optimizer": True,
            "scheduler": True, "scaler": True},
        "rng_state_applied_exactly": rng_matches,
        "run_artifact_sha256_before": artifacts_before,
        "run_artifact_sha256_after": artifacts_after,
        "run_artifacts_unchanged": artifacts_before == artifacts_after,
        "training_steps": restore_only_step_evidence(),
        "report_contains_sample_content": False,
    }


def _state_values_equal(left, right, torch):
    if torch.is_tensor(left):
        return torch.is_tensor(right) and torch.equal(left.detach().cpu(), right.detach().cpu())
    if isinstance(left, dict):
        return isinstance(right, dict) and left.keys() == right.keys() and all(
            _state_values_equal(left[key], right[key], torch) for key in left)
    if isinstance(left, (list, tuple)):
        return type(left) is type(right) and len(left) == len(right) and all(
            _state_values_equal(a, b, torch) for a, b in zip(left, right))
    if type(left).__module__.startswith("numpy"):
        import numpy as np
        if isinstance(left, np.ndarray):
            return isinstance(right, np.ndarray) and np.array_equal(left, right)
    return left == right


def synchronize_device(torch, device):
    """Wait for asynchronous device work when the backend exposes a sync call."""
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    elif device.type == "mps" and hasattr(torch.mps, "synchronize"):
        torch.mps.synchronize()


def _run_training_impl(config: dict, *, resume=False, extend_to_epoch=None, restore_only=False,
                       attempt_clock_start=None, attempt_started_utc=None):
    attempt_clock_start = time.monotonic() if attempt_clock_start is None else attempt_clock_start
    attempt_started_utc = attempt_started_utc or datetime.now(timezone.utc).isoformat()
    if extend_to_epoch is not None:
        if config.get("mode") != "comparative":
            raise ValueError("Epoch extension is only available for comparative CV runs")
        config = json.loads(json.dumps(config))
        config.setdefault("training", {})["epochs"] = extend_to_epoch
    if restore_only:
        validate_restore_only_request(config, resume=resume, extend_to_epoch=extend_to_epoch)
        config = json.loads(json.dumps(config))
        config["runtime"]["local_files_only"] = True
    validate_config(config)
    # Third-party runtimes are lazy: config/data validation occurs before model download.
    try:
        import torch
        from torch.nn import functional as F
        from torch.nn.utils import clip_grad_norm_
        from torch.optim import AdamW
        from torch.optim.lr_scheduler import LambdaLR
    except ImportError as exc:
        raise RuntimeError("Install the approved PyTorch/Transformers runtime before execution") from exc
    sys.path.insert(0, str(INPUT_DIR))
    import inputs

    data_loading_start = time.monotonic()
    train_records, val_records, train, val, input_config, membership = get_records(config, inputs)
    data_loading_seconds = time.monotonic() - data_loading_start
    run_root = Path(config["paths"]["persistent_runs"]).expanduser().resolve()
    run_dir = run_root / config["run_id"]
    if restore_only and (not run_dir.is_dir() or run_dir.is_symlink()):
        raise FileNotFoundError(f"Restore-only verification requires an existing regular run directory: {run_dir}")
    if not restore_only:
        run_root.mkdir(parents=True, exist_ok=True)
    if run_dir.exists() and not resume:
        raise FileExistsError(f"Run already exists; new independent run requires a unique run_id: {run_dir}")
    if not run_dir.exists():
        if restore_only:
            raise FileNotFoundError(f"Restore-only verification will not create a run directory: {run_dir}")
        run_dir.mkdir(parents=True)
    prior_summary = {}
    prior_summary_path = run_dir / "run_summary.json"
    if resume and prior_summary_path.is_file():
        prior_summary = json.loads(prior_summary_path.read_text(encoding="utf-8"))
    if resume and not restore_only:
        if prior_summary.get("status") != "completed":
            raise ValueError("Failed or interrupted fits cannot be resumed; rerun with a new run_id and fresh state")
        if extend_to_epoch is None:
            raise ValueError("Resume is reserved for an approved epoch-target extension after successful completion")
    cumulative_elapsed_base = float(prior_summary.get("elapsed_seconds", 0.0))
    run_cfg = dict(config)
    run_cfg["configuration_id"] = configuration_id(config)
    run_cfg["identities"] = {"preprocessing_config_sha256": sha256_file(Path(config["paths"]["input_config"])),
        "input_component_sha256": sha256_file(INPUT_DIR / "inputs.py"),
        "input_manifest_sha256": sha256_file(Path(config["paths"]["input_exports"]) / "manifest.json"),
        "input_length_report_sha256": sha256_file(INPUT_DIR / "token_length_report.json"),
        "training_component_sha256": sha256_file(Path(__file__)),
        "selection_component_sha256": sha256_file(ROOT / "03 - MODEL DEVELOPMENT/selection/runtime.py"),
        "assignments_sha256": input_config["assignments_sha256"],
        "training_csv_sha256": input_config["training_csv_sha256"],
        "training_membership_sha256": canonical_hash(membership["training_sample_ids"]),
        "validation_membership_sha256": canonical_hash(membership["validation_sample_ids"]),
        "training_sample_ids": membership["training_sample_ids"],
        "validation_sample_ids": membership["validation_sample_ids"],
        "training_count": len(train), "validation_count": len(val_records)}
    if membership.get("window_policy"):
        run_cfg["identities"]["window_policy"] = membership["window_policy"]
        run_cfg["identities"]["full_context_component_sha256"] = sha256_file(Path(__file__).with_name("full_context.py"))
        run_cfg["identities"]["gradient_checkpointing"] = config["training"]["gradient_checkpointing"]
    config_path = run_dir / "run_config.json"
    state = None
    restore_artifacts_before = _artifact_tree_sha256(run_dir) if restore_only else None
    if restore_only:
        validate_cp01_previous_checkpoint(run_dir)
    if resume:
        if not config_path.exists():
            raise FileNotFoundError("Cannot resume: run_config.json is missing")
        old_config = json.loads(config_path.read_text(encoding="utf-8"))
        if restore_only:
            # Pin the trainer that created this checkpoint; only the verifier
            # source hash differs because this read-only mode is new.
            recorded_trainer = old_config.get("identities", {}).get("training_component_sha256")
            if recorded_trainer != CP01_RECORDED_TRAINER_SHA256:
                raise ValueError("Restore-only checkpoint was not created by the reviewed CP01 trainer")
            old_compare = json.loads(json.dumps(old_config))
            new_compare = json.loads(json.dumps(run_cfg))
            old_compare.get("identities", {}).pop("training_component_sha256", None)
            new_compare.get("identities", {}).pop("training_component_sha256", None)
            # CP01 restore-only compatibility predates selection source hashing.
            old_compare.get("identities", {}).pop("selection_component_sha256", None)
            new_compare.get("identities", {}).pop("selection_component_sha256", None)
            old_compare.get("runtime", {}).pop("local_files_only", None)
            new_compare.get("runtime", {}).pop("local_files_only", None)
            if recovery_identity(old_compare) != recovery_identity(new_compare):
                raise ValueError("Restore-only configuration/input identities differ from the saved run")
            if config.get("training", {}).get("optimizer_updates_limit") != 2:
                raise ValueError("Restore-only verification requires the original two-update limit")
        elif recovery_identity(old_config) != recovery_identity(run_cfg):
            raise ValueError("Resume configuration/input identities differ; config was not overwritten")
        if not restore_only:
            old_epoch_target = old_config.get("training", {}).get("epochs")
            new_epoch_target = config.get("training", {}).get("epochs")
            if (config["mode"] != "comparative" or extend_to_epoch != new_epoch_target
                    or new_epoch_target != old_epoch_target + 1):
                raise ValueError("Resume may only extend a successfully completed comparative target by exactly one approved epoch")
            if new_epoch_target > config["selection"]["max_epochs"]:
                raise ValueError("Epoch extension exceeds the approved maximum")
            if int(prior_summary.get("epochs_completed", 0)) != old_epoch_target:
                raise ValueError("The prior approved epoch target did not complete successfully")
            extensions = old_config.get("epoch_extensions", [])
            extensions.append({"from_epoch_target": old_epoch_target, "to_epoch_target": new_epoch_target,
                "approval_reference": config["approval"]["selection_protocol_reference"],
                "prior_approved_settings_sha256": old_config.get("approval", {}).get("approved_settings_sha256"),
                "approved_settings_sha256": config["approval"]["approved_settings_sha256"]})
            run_cfg["epoch_extensions"] = extensions
        # Select a valid recovery slot before changing the recorded run config.
        # Corrupt/missing/wrong-run latest state falls back to the verified previous slot.
        if restore_only:
            state, resume_checkpoint_slot, resume_slot_failures = load_recovery_checkpoint_with_evidence(
                run_dir, recovery_identity(old_config), torch,
                expected_slot_sha256={"previous": CP01_RESTORE_PREVIOUS_SHA256},
                rejected_slots={"latest": "the recorded CP01 readback found an unreadable ZIP central directory"})
            if resume_checkpoint_slot != "previous":
                raise RuntimeError("CP01 restore-only verification requires the pinned previous.pt fallback slot")
            validate_cp01_previous_checkpoint(run_dir)
        else:
            state, resume_checkpoint_slot = load_recovery_checkpoint(
                run_dir, recovery_identity(run_cfg), torch)
            resume_slot_failures = []
            if (state.get("epoch_complete") is not True
                    or state.get("epoch") != old_epoch_target):
                raise ValueError("Epoch extension requires a verified checkpoint at the last completed target")
        if restore_only:
            required_restore_state = {"model", "optimizer", "scheduler", "scaler", "rng", "epoch",
                "optimizer_updates", "epoch_complete", "next_batch_cursor", "epoch_loss_sum",
                "epoch_conversations_processed", "history", "predictions", "run_config"}
            missing_restore_state = required_restore_state - set(state)
            if missing_restore_state:
                raise RuntimeError(f"Restore-only checkpoint lacks required recovery evidence: {sorted(missing_restore_state)}")
            if recovery_identity(state["run_config"]) != state["run_identity"]:
                raise RuntimeError("Checkpoint's embedded run configuration does not match its recovery identity")
        if not restore_only:
            config_path.write_text(json.dumps(run_cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        if restore_only:
            raise ValueError("Restore-only verification must use an existing run configuration")
        config_path.write_text(json.dumps(run_cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    recovery_slots = {"latest.pt", "previous.pt"}
    if recovery_slots & {p.name for p in (run_dir / "checkpoints").glob("*")} and not resume:
        raise FileExistsError("Existing recovery state requires --resume or a new run_id")
    seed_everything(config["training"]["seed"], torch)
    device = torch.device(config.get("runtime", {}).get("device", "cuda" if torch.cuda.is_available() else "cpu"))
    if restore_only and device.type != "cuda":
        raise RuntimeError("Restore-only verification requires the original CUDA runtime; no device fallback is allowed")
    precision = resolve_precision(torch, device, config["precision"]["mode"])
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    environment = describe_environment(torch, device, precision)
    tokenizer_loading_start = time.monotonic()
    tokenizer = inputs.load_tokenizer(config["model"], input_config,
        local_files_only=bool(config.get("runtime", {}).get("local_files_only", False)))
    tokenizer_loading_seconds = time.monotonic() - tokenizer_loading_start
    model_loading_start = time.monotonic()
    if resume:
        model = build_model(config["model"], config["checkpoint"]["id"],
            config["checkpoint"]["revision"], local_files_only=bool(config.get("runtime", {}).get("local_files_only", False)))
    else:
        model = build_model(config["model"], config["checkpoint"]["id"],
            config["checkpoint"]["revision"], local_files_only=bool(config.get("runtime", {}).get("local_files_only", False)))
        state = None
    model_loading_seconds = time.monotonic() - model_loading_start
    synchronize_device(torch, device)
    model_transfer_start = time.monotonic()
    model.to(device)
    gradient_checkpointing = bool(config.get("training", {}).get("gradient_checkpointing", False))
    if gradient_checkpointing:
        if not hasattr(model, "gradient_checkpointing_enable"):
            raise RuntimeError("The explicitly configured gradient checkpointing setting is unsupported by this model")
        model.gradient_checkpointing_enable()
    environment["gradient_checkpointing"] = gradient_checkpointing
    synchronize_device(torch, device)
    model_transfer_seconds = time.monotonic() - model_transfer_start
    opt_cfg = config["optimizer"]
    environment["checkpoint"] = config["checkpoint"]
    if resume:
        environment["resume_checkpoint_slot"] = resume_checkpoint_slot
    environment["model_architectures"] = getattr(model.config, "architectures", None)
    environment["classification_head_modules_reinitialized"] = getattr(model, "_scam_reinitialized_head_modules", [])
    environment["pretrained_loading_info"] = getattr(model, "_scam_loading_info", {})
    environment["classification_head_parameter_names"] = [name for name, _ in model.named_parameters()
        if any(term in name.lower() for term in ("classifier", "classification_head", "pre_classifier", "sequence_summary", "logits_proj", "score"))]
    environment["dropout_config"] = {key: value for key, value in model.config.to_dict().items() if "dropout" in key.lower()}
    environment["optimizer_parameter_groups"] = optimizer_group_names(model)
    environment["attempt_phase_durations_seconds"] = {
        "data_and_prepared_input_loading": data_loading_seconds,
        "tokenizer_loading": tokenizer_loading_seconds,
        "model_loading_and_checkpoint_restore": model_loading_seconds,
        "model_device_transfer": model_transfer_seconds,
    }
    env_path = run_dir / "environment.json"
    if restore_only:
        pass
    elif resume and env_path.exists():
        resume_path = run_dir / f"environment_resume_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        resume_path.write_text(json.dumps(environment, indent=2) + "\n", encoding="utf-8")
    else:
        env_path.write_text(json.dumps(environment, indent=2) + "\n", encoding="utf-8")
    groups = adamw_parameter_groups(model, opt_cfg["weight_decay"])
    optimizer = AdamW(groups, lr=opt_cfg["learning_rate"], betas=(opt_cfg["beta1"], opt_cfg["beta2"]), eps=opt_cfg["epsilon"])
    epoch_target = config["training"].get("epochs", 1)
    update_limit = config["training"].get("optimizer_updates_limit")
    total_updates = (update_limit if update_limit else
        ((len(train) + config["training"]["effective_batch_size"] - 1) // config["training"]["effective_batch_size"]) * epoch_target)
    warmup = config["schedule"]["warmup_updates"]
    def schedule_scale(update):
        return min(1.0, (update + 1) / warmup) if warmup else 1.0
    scheduler = LambdaLR(optimizer, schedule_scale)
    scaler = torch.amp.GradScaler(device.type, enabled=precision == "fp16")
    start_epoch, updates, resume_cursor, resume_loss, resume_count = 0, 0, 0, 0.0, 0
    history_path, predictions_path = run_dir / "training_history.csv", run_dir / "validation_predictions.csv"
    history = []
    predictions = []
    active_epoch = None
    active_epoch_loop_start = None
    active_epoch_update_start = 0
    active_epoch_loss_sum = 0.0
    active_epoch_count = 0
    active_epoch_learning_rates = []
    if resume:
        progress = apply_recovery_state(state, model, optimizer, scheduler, scaler, torch)
        start_epoch = progress["start_epoch"]
        updates = progress["optimizer_updates"]
        resume_cursor = progress["next_batch_cursor"]
        resume_loss = progress["epoch_loss_sum"]
        resume_count = progress["epoch_conversations_processed"]
        history = progress["history"]
        predictions = progress["predictions"]
        if restore_only:
            if updates != config["training"]["optimizer_updates_limit"]:
                raise RuntimeError("Checkpoint update count does not match the approved two-update diagnostic")
            report = _restore_only_report(state, resume_checkpoint_slot, resume_slot_failures, progress,
                run_dir, restore_artifacts_before, torch, device.type)
            if report["status"] != "restore_verified":
                raise RuntimeError("Restore-only verification did not preserve exact RNG/artifact state")
            return report
    loop_clock_start = time.monotonic()
    attempt_started = attempt_started_utc
    attempt_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:8]
    attempt_dir = run_dir / "attempt_evidence" / attempt_id
    attempt_dir.mkdir(parents=True, exist_ok=False)
    progress_path = attempt_dir / "optimizer_progress.jsonl"
    attempt_state_path = attempt_dir / "attempt_state.json"
    attempt_state = {"run_id": config["run_id"], "attempt_id": attempt_id,
        "started_utc": attempt_started, "status": "running", "target_epochs": epoch_target,
        "starting_optimizer_updates": updates, "optimizer_updates": updates,
        "last_completed_epoch": start_epoch, "progress_log": str(progress_path)}
    _atomic_write_json(attempt_state_path, attempt_state)
    status = "running"
    failure_reason = None
    try:
        def record_overflow(retry, old_scale, new_scale):
            _append_attempt_progress(progress_path, {
                "event": "fp16_overflow_retry", "run_id": config["run_id"],
                "attempt_id": attempt_id, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "epoch": epoch, "optimizer_updates": updates,
                "conversations_processed_in_epoch": epoch_count,
                "conversations_in_group": group_n,
                "retry": retry, "old_scale": old_scale, "new_scale": new_scale,
            })

        for epoch in range(start_epoch + 1, epoch_target + 1):
            synchronize_device(torch, device)
            model.train()
            epoch_loop_start = time.monotonic()
            active_epoch = epoch
            active_epoch_loop_start = epoch_loop_start
            active_epoch_update_start = updates
            epoch_loss_sum = resume_loss if epoch == start_epoch + 1 else 0.0
            epoch_count = resume_count if epoch == start_epoch + 1 else 0
            epoch_learning_rates = []
            active_epoch_loss_sum = epoch_loss_sum
            active_epoch_count = epoch_count
            active_epoch_learning_rates = epoch_learning_rates
            group = []
            optimizer.zero_grad(set_to_none=True)
            batch_cursor = 0
            stop_at_diagnostic_limit = False
            for mb in batches(train, config["training"]["microbatch_size"], shuffle=True,
                               seed=config["training"]["seed"], epoch=epoch):
                if epoch == start_epoch + 1 and batch_cursor < resume_cursor:
                    batch_cursor += 1
                    continue
                group.append(mb)
                batch_cursor += 1
                group_n = sum(len(batch) for batch in group)
                full_group = group_n >= config["training"]["effective_batch_size"]
                if not full_group:
                    continue
                epoch_learning_rates.append(optimizer.param_groups[0]["lr"])
                epoch_loss_sum += _train_group(group, tokenizer, model, optimizer, scaler, torch, F,
                    device, precision, clip_grad_norm_, config["optimizer"]["gradient_clip_norm"], group_n,
                    input_module=inputs, pooling_method=config.get("training", {}).get("pooling_method"),
                    on_overflow=record_overflow)
                epoch_count += group_n
                active_epoch_loss_sum = epoch_loss_sum
                active_epoch_count = epoch_count
                group = []
                updates += 1
                scheduler.step()
                _append_attempt_progress(progress_path, {
                    "run_id": config["run_id"], "attempt_id": attempt_id,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(), "epoch": epoch,
                    "optimizer_updates": updates, "epoch_optimizer_updates": updates - active_epoch_update_start,
                    "learning_rate": epoch_learning_rates[-1],
                    "conversations_processed_in_epoch": epoch_count,
                    "epoch_progress_fraction": epoch_count / len(train),
                    "epoch_training_loss_so_far": epoch_loss_sum / epoch_count if epoch_count else None,
                    "elapsed_seconds": cumulative_elapsed_base + (time.monotonic() - attempt_clock_start),
                    "resource_snapshot": resource_snapshot(torch, device),
                })
                attempt_state.update({"optimizer_updates": updates,
                    "last_observed_epoch": epoch,
                    "last_observed_conversations_processed": epoch_count,
                    "last_observed_elapsed_seconds": cumulative_elapsed_base +
                        (time.monotonic() - attempt_clock_start)})
                if update_limit and updates >= update_limit:
                    stop_at_diagnostic_limit = True
                    break
            if group:
                group_n = sum(len(batch) for batch in group)
                epoch_learning_rates.append(optimizer.param_groups[0]["lr"])
                epoch_loss_sum += _train_group(group, tokenizer, model, optimizer, scaler, torch, F,
                    device, precision, clip_grad_norm_, config["optimizer"]["gradient_clip_norm"], group_n,
                    input_module=inputs, pooling_method=config.get("training", {}).get("pooling_method"),
                    on_overflow=record_overflow)
                epoch_count += group_n
                active_epoch_loss_sum = epoch_loss_sum
                active_epoch_count = epoch_count
                updates += 1
                scheduler.step()
                _append_attempt_progress(progress_path, {
                    "run_id": config["run_id"], "attempt_id": attempt_id,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(), "epoch": epoch,
                    "optimizer_updates": updates, "epoch_optimizer_updates": updates - active_epoch_update_start,
                    "learning_rate": epoch_learning_rates[-1],
                    "conversations_processed_in_epoch": epoch_count,
                    "epoch_progress_fraction": epoch_count / len(train),
                    "epoch_training_loss_so_far": epoch_loss_sum / epoch_count if epoch_count else None,
                    "elapsed_seconds": cumulative_elapsed_base + (time.monotonic() - attempt_clock_start),
                    "resource_snapshot": resource_snapshot(torch, device),
                })
                attempt_state.update({"optimizer_updates": updates,
                    "last_observed_epoch": epoch,
                    "last_observed_conversations_processed": epoch_count,
                    "last_observed_elapsed_seconds": cumulative_elapsed_base +
                        (time.monotonic() - attempt_clock_start)})
            if epoch_count == 0:
                raise RuntimeError("No conversations were processed in this epoch")
            train_loss = epoch_loss_sum / epoch_count
            epoch_validation_rows = []
            if val:
                for marker, items in val.items():
                    results, val_loss = evaluate(model, items, tokenizer, torch, F, device, precision,
                        batch_size=config["training"]["microbatch_size"], input_module=inputs,
                        pooling_method=config.get("training", {}).get("pooling_method"))
                    labels = [row["label"] for row in results]
                    preds = [int(row["prob_scam"] >= 0.5) for row in results]
                    metrics = metrics_from_predictions(labels, preds)
                    for pred in results:
                        predictions.append({"run_id": config["run_id"], "model": config["model"],
                            "data_condition": config["data"]["condition"],
                            "training_representation": config["training"]["representation"],
                            "training_marker_condition": config["training"]["marker_condition"],
                            "validation_representation": config["validation"]["representation"],
                            "validation_marker_condition": marker, "fold": config["fold"],
                            "seed": config["training"]["seed"], "epoch": epoch,
                            "configuration_id": run_cfg["configuration_id"],
                            "evaluation_point": "diagnostic_limit" if stop_at_diagnostic_limit else "epoch_end", "execution_state": "success",
                            "failure_reason": "", "elapsed_seconds": cumulative_elapsed_base +
                                (time.monotonic() - attempt_clock_start),
                            "pooling_method": config.get("training", {}).get("pooling_method", ""), **pred})
                    epoch_validation_rows.append({"marker": marker, "loss": val_loss, "metrics": metrics})
            else:
                epoch_validation_rows = [{"marker": "unavailable", "loss": None, "metrics": {}}]
            for item in epoch_validation_rows:
                metrics = item["metrics"]
                history.append({"run_id": config["run_id"], "model": config["model"],
                    "data_condition": config["data"]["condition"],
                    "training_representation": config["training"]["representation"],
                    "training_marker_condition": config["training"]["marker_condition"],
                    "validation_representation": config.get("validation", {}).get("representation", "unavailable"),
                    "validation_marker_condition": item["marker"], "fold": config.get("fold"),
                    "seed": config["training"]["seed"], "epoch": epoch,
                    "configuration_id": run_cfg["configuration_id"],
                    "evaluation_point": "diagnostic_limit" if stop_at_diagnostic_limit else "epoch_end", "optimizer_updates": updates,
                    "conversations_processed": epoch_count,
                    "validation_conversations": len(val.get(item["marker"], [])) if item["marker"] in val else None,
                    "training_loss": train_loss,
                    "validation_loss": item["loss"], **metrics,
                    "elapsed_seconds": cumulative_elapsed_base + (time.monotonic() - attempt_clock_start),
                    "attempt_epoch_loop_seconds": time.monotonic() - epoch_loop_start,
                    "learning_rate": epoch_learning_rates[-1] if epoch_learning_rates else optimizer.param_groups[0]["lr"],
                    "checkpoint_reference": None, "checkpoint_sha256": None,
                    "status": "partial_diagnostic" if stop_at_diagnostic_limit else "completed_epoch"})
            memory = resource_snapshot(torch, device)
            if config["mode"] == "comparative":
                ref, snapshot_sha = save_epoch_model(run_dir, model, epoch)
            else:
                ref, snapshot_sha = None, None
            for row in history[-len(epoch_validation_rows):]:
                row["checkpoint_reference"] = ref
                row["checkpoint_sha256"] = snapshot_sha
                row["resource_snapshot_json"] = json.dumps(memory, sort_keys=True)
            synchronize_device(torch, device)
            epoch_elapsed = cumulative_elapsed_base + (time.monotonic() - attempt_clock_start)
            for row in history[-len(epoch_validation_rows):]:
                row["elapsed_seconds"] = epoch_elapsed
                row["attempt_epoch_loop_seconds"] = time.monotonic() - epoch_loop_start
            for row in predictions:
                if row.get("epoch") == epoch and row.get("evaluation_point") in {"epoch_end", "diagnostic_limit"}:
                    row["elapsed_seconds"] = epoch_elapsed
            checkpoint = _checkpoint_payload(model, optimizer, scheduler, scaler, torch,
                run_cfg, epoch, updates, history, predictions, epoch_complete=True,
                device_type=device.type)
            ref = save_recovery(run_dir, checkpoint, torch)
            _write_csv(history_path, HISTORY_FIELDS, history)
            _write_csv(predictions_path, PREDICTION_FIELDS, predictions)
            attempt_state.update({"last_completed_epoch": epoch, "status": "running"})
            _atomic_write_json(attempt_state_path, attempt_state)
            active_epoch = None
            resume_cursor, resume_loss, resume_count = 0, 0.0, 0
            if stop_at_diagnostic_limit:
                break
        status = "completed"
    except KeyboardInterrupt:
        status = "interrupted"
        failure_reason = "KeyboardInterrupt"
        raise
    except Exception as exc:
        status = "failed"
        failure_reason = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        synchronize_device(torch, device)
        attempt_evidence = {}
        if status != "completed":
            if active_epoch is not None:
                elapsed_now = cumulative_elapsed_base + (time.monotonic() - attempt_clock_start)
                partial_status = f"{status}_partial_epoch"
                markers = list(val) if val else ["unavailable"]
                for marker in markers:
                    history.append({"run_id": config["run_id"], "model": config["model"],
                        "data_condition": config["data"]["condition"],
                        "training_representation": config["training"]["representation"],
                        "training_marker_condition": config["training"]["marker_condition"],
                        "validation_representation": config.get("validation", {}).get("representation", "unavailable"),
                        "validation_marker_condition": marker, "fold": config.get("fold"),
                        "seed": config["training"]["seed"], "epoch": active_epoch,
                        "configuration_id": run_cfg["configuration_id"],
                        "evaluation_point": partial_status, "optimizer_updates": updates,
                        "conversations_processed": active_epoch_count,
                        "validation_conversations": len(val.get(marker, [])) if marker in val else None,
                        "training_loss": active_epoch_loss_sum / active_epoch_count if active_epoch_count else None,
                        "validation_loss": None, "scam_precision": None, "scam_recall": None,
                        "scam_f1": None, "macro_f1": None, "accuracy": None,
                        "elapsed_seconds": elapsed_now,
                        "attempt_epoch_loop_seconds": (time.monotonic() - active_epoch_loop_start
                            if active_epoch_loop_start is not None else None),
                        "learning_rate": (active_epoch_learning_rates[-1] if active_epoch_learning_rates
                            else optimizer.param_groups[0]["lr"]),
                        "checkpoint_reference": None, "checkpoint_sha256": None,
                        "resource_snapshot_json": json.dumps(resource_snapshot(torch, device), sort_keys=True),
                        "status": partial_status})
            attempt_history_path = attempt_dir / "training_history.csv"
            attempt_predictions_path = attempt_dir / "validation_predictions.csv"
            _write_csv(attempt_history_path, HISTORY_FIELDS, history)
            _write_csv(attempt_predictions_path, PREDICTION_FIELDS, predictions)
            attempt_evidence = {"attempt_training_history": str(attempt_history_path),
                "attempt_validation_predictions": str(attempt_predictions_path),
                "attempt_progress_log": str(progress_path),
                "attempt_state": str(attempt_state_path)}
        summary = {"run_id": config["run_id"], "status": status,
            "attempt_started_utc": attempt_started,
            "attempt_finished_utc": datetime.now(timezone.utc).isoformat(),
            "attempt_elapsed_seconds": time.monotonic() - attempt_clock_start,
            "elapsed_seconds": cumulative_elapsed_base + (time.monotonic() - attempt_clock_start),
            "attempt_phase_durations_seconds": environment.get("attempt_phase_durations_seconds", {
                "data_and_prepared_input_loading": data_loading_seconds,
                "tokenizer_loading": None, "model_loading_and_checkpoint_restore": None,
                "model_device_transfer": None}),
            "attempt_training_loop_elapsed_seconds": time.monotonic() - loop_clock_start,
            "epochs_completed": max((r["epoch"] for r in history if r.get("status") == "completed_epoch"), default=0),
            "optimizer_updates": updates, "training_count": len(train),
            "validation_count": len(val_records),
            "checkpoint": str(run_dir / "checkpoints/latest.pt"),
            **attempt_evidence,
            "failure_or_interruption": failure_reason}
        if status == "completed":
            summary["artifact_sha256"] = {
                name: sha256_file(run_dir / name) for name in (
                    "run_config.json", "training_history.csv", "validation_predictions.csv")}
        summary["resource_snapshot"] = resource_snapshot(torch, device)
        attempt_state.update({"status": status, "finished_utc": summary["attempt_finished_utc"],
            "optimizer_updates": updates, "last_completed_epoch": summary["epochs_completed"],
            "elapsed_seconds": summary["elapsed_seconds"],
            "resource_snapshot": summary["resource_snapshot"],
            "failure_or_interruption": failure_reason})
        _atomic_write_json(attempt_state_path, attempt_state)
        summary.update(attempt_evidence)
        summary["attempt_progress_log"] = str(progress_path)
        summary["attempt_state"] = str(attempt_state_path)
        with (run_dir / "run_attempts.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(summary, ensure_ascii=False) + "\n")
        (run_dir / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if status == "completed" and config["mode"] == "final_training":
        try:
            model_dir = export_model(run_dir)
            summary = json.loads((run_dir / "run_summary.json").read_text(encoding="utf-8"))
            summary["inference_artifact"] = str(model_dir)
            summary["inference_manifest_sha256"] = sha256_file(model_dir / "artifact_manifest.json")
            (run_dir / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        except Exception as exc:
            summary = json.loads((run_dir / "run_summary.json").read_text(encoding="utf-8"))
            summary["status"] = "failed"
            summary["failure_or_interruption"] = f"Inference artifact export failed: {type(exc).__name__}: {exc}"
            (run_dir / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
            raise
    return run_dir


def run_training(config: dict, *, resume=False, extend_to_epoch=None, restore_only=False):
    attempt_clock_start = time.monotonic()
    attempt_started_utc = datetime.now(timezone.utc).isoformat()
    caller_rng = None
    if resume and not restore_only:
        _validate_extension_resume_request(config, extend_to_epoch)
    if restore_only:
        validate_restore_only_request(config, resume=resume, extend_to_epoch=extend_to_epoch)
        import torch
        device_type = str(config.get("runtime", {}).get("device", "cuda")).split(":", 1)[0]
        caller_rng = environment_rng_state(torch, device_type)
    try:
        return _run_training_impl(config, resume=resume, extend_to_epoch=extend_to_epoch,
            restore_only=restore_only,
            attempt_clock_start=attempt_clock_start, attempt_started_utc=attempt_started_utc)
    except Exception as exc:
        if restore_only:
            raise
        # Preserve startup/load failures as attempts without overwriting prior
        # successful evidence or a mismatched run configuration.
        try:
            run_id = config.get("run_id")
            root = Path(config.get("paths", {}).get("persistent_runs", "" )).expanduser()
            if run_id and root.is_absolute() and all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in run_id):
                run_dir = root / run_id
                run_dir.mkdir(parents=True, exist_ok=True)
                attempt_elapsed = time.monotonic() - attempt_clock_start
                entry = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "status": "failed", "reason": f"{type(exc).__name__}: {exc}",
                    "resume": resume, "extend_to_epoch": extend_to_epoch,
                    "attempt_started_utc": attempt_started_utc,
                    "attempt_elapsed_seconds": attempt_elapsed}
                with (run_dir / "attempt_failures.jsonl").open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
                summary_path = run_dir / "run_summary.json"
                existing = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
                already_recorded = existing.get("attempt_started_utc") == attempt_started_utc
                if not already_recorded and (resume or not existing):
                    cumulative = float(existing.get("elapsed_seconds", 0.0)) + attempt_elapsed
                    failed_summary = {**existing, "run_id": run_id, "status": "failed",
                        "attempt_started_utc": attempt_started_utc,
                        "attempt_finished_utc": datetime.now(timezone.utc).isoformat(),
                        "attempt_elapsed_seconds": attempt_elapsed, "elapsed_seconds": cumulative,
                        "attempt_phase_durations_seconds": {}, "attempt_training_loop_elapsed_seconds": 0.0,
                        "failure_or_interruption": entry["reason"]}
                    (run_dir / "run_attempts.jsonl").open("a", encoding="utf-8").write(
                        json.dumps(failed_summary, ensure_ascii=False) + "\n")
                    summary_path.write_text(json.dumps(failed_summary, indent=2) + "\n", encoding="utf-8")
        except Exception:
            pass
        raise
    finally:
        if caller_rng is not None:
            import torch
            restore_rng_state(caller_rng, torch)


def _validate_extension_resume_request(config, extend_to_epoch):
    """Reject recovery resumes; permit only a completed comparative-target extension."""
    if extend_to_epoch is None or config.get("mode") != "comparative":
        raise ValueError("Resume is reserved for an approved comparative epoch-target extension")
    training = config.get("training", {})
    if training.get("epochs") != extend_to_epoch:
        raise ValueError("Extension config epoch target must match --extend-to-epoch")
    run_id = config.get("run_id")
    runs_root = Path(config.get("paths", {}).get("persistent_runs", "")).expanduser()
    if not run_id or not runs_root.is_absolute():
        raise ValueError("Epoch extension requires the existing run ID and persistent run directory")
    run_dir = runs_root / run_id
    summary_path = run_dir / "run_summary.json"
    config_path = run_dir / "run_config.json"
    if not summary_path.is_file() or not config_path.is_file():
        raise ValueError("Epoch extension requires a previously completed run with saved config and summary")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    previous_config = json.loads(config_path.read_text(encoding="utf-8"))
    if summary.get("status") != "completed":
        raise ValueError("Failed or interrupted fits cannot be resumed; rerun with a new run_id and fresh state")
    previous_target = previous_config.get("training", {}).get("epochs")
    if (type(previous_target) is not int or extend_to_epoch != previous_target + 1
            or int(summary.get("epochs_completed", 0)) != previous_target):
        raise ValueError("Epoch extension must add exactly one epoch after the previous target completed")
    attempt_root = run_dir / "attempt_evidence"
    if attempt_root.is_dir() and not attempt_root.is_symlink():
        for state_path in attempt_root.glob("*/attempt_state.json"):
            if state_path.is_symlink() or not state_path.is_file():
                continue
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if (state.get("status") == "running"
                    and state.get("target_epochs") == extend_to_epoch):
                raise ValueError("A prior epoch-extension attempt was interrupted; rerun the full fit with a new run_id")


def _train_group(group, tokenizer, model, optimizer, scaler, torch, F, device, precision,
                 clip_grad_norm, max_norm, total_conversations, *, input_module=None, pooling_method=None,
                 on_overflow=None, max_overflow_retries=8):
    # An FP16 overflow skips GradScaler's optimizer step. Replay the entire
    # accumulation group at its reduced scale so its conversations are not lost
    # and the caller advances its update/scheduler only after a real step.
    rng_cpu = torch.get_rng_state() if scaler.is_enabled() else None
    rng_device = (torch.cuda.get_rng_state_all() if scaler.is_enabled() and device.type == "cuda" else None)
    overflow_retries = 0
    while True:
        if overflow_retries:
            torch.set_rng_state(rng_cpu)
            if rng_device is not None:
                torch.cuda.set_rng_state_all(rng_device)
        group_loss_sum = 0.0
        optimizer.zero_grad(set_to_none=True)
        for items in group:
            if pooling_method:
                batch, owners = pad_window_collate(items, tokenizer, torch)
            else:
                batch = (pad_collate(items, tokenizer, torch) if input_module is None
                         else pad_collate(items, tokenizer, torch, input_module))
                owners = None
            inputs = {key: value.to(device) for key, value in batch["inputs"].items()}
            labels = batch["labels"].to(device)
            with amp_context(torch, device, precision):
                window_logits = model(**inputs).logits
                logits = (pool_window_logits(window_logits, owners, len(items), pooling_method)
                          if pooling_method else window_logits)
                if logits.ndim != 2 or tuple(logits.shape) != (len(items), 2):
                    raise ValueError("Training requires exactly two logits per conversation")
                if not torch.isfinite(logits).all():
                    raise FloatingPointError("Training produced non-finite logits")
                losses = F.cross_entropy(logits.float(), labels, reduction="none")
                loss_sum = losses.sum()
                if not torch.isfinite(loss_sum):
                    raise FloatingPointError("Training produced non-finite loss")
                # Weight each microbatch by actual conversation count, including partial final groups.
                loss = loss_sum / total_conversations
            if scaler.is_enabled():
                scaler.scale(loss).backward()
            else:
                loss.backward()
            group_loss_sum += float(loss_sum.detach().cpu())
        if scaler.is_enabled():
            scaler.unscale_(optimizer)
        has_nonfinite_grad = any(parameter.grad is not None and not torch.isfinite(parameter.grad).all()
                                 for parameter in model.parameters())
        if has_nonfinite_grad and scaler.is_enabled():
            old_scale = float(scaler.get_scale())
            scaler.step(optimizer)  # GradScaler records the overflow and skips this step.
            scaler.update()
            new_scale = float(scaler.get_scale())
            optimizer.zero_grad(set_to_none=True)
            if new_scale >= old_scale:
                raise FloatingPointError("FP16 non-finite gradients were not handled by GradScaler")
            overflow_retries += 1
            if on_overflow is not None:
                on_overflow(overflow_retries, old_scale, new_scale)
            if overflow_retries > max_overflow_retries:
                raise FloatingPointError(
                    f"FP16 gradient overflow persisted after {max_overflow_retries} retries")
            continue
        if has_nonfinite_grad:
            optimizer.zero_grad(set_to_none=True)
            raise FloatingPointError("Training produced non-finite gradients")
        clip_grad_norm(model.parameters(), max_norm, error_if_nonfinite=True)
        if scaler.is_enabled():
            old_scale = float(scaler.get_scale())
            scaler.step(optimizer)
            scaler.update()
            if float(scaler.get_scale()) < old_scale:
                # Protect update accounting if the scaler observed an overflow
                # that was not visible in the explicit gradient check.
                optimizer.zero_grad(set_to_none=True)
                overflow_retries += 1
                if on_overflow is not None:
                    on_overflow(overflow_retries, old_scale, float(scaler.get_scale()))
                if overflow_retries > max_overflow_retries:
                    raise FloatingPointError(
                        f"FP16 gradient overflow persisted after {max_overflow_retries} retries")
                continue
        else:
            optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        return group_loss_sum


def evaluate(model, items, tokenizer, torch, F, device, precision, *, batch_size, input_module=None, pooling_method=None):
    model.eval()
    output, total_loss, seen = [], 0.0, 0
    if pooling_method:
        # One conversation per timed pass makes chunk-count runtime summaries attributable.
        with torch.inference_mode():
            for item in items:
                batch, owners = pad_window_collate([item], tokenizer, torch)
                inputs = {key: value.to(device) for key, value in batch["inputs"].items()}
                labels = batch["labels"].to(device)
                synchronize_device(torch, device)
                started = time.perf_counter()
                with amp_context(torch, device, precision):
                    window_logits = model(**inputs).logits
                    logits = pool_window_logits(window_logits, owners, 1, pooling_method)
                    if logits.ndim != 2 or tuple(logits.shape) != (1, 2):
                        raise ValueError("Validation requires exactly two logits per conversation")
                    if not torch.isfinite(logits).all():
                        raise FloatingPointError("Validation produced non-finite logits")
                    loss = F.cross_entropy(logits.float(), labels, reduction="sum")
                    probs = torch.softmax(logits.float(), dim=-1).cpu().tolist()[0]
                    if (not all(math.isfinite(float(value)) and 0.0 <= float(value) <= 1.0 for value in probs)
                            or abs(sum(float(value) for value in probs) - 1.0) > 1e-5):
                        raise ValueError("Validation produced invalid probabilities")
                synchronize_device(torch, device)
                elapsed = time.perf_counter() - started
                total_loss += float(loss.cpu())
                seen += 1
                output.append({"sample_id": item["sample_id"], "source_dataset": item["source_dataset"],
                    "true_label": LABEL_NAMES[item["label"]], "prob_not_scam": float(probs[0]),
                    "prob_scam": float(probs[1]), "label": item["label"],
                    "chunk_count": item["chunk_count"], "content_token_count": item["content_token_count"],
                    "inference_seconds": elapsed})
        expected_ids = [item["sample_id"] for item in items]
        actual_ids = [row["sample_id"] for row in output]
        if len(actual_ids) != len(set(actual_ids)) or set(actual_ids) != set(expected_ids):
            raise ValueError("Validation predictions contain missing, duplicate, or unexpected conversation IDs")
        return output, total_loss / seen
    with torch.inference_mode():
        for mb in batches(items, batch_size, shuffle=False, seed=0, epoch=0):
            if pooling_method:
                batch, owners = pad_window_collate(mb, tokenizer, torch)
            else:
                batch = (pad_collate(mb, tokenizer, torch) if input_module is None
                         else pad_collate(mb, tokenizer, torch, input_module))
                owners = None
            inputs = {key: value.to(device) for key, value in batch["inputs"].items()}
            labels = batch["labels"].to(device)
            with amp_context(torch, device, precision):
                window_logits = model(**inputs).logits
                logits = (pool_window_logits(window_logits, owners, len(mb), pooling_method)
                          if pooling_method else window_logits)
                if logits.ndim != 2 or tuple(logits.shape) != (len(mb), 2):
                    raise ValueError("Validation requires exactly two logits per conversation")
                if not torch.isfinite(logits).all():
                    raise FloatingPointError("Validation produced non-finite logits")
                losses = F.cross_entropy(logits.float(), labels, reduction="sum")
            probs = torch.softmax(logits.float(), dim=-1).cpu().tolist()
            total_loss += float(losses.cpu())
            seen += len(mb)
            for sample_id, source, label, prob in zip(batch["sample_ids"], batch["sources"], batch["labels"].tolist(), probs):
                output.append({"sample_id": sample_id, "source_dataset": source,
                    "true_label": LABEL_NAMES[int(label)], "prob_not_scam": float(prob[0]), "prob_scam": float(prob[1]), "label": int(label)})
    ids = [r["sample_id"] for r in output]
    if len(ids) != len(set(ids)) or len(ids) != len(items):
        raise ValueError("Validation predictions contain missing or duplicate conversation IDs")
    if any(not all(0.0 <= r[key] <= 1.0 for key in ("prob_not_scam", "prob_scam"))
           or abs(r["prob_not_scam"] + r["prob_scam"] - 1.0) > 1e-5 for r in output):
        raise ValueError("Validation produced invalid probabilities")
    if items and "chunk_count" in items[0]:
        by_id = {item["sample_id"]: item for item in items}
        for row in output:
            row["chunk_count"] = by_id[row["sample_id"]]["chunk_count"]
            row["content_token_count"] = by_id[row["sample_id"]]["content_token_count"]
    return output, total_loss / seen


def _checkpoint_payload(model, optimizer, scheduler, scaler, torch, run_cfg, epoch, updates,
                        history, predictions, *, epoch_complete=True, next_batch_cursor=0,
                        epoch_loss_sum=0.0, epoch_conversations_processed=0, device_type=None):
    return {"run_identity": recovery_identity(run_cfg), "run_config": run_cfg,
        "model": model.state_dict(), "optimizer": optimizer.state_dict(),
        "scheduler": scheduler.state_dict(), "scaler": scaler.state_dict(),
        "epoch": epoch, "optimizer_updates": updates, "rng": environment_rng_state(torch, device_type),
        "epoch_complete": epoch_complete, "next_batch_cursor": next_batch_cursor,
        "epoch_loss_sum": epoch_loss_sum,
        "epoch_conversations_processed": epoch_conversations_processed,
        "history": history, "predictions": predictions}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--extend-to-epoch", type=int)
    parser.add_argument("--restore-only", action="store_true",
        help="Apply and verify an existing two-update Wangchan checkpoint without training or writing run artifacts")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        run_dir = run_training(config, resume=args.resume, extend_to_epoch=args.extend_to_epoch,
            restore_only=args.restore_only)
    except Exception as exc:
        parser.exit(2, f"Training stopped: {exc}\n")
    print(json.dumps(run_dir, indent=2, ensure_ascii=False) if args.restore_only else run_dir)


if __name__ == "__main__":
    main()
