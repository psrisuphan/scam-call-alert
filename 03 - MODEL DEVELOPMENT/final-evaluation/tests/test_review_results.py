import copy
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("scam_review_results", Path(__file__).resolve().parents[1] / "review_results.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


def evidence():
    assignments = [{"sample_id": str(i), "split": "test", "source_dataset": "primary"} for i in range(3)]
    base = {"evaluation_id": "synthetic", "artifact_id": "synthetic-model", "source_dataset": "primary",
            "threshold": "0.5", "failure_reason": ""}
    predictions = [
        {**base, "sample_id": "0", "true_label": "Not Scam", "predicted_label": "Not Scam",
         "execution_state": "success", "p_not_scam": "0.9", "p_scam": "0.1"},
        {**base, "sample_id": "1", "true_label": "Scam", "predicted_label": "Not Scam",
         "execution_state": "success", "p_not_scam": "0.8", "p_scam": "0.2"},
        {**base, "sample_id": "2", "true_label": "Scam", "predicted_label": "",
         "execution_state": "failure", "p_not_scam": "", "p_scam": "", "failure_reason": "synthetic failure"},
    ]
    errors = [{**predictions[1], "error_type": "false_negative", "transcript_evidence": "Invented test fixture",
               "review_status": "pending_review"}]
    return predictions, errors, assignments


def test_all_assignments_and_every_prediction_error_are_accounted():
    prediction, error, assignments = evidence()
    result = review.audit(prediction, error, assignments)
    assert (result["assigned"], result["successful"], result["failed"]) == (3, 2, 1)
    assert result["pending_error_reviews"] == ["1"]
    assert not result["error_review_complete"]


def test_documented_review_is_required_even_with_reviewed_flag():
    prediction, error, assignments = evidence()
    error[0]["review_status"] = "reviewed"
    assert not review.audit(prediction, error, assignments)["error_review_complete"]
    for field in ("observed_error_category", "review_explanation", "review_evidence", "uncertainty", "potential_future_investigation"):
        error[0][field] = "Synthetic verification statement only"
    assert review.audit(prediction, error, assignments)["error_review_complete"]


def test_review_copy_cannot_rewrite_original_transcript_or_length_evidence():
    prediction, error, assignments = evidence()
    originals = copy.deepcopy(error)
    error[0]["transcript_evidence"] = "Altered original transcript"
    with pytest.raises(ValueError, match="immutable"):
        review.audit(prediction, error, assignments, originals)


def test_review_annotations_can_be_added_without_changing_originals():
    prediction, error, assignments = evidence()
    originals = copy.deepcopy(error)
    error[0]["review_explanation"] = "An observation in a separate review copy"
    result = review.audit(prediction, error, assignments, originals)
    assert result["coverage_verified"]
    assert originals[0].get("review_explanation") is None


@pytest.mark.parametrize("change", ["missing_outcome", "missing_error", "duplicate", "changed_error_score", "fabricated_failure_class", "changed_threshold"])
def test_invalid_evidence_is_rejected(change):
    prediction, error, assignments = evidence()
    if change == "missing_outcome":
        prediction.pop()
    elif change == "missing_error":
        error.clear()
    elif change == "duplicate":
        prediction.append(copy.deepcopy(prediction[0]))
    elif change == "changed_error_score":
        error[0]["p_scam"] = "0.3"
    elif change == "fabricated_failure_class":
        prediction[2]["predicted_label"] = "Not Scam"
    else:
        prediction[0]["threshold"] = "0.4"
    with pytest.raises(ValueError):
        review.audit(prediction, error, assignments)


def test_confusion_figures_include_failed_count_and_can_be_reproduced(tmp_path):
    spec = importlib.util.spec_from_file_location("scam_metrics_review", Path(__file__).resolve().parents[1] / "evaluation.py")
    evaluation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluation)
    prediction, _, _ = evidence()
    metrics = evaluation.compute_metrics(prediction)
    assert metrics["combined"]["assigned"] == 3
    assert metrics["combined"]["failed"] == 1
    review.figures(metrics, tmp_path / "figures")
    for subset in ("combined", "primary", "supplemental"):
        for extension in ("png", "pdf"):
            assert (tmp_path / "figures" / f"confusion_matrix_{subset}.{extension}").stat().st_size > 0
