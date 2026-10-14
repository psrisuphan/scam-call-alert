import importlib.util
import csv
import json
from pathlib import Path
import tempfile
import unittest
import wave


MODULE_PATH = Path(__file__).resolve().parents[1] / "summarize_context_comparison.py"
SPEC = importlib.util.spec_from_file_location("summarize_context_comparison", MODULE_PATH)
SUMMARY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUMMARY)


class ContextSummaryTests(unittest.TestCase):
    def test_approved_demo_choice_is_hashed_and_bound_to_manifest_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_hash = "a" * 64
            selection = {
                "selected_approach": "accumulated", "scope": "provisional_demo",
                "owner_approved": True, "approval_date": "2026-10-14",
                "approval_evidence": "Owner approved accumulated context for the demo",
                "token_budget": 510, "retain": "newest eligible source text",
                "formal_release_approved": False, "final_test_access_authorized": False,
                "recording_fidelity": "unverified_owner_declined_review",
                "basis": "matched screen", "plan_reference": "Plan 04/01 section 11",
            }
            path = root / "demo_selection.json"
            path.write_text(json.dumps(selection), encoding="utf-8")
            result = SUMMARY.load_demo_selection(root, {
                "model_kind": "interim", "model_version": model_hash,
                "configuration_id": "config-id", "apk_sha256": "apk-hash",
                "classifier_identity": {"artifact_manifest_sha256": "artifact-hash",
                    "model_bundle_run_id": "bundle-run",
                    "bundle_files_sha256": {"model.safetensors": model_hash}},
            })
            self.assertEqual(result["selected_approach"], "accumulated")
            self.assertFalse(result["formal_release_approved"])
            self.assertEqual(result["model_provenance"]["model_version"], model_hash)
            self.assertEqual(result["selection_sidecar_sha256"], SUMMARY.sha256_file(path))

    def test_demo_choice_rejects_provenance_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "demo_selection.json"
            selection = {"selected_approach": "accumulated", "scope": "provisional_demo",
                "owner_approved": True, "approval_date": "2026-10-14", "token_budget": 510,
                "formal_release_approved": True, "final_test_access_authorized": False,
                "plan_reference": "Plan 04/01 section 11"}
            path.write_text(json.dumps(selection), encoding="utf-8")
            with self.assertRaises(ValueError):
                SUMMARY.load_demo_selection(root, {"model_kind": "interim"})

    def test_metrics_exclude_incomplete_predictions_but_keep_assigned_denominator(self):
        cases = [
            {"actual": "Scam", "outcome": "Scam", "usable_completed_run": True},
            {"actual": "Not Scam", "outcome": "Scam", "usable_completed_run": True},
            {"actual": "Scam", "outcome": "Scam", "usable_completed_run": False},
            {"actual": "Not Scam", "outcome": None, "usable_completed_run": False},
        ]
        result = SUMMARY.metric_summary(cases)
        self.assertEqual(result["assigned_n"], 4)
        self.assertEqual(result["completed_n"], 2)
        self.assertEqual(result["eligible_n"], 2)
        self.assertEqual(result["coverage"], 0.5)
        self.assertEqual(result["confusion_matrix_actual_rows_predicted_columns"]["Scam"]["Scam"], 1)
        self.assertEqual(result["confusion_matrix_actual_rows_predicted_columns"]["Not Scam"]["Scam"], 1)

    def test_undefined_metrics_are_numeric_zero_with_reason_flags(self):
        result = SUMMARY.metric_summary([
            {"actual": "Not Scam", "outcome": "Not Scam", "usable_completed_run": True},
        ])
        self.assertEqual(result["scam_precision"], 0.0)
        self.assertEqual(result["scam_recall"], 0.0)
        self.assertEqual(result["scam_f1"], 0.0)
        self.assertFalse(result["metric_defined"]["scam_precision"])
        self.assertFalse(result["metric_defined"]["scam_recall"])
        self.assertEqual(result["undefined_metric_reasons"]["scam_precision"], "no_predicted_scam_cases")
        self.assertEqual(result["undefined_metric_reasons"]["scam_recall"], "no_actual_scam_cases")
        self.assertTrue(result["metric_defined"]["not_scam_f1"])
        empty = SUMMARY.metric_summary([])
        self.assertEqual(empty["accuracy"], 0.0)
        self.assertEqual(empty["undefined_metric_reasons"]["accuracy"], "no_eligible_completed_cases")

    def test_diagnostics_use_native_clocks_and_actual_resource_fields(self):
        events = [
            {"event_id": 0, "kind": "audio_accepted", "start_sample": 0, "end_sample": 16000},
            {"event_id": 1, "kind": "classification_started", "request_id": "r1", "host_elapsed_s": 1.0},
            {"event_id": 2, "kind": "stt_completed", "start_sample": 0, "end_sample": 8000,
             "resources": {"processing_seconds": 0.25}},
            {"event_id": 3, "kind": "audio_accepted", "start_sample": 16000, "end_sample": 24000},
            {"event_id": 4, "kind": "classification_completed", "host_elapsed_s": 1.4,
             "response": {"request_id": "r1", "status": "success"}},
            {"event_id": 5, "kind": "client_observation", "client_kind": "notification_posted",
             "client_elapsed_ms": 12000, "audio_position_ms": 9000},
            {"event_id": 6, "kind": "client_observation", "client_kind": "native_resource_sample",
             "process_pss_bytes": 100, "process_cpu_time_ms": 10},
            {"event_id": 7, "kind": "client_observation", "client_kind": "native_resource_sample",
             "process_pss_bytes": 130, "process_cpu_time_ms": 14},
            {"event_id": 8, "kind": "stt_completed", "start_sample": 4000, "end_sample": 24000,
             "resources": {"processing_seconds": 0.5}},
        ]
        result = SUMMARY.session_diagnostics(events)
        self.assertEqual(result["stt_processing_seconds"]["n"], 2)
        self.assertEqual(result["stt_processing_seconds"]["mean"], 0.375)
        self.assertAlmostEqual(result["classifier_host_duration_seconds"]["mean"], 0.4)
        self.assertEqual(result["first_notification_posted_client_elapsed_ms"], 12000)
        self.assertEqual(result["first_notification_posted_audio_position_ms"], 9000)
        self.assertEqual(result["android_process_pss_bytes_max"], 130)
        self.assertEqual(result["android_process_cpu_time_ms_max"], 14)
        self.assertEqual(result["max_queued_seconds_derived"], 1.0)
        self.assertIn("accepted_end_minus_latest_stt_completed_end_sample", result["max_queued_seconds_source"])

    def test_noncontiguous_queue_ranges_remain_unavailable(self):
        result = SUMMARY.session_diagnostics([
            {"event_id": 0, "kind": "audio_accepted", "start_sample": 0, "end_sample": 100},
            {"event_id": 1, "kind": "audio_accepted", "start_sample": 120, "end_sample": 200},
        ])
        self.assertIsNone(result["max_queued_seconds_derived"])
        self.assertEqual(result["max_queued_seconds_derived_reason"],
                         "noncontiguous_or_invalid_audio_acceptance_ranges")

    def test_incomplete_run_keeps_early_scam_event_out_of_completed_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evaluation = root / "evaluation"
            storage = root / "storage"
            recordings = root / "recordings"
            run = storage / "runs" / "session-1"
            for folder in (evaluation, storage, recordings, run, recordings / "audio"):
                folder.mkdir(parents=True, exist_ok=True)
            audio_path = recordings / "audio" / "r.wav"
            with wave.open(str(audio_path), "wb") as audio:
                audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000)
                audio.writeframes(b"\0\0" * 100)
            with (recordings / "audio_manifest.csv").open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=["recording_id", "audio_file"])
                writer.writeheader(); writer.writerow({"recording_id": "development-00", "audio_file": "audio/r.wav"})
            schedule_path = evaluation / "schedule.json"
            schedule_path.write_text("[]", encoding="utf-8")
            assignment = {"assigned_run_id": "assigned-1", "recording_id": "development-00",
                          "label": "Scam", "approach": "latest"}
            manifest = {"schedule": [assignment], "schedule_path": str(schedule_path),
                        "recordings_path": str(recordings), "model_kind": "interim"}
            (evaluation / "artifact_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (evaluation / "attempt_events.jsonl").write_text(json.dumps({
                "event": "attempt_finished", "assigned_run_id": "assigned-1",
                "state": "failed", "harness_timeout": False, "error": "interrupted"}) + "\n", encoding="utf-8")
            (run / "snapshot.json").write_text(json.dumps({"state": "failed", "error": "interrupted",
                "audio_samples": 80, "processed_samples": 80}), encoding="utf-8")
            (run / "events.jsonl").write_text(json.dumps({"event_id": 0, "kind": "classification_completed",
                "host_elapsed_s": 1.2, "response": {"request_id": "r", "status": "success", "label": "Scam"}}) + "\n", encoding="utf-8")
            (evaluation / "failure_session_attributions.json").write_text(json.dumps({"attributions": [{
                "assigned_run_id": "assigned-1", "session_id": "session-1", "basis": "unique failed session",
                "snapshot_sha256": SUMMARY.sha256_file(run / "snapshot.json"),
                "events_sha256": SUMMARY.sha256_file(run / "events.jsonl"),
            }]}), encoding="utf-8")
            result = SUMMARY.aggregate(evaluation, storage)
            case = result["cases"][0]
            self.assertEqual(case["prediction_labels"], ["Scam"])
            self.assertTrue(case["scam_event_any_state"])
            self.assertTrue(case["scam_event_on_incomplete_run"])
            self.assertTrue(case["retrospective_session_attribution"]["verified_by_snapshot_and_event_sha256"])
            self.assertIsNone(case["outcome"])
            self.assertFalse(case["usable_completed_run"])
            self.assertEqual(result["metrics"]["eligible_n"], 0)

    def test_timing_summary_reports_sample_sd_and_empty_denominators(self):
        self.assertEqual(SUMMARY.sample_summary([2.0, 4.0]),
                         {"n": 2, "mean": 3.0, "sample_sd": 2 ** 0.5})
        self.assertEqual(SUMMARY.sample_summary([]), {"n": 0, "mean": None, "sample_sd": None})


if __name__ == "__main__":
    unittest.main()
