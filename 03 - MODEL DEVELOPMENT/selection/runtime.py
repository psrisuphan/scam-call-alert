#!/usr/bin/env python3
"""Focused metric aggregation and saved-fold membership validation."""
from __future__ import annotations
import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

FOLDS = tuple(range(5))
PREDICTION_FIELDS = (
    "run_id",
    "configuration_id",
    "run_configuration_id",
    "model_key",
    "data_condition",
    "training_representation",
    "training_marker_condition",
    "validation_representation",
    "validation_marker_condition",
    "fold",
    "epoch",
    "sample_id",
    "source_dataset",
    "true_label",
    "p_not_scam",
    "p_scam",
    "prediction_state",
    "failure_reason",
    "elapsed_seconds",
    "chunk_count",
    "content_token_count",
    "inference_seconds",
    "pooling_method",
)

def _validate_normalized_membership(normalized_path: Path, assignments_path: Path, training_csv_path: Path,
                                   manifest_rows: list[dict[str, str]]) -> None:
    """Bind every normalized prediction to exact saved train-pool membership and metadata."""
    assignments = [row for row in _read_csv(assignments_path) if row.get("split") == "train"]
    train_records = _read_csv(training_csv_path)
    records = {row["sample_id"]: row for row in train_records}
    if len(records) != len(train_records):
        raise ValueError("Training CSV contains duplicate sample IDs")
    expected: dict[int, dict[str, dict[str, str]]] = {fold: {} for fold in FOLDS}
    for assignment in assignments:
        sample_id = assignment["sample_id"]
        fold = int(assignment["cv_fold"])
        record = records.get(sample_id)
        if fold not in FOLDS or record is None:
            raise ValueError(f"Invalid train assignment: {sample_id}")
        if any(sample_id in ids for ids in expected.values()):
            raise ValueError(f"Duplicate train-pool assignment ID: {sample_id}")
        if (record.get("source_dataset") != assignment.get("source_dataset")
                or record.get("label") not in {"Scam", "Not Scam"}):
            raise ValueError(f"Assignment metadata does not match canonical training record: {sample_id}")
        expected[fold][sample_id] = {"source_dataset": record["source_dataset"], "true_label": record["label"]}
    assigned_ids = set().union(*(set(ids) for ids in expected.values()))
    if assigned_ids != set(records) or any(not expected[fold] for fold in FOLDS):
        raise ValueError("Saved training CSV and five-fold train assignments do not have exact nonempty membership")
    by_run = {row["run_id"]: row for row in manifest_rows if row.get("run_id")}
    if len(by_run) != sum(bool(row.get("run_id")) for row in manifest_rows):
        raise ValueError("Manifest contains duplicate run IDs")
    configs: dict[str, dict[str, Any]] = {}
    for run_id, manifest_row in by_run.items():
        artifact = Path(manifest_row.get("artifact_location") or "")
        config_path = artifact / "run_config.json"
        if not config_path.is_file() and manifest_row.get("run_config_path"):
            config_path = Path(manifest_row["run_config_path"]).resolve()
        if not config_path.is_file():
            raise FileNotFoundError(f"Cannot validate normalized membership without run config: {run_id}")
        config = _read_json(config_path)
        if config.get("run_id") != run_id:
            raise ValueError(f"Manifest/run config ID mismatch: {run_id}")
        configs[run_id] = config
    normalized = _read_csv(normalized_path)
    required = set(PREDICTION_FIELDS) | {"evaluation_point", "learning_rate"}
    if normalized and not required.issubset(normalized[0]):
        raise ValueError("Normalized prediction file lacks required identity/membership fields: "
                         + ", ".join(sorted(required - set(normalized[0]))))
    groups: defaultdict[tuple[str, int, int, str], list[dict[str, str]]] = defaultdict(list)
    seen: set[tuple[str, int, int, str]] = set()
    for row in normalized:
        run_id = row.get("run_id", "")
        config = configs.get(run_id)
        if config is None:
            raise ValueError(f"Normalized prediction references a run absent from manifest: {run_id}")
        fold = int(row["fold"])
        epoch = int(row["epoch"])
        marker = row["validation_marker_condition"]
        if fold != int(config.get("fold", -1)) or fold not in FOLDS:
            raise ValueError(f"Normalized prediction is assigned to the wrong fold: {run_id}/{row.get('sample_id')}")
        if epoch < 1 or epoch > int(config.get("training", {}).get("epochs", 0)):
            raise ValueError(f"Normalized prediction epoch exceeds its run config: {run_id}/{epoch}")
        if marker not in {"role_free", "role_marked"}:
            raise ValueError(f"Invalid normalized marker condition: {run_id}/{marker}")
        sample_id = row["sample_id"]
        truth = expected[fold].get(sample_id)
        if truth is None:
            raise ValueError(f"Normalized prediction ID is not assigned to its saved validation fold: {run_id}/{sample_id}")
        if row["source_dataset"] != truth["source_dataset"] or row["true_label"] != truth["true_label"]:
            raise ValueError(f"Normalized source/label differs from canonical train record: {run_id}/{sample_id}")
        search_id = f"{config['model']}__{config['data']['condition']}__lr-{float(config['optimizer']['learning_rate']):.0e}"
        if config.get("training", {}).get("representation") == "caller_only":
            search_id += "__caller_only"
        if (row["configuration_id"] != search_id
                or row["run_configuration_id"] != config.get("configuration_id")
                or row["model_key"] != config.get("model")
                or row["data_condition"] != config.get("data", {}).get("condition")
                or row["training_representation"] != config.get("training", {}).get("representation")
                or row["training_marker_condition"] != config.get("training", {}).get("marker_condition")
                or row["validation_representation"] != config.get("validation", {}).get("representation")
                or float(row.get("learning_rate", -1)) != float(config["optimizer"]["learning_rate"])):
            raise ValueError(f"Normalized prediction config identity mismatch: {run_id}")
        identity = (run_id, fold, epoch, marker, sample_id)
        if identity in seen:
            raise ValueError(f"Duplicate normalized sample prediction: {identity}")
        seen.add(identity)
        groups[(run_id, fold, epoch, marker)].append(row)
    for run_id, config in configs.items():
        fold = int(config["fold"])
        max_epoch = int(config.get("training", {}).get("epochs", 0))
        for epoch in range(1, max_epoch + 1):
            for marker in ("role_free", "role_marked"):
                rows = groups.get((run_id, fold, epoch, marker), [])
                ids = [row["sample_id"] for row in rows]
                if len(ids) != len(expected[fold]) or set(ids) != set(expected[fold]):
                    raise ValueError(f"Normalized validation membership is incomplete for {run_id}/{epoch}/{marker}")

