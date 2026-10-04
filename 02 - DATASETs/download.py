"""Download pinned sources without overwriting existing raw files."""
from pathlib import Path
from urllib.request import Request, urlopen
from zipfile import ZipFile
import hashlib
import json
import tempfile

DATA = Path(__file__).resolve().parent


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    for source in manifest["datasets"]:
        for item in source["files"]:
            target = DATA / item["path"]
            if target.exists():
                if sha256(target) != item["sha256"]:
                    raise ValueError(f"Source checksum mismatch: {target}; preserve and investigate the existing file")
                print(f"Verified {item['path']}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            # Verify a temporary file before publishing it into the raw directory.
            with tempfile.TemporaryDirectory(dir=target.parent, prefix=".download-") as temporary:
                staged = Path(temporary) / target.name
                if target.suffix == ".csv" and "url" not in item:
                    archive = target.parent / "thai-call-center-call-log-dataset.zip"
                    with ZipFile(archive) as file:
                        staged.write_bytes(file.read("Dataset.csv"))
                else:
                    url = item.get("url") or source["download_url"]
                    request = Request(url, headers={"User-Agent": "scam-call-alert/1.0"})
                    with urlopen(request, timeout=120) as response, staged.open("wb") as file:
                        while chunk := response.read(65536):
                            file.write(chunk)
                if sha256(staged) != item["sha256"]:
                    raise ValueError(f"Downloaded checksum mismatch: {item['path']}")
                # Hard-link creation fails if a concurrent download created the target.
                target.hardlink_to(staged)
            print(f"Downloaded and verified {item['path']}")


if __name__ == "__main__":
    main()
