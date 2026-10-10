#!/usr/bin/env python3
"""Build a deterministic, training-only Colab source bundle from this checkout.

Only the explicit repository-relative allowlist below is copied. The script
rejects missing inputs, symlinks, unexpected path types, and forbidden paths.
It never opens any path outside that allowlist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath

ARCHIVE_ROOT = "scam-call-alert"

PLAN_FILES = [
    "01 - PLANs/README.md",
    "01 - PLANs/00 - DATA PREPARATION.md",
    "01 - PLANs/01 - DATA SPLIT AND EXPERIMENT DESIGN.md",
    "01 - PLANs/02 - DATA PREPROCESSING AND MODEL INPUTS.md",
    "01 - PLANs/03 - MODEL DEVELOPMENT/00 - MODEL TRAINING.md",
    "01 - PLANs/03 - MODEL DEVELOPMENT/01 - HYPERPARAMETER TUNING AND MODEL SELECTION.md",
    "01 - PLANs/03 - MODEL DEVELOPMENT/02 - FINAL MODEL EVALUATION AND ERROR ANALYSIS.md",
    "01 - PLANs/03 - MODEL DEVELOPMENT/03 - MODEL FREEZE AND APP HANDOFF.md",
]

DATA_DOCS = [
    "02 - DATASETs/README.md",
    "02 - DATASETs/labeling_guideline.md",
    "02 - DATASETs/prepared/README.md",
    "02 - DATASETs/prepared/preparation_report.md",
    "02 - DATASETs/prepared/splits/split_report.md",
    "02 - DATASETs/split_config.json",
    "02 - DATASETs/reports/data_preparation_findings_v1.md",
    "02 - DATASETs/reports/data_quality_v1.md",
    "02 - DATASETs/reports/preparation_csv_v2.md",
    "02 - DATASETs/reports/split_v1.md",
    "02 - DATASETs/reports/stage00_reconciliation.md",
    "02 - DATASETs/scripts/README.md",
]

TRAINING_FILES = [
    "03 - MODEL DEVELOPMENT/training/README.md",
    "03 - MODEL DEVELOPMENT/training/__init__.py",
    "03 - MODEL DEVELOPMENT/training/train.py",
    "03 - MODEL DEVELOPMENT/training/trainer.py",
    "03 - MODEL DEVELOPMENT/training/full_context.py",
    "03 - MODEL DEVELOPMENT/training/tests/test_full_context.py",
    "03 - MODEL DEVELOPMENT/training/tests/test_review_regressions.py",
    "03 - MODEL DEVELOPMENT/training/tests/test_engine_recovery.py",
    "03 - MODEL DEVELOPMENT/training/tests/config_factory.py",
    "03 - MODEL DEVELOPMENT/training/test_trainer.py",
    "03 - MODEL DEVELOPMENT/training/prune_epoch_snapshots.py",
    "03 - MODEL DEVELOPMENT/training/report_truncation.py",
    "03 - MODEL DEVELOPMENT/training/requirements.txt",
    "03 - MODEL DEVELOPMENT/training/run_config.template.json",
    "03 - MODEL DEVELOPMENT/training/training_report.md",
    "03 - MODEL DEVELOPMENT/training/colab/build_training_source_zip.py",
    "03 - MODEL DEVELOPMENT/training/colab/README.md",
]

SELECTION_FILES = [
    "03 - MODEL DEVELOPMENT/selection/README.md",
    "03 - MODEL DEVELOPMENT/selection/WANGCHANBERTA REPRODUCTION GUIDE.md",
    "03 - MODEL DEVELOPMENT/selection/runtime.py",
    "03 - MODEL DEVELOPMENT/selection/workflow.py",
    "03 - MODEL DEVELOPMENT/selection/tests/test_workflow.py",
    "03 - MODEL DEVELOPMENT/selection/cv_results.csv",
    "03 - MODEL DEVELOPMENT/selection/comparison_report.md",
    "03 - MODEL DEVELOPMENT/selection/search_space.json",
    "03 - MODEL DEVELOPMENT/selection/experiment_manifest.csv",
]

INPUT_FILES = [
    "03 - MODEL DEVELOPMENT/input-preparation/README.md",
    "03 - MODEL DEVELOPMENT/input-preparation/inputs.py",
    "03 - MODEL DEVELOPMENT/input-preparation/preprocessing_config.json",
    "03 - MODEL DEVELOPMENT/input-preparation/preprocessing_report.md",
    "03 - MODEL DEVELOPMENT/input-preparation/token_length_report.json",
    "03 - MODEL DEVELOPMENT/input-preparation/scripts/README.md",
    "03 - MODEL DEVELOPMENT/input-preparation/scripts/6.inspect_models.py",
    "03 - MODEL DEVELOPMENT/input-preparation/scripts/7.measure_lengths.py",
    "03 - MODEL DEVELOPMENT/input-preparation/scripts/8.export_inputs.py",
    "03 - MODEL DEVELOPMENT/input-preparation/scripts/9.test_inputs.py",
    "03 - MODEL DEVELOPMENT/input-preparation/prepared/manifest.json",
]

PREPARED_EXPORTS = [
    f"03 - MODEL DEVELOPMENT/input-preparation/prepared/{model}.whole_conversation.{marker}.jsonl"
    for model in ("hplt", "phayathaibert", "wangchanberta", "xlmr")
    for marker in ("role_free", "role_marked")
]

DATA_FILES = [
    "02 - DATASETs/prepared/splits/0 - train/dataset.csv",
    "02 - DATASETs/prepared/splits/split_assignments.csv",
]

# This file contains only the saved 1,164-record training pool. The held-out
# test CSV and full-population source/prepared files are never allowlisted.
TRAINING_READABLE_EXPORT = [
    "03 - MODEL DEVELOPMENT/input-preparation/prepared/training_text.csv",
]
ALLOWLIST = tuple(sorted(set(
    ["AGENTS.md"] + PLAN_FILES + DATA_DOCS + TRAINING_FILES + SELECTION_FILES + INPUT_FILES
    + PREPARED_EXPORTS + DATA_FILES + TRAINING_READABLE_EXPORT
)))

FORBIDDEN_PARTS = {
    ".git", ".env", ".aws", ".codex", ".agents", "__pycache__",
    "runs", "checkpoints", "epoch_models", "final_training", "evaluations",
    "raw", "lecture", "course-lecture-sheets",
}
FORBIDDEN_EXACT = {
    "02 - DATASETs/prepared/splits/1 - test/dataset.csv",
    "02 - DATASETs/prepared/prepared.csv",
    "02 - DATASETs/prepared/source_manifest.csv",
    "03 - MODEL DEVELOPMENT/input-preparation/prepared.csv",
}


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate_path(relative: str) -> PurePosixPath:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise ValueError(f"Unsafe allowlist path: {relative}")
    if relative in FORBIDDEN_EXACT:
        raise ValueError(f"Forbidden file in allowlist: {relative}")
    if any(part in FORBIDDEN_PARTS for part in pure.parts):
        raise ValueError(f"Forbidden path component in allowlist: {relative}")
    if pure.name.lower() in {".env", "credentials", "credentials.json", "secrets.json"}:
        raise ValueError(f"Forbidden sensitive filename: {relative}")
    if "1 - test" in pure.parts:
        raise ValueError(f"Held-out test path is forbidden: {relative}")
    return pure


def collect_payload(project_root: Path) -> list[tuple[str, bytes]]:
    payload = []
    for relative in ALLOWLIST:
        pure = validate_path(relative)
        source = project_root.joinpath(*pure.parts)
        if source.is_symlink() or not source.is_file():
            raise FileNotFoundError(f"Allowlisted input is missing or not a regular file: {relative}")
        payload.append((relative, source.read_bytes()))
    by_path = dict(payload)
    config_path = "03 - MODEL DEVELOPMENT/input-preparation/preprocessing_config.json"
    manifest_path = "03 - MODEL DEVELOPMENT/input-preparation/prepared/manifest.json"
    component_path = "03 - MODEL DEVELOPMENT/input-preparation/inputs.py"
    export_script_path = "03 - MODEL DEVELOPMENT/input-preparation/scripts/8.export_inputs.py"
    training_path = "02 - DATASETs/prepared/splits/0 - train/dataset.csv"
    assignments_path = "02 - DATASETs/prepared/splits/split_assignments.csv"
    config = json.loads(by_path[config_path])
    manifest = json.loads(by_path[manifest_path])
    expected_hashes = {
        "training_csv_sha256": sha256_bytes(by_path[training_path]),
        "assignments_sha256": sha256_bytes(by_path[assignments_path]),
        "configuration_sha256": sha256_bytes(by_path[config_path]),
        "component_sha256": sha256_bytes(by_path[component_path]),
        "export_script_sha256": sha256_bytes(by_path[export_script_path]),
    }
    if config["training_csv_sha256"] != expected_hashes["training_csv_sha256"]:
        raise ValueError("Canonical training CSV differs from the frozen preprocessing configuration")
    if config["assignments_sha256"] != expected_hashes["assignments_sha256"]:
        raise ValueError("Saved assignments differ from the frozen preprocessing configuration")
    for key, digest in expected_hashes.items():
        if manifest.get(key) != digest:
            raise ValueError(f"Prepared-input provenance mismatch: {key}")
    for relative in PREPARED_EXPORTS + TRAINING_READABLE_EXPORT:
        basename = Path(relative).name
        expected = manifest.get("files", {}).get(basename, {}).get("sha256")
        if expected != sha256_bytes(by_path[relative]):
            raise ValueError(f"Prepared export differs from its manifest: {relative}")
    return payload


def create_archive(project_root: Path, archive_path: Path, inventory_path: Path,
                   payload: list[tuple[str, bytes]] | None = None,
                   source_description: str = "explicit training-only allowlist; no filesystem traversal") -> dict:
    payload = collect_payload(project_root) if payload is None else payload
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    if archive_path.resolve() == inventory_path.resolve():
        raise ValueError("Archive and inventory paths must differ")

    inventory = {
        "schema_version": 1,
        "archive_root": ARCHIVE_ROOT,
        "source": source_description,
        "files": [
            {"path": f"{ARCHIVE_ROOT}/{relative}", "size_bytes": len(data),
             "sha256": sha256_bytes(data)}
            for relative, data in payload
        ],
    }
    inventory_bytes = (json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    archive_payload = payload + [("COLAB_SOURCE_INVENTORY.json", inventory_bytes)]

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9, strict_timestamps=True) as archive:
        for relative, data in sorted(archive_payload, key=lambda item: item[0]):
            path = f"{ARCHIVE_ROOT}/{relative}" if relative != "COLAB_SOURCE_INVENTORY.json" else f"{ARCHIVE_ROOT}/{relative}"
            info = zipfile.ZipInfo(path, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    archive_sha = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    full_inventory = {
        **inventory,
        "archive_file": archive_path.name,
        "archive_sha256": archive_sha,
        "archive_size_bytes": archive_path.stat().st_size,
        "inventory_sha256": sha256_bytes(inventory_bytes),
        "archive_entries": [f"{ARCHIVE_ROOT}/{p}" for p, _ in payload]
        + [f"{ARCHIVE_ROOT}/COLAB_SOURCE_INVENTORY.json"],
    }
    inventory_path.write_text(json.dumps(full_inventory, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                              encoding="utf-8")
    verify_archive(archive_path, full_inventory)
    return full_inventory


def verify_archive(archive_path: Path, inventory: dict) -> None:
    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != inventory["archive_sha256"]:
        raise ValueError("Archive SHA-256 changed during verification")
    expected = set(inventory["archive_entries"])
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != expected:
            raise ValueError("Archive entry list differs from the generated inventory")
        bad = archive.testzip()
        if bad is not None:
            raise ValueError(f"ZIP integrity check failed at {bad}")
        for record in inventory["files"]:
            data = archive.read(record["path"])
            if len(data) != record["size_bytes"] or sha256_bytes(data) != record["sha256"]:
                raise ValueError(f"Payload checksum mismatch: {record['path']}")
        packaged_manifest = json.loads(archive.read(f"{ARCHIVE_ROOT}/COLAB_SOURCE_INVENTORY.json"))
        if packaged_manifest != {k: inventory[k] for k in ("schema_version", "archive_root", "source", "files")}:
            raise ValueError("Packaged inventory does not match the external inventory")
        if any("1 - test" in name or name.endswith("/training_text.csv") is False and
               name.endswith("/prepared.csv") for name in names):
            raise ValueError("Archive includes an explicitly forbidden dataset path")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path,
                        default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--name", default="scam-call-alert-colab-training-source.zip")
    args = parser.parse_args()
    if Path(args.name).name != args.name or not args.name.endswith(".zip"):
        parser.error("--name must be a simple .zip filename")
    output_dir = args.output_dir.expanduser().resolve()
    if output_dir == args.project_root.resolve() or args.project_root.resolve() in output_dir.parents:
        parser.error("Output directory must be outside the project checkout")
    archive_path = output_dir / args.name
    inventory_path = output_dir / f"{Path(args.name).stem}.inventory.json"
    inventory = create_archive(args.project_root.resolve(), archive_path, inventory_path)
    print(json.dumps({"archive": str(archive_path), "sha256": inventory["archive_sha256"],
                      "size_bytes": inventory["archive_size_bytes"], "file_count": len(inventory["files"]),
                      "inventory": str(inventory_path)}, indent=2))


if __name__ == "__main__":
    main()