def _number(value: Any) -> float:
    if value is None or str(value).strip() == "":
        raise ValueError("missing numeric value")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("non-finite numeric value")
    return result

def _rates(y_true: list[int], y_pred: list[int]) -> dict[str, Any]:
    tn = sum(t == 0 and p == 0 for t, p in zip(y_true, y_pred))
    fp = sum(t == 0 and p == 1 for t, p in zip(y_true, y_pred))
    fn = sum(t == 1 and p == 0 for t, p in zip(y_true, y_pred))
    tp = sum(t == 1 and p == 1 for t, p in zip(y_true, y_pred))

    def ratio(numerator: int, denominator: int, name: str) -> tuple[float | None, str]:
        if denominator:
            return numerator / denominator, ""
        if y_true:
            return 0.0, f"{name}_undefined_denominator_zero"
        return None, f"{name}_unavailable_empty_subset"

    precision, precision_flag = ratio(tp, tp + fp, "scam_precision")
    recall, recall_flag = ratio(tp, tp + fn, "scam_recall")
    f1, f1_flag = ratio(2 * tp, 2 * tp + fp + fn, "scam_f1")
    not_scam_f1, not_scam_flag = ratio(2 * tn, 2 * tn + fp + fn, "not_scam_f1")
    accuracy, accuracy_flag = ratio(tp + tn, len(y_true), "accuracy")
    macro_f1 = (f1 + not_scam_f1) / 2 if y_true else None
    flags = ";".join(
        flag
        for flag in (precision_flag, recall_flag, f1_flag, not_scam_flag, accuracy_flag)
        if flag
    )
    return {
        "n_assigned": len(y_true),
        "n_successful": len(y_true),
        "n_failed": 0,
        "true_not_scam": sum(value == 0 for value in y_true),
        "true_scam": sum(value == 1 for value in y_true),
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
        "scam_precision": precision,
        "scam_recall": recall,
        "scam_f1": f1,
        "macro_f1": macro_f1,
        "accuracy": accuracy,
        "undefined_metric_flags": flags,
    }

