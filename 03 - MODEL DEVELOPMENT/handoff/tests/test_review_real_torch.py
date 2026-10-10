"""Reviewer integration checks with random tiny weights and frozen cached tokenizers."""
from pathlib import Path
import csv
import hashlib
import importlib.util
import json
import shutil
import sys

import pytest
import torch
from transformers import CamembertConfig, CamembertForSequenceClassification

MODEL_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(MODEL_ROOT / "input-preparation"))
sys.path.insert(0, str(MODEL_ROOT / "handoff"))
import inputs
from inference import LocalClassifier
from inference import assemble_bundle, load_local_bundle
from bundle_manifest import sha256_file

FINAL_DIR = MODEL_ROOT / "final-evaluation"


def _write_rows(path, rows):
    fields = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _synthetic_release_evidence(tmp_path, native, service, *, reviewed=True):
    """Create synthetic post-evaluation artifacts without reading test data."""
    training_dir = MODEL_ROOT / "training"
    if str(training_dir) not in sys.path:
        sys.path.insert(0, str(training_dir))
    from trainer import verify_model_artifact
    native_manifest = verify_model_artifact(native)
    checkpoint = service.config["models"]["wangchanberta"]
    synthetic_assignments = tmp_path / "split_assignments.csv"
    synthetic_assignments.write_text(
        "sample_id,source_dataset,group_id,split,cv_fold\nsynthetic-1,primary,g1,test,\n",
        encoding="utf-8")
    config = json.loads(json.dumps(service.config))
    config["assignments_sha256"] = sha256_file(synthetic_assignments)
    preprocessing = tmp_path / "preprocessing_config.json"
    preprocessing.write_text(json.dumps(config), encoding="utf-8")
    # The same pinned model/tokenizer identity and only the assignment checksum
    # differs; it is synthetic evidence, not a project dataset assignment.
    native_manifest["preprocessing_config_sha256"] = sha256_file(preprocessing)
    native_manifest["assignments_sha256"] = config["assignments_sha256"]
    (native / "artifact_manifest.json").write_text(json.dumps(native_manifest), encoding="utf-8")
    inventory = {path.name: sha256_file(path) for path in native.iterdir()
                 if path.is_file() and path.name != "artifact_manifest.json"}
    native_manifest["files"] = inventory
    (native / "artifact_manifest.json").write_text(json.dumps(native_manifest), encoding="utf-8")
    native_manifest_sha = sha256_file(native / "artifact_manifest.json")
    weights_sha = sha256_file(native / "model.safetensors")
    artifact_id = f"{native_manifest['run_id']}:{native_manifest_sha}"
    selected_path = tmp_path / "selected_config.json"
    selected = {"status": "frozen_by_human_approval", "model_key": "wangchanberta",
        "checkpoint": checkpoint["checkpoint"], "checkpoint_revision": checkpoint["revision"],
        "configuration_id": "synthetic-cv-selection", "data_condition": "primary_plus_supplemental",
        "learning_rate": 3e-5, "selected_duration_epochs": 3, "training_seed": 67,
        "training_representation": "whole_conversation", "training_marker_condition": "role_marked"}
    selected_path.write_text(json.dumps({
        **selected}), encoding="utf-8")
    selected_sha = sha256_file(selected_path)
    selection_completion_path = tmp_path / "selection_complete.json"
    selection_completion_path.write_text(json.dumps({"status": "complete_verified",
        "selected_config_sha256": selected_sha, "main_fit_count": 120, "caller_only_fit_count": 5}),
        encoding="utf-8")
    run_config = {"schema_version": 1, "mode": "final_training",
        "run_id": native_manifest["run_id"], "model": "wangchanberta",
        "checkpoint": {"id": checkpoint["checkpoint"], "revision": checkpoint["revision"]},
        "data": {"condition": "primary_plus_supplemental"},
        "training": {"epochs": 3, "seed": 67, "representation": "whole_conversation",
                     "marker_condition": "role_marked"},
        "validation": {"enabled": False}, "optimizer": {"learning_rate": 3e-5},
        "schedule": {"name": "linear_warmup_then_constant", "warmup_updates": 0},
        "precision": {"mode": "fp32"}, "runtime": {"device": "cpu"},
        "selection": {"selected_config_sha256": selected_sha,
                      "selected_configuration_id": selected["configuration_id"],
                      "selection_completion_path": str(selection_completion_path),
                      "selection_completion_sha256": sha256_file(selection_completion_path)},
        "evaluation": {"scam_threshold": 0.5},
        "identities": {"preprocessing_config_sha256": sha256_file(preprocessing),
                       "input_component_sha256": sha256_file(MODEL_ROOT / "input-preparation/inputs.py"),
                       "assignments_sha256": config["assignments_sha256"]}}
    sys.path.insert(0, str(MODEL_ROOT / "training"))
    import trainer
    native_manifest["configuration_id"] = trainer.configuration_id(run_config)
    run_config["configuration_id"] = native_manifest["configuration_id"]
    (native / "artifact_manifest.json").write_text(json.dumps(native_manifest), encoding="utf-8")
    native_manifest_sha = sha256_file(native / "artifact_manifest.json")
    artifact_id = f"{native_manifest['run_id']}:{native_manifest_sha}"
    (native.parent / "run_config.json").write_text(json.dumps(run_config), encoding="utf-8")
    (native.parent / "run_summary.json").write_text(json.dumps({"run_id": native_manifest["run_id"],
        "status": "completed", "epochs_completed": 3}), encoding="utf-8")
    evaluation_dir = tmp_path / "evaluation"
    evaluation_dir.mkdir()
    audit_dir = tmp_path / "review-generation"
    audit_dir.mkdir()
    review_copy_path = audit_dir / "error_analysis_reviewed.csv"
    assignments = [{"sample_id": "synthetic-1", "source_dataset": "primary",
                    "group_id": "g1", "split": "test", "cv_fold": ""}]
    # Synthetic false-negative evidence exercises the review gate; its text is
    # explicitly fictional and does not come from any held-out dataset.
    outcome = {"evaluation_id": "synthetic-eval", "final_run_id": native_manifest["run_id"],
        "final_configuration_id": native_manifest["configuration_id"], "artifact_id": artifact_id,
        "sample_id": "synthetic-1", "source_dataset": "primary", "true_label": "Scam",
        "p_not_scam": 0.8, "p_scam": 0.2, "predicted_label": "Not Scam", "threshold": 0.5,
        "execution_state": "success", "failure_reason": "", "truncated": False,
        "original_token_count": 10, "prepared_token_count": 10, "dropped_token_count": 0}
    error = {"evaluation_id": "synthetic-eval", "sample_id": "synthetic-1", "source_dataset": "primary",
        "prediction_artifact_reference": "synthetic-predictions.csv", "error_type": "false_negative",
        "true_label": "Scam", "predicted_label": "Not Scam", "p_scam": 0.2, "threshold": 0.5,
        "transcript_evidence": "fictional synthetic text", "input_length_findings": "synthetic",
        "structural_marker_findings": "synthetic", "observed_error_category": "synthetic",
        "review_explanation": "synthetic review", "review_evidence": "synthetic evidence",
        "uncertainty": "synthetic uncertainty", "potential_future_investigation": "synthetic follow-up",
        "review_status": "reviewed" if reviewed else "pending_review"}
    original_error = dict(error, observed_error_category="", review_explanation="", review_evidence="",
                          uncertainty="", potential_future_investigation="", review_status="pending_review")
    predictions_path = evaluation_dir / "test_predictions.csv"
    errors_path = evaluation_dir / "error_analysis.csv"
    _write_rows(predictions_path, [outcome])
    _write_rows(errors_path, [original_error])
    _write_rows(review_copy_path, [error])
    (evaluation_dir / "evaluation_events.jsonl").write_text(json.dumps({"prediction": outcome}) + "\n")
    test_csv_sha = "d" * 64
    auth_ref = "synthetic owner authorization"
    metrics_path = evaluation_dir / "metrics.json"
    spec = importlib.util.spec_from_file_location("synthetic_eval_metrics", FINAL_DIR / "evaluation.py")
    evaluation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluation)
    metrics = evaluation.compute_metrics([outcome])
    metrics.update({"evaluation_id": "synthetic-eval", "final_run_id": native_manifest["run_id"],
        "final_configuration_id": native_manifest["configuration_id"], "artifact_id": artifact_id,
        "artifact_manifest_sha256": native_manifest_sha, "model_safetensors_sha256": weights_sha,
        "model_export_directory": str(native.resolve()), "selected_config_sha256": selected_sha,
        "test_csv_sha256": test_csv_sha, "assignments_sha256": config["assignments_sha256"],
        "threshold": 0.5, "authorization_reference": auth_ref})
    metrics_path.write_text(json.dumps(metrics), encoding="utf-8")
    protocol = {"status": "executed_under_owner_authorization", "selection": str(selected_path.resolve()),
        "selection_sha256": selected_sha, "training_run_id": native_manifest["run_id"],
        "selection_completion_sha256": sha256_file(selection_completion_path),
        "inference_artifact": str(native.resolve()), "model_safetensors_sha256": weights_sha,
        "artifact_manifest_sha256": native_manifest_sha,
        "preprocessing_config_sha256": sha256_file(preprocessing), "test_csv_sha256": test_csv_sha,
        "assignments_sha256": config["assignments_sha256"], "threshold": 0.5,
        "authorization_reference": auth_ref}
    protocol_path = evaluation_dir / "evaluation_protocol.md"
    protocol_path.write_text("# Protocol\n\n```json\n" + json.dumps(protocol) + "\n```\n")
    report_path = evaluation_dir / "evaluation_report.md"
    report_path.write_text("# Synthetic report\n\n- Evaluation ID: `synthetic-eval`\n"
        f"- Final run: `{native_manifest['run_id']}`\n- Artifact ID: `{artifact_id}`\n- Threshold: `0.5`\n"
        "- Authorization: `synthetic owner authorization`\n")
    journal_path = evaluation_dir / "evaluation_events.jsonl"
    completion = {"schema_version": 1, "status": "artifacts_complete_pending_error_review",
        "evaluation_id": "synthetic-eval", "final_run_id": native_manifest["run_id"],
        "artifact_id": artifact_id, "selected_config_sha256": selected_sha,
        "selection_completion_sha256": sha256_file(selection_completion_path),
        "artifact_manifest_sha256": native_manifest_sha, "model_safetensors_sha256": weights_sha,
        "test_csv_sha256": test_csv_sha, "assignments_sha256": config["assignments_sha256"],
        "assigned_prediction_count": 1, "failed_execution_count": 0, "pending_error_review_count": 1,
        "files_sha256": {p.name: sha256_file(p) for p in
            (predictions_path, metrics_path, errors_path, report_path, protocol_path, journal_path)}}
    (evaluation_dir / "evaluation_complete.json").write_text(json.dumps(completion), encoding="utf-8")
    sys.path.insert(0, str(FINAL_DIR))
    import review_results
    audit_result = review_results.audit([outcome], [error], assignments, [original_error])
    audit_result["source_sha256"] = {
        str(predictions_path.resolve()): sha256_file(predictions_path),
        str(review_copy_path.resolve()): sha256_file(review_copy_path),
        str(errors_path.resolve()): sha256_file(errors_path),
        str(synthetic_assignments.resolve()): sha256_file(synthetic_assignments)}
    audit_result["source_files"] = {"predictions": str(predictions_path.resolve()),
        "reviewed_errors": str(review_copy_path.resolve()), "original_errors": str(errors_path.resolve()),
        "assignments": str(synthetic_assignments.resolve())}
    audit_result["metrics"] = evaluation.compute_metrics([outcome])
    audit_path = audit_dir / "review_audit.json"
    audit_path.write_text(json.dumps(audit_result), encoding="utf-8")
    identity = {"candidate": "wangchanberta", "checkpoint": checkpoint["checkpoint"],
        "revision": checkpoint["revision"], "model_code_revision": checkpoint["revision"],
        "tokenizer_revision": checkpoint["revision"], "preprocessing_config_sha256": sha256_file(preprocessing),
        "label_mapping": {"Not Scam": 0, "Scam": 1}, "threshold": 0.5,
        "dependencies": {"torch": torch.__version__, **service.config["dependencies"]},
        "license": "Synthetic verification only; no release model", "runtime_requirements": {"device": "cpu"},
        "evaluation_identity": {"caller_claim": "must be ignored"}, "bundle_id": "synthetic-review",
        "model_directory": "model", "weights_path": "model/model.safetensors",
        "preprocessing_config_path": "preprocessing_config.json", "tokenizer_path": "model/tokenizer.json",
        "model_config_path": "model/config.json"}
    return {"evaluation_dir": evaluation_dir, "audit_path": audit_path,
            "preprocessing_path": preprocessing, "identity": identity,
            "completion_path": evaluation_dir / "evaluation_complete.json"}


