"""Verify local v1 and reproduce it without modifying repository data.

Run: uv run --no-project --with pyarrow==25.0.1 --with scikit-learn==1.9.1 python '02 - DATASETs/test_prepare.py'
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

DATA = Path(__file__).resolve().parent


def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def hashes(folder):
    return {file.name: hashlib.sha256(file.read_bytes()).hexdigest() for file in folder.iterdir() if file.is_file()}


class PreparationTests(unittest.TestCase):
    def test_record_integrity(self):
        folder = DATA / "processed/v1"
        kept = jsonl(folder / "primary.jsonl") + jsonl(folder / "supplemental.jsonl")
        logs = jsonl(folder / "decisions.jsonl")
        excluded = jsonl(folder / "exclusions.jsonl")
        groups = jsonl(folder / "groups.jsonl")

        self.assertEqual((len(kept), len(excluded), len(logs)), (1440, 38, 1478))
        self.assertEqual(len({r["conversation_id"] for r in logs}), 1478)
        self.assertEqual(len({r["text"] for r in kept}), 1440)
        self.assertTrue(all(type(r["label"]) is int and r["label"] in (0, 1) for r in kept))
        self.assertTrue(all(r["human_verified"] is False for r in kept))
        self.assertTrue({r["conversation_id"] for r in kept}.isdisjoint(r["conversation_id"] for r in excluded))
        self.assertEqual(sorted(m for g in groups for m in g["members"]), sorted(r["conversation_id"] for r in kept))

        # Check category mappings per proposal
        by_id = {r["conversation_id"]: r for r in kept}
        self.assertEqual(by_id["kaggle_000001"]["label"], 0)  # General -> Not Scam
        self.assertEqual(by_id["kaggle_000002"]["label"], 0)  # Verification-call -> Not Scam
        self.assertEqual(by_id["kaggle_000004"]["label"], 0)  # Official -> Not Scam
        self.assertEqual(by_id["kaggle_000000"]["label"], 1)  # Scam -> Scam

    def test_reproduction_and_boundary_failures(self):
        expected = hashes(DATA / "processed/v1")
        with tempfile.TemporaryDirectory(prefix="scam-prep-test-") as temporary:
            root = Path(temporary)
            for name in ["prepare.py", "sources.json"]:
                shutil.copy(DATA / name, root / name)
            shutil.copytree(DATA / "raw", root / "raw")
            (root / "reports").mkdir()

            command = [sys.executable, str(root / "prepare.py")]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(hashes(root / "processed/v1"), expected)

            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("do not overwrite", result.stderr)

            raw = root / "raw/thai-call-center-call-log/Dataset.csv"
            raw.write_bytes(raw.read_bytes() + b"\n")
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Source checksum mismatch", result.stderr)


if __name__ == "__main__":
    unittest.main()