def _metric_row(group: list[dict[str, str]], *, subset: str, source: str, row_type: str,
                template: dict[str, str] | None = None) -> dict[str, Any]:
    representative = group[0] if group else template
    if representative is None:
        raise ValueError("empty metric subset requires a representative row for identity")
    if not group:
        return {
            "row_type": row_type, "subset": subset, "source_dataset": source,
            "configuration_id": representative["configuration_id"], "model_key": representative["model_key"],
            "data_condition": representative["data_condition"],
            "training_representation": representative["training_representation"],
            "training_marker_condition": representative["training_marker_condition"],
            "validation_representation": representative["validation_representation"],
            "validation_marker_condition": representative["validation_marker_condition"],
            "fold": representative["fold"], "epoch": representative["epoch"],
            "learning_rate": representative.get("learning_rate", ""),
            "n_assigned": 0, "n_successful": 0, "n_failed": 0,
            "assigned_true_not_scam": 0, "assigned_true_scam": 0,
            "true_not_scam": 0, "true_scam": 0, "tn": 0, "fp": 0, "fn": 0, "tp": 0,
            "scam_precision": "", "scam_recall": "", "scam_f1": "", "macro_f1": "",
            "accuracy": "", "undefined_metric_flags": "metrics_unavailable_empty_subset",
            "elapsed_seconds": "", "failure_reasons": "{}",
        }
    successful: list[tuple[int, int]] = []
    failures = 0
    ids: set[str] = set()
    elapsed = []
    failure_reasons: defaultdict[str, int] = defaultdict(int)
    for row in group:
        sample_id = row["sample_id"].strip()
        if not sample_id or sample_id in ids:
            raise ValueError(f"duplicate or blank sample_id in {row_type}/{subset}/{source}: {sample_id!r}")
        ids.add(sample_id)
        label = row["true_label"].strip()
        if label not in {"Scam", "Not Scam"}:
            raise ValueError(f"invalid true_label for {sample_id}: {label!r}")
        if row["prediction_state"].strip() != "success":
            failures += 1
            failure_reasons[row.get("failure_reason", "").strip() or "unspecified"] += 1
            continue
        p0, p1 = _number(row["p_not_scam"]), _number(row["p_scam"])
        if not (0 <= p0 <= 1 and 0 <= p1 <= 1) or abs(p0 + p1 - 1) > 1e-5:
            raise ValueError(f"invalid probability pair for {sample_id}")
        predicted = 1 if p1 >= 0.5 else 0
        successful.append((1 if label == "Scam" else 0, predicted))
        try:
            elapsed.append(_number(row.get("elapsed_seconds")))
        except ValueError:
            pass

    y_true = [item[0] for item in successful]
    y_pred = [item[1] for item in successful]
    metrics = _rates(y_true, y_pred)
    # Class support on all assigned records remains visible even when failures occur.
    metrics["n_assigned"] = len(group)
    metrics["n_successful"] = len(successful)
    metrics["n_failed"] = failures
    metrics["assigned_true_not_scam"] = sum(row["true_label"].strip() == "Not Scam" for row in group)
    metrics["assigned_true_scam"] = sum(row["true_label"].strip() == "Scam" for row in group)
    metrics["elapsed_seconds"] = statistics.fmean(elapsed) if elapsed else ""
    metrics["failure_reasons"] = json.dumps(dict(sorted(failure_reasons.items())), ensure_ascii=False)
    return {
        "row_type": row_type,
        "subset": subset,
        "source_dataset": source,
        "configuration_id": representative["configuration_id"],
        "model_key": representative["model_key"],
        "data_condition": representative["data_condition"],
        "training_representation": representative["training_representation"],
        "training_marker_condition": representative["training_marker_condition"],
        "validation_representation": representative["validation_representation"],
        "validation_marker_condition": representative["validation_marker_condition"],
        "fold": representative["fold"],
        "epoch": representative["epoch"],
        "learning_rate": representative.get("learning_rate", ""),
        **metrics,
    }