@pytest.fixture(scope="module")
def service():
    config = inputs.load_config()
    tokenizer = inputs.load_tokenizer("wangchanberta", config, local_files_only=True)
    torch.manual_seed(67)
    tiny = CamembertForSequenceClassification(CamembertConfig(
        # Mirror the approved Camembert checkpoint's unused embedding row.
        vocab_size=len(tokenizer) + 1, hidden_size=8, num_hidden_layers=1,
        num_attention_heads=2, intermediate_size=16, max_position_embeddings=514,
        pad_token_id=tokenizer.pad_token_id, num_labels=2,
        id2label={0: "Not Scam", 1: "Scam"}, label2id={"Not Scam": 0, "Scam": 1},
    ))
    return LocalClassifier(tiny, tokenizer, config, model_key="wangchanberta",
                           model_version="synthetic-review-only", device="cpu")


def test_real_tokenizer_and_tensor_path_matches_direct_preparation(service):
    text = "สวัสดี กรุณาอย่าโอนเงิน Caller: เป็นคำพูดจริง"
    response, trace = service.predict_with_trace({"request_id": "synthetic-review", "transcript": text})
    assert response["status"] == "success"
    expected = inputs.prepare_text(text, "wangchanberta", service.config, service.tokenizer)
    assert trace["unpadded_input_ids"] == expected["inputs"]["input_ids"]
    assert trace["attention_mask"] == expected["inputs"]["attention_mask"]
    assert trace["prepared_text"] == inputs.checkpoint_prepare_text(text, "wangchanberta", service.config)
    assert sum(response["probabilities"].values()) == pytest.approx(1.0, abs=1e-6)
    assert response["label"] == ("Scam" if response["probabilities"]["Scam"] >= 0.5 else "Not Scam")


