#!/usr/bin/env python3
"""Plan-aligned manifest creation and import of verified aggregate CV evidence.

This utility never trains a model, loads evaluation-test data, or imports
sample-level predictions. The source export and its hashes remain the authority
for imported results; generated tables are development-validation summaries.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODELS = ("wangchanberta", "phayathaibert", "hplt", "xlmr")
RATES = (2e-5, 3e-5, 5e-5)
FOLDS = range(5)
POOLING = {"wangchanberta": ("max", "mean"), "phayathaibert": ("",), "hplt": ("",), "xlmr": ("",)}
MANIFEST_FIELDS = [
    "experiment_id", "run_id", "configuration_id", "model_key", "checkpoint",
    "checkpoint_revision", "data_condition", "training_representation",
    "training_marker_condition", "validation_representation",
    "validation_marker_condition", "input_policy", "max_content_tokens", "overlap_tokens",
    "pooling_method", "fold", "training_seed", "learning_rate", "purpose",
    "execution_state", "artifact_location", "run_config_sha256", "history_sha256",
    "predictions_sha256", "source_export_sha256", "epochs_completed", "optimizer_updates",
    "failure_reason", "attempt_history_json",
]
RESULT_FIELDS = [
    "row_type", "configuration_id", "data_condition", "training_representation",
    "training_marker_condition", "validation_representation", "validation_marker_condition",
    "input_policy", "pooling_method", "fold", "epoch", "evaluated_subset", "n",
    "n_not_scam", "n_scam", "n_primary", "n_supplemental", "scam_precision",
    "scam_recall", "scam_f1", "macro_f1", "accuracy", "training_loss",
    "validation_loss", "sample_sd_scam_f1", "source_export_sha256",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def make_manifest(search_path: Path, preprocessing_path: Path, output: Path) -> None:
    search = read_json(search_path)
    prep = read_json(preprocessing_path)
    expected = (search.get("models"), search.get("learning_rates"), search.get("folds"),
                search.get("training_seed"), search.get("data_conditions"))
    if expected != (list(MODELS), list(RATES), list(FOLDS), 67, ["primary_only"]):
        raise ValueError("search_space.json does not match the approved primary-only comparison")
    unresolved_gates = [name for name, gate in search.get("execution_gates", {}).items()
                        if gate.get("status") != "approved"]
    initial_state = "blocked_by_gates" if unresolved_gates else "not_started"
    rows: list[dict[str, Any]] = []
    for model in MODELS:
        identity = prep.get("models", {}).get(model, {})
        if not identity.get("checkpoint") or not identity.get("revision"):
            raise ValueError(f"Missing pinned checkpoint identity for {model}")
        for pooling in POOLING[model]:
            for lr in RATES:
                config_id = f"{model}__primary_only__lr-{lr:.0e}" + (f"__pool-{pooling}" if pooling else "")
                purpose = "initial_reference_and_search" if lr == 3e-5 else "search"
                for fold in FOLDS:
                    run_id = f"selection-primary-{model}-lr-{lr:.0e}" + (f"-pool-{pooling}" if pooling else "") + f"-fold-{fold}"
                    rows.append({
                        "experiment_id": f"{config_id}__fold-{fold}", "run_id": "",
                        "configuration_id": config_id, "model_key": model,
                        "checkpoint": identity["checkpoint"], "checkpoint_revision": identity["revision"],
                        "data_condition": "primary_only", "training_representation": "whole_conversation",
                        "training_marker_condition": "role_marked", "validation_representation": "whole_conversation",
                        "validation_marker_condition": "paired_role_free_and_role_marked",
                        "input_policy": "wangchan_full_context_v1" if model == "wangchanberta" else "candidate_policy_pending_review",
                        "max_content_tokens": 508 if model == "wangchanberta" else "",
                        "overlap_tokens": 127 if model == "wangchanberta" else "",
                        "pooling_method": pooling, "fold": fold, "training_seed": 67,
                        "learning_rate": lr, "purpose": purpose, "execution_state": initial_state,
                        "artifact_location": "", "run_config_sha256": "", "history_sha256": "",
                        "predictions_sha256": "", "source_export_sha256": "", "epochs_completed": "",
                        "optimizer_updates": "", "failure_reason": "", "attempt_history_json": "[]",
                    })
    if len(rows) != 75 or len({r["experiment_id"] for r in rows}) != 75:
        raise ValueError("Generated matrix must contain 75 unique primary-only fits")
    write_csv(output, MANIFEST_FIELDS, rows)
    print(f"Wrote {len(rows)} primary-only fit rows; no training was launched.")


def import_verified_export(export_path: Path, manifest_path: Path, results_path: Path) -> None:
    export = read_json(export_path)
    if export.get("status") != "verified_five_fold_epoch3":
        raise ValueError("Only the verified five-fold epoch-3 export can be imported")
    settings = export.get("approved_settings", {})
    expected = {
        "model": "wangchanberta", "data_condition": "primary_only", "learning_rate": 2e-5,
        "training_representation": "whole_conversation", "training_marker_condition": "role_marked",
        "validation_marker_conditions": ["role_free", "role_marked"], "pooling_method": "max",
        "seed": 67, "scam_threshold": 0.5, "epoch": 3,
    }
    if settings != expected:
        raise ValueError("Existing run settings do not exactly match the approved WangchanBERTa configuration")
    folds = export.get("folds", [])
    if [item.get("fold") for item in folds] != list(FOLDS):
        raise ValueError("Export must contain folds 0 through 4 exactly once and in order")
    aggregates = export.get("aggregates", {})
    aggregate_epoch = aggregates.get("3", {})
    if set(aggregate_epoch) != {"role_free", "role_marked"}:
        raise ValueError("Epoch-3 aggregate must contain both validation marker conditions")
    manifest = list(csv.DictReader(manifest_path.open(newline="", encoding="utf-8")))
    export_hash = sha256(export_path)
    config_id = export.get("configuration_id")
    expected_id = "wangchanberta__primary_only__lr-2e-05__pool-max"
    if config_id != expected_id:
        raise ValueError(f"Unexpected existing configuration: {config_id}")
    targets = [r for r in manifest if r["configuration_id"] == config_id]
    if len(targets) != 5:
        raise ValueError("Manifest must contain exactly five rows for the imported configuration")
    by_fold = {int(r["fold"]): r for r in targets}
    for item in folds:
        fold = int(item["fold"])
        expected_run_id = f"selection-pilot-wangchanberta-primary-only-lr-2e-05-pool-max-fold-{fold}"
        if item.get("run_id") != expected_run_id:
            raise ValueError(f"Fold {fold} run identity differs from the verified export")
        for key in ("run_config_sha256", "history_sha256", "predictions_sha256"):
            value = item.get(key)
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(f"Fold {fold} has invalid {key}")
        if item.get("epochs_completed") != 3 or item.get("optimizer_updates", 0) <= 0:
            raise ValueError(f"Fold {fold} does not show a complete three-epoch run")
        row = by_fold[fold]
        if row["execution_state"] not in {"not_started", "blocked_by_gates", "completed"}:
            raise ValueError(f"Fold {fold} already has another execution state; refusing overwrite")
        row.update({
            "run_id": item["run_id"], "execution_state": "completed",
            "artifact_location": item["artifact_location"],
            "run_config_sha256": item["run_config_sha256"], "history_sha256": item["history_sha256"],
            "predictions_sha256": item["predictions_sha256"], "source_export_sha256": export_hash,
            "epochs_completed": item["epochs_completed"], "optimizer_updates": item["optimizer_updates"],
            "attempt_history_json": json.dumps([{
                "run_id": item["run_id"], "status": "completed", "epochs_completed": 3,
                "run_config_sha256": item["run_config_sha256"], "history_sha256": item["history_sha256"],
                "predictions_sha256": item["predictions_sha256"], "source_export_sha256": export_hash,
                "evidence_completeness": "verified aggregate export; raw sample predictions remain in persistent Drive",
            }], separators=(",", ":")),
        })
    write_csv(manifest_path, MANIFEST_FIELDS, manifest)

    rows: list[dict[str, Any]] = []
    config_fields = {
        "configuration_id": config_id, "data_condition": "primary_only",
        "training_representation": "whole_conversation", "training_marker_condition": "role_marked",
        "validation_representation": "whole_conversation", "input_policy": "wangchan_full_context_v1",
        "pooling_method": "max", "epoch": 3, "evaluated_subset": "combined_sources",
        "source_export_sha256": export_hash,
    }
    for item in folds:
        for marker in ("role_free", "role_marked"):
            metric = item["epoch3_metrics_by_marker"][marker]
            rows.append({"row_type": "fold", **config_fields, "validation_marker_condition": marker,
                         "fold": item["fold"], **metric})
    for epoch_key in sorted(aggregates, key=int):
        for marker in ("role_free", "role_marked"):
            metric_aggregate = aggregates[epoch_key][marker]
            means = {key: value["mean"] for key, value in metric_aggregate.items()
                     if isinstance(value, dict) and "mean" in value}
            f1_sd = metric_aggregate["scam_f1"]["sample_sd"]
            rows.append({"row_type": "mean_and_sample_sd", **config_fields,
                         "validation_marker_condition": marker, "fold": "5-fold mean ± sample SD",
                         "epoch": int(epoch_key), **means, "sample_sd_scam_f1": f1_sd})
    write_csv(results_path, RESULT_FIELDS, rows)
    print(f"Imported the existing five-fold result into {manifest_path}; wrote {len(rows)} aggregate-evidence rows to {results_path}. No training was launched.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    planned = commands.add_parser("manifest", help="write the approved 75-fit primary-only manifest")
    planned.add_argument("--search-space", type=Path, default=HERE / "search_space.json")
    planned.add_argument("--preprocessing", type=Path, default=ROOT / "03 - MODEL DEVELOPMENT/input-preparation/preprocessing_config.json")
    planned.add_argument("--output", type=Path, default=HERE / "experiment_manifest.csv")
    planned.set_defaults(func=lambda a: make_manifest(a.search_space, a.preprocessing, a.output))
    imported = commands.add_parser("import-verified-export", help="import existing verified aggregate evidence without rerunning")
    imported.add_argument("--export", type=Path, required=True)
    imported.add_argument("--manifest", type=Path, default=HERE / "experiment_manifest.csv")
    imported.add_argument("--results", type=Path, default=HERE / "cv_results.csv")
    imported.set_defaults(func=lambda a: import_verified_export(a.export, a.manifest, a.results))
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
