#!/usr/bin/env python3
"""Aggregate the frozen first-pass context screen without retaining speech text."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import wave

LABELS = ("Scam", "Not Scam")
APPROACHES = ("latest", "recent", "accumulated")


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def sample_summary(values: list[float]) -> dict:
    return {"n": len(values), "mean": statistics.mean(values) if values else None,
            "sample_sd": statistics.stdev(values) if len(values) > 1 else None}


def _finite_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def undefined_metric_reason(denominator: int, reason: str) -> str | None:
    return None if denominator else reason


def session_diagnostics(events: list[dict], sample_rate_hz: int = 16000) -> dict:
    """Derive component timings and queue/resource observations from original events."""
    stt_durations = []
    for event in events:
        if event.get("kind") != "stt_completed":
            continue
        resources = event.get("resources") or {}
        duration = resources.get("processing_seconds")
        if _finite_number(duration) and duration >= 0:
            stt_durations.append(float(duration))

    classifier_starts = {}
    classifier_durations = []
    for event in events:
        if event.get("kind") == "classification_started":
            request_id = event.get("request_id")
            elapsed = event.get("host_elapsed_s")
            if request_id is not None and _finite_number(elapsed):
                classifier_starts[request_id] = float(elapsed)
        elif event.get("kind") == "classification_completed":
            response = event.get("response") or {}
            request_id = response.get("request_id")
            started = classifier_starts.get(request_id)
            ended = event.get("host_elapsed_s")
            if started is not None and _finite_number(ended) and ended >= started:
                classifier_durations.append(float(ended) - started)

    # Host queue high-water is a derived sample-range backlog, not a native
    # queue observation. Require contiguous accepted ranges before reporting it.
    ordered = sorted(events, key=lambda e: e.get("event_id", 0))
    accepted_end = 0
    processed_end = 0
    expected_start = 0
    queue_highwater_samples = 0
    saw_audio_range = False
    contiguous = True
    for event in ordered:
        kind = event.get("kind")
        if kind == "audio_accepted":
            start, end = event.get("start_sample"), event.get("end_sample")
            if not (isinstance(start, int) and isinstance(end, int) and end >= start):
                contiguous = False
                continue
            saw_audio_range = True
            if start != expected_start:
                contiguous = False
            expected_start = max(expected_start, end)
            accepted_end = max(accepted_end, end)
        elif kind == "stt_completed":
            end = event.get("end_sample")
            if isinstance(end, int):
                processed_end = max(processed_end, end)
        if saw_audio_range:
            queue_highwater_samples = max(queue_highwater_samples, accepted_end - processed_end)

    if saw_audio_range and contiguous:
        queue_highwater_seconds = max(0, queue_highwater_samples) / sample_rate_hz
        queue_reason = None
    else:
        queue_highwater_seconds = None
        queue_reason = ("no_audio_acceptance_ranges" if not saw_audio_range
                        else "noncontiguous_or_invalid_audio_acceptance_ranges")

    notification_events = [event for event in events
                           if event.get("kind") == "client_observation"
                           and event.get("client_kind") == "notification_posted"]
    first_notification = notification_events[0] if notification_events else None
    native_resources = [event for event in events
                        if event.get("kind") == "client_observation"
                        and event.get("client_kind") == "native_resource_sample"]
    pss = [event["process_pss_bytes"] for event in native_resources
           if _finite_number(event.get("process_pss_bytes"))]
    cpu = [event["process_cpu_time_ms"] for event in native_resources
           if _finite_number(event.get("process_cpu_time_ms"))]
    return {
        "stt_processing_seconds": sample_summary(stt_durations),
        "classifier_host_duration_seconds": sample_summary(classifier_durations),
        "notification_posted_observation_n": len(notification_events),
        "first_notification_posted_client_elapsed_ms": (
            first_notification.get("client_elapsed_ms") if first_notification else None),
        "first_notification_posted_audio_position_ms": (
            first_notification.get("audio_position_ms") if first_notification else None),
        "android_native_resource_sample_n": len(native_resources),
        "android_process_pss_bytes_max": max(pss) if pss else None,
        "android_process_pss_value_n": len(pss),
        "android_process_cpu_time_ms_max": max(cpu) if cpu else None,
        "android_process_cpu_time_value_n": len(cpu),
        "max_queued_seconds_derived": queue_highwater_seconds,
        "max_queued_seconds_derived_reason": queue_reason,
        "max_queued_seconds_source": "accepted_end_minus_latest_stt_completed_end_sample_over_sample_rate"
        if queue_highwater_seconds is not None else None,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_demo_selection(evaluation_dir: Path, manifest: dict) -> dict | None:
    """Load and bind the owner's bounded demo choice to this run's model identity."""
    path = evaluation_dir / "demo_selection.json"
    if not path.is_file():
        return None
    selection = json.loads(path.read_text(encoding="utf-8"))
    approach = selection.get("selected_approach")
    if approach not in APPROACHES or selection.get("owner_approved") is not True:
        raise ValueError("demo_selection.json must name an approved approach")
    if selection.get("scope") != "provisional_demo":
        raise ValueError("demo selection scope must be provisional_demo")
    if selection.get("formal_release_approved") is not False or selection.get("final_test_access_authorized") is not False:
        raise ValueError("demo selection must preserve formal-release and final-test restrictions")
    if not selection.get("plan_reference") or not selection.get("approval_date"):
        raise ValueError("demo selection is missing plan or approval provenance")
    token_budget = selection.get("token_budget")
    if not isinstance(token_budget, int) or isinstance(token_budget, bool) or token_budget <= 0:
        raise ValueError("demo selection token_budget must be a positive integer")

    classifier = manifest.get("classifier_identity") or {}
    model_hash = (classifier.get("bundle_files_sha256") or {}).get("model.safetensors")
    model_version = manifest.get("model_version")
    if model_hash and model_version and model_hash != model_version:
        raise ValueError("manifest model_version does not match classifier model artifact hash")
    return {
        "selected_approach": approach,
        "scope": selection["scope"],
        "owner_approved": True,
        "approval_date": selection["approval_date"],
        "approval_evidence": selection.get("approval_evidence"),
        "token_budget": token_budget,
        "retain": selection.get("retain"),
        "basis": selection.get("basis"),
        "plan_reference": selection["plan_reference"],
        "formal_release_approved": False,
        "final_test_access_authorized": False,
        "recording_fidelity": selection.get("recording_fidelity"),
        "selection_sidecar_sha256": sha256_file(path),
        "model_provenance": {
            "model_kind": manifest.get("model_kind"),
            "model_version": model_version,
            "configuration_id": manifest.get("configuration_id"),
            "classifier_artifact_manifest_sha256": classifier.get("artifact_manifest_sha256"),
            "model_bundle_run_id": classifier.get("model_bundle_run_id"),
            "apk_sha256": manifest.get("apk_sha256"),
        },
    }


def metric_summary(cases: list[dict]) -> dict:
    eligible = [row for row in cases
                if row.get("usable_completed_run") is True and row["outcome"] in LABELS]
    matrix = {actual: {pred: 0 for pred in LABELS} for actual in LABELS}
    for row in eligible:
        matrix[row["actual"]][row["outcome"]] += 1
    tp = matrix["Scam"]["Scam"]
    fp = matrix["Not Scam"]["Scam"]
    fn = matrix["Scam"]["Not Scam"]
    tn = matrix["Not Scam"]["Not Scam"]
    denominators = {
        "scam_precision": tp + fp,
        "scam_recall": tp + fn,
        "scam_f1": 2 * tp + fp + fn,
        "not_scam_precision": tn + fn,
        "not_scam_recall": tn + fp,
        "not_scam_f1": 2 * tn + fn + fp,
        "accuracy": len(eligible),
    }
    precision = tp / denominators["scam_precision"] if denominators["scam_precision"] else 0.0
    recall = tp / denominators["scam_recall"] if denominators["scam_recall"] else 0.0
    scam_f1 = (2 * tp / denominators["scam_f1"] if denominators["scam_f1"] else 0.0)
    not_precision = tn / denominators["not_scam_precision"] if denominators["not_scam_precision"] else 0.0
    not_recall = tn / denominators["not_scam_recall"] if denominators["not_scam_recall"] else 0.0
    not_f1 = (2 * tn / denominators["not_scam_f1"] if denominators["not_scam_f1"] else 0.0)
    metric_reasons = {
        "scam_precision": undefined_metric_reason(denominators["scam_precision"], "no_predicted_scam_cases"),
        "scam_recall": undefined_metric_reason(denominators["scam_recall"], "no_actual_scam_cases"),
        "scam_f1": undefined_metric_reason(denominators["scam_f1"], "no_actual_or_predicted_scam_cases"),
        "not_scam_precision": undefined_metric_reason(denominators["not_scam_precision"], "no_predicted_not_scam_cases"),
        "not_scam_recall": undefined_metric_reason(denominators["not_scam_recall"], "no_actual_not_scam_cases"),
        "not_scam_f1": undefined_metric_reason(denominators["not_scam_f1"], "no_actual_or_predicted_not_scam_cases"),
        "accuracy": undefined_metric_reason(denominators["accuracy"], "no_eligible_completed_cases"),
        "macro_f1": undefined_metric_reason(denominators["accuracy"], "no_eligible_completed_cases"),
    }
    metric_values = {
        "scam_precision": precision, "scam_recall": recall, "scam_f1": scam_f1,
        "not_scam_precision": not_precision, "not_scam_recall": not_recall,
        "not_scam_f1": not_f1, "accuracy": (tp + tn) / len(eligible) if eligible else 0.0,
    }
    return {"eligible_n": len(eligible), "completed_n": sum(row.get("usable_completed_run") is True for row in cases),
            "assigned_n": len(cases), "coverage": len(eligible) / len(cases) if cases else None,
            "confusion_matrix_actual_rows_predicted_columns": matrix,
            "scam_precision": precision, "scam_recall": recall, "scam_f1": scam_f1,
            "not_scam_precision": not_precision, "not_scam_recall": not_recall,
            "not_scam_f1": not_f1, "macro_f1": (scam_f1 + not_f1) / 2,
            "accuracy": metric_values["accuracy"],
            "metric_defined": {name: reason is None for name, reason in metric_reasons.items()},
            "undefined_metric_reasons": {name: reason for name, reason in metric_reasons.items() if reason},
            "unresolved_n": sum(row["outcome"] is None for row in cases)}


def aggregate(evaluation_dir: Path, storage: Path) -> dict:
    manifest = json.loads((evaluation_dir / "artifact_manifest.json").read_text(encoding="utf-8"))
    demo_selection = load_demo_selection(evaluation_dir, manifest)
    schedule = manifest["schedule"]
    recordings_dir = Path(manifest["recordings_path"])
    audio_manifest = {}
    with (recordings_dir / "audio_manifest.csv").open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            path = recordings_dir / row["audio_file"]
            with wave.open(str(path), "rb") as audio:
                audio_manifest[row["recording_id"]] = {
                    "expected_samples": audio.getnframes(),
                    "sample_rate_hz": audio.getframerate(),
                    "channels": audio.getnchannels(),
                }
    ledger = read_jsonl(evaluation_dir / "attempt_events.jsonl")
    finished = {row["assigned_run_id"]: row for row in ledger
                if row.get("event") == "attempt_finished"}
    started = {row["assigned_run_id"]: row for row in ledger
               if row.get("event") == "attempt_started"}
    attributions = {}
    attribution_path = evaluation_dir / "failure_session_attributions.json"
    if attribution_path.is_file():
        try:
            attribution_doc = json.loads(attribution_path.read_text(encoding="utf-8"))
            for item in attribution_doc.get("attributions", []):
                attributions[item.get("assigned_run_id")] = item
        except (OSError, json.JSONDecodeError):
            attributions = {}
    warning_evidence = {row.get("assigned_run_id"): row for row in ledger
                        if row.get("event") == "warning_evidence"}
    cases = []
    for assignment in schedule:
        assigned_id = assignment["assigned_run_id"]
        attempt = finished.get(assigned_id, {})
        start_event = started.get(assigned_id, {})
        session_id = attempt.get("session_id")
        attribution = attributions.get(assigned_id)
        attribution_verified = False
        if attribution and attribution.get("session_id"):
            candidate_dir = storage / "runs" / attribution["session_id"]
            try:
                snapshot_hash = sha256_file(candidate_dir / "snapshot.json")
                events_hash = sha256_file(candidate_dir / "events.jsonl")
                if (snapshot_hash == attribution.get("snapshot_sha256")
                        and events_hash == attribution.get("events_sha256")):
                    attribution_verified = True
                    if not session_id:
                        session_id = attribution["session_id"]
                    elif session_id != attribution["session_id"]:
                        attribution_verified = False
            except OSError:
                pass
        session_dir = storage / "runs" / session_id if session_id else None
        snapshot = {}
        events = []
        if session_dir:
            try:
                snapshot = json.loads((session_dir / "snapshot.json").read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
            events = read_jsonl(session_dir / "events.jsonl")
        predictions = [event.get("response", {}) for event in events
                       if event.get("kind") == "classification_completed"
                       and event.get("response", {}).get("status") == "success"
                       and event.get("response", {}).get("label") in LABELS]
        labels = [item["label"] for item in predictions]
        expected_audio = audio_manifest[assignment["recording_id"]]
        observed_samples = snapshot.get("audio_samples", attempt.get("audio_samples"))
        processed_samples = snapshot.get("processed_samples", attempt.get("processed_samples"))
        no_error = not snapshot.get("error") and not attempt.get("error")
        timeout_status = attempt.get("harness_timeout")
        no_timeout = timeout_status is False
        complete = (attempt.get("state") == "complete" and snapshot.get("state") == "complete"
                    and no_error and no_timeout and expected_audio["sample_rate_hz"] == 16000
                    and expected_audio["channels"] == 1
                    and observed_samples == expected_audio["expected_samples"]
                    and processed_samples == expected_audio["expected_samples"])
        # The plan's first-pass conversation rule: any valid Scam prediction
        # defines Scam; Not Scam requires a completed run with a valid prediction.
        outcome = ("Scam" if "Scam" in labels else
                   "Not Scam" if complete and "Not Scam" in labels else None) if complete else None
        session_start = next((e.get("host_elapsed_s") for e in events
                              if e.get("kind") == "session_created"), None)
        first_scam = next((e.get("host_elapsed_s") for e in events
                           if e.get("kind") == "classification_completed"
                           and e.get("response", {}).get("status") == "success"
                           and e.get("response", {}).get("label") == "Scam"), None)
        detection_s = (first_scam - session_start) if first_scam is not None and session_start is not None else None
        any_scam_event = first_scam is not None
        resources = [e for e in events if e.get("kind") == "resource_sample"]
        client_kinds = [e.get("client_kind") for e in events if e.get("kind") == "client_observation"]
        diagnostics = session_diagnostics(events, expected_audio["sample_rate_hz"])
        start_wall = next((e.get("started_wall_time") for e in ledger
                           if e.get("event") == "attempt_started" and e.get("assigned_run_id") == assigned_id), None)
        finish_wall = attempt.get("finished_wall_time")
        prediction_usable = complete and outcome in LABELS
        cases.append({
            "assigned_run_id": assigned_id, "recording_id": assignment["recording_id"],
            "sample_id": assignment.get("sample_id"), "group_id": assignment.get("group_id"),
            "source_dataset": assignment.get("source_dataset"),
            "attempt_id": start_event.get("attempt_id"),
            "attempt_apk_sha256": start_event.get("apk_sha256"),
            "attempt_source_sha256": start_event.get("source_sha256"),
            "session_id": session_id,
            "retrospective_session_attribution": ({
                "verified_by_snapshot_and_event_sha256": attribution_verified,
                "basis": attribution.get("basis"),
                "snapshot_sha256": attribution.get("snapshot_sha256"),
                "events_sha256": attribution.get("events_sha256"),
            } if attribution_verified else None),
            "actual": assignment["label"], "approach": assignment["approach"],
            "attempt_status": attempt.get("status", attempt.get("state", "not_started")),
            "attempt_error": attempt.get("error"),
            "session_state": snapshot.get("state", attempt.get("state")),
            "prediction_events": len(predictions), "prediction_labels": labels,
            "outcome": outcome, "usable_completed_run": complete,
            "scam_event_any_state": any_scam_event,
            "scam_event_on_incomplete_run": any_scam_event and not complete,
            "completion_exclusion_reasons": ([reason for reason, failed in (
                ("attempt_not_complete", attempt.get("state") != "complete"),
                ("snapshot_not_complete", snapshot.get("state") != "complete"),
                ("error_present", not no_error),
                ("harness_timeout", timeout_status is True),
                ("timeout_status_unrecorded", timeout_status is not True and timeout_status is not False),
                ("sample_count_or_format_mismatch", not (
                    expected_audio["sample_rate_hz"] == 16000 and expected_audio["channels"] == 1
                    and observed_samples == expected_audio["expected_samples"]
                    and processed_samples == expected_audio["expected_samples"])),
            ) if failed] if not complete else []),
            "expected_audio_samples": expected_audio["expected_samples"],
            "observed_audio_samples": observed_samples, "processed_audio_samples": processed_samples,
            "warning": bool(snapshot.get("warning") or attempt.get("warning")),
            "warning_from_completed_run": bool(prediction_usable and snapshot.get("warning")),
            "warning_evidence_captured": assigned_id in warning_evidence,
            "system_banner_visibility": attempt.get("system_banner_visibility", "not_assessed"),
            "notification_posted_observation_n": diagnostics["notification_posted_observation_n"],
            "first_notification_posted_client_elapsed_ms": diagnostics["first_notification_posted_client_elapsed_ms"],
            "first_notification_posted_audio_position_ms": diagnostics["first_notification_posted_audio_position_ms"],
            "first_scam_detection_host_session_elapsed_s": detection_s if prediction_usable else None,
            "first_scam_event_host_session_elapsed_s_any_state": detection_s,
            "true_scam_detection_host_session_elapsed_s": detection_s if prediction_usable and assignment["label"] == "Scam" and "Scam" in labels else None,
            "false_warning_host_session_elapsed_s": detection_s if prediction_usable and assignment["label"] == "Not Scam" and "Scam" in labels else None,
            "attempt_wall_seconds": (finish_wall - start_wall) if start_wall and finish_wall else None,
            "host_resource_sample_n": len(resources),
            "host_cpu_percent_max": max((e["process_cpu_percent"] for e in resources if isinstance(e.get("process_cpu_percent"), (int, float))), default=None),
            "host_rss_bytes_max": max((e["process_rss_bytes"] for e in resources if isinstance(e.get("process_rss_bytes"), (int, float))), default=None),
            "mps_allocated_bytes_max": max((e["mps_driver_allocated_bytes"] for e in resources if isinstance(e.get("mps_driver_allocated_bytes"), (int, float))), default=None),
            "stt_processing_seconds": diagnostics["stt_processing_seconds"],
            "classifier_host_duration_seconds": diagnostics["classifier_host_duration_seconds"],
            "android_native_resource_sample_n": diagnostics["android_native_resource_sample_n"],
            "android_process_pss_bytes_max": diagnostics["android_process_pss_bytes_max"],
            "android_process_pss_value_n": diagnostics["android_process_pss_value_n"],
            "android_process_cpu_time_ms_max": diagnostics["android_process_cpu_time_ms_max"],
            "android_process_cpu_time_value_n": diagnostics["android_process_cpu_time_value_n"],
            "max_queued_seconds_derived": diagnostics["max_queued_seconds_derived"],
            "max_queued_seconds_derived_reason": diagnostics["max_queued_seconds_derived_reason"],
            "max_queued_seconds_source": diagnostics["max_queued_seconds_source"],
            "client_pause_observation_n": sum(kind in {"automatic_queue_pause", "playback_paused"} for kind in client_kinds),
        })

    recording_ids = sorted({case["recording_id"] for case in cases})
    matched_ids = [recording_id for recording_id in recording_ids
                   if all(any(case["recording_id"] == recording_id and case["approach"] == approach
                              and case["usable_completed_run"] for case in cases)
                          for approach in APPROACHES)]

    by_approach = {}
    for approach in APPROACHES:
        selected = [case for case in cases if case["approach"] == approach]
        detections = [case["true_scam_detection_host_session_elapsed_s"] for case in selected
                      if case["true_scam_detection_host_session_elapsed_s"] is not None]
        false_warnings = [case["false_warning_host_session_elapsed_s"] for case in selected
                          if case["false_warning_host_session_elapsed_s"] is not None]
        runtimes = [case["attempt_wall_seconds"] for case in selected if case["attempt_wall_seconds"] is not None]
        metrics = metric_summary(selected)
        matrix = metrics["confusion_matrix_actual_rows_predicted_columns"]
        by_approach[approach] = {
            "assigned_n": len(selected),
            "complete_n": sum(case["usable_completed_run"] for case in selected),
            "failed_or_cancelled_n": sum(case["session_state"] in {"failed", "cancelled"}
                                           or case["attempt_status"] in {"harness_failure", "harness_interrupted"}
                                           for case in selected),
            "prediction_warning_coverage_n": sum(case["warning"] for case in selected),
            "any_scam_event_n_including_incomplete_runs": sum(case["scam_event_any_state"] for case in selected),
            "scam_event_on_incomplete_run_n": sum(case["scam_event_on_incomplete_run"] for case in selected),
            "true_scam_event_any_state_n": sum(case["actual"] == "Scam" and case["scam_event_any_state"] for case in selected),
            "false_warning_event_any_state_n": sum(case["actual"] == "Not Scam" and case["scam_event_any_state"] for case in selected),
            "warning_evidence_capture_n": sum(case["warning_evidence_captured"] for case in selected),
            "metrics": metrics,
            "false_warning_n": matrix["Not Scam"]["Scam"],
            "missed_scam_n": matrix["Scam"]["Not Scam"],
            "assigned_by_actual_label": {label: sum(case["actual"] == label for case in selected) for label in LABELS},
            "completed_by_actual_label": {label: sum(case["actual"] == label and case["usable_completed_run"] for case in selected) for label in LABELS},
            "assigned_by_source": {source: sum(case.get("source_dataset") == source for case in selected)
                                   for source in sorted({case.get("source_dataset") for case in selected if case.get("source_dataset")})},
            "completed_by_source": {source: sum(case.get("source_dataset") == source and case["usable_completed_run"] for case in selected)
                                    for source in sorted({case.get("source_dataset") for case in selected if case.get("source_dataset")})},
            "true_scam_detection_host_session_elapsed_s": sample_summary(detections),
            "false_warning_host_session_elapsed_s": sample_summary(false_warnings),
            "attempt_wall_seconds": sample_summary(runtimes),
        }
    matched = [case for case in cases if case["recording_id"] in matched_ids]
    matched_by_approach = {}
    for approach in APPROACHES:
        selected = [case for case in matched if case["approach"] == approach]
        metrics = metric_summary(selected)
        matrix = metrics["confusion_matrix_actual_rows_predicted_columns"]
        matched_by_approach[approach] = {
            "matched_recording_n": len(matched_ids), "assigned_n": len(selected),
            "completed_n": sum(case["usable_completed_run"] for case in selected),
            "metrics": metrics,
            "false_warning_n": matrix["Not Scam"]["Scam"],
            "missed_scam_n": matrix["Scam"]["Not Scam"],
            "assigned_by_source": {source: sum(case.get("source_dataset") == source for case in selected)
                                   for source in sorted({case.get("source_dataset") for case in selected if case.get("source_dataset")})},
            "completed_by_source": {source: sum(case.get("source_dataset") == source and case["usable_completed_run"] for case in selected)
                                    for source in sorted({case.get("source_dataset") for case in selected if case.get("source_dataset")})},
            "true_scam_detection_host_session_elapsed_s": sample_summary([
                case["true_scam_detection_host_session_elapsed_s"] for case in selected
                if case["true_scam_detection_host_session_elapsed_s"] is not None]),
            "false_warning_host_session_elapsed_s": sample_summary([
                case["false_warning_host_session_elapsed_s"] for case in selected
                if case["false_warning_host_session_elapsed_s"] is not None]),
        }

    def case_level_mean(selected, field):
        values = []
        for case in selected:
            item = case.get(field) or {}
            if item.get("n", 0) and _finite_number(item.get("mean")):
                values.append(float(item["mean"]))
        return sample_summary(values)

    def diagnostics_summary(selected):
        return {
            "stt_mean_window_processing_seconds_per_run": case_level_mean(selected, "stt_processing_seconds"),
            "classifier_mean_request_duration_seconds_per_run": case_level_mean(selected, "classifier_host_duration_seconds"),
            "derived_queue_highwater_seconds_per_run": sample_summary([
                float(case["max_queued_seconds_derived"]) for case in selected
                if _finite_number(case.get("max_queued_seconds_derived"))]),
            "android_process_pss_run_maxima_bytes": sample_summary([
                float(case["android_process_pss_bytes_max"]) for case in selected
                if _finite_number(case.get("android_process_pss_bytes_max"))]),
            "android_process_cpu_time_run_maxima_ms": sample_summary([
                float(case["android_process_cpu_time_ms_max"]) for case in selected
                if _finite_number(case.get("android_process_cpu_time_ms_max"))]),
            "notification_posted_client_elapsed_ms": sample_summary([
                float(case["first_notification_posted_client_elapsed_ms"]) for case in selected
                if _finite_number(case.get("first_notification_posted_client_elapsed_ms"))]),
            "notification_posted_audio_position_ms": sample_summary([
                float(case["first_notification_posted_audio_position_ms"]) for case in selected
                if _finite_number(case.get("first_notification_posted_audio_position_ms"))]),
        }

    for approach in APPROACHES:
        by_approach[approach]["diagnostics"] = diagnostics_summary(
            [case for case in cases if case["approach"] == approach])
        matched_by_approach[approach]["diagnostics"] = diagnostics_summary(
            [case for case in matched if case["approach"] == approach])
    execution_variants = {}
    for assigned_id, event in started.items():
        identity = {"apk_sha256": event.get("apk_sha256"), "source_sha256": event.get("source_sha256")}
        key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()
        execution_variants.setdefault(key, {**identity, "assigned_run_ids": []})["assigned_run_ids"].append(assigned_id)
    return {
        "scope": "provisional development context screen; owner-approved demo choice recorded separately; recording fidelity unverified; no formal integration freeze",
        "model_kind": manifest.get("model_kind"), "model_version": manifest.get("model_version"),
        "configuration_id": manifest.get("configuration_id"),
        "run_artifact_identity": {
            "artifact_manifest_sha256": sha256_file(evaluation_dir / "artifact_manifest.json"),
            "attempt_events_sha256": sha256_file(evaluation_dir / "attempt_events.jsonl"),
            "failure_session_attributions_sha256": (sha256_file(attribution_path) if attribution_path.is_file() else None),
            "demo_selection_sha256": demo_selection["selection_sidecar_sha256"] if demo_selection else None,
            "aggregate_code_sha256": sha256_file(Path(__file__).resolve()),
            "apk_sha256": manifest.get("apk_sha256"),
            "installed_apk_sha256": manifest.get("installed_apk_sha256"),
            "execution_source_sha256": manifest.get("source_sha256"),
            "execution_source_identity_variants": list(execution_variants.values()),
            "classifier_identity": manifest.get("classifier_identity"),
        },
        "schedule_sha256": sha256_file(Path(manifest["schedule_path"])),
        "assigned_n": len(cases), "complete_n": sum(c["usable_completed_run"] for c in cases),
        "failed_or_cancelled_n": sum(c["session_state"] in {"failed", "cancelled"}
                                      or c["attempt_status"] in {"harness_failure", "harness_interrupted"} for c in cases),
        "metrics": metric_summary(cases), "approaches": by_approach,
        "owner_approved_demo_choice": demo_selection,
        "matched_completed_recordings": {"recording_ids": matched_ids,
                                          "recording_n": len(matched_ids),
                                          "actual_label_counts_by_recording": {label: sum(next(case for case in matched if case["recording_id"] == recording_id)["actual"] == label for recording_id in matched_ids) for label in LABELS},
                                          "source_counts_by_recording": {source: sum(next(case for case in matched if case["recording_id"] == recording_id).get("source_dataset") == source for recording_id in matched_ids)
                                                                          for source in sorted({case.get("source_dataset") for case in matched if case.get("source_dataset")})},
                                          "approaches": matched_by_approach},
        "limitations": [
            "Only the frozen 36 development first-pass assignments are included; no held-out records are accessed.",
            "All 36 assignments were attempted once with no retries: 27 completed and 9 ended in ADB, emulator/UI navigation, or app-state harness failures. Failures are execution coverage gaps, not classifier errors; no unattempted assignments remain.",
            "The classifier is the owner-approved interim PhayaThaiBERT adapter. The official evaluated model handoff/manifest is still not packaged, and this model has not been evaluated on final-test data; this result is not formal context-comparison or model-selection evidence.",
            "Classification metrics use only assignments with both terminal states complete, no error or harness timeout, and exact expected source and processed sample counts; all assigned cases remain in the coverage denominator.",
            "Conversation outcomes use any valid Scam prediction on a usable completed run; Not Scam requires a usable completed run with a valid prediction.",
            "The matched-completed comparison includes only recording IDs with usable completed runs for all three approaches; its denominators are shown separately.",
            "True Scam event timing is reported for actual Scam cases with a Scam prediction; false-warning event timing is reported for actual Not Scam cases with a Scam prediction. These use host-monotonic classification-completion events relative to host session creation, not client receipt or exact banner/render latency. They exclude nondetections and report n and sample SD.",
            "System banner visibility is not assessed by the harness; screenshots/UI hierarchy document app warning rendering for later visual review.",
            "Host CPU/RSS/MPS values come only from host resource_sample events. STT processing duration comes from stt_completed.resources.processing_seconds; classifier duration pairs classification_started/completed by request ID using host monotonic elapsed time. Android process PSS and cumulative CPU-time maxima use native_resource_sample client observations where present; CPU time is not CPU utilization.",
            "Queue high-water is a derived sample-range backlog (accepted end sample minus latest completed STT end sample divided by sample rate), and is reported only when accepted audio ranges are valid and contiguous. It is not a native queue measurement.",
            "Notification posting uses the first native notification_posted client observation's client_elapsed_ms and audio_position_ms. These are separate playback elapsed/audio-position values; neither is banner visibility or render latency. Missing values stay null.",
            "Human audio/script fidelity is unverified; the owner declined human verification. The approved accumulated choice is for bounded demo use only; formal integration freeze and final-system claims remain unauthorized.",
        ],
        "cases": cases,
    }


def render_markdown(summary: dict) -> str:
    lines = ["# Development context screen (provisional)", "",
             "This is a first-pass, development-only screening result. Recording fidelity is unverified; the owner declined human verification. The owner selected an approach for bounded demo use; formal integration freeze and final system evaluation are separate gates.", "",
             f"- Assigned: {summary['assigned_n']}; complete: {summary['complete_n']}; failed/cancelled: {summary['failed_or_cancelled_n']}",
             f"- Model: `{summary.get('model_kind')}` / `{summary.get('model_version')}`",
             f"- Configuration: `{summary.get('configuration_id')}`", "",
             "| Approach | Assigned | Complete | Failed/cancelled | Coverage (n/assigned) | Scam P | Scam R | Scam F1 | Macro F1 | Accuracy | False warnings | Missed Scam | Assigned source counts | Completed source counts | True Scam host event timing n / mean ± sample SD (s) | False-warning host event timing n / mean ± sample SD (s) |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|"]
    for name, result in summary["approaches"].items():
        m = result["metrics"]
        t = result["true_scam_detection_host_session_elapsed_s"]
        f = result["false_warning_host_session_elapsed_s"]
        fmt = lambda value: "NA" if value is None else f"{value:.3f}"
        lines.append(f"| {name} | {result['assigned_n']} | {result['complete_n']} | {result['failed_or_cancelled_n']} | {m['eligible_n']}/{m['assigned_n']} | {fmt(m['scam_precision'])} | {fmt(m['scam_recall'])} | {fmt(m['scam_f1'])} | {fmt(m['macro_f1'])} | {fmt(m['accuracy'])} | {result['false_warning_n']} | {result['missed_scam_n']} | {result['assigned_by_source']} | {result['completed_by_source']} | {t['n']} / {fmt(t['mean'])} ± {fmt(t['sample_sd'])} | {f['n']} / {fmt(f['mean'])} ± {fmt(f['sample_sd'])} |")
    identity = summary.get("run_artifact_identity", {})
    lines.extend(["", "## Run identities", "",
                  f"- APK SHA-256: `{identity.get('apk_sha256')}`; installed APK SHA-256: `{identity.get('installed_apk_sha256')}`",
                  f"- Artifact manifest SHA-256: `{identity.get('artifact_manifest_sha256')}`; attempt ledger SHA-256: `{identity.get('attempt_events_sha256')}`",
                  f"- Aggregate code SHA-256: `{identity.get('aggregate_code_sha256')}`; schedule SHA-256: `{summary.get('schedule_sha256')}`",
                  "- The APK hash is constant across the 36 starts. Four exact runtime source snapshots were recorded, differing only in `service/context_comparison_harness.py`; the other listed app source hashes are unchanged. This reflects harness revisions during recovery, so results retain per-run source identity and should be read with that caveat. Full file-by-file hashes and assignment mapping are in the JSON. This postprocessing code was not part of the recorded APK/source identity.",
                  "", "## Matched completed recordings", "",
                  "This secondary comparison restricts the same first-pass results to recording IDs with a usable completed run for all three approaches. It does not add runs; approach metrics and timing denominators are recalculated on that shared subset.", "",
                  f"Matched recording IDs: `{summary['matched_completed_recordings']['recording_ids']}`. Matched set composition by unique recording: `{summary['matched_completed_recordings'].get('actual_label_counts_by_recording', {})}` by true label and `{summary['matched_completed_recordings'].get('source_counts_by_recording', {})}` by source. All approaches share these IDs; failures outside this subset remain in the full assigned-run tables.", "",
                  "| Approach | Matched recordings | Completed / matched | Scam P | Scam R | Scam F1 | Macro F1 | Accuracy | False warnings | Missed Scam | Assigned source counts | Completed source counts | True Scam timing n / mean ± sample SD (s) | False-warning timing n / mean ± sample SD (s) |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|"])
    for name, result in summary["matched_completed_recordings"]["approaches"].items():
        m = result["metrics"]
        t = result["true_scam_detection_host_session_elapsed_s"]
        f = result["false_warning_host_session_elapsed_s"]
        fmt = lambda value: "NA" if value is None else f"{value:.3f}"
        lines.append(f"| {name} | {result['matched_recording_n']} | {result['completed_n']}/{result['assigned_n']} | {fmt(m['scam_precision'])} | {fmt(m['scam_recall'])} | {fmt(m['scam_f1'])} | {fmt(m['macro_f1'])} | {fmt(m['accuracy'])} | {result['false_warning_n']} | {result['missed_scam_n']} | {result['assigned_by_source']} | {result['completed_by_source']} | {t['n']} / {fmt(t['mean'])} ± {fmt(t['sample_sd'])} | {f['n']} / {fmt(f['mean'])} ± {fmt(f['sample_sd'])} |")
    lines.extend(["", "## Provisional screening signal", "",
                  "On the matched completed subset, accumulated has the highest Scam F1 and is tied with recent for the fewest observed false warnings (zero each). Treat this only as a provisional screening signal: the shared subset contains 8 recordings (5 Scam, 3 Not Scam), all first-pass comparisons are one run per recording and approach, and recording/script fidelity was not human-verified. Failures exclude all valid Supplemental Not Scam examples in the accumulated arm, so its zero observed false warnings are especially weak evidence. This result alone does not establish a formal integration freeze.",
                  ""])
    choice = summary.get("owner_approved_demo_choice")
    if choice:
        lines.extend(["", "## Owner-approved demo choice", "",
                      f"The owner approved **{choice['selected_approach']} context** for provisional demo use on {choice['approval_date']}, retaining `{choice['retain']}` within a {choice['token_budget']}-token budget. Approval basis: {choice['basis']}. Source: `{choice['plan_reference']}`; immutable selection sidecar SHA-256: `{choice['selection_sidecar_sha256']}`.",
                      f"The choice is bound here to the recorded `{choice['model_provenance']['model_kind']}` model `{choice['model_provenance']['model_version']}` and configuration `{choice['model_provenance']['configuration_id']}`. Formal release approved: `{str(choice['formal_release_approved']).lower()}`; final-test access authorized: `{str(choice['final_test_access_authorized']).lower()}`. Demo selection does not complete current-model microphone/background acceptance, official packaging, or formal Plan 05 release.",
                      ""])
    lines.extend(["## Undefined metric flags", "",
                  "Undefined classification metrics are stored as numeric zero with `metric_defined: false` and a reason in the JSON. A zero with a true flag is an observed zero score.", ""])
    for name, result in summary["approaches"].items():
        reasons = result["metrics"].get("undefined_metric_reasons", {})
        if reasons:
            lines.append(f"- **{name}:** " + "; ".join(f"{metric}: {reason}" for metric, reason in reasons.items()))
        else:
            lines.append(f"- **{name}:** no undefined metrics.")
    failed_cases = [case for case in summary["cases"] if not case["usable_completed_run"]]
    lines.extend(["", "## Assigned run accounting", "",
                  "Every frozen assignment appears once in the JSON. Failed runs remain in coverage denominators and are excluded from classification metrics; early Scam events on failed runs are retained as execution evidence only.", "",
                  "| Assigned run | Approach | Recording | Status | Exclusion reasons | Harness error |",
                  "|---|---|---|---|---|---|"])
    for case in failed_cases:
        error = str(case.get("attempt_error") or "")
        lines.append(f"| {case['assigned_run_id']} | {case['approach']} | {case['recording_id']} | {case['attempt_status']} | {', '.join(case['completion_exclusion_reasons'])} | {error.replace('|', '/')} |")
    lines.extend(["", "## Per-approach confusion matrices", ""])
    for name, result in summary["approaches"].items():
        lines.append(f"### {name}")
        lines.append("")
        lines.append("Rows are actual labels; columns are predicted labels. Incomplete cases are unresolved and excluded from the matrix, with assigned denominator and coverage shown above.")
        lines.append("")
        matrix = result["metrics"]["confusion_matrix_actual_rows_predicted_columns"]
        lines.append("| Actual \\ Predicted | Scam | Not Scam |")
        lines.append("|---|---:|---:|")
        for actual in LABELS:
            lines.append(f"| {actual} | {matrix[actual]['Scam']} | {matrix[actual]['Not Scam']} |")
        lines.append("")
    lines.extend(["## Resource and timing notes", "",
                  "Per-assignment host CPU, RSS and MPS allocation; STT window and classifier request durations; derived queue high-water; native Android PSS and cumulative CPU-time observations; notification-posted client elapsed/audio position; pause observations; prediction events; and UI evidence references are retained in the machine-readable aggregate JSON alongside each session's original event log. Android CPU time is not utilization. Notification posting is not banner visibility or render latency. Detection timing summaries omit undetected cases and report `n`; sample SD is unavailable for fewer than two observations. No source audio or transcript text is copied into this report.", "",
                  "## Limitations", ""])
    lines.extend(f"- {item}" for item in summary["limitations"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation-dir", type=Path, required=True)
    parser.add_argument("--storage", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()
    result = aggregate(args.evaluation_dir, args.storage)
    args.json_output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    args.markdown_output.write_text(render_markdown(result), encoding="utf-8")


if __name__ == "__main__":
    main()
