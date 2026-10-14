import importlib.util
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

SERVICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE))
import context_comparison_harness as harness


class ContextComparisonHarnessTests(unittest.TestCase):
    def test_pending_fidelity_is_provisional_only_and_never_freezable(self):
        config = {name: 1 for name in harness.REQUIRED_RUNTIME_SETTINGS}
        config.update({"context_approach": "accumulated"})
        health = {"model_kind": "interim", "model_version": "m1",
                  "configuration_id": "c1", "configuration": config}
        approval = {
            "approval_status": "owner_approved",
            "scope": "provisional_development_screening",
            "model_kind": "interim", "model_version": "m1", "configuration_id": "c1",
            "recording_fidelity_status": "pending_human_verification",
            "freeze_allowed": False,
            "combined_feasibility": {"approved": True, "approved_run_count": 36,
                                     "minimum_playback_minutes": 40.8425,
                                     "processing_and_setup_included": True},
            "runtime_settings": config,
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "approval.json"
            path.write_text(json.dumps(approval))
            self.assertEqual(harness.check_authorization(path, health), approval)
            approval["freeze_allowed"] = True
            path.write_text(json.dumps(approval))
            with self.assertRaisesRegex(harness.HarnessError, "blocks freeze"):
                harness.check_authorization(path, health)

    def test_interim_model_cannot_claim_official_scope(self):
        config = {name: 1 for name in harness.REQUIRED_RUNTIME_SETTINGS}
        health = {"model_kind": "interim", "model_version": "m1",
                  "configuration_id": "c1", "configuration": config}
        approval = {
            "approval_status": "owner_approved", "scope": "official_comparison",
            "model_kind": "interim", "model_version": "m1", "configuration_id": "c1",
            "recording_fidelity_status": "verified", "freeze_allowed": True,
            "combined_feasibility": {"approved": True, "approved_run_count": 36,
                                     "minimum_playback_minutes": 40.8425,
                                     "processing_and_setup_included": True},
            "runtime_settings": config,
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "approval.json"
            path.write_text(json.dumps(approval))
            with self.assertRaisesRegex(harness.HarnessError, "provisional development"):
                harness.check_authorization(path, health)

    def test_schedule_validation_uses_saved_assignment_order_and_hash(self):
        records = []
        for i in range(12):
            records.append({"partition": "development", "label": "Scam" if i < 6 else "Not Scam",
                            "group_id": f"g{i}", "recording_id": f"r{i}",
                            "sample_id": f"s{i}", "source_dataset": "primary",
                            "audio_sha256": f"a{i}", "script_sha256": f"t{i}",
                            "fidelity_status": "pending_human_verification", "duration_seconds": "10"})
        assignments = []
        from prepare_context_schedule import schedule
        assignments = schedule(records)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rec = root / "recordings"; rec.mkdir()
            manifest = rec / "audio_manifest.csv"
            with manifest.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=records[0].keys())
                writer.writeheader(); writer.writerows(records)
            schedule_path = root / "schedule.json"
            saved = {"manifest_sha256": harness.sha256_file(rec / "audio_manifest.csv"),
                     "assignments": assignments}
            schedule_path.write_text(json.dumps(saved))
            with patch.object(harness, "load_dependencies", return_value=(
                type("Schedule", (), {"schedule": staticmethod(schedule)}),
                type("Recordings", (), {"validate_provenance": staticmethod(lambda *_: None)}),
            )):
                loaded, info = harness.validate_schedule(rec, schedule_path)
            self.assertEqual(len(loaded), 36)
            self.assertEqual(info["fidelity_statuses"], ["pending_human_verification"])
            self.assertEqual(info["audio_playback_seconds"], 360)

    def test_android_click_uses_accessible_label_and_clickable_ancestor(self):
        root = ET.fromstring('<hierarchy><node clickable="true" bounds="[0,0][100,100]">'
                             '<node text="ตอบรับ" bounds="[10,10][90,90]"/></node></hierarchy>')
        ui = harness.AndroidUI("adb", "emu", Path("/tmp"))
        nodes = list(root.iter())
        with patch.object(ui, "nodes", return_value=(root, {nodes[2]: nodes[1], nodes[1]: root})), \
             patch.object(harness, "adb") as mock_adb:
            ui.tap(exact="ตอบรับ", timeout=0.1)
        self.assertEqual(mock_adb.call_args.args[2:], ("shell", "input", "tap", "50", "50"))

    def test_android_click_avoids_floating_call_button_overlapping_record_row(self):
        root = ET.fromstring(
            '<hierarchy>'
            '<node content-desc="development-09 · diagnostic / unverified" '
            'clickable="true" bounds="[53,2071][1028,2228]"/>'
            '<node content-desc="จำลองสายเข้า" clickable="true" '
            'bounds="[440,2075][640,2274]"/>'
            '</hierarchy>')
        ui = harness.AndroidUI("adb", "emu", Path("/tmp"))
        nodes = list(root.iter())
        with patch.object(ui, "nodes", return_value=(root, {nodes[1]: root, nodes[2]: root})), \
             patch.object(harness, "adb") as mock_adb:
            ui.tap(contains="development-09", timeout=0.1)
        self.assertEqual(mock_adb.call_args.args[2:],
                         ("shell", "input", "tap", "85", "2149"))

    def test_android_click_can_deliberately_activate_floating_call_control(self):
        root = ET.fromstring(
            '<hierarchy>'
            '<node content-desc="development-09 · diagnostic / unverified" '
            'clickable="true" bounds="[53,2071][1028,2228]"/>'
            '<node content-desc="จำลองสายเข้า" clickable="true" '
            'bounds="[440,2075][640,2274]"/>'
            '</hierarchy>')
        ui = harness.AndroidUI("adb", "emu", Path("/tmp"))
        nodes = list(root.iter())
        with patch.object(ui, "nodes", return_value=(root, {nodes[1]: root, nodes[2]: root})), \
             patch.object(harness, "adb") as mock_adb:
            ui.tap(exact=harness.START_LABEL, timeout=0.1)
        self.assertEqual(mock_adb.call_args.args[2:],
                         ("shell", "input", "tap", "540", "2174"))

    def test_android_click_does_not_clip_reset_button_to_sibling_scroll_view(self):
        root = ET.fromstring(
            '<hierarchy>'
            '<node class="android.widget.ScrollView" scrollable="true" bounds="[42,638][1038,2043]">'
            '<node text="list" bounds="[42,638][1038,2043]"/></node>'
            '<node content-desc="เริ่ม Session ใหม่" clickable="true" bounds="[446,2101][635,2290]"/>'
            '</hierarchy>')
        ui = harness.AndroidUI("adb", "emu", Path("/tmp"))
        nodes = list(root.iter())
        with patch.object(ui, "nodes", return_value=(root, {nodes[1]: root, nodes[2]: nodes[1], nodes[3]: root})), \
             patch.object(harness, "adb") as mock_adb:
            ui.tap(exact=harness.RESET_LABEL, timeout=0.1)
        self.assertEqual(mock_adb.call_args.args[2:],
                         ("shell", "input", "tap", "540", "2195"))

    def test_android_click_clips_row_to_its_scrollable_ancestor(self):
        root = ET.fromstring(
            '<hierarchy><node class="android.widget.ScrollView" scrollable="true" '
            'bounds="[0,100][400,900]">'
            '<node content-desc="development-11" clickable="true" bounds="[10,901][390,990]"/>'
            '</node></hierarchy>')
        nodes = list(root.iter())
        parents = {nodes[1]: root, nodes[2]: nodes[1]}
        self.assertIsNone(harness.AndroidUI.safe_tap_point(nodes[2], root, parents))

    def test_home_selection_gate_requires_correct_recording_and_call_control(self):
        root = ET.fromstring(
            '<hierarchy>'
            '<node text="Scam Call Alert"/>'
            '<node text="บทสนทนาที่บันทึกไว้" selected="true" clickable="true" bounds="[60,480][540,580]"/>'
            '<node text="ไมโครโฟนสด" clickable="true" bounds="[540,480][1020,580]"/>'
            '<node text="การตั้งค่า" clickable="true" bounds="[900,100][1040,280]"/>'
            '<node content-desc="development-09 · diagnostic / unverified" '
            'checked="true" clickable="true" bounds="[53,2071][1028,2228]"/>'
            '<node content-desc="จำลองสายเข้า" clickable="true" '
            'bounds="[440,2075][640,2274]"/>'
            '</hierarchy>')
        ui = harness.AndroidUI("adb", "emu", Path("/tmp"))
        nodes = list(root.iter())
        with patch.object(ui, "nodes", return_value=(root, {node: root for node in nodes[1:]})):
            ui.require_home_selection("development-09")
            with self.assertRaisesRegex(harness.HarnessError, "was not selected"):
                ui.require_home_selection("development-10")

    def test_home_selection_gate_accepts_scrolled_home_title_offscreen(self):
        root = ET.fromstring(
            '<hierarchy>'
            '<node text="การตั้งค่า" clickable="true" bounds="[900,120][1040,280]"/>'
            '<node content-desc="development-11 · diagnostic / unverified" checked="true" clickable="true" bounds="[53,1770][1028,1927]"/>'
            '<node content-desc="จำลองสายเข้า" clickable="true" bounds="[440,2075][640,2274]"/>'
            '</hierarchy>')
        ui = harness.AndroidUI("adb", "emu", Path("/tmp"))
        nodes = list(root.iter())
        with patch.object(ui, "nodes", return_value=(root, {node: root for node in nodes[1:]})):
            self.assertFalse(ui.text(exact="Scam Call Alert"))
            ui.require_home_selection("development-11")

    def test_home_selection_gate_rejects_incoming_call_controls(self):
        root = ET.fromstring(
            '<hierarchy><node text="Scam Call Alert"/>'
            '<node text="ตอบรับ" clickable="true" bounds="[10,10][100,100]"/>'
            '<node text="ปฏิเสธ" clickable="true" bounds="[10,120][100,210]"/></hierarchy>')
        ui = harness.AndroidUI("adb", "emu", Path("/tmp"))
        nodes = list(root.iter())
        with patch.object(ui, "nodes", return_value=(root, {node: root for node in nodes[1:]})):
            with self.assertRaisesRegex(harness.HarnessError, "left the home screen"):
                ui.require_home_selection("development-11")

    def test_continuation_accepts_only_reviewed_harness_change_and_unattempted_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evaluation = root / "evaluation"
            evaluation.mkdir()
            artifact = evaluation / "artifact_manifest.json"
            artifact.write_text("{}")
            ledger = evaluation / "attempt_events.jsonl"
            ledger.write_text(json.dumps({"event": "attempt_finished", "assigned_run_id": "run-a"}) + "\n")
            harness_key = "04 - APPLICATION DEVELOPMENT/prototype/service/context_comparison_harness.py"
            old_sources = {harness_key: "old", "App.tsx": "unchanged"}
            new_sources = {harness_key: "new", "App.tsx": "unchanged"}
            assignments = [{"assigned_run_id": "run-a"}, {"assigned_run_id": "run-b"}]
            previous = {"source_sha256": old_sources}
            current = {"source_sha256": new_sources, "model_version": "m1", "configuration_id": "c1",
                       "classifier_identity": {"id": "classifier"}, "apk_sha256": "apk",
                       "installed_apk_sha256": "apk"}
            continuation = {
                "schema_version": 1, "evaluation_dir": str(evaluation),
                "previous_artifact_manifest_sha256": harness.sha256_file(artifact),
                "previous_source_sha256": old_sources, "continuation_source_sha256": new_sources,
                "schedule": assignments, "model_version": "m1", "configuration_id": "c1",
                "classifier_identity": {"id": "classifier"}, "apk_sha256": "apk",
                "installed_apk_sha256": "apk", "failed_assignments_preserved": True,
                "no_failed_assignment_retries": True, "unattempted_assignments": ["run-b"],
                "review_status": "awaiting_root_review", "launch_authorized": False,
            }
            path = evaluation / "continuation_manifest.json"
            path.write_text(json.dumps(continuation))
            with self.assertRaisesRegex(harness.HarnessError, "requires root review"):
                harness.validate_continuation(path, evaluation, previous, current, assignments, ledger)
            continuation["review_status"] = "root_reviewed"
            continuation["launch_authorized"] = True
            path.write_text(json.dumps(continuation))
            self.assertEqual(harness.validate_continuation(
                path, evaluation, previous, current, assignments, ledger)["unattempted_assignments"], ["run-b"])

    def test_android_checked_reads_checked_state_from_accessible_parent(self):
        root = ET.fromstring('<hierarchy><node checked="true" text="Latest">'
                             '<node text="Latest"/></node></hierarchy>')
        ui = harness.AndroidUI("adb", "emu", Path("/tmp"))
        nodes = list(root.iter())
        with patch.object(ui, "nodes", return_value=(root, {nodes[1]: root})):
            self.assertTrue(ui.checked(exact="Latest"))

    def test_scroll_container_is_derived_from_visible_accessibility_bounds(self):
        root = ET.fromstring('<hierarchy><node scrollable="true" bounds="[8,100][400,900]"/>'
                             '<node scrollable="true" bounds="[0,0][10,10]"/></hierarchy>')
        self.assertEqual(harness.AndroidUI.scroll_rect(root), (8, 100, 400, 900))

    def test_scroll_to_top_swipes_down_within_observed_scroll_bounds(self):
        root = ET.fromstring('<hierarchy><node scrollable="true" bounds="[0,0][1080,2400]"/></hierarchy>')
        ui = harness.AndroidUI("adb", "emu", Path("/tmp"))
        with patch.object(ui, "nodes", return_value=(root, {})), \
             patch.object(harness, "adb") as mock_adb, \
             patch.object(harness.time, "sleep"):
            ui.scroll_to_top()
        self.assertEqual(mock_adb.call_count, 4)
        self.assertEqual(mock_adb.call_args.args[2:],
                         ("shell", "input", "swipe", "540", "600", "540", "1800", "350"))

    def test_tap_scrolls_past_clipped_rows_instead_of_tapping_the_screen_edge(self):
        root = ET.fromstring('<hierarchy><node scrollable="true" bounds="[0,100][400,900]">'
                             '<node clickable="true" bounds="[10,890][390,900]">'
                             '<node content-desc="development-11"/></node></node></hierarchy>')
        ui = harness.AndroidUI("adb", "emu", Path("/tmp"))
        nodes = list(root.iter())
        with patch.object(ui, "nodes", return_value=(root, {nodes[2]: nodes[1], nodes[1]: root})), \
             patch.object(harness, "adb") as mock_adb, \
             self.assertRaisesRegex(harness.HarnessError, "not found/clickable"):
            ui.tap(contains="development-11", timeout=0.01)
        self.assertEqual(mock_adb.call_args.args[2:6], ("shell", "input", "swipe", "200"))

    def test_snapshot_lookup_reads_only_saved_run_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = Path(tmp)
            directory = storage / "runs" / "session"
            directory.mkdir(parents=True)
            (directory / "snapshot.json").write_text(json.dumps({"session_id": "session", "state": "complete"}))
            self.assertEqual(harness.snapshot_for(storage, "session")["state"], "complete")
            self.assertEqual(harness.run_directories(storage), {"session"})


if __name__ == "__main__":
    unittest.main()
