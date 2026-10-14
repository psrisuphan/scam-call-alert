#!/usr/bin/env python3
"""Run the frozen 36-assignment development context screen through Android UI.

The default mode is read-only preflight. ``--execute`` is refused until an
owner-approved authorization file records the model, fidelity, runtime and
feasibility gates. Playback is always started through the visible Android app;
this tool never creates sessions or uploads audio through the service API.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
PROTOTYPE = HERE.parent
REPO = PROTOTYPE.parents[1]
APP_PACKAGE = "com.anonymous.scamcallalert"
APP_BUILD = PROTOTYPE / "android/app/build/outputs/apk/release/app-release.apk"
APP_SOURCE_FILES = [
    PROTOTYPE / "App.tsx",
    PROTOTYPE / "index.ts",
    HERE / "server.py",
    HERE / "core.py",
    HERE / "adapters.py",
    HERE / "prepare_context_schedule.py",
    HERE / "context_comparison_harness.py",
] + sorted(p for p in (PROTOTYPE / "ui").rglob("*") if p.is_file() and p.suffix in {".ts", ".tsx"}) \
  + sorted((PROTOTYPE / "modules/scam-monitor/android/src/main/java").rglob("*.kt"))
CLASSIFIER_SOURCE_FILES = [
    REPO / "03 - MODEL DEVELOPMENT/selection/selected_config.json",
    REPO / "03 - MODEL DEVELOPMENT/selection/selection_completion.json",
    REPO / "03 - MODEL DEVELOPMENT/input-preparation/preprocessing_config.json",
    REPO / "03 - MODEL DEVELOPMENT/final-evaluation/evaluation.py",
]
DEFAULT_MODEL_BUNDLE = Path.home() / "Library/Application Support/scam-call-alert/model-development/mac-compatibility-transfer/phaya-final-replacement-primary-epoch2-20261012T050936Z/final_model"
REQUIRED_RUNTIME_SETTINGS = {
    "stt_window_seconds", "stt_overlap_seconds", "update_interval_seconds",
    "recent_segment_count", "newest_text_boundary", "max_queued_audio_seconds",
    "request_timeout_seconds", "completion_timeout_seconds", "retry_limit",
    "delay_indicator_seconds", "resource_sampling_interval_seconds",
}
APPROACH_LABELS = {"latest": "Latest", "recent": "Recent", "accumulated": "Accumulated"}
RECORD_TAB = "บทสนทนาที่บันทึกไว้"
START_LABEL = "จำลองสายเข้า"
ACCEPT_LABEL = "ตอบรับ"
DECLINE_LABEL = "ปฏิเสธ"
RESET_LABEL = "เริ่ม Session ใหม่"
STOP_LABEL = "จบ / หยุด"
WARNING_TEXT = "ระวัง! สายนี้อาจเป็นมิจฉาชีพ"
SETTINGS_LABEL = "การตั้งค่า"


class HarnessError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def source_identity() -> dict:
    return {str(path.relative_to(REPO)): sha256_file(path) for path in APP_SOURCE_FILES}


def classifier_identity(bundle: Path, health: dict) -> dict:
    manifest_path = bundle / "artifact_manifest.json"
    if not manifest_path.is_file():
        raise HarnessError("Selected interim model bundle is missing its artifact manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    file_hashes = {}
    for name, expected in manifest.get("files", {}).items():
        path = bundle / name
        if not path.is_file() or sha256_file(path) != expected:
            raise HarnessError(f"Interim model bundle file failed manifest verification: {name}")
        file_hashes[name] = expected
    if manifest.get("files", {}).get("model.safetensors") != health.get("model_version"):
        raise HarnessError("Running service model weights do not match the selected bundle")
    return {
        "artifact_manifest_sha256": sha256_file(manifest_path),
        "bundle_files_sha256": file_hashes,
        "model_bundle_path": str(bundle),
        "model_bundle_run_id": manifest.get("run_id"),
        "selected_config_and_preprocessing_sha256": {
            str(path.relative_to(REPO)): sha256_file(path) for path in CLASSIFIER_SOURCE_FILES
        },
    }


def load_dependencies():
    sys.path.insert(0, str(HERE))
    import prepare_context_schedule
    import prepare_recordings
    return prepare_context_schedule, prepare_recordings


def validate_schedule(recordings: Path, schedule_path: Path) -> tuple[list[dict], dict]:
    schedule_module, recording_module = load_dependencies()
    manifest_path = recordings / "audio_manifest.csv"
    with manifest_path.open(encoding="utf-8", newline="") as stream:
        records = list(csv.DictReader(stream))
    recording_module.validate_provenance(recordings, records)
    assignments = schedule_module.schedule(records)
    saved = json.loads(schedule_path.read_text(encoding="utf-8"))
    manifest_hash = sha256_file(manifest_path)
    if saved.get("manifest_sha256") != manifest_hash:
        raise HarnessError("Saved first-pass schedule belongs to a different manifest")
    if saved.get("assignments") != assignments:
        raise HarnessError("Saved first-pass assignments differ from deterministic schedule")
    if len(assignments) != 36 or len({x["assigned_run_id"] for x in assignments}) != 36:
        raise HarnessError("Expected 36 unique first-pass assignments")
    if any(x["display_condition"] != "foreground" or x["repetition"] != 1 for x in assignments):
        raise HarnessError("First-pass schedule must be foreground, one run per approach/recording")
    return assignments, {
        "recording_count": len(records),
        "class_counts": {label: sum(r["label"] == label for r in records) for label in ("Scam", "Not Scam")},
        "fidelity_statuses": sorted({r["fidelity_status"] for r in records}),
        "manifest_sha256": manifest_hash,
        "schedule_sha256": sha256_file(schedule_path),
        "assignments_sha256": hashlib.sha256(json.dumps(assignments, sort_keys=True).encode()).hexdigest(),
        "recording_duration_seconds": sum(float(r["duration_seconds"]) for r in records),
        "audio_playback_seconds": 3 * sum(float(r["duration_seconds"]) for r in records),
    }


def read_health(url: str) -> dict:
    with urlopen(url, timeout=3) as response:
        value = json.load(response)
    if value.get("status") != "ready":
        raise HarnessError("Local analysis service is not ready")
    return value


def read_session_state(health_url: str, session_id: str) -> str | None:
    base = health_url.rsplit("/", 1)[0]
    with urlopen(f"{base}/sessions/{session_id}", timeout=3) as response:
        return json.load(response).get("state")


def installed_apk_sha256(adb_path: str, serial: str) -> str:
    paths = adb(adb_path, serial, "shell", "pm", "path", APP_PACKAGE).decode(errors="replace").splitlines()
    base = next((line.removeprefix("package:").strip() for line in paths
                 if line.startswith("package:") and line.rstrip().endswith("/base.apk")), None)
    if not base:
        raise HarnessError("Installed application base APK could not be located")
    return hashlib.sha256(adb(adb_path, serial, "exec-out", "cat", base, timeout=45)).hexdigest()


def check_authorization(path: Path, health: dict) -> dict:
    approval = json.loads(path.read_text(encoding="utf-8"))
    if approval.get("approval_status") != "owner_approved":
        raise HarnessError("Authorization file does not record owner approval")
    model_kind = approval.get("model_kind")
    if model_kind not in {"official", "interim"} or health.get("model_kind") != model_kind:
        raise HarnessError("Service model kind does not match the owner-approved development screen")
    provisional = approval.get("scope") == "provisional_development_screening"
    if model_kind == "interim" and not provisional:
        raise HarnessError("Interim model is permitted only for provisional development screening")
    for key in ("model_version", "configuration_id"):
        if not approval.get(key) or approval[key] != health.get(key):
            raise HarnessError(f"Owner approval does not match current service {key}")
    fidelity = approval.get("recording_fidelity_status")
    if fidelity not in {"human_verified", "pending_human_verification"}:
        raise HarnessError("Recording fidelity state is missing or invalid")
    if fidelity == "pending_human_verification" and (
        not provisional or approval.get("freeze_allowed") is not False
    ):
        raise HarnessError("Pending fidelity permits provisional screening only and blocks freeze")
    feasibility = approval.get("combined_feasibility", {})
    if (feasibility.get("approved") is not True
            or feasibility.get("approved_run_count") != 36
            or not feasibility.get("processing_and_setup_included")
            or float(feasibility.get("minimum_playback_minutes", 0)) < 40):
        raise HarnessError("Combined runtime/feasibility budget approval is missing")
    settings = approval.get("runtime_settings", {})
    missing = sorted(REQUIRED_RUNTIME_SETTINGS - set(settings))
    if missing:
        raise HarnessError("Owner-approved runtime settings missing: " + ", ".join(missing))
    if settings != health.get("configuration"):
        raise HarnessError("Live service configuration differs from owner-approved settings")
    return approval


def adb(adb_path: str, serial: str | None, *args: str, timeout: float = 15) -> bytes:
    command = [adb_path]
    if serial:
        command += ["-s", serial]
    command += list(args)
    try:
        return subprocess.run(command, check=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=timeout).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        detail = getattr(exc, "stderr", b"") or b""
        raise HarnessError(f"ADB command failed: {args[0]} {detail.decode(errors='replace')[:200]}") from exc


class AndroidUI:
    def __init__(self, adb_path: str, serial: str, evidence_dir: Path):
        self.adb_path, self.serial, self.evidence_dir = adb_path, serial, evidence_dir
        self.counter = 0

    def xml(self) -> ET.Element:
        self.counter += 1
        remote = f"/sdcard/context-harness-{self.counter}.xml"
        adb(self.adb_path, self.serial, "shell", "uiautomator", "dump", remote, timeout=25)
        raw = adb(self.adb_path, self.serial, "shell", "cat", remote)
        try:
            return ET.fromstring(raw.decode("utf-8", errors="replace"))
        except ET.ParseError as exc:
            raise HarnessError("Android UI hierarchy is not valid XML") from exc

    def nodes(self) -> tuple[ET.Element, dict[ET.Element, ET.Element]]:
        root = self.xml()
        parents = {child: parent for parent in root.iter() for child in parent}
        return root, parents

    @staticmethod
    def labels(node: ET.Element) -> str:
        return " ".join(node.attrib.get(k, "").strip() for k in ("text", "content-desc") if node.attrib.get(k, "").strip())

    @staticmethod
    def matches(node: ET.Element, *, exact: str | None, contains: str | None) -> bool:
        values = [node.attrib.get(k, "").strip() for k in ("text", "content-desc")]
        values = [value for value in values if value]
        return any((exact is not None and value == exact) or
                   (contains is not None and contains in value) for value in values)

    def text(self, *, exact: str | None = None, contains: str | None = None) -> bool:
        root, _ = self.nodes()
        for node in root.iter():
            if self.matches(node, exact=exact, contains=contains):
                return True
        return False

    def tap(self, *, exact: str | None = None, contains: str | None = None,
            timeout: float = 8) -> None:
        deadline = time.monotonic() + timeout
        last_swipe = 0.0
        while time.monotonic() < deadline:
            root, parents = self.nodes()
            for node in root.iter():
                if not self.matches(node, exact=exact, contains=contains):
                    continue
                target = node
                while target is not None and target.attrib.get("clickable") != "true":
                    target = parents.get(target)
                if target is None:
                    continue
                match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", target.attrib.get("bounds", ""))
                if not match:
                    continue
                x1, y1, x2, y2 = map(int, match.groups())
                if x2 - x1 < 32 or y2 - y1 < 32:
                    # The accessibility tree includes clipped off-screen
                    # recording rows; expose them through the scroll container.
                    continue
                match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", target.attrib.get("bounds", ""))
                point = ((int(match.group(1)) + int(match.group(3))) // 2,
                         (int(match.group(2)) + int(match.group(4))) // 2) if exact == START_LABEL else \
                    self.safe_tap_point(target, root, parents)
                if point is None:
                    continue
                adb(self.adb_path, self.serial, "shell", "input", "tap", str(point[0]), str(point[1]))
                return
            if time.monotonic() - last_swipe >= 1.5:
                # Scroll only within the bounds of the visible UI container.
                rect = self.scroll_rect(root)
                if rect is None:
                    time.sleep(0.3)
                    continue
                x1, y1, x2, y2 = rect
                x = (x1 + x2) // 2
                adb(self.adb_path, self.serial, "shell", "input", "swipe", str(x),
                    str(y2 - (y2-y1)//4), str(x), str(y1 + (y2-y1)//4), "350")
                last_swipe = time.monotonic()
            time.sleep(0.3)
        raise HarnessError(f"Android control not found/clickable: {exact or contains}")

    @staticmethod
    def safe_tap_point(target: ET.Element, root: ET.Element,
                       parents: dict[ET.Element, ET.Element]) -> tuple[int, int] | None:
        """Choose an unoccluded point inside a clickable control.

        React Native's floating call button overlaps the accessibility bounds of
        the last visible recording row. The Android hierarchy reports both
        controls as clickable; tapping the row center can therefore invoke the
        floating button. Candidate points are rejected whenever another
        clickable node covers them.
        """
        match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", target.attrib.get("bounds", ""))
        if not match:
            return None
        x1, y1, x2, y2 = map(int, match.groups())
        width, height = x2 - x1, y2 - y1
        margin_x = min(32, max(8, width // 8))
        margin_y = min(24, max(8, height // 8))
        candidates = [
            ((x1 + x2) // 2, (y1 + y2) // 2),
            (x1 + margin_x, (y1 + y2) // 2),
            (x2 - margin_x, (y1 + y2) // 2),
            (x1 + margin_x, y1 + margin_y),
            (x1 + margin_x, y2 - margin_y),
            (x2 - margin_x, y1 + margin_y),
            (x2 - margin_x, y2 - margin_y),
        ]

        related = {target}
        ancestor = parents.get(target)
        while ancestor is not None:
            related.add(ancestor)
            ancestor = parents.get(ancestor)
        for node in target.iter():
            related.add(node)

        occluders = []
        for node in root.iter():
            if node in related or node.attrib.get("clickable") != "true":
                continue
            rect = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
            if rect:
                occluders.append(tuple(map(int, rect.groups())))

        # Clip to a scroll viewport only when it is an ancestor of this
        # target. Controls such as the post-call Reset button can sit outside
        # the list's ScrollView and must remain tappable there.
        scroll_rect = None
        ancestor = parents.get(target)
        while ancestor is not None:
            if ancestor.attrib.get("scrollable") == "true":
                rect = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]",
                                    ancestor.attrib.get("bounds", ""))
                if rect:
                    scroll_rect = tuple(map(int, rect.groups()))
                    break
            ancestor = parents.get(ancestor)
        for x, y in candidates:
            if not (x1 <= x < x2 and y1 <= y < y2):
                continue
            if scroll_rect is not None:
                sx1, sy1, sx2, sy2 = scroll_rect
                if not (sx1 <= x < sx2 and sy1 <= y < sy2):
                    continue
            if any(left <= x < right and top <= y < bottom
                   for left, top, right, bottom in occluders):
                continue
            return x, y
        return None

    def checked(self, *, exact: str, attribute: str = "checked") -> bool:
        root, parents = self.nodes()
        for node in root.iter():
            if self.matches(node, exact=exact, contains=None):
                target = node
                while target is not None:
                    if target.attrib.get(attribute) == "true":
                        return True
                    target = parents.get(target)
                return False
        raise HarnessError(f"Android selection not found: {exact}")

    def checked_contains(self, *, fragment: str, attribute: str = "checked") -> bool:
        root, parents = self.nodes()
        for node in root.iter():
            if not self.matches(node, exact=None, contains=fragment):
                continue
            target = node
            while target is not None:
                if target.attrib.get(attribute) == "true":
                    return True
                target = parents.get(target)
            return False
        raise HarnessError(f"Android selection not found: {fragment}")

    def require_home_selection(self, recording_id: str) -> None:
        # The recording list can scroll the title and mode tabs off-screen.
        # Identify Home from its persistent controls and reject incoming-call
        # controls before accepting anything. The recorded tab is verified
        # selected before opening Settings in run_assignment.
        if not self.home_controls_visible():
            raise HarnessError("Recording row tap left the home screen; refusing to accept a call")
        try:
            selected = self.checked_contains(fragment=recording_id)
        except HarnessError:
            selected = False
        if not selected:
            raise HarnessError(f"Scheduled recording was not selected: {recording_id}")
        if not self.clickable(exact=START_LABEL):
            raise HarnessError("Call control is unavailable on the home screen")

    def home_controls_visible(self) -> bool:
        return (self.clickable(exact=START_LABEL)
                and self.clickable(exact=SETTINGS_LABEL)
                and not self.clickable(exact=ACCEPT_LABEL)
                and not self.clickable(exact=DECLINE_LABEL)
                and not self.clickable(exact=STOP_LABEL))

    def clickable(self, *, exact: str) -> bool:
        root, parents = self.nodes()
        for node in root.iter():
            if not self.matches(node, exact=exact, contains=None):
                continue
            target = node
            while target is not None:
                bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", target.attrib.get("bounds", ""))
                if target.attrib.get("clickable") == "true" and bounds:
                    x1, y1, x2, y2 = map(int, bounds.groups())
                    return x2 - x1 >= 32 and y2 - y1 >= 32
                target = parents.get(target)
        return False

    @staticmethod
    def scroll_rect(root: ET.Element) -> tuple[int, int, int, int] | None:
        candidates = []
        for node in root.iter():
            if node.attrib.get("scrollable") != "true":
                continue
            match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
            if match:
                rect = tuple(map(int, match.groups()))
                candidates.append((max(0, rect[2] - rect[0]) * max(0, rect[3] - rect[1]), rect))
        return max(candidates, default=(0, None), key=lambda item: item[0])[1]

    def scroll_to_top(self) -> None:
        for _ in range(4):
            root, _ = self.nodes()
            rect = self.scroll_rect(root)
            if rect is None:
                return
            x1, y1, x2, y2 = rect
            x = (x1 + x2) // 2
            adb(self.adb_path, self.serial, "shell", "input", "swipe", str(x),
                str(y1 + (y2-y1)//4), str(x), str(y2 - (y2-y1)//4), "350")
            time.sleep(0.15)

    def save_evidence(self, folder: Path, stem: str) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        xml = ET.tostring(self.xml(), encoding="utf-8", xml_declaration=True)
        (folder / f"{stem}.xml").write_bytes(xml)
        image = adb(self.adb_path, self.serial, "exec-out", "screencap", "-p")
        (folder / f"{stem}.png").write_bytes(image)


def run_directories(storage: Path) -> set[str]:
    root = storage / "runs"
    return {p.name for p in root.iterdir() if p.is_dir()} if root.exists() else set()


def snapshot_for(storage: Path, session_id: str) -> dict | None:
    path = storage / "runs" / session_id / "snapshot.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def validate_continuation(path: Path, evaluation_dir: Path, previous: dict,
                          current: dict, assignments: list[dict], ledger: Path) -> dict:
    """Verify an append-only record for a harness-only continuation change."""
    if not path.is_file():
        raise HarnessError("Source identity changed; a continuation manifest is required")
    continuation = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version": 1,
        "evaluation_dir": str(evaluation_dir),
        "previous_artifact_manifest_sha256": sha256_file(evaluation_dir / "artifact_manifest.json"),
        "previous_source_sha256": previous.get("source_sha256"),
        "continuation_source_sha256": current.get("source_sha256"),
        "schedule": assignments,
        "model_version": current.get("model_version"),
        "configuration_id": current.get("configuration_id"),
        "classifier_identity": current.get("classifier_identity"),
        "apk_sha256": current.get("apk_sha256"),
        "installed_apk_sha256": current.get("installed_apk_sha256"),
    }
    for key, expected in required.items():
        if continuation.get(key) != expected:
            raise HarnessError(f"Continuation manifest mismatch: {key}")
    old_sources = continuation["previous_source_sha256"]
    new_sources = continuation["continuation_source_sha256"]
    changed = {key for key in old_sources.keys() | new_sources.keys()
               if old_sources.get(key) != new_sources.get(key)}
    harness_key = "04 - APPLICATION DEVELOPMENT/prototype/service/context_comparison_harness.py"
    if changed != {harness_key}:
        raise HarnessError("Continuation may change only the reviewed harness source")
    if continuation.get("failed_assignments_preserved") is not True:
        raise HarnessError("Continuation must preserve all prior assigned failures")
    if continuation.get("no_failed_assignment_retries") is not True:
        raise HarnessError("Continuation cannot replay a failed assignment")
    if not ledger.is_file():
        raise HarnessError("Continuation requires the existing append-only attempt ledger")
    accounted = set()
    for line in ledger.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("event") == "attempt_finished":
            accounted.add(event.get("assigned_run_id"))
    expected_unattempted = [row["assigned_run_id"] for row in assignments
                            if row["assigned_run_id"] not in accounted]
    if continuation.get("unattempted_assignments") != expected_unattempted:
        raise HarnessError("Continuation assignment set differs from the append-only ledger")
    if continuation.get("review_status") != "root_reviewed" or continuation.get("launch_authorized") is not True:
        raise HarnessError("Continuation requires root review before execution")
    return continuation


def assert_app_foreground(adb_path: str, serial: str) -> None:
    top = adb(adb_path, serial, "shell", "dumpsys", "activity", "activities").decode(errors="replace")
    resumed = re.search(
        r"^\s*(?:mResumedActivity|topResumedActivity|ResumedActivity)\s*:?=?[^\n]*?\bu\d+\s+([\w.]+)/(?:[\w.$]+)",
        top, re.MULTILINE)
    if not resumed or resumed.group(1) != APP_PACKAGE:
        raise HarnessError("Scam Call Alert must remain foregrounded for this assigned run")


def run_assignment(assignment: dict, recordings: Path, storage: Path, evidence_root: Path,
                   ledger: Path, ui: AndroidUI, adb_path: str, serial: str,
                   completion_timeout: int, source_hashes: dict,
                   classifier_hashes: dict) -> dict:
    assigned_id = assignment["assigned_run_id"]
    attempt_id = uuid.uuid4().hex
    evidence = evidence_root / assigned_id / attempt_id
    before = run_directories(storage)
    started = time.time()
    session_id = None
    accepted = False
    harness_timeout = False
    append_jsonl(ledger, {"event": "attempt_started", "assigned_run_id": assigned_id,
                          "attempt_id": attempt_id, "recording_id": assignment["recording_id"],
                          "approach": assignment["approach"], "started_wall_time": started,
                          "apk_sha256": sha256_file(APP_BUILD), "source_sha256": source_hashes,
                          "classifier_identity": classifier_hashes,
                          "foreground_check_interval_seconds": 2,
                          "foreground_observer": "adb dumpsys activity activities"})
    try:
        assert_app_foreground(adb_path, serial)
        if source_identity() != source_hashes:
            raise HarnessError("Application/service source changed after preflight")
        if not ui.home_controls_visible():
            if ui.text(exact=RESET_LABEL):
                ui.tap(exact=RESET_LABEL)
            if not ui.home_controls_visible():
                raise HarnessError("App must be on the home screen before each assigned run")
        # The home page itself is scrollable; previous attempts may leave its
        # mode tabs above the viewport even while persistent home controls remain visible.
        ui.scroll_to_top()
        ui.tap(exact=RECORD_TAB)
        if not ui.checked(exact=RECORD_TAB, attribute="selected"):
            raise HarnessError("Recorded mode tab did not become selected")
        ui.tap(exact=SETTINGS_LABEL)
        ui.tap(exact=APPROACH_LABELS[assignment["approach"]])
        if not ui.checked(exact=APPROACH_LABELS[assignment["approach"]]):
            raise HarnessError("Requested context approach did not become selected")
        # Staged playback deliberately changes lifecycle and playback timing;
        # this screen is the normal foreground condition for all assignments.
        if ui.checked(exact="Background check"):
            ui.tap(exact="Background check")
        if ui.checked(exact="Background check"):
            raise HarnessError("Background check must be off for foreground screening")
        ui.tap(exact="ปิด")
        ui.scroll_to_top()
        ui.tap(contains=assignment["recording_id"])
        ui.require_home_selection(assignment["recording_id"])
        ui.save_evidence(evidence, "prestart")
        ui.tap(exact=START_LABEL)
        if not ui.clickable(exact=ACCEPT_LABEL) or not ui.clickable(exact=DECLINE_LABEL):
            raise HarnessError("Incoming call screen did not expose both accept and decline controls")
        ui.tap(exact=ACCEPT_LABEL)
        accepted = True

        session_id = None
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            created = run_directories(storage) - before
            if len(created) > 1:
                raise HarnessError("More than one host session appeared for a single assigned run")
            if created:
                candidate = next(iter(created))
                snapshot = snapshot_for(storage, candidate)
                if snapshot:
                    session_id = candidate
                    break
            time.sleep(0.25)
        if not session_id:
            raise HarnessError("Android did not create a persisted recorded session")
        append_jsonl(ledger, {"event": "session_bound", "assigned_run_id": assigned_id,
                              "attempt_id": attempt_id, "session_id": session_id})
        snapshot = snapshot_for(storage, session_id)
        event_path = storage / "runs" / session_id / "events.jsonl"
        session_event = None
        if event_path.is_file():
            with event_path.open(encoding="utf-8") as stream:
                for line in stream:
                    event = json.loads(line)
                    if event.get("kind") == "session_created":
                        session_event = event
                        break
        if (snapshot.get("mode") != "recorded" or snapshot.get("recording_id") != assignment["recording_id"]
                or not session_event or session_event.get("approach") != assignment["approach"]
                or session_event.get("recording_id") != assignment["recording_id"]):
            raise HarnessError("Started Android session does not match its frozen schedule assignment")
        with (recordings / "audio_manifest.csv").open(encoding="utf-8", newline="") as stream:
            durations = {r["recording_id"]: float(r["duration_seconds"]) for r in csv.DictReader(stream)}
        expected_audio_s = durations[assignment["recording_id"]]
        end_by = time.monotonic() + expected_audio_s + completion_timeout
        warning_captured = False
        next_foreground_check = time.monotonic()
        while time.monotonic() < end_by:
            if time.monotonic() >= next_foreground_check:
                assert_app_foreground(adb_path, serial)
                next_foreground_check = time.monotonic() + 2.0
            snapshot = snapshot_for(storage, session_id)
            if not snapshot:
                time.sleep(0.5); continue
            if snapshot.get("warning") and not warning_captured:
                warning_captured = True
                ui.save_evidence(evidence, "first_warning")
                ui_warning_visible = ui.text(contains=WARNING_TEXT)
                append_jsonl(ledger, {
                    "event": "warning_evidence", "assigned_run_id": assigned_id,
                    "attempt_id": attempt_id, "session_id": session_id,
                    "warning_state_in_snapshot": True,
                    "warning_text_in_foreground_ui_hierarchy": ui_warning_visible,
                    "system_banner_visibility": "not_assessed",
                    "evidence_stem": "first_warning",
                    "observer": "context_comparison_harness_uiautomator_and_screencap",
                    "captured_wall_time": time.time(),
                })
            state = snapshot.get("state")
            if state in {"complete", "failed", "cancelled"}:
                break
            time.sleep(0.5)
        else:
            harness_timeout = True
            ui.tap(exact=STOP_LABEL, timeout=3)
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                snapshot = snapshot_for(storage, session_id) or {}
                if snapshot.get("state") in {"complete", "failed", "cancelled"}:
                    break
                time.sleep(0.25)
        if not snapshot:
            snapshot = snapshot_for(storage, session_id) or {}
        ui.save_evidence(evidence, "terminal")
        assert_app_foreground(adb_path, serial)
        outcome = {
            "event": "attempt_finished", "assigned_run_id": assigned_id,
            "attempt_id": attempt_id, "session_id": session_id,
            "state": snapshot.get("state"), "error": snapshot.get("error"),
            "audio_samples": snapshot.get("audio_samples"),
            "processed_samples": snapshot.get("processed_samples"),
            "transcript_characters": len(snapshot.get("transcript") or ""),
            "prediction_label": (snapshot.get("prediction") or {}).get("label"),
            "warning": bool(snapshot.get("warning")),
            "system_banner_visibility": "not_assessed",
            "harness_timeout": harness_timeout,
            "evidence_dir": str(evidence), "finished_wall_time": time.time(),
        }
        append_jsonl(ledger, outcome)
        return outcome
    except Exception as exc:
        cleanup = {"stop_requested": False, "terminal_state_after_cleanup": None,
                   "cleanup_confirmed": False, "decline_requested": False}
        if accepted:
            try:
                if ui.text(exact=STOP_LABEL):
                    ui.tap(exact=STOP_LABEL, timeout=3)
                    cleanup["stop_requested"] = True
                    deadline = time.monotonic() + 12
                    while session_id and time.monotonic() < deadline:
                        current = snapshot_for(storage, session_id) or {}
                        state = current.get("state")
                        if state in {"complete", "failed", "cancelled"}:
                            cleanup["terminal_state_after_cleanup"] = state
                            cleanup["cleanup_confirmed"] = True
                            break
                        time.sleep(0.25)
            except Exception as cleanup_exc:
                cleanup["cleanup_error"] = str(cleanup_exc)
        elif not accepted:
            try:
                # If a row tap hit the floating call button, leave the pending
                # incoming screen without accepting or creating a session.
                if ui.clickable(exact=ACCEPT_LABEL) and ui.clickable(exact=DECLINE_LABEL):
                    ui.tap(exact=DECLINE_LABEL, timeout=3)
                    cleanup["decline_requested"] = True
                    cleanup["cleanup_confirmed"] = ui.text(exact="Scam Call Alert")
            except Exception as cleanup_exc:
                cleanup["cleanup_error"] = str(cleanup_exc)
        try:
            ui.save_evidence(evidence, "failure")
        except Exception:
            evidence.mkdir(parents=True, exist_ok=True)
        result = {"event": "attempt_finished", "assigned_run_id": assigned_id,
                  "attempt_id": attempt_id, "status": "harness_failure",
                  "session_id": session_id,
                  "error": str(exc), **cleanup,
                  "evidence_dir": str(evidence), "finished_wall_time": time.time()}
        append_jsonl(ledger, result)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recordings", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--storage", type=Path, required=True,
                        help="same persistent storage passed to service --storage")
    parser.add_argument("--model-bundle", type=Path, default=Path(os.environ.get("FINAL_MODEL", DEFAULT_MODEL_BUNDLE)),
                        help="verified external model bundle loaded by the local service")
    parser.add_argument("--health-url", default="http://127.0.0.1:8765/health")
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="emulator-5554")
    parser.add_argument("--evaluation-dir", type=Path,
                        help="external persistent directory for append-only harness evidence")
    parser.add_argument("--authorization", type=Path,
                        help="owner-approved JSON gate record; required with --execute")
    parser.add_argument("--execute", action="store_true",
                        help="launch scheduled sessions through Android UI (never API-injects audio)")
    parser.add_argument("--resume", action="store_true",
                        help="continue an existing evaluation without retrying any assigned run")
    parser.add_argument("--continuation-manifest", type=Path,
                        help="owner-reviewed source correction record for a frozen evaluation continuation")
    args = parser.parse_args()

    assignments, manifest_info = validate_schedule(args.recordings, args.schedule)
    health = read_health(args.health_url)
    summary = {"schedule": manifest_info, "run_count": len(assignments),
               "model_kind": health.get("model_kind"), "model_version": health.get("model_version"),
               "configuration_id": health.get("configuration_id"),
               "configuration": health.get("configuration"),
               "source_sha256": source_identity(),
               "classifier_identity": classifier_identity(args.model_bundle, health),
               "apk_sha256": sha256_file(APP_BUILD) if APP_BUILD.is_file() else None,
               "execution": "not launched"}
    if not args.execute:
        summary["readiness_gates"] = [
            "matching owner authorization for this provisional development screen",
            "all assigned runs remain provisional while recording fidelity is pending",
            "installed APK identity matches the release artifact and app is foregrounded",
        ]
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    if not args.authorization or not args.evaluation_dir:
        raise HarnessError("--execute requires --authorization and --evaluation-dir")
    approval = check_authorization(args.authorization, health)
    expected_fidelity = approval["recording_fidelity_status"]
    actual_fidelity = manifest_info["fidelity_statuses"]
    allowed_fidelity = {
        "human_verified": ["verified"],
        "pending_human_verification": ["pending_human_verification"],
    }
    if actual_fidelity != allowed_fidelity.get(expected_fidelity):
        raise HarnessError("Recording manifest fidelity status changed from owner-approved state")
    if summary["apk_sha256"] is None:
        raise HarnessError("Release APK is missing; build and install the approved application first")
    devices = adb(args.adb, None, "devices", "-l").decode(errors="replace")
    if args.serial not in devices or "device" not in next((x for x in devices.splitlines() if x.startswith(args.serial)), ""):
        raise HarnessError("Requested Android emulator is not connected")
    assert_app_foreground(args.adb, args.serial)
    package_details = adb(args.adb, args.serial, "shell", "dumpsys", "package", APP_PACKAGE).decode(errors="replace")
    permission_granted = re.search(r"android\.permission\.POST_NOTIFICATIONS:\s*granted=true", package_details)
    if not permission_granted:
        raise HarnessError("Notification permission must be resolved before the assigned screen")
    installed_hash = installed_apk_sha256(args.adb, args.serial)
    summary["installed_apk_sha256"] = installed_hash
    if installed_hash != summary["apk_sha256"]:
        raise HarnessError("Installed APK does not match the release APK whose identity would be recorded")
    artifact_manifest = args.evaluation_dir / "artifact_manifest.json"
    ledger_path = args.evaluation_dir / "attempt_events.jsonl"
    if args.resume:
        if not args.evaluation_dir.is_dir() or not artifact_manifest.is_file():
            raise HarnessError("--resume requires an existing evaluation with artifact_manifest.json")
        previous = json.loads(artifact_manifest.read_text(encoding="utf-8"))
        for key in ("schedule", "model_version", "configuration_id",
                    "classifier_identity", "apk_sha256", "installed_apk_sha256"):
            if previous.get(key) != (assignments if key == "schedule" else summary.get(key)):
                raise HarnessError(f"Cannot resume because {key} changed")
        if previous.get("source_sha256") != summary.get("source_sha256"):
            if not args.continuation_manifest:
                raise HarnessError("Source identity changed; pass a reviewed continuation manifest")
            validate_continuation(args.continuation_manifest, args.evaluation_dir,
                                  previous, summary, assignments, ledger_path)
    else:
        if args.evaluation_dir.exists():
            raise HarnessError("Evaluation directory already exists; use --resume to continue without retries")
        args.evaluation_dir.mkdir(parents=True)
        evidence_root = args.evaluation_dir / "ui-evidence"
        evidence_root.mkdir()
        artifact_manifest.write_text(json.dumps({
            **summary, "approval": approval, "schedule_path": str(args.schedule),
            "recordings_path": str(args.recordings), "storage_path": str(args.storage),
            "schedule": assignments,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    evidence_root = args.evaluation_dir / "ui-evidence"
    ledger = ledger_path
    ui = AndroidUI(args.adb, args.serial, evidence_root)
    print(json.dumps({"evaluation_dir": str(args.evaluation_dir), "run_count": len(assignments),
                      "approved_playback_lower_bound_minutes": approval["combined_feasibility"]["minimum_playback_minutes"],
                      "approval_basis": approval["combined_feasibility"]["basis"]}, ensure_ascii=False))
    accounted = set()
    attempts_by_run = {}
    if args.resume and ledger.is_file():
        for line in ledger.read_text(encoding="utf-8").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise HarnessError("Attempt ledger has a partial/corrupt final line; preserve it before resuming") from exc
            run_id = event.get("assigned_run_id")
            if event.get("event") == "attempt_started":
                attempts_by_run.setdefault(run_id, {"attempt_id": event.get("attempt_id"), "session_id": None})
            elif event.get("event") == "session_bound":
                attempts_by_run.setdefault(run_id, {"attempt_id": event.get("attempt_id"), "session_id": None})["session_id"] = event.get("session_id")
            elif event.get("event") == "attempt_finished":
                accounted.add(run_id)
                attempts_by_run.pop(run_id, None)
        # Never replay an interrupted assigned run. Stop any still-visible
        # session, preserve the partial session artifacts, and mark that one
        # first attempt as failed before proceeding to the next assignment.
        for run_id, partial in attempts_by_run.items():
            cleanup = {"stop_requested": False, "terminal_state_after_cleanup": None,
                       "cleanup_confirmed": False}
            if ui.text(exact=STOP_LABEL):
                ui.tap(exact=STOP_LABEL, timeout=3)
                cleanup["stop_requested"] = True
            sid = partial.get("session_id")
            if sid:
                deadline = time.monotonic() + 12
                while time.monotonic() < deadline:
                    current = snapshot_for(args.storage, sid) or {}
                    state = current.get("state")
                    if state in {"complete", "failed", "cancelled"}:
                        cleanup["terminal_state_after_cleanup"] = state
                        cleanup["cleanup_confirmed"] = True
                        break
                    time.sleep(0.25)
                if not cleanup["cleanup_confirmed"]:
                    try:
                        current_state = read_session_state(args.health_url, sid)
                        cleanup["terminal_state_after_cleanup"] = current_state
                        cleanup["cleanup_confirmed"] = current_state in {"complete", "failed", "cancelled"}
                    except Exception as check_exc:
                        raise HarnessError(f"Cannot prove interrupted session {sid} is inactive; refusing to continue") from check_exc
            else:
                cleanup["cleanup_confirmed"] = ui.home_controls_visible()
            if not cleanup["cleanup_confirmed"]:
                raise HarnessError(f"Cannot prove interrupted assignment {run_id} is inactive; refusing to continue")
            append_jsonl(ledger, {"event": "attempt_finished", "assigned_run_id": run_id,
                                  "attempt_id": partial.get("attempt_id"), "session_id": sid,
                                  "status": "harness_interrupted", **cleanup,
                                  "finished_wall_time": time.time()})
            accounted.add(run_id)
    for assignment in assignments:
        if assignment["assigned_run_id"] in accounted:
            continue
        print(json.dumps({"next_assigned_run_id": assignment["assigned_run_id"],
                          "recording_id": assignment["recording_id"], "approach": assignment["approach"]}, ensure_ascii=False))
        result = run_assignment(assignment, args.recordings, args.storage, evidence_root,
                                ledger, ui, args.adb, args.serial,
                                int(approval["runtime_settings"]["completion_timeout_seconds"]),
                                summary["source_sha256"], summary["classifier_identity"])
        print(json.dumps({k: result.get(k) for k in (
            "assigned_run_id", "attempt_id", "session_id", "state", "error",
            "audio_samples", "processed_samples", "transcript_characters", "prediction_label",
            "warning", "system_banner_visibility")}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (HarnessError, OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"context harness: {exc}", file=sys.stderr)
        raise SystemExit(2)
