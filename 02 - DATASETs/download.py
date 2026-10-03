"""Download and verify raw datasets for Scam Call Alert.

Uses public endpoints pinned in sources.json.
Run from repository root or 02 - DATASETs/:
    python '02 - DATASETs/download.py'
"""
from pathlib import Path
from urllib.request import urlopen, Request
from zipfile import ZipFile
import hashlib
import json

DATA = Path(__file__).resolve().parent


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def fetch_file(url, target_path):
    target_path.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "scam-call-alert/1.0"})
    with urlopen(req) as resp, open(target_path, "wb") as out:
        while chunk := resp.read(65536):
            out.write(chunk)


def main():
    manifest = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    print("Checking / downloading raw datasets...")

    for dataset in manifest["datasets"]:
        print(f"\nDataset: {dataset['id']} ({dataset['platform']})")
        for item in dataset["files"]:
            target = DATA / item["path"]
            expected_hash = item["sha256"]

            if target.is_file() and sha256(target) == expected_hash:
                print(f"  [OK] {item['path']} (already verified)")
                continue

            print(f"  Downloading {item['path']}...")
            fetch_file(item["url"], target)

            actual_hash = sha256(target)
            if actual_hash != expected_hash:
                raise ValueError(f"Checksum mismatch for {target}: expected {expected_hash}, got {actual_hash}")
            print(f"  [Verified] {item['path']}")

    # Extract Kaggle CSV if needed
    kaggle_dir = DATA / "raw/thai-call-center-call-log"
    zip_path = kaggle_dir / "thai-call-center-call-log-dataset.zip"
    csv_path = kaggle_dir / "Dataset.csv"
    if not csv_path.is_file() or sha256(csv_path) != "615fde01d5704da4ff2c5d5f39d1729e108cac40598d518b487480337cbca992":
        print("  Extracting Dataset.csv from zip...")
        with ZipFile(zip_path) as z:
            csv_path.write_bytes(z.read("Dataset.csv"))
        print("  [Verified] Dataset.csv extracted")

    print("\nAll raw datasets are downloaded and verified against sources.json.")


if __name__ == "__main__":
    main()
