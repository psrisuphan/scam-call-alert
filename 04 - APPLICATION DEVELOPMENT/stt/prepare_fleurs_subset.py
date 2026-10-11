#!/usr/bin/env python3
"""Prepare the approved deterministic FLEURS Thai development subset."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import shutil
import sys
import struct
import tarfile
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


DATASET_REVISION = "70bb2e84b976b7e960aa89f1c648e09c59f894dd"
DATASET_CONFIG = "th_th"
DATASET_SOURCE_SPLIT = "dev"
SEED = 67
TARGET_SECONDS = 450
SAMPLE_RATE = 16_000
EXPECTED_TSV_SHA256 = "214f74aa346dd643390e1a629e647d662697c542bff1a318c78d3274e2662be2"
EXPECTED_ARCHIVE_SHA256 = "505c9e40878df8690a4b20ecb8cd630aec7951259c51c007ac8df2fe78377685"
DATASET_URL = (
    "https://huggingface.co/datasets/google/fleurs/tree/"
    f"{DATASET_REVISION}/data/{DATASET_CONFIG}"
)
ATTRIBUTION = (
    "Conneau et al., FLEURS: Few-shot Learning Evaluation of Universal "
    "Representations of Speech (2022), https://arxiv.org/abs/2205.12446"
)


@dataclass(frozen=True)
class FleursRecord:
    sentence_id: str
    audio_filename: str
    raw_transcription: str
    transcription: str
    phonemized_transcription: str
    num_samples: int
    gender: str

    @property
    def duration_seconds(self) -> float:
        return self.num_samples / SAMPLE_RATE


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_wav(path: Path) -> tuple[int, int, int, int]:
    """Return channels, sample rate, sample width, and frames for a RIFF/WAVE file."""
    with path.open("rb") as stream:
        header = stream.read(12)
        if len(header) != 12 or header[:4] != b"RIFF" or header[8:] != b"WAVE":
            raise ValueError(f"Not a little-endian RIFF/WAVE file: {path.name}")
        fmt: tuple[int, int, int, int, int] | None = None
        data_size: int | None = None
        while chunk_header := stream.read(8):
            if len(chunk_header) != 8:
                raise ValueError(f"Truncated WAV chunk header: {path.name}")
            chunk_id, chunk_size = struct.unpack("<4sI", chunk_header)
            chunk_start = stream.tell()
            if chunk_id == b"fmt ":
                chunk = stream.read(min(chunk_size, 40))
                if len(chunk) < 16:
                    raise ValueError(f"Truncated WAV format chunk: {path.name}")
                fmt = struct.unpack("<HHIIHH", chunk[:16])
            elif chunk_id == b"data":
                data_size = chunk_size
            stream.seek(chunk_start + chunk_size + (chunk_size % 2))
            if fmt is not None and data_size is not None:
                break
        if fmt is None or data_size is None:
            raise ValueError(f"WAV format or data chunk missing: {path.name}")
        encoding, channels, sample_rate, _byte_rate, block_align, bits_per_sample = fmt
        if encoding != 3 or bits_per_sample != 32:
            raise ValueError(f"Expected IEEE float32 WAV encoding: {path.name}")
        if block_align != channels * (bits_per_sample // 8) or data_size % block_align:
            raise ValueError(f"Invalid WAV frame alignment: {path.name}")
        return channels, sample_rate, bits_per_sample // 8, data_size // block_align


def parse_metadata(path: Path) -> list[FleursRecord]:
    records: list[FleursRecord] = []
    seen_files: set[str] = set()
    with path.open(encoding="utf-8", newline="") as stream:
        for line_number, raw_line in enumerate(stream, start=1):
            columns = raw_line.rstrip("\r\n").split("\t")
            if len(columns) != 7:
                raise ValueError(
                    f"Expected 7 FLEURS TSV columns on line {line_number}; "
                    f"found {len(columns)}."
                )
            sentence_id, filename, raw_text, normalized_text, phonemized, samples, gender = columns
            if not filename.endswith(".wav") or PurePosixPath(filename).name != filename:
                raise ValueError(f"Unsafe or unexpected audio filename on line {line_number}.")
            if filename in seen_files:
                raise ValueError(f"Duplicate audio filename on line {line_number}: {filename}")
            seen_files.add(filename)
            if not raw_text or not normalized_text:
                raise ValueError(f"Missing transcript on line {line_number}: {filename}")
            sample_count = int(samples)
            if sample_count <= 0:
                raise ValueError(f"Invalid sample count on line {line_number}: {filename}")
            records.append(
                FleursRecord(
                    sentence_id=sentence_id,
                    audio_filename=filename,
                    raw_transcription=raw_text,
                    transcription=normalized_text,
                    phonemized_transcription=phonemized,
                    num_samples=sample_count,
                    gender=gender,
                )
            )
    if not records:
        raise ValueError("FLEURS development metadata is empty.")
    return records


def select_records(
    records: Iterable[FleursRecord], target_seconds: int = TARGET_SECONDS
) -> tuple[list[FleursRecord], list[FleursRecord]]:
    ordered = sorted(records, key=lambda record: record.audio_filename)
    random.Random(SEED).shuffle(ordered)
    selected: list[FleursRecord] = []
    accumulated_seconds = 0.0
    for record in ordered:
        selected.append(record)
        accumulated_seconds += record.duration_seconds
        if accumulated_seconds >= target_seconds:
            break
    if accumulated_seconds < target_seconds:
        raise ValueError(
            f"FLEURS development split totals only {accumulated_seconds:.3f} seconds; "
            f"the requested target is {target_seconds} seconds."
        )
    selected_names = {record.audio_filename for record in selected}
    remaining = [record for record in ordered if record.audio_filename not in selected_names]
    return selected, remaining


def copy_selected_audio(
    archive_path: Path, audio_dir: Path, records: list[FleursRecord]
) -> dict[str, str]:
    expected = {record.audio_filename: record for record in records}
    copied: dict[str, str] = {}
    with tarfile.open(archive_path, mode="r:gz") as archive:
        for member in archive:
            filename = PurePosixPath(member.name).name
            if filename not in expected:
                continue
            if PurePosixPath(member.name).parent != PurePosixPath("dev") or not member.isfile():
                raise ValueError(f"Unexpected FLEURS archive member for {filename}: {member.name}")
            source = archive.extractfile(member)
            if source is None:
                raise ValueError(f"Unable to read selected audio member: {member.name}")
            destination = audio_dir / filename
            with source, destination.open("wb") as output:
                shutil.copyfileobj(source, output)
            channels, sample_rate, _sample_width, frame_count = inspect_wav(destination)
            if channels != 1 or sample_rate != SAMPLE_RATE:
                raise ValueError(f"Unexpected WAV format for {filename}.")
            if frame_count != expected[filename].num_samples:
                raise ValueError(f"TSV/WAV sample-count mismatch for {filename}.")
            copied[filename] = sha256_file(destination)
    missing = set(expected) - set(copied)
    if missing:
        raise ValueError(f"Selected audio files missing from source archive: {sorted(missing)}")
    return copied


def write_outputs(
    output_dir: Path,
    source_dir: Path,
    records: list[FleursRecord],
    selected: list[FleursRecord],
    unselected: list[FleursRecord],
) -> dict[str, object]:
    audio_dir = output_dir / "audio"
    audio_dir.mkdir()
    audio_hashes = copy_selected_audio(source_dir / "dev.tar.gz", audio_dir, selected)

    with (output_dir / "audio_manifest.csv").open("w", encoding="utf-8", newline="") as stream:
        fields = [
            "selection_order",
            "sentence_id",
            "audio_filename",
            "audio_path",
            "duration_seconds",
            "audio_sha256",
            "gender",
            "raw_transcription",
            "transcription",
        ]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for order, record in enumerate(selected, start=1):
            writer.writerow(
                {
                    "selection_order": order,
                    "sentence_id": record.sentence_id,
                    "audio_filename": record.audio_filename,
                    "audio_path": f"audio/{record.audio_filename}",
                    "duration_seconds": f"{record.duration_seconds:.6f}",
                    "audio_sha256": audio_hashes[record.audio_filename],
                    "gender": record.gender,
                    "raw_transcription": record.raw_transcription,
                    "transcription": record.transcription,
                }
            )

    selected_seconds = sum(record.duration_seconds for record in selected)
    inventory = {
        "dataset": "Google FLEURS",
        "config": DATASET_CONFIG,
        "source_split": DATASET_SOURCE_SPLIT,
        "loader_alias": "validation",
        "dataset_revision": DATASET_REVISION,
        "source_url": DATASET_URL,
        "license": "CC BY 4.0",
        "attribution": ATTRIBUTION,
        "source_files": {
            "metadata_path": "dev.tsv",
            "metadata_sha256": sha256_file(source_dir / "dev.tsv"),
            "archive_path": "dev.tar.gz",
            "archive_sha256": sha256_file(source_dir / "dev.tar.gz"),
        },
        "selection": {
            "stable_sort_key": "audio_filename (ascending Unicode string order)",
            "shuffle": "Python random.Random(seed).shuffle",
            "seed": SEED,
            "python_version": sys.version.split()[0],
            "target_seconds": TARGET_SECONDS,
            "rule": "Select complete clips in shuffled order until cumulative duration reaches or exceeds target.",
            "source_record_count": len(records),
            "selected_record_count": len(selected),
            "selected_duration_seconds": round(selected_seconds, 6),
            "unselected_record_count": len(unselected),
            "selected_audio_filenames": [record.audio_filename for record in selected],
            "unselected_audio_filenames": [record.audio_filename for record in unselected],
            "excluded_records": [],
        },
        "audio_validation": {
            "sample_rate_hz": SAMPLE_RATE,
            "channels": 1,
            "encoding": "IEEE float32 WAV",
            "tsv_sample_counts_match_wav_frames": True,
            "selected_audio_sha256": audio_hashes,
        },
    }
    (output_dir / "selection_manifest.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return inventory


def prepare(
    source_dir: Path, output_dir: Path, tracked_manifest_path: Path | None = None
) -> dict[str, object]:
    source_dir = source_dir.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    tsv = source_dir / "dev.tsv"
    archive = source_dir / "dev.tar.gz"
    if not tsv.is_file() or not archive.is_file():
        raise FileNotFoundError("Source directory must contain dev.tsv and dev.tar.gz.")
    if sha256_file(tsv) != EXPECTED_TSV_SHA256:
        raise ValueError("dev.tsv checksum does not match the approved pinned FLEURS revision.")
    if sha256_file(archive) != EXPECTED_ARCHIVE_SHA256:
        raise ValueError("dev.tar.gz checksum does not match the approved pinned FLEURS revision.")
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    records = parse_metadata(tsv)
    selected, unselected = select_records(records)
    temporary_dir = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}-", dir=output_dir.parent))
    try:
        inventory = write_outputs(temporary_dir, source_dir, records, selected, unselected)
        temporary_dir.rename(output_dir)
    except Exception:
        shutil.rmtree(temporary_dir, ignore_errors=True)
        raise
    if tracked_manifest_path is not None:
        tracked_manifest_path = tracked_manifest_path.expanduser().resolve()
        tracked_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output_dir / "audio_manifest.csv", tracked_manifest_path)
    return inventory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True, help="Directory with pinned dev.tsv and dev.tar.gz")
    parser.add_argument("--output-dir", type=Path, required=True, help="New persistent directory for selected audio and manifests")
    parser.add_argument("--tracked-manifest", type=Path, help="Optional repository path for the selected-clip manifest")
    args = parser.parse_args()
    inventory = prepare(args.source_dir, args.output_dir, args.tracked_manifest)
    selection = inventory["selection"]
    print(
        "Prepared {selected_record_count} clips ({selected_duration_seconds:.3f}s) "
        "from {source_record_count} eligible FLEURS dev clips at seed {seed}.".format(**selection)
    )
    print(f"Output: {args.output_dir.expanduser().resolve()}")


if __name__ == "__main__":
    main()
