#!/usr/bin/env python3
"""Score saved STT run JSONL files using Plan 04/00 corpus CER rules."""

from __future__ import annotations

import argparse
import csv
import json
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


def normalize_for_cer(text: str) -> str:
    """Apply the approved scoring-only normalization; preserve source text elsewhere."""
    normalized = unicodedata.normalize("NFC", text)
    return "".join(
        char.lower() if "A" <= char <= "Z" else char
        for char in normalized
        if not char.isspace() and not unicodedata.category(char).startswith("P")
    )


def edit_counts(reference: str, hypothesis: str) -> tuple[int, int, int]:
    """Return deterministic character-level substitution, deletion, insertion counts."""
    rows, columns = len(reference), len(hypothesis)
    distances = [[0] * (columns + 1) for _ in range(rows + 1)]
    operations = [[""] * (columns + 1) for _ in range(rows + 1)]
    for i in range(1, rows + 1):
        distances[i][0], operations[i][0] = i, "delete"
    for j in range(1, columns + 1):
        distances[0][j], operations[0][j] = j, "insert"
    for i in range(1, rows + 1):
        for j in range(1, columns + 1):
            if reference[i - 1] == hypothesis[j - 1]:
                distances[i][j] = distances[i - 1][j - 1]
                operations[i][j] = "match"
                continue
            # Tie priority is fixed for reproducible S/D/I attribution.
            choices = (
                (distances[i - 1][j - 1] + 1, "substitution"),
                (distances[i - 1][j] + 1, "delete"),
                (distances[i][j - 1] + 1, "insert"),
            )
            distances[i][j], operations[i][j] = min(choices, key=lambda item: item[0])
    substitutions = deletions = insertions = 0
    i, j = rows, columns
    while i or j:
        operation = operations[i][j]
        if operation == "match":
            i -= 1
            j -= 1
        elif operation == "substitution":
            substitutions += 1
            i -= 1
            j -= 1
        elif operation == "delete":
            deletions += 1
            i -= 1
        elif operation == "insert":
            insertions += 1
            j -= 1
        else:
            raise AssertionError(f"Missing edit operation at ({i}, {j}).")
    return substitutions, deletions, insertions


