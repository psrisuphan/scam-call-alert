"""Fail-closed live comparator for role-free development-path/package parity."""
import math
import csv
import hashlib
from io import StringIO
from pathlib import Path


def training_pool_fixtures(training_records, sample_ids, assignments_path):
    """Select only verified train-assigned rows for development parity.

    Supply records returned by ``inputs.load_partition('train_pool')``. This
    helper reads only the assignment metadata CSV, never the held-out test
    transcript file, and rejects IDs assigned to the final test partition.
    """
    wanted = list(sample_ids)
    if not wanted or len(wanted) != len(set(wanted)) or any(not isinstance(value, str) or not value for value in wanted):
        raise ValueError("Select a nonempty unique list of training-pool sample IDs")
    assignments_path = Path(assignments_path)
    if assignments_path.is_symlink():
        raise ValueError("Saved assignment file may not be a symlink")
    assignment_bytes = assignments_path.read_bytes()
    reader = csv.DictReader(StringIO(assignment_bytes.decode("utf-8-sig")))
    if reader.fieldnames != ["sample_id", "source_dataset", "group_id", "split", "cv_fold"]:
        raise ValueError("Unexpected saved assignment schema")
    rows = list(reader)
    by_id = {row.get("sample_id"): row for row in rows}
    if len(by_id) != len(rows) or set(wanted) - by_id.keys():
        raise ValueError("Fixture IDs are missing or duplicated in the saved assignments")
    if any(by_id[sample_id].get("split") != "train" for sample_id in wanted):
        raise ValueError("Parity fixtures must come from the saved training pool, never final test")
    records = {row.get("sample_id"): row for row in training_records}
    if len(records) != len(training_records) or set(wanted) - records.keys():
        raise ValueError("Selected records do not match the verified training-pool records")
    fixtures = []
    for sample_id in wanted:
        transcript = records[sample_id].get("transcript")
        if not isinstance(transcript, str) or not transcript.strip():
            raise ValueError(f"Training-pool fixture {sample_id!r} has unusable text")
        fixtures.append({"fixture_id": sample_id, "transcript": transcript})
    provenance = {"source": "training_pool", "fixture_ids": wanted,
                  "assignments_sha256": hashlib.sha256(assignment_bytes).hexdigest()}
    return fixtures, provenance


def validate_parity_authorization(*, approved_tolerance, comparison_context):
    """Fail before prediction if owner approval/provenance is incomplete."""
    if not isinstance(approved_tolerance, dict) or approved_tolerance.get("status") != "approved":
        raise ValueError("An owner-approved parity tolerance is required")
    atol = approved_tolerance.get("atol")
    if isinstance(atol, bool) or not isinstance(atol, (int, float)) or not math.isfinite(atol) or atol < 0:
        raise ValueError("Approved tolerance must contain a finite nonnegative atol")
    if not approved_tolerance.get("reviewer") or not approved_tolerance.get("reference"):
        raise ValueError("Tolerance approval must identify reviewer and approval reference")
    keys = ("reference_artifact", "packaged_manifest_sha256", "environment", "fixture_provenance")
    if not isinstance(comparison_context, dict) or any(not comparison_context.get(key) for key in keys):
        raise ValueError("Comparison must identify both artifacts, environment and development fixture provenance")
    reference = comparison_context["reference_artifact"]
    if not isinstance(reference, dict) or not reference.get("artifact_id"):
        raise ValueError("Reference artifact identity must include an artifact_id")
    ref_digest = reference.get("weights_sha256")
    if not isinstance(ref_digest, str) or len(ref_digest) != 64 or any(c not in "0123456789abcdef" for c in ref_digest):
        raise ValueError("Reference artifact identity must include its evaluated weight SHA-256")
    digest = comparison_context["packaged_manifest_sha256"]
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Packaged manifest identity must be a SHA-256 digest")
    environment = comparison_context["environment"]
    required_environment = ("python_version", "platform", "device", "package_versions")
    if not isinstance(environment, dict) or any(not environment.get(key) for key in required_environment):
        raise ValueError("Record actual Python, platform, device and package versions")
    provenance = comparison_context["fixture_provenance"]
    if not isinstance(provenance, dict) or provenance.get("source") not in ("development", "training_pool"):
        raise ValueError("Fixtures must be identified as development/training-pool evidence")
    fixture_ids = provenance.get("fixture_ids")
    if not isinstance(fixture_ids, list) or not fixture_ids or len(fixture_ids) != len(set(fixture_ids)):
        raise ValueError("Fixture provenance must list its unique stable fixture IDs")
    if provenance["source"] == "training_pool":
        assignments_sha = provenance.get("assignments_sha256")
        if not isinstance(assignments_sha, str) or len(assignments_sha) != 64 or any(c not in "0123456789abcdef" for c in assignments_sha):
            raise ValueError("Training-pool parity provenance must bind saved assignment checksum")
    return float(atol)


