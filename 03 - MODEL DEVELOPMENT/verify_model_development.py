#!/usr/bin/env python3
"""Run offline component tests without pretrained weights or final-test inference."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path,
                        help="New verification report path in persistent/local ignored storage")
    parser.add_argument("--include-input-checks", action="store_true",
                        help="Also run the existing offline Plan 02 checks with cached tokenizers")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Preserve previous evidence: choose a new report path")
    config_path = HERE / "input-preparation/preprocessing_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    frozen = {
        ROOT / "02 - DATASETs/prepared/splits/0 - train/dataset.csv": config["training_csv_sha256"],
        ROOT / "02 - DATASETs/prepared/splits/split_assignments.csv": config["assignments_sha256"],
        config_path: digest(config_path),
        HERE / "input-preparation/inputs.py": digest(HERE / "input-preparation/inputs.py"),
    }
    for path, expected in frozen.items():
        if digest(path) != expected:
            parser.error(f"Frozen prerequisite identity mismatch: {path}")
    env = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
               PYTHONDONTWRITEBYTECODE="1")
    commands = []
    for stage in ("training", "selection", "final-evaluation", "handoff"):
        tests = HERE / stage / "tests"
        if not tests.is_dir():
            parser.error(f"Missing stage verification suite: {tests}")
        test_targets = [str(tests)]
        if stage == "training":
            test_targets.append(str(HERE / stage / "test_trainer.py"))
        commands.append((stage, [sys.executable, "-m", "pytest", *test_targets, "-q", "-p", "no:cacheprovider"]))
    if args.include_input_checks:
        commands.append(("input-preparation", [sys.executable, str(HERE / "input-preparation/scripts/9.test_inputs.py")]))
    results = []
    for stage, command in commands:
        print(f"Verifying {stage}…", flush=True)
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
        results.append({"stage": stage, "command": command, "exit_code": result.returncode,
                        "stdout": result.stdout, "stderr": result.stderr})
        print(result.stdout, end="")
        if result.returncode:
            print(result.stderr, file=sys.stderr, end="")
    unchanged = all(digest(path) == expected for path, expected in frozen.items())
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Offline synthetic component verification; no real pretrained diagnostics, search, final-test inference or actual-bundle parity",
        "python": sys.version, "results": results,
        "frozen_prerequisites_unchanged": unchanged,
        "prerequisite_sha256": {str(path.relative_to(ROOT)): expected for path, expected in frozen.items()},
        "passed": unchanged and all(result["exit_code"] == 0 for result in results),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
