import importlib.util
import json
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "evaluation.py"
spec = importlib.util.spec_from_file_location("evaluation_under_test", MODULE)
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


def test_metrics_keep_execution_failures_out_of_classification_errors():
    outcomes = [
        {"execution_state": "success", "true_label": "Scam", "predicted_label": "Scam", "source_dataset": "primary"},
        {"execution_state": "success", "true_label": "Not Scam", "predicted_label": "Scam", "source_dataset": "primary"},
        {"execution_state": "failure", "true_label": "Scam", "predicted_label": "", "source_dataset": "supplemental", "failure_reason": "synthetic"},
    ]
    metrics = evaluation.compute_metrics(outcomes)
    assert metrics["combined"]["assigned"] == 3
    assert metrics["combined"]["successful"] == 2
    assert metrics["combined"]["failed"] == 1
    assert metrics["combined"]["tp"] == 1 and metrics["combined"]["fp"] == 1
    assert metrics["by_source"]["supplemental"]["scam_f1"] is None
    assert metrics["by_source"]["supplemental"]["failures_by_reason"] == {"synthetic": 1}


def test_completion_record_can_be_relocated_by_exact_sha_without_rewriting_run_config(tmp_path):
    stored = tmp_path / "unavailable-drive-path" / "selection_completion.json"
    local = tmp_path / "copied-selection-completion.json"
    app = tmp_path / "approval.md"
    app.write_text("approved scope reduction")
    content = {
        "status": "complete_verified",
        "selected_config_sha256": "selected-sha",
        "main_fit_count": 45,
        "excluded_main_fit_count": 30,
        "caller_only_fit_count": 0,
        "supplemental_fit_count": 0,
        "scope_approval": {
            "status": "owner_approved",
            "reference": "ref",
            "path": str(app),
            "sha256": evaluation.sha256(app),
        },
    }
    local.write_text(json.dumps(content) + "\n", encoding="utf-8")
    final_run = {"selection": {"selection_completion_path": str(stored),
                               "selection_completion_sha256": evaluation.sha256(local),
                               "selected_config_sha256": "selected-sha"}}
    assert evaluation.resolve_selection_completion(final_run, local) == local.resolve()
    assert final_run["selection"]["selection_completion_path"] == str(stored)
    local.write_text(json.dumps({**content, "selected_config_sha256": "different"}) + "\n", encoding="utf-8")
    try:
        evaluation.resolve_selection_completion(final_run, local)
    except ValueError as exc:
        assert "checksum" in str(exc)
    else:
        raise AssertionError("relocated completion record with different bytes must be rejected")


def test_predictor_adapter_preserves_request_and_trace_without_a_model():
    class FakePipeline:
        model_key = "wangchanberta"
        threshold = 0.5
        artifact_id = "synthetic-run:synthetic-manifest-sha256"

    predictor = evaluation.FinalEvaluationPredictor(FakePipeline())
    original = evaluation.predict_with_trace
    evaluation.predict_with_trace = lambda text, pipeline: {
        "prepared_text": text.upper(), "unpad_input_ids": [1, 2], "unpad_attention_mask": [1, 1],
        "batched_inputs": {"input_ids": [1, 2], "attention_mask": [1, 1]},
        "request_batch_size": 1, "padding": "shared", "padded_length": 2,
        "p_not_scam": 0.2, "p_scam": 0.8, "predicted_label": "Scam", "threshold": 0.5,
        "notices": {},
    }
    try:
        response, trace = predictor.predict_with_trace({"request_id": "synthetic-1", "text": "hi"})
    finally:
        evaluation.predict_with_trace = original
    assert response["request_id"] == "synthetic-1" and response["model_version"] == "synthetic-run:synthetic-manifest-sha256"
    assert response["label"] == "Scam"
    assert trace["unpadded_input_ids"] == [1, 2]
    assert trace["padded_model_inputs"]["input_ids"] == [1, 2]


def test_partial_journal_recovery_reuses_successful_and_failed_records(tmp_path):
    journal = tmp_path / "evaluation_events.jsonl"
    auth = {"evaluation_id": "synthetic-eval", "final_run_id": "synthetic-run"}
    artifact_id = "synthetic-run:manifest-sha"
    records = {
        "synthetic-1": {"sample_id": "synthetic-1", "label": "Scam", "source_dataset": "primary"},
        "synthetic-2": {"sample_id": "synthetic-2", "label": "Not Scam", "source_dataset": "supplemental"},
    }
    outcome1 = {"evaluation_id": auth["evaluation_id"], "final_run_id": auth["final_run_id"],
                "artifact_id": artifact_id, "sample_id": "synthetic-1", "true_label": "Scam",
                "source_dataset": "primary", "execution_state": "success"}
    journal.write_text(json.dumps({"prediction": outcome1, "error_review": None}) + "\n", encoding="utf-8")
    outcomes, errors = evaluation.read_evaluation_journal(journal, auth, artifact_id, records)
    assert [row["sample_id"] for row in outcomes] == ["synthetic-1"] and errors == []
    # A resumed run skips synthetic-1 and appends only the unfinished ID.
    outcome2 = {"evaluation_id": auth["evaluation_id"], "final_run_id": auth["final_run_id"],
                "artifact_id": artifact_id, "sample_id": "synthetic-2", "true_label": "Not Scam",
                "source_dataset": "supplemental", "execution_state": "failure", "failure_reason": "synthetic"}
    with journal.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"prediction": outcome2, "error_review": None}) + "\n")
    outcomes, _ = evaluation.read_evaluation_journal(journal, auth, artifact_id, records)
    assert {row["sample_id"] for row in outcomes} == set(records)
    assert sum(row["execution_state"] == "failure" for row in outcomes) == 1


def test_atomic_publication_preserves_and_checks_partial_files(tmp_path):
    destination = tmp_path / "metrics.json"
    destination.write_text('{"value": 1}\n', encoding="utf-8")
    matching_stage = tmp_path / "metrics-stage.json"
    matching_stage.write_text('{"value": 1}\n', encoding="utf-8")
    assert evaluation.atomic_publish(tmp_path, {"metrics.json": matching_stage})["metrics.json"] == evaluation.sha256(destination)
    conflicting_stage = tmp_path / "metrics-conflict.json"
    conflicting_stage.write_text('{"value": 2}\n', encoding="utf-8")
    try:
        evaluation.atomic_publish(tmp_path, {"metrics.json": conflicting_stage})
    except ValueError as exc:
        assert "preserve it" in str(exc)
    else:
        raise AssertionError("conflicting partial evidence must not be overwritten")