def compare_parity(reference, packaged, *, approved_tolerance, comparison_context):
    """Compare traces captured live from the reference and packaged predictors.

    Each predictor must return ``(response, trace)`` from ``predict_with_trace``.
    Exact comparisons cover fixture identity, prepared text, unpadded IDs, mask,
    batch/padding setup and predicted label. Scores alone use the owner-approved
    tolerance. This function accepts only already-authorized development fixtures.
    """
    atol = validate_parity_authorization(approved_tolerance=approved_tolerance,
                                         comparison_context=comparison_context)
    if not reference or not packaged:
        raise ValueError("Parity requires a nonempty set of development fixtures")
    ids = [item.get("fixture_id") if isinstance(item, dict) else None for item in reference]
    package_ids = [item.get("fixture_id") if isinstance(item, dict) else None for item in packaged]
    for name, values in (("reference", ids), ("packaged", package_ids)):
        if any(not isinstance(value, str) or not value for value in values) or len(values) != len(set(values)):
            raise ValueError(f"{name} fixtures require unique stable fixture IDs")
    if ids != package_ids:
        return {"passed": False, "fixture_count": len(reference),
                "mismatches": ["fixture_id_order_or_membership"], "max_probability_abs_error": None,
                "tolerance": approved_tolerance, "comparison_context": comparison_context}
    fields = ("prepared_text", "unpadded_input_ids", "attention_mask", "padded_model_inputs", "batching")
    mismatches = []
    max_error = 0.0
    for index, (ref, pkg) in enumerate(zip(reference, packaged)):
        if ref.get("transcript") != pkg.get("transcript"):
            mismatches.append(f"fixture[{index}].transcript_mismatch")
        if not isinstance(ref.get("transcript"), str) or not ref["transcript"].strip():
            mismatches.append(f"fixture[{index}].transcript_invalid")
        for name, record in (("reference", ref), ("packaged", pkg)):
            response, trace = record.get("response"), record.get("trace")
            if not isinstance(response, dict) or response.get("status") != "success":
                mismatches.append(f"fixture[{index}].{name}_execution")
            if not isinstance(trace, dict) or any(field not in trace for field in fields):
                mismatches.append(f"fixture[{index}].{name}_trace_schema")
        ref_response, pkg_response = ref.get("response", {}), pkg.get("response", {})
        ref_trace, pkg_trace = ref.get("trace", {}), pkg.get("trace", {})
        if ref_response.get("threshold") != 0.5 or pkg_response.get("threshold") != 0.5:
            mismatches.append(f"fixture[{index}].threshold")
        for field in fields:
            if field in ref_trace and field in pkg_trace and ref_trace[field] != pkg_trace[field]:
                mismatches.append(f"fixture[{index}].{field}")
        if ref_response.get("label") not in ("Not Scam", "Scam") or pkg_response.get("label") not in ("Not Scam", "Scam"):
            mismatches.append(f"fixture[{index}].label_schema")
        if ref_response.get("label") != pkg_response.get("label"):
            mismatches.append(f"fixture[{index}].label_mismatch")
        left, right = ref_response.get("probabilities"), pkg_response.get("probabilities")
        if not isinstance(left, dict) or not isinstance(right, dict) or set(left) != {"Not Scam", "Scam"} or set(right) != set(left):
            mismatches.append(f"fixture[{index}].probabilities_schema")
            continue
        parsed = {}
        for side, scores in (("reference", left), ("packaged", right)):
            values = []
            for label in ("Not Scam", "Scam"):
                value = scores[label]
                if isinstance(value, bool):
                    mismatches.append(f"fixture[{index}].{side}.{label}_invalid")
                    continue
                try:
                    number = float(value)
                except (TypeError, ValueError):
                    mismatches.append(f"fixture[{index}].{side}.{label}_invalid")
                    continue
                if not math.isfinite(number) or not 0.0 <= number <= 1.0:
                    mismatches.append(f"fixture[{index}].{side}.{label}_invalid")
                values.append(number)
                parsed[(side, label)] = number
            if len(values) == 2 and abs(sum(values) - 1.0) > 1e-6:
                mismatches.append(f"fixture[{index}].{side}_probability_sum")
            if len(values) == 2:
                predicted = "Scam" if values[1] >= 0.5 else "Not Scam"
                if response_label := (ref_response if side == "reference" else pkg_response).get("label"):
                    if response_label != predicted:
                        mismatches.append(f"fixture[{index}].{side}_threshold_label")
        for label in ("Not Scam", "Scam"):
            if ("reference", label) in parsed and ("packaged", label) in parsed:
                difference = abs(parsed[("reference", label)] - parsed[("packaged", label)])
                max_error = max(max_error, difference)
                if difference > atol:
                    mismatches.append(f"fixture[{index}].probabilities.{label}")
    return {"passed": not mismatches, "fixture_count": len(reference), "mismatches": mismatches,
            "max_probability_abs_error": max_error, "tolerance": approved_tolerance,
            "comparison_context": comparison_context}


