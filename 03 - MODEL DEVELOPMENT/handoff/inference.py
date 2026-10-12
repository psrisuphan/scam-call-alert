"""Local inference component for the frozen Scam Call Alert text classifier.

Model construction is injected so the handoff layer does not choose a backend
or duplicate the four-candidate model factory. Text is prepared only through
the shared Plan 02 ``inputs.prepare_text`` and ``inputs.pad_batch`` functions.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
import shutil
import re


ERRORS = {
    "E_INVALID_REQUEST": "Request must contain exactly request_id and transcript.",
    "E_TRANSCRIPT_INVALID": "Transcript must be nonempty text.",
    "E_MODEL_UNAVAILABLE": "The frozen model bundle is unavailable.",
    "E_PREPROCESSING_FAILED": "Transcript could not be prepared under the frozen policy.",
    "E_INFERENCE_FAILED": "Model inference failed.",
    "E_INVALID_OUTPUT": "Model returned invalid class scores.",
}
LABELS = ("Not Scam", "Scam")
THRESHOLD = 0.5


def _shared_inputs_module():
    input_dir = Path(__file__).resolve().parents[1] / "input-preparation"
    if str(input_dir) not in sys.path:
        sys.path.insert(0, str(input_dir))
    import inputs  # imported here so the handoff remains usable as a standalone script
    return inputs


def _response(request_id, model_version, status, label=None, probabilities=None,
              threshold=None, warnings=None, error=None):
    return {
        "request_id": request_id,
        "model_version": model_version,
        "status": status,
        "label": label,
        "probabilities": probabilities,
        "threshold": threshold,
        "warnings": [] if warnings is None else warnings,
        "error": error,
    }


def serve_jsonl(service, input_stream, output_stream):
    """Serve one JSON request/response per line for a local development client."""
    for line in input_stream:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            request = None
        output_stream.write(json.dumps(service.predict(request), ensure_ascii=False) + "\n")
        output_stream.flush()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local Scam Call Alert JSONL inference")
    parser.add_argument("--bundle", required=True, help="Validated frozen bundle directory")
    parser.add_argument("--device", default="cpu", help="Backend device, such as cpu or cuda:0")
    args = parser.parse_args(argv)
    try:
        service = load_local_bundle(args.bundle, device=args.device)
    except Exception:
        # Continue serving contract-shaped failures; never fall back to another model.
        service = LocalClassifier(None, None, {}, model_key="unavailable", model_version=None)
    serve_jsonl(service, sys.stdin, sys.stdout)


def _valid_request_id(value):
    return isinstance(value, str) and bool(value.strip())


def load_local_bundle(bundle_dir, *, device="cpu"):
    """Load the exact evaluated export using the shared model/input loaders.

    The native pre-evaluation ``final_model/`` directory is copied byte-for-byte.
    Its internal manifest is verified by the training artifact loader. The
    pinned tokenizer revision must already be cached locally; model weights are
    loaded from the bundled evaluated artifact without serialization/download.
    """
    from bundle_manifest import manifest_identity, validate_manifest
    bundle_arg = Path(bundle_dir)
    if bundle_arg.is_symlink():
        raise ValueError("Bundle directory may not be a symlink")
    root = bundle_arg.resolve()
    manifest_path = root / "artifact_manifest.json"
    if manifest_path.is_symlink():
        raise ValueError("Bundle manifest may not be a symlink")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = validate_manifest(root, manifest)
    if errors:
        raise ValueError("Invalid model bundle: " + "; ".join(errors))
    identity = manifest["identity"]
    if manifest.get("bundle_status") != "ready_for_parity" or not identity.get("evaluation_identity"):
        raise ValueError("Bundle is not bound to a final evaluated artifact identity")
    config_path = root / identity["preprocessing_config_path"]
    if hashlib.sha256(config_path.read_bytes()).hexdigest() != identity["preprocessing_config_sha256"]:
        raise ValueError("Frozen preprocessing configuration checksum mismatch")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    candidate = identity["candidate"]
    entry = config.get("models", {}).get(candidate)
    if not entry or entry.get("checkpoint") != identity["checkpoint"] or entry.get("revision") != identity["revision"]:
        raise ValueError("Bundle checkpoint identity differs from the frozen input configuration")
    if identity["tokenizer_revision"] != entry["revision"]:
        raise ValueError("Tokenizer revision differs from the frozen checkpoint revision")
    if Path(identity["weights_path"]).name != "model.safetensors":
        raise ValueError("The bundle must copy the exact pre-evaluation model.safetensors artifact")
    model_config_path = root / identity["model_config_path"]
    model_config = json.loads(model_config_path.read_text(encoding="utf-8"))
    if model_config.get("num_labels") not in (None, 2):
        raise ValueError("Evaluated model configuration must contain exactly two labels")
    if model_config.get("id2label") not in ({"0": "Not Scam", "1": "Scam"}, {0: "Not Scam", 1: "Scam"}):
        raise ValueError("Evaluated model configuration label order mismatch")
    if model_config.get("label2id") != {"Not Scam": 0, "Scam": 1}:
        raise ValueError("Evaluated model configuration inverse label map mismatch")

    training_dir = Path(__file__).resolve().parents[1] / "training"
    if str(training_dir) not in sys.path:
        sys.path.insert(0, str(training_dir))
    from trainer import load_model_for_inference
    model_dir = root / identity["model_directory"]
    model, model_manifest = load_model_for_inference(model_dir)
    expected_code_revision = model_manifest.get("custom_code_revision") or model_manifest.get("checkpoint_revision")
    if (model_manifest.get("model") != candidate
            or model_manifest.get("checkpoint_id") != identity["checkpoint"]
            or model_manifest.get("checkpoint_revision") != identity["revision"]
            or model_manifest.get("preprocessing_config_sha256") != identity["preprocessing_config_sha256"]
            or expected_code_revision != identity["model_code_revision"]):
        raise ValueError("Native evaluated model manifest differs from the handoff identity")
    if getattr(model.config, "num_labels", None) != 2:
        raise ValueError("Loaded model does not expose exactly two scores")
    # The bundle is self-contained: load the exact tokenizer assets copied
    # alongside the evaluated weights, never the original checkpoint cache.
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True,
        trust_remote_code=False, token=False, use_fast=True)
    tokenizer_entry = config["models"][candidate]
    if (type(tokenizer).__name__ != tokenizer_entry["tokenizer_class"]
            or tokenizer.pad_token_id != tokenizer_entry["pad_token_id"]
            or tokenizer.padding_side != tokenizer_entry["padding_side"]
            or tokenizer.truncation_side != config["truncation_side"]
            or tokenizer.num_special_tokens_to_add() != tokenizer_entry["special_tokens_count"]):
        raise ValueError("Bundled tokenizer differs from the approved tokenizer contract")
    # Some approved Camembert checkpoints include an unused embedding row.
    # Require every actual tokenizer ID to fit the unchanged evaluated model,
    # rather than equating the vocabulary-entry count with embedding rows.
    vocabulary_ids = list(tokenizer.get_vocab().values())
    if (not vocabulary_ids or min(vocabulary_ids) < 0
            or max(vocabulary_ids) >= int(model.config.vocab_size)):
        raise ValueError("Bundled tokenizer IDs exceed the evaluated model embeddings")
    component_path = root / identity["input_component_path"]
    component_digest = hashlib.sha256(component_path.read_bytes()).hexdigest()
    if component_digest != identity["input_component_sha256"]:
        raise ValueError("Bundled input-preparation implementation checksum mismatch")
    module_name = f"scam_bundle_inputs_{component_digest}"
    spec = importlib.util.spec_from_file_location(module_name, component_path)
    if spec is None or spec.loader is None:
        raise ValueError("Could not load the frozen bundled input-preparation implementation")
    frozen_inputs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(frozen_inputs)
    tokenizer._scam_checkpoint_identity = (entry["checkpoint"], entry["revision"])
    tokenizer._scam_added_token_identity = frozen_inputs.added_token_identity(tokenizer)
    return LocalClassifier(model, tokenizer, config, model_key=candidate,
                           model_version=manifest_identity(manifest), device=device,
                           prepare_text_fn=frozen_inputs.prepare_text,
                           pad_batch_fn=frozen_inputs.pad_batch,
                           checkpoint_prepare_fn=frozen_inputs.checkpoint_prepare_text)


def _evaluation_protocol(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    matches = re.findall(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if len(matches) != 1:
        raise ValueError("Final evaluation protocol must contain exactly one JSON evidence block")
    value = json.loads(matches[0])
    if not isinstance(value, dict):
        raise ValueError("Final evaluation protocol evidence must be a JSON object")
    return value


def evaluation_identity_from_directory(evaluation_dir, model_dir, *, preprocessing_config_source,
                                      review_audit_path):
    """Derive bundle provenance from completed final-evaluation records.

    This consumes only the evaluation's metrics, protocol and human-readable
    report plus the native model/config artifacts. It does not read prediction
    rows or any test transcript.
    """
    from bundle_manifest import _CompletedEvaluationEvidence, sha256_file
    training_dir = Path(__file__).resolve().parents[1] / "training"
    if str(training_dir) not in sys.path:
        sys.path.insert(0, str(training_dir))
    import trainer
    verify_model_artifact = trainer.verify_model_artifact
    root = Path(evaluation_dir)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("A completed final-evaluation directory is required")
    model_root = Path(model_dir)
    metrics_path = root / "metrics.json"
    protocol_path = root / "evaluation_protocol.md"
    report_path = root / "evaluation_report.md"
    predictions_path = root / "test_predictions.csv"
    errors_path = root / "error_analysis.csv"
    journal_path = root / "evaluation_events.jsonl"
    completion_path = root / "evaluation_complete.json"
    audit_path = Path(review_audit_path)
    required = (metrics_path, protocol_path, report_path, predictions_path, errors_path,
                journal_path, completion_path, audit_path)
    if any(path.is_symlink() or not path.is_file() for path in required):
        raise ValueError("Final evaluation outputs, completion marker and completed review audit must be present regular files")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    protocol = _evaluation_protocol(protocol_path)
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    review_audit = json.loads(audit_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")
    native = verify_model_artifact(model_root)
    weights = model_root / "model.safetensors"
    native_manifest_path = model_root / "artifact_manifest.json"
    selected_path = Path(protocol.get("selection", ""))
    prep_path = Path(preprocessing_config_source)
    if selected_path.is_symlink() or not selected_path.is_file() or prep_path.is_symlink() or not prep_path.is_file():
        raise ValueError("Evaluation must reference existing selected and preprocessing configs")
    selected = json.loads(selected_path.read_text(encoding="utf-8"))
    selected_sha = sha256_file(selected_path)
    prep_sha = sha256_file(prep_path)
    weights_sha = sha256_file(weights)
    native_manifest_sha = sha256_file(native_manifest_path)
    artifact_id = f"{native['run_id']}:{native_manifest_sha}"
    final_training_path = model_root.parent / "run_config.json"
    final_summary_path = model_root.parent / "run_summary.json"
    if not final_training_path.is_file() or not final_summary_path.is_file():
        raise ValueError("Evaluated model must remain beside its completed final-training config and summary")
    final_training = json.loads(final_training_path.read_text(encoding="utf-8"))
    final_summary = json.loads(final_summary_path.read_text(encoding="utf-8"))
    if trainer.configuration_id(final_training) != native.get("configuration_id"):
        raise ValueError("Final-training configuration does not reproduce the native artifact configuration ID")
    workspace_input_component = Path(__file__).resolve().parents[1] / "input-preparation" / "inputs.py"
    expected_input_component_sha = final_training.get("identities", {}).get("input_component_sha256")
    if (not isinstance(expected_input_component_sha, str)
            or sha256_file(workspace_input_component) != expected_input_component_sha):
        raise ValueError("Current shared input-preparation code differs from the implementation used in final training")
    selection = final_training.get("selection", {})
    if (final_training.get("mode") != "final_training"
            or final_training.get("run_id") != native.get("run_id")
            or final_training.get("configuration_id") != native.get("configuration_id")
            or final_summary.get("status") != "completed"
            or final_summary.get("epochs_completed", 0) != selected.get("selected_duration_epochs")):
        raise ValueError("Native artifact is not from the completed selected final-training run")
    if (selection.get("selected_config_sha256") != selected_sha
            or selection.get("selected_configuration_id") != selected.get("configuration_id")):
        raise ValueError("Final-training config does not bind the exact human-frozen selection")
    selection_completion_path = Path(selection.get("selection_completion_path", ""))
    recorded_completion_sha = selection.get("selection_completion_sha256")
    default_path = MODEL_ROOT / "selection/selection_completion.json"
    if not selection_completion_path.is_file() and default_path.is_file():
        selection_completion_path = default_path
    if not selection_completion_path.is_file() or selection_completion_path.is_symlink():
        raise ValueError("Selection-completion artifact is missing or a symlink")
    if recorded_completion_sha and recorded_completion_sha != sha256_file(selection_completion_path):
        raise ValueError("Final-training run is not bound to the verified selection-completion artifact")
    selection_completion = json.loads(selection_completion_path.read_text(encoding="utf-8"))
    scope = selection_completion.get("scope_approval", {})
    if (selection_completion.get("status") != "complete_verified"
            or selection_completion.get("selected_config_sha256") != selected_sha
            or selection_completion.get("main_fit_count") != 45
            or selection_completion.get("excluded_main_fit_count") != 30
            or selection_completion.get("caller_only_fit_count") != 0
            or selection_completion.get("supplemental_fit_count") != 0
            or scope.get("status") != "owner_approved"
            or not scope.get("reference")):
        raise ValueError("Selection-completion artifact does not verify the complete approved comparison matrix")
    selection_completion_sha = sha256_file(selection_completion_path)
    checkpoint = final_training.get("checkpoint", {})
    training = final_training.get("training", {})
    if (final_training.get("model") != selected.get("model_key")
            or checkpoint.get("id") != selected.get("checkpoint")
            or checkpoint.get("revision") != selected.get("checkpoint_revision")
            or final_training.get("data", {}).get("condition") != selected.get("data_condition")
            or final_training.get("optimizer", {}).get("learning_rate") != selected.get("learning_rate")
            or training.get("epochs") != selected.get("selected_duration_epochs")
            or training.get("seed") != selected.get("training_seed")
            or training.get("representation") != selected.get("training_representation")
            or training.get("marker_condition") != selected.get("training_marker_condition")
            or final_training.get("validation") not in (None, {"enabled": False})
            or final_training.get("identities", {}).get("preprocessing_config_sha256") != prep_sha
            or final_training.get("identities", {}).get("assignments_sha256") != native.get("assignments_sha256")):
        raise ValueError("Final-training config differs from the frozen candidate or native artifact provenance")
    marker_status = completion.get("status")
    if marker_status not in {"artifacts_complete_pending_error_review", "artifacts_complete_no_errors"}:
        raise ValueError("Final evaluation completion marker does not attest completed output coverage")
    if (completion.get("final_run_id") != native.get("run_id")
            or completion.get("artifact_id") != artifact_id
            or completion.get("model_safetensors_sha256") != weights_sha
            or completion.get("artifact_manifest_sha256") != native_manifest_sha):
        raise ValueError("Finalization marker does not identify the exact native evaluated artifact")
    for filename, path in (("metrics.json", metrics_path), ("evaluation_protocol.md", protocol_path),
                           ("evaluation_report.md", report_path), ("test_predictions.csv", predictions_path),
                           ("error_analysis.csv", errors_path), ("evaluation_events.jsonl", journal_path)):
        if completion.get("files_sha256", {}).get(filename) != sha256_file(path):
            raise ValueError(f"Finalization marker checksum mismatch: {filename}")
    if protocol.get("status") != "executed_under_owner_authorization":
        raise ValueError("Final evaluation protocol is not marked as executed under owner authorization")
    if protocol.get("training_run_id") != native.get("run_id"):
        raise ValueError("Final evaluation run does not match the native model artifact")
    if protocol.get("inference_artifact") != str(model_root.resolve()):
        raise ValueError("Final evaluation protocol does not identify this exact native model directory")
    if protocol.get("selection_sha256") != selected_sha or metrics.get("selected_config_sha256") != selected_sha:
        raise ValueError("Final evaluation selected-config checksum does not match its source file")
    if (protocol.get("selection_completion_sha256") != selection_completion_sha
            or completion.get("selection_completion_sha256") != selection_completion_sha):
        raise ValueError("Final evaluation does not bind the verified selection-completion artifact")
    if protocol.get("preprocessing_config_sha256") != prep_sha:
        raise ValueError("Final evaluation preprocessing checksum does not match its source file")
    if (protocol.get("model_safetensors_sha256") != weights_sha
            or metrics.get("model_safetensors_sha256") != weights_sha):
        raise ValueError("Final evaluation does not bind the exact native model weights")
    if protocol.get("artifact_manifest_sha256") != native_manifest_sha:
        raise ValueError("Final evaluation does not bind the native model manifest")
    if metrics.get("artifact_id") != artifact_id:
        raise ValueError("Final evaluation artifact identity differs from native manifest identity")
    if (metrics.get("final_run_id") != native.get("run_id")
            or metrics.get("final_configuration_id") != native.get("configuration_id")):
        raise ValueError("Final evaluation run/configuration identity differs from the native artifact")
    if (selected.get("status") != "frozen_by_human_approval"
            or selected.get("model_key") != native.get("model")
            or selected.get("checkpoint") != native.get("checkpoint_id")
            or selected.get("checkpoint_revision") != native.get("checkpoint_revision")):
        raise ValueError("Final evaluation selected config does not authorize this candidate/checkpoint")
    if metrics.get("threshold") != 0.5 or protocol.get("threshold") != 0.5:
        raise ValueError("Final evaluation threshold must match the frozen 0.5 threshold")
    auth = protocol.get("authorization_reference")
    if not isinstance(auth, str) or not auth or metrics.get("authorization_reference") != auth:
        raise ValueError("Final evaluation authorization reference is missing or inconsistent")
    if not metrics.get("evaluation_id") or not metrics.get("combined"):
        raise ValueError("Final evaluation metrics are incomplete or unbound to the protocol")
    if (completion.get("evaluation_id") != metrics.get("evaluation_id")
            or completion.get("selected_config_sha256") != selected_sha
            or completion.get("test_csv_sha256") != metrics.get("test_csv_sha256")
            or completion.get("assignments_sha256") != metrics.get("assignments_sha256")
            or protocol.get("test_csv_sha256") != metrics.get("test_csv_sha256")
            or protocol.get("assignments_sha256") != metrics.get("assignments_sha256")):
        raise ValueError("Final evaluation completion/data identity differs from metrics or protocol")
    if (completion.get("assigned_prediction_count") != metrics["combined"].get("assigned")
            or completion.get("failed_execution_count") != metrics["combined"].get("failed")):
        raise ValueError("Finalization marker coverage counts differ from metrics")
    # The independent review audit binds and recomputes the original saved
    # prediction/error evidence; only aggregate JSON is read here, never test text.
    source_hashes = review_audit.get("source_sha256", {})
    source_files = review_audit.get("source_files", {})
    expected_prediction_sha = sha256_file(predictions_path)
    expected_error_sha = sha256_file(errors_path)
    if (not any(Path(source).name == predictions_path.name and digest == expected_prediction_sha
                for source, digest in source_hashes.items())
            or not any(Path(source).name == errors_path.name and digest == expected_error_sha
                       for source, digest in source_hashes.items())):
        raise ValueError("Review audit does not bind the original prediction and error files")
    original_error_path = Path(source_files.get("original_errors", ""))
    reviewed_error_path = Path(source_files.get("reviewed_errors", ""))
    audited_prediction_path = Path(source_files.get("predictions", ""))
    assignments_path = Path(source_files.get("assignments", ""))
    if (not original_error_path.is_file() or original_error_path.resolve() != errors_path.resolve()
            or not reviewed_error_path.is_file() or reviewed_error_path.resolve() == errors_path.resolve()
            or not audited_prediction_path.is_file() or audited_prediction_path.resolve() != predictions_path.resolve()
            or not assignments_path.is_file()):
        raise ValueError("Review audit must identify the original errors, reviewed copy and assignment metadata")
    reviewed_error_sha = source_hashes.get(str(reviewed_error_path.resolve()))
    assignment_sha = source_hashes.get(str(assignments_path.resolve()))
    if (not reviewed_error_sha or reviewed_error_sha != sha256_file(reviewed_error_path)
            or not assignment_sha or assignment_sha != protocol.get("assignments_sha256")):
        raise ValueError("Review audit copy or assignment provenance checksum mismatch")
    if (review_audit.get("coverage_verified") is not True
            or review_audit.get("error_review_complete") is not True
            or review_audit.get("pending_error_reviews")
            or review_audit.get("assigned") != metrics["combined"].get("assigned")
            or review_audit.get("failed") != metrics["combined"].get("failed")):
        raise ValueError("Final evaluation requires complete coverage and documented review of every classification error before release")
    if (completion.get("pending_error_review_count") != review_audit.get("classification_errors")
            or completion.get("status") != ("artifacts_complete_no_errors" if review_audit.get("classification_errors") == 0
                                              else "artifacts_complete_pending_error_review")):
        raise ValueError("Review audit does not reconcile with the original finalization error count")
    audited_metrics = review_audit.get("metrics", {})
    if audited_metrics.get("combined") != metrics.get("combined") or audited_metrics.get("by_source") != metrics.get("by_source"):
        raise ValueError("Reviewed recomputed metrics do not match the final metrics record")
    for text in (f"- Evaluation ID: `{metrics['evaluation_id']}`",
                 f"- Final run: `{native['run_id']}`", f"- Artifact ID: `{artifact_id}`",
                 "- Threshold: `0.5`", f"- Authorization: `{auth}`"):
        if text not in report:
            raise ValueError("Final evaluation report does not match its metrics/protocol identity")
    if int(metrics["combined"].get("assigned", 0)) <= 0:
        raise ValueError("Final evaluation has no assigned records")
    identity = {"artifact_id": artifact_id, "weights_sha256": weights_sha,
            "selected_config_sha256": selected_sha,
            "final_evaluation_report_sha256": sha256_file(report_path),
            "evaluation_protocol_sha256": sha256_file(protocol_path),
            "metrics_sha256": sha256_file(metrics_path),
            "completion_marker_sha256": sha256_file(completion_path),
            "review_audit_sha256": sha256_file(audit_path),
            "reviewed_errors_sha256": reviewed_error_sha,
            "input_component_sha256": expected_input_component_sha,
            "native_artifact_manifest_sha256": native_manifest_sha,
            "evaluation_id": metrics["evaluation_id"],
            "authorization_reference": auth}
    return _CompletedEvaluationEvidence(identity)


def assemble_bundle(source_model_dir, bundle_dir, identity, *, preprocessing_config_source,
                    evaluation_dir, review_audit_path):
    """Copy the exact verified native final export and create a handoff manifest.

    The source directory is the final-training ``final_model/`` output before
    final test evaluation. The caller supplies reviewed evaluation identities
    and the full list of required bundle files is derived after exact copying.
    Destination must not already exist; no model serialization is performed.
    """
    from bundle_manifest import build_manifest, sha256_file, write_manifest
    source_arg = Path(source_model_dir)
    destination_arg = Path(bundle_dir)
    if source_arg.is_symlink() or destination_arg.is_symlink():
        raise ValueError("Model source and bundle destination may not be symlinks")
    source = source_arg.resolve()
    destination = destination_arg.resolve()
    if destination.exists():
        raise FileExistsError(f"Refusing to replace existing bundle path: {destination}")
    model_directory = identity.get("model_directory")
    config_path = identity.get("preprocessing_config_path")
    if not isinstance(model_directory, str) or not model_directory or not isinstance(config_path, str) or not config_path:
        raise ValueError("Identity must provide model_directory and preprocessing_config_path")
    model_rel = Path(model_directory)
    config_rel = Path(config_path)
    if model_rel.is_absolute() or ".." in model_rel.parts or config_rel.is_absolute() or ".." in config_rel.parts:
        raise ValueError("Bundle paths must be relative and remain inside the bundle")
    training_dir = Path(__file__).resolve().parents[1] / "training"
    if str(training_dir) not in sys.path:
        sys.path.insert(0, str(training_dir))
    from trainer import verify_model_artifact
    model_manifest = verify_model_artifact(source)
    evaluation = evaluation_identity_from_directory(evaluation_dir, source,
        preprocessing_config_source=preprocessing_config_source,
        review_audit_path=review_audit_path)
    component_sha = evaluation.identity["input_component_sha256"]
    component_rel = identity.get("input_component_path", "runtime/inputs.py")
    if component_rel != "runtime/inputs.py":
        raise ValueError("Frozen shared input-preparation implementation must be stored at runtime/inputs.py")
    if identity.get("input_component_sha256") not in (None, component_sha):
        raise ValueError("Caller input-preparation checksum differs from final-training provenance")
    identity = {**identity, "evaluation_identity": evaluation.identity,
                "input_component_path": component_rel, "input_component_sha256": component_sha}
    if (model_manifest.get("model") != identity.get("candidate")
            or model_manifest.get("checkpoint_id") != identity.get("checkpoint")
            or model_manifest.get("checkpoint_revision") != identity.get("revision")
            or model_manifest.get("preprocessing_config_sha256") != identity.get("preprocessing_config_sha256")):
        raise ValueError("Source final-model artifact differs from supplied candidate/config identity")
    expected_code = model_manifest.get("custom_code_revision") or model_manifest.get("checkpoint_revision")
    if expected_code != identity.get("model_code_revision"):
        raise ValueError("Source final-model code revision differs from supplied identity")

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.parent / (destination.name + ".staging")
    if staging.exists():
        raise FileExistsError(f"Refusing to replace staging directory: {staging}")
    staging.mkdir()
    try:
        copied_model = staging / model_rel
        copied_model.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, copied_model, copy_function=shutil.copy2)
        source_config_arg = Path(preprocessing_config_source)
        if source_config_arg.is_symlink():
            raise ValueError("Preprocessing config source may not be a symlink")
        source_config = source_config_arg.resolve()
        if not source_config.is_file() or sha256_file(source_config) != identity["preprocessing_config_sha256"]:
            raise ValueError("Approved preprocessing configuration source/checksum mismatch")
        copied_config = staging / config_rel
        copied_config.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_config, copied_config)
        component_source = Path(__file__).resolve().parents[1] / "input-preparation" / "inputs.py"
        if sha256_file(component_source) != component_sha:
            raise ValueError("Shared input-preparation implementation changed during bundle assembly")
        copied_component = staging / component_rel
        copied_component.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(component_source, copied_component)
        files = [path.relative_to(staging).as_posix() for path in staging.rglob("*") if path.is_file()]
        manifest = build_manifest(staging, identity, files, completed_evaluation=evaluation)
        write_manifest(staging, manifest)
        destination.parent.mkdir(parents=True, exist_ok=True)
        staging.rename(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return destination


class LocalClassifier:
    """Classify role-free chronological transcript text under the frozen contract.

    ``model`` and ``tokenizer`` are the already-loaded evaluated artifacts.
    The owning model factory supplies these; this class never downloads or
    substitutes a checkpoint. ``device`` may be any device supported by the
    loaded model (for example ``cpu`` or ``cuda:0``).
    """

    def __init__(self, model, tokenizer, preprocessing_config, *, model_key, model_version,
                 device="cpu", prepare_text_fn=None, pad_batch_fn=None,
                 torch_module=None, checkpoint_prepare_fn=None):
        self.model = model
        self.tokenizer = tokenizer
        self.config = preprocessing_config
        self.model_key = model_key
        self.model_version = model_version
        self.device = device
        shared = _shared_inputs_module() if prepare_text_fn is None or pad_batch_fn is None else None
        self.prepare_text = prepare_text_fn or shared.prepare_text
        self.pad_batch = pad_batch_fn or shared.pad_batch
        self.checkpoint_prepare = checkpoint_prepare_fn or (shared.checkpoint_prepare_text if shared else None)
        self.torch = torch_module
        self.available = model is not None and tokenizer is not None and bool(model_version)
        self.decision_threshold = THRESHOLD if (self.available or (
            bool(model_version) and self.config.get("label_to_id") == {"Not Scam": 0, "Scam": 1}
            and model_key in self.config.get("models", {}))) else None
        if self.available:
            try:
                if hasattr(model, "to"):
                    model.to(device)
                if hasattr(model, "eval"):
                    model.eval()
            except Exception:
                self.available = False
        if not self.available:
            self.model_version = None

    def _tensor_batch(self, item):
        batch = self.pad_batch([item], self.tokenizer)
        values = batch["inputs"]
        if self.torch is None:
            import torch
            self.torch = torch
        tensors = {key: self.torch.as_tensor(value, device=self.device) for key, value in values.items()}
        return tensors, values

    @staticmethod
    def _logits(output):
        if hasattr(output, "logits"):
            return output.logits
        if isinstance(output, dict) and "logits" in output:
            return output["logits"]
        return output

    def predict(self, request, *, include_trace=False):
        trace = None
        def finish(response):
            return (response, trace) if include_trace else response

        request_id = request.get("request_id") if isinstance(request, dict) else None
        if not isinstance(request, dict) or set(request) != {"request_id", "transcript"} or not _valid_request_id(request_id):
            if not _valid_request_id(request_id):
                request_id = None
            return finish(_response(request_id, self.model_version, "error", threshold=self.decision_threshold,
                             error={"code": "E_INVALID_REQUEST", "message": ERRORS["E_INVALID_REQUEST"]}))
        transcript = request["transcript"]
        if not isinstance(transcript, str) or not transcript.strip():
            return finish(_response(request_id, self.model_version, "error", threshold=self.decision_threshold,
                             error={"code": "E_TRANSCRIPT_INVALID", "message": ERRORS["E_TRANSCRIPT_INVALID"]}))
        if not self.available:
            return finish(_response(request_id, None, "error", threshold=self.decision_threshold,
                             error={"code": "E_MODEL_UNAVAILABLE", "message": ERRORS["E_MODEL_UNAVAILABLE"]}))
        try:
            item = self.prepare_text(transcript, self.model_key, self.config,
                                     self.tokenizer, mode="whole_conversation", marker_condition="role_free")
            notices = item.get("notices", {})
            warnings = ["TRUNCATED_TO_APPROVED_LIMIT"] if notices.get("truncated") else []
            if include_trace:
                prepared_text = self.checkpoint_prepare(transcript, self.model_key, self.config)
                unpadded = item["inputs"]
                trace = {"prepared_text": prepared_text,
                         "unpadded_input_ids": list(unpadded["input_ids"]),
                         "attention_mask": list(unpadded["attention_mask"]),
                         "batching": {"request_batch_size": 1, "padding": "shared input module pad_batch; single-request right-padded batch",
                                      "padded_length": len(unpadded["input_ids"])}}
        except Exception:
            return finish(_response(request_id, self.model_version, "error", threshold=self.decision_threshold,
                             error={"code": "E_PREPROCESSING_FAILED", "message": ERRORS["E_PREPROCESSING_FAILED"]}))
        try:
            inputs, padded_inputs = self._tensor_batch(item)
            if include_trace:
                trace["padded_model_inputs"] = padded_inputs
                trace["batching"]["padded_length"] = len(padded_inputs["input_ids"][0])
            context = self.torch.inference_mode() if hasattr(self.torch, "inference_mode") else nullcontext()
            with context:
                output = self.model(**inputs)
            logits = self._logits(output)
            if hasattr(logits, "ndim") and logits.ndim == 2:
                if logits.shape != (1, 2):
                    raise ValueError("Expected one row and two logits")
                float_logits = logits.float() if hasattr(logits, "float") else logits
                probabilities = self.torch.softmax(float_logits, dim=-1)[0].detach().cpu().tolist()
            else:
                raise ValueError("Expected a two-class logits tensor")
            if len(probabilities) != 2 or any(not self._finite_probability(p) for p in probabilities):
                raise ValueError("Non-finite or malformed probabilities")
            if abs(sum(float(p) for p in probabilities) - 1.0) > 1e-6:
                raise ValueError("Two-class probabilities do not sum to one")
        except (ValueError, TypeError, IndexError):
            return finish(_response(request_id, self.model_version, "error", threshold=self.decision_threshold, warnings=warnings,
                             error={"code": "E_INVALID_OUTPUT", "message": ERRORS["E_INVALID_OUTPUT"]}))
        except Exception:
            return finish(_response(request_id, self.model_version, "error", threshold=self.decision_threshold, warnings=warnings,
                             error={"code": "E_INFERENCE_FAILED", "message": ERRORS["E_INFERENCE_FAILED"]}))
        scores = {LABELS[0]: float(probabilities[0]), LABELS[1]: float(probabilities[1])}
        label = "Scam" if scores["Scam"] >= THRESHOLD else "Not Scam"
        return finish(_response(request_id, self.model_version, "success", label=label,
                         probabilities=scores, threshold=THRESHOLD, warnings=warnings))

    def predict_with_trace(self, request):
        """Development-only parity seam; returns exact preparation/batch trace."""
        return self.predict(request, include_trace=True)

    @staticmethod
    def _finite_probability(value):
        try:
            if isinstance(value, bool):
                return False
            return 0.0 <= float(value) <= 1.0 and float(value) == float(value)
        except (TypeError, ValueError):
            return False


if __name__ == "__main__":
    main()
