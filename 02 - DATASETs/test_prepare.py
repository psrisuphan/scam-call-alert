"""Verify the Plan 00 CSV handoff and deterministic rebuild."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import csv
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest

import download
import prepare

DATA = Path(__file__).resolve().parent
# Plan 01 updates README.md; canonical data, audit, manifest, and report stay immutable.
OUTPUT_FILES = ["prepared.csv", "record_audit.csv", "source_manifest.csv", "preparation_report.md"]


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def hashes(folder):
    return {name: hashlib.sha256((folder / name).read_bytes()).hexdigest() for name in OUTPUT_FILES}


class PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest, cls.raw = prepare.load_sources()
        cls.approvals = prepare.review_inputs(cls.manifest, cls.raw)
        cls.pairs = prepare.candidates(cls.raw)
        cls.kept = read_csv(DATA / "prepared/prepared.csv")
        cls.audit = read_csv(DATA / "prepared/record_audit.csv")

    def test_schema_provenance_and_preserved_content(self):
        self.assertEqual(list(self.kept[0]), prepare.COLUMNS)
        self.assertEqual(len(self.kept), 1455)
        self.assertEqual(len({row["sample_id"] for row in self.kept}), 1455)
        raw = {row["sample_id"]: row for row in self.raw}
        for row in self.kept:
            self.assertEqual(row, {key: str(raw[row["sample_id"]][key]) for key in prepare.COLUMNS})
        self.assertEqual(Counter(row["label"] for row in self.kept), {"Scam": 692, "Not Scam": 763})
        self.assertEqual(Counter(row["source_dataset"] for row in self.kept), {"primary": 1276, "supplemental": 179})

    def test_disposition_and_audit_accounting(self):
        finals = [row for row in self.audit if row["action"] in ("retain", "exclude", "remove_duplicate")]
        self.assertEqual(len(finals), 1478)
        self.assertEqual(len({row["sample_id"] for row in finals}), 1478)
        self.assertEqual(Counter(row["action"] for row in finals),
                         {"retain": 1455, "exclude": 3, "remove_duplicate": 20})
        raw = {row["sample_id"]: row for row in self.raw}
        kept = {row["sample_id"]: row for row in self.kept}
        for row in self.audit:
            original = raw[row["sample_id"]]
            self.assertEqual(row["source_file"], original["source_file"])
            self.assertEqual(int(row["source_row_index"]), original["source_row_index"])
            self.assertEqual(row["source_record_id"], original["source_record_id"])
            self.assertTrue(all(row[key] for key in ("reason", "evidence", "review_status", "reviewer", "final_decision")))
            self.assertEqual(row["review_status"], "resolved")
            if row["action"] == "exclude":
                self.assertTrue(row["recovery_attempt"])
            if row["action"] == "remove_duplicate":
                representative = kept[row["related_sample_id"]]
                self.assertEqual(prepare.comparison_copy(original["transcript"]),
                                 prepare.comparison_copy(representative["transcript"]))
                self.assertEqual(original["label"], representative["label"])

    def test_unknown_and_integrity_decisions(self):
        retained = {row["sample_id"]: row for row in self.kept}
        unknown = [row for row in self.kept if row["original_label"] == "Unknow"]
        self.assertEqual(len(unknown), 12)  # 13 raw rows minus one exact copy.
        self.assertTrue(all(row["label"] == "Not Scam" for row in unknown))
        for index in (83, 191, 567):
            self.assertIn("\ufffd", retained[f"hf_{index:06d}"]["transcript"])
        for index in (286, 308, 439):
            self.assertNotIn(f"hf_{index:06d}", retained)

    def test_relationship_reviews(self):
        self.assertEqual(len(self.pairs), 46)
        relations = [row for row in self.audit if row["action"] == "relationship"]
        self.assertEqual(len(relations), 92)
        actual = {(row["sample_id"], row["related_sample_id"]) for row in relations}
        for pair in self.pairs:
            self.assertIn((pair["left"], pair["right"]), actual)
            self.assertIn((pair["right"], pair["left"]), actual)
        self.assertTrue(all(row["final_decision"] == "confirmed_related" for row in relations))

    def test_manifest_and_conservative_comparison(self):
        manifest = read_csv(DATA / "prepared/source_manifest.csv")
        self.assertEqual(len(manifest), 3)
        for row in manifest:
            self.assertEqual(row["checksum_algorithm"], "SHA-256")
            self.assertEqual(row["checksum"], prepare.digest((DATA / row["source_file"]).read_bytes()))
            self.assertTrue(all(row[key] for key in ("license", "download_date", "version", "source_url")))
        keys = [prepare.comparison_copy(row["transcript"]) for row in self.kept]
        self.assertEqual(len(set(keys)), len(keys))
        self.assertEqual(prepare.comparison_copy(" \r\nA  B\rC \n"), "A  B\nC")
        self.assertNotEqual(prepare.comparison_copy("A  B"), prepare.comparison_copy("A B"))

    def test_csv_multiline_roundtrip(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "roundtrip.csv"
            row = dict(zip(prepare.COLUMNS, ["x", "source", "1", "Scam", "Scam",
                           'ผู้โทร: "OTP, 123"\r\nผู้รับ: ขอบคุณ\nURL: https://example.com']))
            prepare.write_csv(path, prepare.COLUMNS, [row])
            self.assertEqual(read_csv(path), [row])

    def test_unresolved_or_stale_review_fails(self):
        for change, pattern in (("missing", "coverage"), ("pending", "Unresolved"), ("stale", "match")):
            with self.subTest(change=change):
                approvals = deepcopy(self.approvals)
                if change == "missing":
                    approvals["relationships"].pop()
                elif change == "pending":
                    approvals["relationships"][0]["decision"] = "pending"
                else:
                    approvals["relationships"][0]["left_sha256"] = "wrong"
                with self.assertRaisesRegex(ValueError, pattern):
                    prepare.prepare_records(self.raw, approvals, self.pairs)

    def test_duplicate_preference_and_conflicts(self):
        rows = [dict(row) for row in self.raw[:3]]
        for i, row in enumerate(rows):
            row.update(sample_id=f"test_{i}", source_dataset="primary" if i else "supplemental",
                       source_row_index=2-i, transcript="Same\r\ntext", label="Scam")
        kept, audit = prepare.prepare_records(rows, {"relationships": [], "integrity": {}}, [])
        self.assertEqual([row["sample_id"] for row in kept], ["test_2"])
        self.assertEqual({row["related_sample_id"] for row in audit if row["action"] == "remove_duplicate"}, {"test_2"})
        rows[0]["label"] = "Not Scam"
        with self.assertRaisesRegex(ValueError, "label conflict"):
            prepare.prepare_records(rows, {"relationships": [], "integrity": {}}, [])

    def test_reproduction_and_boundary_failures(self):
        with tempfile.TemporaryDirectory(prefix="scam-csv-test-") as temporary:
            root = Path(temporary)
            for name in ("prepare.py", "sources.json", "preparation_decisions.json"):
                shutil.copy(DATA / name, root / name)
            shutil.copytree(DATA / "raw", root / "raw")
            command = [sys.executable, str(root / "prepare.py")]
            # Pending approval must not create the canonical output.
            decisions = json.loads((root / "preparation_decisions.json").read_text())
            decisions["source_mapping_review"]["status"] = "pending"
            (root / "preparation_decisions.json").write_text(json.dumps(decisions))
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Source mapping is not approved", result.stderr)
            self.assertFalse((root / "prepared").exists())
            shutil.copy(DATA / "preparation_decisions.json", root / "preparation_decisions.json")
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(hashes(root / "prepared"), hashes(DATA / "prepared"))
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("do not overwrite", result.stderr)
            raw = root / "raw/thai-call-center-call-log/Dataset.csv"
            raw.write_bytes(raw.read_bytes() + b"\n")
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Source checksum mismatch", result.stderr)

    def test_download_clean_checkout_and_tamper(self):
        # Mock only transport; exercise actual archive extraction and hash verification.
        source_bytes = {item["path"]: (DATA / item["path"]).read_bytes()
                        for source in self.manifest["datasets"] for item in source["files"]}
        urls = {}
        for source in self.manifest["datasets"]:
            for item in source["files"]:
                if "url" in item or item["path"].endswith(".zip"):
                    urls[item.get("url") or source["download_url"]] = source_bytes[item["path"]]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copy(DATA / "sources.json", root / "sources.json")
            def response(request, timeout):
                return io.BytesIO(urls[request.full_url])
            with patch.object(download, "DATA", root), patch.object(download, "urlopen", side_effect=response) as fetch:
                download.main()
                self.assertEqual(fetch.call_count, 2)
                download.main()
                self.assertEqual(fetch.call_count, 2)
                raw = root / "raw/thai-call-center-call-log/Dataset.csv"
                raw.write_bytes(b"altered")
                with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                    download.main()
                self.assertEqual(raw.read_bytes(), b"altered")


if __name__ == "__main__":
    unittest.main()
