#!/usr/bin/env python3
"""Owner-gated final training launch and frozen-bundle text evaluation.

The test loader is imported/called only after a matching owner authorization
record and explicit CLI flag pass. Importing this file never loads test data,
torch, or Transformers. Development parity users can call ``predict_with_trace``
without opening any dataset.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import importlib.metadata
import json
import math
import os
import statistics
import subprocess
import sys
import platform
import tempfile
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
FINAL_DIR = Path(__file__).resolve().parent
TRAINING_DIR = ROOT / "03 - MODEL DEVELOPMENT/training"
INPUT_DIR = ROOT / "03 - MODEL DEVELOPMENT/input-preparation"
LABELS = {"Not Scam": 0, "Scam": 1}
SOURCES = ("primary", "supplemental")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def expected_full_pool_warmup(selected: dict[str, Any], assignments_path: Path, training_csv_path: Path) -> int:
    assignments = [r for r in read_csv(assignments_path) if r.get("split") == "train"]
    training_ids = {r["sample_id"] for r in read_csv(training_csv_path)}
    if not assignments or {r["sample_id"] for r in assignments} != training_ids:
        raise ValueError("Saved train-pool assignments do not match canonical training records")
    count = sum(selected["data_condition"] != "primary_only" or row["source_dataset"] == "primary" for row in assignments)
    batch = int(selected["training_settings"]["training"]["effective_batch_size"])
    rule = selected["warmup_rule"]
    updates = 3 * math.ceil(count / batch)
    value = float(rule["fraction"]) * updates
    rounding = rule["rounding"]
    return math.ceil(value) if rounding == "ceil" else math.floor(value) if rounding == "floor" else math.floor(value + 0.5)


def expected_frozen_training_warmup(selected: dict[str, Any], final_training: dict[str, Any]) -> int:
    """Check deployment warmup from hash-bound membership, without dataset files."""
    sys.path.insert(0, str(TRAINING_DIR))
    import trainer
    identities = final_training.get("identities", {})
    ids = identities.get("training_sample_ids")
    if (not isinstance(ids, list) or not ids or any(not isinstance(x, str) or not x for x in ids)
            or len(set(ids)) != len(ids) or ids != sorted(ids)
            or trainer.canonical_hash(ids) != identities.get("training_membership_sha256")):
        raise ValueError("Frozen training membership is missing, duplicated or not checksum-bound")
    batch = selected["training_settings"]["training"]["effective_batch_size"]
    rule = selected["warmup_rule"]
    value = float(rule["fraction"]) * 3 * math.ceil(len(ids) / batch)
    rounding = rule["rounding"]
    if rounding not in ("ceil", "floor", "nearest"):
        raise ValueError("Unknown approved warmup rounding rule")
    return math.ceil(value) if rounding == "ceil" else math.floor(value) if rounding == "floor" else math.floor(value + 0.5)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def environment_metadata(pipeline: Any) -> dict[str, Any]:
    packages = {}
    for package in ("torch", "transformers", "tokenizers", "safetensors"):
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = None
    return {"python": sys.version, "platform": platform.platform(), "device": getattr(pipeline, "device", None),
            "model_key": getattr(pipeline, "model_key", None),
            "tokenizer_class": type(getattr(pipeline, "tokenizer", None)).__name__, "packages": packages}


def atomic_publish(directory: Path, artifacts: dict[str, Path]) -> dict[str, str]:
    """Publish deterministic files, preserving and checking any partial prior publication."""
    published = {}
    for name, staged in artifacts.items():
        target = directory / name
        digest = sha256(staged)
        if target.exists():
            if sha256(target) != digest:
                raise ValueError(f"Existing partial evaluation artifact differs; preserve it: {target}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staged, target)
        published[name] = digest
    return published


def read_evaluation_journal(path: Path, authorization: dict[str, Any], artifact_id: str,
                            records_by_id: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    outcomes, errors, seen = [], [], set()
    if not path.exists():
        return outcomes, errors
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            outcome = event["prediction"]
            sample_id = outcome.get("sample_id")
            source = records_by_id.get(sample_id)
            if (outcome.get("evaluation_id") != authorization["evaluation_id"]
                    or outcome.get("final_run_id") != authorization["final_run_id"]
                    or outcome.get("artifact_id") != artifact_id):
                raise ValueError("Existing per-record journal belongs to a different evaluation/artifact")
            if source is None or sample_id in seen:
                raise ValueError("Existing evaluation journal contains an unknown or duplicate sample ID")
            if (outcome.get("true_label") != source["label"]
                    or outcome.get("source_dataset") != source["source_dataset"]):
                raise ValueError("Existing evaluation journal truth/source differs from the authorized assignment")
            seen.add(sample_id)
            outcomes.append(outcome)
            if event.get("error_review"):
                errors.append(event["error_review"])
    return outcomes, errors


def validate_selection_scope(completion: dict[str, Any]) -> None:
    """Require the owner-approved reduced scope, with its approval hash-bound."""
    scope = completion.get("scope_approval", {})
    if (completion.get("main_fit_count") != 45
            or completion.get("excluded_main_fit_count") != 30
            or completion.get("caller_only_fit_count") != 0
            or completion.get("supplemental_fit_count") != 0
            or scope.get("status") != "owner_approved"
            or not scope.get("reference")):
        raise ValueError("Selection completion must account for the approved 45 fits and 30 exclusions")
    path = Path(scope.get("path") or "")
    if not path.is_file() or sha256(path) != scope.get("sha256"):
        raise ValueError("Reduced-scope approval evidence is missing or changed")


def validate_mac_compatibility(authorization: dict[str, Any]) -> None:
    """Block test access until final-model/STT compatibility evidence verifies."""
    evidence = authorization.get("mac_compatibility", {})
    path = Path(evidence.get("path") or "")
    if not path.is_file() or sha256(path) != evidence.get("sha256"):
        raise ValueError("Final-test access requires hash-bound Mac compatibility evidence")
    record = read_json(path)
    required = {
        "selected_config_sha256": authorization.get("selected_config_sha256"),
        "model_safetensors_sha256": authorization.get("model_safetensors_sha256"),
    }
    if (record.get("status") != "passed"
            or record.get("host") != "MacBook Air M2"
            or record.get("stt_checkpoint") != "airesearch/wav2vec2-large-xlsr-53-th"
            or record.get("stt_checkpoint_revision") != "3155938c549b23eee16b1d4b55dcb161b7fe4bcf"
            or record.get("audio_partition") != "development"
            or not record.get("execution_evidence")
            or any(not value or record.get(key) != value for key, value in required.items())):
        raise ValueError("Mac compatibility evidence does not match the final pipeline")


def prepare_final_training_config(args: argparse.Namespace) -> None:
    selected_path = Path(args.selected_config).resolve()
    cv_path = Path(args.cv_run_config).resolve()
    owner_path = Path(args.final_training_approval).resolve()
    selected = read_json(selected_path)
    cv_config = read_json(cv_path)
    owner = read_json(owner_path)
    completion_path = Path(args.completion_record).resolve()
    completion = read_json(completion_path)
    validate_selection_scope(completion)
    if selected.get("status") != "frozen_by_human_approval":
        raise ValueError("A human-frozen selected_config.json is required")
    print_digest = bool(getattr(args, "print_settings_digest", False))
    if (owner.get("status") != "owner_approved" and not print_digest) or not owner.get("reference"):
        raise ValueError("Final training requires a separate owner approval record")
    if owner.get("selected_config_sha256") != sha256(selected_path):
        raise ValueError("Final-training approval must bind the selected-config checksum")
    if not print_digest and (not owner.get("reviewer") or not owner.get("approval_date")):
        raise ValueError("Final-training approval must identify reviewer/date")
    if (completion.get("status") != "complete_verified"
            or completion.get("selected_config_sha256") != sha256(selected_path)
            or owner.get("selection_completion_sha256") != sha256(completion_path)
            or owner.get("selection_completion_path") != str(completion_path)):
        raise ValueError("Final training requires the verified reduced-scope completion artifact bound in owner approval")
    for evidence in completion.get("evidence", {}).values():
        evidence_path = Path(evidence["path"])
        if not evidence_path.is_file() or sha256(evidence_path) != evidence["sha256"]:
            raise ValueError("Selection completion evidence is missing or has changed")
    if not owner.get("final_run_id") or not owner.get("persistent_runs"):
        raise ValueError("Approval must supply a unique final run ID and persistent run directory")
    warmup = owner.get("final_warmup_updates")
    if type(warmup) is not int or warmup < 0:
        raise ValueError("Final warmup updates must be explicitly recorded from the approved full-pool rule")
    if owner.get("warmup_rule_reference") != selected.get("warmup_rule", {}).get("approval_reference"):
        raise ValueError("Final warmup approval must use the same recorded rule as candidate freeze")
    if cv_config.get("model") != selected.get("model_key") or cv_config.get("data", {}).get("condition") != selected.get("data_condition"):
        raise ValueError("Source CV config does not match the selected candidate")
    if cv_config.get("checkpoint", {}).get("id") != selected.get("checkpoint") or cv_config.get("checkpoint", {}).get("revision") != selected.get("checkpoint_revision"):
        raise ValueError("Source CV config checkpoint identity differs from selected_config")
    if float(cv_config.get("optimizer", {}).get("learning_rate", -1)) != float(selected.get("learning_rate", -2)):
        raise ValueError("Source CV config learning rate differs from selected_config")
    cv_ref = next((r for r in selected.get("selection_artifacts", {}).get("selected_cv_runs", [])
                   if int(r.get("fold", -1)) == int(cv_config.get("fold", -2))), None)
    if (cv_ref is None or cv_ref.get("run_id") != cv_config.get("run_id")
            or cv_ref.get("run_config_sha256") != sha256(cv_path)):
        raise ValueError("CV config must be the exact selected fold run config recorded in selected_config")
    if (owner.get("source_cv_run_id") != cv_config.get("run_id")
            or owner.get("source_cv_run_config_sha256") != sha256(cv_path)):
        raise ValueError("Final-training owner record must identify the exact selected CV source config")

    # Recompute the full-pool warmup from saved train assignments. Never use a
    # fold's count or accept a manually chosen update count as the rule itself.
    expected_warmup = expected_full_pool_warmup(selected, Path(args.assignments).resolve(), Path(args.training_csv).resolve())
    if warmup != expected_warmup:
        raise ValueError(f"Owner-recorded final warmup ({warmup}) differs from approved full-pool calculation ({expected_warmup})")

    # Ensure all selected immutable hyperparameters came from the frozen record.
    settings = selected.get("training_settings", {})
    for section in ("training", "optimizer", "precision", "runtime"):
        expected = dict(settings.get(section, {}))
        actual = dict(cv_config.get(section, {}))
        if section == "training":
            expected.pop("epochs", None); actual.pop("epochs", None)
        if expected != actual:
            raise ValueError(f"CV config {section} settings do not match the frozen selected config")
    expected_schedule = dict(settings.get("schedule", {})); actual_schedule = dict(cv_config.get("schedule", {}))
    expected_schedule.pop("warmup_updates", None); actual_schedule.pop("warmup_updates", None)
    if expected_schedule != actual_schedule:
        raise ValueError("CV schedule settings differ from frozen selected config")

    config = json.loads(json.dumps(cv_config))
    config["mode"] = "final_training"
    config["run_id"] = owner["final_run_id"]
    config["fold"] = None
    config["training"]["epochs"] = int(selected["selected_duration_epochs"])
    config["training"]["seed"] = 67
    config["training"]["representation"] = "whole_conversation"
    config["training"]["marker_condition"] = "role_marked"
    config["validation"] = {"enabled": False}
    config["schedule"]["warmup_updates"] = warmup
    config["paths"]["persistent_runs"] = owner["persistent_runs"]
    config.setdefault("selection", {})["selected_configuration_id"] = selected["configuration_id"]
    config["selection"]["selected_config_sha256"] = sha256(selected_path)
    config["selection"]["selection_completion_sha256"] = sha256(completion_path)
    config["selection"]["selection_completion_path"] = str(completion_path)
    config["approval"] = {
        **config.get("approval", {}),
        "status": "owner_approved",
        "reference": owner["reference"],
        "approved_settings_sha256": None,
        "final_training_approval": True,
        "selection_protocol_reference": selected.get("approval", {}).get("gates", {}).get("final_candidate_human_approval"),
        "final_training_approval_reference": owner["reference"],
        "final_training_reviewer": owner["reviewer"],
        "final_training_approval_date": owner["approval_date"],
        "selected_config_sha256": sha256(selected_path),
        "source_cv_run_id": cv_config["run_id"],
        "source_cv_run_config_sha256": sha256(cv_path),
        "selection_completion_sha256": sha256(completion_path),
    }
    # Keep the training component's approved-settings digest contract in sync.
    trainer_path = TRAINING_DIR / "trainer.py"
    spec = importlib.util.spec_from_file_location("scam_training_trainer", trainer_path)
    trainer = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(trainer)
    config["approval"]["approved_settings_sha256"] = trainer.approved_settings_digest(config)
    if print_digest:
        print(config["approval"]["approved_settings_sha256"])
        return
    if owner.get("approved_settings_sha256") != config["approval"]["approved_settings_sha256"]:
        raise ValueError("Final-training owner approval must contain the exact approved-settings digest for this config")
    trainer.validate_config(config, require_diagnostic_approval=False)
    output = Path(args.output).resolve()
    write_json(output, config)
    print(f"Wrote owner-approved fresh final-training config: {output}")


def draft_approval(args: argparse.Namespace) -> None:
    """Write identity-prefilled approval drafts; never changes template status to approved."""
    selected_path = Path(args.selected_config).resolve()
    selected = read_json(selected_path)
    if selected.get("status") != "frozen_by_human_approval":
        raise ValueError("Approval drafts require the frozen selected candidate")
    if args.kind == "final-training":
        if not args.cv_run_config or not args.final_run_id or not args.persistent_runs:
            raise ValueError("Final-training draft requires --cv-run-config, --final-run-id, and --persistent-runs")
        template = read_json(FINAL_DIR / "final_training_approval.template.json")
        completion_path = Path(args.completion_record).resolve()
        completion = read_json(completion_path)
        validate_selection_scope(completion)
        cv_path = Path(args.cv_run_config).resolve()
        cv = read_json(cv_path)
        if completion.get("status") != "complete_verified" or completion.get("selected_config_sha256") != sha256(selected_path):
            raise ValueError("Final-training approval draft requires matching reduced-scope selection completion")
        expected = expected_full_pool_warmup(selected, Path(args.assignments).resolve(), Path(args.training_csv).resolve())
        template.update({
            "selected_config_sha256": sha256(selected_path),
            "selection_completion_path": str(completion_path),
            "selection_completion_sha256": sha256(completion_path),
            "source_cv_run_id": cv.get("run_id"), "source_cv_run_config_sha256": sha256(cv_path),
            "final_run_id": args.final_run_id, "persistent_runs": args.persistent_runs,
            "final_warmup_updates": expected,
            "warmup_rule_reference": selected.get("warmup_rule", {}).get("approval_reference"),
        })
    else:
        if not args.model_dir or not args.output_location:
            raise ValueError("Test-execution draft requires --model-dir and --output-location")
        template = read_json(FINAL_DIR / "final_test_authorization.template.json")
        model_dir = Path(args.model_dir).resolve()
        prep_path = Path(args.preprocessing_config).resolve()
        prep = read_json(prep_path)
        final_run_config = read_json(model_dir.parent / "run_config.json")
        model_hash = sha256(model_dir / "model.safetensors")
        manifest_hash = sha256(model_dir / "artifact_manifest.json")
        completion_path = Path(final_run_config.get("selection", {}).get("selection_completion_path", ""))
        if (not completion_path.is_file()
                or final_run_config.get("selection", {}).get("selected_config_sha256") != sha256(selected_path)):
            raise ValueError("Test authorization draft requires the matching completed final-training export")
        template.update({
            "final_run_id": final_run_config.get("run_id"),
            "selected_config_sha256": sha256(selected_path),
            "selection_completion_sha256": sha256(completion_path),
            "assignments_sha256": sha256(Path(args.assignments).resolve()),
            "preprocessing_config_sha256": sha256(prep_path),
            "test_csv_sha256": prep.get("test_csv_sha256"),
            "model_safetensors_sha256": model_hash,
            "artifact_manifest_sha256": manifest_hash,
            "persistent_output_location": args.output_location,
        })
    template["status"] = "template_unapproved"
    template["explicit_final_test_execution_authorized"] = False if args.kind == "test-execution" else template.get("explicit_final_test_execution_authorized")
    write_json(Path(args.output).resolve(), template)
    print(f"Wrote an unapproved {args.kind} approval draft; no model run was launched and no held-out records were read.")


def launch_final_training(args: argparse.Namespace) -> None:
    if not args.authorized_final_training:
        raise ValueError("Pass --authorized-final-training only after the owner authorizes execution")
    config_path = Path(args.config).resolve()
    config = read_json(config_path)
    if config.get("mode") != "final_training" or config.get("approval", {}).get("final_training_approval") is not True:
        raise ValueError("Config is not an owner-approved final_training run")
    command = [sys.executable, str(TRAINING_DIR / "train.py"), "--config", str(config_path)]
    subprocess.run(command, cwd=ROOT, check=True)


class InferencePipeline:
    def __init__(self, model, tokenizer, input_module, input_config, model_key, threshold, device):
        self.model = model
        self.tokenizer = tokenizer
        self.inputs = input_module
        self.input_config = input_config
        self.model_key = model_key
        self.threshold = threshold
        self.device = device


def resolve_selection_completion(final_training: dict[str, Any], explicit_path: Path | None = None) -> Path:
    """Resolve a relocated byte-identical completion record for development parity."""
    selection = final_training.get("selection", {})
    recorded = selection.get("selection_completion_sha256")
    stored_path = Path(selection.get("selection_completion_path", ""))
    candidate = explicit_path.resolve() if explicit_path is not None else stored_path
    if not recorded or not candidate.is_file() or sha256(candidate) != recorded:
        raise ValueError("Final-training run is not bound to the current verified selection-completion checksum")
    completion = read_json(candidate)
    if (completion.get("status") != "complete_verified"
            or completion.get("selected_config_sha256") != selection.get("selected_config_sha256")):
        raise ValueError("Selection-completion record is not verified for this selected config")
    return candidate.resolve()


def load_pipeline(model_dir: Path, selected_config_path: Path, input_config_path: Path, *,
                  device: str | None = None, completion_record_path: Path | None = None) -> tuple[InferencePipeline, dict[str, Any]]:
    """Load only the verified inference export; useful for development parity too."""
    model_dir = model_dir.resolve()
    selected_path = selected_config_path.resolve()
    selected = read_json(selected_path)
    if selected.get("status") != "frozen_by_human_approval":
        raise ValueError("selected_config is not frozen by human approval")
    sys.path.insert(0, str(TRAINING_DIR))
    import trainer
    artifact = trainer.verify_model_artifact(model_dir)
    if artifact.get("model") != selected.get("model_key") or artifact.get("checkpoint_id") != selected.get("checkpoint") or artifact.get("checkpoint_revision") != selected.get("checkpoint_revision"):
        raise ValueError("Inference export identity differs from selected_config")
    final_training_path = model_dir.parent / "run_config.json"
    if not final_training_path.is_file():
        raise ValueError("Inference export must remain beside its final_training run_config.json")
    final_training = read_json(final_training_path)
    if final_training.get("mode") != "final_training" or final_training.get("model") != selected["model_key"]:
        raise ValueError("Export does not belong to the selected final-training run")
    if final_training.get("selection", {}).get("selected_config_sha256") != sha256(selected_path):
        raise ValueError("Final-training run is not bound to this selected_config checksum")
    completion_path = resolve_selection_completion(final_training, completion_record_path)
    if (final_training.get("data", {}).get("condition") != selected.get("data_condition")
            or final_training.get("training", {}).get("epochs") != selected.get("selected_duration_epochs")
            or final_training.get("training", {}).get("seed") != selected.get("training_seed")
            or final_training.get("training", {}).get("representation") != selected.get("training_representation")
            or final_training.get("training", {}).get("marker_condition") != selected.get("training_marker_condition")
            or final_training.get("optimizer", {}).get("learning_rate") != selected.get("learning_rate")
            or final_training.get("validation") != {"enabled": False}):
        raise ValueError("Final-training run settings differ from the frozen selected candidate")
    training_settings = selected.get("training_settings", {})
    for section in ("training", "optimizer", "precision", "runtime"):
        if final_training.get(section) != training_settings.get(section):
            raise ValueError(f"Final-training {section} settings differ from selected_config")
    expected_schedule = dict(training_settings.get("schedule", {}))
    final_schedule = dict(final_training.get("schedule", {}))
    expected_schedule.pop("warmup_updates", None); final_schedule.pop("warmup_updates", None)
    if final_schedule != expected_schedule:
        raise ValueError("Final-training schedule differs from selected_config")
    assigned_warmup = expected_frozen_training_warmup(selected, final_training)
    if final_training.get("schedule", {}).get("warmup_updates") != assigned_warmup:
        raise ValueError("Final-training warmup differs from the approved full-pool rule")
    trainer.validate_config(final_training, require_diagnostic_approval=False)
    model_weights = model_dir / "model.safetensors"
    if not model_weights.is_file():
        raise ValueError("Inference export must contain the frozen model.safetensors file")
    if artifact.get("run_id") != final_training.get("run_id") or artifact.get("configuration_id") != final_training.get("configuration_id"):
        raise ValueError("Export run/configuration identity differs from final-training config")
    artifact_matches = {
        "model": final_training.get("model"),
        "checkpoint_id": final_training.get("checkpoint", {}).get("id"),
        "checkpoint_revision": final_training.get("checkpoint", {}).get("revision"),
        "preprocessing_config_sha256": final_training.get("identities", {}).get("preprocessing_config_sha256"),
        "assignments_sha256": final_training.get("identities", {}).get("assignments_sha256"),
        "training_membership_sha256": final_training.get("identities", {}).get("training_membership_sha256"),
        "training_seed": final_training.get("training", {}).get("seed"),
        "training_data_condition": final_training.get("data", {}).get("condition"),
        "training_representation": final_training.get("training", {}).get("representation"),
        "training_marker_condition": final_training.get("training", {}).get("marker_condition"),
    }
    if any(artifact.get(key) != value for key, value in artifact_matches.items()):
        raise ValueError("Inference artifact training provenance differs from final_training config")
    input_config = read_json(input_config_path.resolve())
    expected = input_config["models"][selected["model_key"]]
    if (expected["checkpoint"] != selected["checkpoint"] or expected["revision"] != selected["checkpoint_revision"]
            or final_training.get("identities", {}).get("preprocessing_config_sha256") != sha256(input_config_path.resolve())):
        raise ValueError("Frozen preprocessing/model source identity mismatch")
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    import torch
    trust_remote_code = selected["model_key"] == "hplt"
    model = AutoModelForSequenceClassification.from_pretrained(
        model_dir, local_files_only=True, trust_remote_code=trust_remote_code
    )
    tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True, trust_remote_code=False)
    if type(tokenizer).__name__ != expected["tokenizer_class"] or tokenizer.pad_token_id != expected["pad_token_id"]:
        raise ValueError("Exported tokenizer class/padding differs from approved input config")
    tokenizer._scam_checkpoint_identity = (expected["checkpoint"], expected["revision"])
    sys.path.insert(0, str(INPUT_DIR))
    import inputs
    tokenizer._scam_added_token_identity = inputs.added_token_identity(tokenizer)
    chosen_device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    model.to(chosen_device)
    model.eval()
    pipeline = InferencePipeline(model, tokenizer, inputs, input_config, selected["model_key"],
                                 float(selected["threshold"]), chosen_device)
    pipeline.artifact_id = f"{artifact['run_id']}:{sha256(model_dir / 'artifact_manifest.json')}"
    pipeline.model_weights_sha256 = sha256(model_weights)
    pipeline.export_directory = str(model_dir)
    return pipeline, artifact


def predict_with_trace(text: str, pipeline: InferencePipeline) -> dict[str, Any]:
    """Run the exact role-free text reference path and expose parity evidence."""
    inputs = pipeline.inputs
    prepared_text = inputs.checkpoint_prepare_text(text, pipeline.model_key, pipeline.input_config)
    item = inputs.prepare_text(text, pipeline.model_key, pipeline.input_config, pipeline.tokenizer,
                               mode="whole_conversation", marker_condition="role_free")
    batch = inputs.pad_batch([item], pipeline.tokenizer)
    import torch
    tensors = {key: torch.tensor(value, dtype=torch.long, device=pipeline.device)
               for key, value in batch["inputs"].items()}
    with torch.inference_mode():
        logits = pipeline.model(**tensors).logits
        probs = torch.softmax(logits.float(), dim=-1)[0].cpu().tolist()
    if len(probs) != 2 or any(not math.isfinite(float(value)) for value in probs):
        raise ValueError("Model produced invalid two-class probabilities")
    p_not, p_scam = float(probs[0]), float(probs[1])
    label = "Scam" if p_scam >= pipeline.threshold else "Not Scam"
    return {
        "prepared_text": prepared_text,
        "unpad_input_ids": item["inputs"]["input_ids"],
        "unpad_attention_mask": item["inputs"]["attention_mask"],
        "batched_inputs": {key: value[0] for key, value in batch["inputs"].items()},
        "request_batch_size": 1,
        "padding": "shared input module pad_batch; single-request right-padded batch",
        "padded_length": len(batch["inputs"]["input_ids"][0]),
        "p_not_scam": p_not,
        "p_scam": p_scam,
        "predicted_label": label,
        "threshold": pipeline.threshold,
        "notices": item["notices"],
    }


class FinalEvaluationPredictor:
    """Adapter for development parity checks against the actual inference path."""
    def __init__(self, pipeline: InferencePipeline, *, model_version: str | None = None):
        self.pipeline = pipeline
        actual = getattr(pipeline, "artifact_id", None)
        if actual is None:
            raise ValueError("Predictor requires a pipeline loaded from a verified frozen export")
        if model_version is not None and model_version != actual:
            raise ValueError("model_version must equal the verified run ID and artifact-manifest checksum")
        self.model_version = actual

    def predict_with_trace(self, request: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        request_id = str(request.get("request_id", ""))
        if not request_id or not isinstance(request.get("text"), str):
            raise ValueError("request must contain request_id and string text")
        result = predict_with_trace(request["text"], self.pipeline)
        response = {
            "request_id": request_id, "model_version": self.model_version,
            "status": "success", "label": result["predicted_label"],
            "probabilities": {"Not Scam": result["p_not_scam"], "Scam": result["p_scam"]},
            "threshold": result["threshold"], "warnings": result["notices"], "error": None,
        }
        trace = {
            "prepared_text": result["prepared_text"],
            "unpadded_input_ids": result["unpad_input_ids"],
            "attention_mask": result["unpad_attention_mask"],
            "padded_model_inputs": result["batched_inputs"],
            "request_batch_size": result["request_batch_size"],
            "padding": result["padding"], "padded_length": result["padded_length"],
        }
        return response, trace


def _authorize_test(args: argparse.Namespace, selected_path: Path, model_dir: Path, assignments_path: Path,
                    test_csv_path: Path, preprocessing_path: Path) -> dict[str, Any]:
    if not args.authorized_test_execution:
        raise ValueError("Final-test access requires the explicit --authorized-test-execution flag")
    authorization_path = Path(args.authorization).resolve()
    authorization = read_json(authorization_path)
    if authorization.get("status") != "owner_approved" or authorization.get("explicit_final_test_execution_authorized") is not True:
        raise ValueError("A matching owner approval is required before opening any test records")
    if authorization.get("selected_config_sha256") != sha256(selected_path):
        raise ValueError("Final-test authorization selected-config checksum mismatch")
    if authorization.get("assignments_sha256") != sha256(assignments_path):
        raise ValueError("Final-test authorization assignment checksum mismatch")
    final_run_config = model_dir.parent / "run_config.json"
    if not final_run_config.is_file():
        raise ValueError("Final-training run config is required to resolve selection completion provenance")
    final_training = read_json(final_run_config)
    completion_path = Path(final_training.get("selection", {}).get("selection_completion_path", ""))
    if (not completion_path.is_file()
            or final_training.get("selection", {}).get("selection_completion_sha256") != sha256(completion_path)
            or authorization.get("selection_completion_sha256") != sha256(completion_path)):
        raise ValueError("Final-test authorization must bind the verified selection completion artifact")
    completion = read_json(completion_path)
    validate_selection_scope(completion)
    validate_mac_compatibility(authorization)
    if (completion.get("status") != "complete_verified"
            or completion.get("selected_config_sha256") != sha256(selected_path)):
        raise ValueError("Selection completion record is incomplete or does not match this selected config")
    if authorization.get("artifact_manifest_sha256") != sha256(model_dir / "artifact_manifest.json"):
        raise ValueError("Final-test authorization final-artifact manifest checksum mismatch")
    weights_path = model_dir / "model.safetensors"
    if not weights_path.is_file() or authorization.get("model_safetensors_sha256") != sha256(weights_path):
        raise ValueError("Final-test authorization must bind the exact model.safetensors bytes")
    if authorization.get("preprocessing_config_sha256") != sha256(preprocessing_path):
        raise ValueError("Final-test authorization preprocessing config checksum mismatch")
    if not authorization.get("reviewer") or not authorization.get("approval_date") or not authorization.get("reference"):
        raise ValueError("Authorization must identify owner, date, and approval reference")
    if not authorization.get("evaluation_id") or not authorization.get("persistent_output_location") or not authorization.get("final_run_id"):
        raise ValueError("Authorization must name a unique evaluation ID and configured persistent output location")
    final_run_config = model_dir.parent / "run_config.json"
    final_training = read_json(final_run_config)
    if authorization["final_run_id"] != final_training.get("run_id"):
        raise ValueError("Final-test authorization run ID differs from the exported final-training run")
    # Only read/hash the test file after every non-test authorization check passed.
    if authorization.get("test_csv_sha256") != sha256(test_csv_path):
        raise ValueError("Final-test authorization test-file checksum mismatch")
    return authorization


def infer_test(args: argparse.Namespace) -> None:
    selected_path = Path(args.selected_config).resolve()
    model_dir = Path(args.model_dir).resolve()
    assignments_path = Path(args.assignments).resolve()
    test_csv_path = Path(args.test_csv).resolve()
    # Verify exact artifacts and approval before loading the test CSV or invoking
    # the approved input module's test partition loader.
    selected = read_json(selected_path)
    preprocessing_path = Path(args.preprocessing_config).resolve()
    authorization = _authorize_test(args, selected_path, model_dir, assignments_path, test_csv_path, preprocessing_path)
    output_dir = Path(args.output_dir).resolve()
    if str(output_dir) != str(Path(authorization["persistent_output_location"]).resolve()):
        raise ValueError("Output directory must equal the owner-approved persistent output location")
    output_names = ("test_predictions.csv", "metrics.json", "error_analysis.csv", "evaluation_report.md", "evaluation_protocol.md")
    completion_marker = output_dir / "evaluation_complete.json"
    if completion_marker.exists():
        marker = read_json(completion_marker)
        if marker.get("status") in {"artifacts_complete_pending_error_review", "artifacts_complete_no_errors"}:
            raise FileExistsError("This evaluation is already finalized; preserve its evidence")

    pipeline, artifact = load_pipeline(model_dir, selected_path, Path(args.preprocessing_config))
    sys.path.insert(0, str(INPUT_DIR))
    import inputs
    input_config = inputs.load_config(Path(args.preprocessing_config))
    expected_test_hash = input_config["test_csv_sha256"]
    if sha256(test_csv_path) != expected_test_hash:
        raise ValueError("Test CSV differs from the frozen Plan 02 test identity")
    data_root = assignments_path.parent
    if test_csv_path != data_root / "1 - test/dataset.csv":
        raise ValueError("Test CSV path must match the frozen split directory layout")
    records = inputs.load_partition("test", data=data_root, allow_final_test=True,
                                    condition="primary_plus_supplemental", config=input_config)
    # Membership and label truth are joined only after all checks and explicit approval.
    assigned_test = {row["sample_id"]: row for row in inputs.read_csv(assignments_path, inputs.ASSIGNMENT_COLUMNS)
                     if row["split"] == "test"}
    if set(assigned_test) != {row["sample_id"] for row in records}:
        raise ValueError("Loaded test IDs differ from the approved assignment membership")
    for record in records:
        if assigned_test[record["sample_id"]]["source_dataset"] != record["source_dataset"]:
            raise ValueError(f"Loaded test source differs from saved assignment: {record['sample_id']}")
    artifact_id = artifact["run_id"] + ":" + authorization["artifact_manifest_sha256"]
    if authorization.get("artifact_id") not in (None, artifact_id):
        raise ValueError("Final-test authorization artifact ID differs from the verified export")
    outcomes = []
    errors = []
    # Append-only per-record journal makes interruption recoverable. It remains
    # beside the approved evaluation outputs and is never rewritten in place.
    journal_path = output_dir / "evaluation_events.jsonl"
    if output_dir.exists():
        if not journal_path.is_file() and any((output_dir / name).exists() for name in (*output_names, "evaluation_complete.json")):
            raise FileExistsError("Output location contains evaluation files but no recoverable journal; preserve it")
    else:
        output_dir.mkdir(parents=True, exist_ok=False)
    record_by_id = {r["sample_id"]: r for r in records}
    journal_auth = {**authorization, "final_run_id": artifact["run_id"]}
    outcomes, errors = read_evaluation_journal(journal_path, journal_auth, artifact_id, record_by_id)
    completed_ids = {row["sample_id"] for row in outcomes}
    if not completed_ids.issubset(set(assigned_test)):
        raise ValueError("Existing evaluation journal has IDs outside the authorized test assignment")
    for record in records:
        if record["sample_id"] in completed_ids:
            continue
        base = {
            "evaluation_id": authorization["evaluation_id"],
            "final_run_id": artifact["run_id"],
            "final_configuration_id": artifact["configuration_id"],
            "artifact_id": artifact_id,
            "sample_id": record["sample_id"],
            "source_dataset": record["source_dataset"],
            "true_label": record["label"],
            "threshold": pipeline.threshold,
        }
        error_record = None
        sample_started = time.perf_counter()
        try:
            role_free_text = inputs.representation(record, "whole_conversation", input_config,
                                                   marker_condition="role_free")
            trace = predict_with_trace(role_free_text, pipeline)
            outcome = {**base, "execution_state": "success", "failure_reason": "",
                       "p_not_scam": trace["p_not_scam"], "p_scam": trace["p_scam"],
                       "predicted_label": trace["predicted_label"],
                       "truncated": trace["notices"]["truncated"],
                       "original_token_count": trace["notices"]["original_token_count"],
                       "prepared_token_count": trace["notices"]["prepared_token_count"],
                       "dropped_token_count": trace["notices"]["dropped_token_count"]}
            if outcome["predicted_label"] != outcome["true_label"]:
                error_record = {
                    "evaluation_id": authorization["evaluation_id"], "sample_id": record["sample_id"],
                    "source_dataset": record["source_dataset"], "prediction_artifact_reference": "test_predictions.csv",
                    "error_type": "false_negative" if outcome["true_label"] == "Scam" else "false_positive",
                    "true_label": outcome["true_label"], "predicted_label": outcome["predicted_label"],
                    "p_scam": outcome["p_scam"], "threshold": pipeline.threshold,
                    "transcript_evidence": record["transcript"],
                    "input_length_findings": json.dumps(trace["notices"], ensure_ascii=False),
                    "structural_marker_findings": "", "observed_error_category": "",
                    "review_explanation": "", "review_evidence": "", "uncertainty": "",
                    "potential_future_investigation": "", "review_status": "pending_review",
                }
                errors.append(error_record)
            else:
                error_record = None
        except Exception as exc:  # Preserve per-sample execution failures separately from classification errors.
            outcome = {**base, "execution_state": "failure", "failure_reason": f"{type(exc).__name__}: {exc}",
                       "p_not_scam": "", "p_scam": "", "predicted_label": "", "truncated": "",
                       "original_token_count": "", "prepared_token_count": "", "dropped_token_count": ""}
        outcomes.append(outcome)
        completed_ids.add(record["sample_id"])
        outcome["elapsed_seconds"] = time.perf_counter() - sample_started
        with journal_path.open("a", encoding="utf-8") as journal:
            journal.write(json.dumps({"prediction": outcome, "error_review": error_record},
                                     ensure_ascii=False, allow_nan=False) + "\n")
            journal.flush()
            os.fsync(journal.fileno())

    if completed_ids != set(assigned_test):
        raise ValueError("Final predictions do not contain exactly one outcome per assigned test ID")
    outcomes.sort(key=lambda r: r["sample_id"])
    errors.sort(key=lambda r: r["sample_id"])

    fields = ["evaluation_id", "final_run_id", "final_configuration_id", "artifact_id", "sample_id",
              "source_dataset", "true_label", "p_not_scam", "p_scam", "predicted_label", "threshold",
              "execution_state", "failure_reason", "truncated", "original_token_count",
              "prepared_token_count", "dropped_token_count", "elapsed_seconds"]
    error_fields = ["evaluation_id", "sample_id", "source_dataset", "prediction_artifact_reference", "error_type",
                    "true_label", "predicted_label", "p_scam", "threshold", "transcript_evidence",
                    "input_length_findings", "structural_marker_findings", "observed_error_category",
                    "review_explanation", "review_evidence", "uncertainty", "potential_future_investigation", "review_status"]
    write_csv(output_dir / "error_analysis.csv", error_fields, errors)
    metrics = compute_metrics(outcomes)
    metrics.update({
        "evaluation_id": authorization["evaluation_id"], "final_run_id": artifact["run_id"],
        "final_configuration_id": artifact["configuration_id"], "artifact_id": artifact_id,
        "artifact_manifest_sha256": authorization["artifact_manifest_sha256"],
        "model_safetensors_sha256": sha256(model_dir / "model.safetensors"),
        "model_export_directory": str(model_dir),
        "selected_config_sha256": authorization["selected_config_sha256"],
        "test_csv_sha256": authorization["test_csv_sha256"],
        "assignments_sha256": authorization["assignments_sha256"],
        "threshold": pipeline.threshold, "class_order": ["Not Scam", "Scam"],
        "positive_class": "Scam", "metrics_denominator": "successful predictions only",
        "completion_rate_denominator": "all assigned test records",
        "authorization_reference": authorization["reference"], "reviewer": authorization["reviewer"],
        "selection_completion_sha256": authorization["selection_completion_sha256"],
        "evaluation_elapsed_seconds_sum_of_record_times": sum(float(r.get("elapsed_seconds") or 0) for r in outcomes),
        "environment": environment_metadata(pipeline),
    })
    environment = environment_metadata(pipeline)
    protocol = {
        "status": "executed_under_owner_authorization",
        "selection": str(selected_path), "selection_sha256": sha256(selected_path),
        "training_run_id": artifact["run_id"], "inference_artifact": str(model_dir),
        "model_safetensors_sha256": sha256(model_dir / "model.safetensors"),
        "artifact_manifest_sha256": authorization["artifact_manifest_sha256"],
        "preprocessing_config_sha256": sha256(Path(args.preprocessing_config).resolve()),
        "test_csv_sha256": authorization["test_csv_sha256"], "assignments_sha256": authorization["assignments_sha256"],
        "threshold": pipeline.threshold, "training_representation": "whole_conversation_role_marked",
        "inference_representation": "whole_conversation_role_free", "validation_checkpoint_selection": "none_in_final_training",
        "authorization_reference": authorization["reference"],
        "selection_completion_sha256": authorization["selection_completion_sha256"],
        "environment": environment,
        "evaluation_elapsed_seconds_sum_of_record_times": metrics["evaluation_elapsed_seconds_sum_of_record_times"],
    }
    protocol_text = "# Final evaluation protocol\n\n```json\n" + json.dumps(protocol, ensure_ascii=False, indent=2, allow_nan=False) + "\n```\n"
    report_text_path = Path(tempfile.gettempdir()) / f"scam-evaluation-report-{uuid.uuid4().hex}.md"
    write_evaluation_report(report_text_path, metrics, len(errors))
    with tempfile.TemporaryDirectory(prefix="scam-evaluation-publish-", dir=output_dir) as stage_name:
        stage = Path(stage_name)
        write_csv(stage / "test_predictions.csv", fields, outcomes)
        write_csv(stage / "error_analysis.csv", error_fields, errors)
        write_json(stage / "metrics.json", metrics)
        (stage / "evaluation_protocol.md").write_text(protocol_text, encoding="utf-8")
        (stage / "evaluation_report.md").write_text(report_text_path.read_text(encoding="utf-8"), encoding="utf-8")
        report_text_path.unlink(missing_ok=True)
        sys.path.insert(0, str(FINAL_DIR))
        import review_results
        review_results.figures(metrics, stage / "figures")
        staged_artifacts = {name: stage / name for name in output_names}
        for figure in sorted((stage / "figures").iterdir()):
            staged_artifacts[str(figure.relative_to(stage))] = figure
        staged_artifacts["evaluation_events.jsonl"] = journal_path
        file_hashes = atomic_publish(output_dir, staged_artifacts)
    marker = {
        "schema_version": 1,
        "status": "artifacts_complete_pending_error_review" if errors else "artifacts_complete_no_errors",
        "evaluation_id": authorization["evaluation_id"], "final_run_id": artifact["run_id"],
        "artifact_id": artifact_id, "selected_config_sha256": sha256(selected_path),
        "selection_completion_sha256": authorization["selection_completion_sha256"],
        "artifact_manifest_sha256": authorization["artifact_manifest_sha256"],
        "model_safetensors_sha256": sha256(model_dir / "model.safetensors"),
        "test_csv_sha256": authorization["test_csv_sha256"], "assignments_sha256": authorization["assignments_sha256"],
        "assigned_prediction_count": len(outcomes),
        "failed_execution_count": sum(r["execution_state"] != "success" for r in outcomes),
        "pending_error_review_count": sum(r.get("review_status") != "reviewed" for r in errors),
        "files_sha256": file_hashes,
    }
    marker_tmp = output_dir / f"evaluation_complete.{uuid.uuid4().hex}.tmp"
    write_json(marker_tmp, marker)
    os.replace(marker_tmp, completion_marker)
    print(f"Saved authorized final evaluation: {output_dir}")


def compute_metrics(outcomes: list[dict[str, Any]]) -> dict[str, Any]:
    def one(rows: list[dict[str, Any]]) -> dict[str, Any]:
        assigned = len(rows)
        succeeded = [row for row in rows if row["execution_state"] == "success"]
        failed = [row for row in rows if row["execution_state"] != "success"]
        truth = [LABELS[row["true_label"]] for row in succeeded]
        pred = [LABELS[row["predicted_label"]] for row in succeeded]
        tn = sum(t == 0 and p == 0 for t, p in zip(truth, pred))
        fp = sum(t == 0 and p == 1 for t, p in zip(truth, pred))
        fn = sum(t == 1 and p == 0 for t, p in zip(truth, pred))
        tp = sum(t == 1 and p == 1 for t, p in zip(truth, pred))
        flags = []
        def ratio(n: int, d: int, name: str) -> float | None:
            if d:
                return n / d
            if succeeded:
                flags.append(name + "_undefined_denominator_zero")
                return 0.0
            return None
        precision = ratio(tp, tp + fp, "scam_precision")
        recall = ratio(tp, tp + fn, "scam_recall")
        f1 = ratio(2 * tp, 2 * tp + fp + fn, "scam_f1")
        not_f1 = ratio(2 * tn, 2 * tn + fp + fn, "not_scam_f1")
        accuracy = ratio(tp + tn, len(succeeded), "accuracy")
        macro = (f1 + not_f1) / 2 if succeeded else None
        reasons: defaultdict[str, int] = defaultdict(int)
        for row in failed:
            reasons[row.get("failure_reason", "unspecified") or "unspecified"] += 1
        return {
            "assigned": assigned, "successful": len(succeeded), "failed": len(failed),
            "completion_rate": len(succeeded) / assigned if assigned else None,
            "assigned_true_not_scam": sum(row["true_label"] == "Not Scam" for row in rows),
            "assigned_true_scam": sum(row["true_label"] == "Scam" for row in rows),
            "successful_true_not_scam": sum(row["true_label"] == "Not Scam" for row in succeeded),
            "successful_true_scam": sum(row["true_label"] == "Scam" for row in succeeded),
            "tn": tn, "fp": fp, "fn": fn, "tp": tp,
            "scam_precision": precision, "scam_recall": recall, "scam_f1": f1,
            "macro_f1": macro, "accuracy": accuracy,
            "undefined_metric_flags": flags, "failures_by_reason": dict(sorted(reasons.items())),
        }
    result = {"combined": one(outcomes), "by_source": {}}
    for source in SOURCES:
        result["by_source"][source] = one([row for row in outcomes if row["source_dataset"] == source])
    return result


def write_evaluation_report(path: Path, metrics: dict[str, Any], error_count: int) -> None:
    lines = [
        "# Final text evaluation",
        "",
        "> Final test metrics are reported only for this authorized run and frozen artifact. They do not estimate real-call accuracy or end-to-end audio performance.",
        "",
        f"- Evaluation ID: `{metrics['evaluation_id']}`",
        f"- Final run: `{metrics['final_run_id']}`",
        f"- Artifact ID: `{metrics['artifact_id']}`",
        f"- Threshold: `{metrics['threshold']}` (Scam probability ≥ threshold predicts Scam)",
        f"- Authorization: `{metrics['authorization_reference']}`",
        "",
        "Metrics use successful predictions only; assigned/success/failed counts and completion rate use all assigned records. Confusion-matrix order is [Not Scam, Scam], with true labels in rows.",
        "",
        "| Scope | Assigned | Success | Failed | Completion | Scam precision | Scam recall | Scam F1 | Macro-F1 | Accuracy | TN | FP | FN | TP |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for scope, row in [("Combined", metrics["combined"]), *[(name, value) for name, value in metrics["by_source"].items()]]:
        def fmt(value): return "—" if value is None else f"{value:.4f}"
        lines.append(f"| {scope} | {row['assigned']} | {row['successful']} | {row['failed']} | {fmt(row['completion_rate'])} | {fmt(row['scam_precision'])} | {fmt(row['scam_recall'])} | {fmt(row['scam_f1'])} | {fmt(row['macro_f1'])} | {fmt(row['accuracy'])} | {row['tn']} | {row['fp']} | {row['fn']} | {row['tp']} |")
    lines.extend([
        "", "Confusion-matrix figures: `figures/confusion_matrix_combined.png` and `figures/confusion_matrix_combined.pdf` (plus source-specific versions).",
        "", f"Every false positive and false negative is represented in `error_analysis.csv` ({error_count} records). Review fields are initially pending and must be completed by a human before Plan 03/02 is declared complete.",
        "", "Execution failures are not classification errors and remain visible in `test_predictions.csv` and failure-reason counts.",
        "", "CV fold mean ± sample SD are development evidence; they are not confidence intervals around this single final-test score.", "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    draft = sub.add_parser("draft-approval", help="prefill known identities in an explicitly unapproved approval template")
    draft.add_argument("--kind", choices=("final-training", "test-execution"), required=True)
    draft.add_argument("--selected-config", default=str(ROOT / "03 - MODEL DEVELOPMENT/selection/selected_config.json"))
    draft.add_argument("--completion-record", default=str(ROOT / "03 - MODEL DEVELOPMENT/selection/selection_completion.json"))
    draft.add_argument("--cv-run-config", help="required for final-training drafts")
    draft.add_argument("--final-run-id", help="required for final-training drafts")
    draft.add_argument("--persistent-runs", help="required for final-training drafts")
    draft.add_argument("--assignments", default=str(ROOT / "02 - DATASETs/prepared/splits/split_assignments.csv"))
    draft.add_argument("--training-csv", default=str(ROOT / "02 - DATASETs/prepared/splits/0 - train/dataset.csv"))
    draft.add_argument("--model-dir", help="required for test-execution drafts")
    draft.add_argument("--preprocessing-config", default=str(INPUT_DIR / "preprocessing_config.json"))
    draft.add_argument("--output-location", help="owner-chosen persistent evaluation directory")
    draft.add_argument("--output", required=True)
    draft.set_defaults(func=draft_approval)
    make_cfg = sub.add_parser("prepare-final-config", help="derive a fresh no-validation config using an owner-approved final warmup")
    make_cfg.add_argument("--selected-config", default=str(ROOT / "03 - MODEL DEVELOPMENT/selection/selected_config.json"))
    make_cfg.add_argument("--cv-run-config", required=True)
    make_cfg.add_argument("--final-training-approval", required=True)
    make_cfg.add_argument("--completion-record", default=str(ROOT / "03 - MODEL DEVELOPMENT/selection/selection_completion.json"))
    make_cfg.add_argument("--assignments", default=str(ROOT / "02 - DATASETs/prepared/splits/split_assignments.csv"))
    make_cfg.add_argument("--training-csv", default=str(ROOT / "02 - DATASETs/prepared/splits/0 - train/dataset.csv"))
    make_cfg.add_argument("--output", required=True)
    make_cfg.add_argument("--print-settings-digest", action="store_true",
                          help="print the computed settings digest without writing a launchable config; use with a draft approval record")
    make_cfg.set_defaults(func=prepare_final_training_config)
    train = sub.add_parser("train-final", help="launch the approved training engine in final_training mode")
    train.add_argument("--config", required=True)
    train.add_argument("--authorized-final-training", action="store_true")
    train.set_defaults(func=launch_final_training)
    infer = sub.add_parser("infer-test", help="owner-gated text-test inference on the frozen safetensors export")
    infer.add_argument("--selected-config", default=str(ROOT / "03 - MODEL DEVELOPMENT/selection/selected_config.json"))
    infer.add_argument("--model-dir", required=True)
    infer.add_argument("--preprocessing-config", default=str(INPUT_DIR / "preprocessing_config.json"))
    infer.add_argument("--assignments", default=str(ROOT / "02 - DATASETs/prepared/splits/split_assignments.csv"))
    infer.add_argument("--test-csv", default=str(ROOT / "02 - DATASETs/prepared/splits/1 - test/dataset.csv"))
    infer.add_argument("--authorization", required=True)
    infer.add_argument("--authorized-test-execution", action="store_true")
    infer.add_argument("--output-dir", default=str(FINAL_DIR))
    infer.set_defaults(func=infer_test)
    return p


if __name__ == "__main__":
    parsed = parser().parse_args()
    parsed.func(parsed)
