"""Verify frozen Stage 01 assignments, boundaries, and rebuild."""
from copy import deepcopy
from pathlib import Path
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parent
DATA = SCRIPTS.parent
spec = importlib.util.spec_from_file_location("split", SCRIPTS / "4.split.py")
split = importlib.util.module_from_spec(spec)
spec.loader.exec_module(split)
ARTIFACTS = ("0 - train/dataset.csv", "1 - test/dataset.csv", "split_assignments.csv", "split_report.md")


class SplitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prepared = DATA / "prepared"
        cls.records = split.read_csv(prepared / "prepared.csv", split.RECORD_COLUMNS)
        cls.audit = split.read_csv(prepared / "record_audit.csv")
        cls.groups = split.group_ids(cls.records, cls.audit)
        folder = prepared / "splits"
        cls.assignments = split.read_csv(folder / "split_assignments.csv", split.ASSIGNMENT_COLUMNS)
        cls.train = split.read_csv(folder / "0 - train/dataset.csv", split.RECORD_COLUMNS)
        cls.test = split.read_csv(folder / "1 - test/dataset.csv", split.RECORD_COLUMNS)
        cls.config = json.loads((DATA / "split_config.json").read_text())

    def test_frozen_integrity_and_allocation(self):
        split.verify(self.records, self.assignments, self.groups, self.train, self.test)
        self.assertEqual((len(self.train), len(self.test)), (1164, 291))
        self.assertEqual({"train": split.counts(self.train), "test": split.counts(self.test)},
                         self.config["approved_allocation"])
        self.assertEqual(split.assign(self.records, self.groups, self.config), self.assignments)
        report = (DATA / "prepared/splits/split_report.md").read_text()
        self.assertEqual(report, split.report(self.records, self.audit, self.groups,
                                              self.assignments, self.config))
        rows = [line for line in report.splitlines() if line.startswith("| train |")
                or line.startswith("| test |") or line.startswith("| fold ")]
        self.assertEqual(len(rows), 24)
        for line in rows:
            fields = [field.strip() for field in line.strip("|").split("|")]
            scam, not_scam, total = map(int, fields[2:5])
            self.assertEqual(scam + not_scam, total)
            self.assertEqual(fields[5], f"{100 * scam / total if total else 0:.2f}%")
            self.assertEqual(fields[6], f"{100 * not_scam / total if total else 0:.2f}%")

    def test_graph_transitivity_via_removed_copy_and_cross_source(self):
        records = [{"sample_id": "a"}, {"sample_id": "b"}, {"sample_id": "c"}]
        events = [
            {"sample_id": cid, "action": "retain", "review_status": "resolved", "related_sample_id": "", "final_decision": "retain"}
            for cid in ("a", "b", "c")]
        events += [
            {"sample_id": "removed", "action": "remove_duplicate", "review_status": "resolved", "related_sample_id": "a", "final_decision": "remove_duplicate"},
            {"sample_id": "removed", "action": "relationship", "review_status": "resolved", "related_sample_id": "b", "final_decision": "confirmed_related"}]
        # This construction makes no source restriction and can connect across sources.
        groups = split.group_ids(records, events)
        self.assertEqual(groups, {"a": "group_a", "b": "group_a", "c": "group_c"})
        events[-1]["related_sample_id"] = "absent"
        with self.assertRaisesRegex(ValueError, "unknown ID"):
            split.group_ids(records, events)

    def test_unresolved_audit_and_duplicate_ids(self):
        audit = deepcopy(self.audit)
        audit[0]["review_status"] = "pending"
        with self.assertRaisesRegex(ValueError, "unresolved"):
            split.group_ids(self.records, audit)
        with self.assertRaisesRegex(ValueError, "unique"):
            split.group_ids(self.records + self.records[:1], self.audit)

    def test_corrupted_assignments(self):
        cases = ("source", "test_fold", "group", "missing", "duplicate")
        for case in cases:
            with self.subTest(case=case):
                assignments = deepcopy(self.assignments)
                if case == "source":
                    assignments[0]["source_dataset"] = "wrong"
                elif case == "test_fold":
                    next(row for row in assignments if row["split"] == "test")["cv_fold"] = "0"
                elif case == "group":
                    assignments[0]["group_id"] = "wrong"
                elif case == "missing":
                    assignments.pop()
                else:
                    assignments.append(assignments[0])
                with self.assertRaises(ValueError):
                    split.verify(self.records, assignments, self.groups, self.train, self.test)

    def test_group_boundary_and_derived_text(self):
        assignments = deepcopy(self.assignments)
        family = next(group for group in self.groups.values() if list(self.groups.values()).count(group) > 1)
        members = [row for row in assignments if row["group_id"] == family]
        if members[0]["split"] == "train":
            members[0]["cv_fold"] = str((int(members[0]["cv_fold"]) + 1) % 5)
        else:
            members[0].update(split="train", cv_fold="0")
        with self.assertRaisesRegex(ValueError, "crosses"):
            split.verify(self.records, assignments, self.groups, self.train, self.test)
        train = deepcopy(self.train)
        train[0]["transcript"] += " changed"
        with self.assertRaisesRegex(ValueError, "differs from canonical"):
            split.verify(self.records, self.assignments, self.groups, train, self.test)

    def test_rebuild_overwrite_and_input_change(self):
        expected = {name: split.checksum(DATA / "prepared/splits" / name) for name in ARTIFACTS}
        with tempfile.TemporaryDirectory(prefix="scam-split-test-") as temporary:
            root = Path(temporary)
            scripts = root / "scripts"
            scripts.mkdir()
            shutil.copy(SCRIPTS / "4.split.py", scripts / "4.split.py")
            shutil.copy(DATA / "split_config.json", root / "split_config.json")
            prepared = root / "prepared"
            prepared.mkdir()
            for name in (*self.config["input_checksums"], "README.md"):
                shutil.copy(DATA / "prepared" / name, prepared / name)
            # Rebuild starts from the preparation README, not its mutable split section.
            text = (prepared / "README.md").read_text().split("\n## Frozen splits", 1)[0]
            (prepared / "README.md").write_text(text)
            command = [sys.executable, str(scripts / "4.split.py")]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual({name: split.checksum(prepared / "splits" / name) for name in ARTIFACTS}, expected)
            for name, expected_hash in self.config["input_checksums"].items():
                self.assertEqual(split.checksum(prepared / name), expected_hash)
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("do not overwrite", result.stderr)
            raw = prepared / "prepared.csv"
            raw.write_bytes(raw.read_bytes() + b"\n")
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Preparation changed", result.stderr)

    def test_unapproved_build_writes_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scripts = root / "scripts"
            scripts.mkdir()
            shutil.copy(SCRIPTS / "4.split.py", scripts / "4.split.py")
            config = deepcopy(self.config)
            config["approval"]["status"] = "pending"
            (root / "split_config.json").write_text(json.dumps(config))
            result = subprocess.run([sys.executable, str(scripts / "4.split.py")], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Owner holdout approval", result.stderr)
            self.assertFalse((root / "prepared").exists())


if __name__ == "__main__":
    unittest.main()