class FinalEvaluationAdapter:
    """Adapt final-evaluation's text request/trace to the handoff contract.

    This wrapper delegates prediction to the approved final-evaluation path; it
    only maps its ``text`` and trace field names and never recomputes a baseline.
    """
    def __init__(self, final_evaluation_predictor):
        self.predictor = final_evaluation_predictor
        self.model_version = getattr(final_evaluation_predictor, "model_version", None)

    def predict_with_trace(self, request):
        if not isinstance(request, dict) or set(request) != {"request_id", "transcript"}:
            raise ValueError("Reference adapter requires the inference request contract")
        if not isinstance(request["request_id"], str) or not request["request_id"].strip():
            raise ValueError("Reference adapter requires a nonempty request_id")
        if not isinstance(request["transcript"], str) or not request["transcript"].strip():
            raise ValueError("Reference adapter requires nonempty role-free transcript text")
        response, raw = self.predictor.predict_with_trace({
            "request_id": request["request_id"], "text": request["transcript"]})
        trace = {
            "prepared_text": raw["prepared_text"],
            "unpadded_input_ids": raw.get("unpadded_input_ids", raw.get("unpad_input_ids")),
            "attention_mask": raw.get("attention_mask", raw.get("unpad_attention_mask")),
            "padded_model_inputs": raw.get("padded_model_inputs", raw.get("batched_inputs")),
            "batching": raw.get("batching", {
                "request_batch_size": raw.get("request_batch_size"),
                "padding": raw.get("padding"), "padded_length": raw.get("padded_length")}),
        }
        return response, trace


def run_live_parity(fixtures, reference_predictor, packaged_predictor, *,
                    approved_tolerance, comparison_context):
    """Execute exact predictions only after approval, then compare captured traces.

    ``fixtures`` contains only stable ``fixture_id`` and development ``transcript``
    fields. Both predictors expose the same ``predict_with_trace`` request API.
    Sample text is used in memory and is not included in the returned aggregate.
    """
    validate_parity_authorization(approved_tolerance=approved_tolerance,
                                  comparison_context=comparison_context)
    if getattr(packaged_predictor, "model_version", None) != comparison_context["packaged_manifest_sha256"]:
        raise ValueError("Packaged predictor version does not match the recorded manifest identity")
    reference_version = getattr(reference_predictor, "model_version", None)
    if reference_version != comparison_context["reference_artifact"]["artifact_id"]:
        raise ValueError("Reference predictor version does not match the recorded final evaluation artifact")
    if not fixtures:
        raise ValueError("Parity requires a nonempty set of development fixtures")
    fixture_ids = [fixture.get("fixture_id") for fixture in fixtures]
    if any(not isinstance(value, str) or not value for value in fixture_ids) or len(fixture_ids) != len(set(fixture_ids)):
        raise ValueError("Fixtures require unique stable fixture IDs")
    if comparison_context["fixture_provenance"]["fixture_ids"] != fixture_ids:
        raise ValueError("Fixture IDs do not match the recorded development provenance")
    reference, packaged = [], []
    for fixture in fixtures:
        if not isinstance(fixture.get("transcript"), str) or not fixture["transcript"].strip():
            raise ValueError("Development fixture transcripts must be nonempty strings")
        request = {"request_id": fixture["fixture_id"], "transcript": fixture["transcript"]}
        left_response, left_trace = reference_predictor.predict_with_trace(request)
        right_response, right_trace = packaged_predictor.predict_with_trace(request)
        if not isinstance(left_response, dict) or left_response.get("request_id") != fixture["fixture_id"]:
            raise ValueError("Reference predictor returned a response for a different fixture")
        if not isinstance(right_response, dict) or right_response.get("request_id") != fixture["fixture_id"]:
            raise ValueError("Packaged predictor returned a response for a different fixture")
        reference.append({**fixture, "response": left_response, "trace": left_trace})
        packaged.append({**fixture, "response": right_response, "trace": right_trace})
    return compare_parity(reference, packaged, approved_tolerance=approved_tolerance,
                          comparison_context=comparison_context)
