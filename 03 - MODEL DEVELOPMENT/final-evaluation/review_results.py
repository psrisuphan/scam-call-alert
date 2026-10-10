#!/usr/bin/env python3
"""Audit saved final predictions/errors and render figures; never run a model."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def rows(path):
    with Path(path).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(predictions, errors, assignments, original_errors=None):
    """Require all held-out assignment IDs, preserve failures, verify every FP/FN."""
    expected = {row["sample_id"]: row for row in assignments if row["split"] == "test"}
    if not expected:
        raise ValueError("No held-out assignments supplied")
    seen, mistakes = {}, {}
    evaluations, versions = set(), set()
    for row in predictions:
        cid = row["sample_id"]
        if cid in seen or cid not in expected:
            raise ValueError("Duplicate or unassigned final prediction ID")
        seen[cid] = row
        if row["source_dataset"] != expected[cid]["source_dataset"]:
            raise ValueError("Prediction source differs from the saved assignment")
        if row["true_label"] not in ("Not Scam", "Scam"):
            raise ValueError("Invalid true class")
        if not row.get("evaluation_id") or not row.get("artifact_id"):
            raise ValueError("Every outcome requires evaluation and artifact identities")
        evaluations.add(row["evaluation_id"])
        versions.add(row["artifact_id"])
        if float(row["threshold"]) != 0.5:
            raise ValueError("Final threshold differs from the approved value")
        state = row["execution_state"]
        if state == "success":
            p0, p1 = float(row["p_not_scam"]), float(row["p_scam"])
            if not all(math.isfinite(p) and 0 <= p <= 1 for p in (p0, p1)) or abs(p0 + p1 - 1) > 1e-5:
                raise ValueError("Invalid final probability pair")
            label = "Scam" if p1 >= 0.5 else "Not Scam"
            if row["predicted_label"] != label:
                raise ValueError("Prediction disagrees with the frozen threshold")
            if label != row["true_label"]:
                mistakes[cid] = row
        elif state == "failure":
            if any(row.get(field) not in (None, "") for field in ("p_not_scam", "p_scam", "predicted_label")):
                raise ValueError("Execution failure contains invented predictions")
            if not row.get("failure_reason"):
                raise ValueError("Failure reason is required")
        else:
            raise ValueError("Unknown outcome execution state")
    if set(seen) != set(expected):
        raise ValueError("Not every assigned final record has an outcome")
    if len(evaluations) != 1 or len(versions) != 1:
        raise ValueError("Mixed final evaluation or artifact identities")
    if original_errors is not None:
        originals = {row["sample_id"]: row for row in original_errors}
        if len(originals) != len(original_errors):
            raise ValueError("Duplicate original error evidence")
        immutable = ("evaluation_id", "sample_id", "source_dataset", "prediction_artifact_reference", "error_type",
                     "true_label", "predicted_label", "p_scam", "threshold", "transcript_evidence", "input_length_findings")
        for error in errors:
            original = originals.get(error["sample_id"])
            if original is None or any(error.get(field) != original.get(field) for field in immutable):
                raise ValueError("Reviewed copy changed immutable original error evidence")
        if {row["sample_id"] for row in errors} != set(originals):
            raise ValueError("Reviewed copy does not cover original errors")
    error_ids, pending = set(), []
    required_review = ("observed_error_category", "review_explanation", "review_evidence", "uncertainty",
                       "potential_future_investigation")
    for error in errors:
        cid = error["sample_id"]
        if cid in error_ids or cid not in mistakes:
            raise ValueError("Error analysis contains a duplicate or non-error record")
        error_ids.add(cid)
        outcome = mistakes[cid]
        for field in ("evaluation_id", "source_dataset", "true_label", "predicted_label"):
            if error.get(field) != outcome[field]:
                raise ValueError("Error evidence differs from its original prediction")
        if float(error["p_scam"]) != float(outcome["p_scam"]):
            raise ValueError("Error-analysis probability was changed")
        kind = "false_negative" if outcome["true_label"] == "Scam" else "false_positive"
        if error["error_type"] != kind or not error.get("transcript_evidence"):
            raise ValueError("Error kind or traceable transcript evidence is missing")
        if error.get("review_status") != "reviewed" or any(not error.get(field, "").strip() for field in required_review):
            pending.append(cid)
    if error_ids != set(mistakes):
        raise ValueError("Every false positive and false negative must be preserved")
    return {"assigned": len(expected), "successful": sum(row["execution_state"] == "success" for row in predictions),
            "failed": sum(row["execution_state"] == "failure" for row in predictions),
            "classification_errors": len(mistakes), "pending_error_reviews": pending,
            "error_review_complete": not pending, "coverage_verified": True}


def figures(metrics, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for name, values in [("combined", metrics["combined"]), *metrics["by_source"].items()]:
        matrix = [[values["tn"], values["fp"]], [values["fn"], values["tp"]]]
        fig, ax = plt.subplots(figsize=(5.5, 4.5), constrained_layout=True)
        ax.imshow(matrix, cmap="Blues", vmin=0, vmax=max(1, max(map(max, matrix))))
        for row in range(2):
            for col in range(2):
                ax.text(col, row, str(matrix[row][col]), ha="center", va="center", fontsize=14)
        ax.set(xticks=[0, 1], yticks=[0, 1], xticklabels=["Not Scam", "Scam"],
               yticklabels=["Not Scam", "Scam"], xlabel="Predicted class", ylabel="True class",
               title=f"Final text test — {name}\nSuccessful {values['successful']}/{values['assigned']}; failures {values['failed']}")
        fig.savefig(output / f"confusion_matrix_{name}.png", dpi=180)
        fig.savefig(output / f"confusion_matrix_{name}.pdf")
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--errors", required=True, type=Path)
    parser.add_argument("--original-errors", required=True, type=Path,
                        help="Unchanged initial error_analysis.csv; --errors is its separate review copy")
    parser.add_argument("--assignments", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path,
                        help="New report generation location; originals remain unchanged")
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Choose a new generation path; do not overwrite evidence")
    sources = (args.predictions, args.errors, args.original_errors, args.assignments)
    originals = {str(path.resolve()): digest(path) for path in sources}
    predictions, errors, assigned = rows(args.predictions), rows(args.errors), rows(args.assignments)
    result = audit(predictions, errors, assigned, rows(args.original_errors))
    spec = importlib.util.spec_from_file_location("scam_final_evaluation_analysis", HERE / "evaluation.py")
    evaluation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluation)
    metrics = evaluation.compute_metrics(predictions)
    args.output_dir.mkdir(parents=True)
    figures(metrics, args.output_dir / "figures")
    result.update({"source_sha256": originals,
                   "source_files": {"predictions": str(args.predictions.resolve()),
                                    "reviewed_errors": str(args.errors.resolve()),
                                    "original_errors": str(args.original_errors.resolve()),
                                    "assignments": str(args.assignments.resolve())},
                   "metrics": metrics,
                   "scope": "Saved final text evidence only; does not authorize retuning or prove other plan gates"})
    (args.output_dir / "review_audit.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    if originals != {str(path.resolve()): digest(path) for path in sources}:
        raise RuntimeError("Original evidence changed during review")
    print(f"Coverage verified; {len(result['pending_error_reviews'])} classification errors still need documented review")


if __name__ == "__main__":
    main()
