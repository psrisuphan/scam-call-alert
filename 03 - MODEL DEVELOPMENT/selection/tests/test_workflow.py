import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import workflow


ROOT = Path(__file__).resolve().parents[3]
def synthetic_export():
    metrics = {
        "n": 20, "n_not_scam": 10, "n_scam": 10, "n_primary": 20, "n_supplemental": 0,
        "scam_precision": 0.8, "scam_recall": 0.9, "scam_f1": 0.85,
        "macro_f1": 0.84, "accuracy": 0.85, "training_loss": 0.1, "validation_loss": 0.2,
    }
    return {
        "status": "verified_five_fold_epoch3",
        "configuration_id": "wangchanberta__primary_only__lr-2e-05__pool-max",
        "approved_settings": {
            "model": "wangchanberta", "data_condition": "primary_only", "learning_rate": 2e-5,
            "training_representation": "whole_conversation", "training_marker_condition": "role_marked",
            "validation_marker_conditions": ["role_free", "role_marked"], "pooling_method": "max",
            "seed": 67, "scam_threshold": 0.5, "epoch": 3,
        },
        "folds": [{
            "fold": fold,
            "run_id": f"selection-pilot-wangchanberta-primary-only-lr-2e-05-pool-max-fold-{fold}",
            "artifact_location": f"/persistent/run-{fold}",
            "run_config_sha256": "a" * 64, "history_sha256": "b" * 64,
            "predictions_sha256": "c" * 64, "epochs_completed": 3, "optimizer_updates": 15,
            "epoch3_metrics_by_marker": {"role_free": {**metrics, "scam_f1": 0.8 + fold / 100},
                                         "role_marked": metrics},
        } for fold in range(5)],
        "aggregates": {str(epoch): {
            "role_free": {key: {"mean": value, "sample_sd": 0.01} for key, value in {
                "scam_precision": 0.8, "scam_recall": 0.9, "scam_f1": 0.82,
                "macro_f1": 0.81, "accuracy": 0.82, "training_loss": 0.1, "validation_loss": 0.2,
            }.items()},
            "role_marked": {key: {"mean": value, "sample_sd": 0.01} for key, value in {
                "scam_precision": 0.8, "scam_recall": 0.9, "scam_f1": 0.85,
                "macro_f1": 0.84, "accuracy": 0.85, "training_loss": 0.1, "validation_loss": 0.2,
            }.items()},
        } for epoch in (1, 2, 3)},
    }


class WorkflowTests(unittest.TestCase):
    def test_manifest_is_75_primary_only_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "manifest.csv"
            workflow.make_manifest(workflow.HERE / "search_space.json",
                                   ROOT / "03 - MODEL DEVELOPMENT/input-preparation/preprocessing_config.json",
                                   output)
            rows = list(csv.DictReader(output.open(newline="", encoding="utf-8")))
        self.assertEqual(len(rows), 75)
        self.assertEqual({r["data_condition"] for r in rows}, {"primary_only"})
        self.assertEqual(sum(r["model_key"] == "wangchanberta" for r in rows), 30)
        self.assertEqual({r["pooling_method"] for r in rows if r["model_key"] == "wangchanberta"}, {"max", "mean"})
        self.assertEqual({r["execution_state"] for r in rows}, {"blocked_by_gates"})

    def test_import_marks_only_existing_five_folds_and_writes_scores(self):
        with tempfile.TemporaryDirectory() as folder:
            manifest = Path(folder) / "manifest.csv"
            results = Path(folder) / "results.csv"
            workflow.make_manifest(workflow.HERE / "search_space.json",
                                   ROOT / "03 - MODEL DEVELOPMENT/input-preparation/preprocessing_config.json",
                                   manifest)
            export = Path(folder) / "export.json"
            export.write_text(json.dumps(synthetic_export()), encoding="utf-8")
            workflow.import_verified_export(export, manifest, results)
            rows = list(csv.DictReader(manifest.open(newline="", encoding="utf-8")))
            scores = list(csv.DictReader(results.open(newline="", encoding="utf-8")))
        completed = [r for r in rows if r["execution_state"] == "completed"]
        self.assertEqual(len(completed), 5)
        self.assertEqual({r["run_id"] for r in completed}, {
            f"selection-pilot-wangchanberta-primary-only-lr-2e-05-pool-max-fold-{fold}"
            for fold in range(5)
        })
        self.assertEqual(len(scores), 16)
        aggregate = next(r for r in scores if r["row_type"] == "mean_and_sample_sd"
                         and r["validation_marker_condition"] == "role_free" and r["epoch"] == "3")
        self.assertAlmostEqual(float(aggregate["scam_f1"]), 0.82)
        self.assertAlmostEqual(float(aggregate["sample_sd_scam_f1"]), 0.01)
        self.assertEqual({r["model_key"] for r in rows if r["execution_state"] == "completed"}, {"wangchanberta"})

    def test_import_rejects_unapproved_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            data = synthetic_export()
            data["approved_settings"]["learning_rate"] = 3e-5
            source = folder / "wrong.json"
            source.write_text(json.dumps(data), encoding="utf-8")
            manifest = folder / "manifest.csv"
            results = folder / "results.csv"
            workflow.make_manifest(workflow.HERE / "search_space.json",
                                   ROOT / "03 - MODEL DEVELOPMENT/input-preparation/preprocessing_config.json",
                                   manifest)
            with self.assertRaisesRegex(ValueError, "settings"):
                workflow.import_verified_export(source, manifest, results)
            self.assertFalse(results.exists())


if __name__ == "__main__":
    unittest.main()