def test_repeated_requests_are_eval_only_and_identical(service):
    before = {key: value.clone() for key, value in service.model.state_dict().items()}
    request = {"request_id": "repeat-synthetic", "transcript": "สวัสดีครับ"}
    first, second = service.predict(request), service.predict(request)
    assert first == second
    assert not service.model.training
    assert all(torch.equal(before[key], value) for key, value in service.model.state_dict().items())
    assert all(parameter.grad is None for parameter in service.model.parameters())


def test_metadata_and_unusable_request_ids_never_reach_predictive_input(service):
    for request in (
        {"request_id": None, "transcript": "สวัสดี"},
        {"request_id": "", "transcript": "สวัสดี"},
        {"request_id": "valid", "transcript": "สวัสดี", "label": "Scam"},
    ):
        response, trace = service.predict_with_trace(request)
        assert response["status"] == "error"
        assert response["label"] is None
        assert response["probabilities"] is None
        assert trace is None


def test_unavailable_bundle_does_not_claim_an_available_decision_config():
    service = LocalClassifier(None, None, {}, model_key="unavailable", model_version=None)
    response = service.predict({"request_id": "unavailable", "transcript": "Synthetic request"})
    assert response["status"] == "error"
    assert response["error"]["code"] == "E_MODEL_UNAVAILABLE"
    assert response["model_version"] is None
    assert response["threshold"] is None
    assert response["label"] is None