def score_rows(
    rows: Iterable[dict[str, Any]], expected_clip_ids: set[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build per-clip and per-candidate/repetition aggregate records."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        candidate = str(row["candidate_id"])
        repetition = str(row["repetition"])
        clip_id = str(row["clip_id"])
        if clip_id not in expected_clip_ids:
            raise ValueError(f"Unexpected clip ID in result: {clip_id}")
        identity = candidate, repetition, clip_id
        if identity in seen:
            raise ValueError(f"Duplicate result row for {identity}")
        seen.add(identity)
        if row.get("status") not in {"success", "failure"}:
            raise ValueError(f"Invalid result status for {identity}")
        groups[(candidate, repetition)].append(row)

    per_clip: list[dict[str, Any]] = []
    aggregates: list[dict[str, Any]] = []
    for (candidate, repetition), run_rows in sorted(groups.items()):
        succeeded = failed = scored = 0
        reference_characters = substitutions = deletions = insertions = 0
        scored_audio_seconds = successful_audio_seconds = 0.0
        successful_processing_seconds = failed_processing_seconds = read_seconds = 0.0
        run_clip_ids: set[str] = set()
        for row in sorted(run_rows, key=lambda value: str(value["clip_id"])):
            clip_id = str(row["clip_id"])
            run_clip_ids.add(clip_id)
            status = row["status"]
            duration = float(row.get("audio_duration_seconds", 0.0))
            read_time = float(row.get("audio_read_seconds", 0.0))
            process_time = float(row.get("processing_seconds", 0.0))
            read_seconds += read_time
            if status == "failure":
                failed += 1
                failed_processing_seconds += process_time
                per_clip.append(
                    {
                        "candidate_id": candidate,
                        "repetition": repetition,
                        "clip_id": clip_id,
                        "status": "failure",
                        "reference_characters": "",
                        "substitutions": "",
                        "deletions": "",
                        "insertions": "",
                        "cer": "",
                        "audio_duration_seconds": duration,
                        "audio_read_seconds": read_time,
                        "processing_seconds": process_time,
                        "error": row.get("error", ""),
                    }
                )
                continue
            succeeded += 1
            successful_processing_seconds += process_time
            successful_audio_seconds += duration
            reference = row.get("reference_raw_transcription")
            hypothesis = row.get("hypothesis_raw_transcription")
            if not isinstance(reference, str) or not isinstance(hypothesis, str):
                raise ValueError(f"Successful result lacks reference/hypothesis for {identity}")
            normalized_reference = normalize_for_cer(reference)
            normalized_hypothesis = normalize_for_cer(hypothesis)
            if not normalized_reference:
                per_clip.append(
                    {
                        "candidate_id": candidate,
                        "repetition": repetition,
                        "clip_id": clip_id,
                        "status": "undefined_empty_reference",
                        "reference_characters": 0,
                        "substitutions": "",
                        "deletions": "",
                        "insertions": "",
                        "cer": "",
                        "audio_duration_seconds": duration,
                        "audio_read_seconds": read_time,
                        "processing_seconds": process_time,
                        "error": "",
                    }
                )
                continue
            s_count, d_count, i_count = edit_counts(normalized_reference, normalized_hypothesis)
            char_count = len(normalized_reference)
            clip_cer = (s_count + d_count + i_count) / char_count
            scored += 1
            reference_characters += char_count
            substitutions += s_count
            deletions += d_count
            insertions += i_count
            scored_audio_seconds += duration
            per_clip.append(
                {
                    "candidate_id": candidate,
                    "repetition": repetition,
                    "clip_id": clip_id,
                    "status": "scored",
                    "reference_characters": char_count,
                    "substitutions": s_count,
                    "deletions": d_count,
                    "insertions": i_count,
                    "cer": clip_cer,
                    "audio_duration_seconds": duration,
                    "audio_read_seconds": read_time,
                    "processing_seconds": process_time,
                    "error": "",
                }
            )
        total_errors = substitutions + deletions + insertions
        aggregates.append(
            {
                "candidate_id": candidate,
                "repetition": repetition,
                "expected_clips": len(expected_clip_ids),
                "result_rows": len(run_rows),
                "completed_clips": succeeded,
                "failed_clips": failed,
                "missing_clips": len(expected_clip_ids - run_clip_ids),
                "scored_clips": scored,
                "reference_characters": reference_characters,
                "substitutions": substitutions,
                "deletions": deletions,
                "insertions": insertions,
                "total_errors": total_errors,
                "corpus_cer": total_errors / reference_characters if reference_characters else "",
                "scored_audio_seconds": scored_audio_seconds,
                "successful_audio_seconds": successful_audio_seconds,
                "audio_read_seconds": read_seconds,
                "successful_processing_seconds": successful_processing_seconds,
                "failed_processing_seconds": failed_processing_seconds,
                "successful_path_rtf": (
                    successful_processing_seconds / successful_audio_seconds
                    if successful_audio_seconds else ""
                ),
            }
        )
    return per_clip, aggregates


def common_clip_scores(
    rows: Iterable[dict[str, Any]], expected_clip_count: int
) -> list[dict[str, Any]]:
    """Compare candidate pairs on shared successfully scored clips, by repetition."""
    groups: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        if row.get("status") != "success":
            continue
        reference = row.get("reference_raw_transcription")
        hypothesis = row.get("hypothesis_raw_transcription")
        if not isinstance(reference, str) or not isinstance(hypothesis, str):
            continue
        normalized_reference = normalize_for_cer(reference)
        if not normalized_reference:
            continue
        key = (str(row["candidate_id"]), str(row["repetition"]))
        groups[key][str(row["clip_id"])] = {
            "reference": normalized_reference,
            "hypothesis": normalize_for_cer(hypothesis),
        }

    candidates = sorted({candidate for candidate, _rep in groups})
    repetitions = sorted({rep for _candidate, rep in groups})
    output = []
    for repetition in repetitions:
        for index, candidate_a in enumerate(candidates):
            rows_a = groups.get((candidate_a, repetition), {})
            for candidate_b in candidates[index + 1 :]:
                rows_b = groups.get((candidate_b, repetition), {})
                common_ids = sorted(set(rows_a) & set(rows_b))
                if not common_ids:
                    continue
                errors_a = errors_b = characters = 0
                for clip_id in common_ids:
                    item_a, item_b = rows_a[clip_id], rows_b[clip_id]
                    if item_a["reference"] != item_b["reference"]:
                        raise ValueError(f"Candidate references differ for common clip {clip_id}.")
                    characters += len(item_a["reference"])
                    s_a, d_a, i_a = edit_counts(item_a["reference"], item_a["hypothesis"])
                    s_b, d_b, i_b = edit_counts(item_b["reference"], item_b["hypothesis"])
                    errors_a += s_a + d_a + i_a
                    errors_b += s_b + d_b + i_b
                output.append(
                    {
                        "candidate_a": candidate_a,
                        "candidate_b": candidate_b,
                        "repetition": repetition,
                        "common_scored_clips": len(common_ids),
                        "expected_clips": expected_clip_count,
                        "coverage": len(common_ids) / expected_clip_count if expected_clip_count else "",
                        "common_reference_characters": characters,
                        "candidate_a_common_cer": errors_a / characters,
                        "candidate_b_common_cer": errors_b / characters,
                    }
                )
    return output


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True, help="JSONL containing preserved per-clip run records")
    parser.add_argument("--audio-manifest", type=Path, required=True, help="Frozen selected-clip manifest")
    parser.add_argument("--candidate-runtime", type=Path, help="Candidate runtime/resource summary JSON from the same run")
    parser.add_argument("--output-dir", type=Path, required=True, help="New output directory, outside Git")
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {args.output_dir}")
    with args.audio_manifest.open(encoding="utf-8", newline="") as stream:
        manifest_rows = list(csv.DictReader(stream))
    expected_ids = {row["audio_filename"] for row in manifest_rows}
    if not expected_ids or len(expected_ids) != len(manifest_rows):
        raise ValueError("Audio manifest must contain a nonempty, unique audio_filename column.")
    records = []
    with args.results.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON on result line {line_number}.") from exc
    per_clip, aggregates = score_rows(records, expected_ids)
    runtime_by_candidate = {}
    if args.candidate_runtime:
        runtime_data = json.loads(args.candidate_runtime.read_text(encoding="utf-8"))
        runtime_by_candidate = {str(item["candidate_id"]): item for item in runtime_data}
    resource_fields = [
        "model_load_seconds", "backend_or_provider", "cpu_mean_percent", "cpu_peak_percent",
        "pre_model_load_process_rss_bytes", "post_model_load_process_rss_bytes",
        "post_warmup_process_rss_bytes", "inference_peak_process_rss_bytes",
        "pre_model_load_mps_driver_allocated_bytes", "post_model_load_mps_driver_allocated_bytes",
        "post_warmup_mps_driver_allocated_bytes", "inference_peak_pytorch_mps_driver_allocated_bytes",
        "resource_sampling_interval_seconds", "resource_sample_count",
    ]
    for aggregate in aggregates:
        item = runtime_by_candidate.get(aggregate["candidate_id"], {})
        aggregate.update({
            "model_load_seconds": item.get("load_seconds", ""),
            "backend_or_provider": json.dumps(item.get("backend_or_provider", ""), ensure_ascii=False),
            "cpu_mean_percent": item.get("cpu_mean_percent", ""),
            "cpu_peak_percent": item.get("cpu_peak_percent", ""),
            "pre_model_load_process_rss_bytes": item.get("pre_model_load_process_rss_bytes", ""),
            "post_model_load_process_rss_bytes": item.get("post_model_load_process_rss_bytes", ""),
            "post_warmup_process_rss_bytes": item.get("post_warmup_process_rss_bytes", ""),
            "inference_peak_process_rss_bytes": item.get("inference_peak_process_rss_bytes", ""),
            "pre_model_load_mps_driver_allocated_bytes": item.get("pre_model_load_mps_driver_allocated_bytes", ""),
            "post_model_load_mps_driver_allocated_bytes": item.get("post_model_load_mps_driver_allocated_bytes", ""),
            "post_warmup_mps_driver_allocated_bytes": item.get("post_warmup_mps_driver_allocated_bytes", ""),
            "inference_peak_pytorch_mps_driver_allocated_bytes": item.get("inference_peak_pytorch_mps_driver_allocated_bytes", ""),
            "resource_sampling_interval_seconds": item.get("sampling_interval_seconds", ""),
            "resource_sample_count": item.get("sample_count", ""),
        })
    common = common_clip_scores(records, len(expected_ids))
    args.output_dir.mkdir(parents=True)
    per_clip_fields = [
        "candidate_id", "repetition", "clip_id", "status", "reference_characters",
        "substitutions", "deletions", "insertions", "cer", "audio_duration_seconds",
        "audio_read_seconds", "processing_seconds", "error",
    ]
    aggregate_fields = [
        "candidate_id", "repetition", "expected_clips", "result_rows", "completed_clips",
        "failed_clips", "missing_clips", "scored_clips", "reference_characters",
        "substitutions", "deletions", "insertions", "total_errors", "corpus_cer",
        "scored_audio_seconds", "successful_audio_seconds", "audio_read_seconds",
        "successful_processing_seconds", "failed_processing_seconds", "successful_path_rtf",
    ] + resource_fields
    common_fields = [
        "candidate_a", "candidate_b", "repetition", "common_scored_clips",
        "expected_clips", "coverage", "common_reference_characters",
        "candidate_a_common_cer", "candidate_b_common_cer",
    ]
    write_csv(args.output_dir / "per_clip_scores.csv", per_clip, per_clip_fields)
    write_csv(args.output_dir / "metrics.csv", aggregates, aggregate_fields)
    write_csv(args.output_dir / "common_clip_metrics.csv", common, common_fields)
    print(f"Scored {len(aggregates)} candidate/repetition groups into {args.output_dir}")


if __name__ == "__main__":
    main()
