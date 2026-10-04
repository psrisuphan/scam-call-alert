"""Export training-only readable text and unpadded model inputs."""
from pathlib import Path
import argparse
import csv
import importlib.metadata
import json
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import inputs

DEFAULT_OUTPUT = inputs.DEFAULT_CONFIG.parent / "prepared"


def export(output=DEFAULT_OUTPUT):
    output = Path(output)
    if output.exists():
        raise FileExistsError("Prepared inputs exist; use a separate output folder to rebuild")
    config = inputs.load_config()
    for package, version in config["dependencies"].items():
        if importlib.metadata.version(package) != version:
            raise ValueError(f"Use {package}=={version}")
    records = inputs.load_partition("train_pool", config=config)
    assignments = {r["sample_id"]: r for r in inputs.read_csv(
        inputs.DEFAULT_DATA / "split_assignments.csv", inputs.ASSIGNMENT_COLUMNS)}
    # Check complete speaker coverage before creating an export.
    for record in records:
        inputs.parse_turns(record, config)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".input-export-", dir=output.parent) as temporary:
        staging = Path(temporary) / "prepared"
        staging.mkdir()
        columns = ["sample_id", "source_dataset", "cv_fold", "label", "label_id",
                   "original_transcript"] + [f"{mode}.{marker}" for mode in config["representations"]
                                            for marker in config["marker_conditions"]]
        with (staging / "training_text.csv").open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            for record in records:
                writer.writerow({
                    "sample_id": record["sample_id"], "source_dataset": record["source_dataset"],
                    "cv_fold": assignments[record["sample_id"]]["cv_fold"],
                    "label": record["label"], "label_id": inputs.LABEL_TO_ID[record["label"]],
                    "original_transcript": record["transcript"],
                    **{f"{mode}.{marker}": inputs.representation(record, mode, config, marker_condition=marker)
                       for mode in config["representations"] for marker in config["marker_conditions"]},
                })
        manifest = {
            "scope": "training pool only; final test not loaded",
            "records": len(records), "configuration_sha256": inputs.checksum(inputs.DEFAULT_CONFIG),
            "training_csv_sha256": config["training_csv_sha256"],
            "assignments_sha256": config["assignments_sha256"],
            "component_sha256": inputs.checksum(Path(inputs.__file__)),
            "export_script_sha256": inputs.checksum(Path(__file__)),
            "dependencies": config["dependencies"],
            "models": config["models"], "representations": config["representations"],
            "marker_conditions": config["marker_conditions"], "files": {},
        }
        for model in config["models"]:
            tokenizer = inputs.load_tokenizer(model, config, local_files_only=True)
            for mode in config["representations"]:
                for marker_condition in config["marker_conditions"]:
                    path = staging / f"{model}.{mode}.{marker_condition}.jsonl"
                    with path.open("w", encoding="utf-8", newline="") as file:
                        for record in records:
                            item = inputs.tokenized_record(record, mode, model, config, tokenizer, marker_condition=marker_condition)
                            membership = assignments[record["sample_id"]]
                            item.update(source_dataset=record["source_dataset"], split="train",
                                        group_id=membership["group_id"], cv_fold=int(membership["cv_fold"]))
                            file.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
        for path in sorted(staging.iterdir()):
            manifest["files"][path.name] = {"sha256": inputs.checksum(path), "records": len(records)}
        (staging / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if output.exists():
            raise FileExistsError("Prepared inputs appeared during export; refusing replacement")
        staging.rename(output)
    print(f"Exported {len(records)} training records, four readable conditions, and sixteen unpadded input files to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="New output folder; existing folders are never replaced")
    export(parser.parse_args().output)