def _native_artifact(service, tmp_path):
    sys.path.insert(0, str(MODEL_ROOT / "training"))
    import trainer
    native = tmp_path / "native"
    service.model.save_pretrained(native, safe_serialization=True)
    service.tokenizer.save_pretrained(native)
    checkpoint = service.config["models"]["wangchanberta"]
    config_path = tmp_path / "preprocessing_config.json"
    config_path.write_text(json.dumps(service.config), encoding="utf-8")
    inventory = {path.name: sha256_file(path) for path in native.iterdir() if path.is_file()}
    native_manifest = {
        "schema_version": 1, "num_labels": 2, "model": "wangchanberta",
        "run_id": "synthetic-final-training", "configuration_id": "synthetic-only",
        "checkpoint_id": checkpoint["checkpoint"], "checkpoint_revision": checkpoint["revision"],
        "custom_code_revision": None, "preprocessing_config_sha256": sha256_file(config_path),
        "assignments_sha256": service.config["assignments_sha256"],
        "training_membership_sha256": "a" * 64, "training_seed": 67,
        "training_data_condition": "primary_plus_supplemental",
        "training_representation": "whole_conversation", "training_marker_condition": "role_marked",
        "id2label": {"0": "Not Scam", "1": "Scam"}, "label2id": {"Not Scam": 0, "Scam": 1},
        "files": inventory,
    }
    (native / "artifact_manifest.json").write_text(json.dumps(native_manifest), encoding="utf-8")
    trainer.verify_model_artifact(native)
    return native, config_path