def aggregate(args: argparse.Namespace) -> None:
    source = Path(args.predictions).resolve()
    rows = _read_csv(source)
    missing = sorted(set(PREDICTION_FIELDS) - set(rows[0] if rows else []))
    if missing:
        raise ValueError("prediction CSV missing required columns: " + ", ".join(missing))
    groups: defaultdict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        try:
            fold = int(row["fold"])
            epoch = int(row["epoch"])
        except ValueError as exc:
            raise ValueError("fold and epoch must be integers") from exc
        if fold not in FOLDS or epoch < 1:
            raise ValueError(f"unexpected fold/epoch: {fold}/{epoch}")
        if row["training_representation"] not in {"whole_conversation", "caller_only"} or row["training_marker_condition"] != "role_marked":
            raise ValueError("unsupported training representation or marker condition")
        if row["validation_representation"] not in {"whole_conversation", "caller_only"}:
            raise ValueError("unsupported validation representation")
        if row["training_representation"] != row["validation_representation"]:
            raise ValueError("training and validation representations must match")
        if row["validation_marker_condition"] not in {"role_free", "role_marked"}:
            raise ValueError("validation_marker_condition must be role_free or role_marked")
        key = (
            row["configuration_id"], row["model_key"], row["data_condition"],
            row["training_representation"], row["training_marker_condition"],
            row["validation_representation"], row["validation_marker_condition"],
            str(fold), str(epoch),
        )
        groups[key].append(row)

    output_rows: list[dict[str, Any]] = []
    for key, group in sorted(groups.items()):
        _, _, _, _, _, _, marker, fold, _ = key
        output_rows.append(_metric_row(group, subset="combined", source="all", row_type="fold"))
        sources = ("primary", "supplemental")
        for source_name in sources:
            output_rows.append(
                _metric_row([row for row in group if row["source_dataset"] == source_name], subset="source", source=source_name, row_type="fold", template=group[0])
            )

    # One aggregate per condition/epoch/subset across five complete, successful folds.
    fold_combined: defaultdict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in output_rows:
        if row["row_type"] == "fold":
            key = tuple(str(row[name]) for name in (
                "configuration_id", "model_key", "data_condition", "training_representation",
                "training_marker_condition", "validation_representation", "validation_marker_condition",
                "epoch", "subset", "source_dataset",
            ))
            fold_combined[key].append(row)
    for key, fold_rows in sorted(fold_combined.items()):
        fold_numbers = {int(row["fold"]) for row in fold_rows}
        complete = len(fold_numbers) == 5 and len(fold_rows) == 5 and all(int(row["n_failed"]) == 0 for row in fold_rows)
        first = fold_rows[0]
        metrics_available = complete and all(row.get("scam_f1") not in ("", None) for row in fold_rows)
        metrics = [float(row["scam_f1"]) for row in fold_rows] if metrics_available else []
        output_rows.append({
            **{name: first[name] for name in (
                "subset", "source_dataset", "configuration_id", "model_key", "data_condition",
                "training_representation", "training_marker_condition", "validation_representation",
                "validation_marker_condition", "epoch", "learning_rate",
            )},
            "row_type": "aggregate",
            "fold": "all_five" if complete else "incomplete",
            "n_assigned": sum(int(row["n_assigned"]) for row in fold_rows),
            "n_successful": sum(int(row["n_successful"]) for row in fold_rows),
            "n_failed": sum(int(row["n_failed"]) for row in fold_rows),
            "assigned_true_not_scam": sum(int(row["assigned_true_not_scam"]) for row in fold_rows),
            "assigned_true_scam": sum(int(row["assigned_true_scam"]) for row in fold_rows),
            "scam_f1_mean": statistics.fmean(metrics) if metrics_available else "",
            "scam_f1_sample_sd": statistics.stdev(metrics) if len(metrics) > 1 else "",
            "scam_f1_fold_values": json.dumps(metrics),
            "complete_five_folds": str(complete).lower(),
            "undefined_metric_flags": "",
            "failure_reasons": "",
            "elapsed_seconds": sum(float(row["elapsed_seconds"] or 0) for row in fold_rows),
        })

    fields = [
        "row_type", "subset", "source_dataset", "configuration_id", "model_key", "data_condition",
        "training_representation", "training_marker_condition", "validation_representation",
        "validation_marker_condition", "fold", "epoch", "learning_rate", "n_assigned", "n_successful",
        "n_failed", "assigned_true_not_scam", "assigned_true_scam", "true_not_scam", "true_scam",
        "tn", "fp", "fn", "tp", "scam_precision", "scam_recall", "scam_f1", "macro_f1", "accuracy",
        "scam_f1_mean", "scam_f1_sample_sd", "scam_f1_fold_values", "complete_five_folds",
        "undefined_metric_flags", "failure_reasons", "elapsed_seconds",
    ]
    _write_csv(Path(args.output).resolve(), fields, output_rows)
    print(f"Aggregated {len(rows)} prediction rows into {len(output_rows)} metric rows.")

def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))

def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("aggregate-predictions", nargs="?")
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    aggregate(argparse.Namespace(predictions=args.predictions, output=args.output))