def test_native_saved_model_can_be_packaged_without_reserializing_weights(service, tmp_path, monkeypatch):
    native, _ = _native_artifact(service, tmp_path)
    evidence = _synthetic_release_evidence(tmp_path, native, service)
    inventory_hash = sha256_file(native / "model.safetensors")
    package = tmp_path / "bundle"
    assemble_bundle(native, package, evidence["identity"],
        preprocessing_config_source=evidence["preprocessing_path"],
        evaluation_dir=evidence["evaluation_dir"], review_audit_path=evidence["audit_path"])
    assert sha256_file(package / "model/model.safetensors") == inventory_hash
    component_sha = sha256_file(package / "runtime/inputs.py")
    manifest = json.loads((package / "artifact_manifest.json").read_text(encoding="utf-8"))
    assert manifest["identity"]["input_component_path"] == "runtime/inputs.py"
    assert manifest["identity"]["input_component_sha256"] == component_sha
    request = {"request_id": "native-load-test", "transcript": "สวัสดีครับ"}
    expected = service.predict(request)
    assert expected["status"] == "success"
    # Bundled tokenizer and preparation code must suffice; never consult the
    # original checkpoint cache or current workspace helper implementation.
    monkeypatch.setattr(inputs, "load_tokenizer", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("external tokenizer loader used")))
    monkeypatch.setattr(inputs, "prepare_text", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("workspace helper used")))
    monkeypatch.setattr(inputs, "pad_batch", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("workspace helper used")))
    monkeypatch.setattr(inputs, "checkpoint_prepare_text", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("workspace helper used")))
    packaged = load_local_bundle(package, device="cpu")
    actual = packaged.predict(request)
    assert actual["status"] == "success"
    assert actual["label"] == expected["label"]
    for label in ("Not Scam", "Scam"):
        assert actual["probabilities"][label] == pytest.approx(expected["probabilities"][label], abs=1e-7)
    tampered = tmp_path / "tampered-bundle"
    shutil.copytree(package, tampered)
    with (tampered / "runtime/inputs.py").open("a", encoding="utf-8") as stream:
        stream.write("\n# tampered\n")
    with pytest.raises(ValueError, match="checksum mismatch"):
        load_local_bundle(tampered, device="cpu")
    with pytest.raises(FileExistsError):
        assemble_bundle(native, package, evidence["identity"],
            preprocessing_config_source=evidence["preprocessing_path"],
            evaluation_dir=evidence["evaluation_dir"], review_audit_path=evidence["audit_path"])


@pytest.mark.parametrize("tamper", ["metrics.json", "evaluation_protocol.md", "evaluation_report.md", "review_audit.json"])
def test_bundle_rejects_tampered_evaluation_or_review_evidence(service, tmp_path, tamper):
    native, _ = _native_artifact(service, tmp_path)
    evidence = _synthetic_release_evidence(tmp_path, native, service)
    target = evidence["audit_path"] if tamper == "review_audit.json" else evidence["evaluation_dir"] / tamper
    target.write_text(target.read_text(encoding="utf-8") + "\nmodified\n", encoding="utf-8")
    with pytest.raises((ValueError, json.JSONDecodeError)):
        assemble_bundle(native, tmp_path / "rejected", evidence["identity"],
            preprocessing_config_source=evidence["preprocessing_path"],
            evaluation_dir=evidence["evaluation_dir"], review_audit_path=evidence["audit_path"])
    assert not (tmp_path / "rejected").exists()


def test_bundle_rejects_pending_error_review(service, tmp_path):
    native, _ = _native_artifact(service, tmp_path)
    evidence = _synthetic_release_evidence(tmp_path, native, service, reviewed=False)
    with pytest.raises(ValueError, match="documented review of every classification error"):
        assemble_bundle(native, tmp_path / "pending", evidence["identity"],
            preprocessing_config_source=evidence["preprocessing_path"],
            evaluation_dir=evidence["evaluation_dir"], review_audit_path=evidence["audit_path"])
