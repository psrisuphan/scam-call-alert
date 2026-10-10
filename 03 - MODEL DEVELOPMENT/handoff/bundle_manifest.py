"""Create and verify checksummed manifests for immutable model bundles."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

SCHEMA_VERSION = 1
REQUIRED_IDENTITY = ("candidate", "checkpoint", "revision", "model_code_revision",
                     "tokenizer_revision", "preprocessing_config_sha256",
                     "label_mapping", "threshold", "dependencies", "license",
                     "runtime_requirements", "evaluation_identity", "bundle_id",
                     "weights_path", "preprocessing_config_path", "tokenizer_path",
                     "model_config_path", "model_directory", "input_component_path",
                     "input_component_sha256")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_file(root: Path, relative: str) -> Path:
    posix = PurePosixPath(relative)
    if posix.is_absolute() or ".." in posix.parts or not posix.parts:
        raise ValueError(f"Unsafe bundle path: {relative!r}")
    candidate = root.joinpath(*posix.parts)
    if candidate.is_symlink():
        raise ValueError(f"Symlinked bundle files are not allowed: {relative!r}")
    resolved_root, resolved = root.resolve(), candidate.resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError(f"Bundle path escapes root: {relative!r}")
    if not resolved.is_file():
        raise ValueError(f"Required bundle file is missing: {relative}")
    return resolved


class _CompletedEvaluationEvidence:
    """In-process proof object issued only after validating evaluation outputs."""
    def __init__(self, identity):
        self.identity = identity


def build_manifest(bundle_dir, identity, files, *, completed_evaluation=None):
    """Return a manifest from caller-supplied pinned provenance and required paths.

    ``identity`` is deliberately not inferred: source/evaluation/license values
    must come from their authoritative records. ``files`` lists bundle-relative
    files that must be present, including the original evaluated model files.
    """
    root = Path(bundle_dir)
    missing = [key for key in REQUIRED_IDENTITY if key not in identity]
    if missing:
        raise ValueError("Missing provenance fields: " + ", ".join(missing))
    if identity["threshold"] != 0.5:
        raise ValueError("Frozen Scam threshold must be 0.5")
    if identity["label_mapping"] != {"Not Scam": 0, "Scam": 1}:
        raise ValueError("Unexpected frozen label mapping")
    required_paths = ("weights_path", "preprocessing_config_path", "tokenizer_path",
                      "model_config_path", "input_component_path")
    if any(identity[key] not in files for key in required_paths):
        raise ValueError("Manifest file list must include weights, preprocessing config, tokenizer and model config")
    if Path(identity["weights_path"]).name != "model.safetensors":
        raise ValueError("Use the native pre-evaluation model.safetensors file without downstream conversion")
    if any(not isinstance(identity.get(key), str) or not identity[key].strip()
           for key in ("candidate", "checkpoint", "revision", "model_code_revision", "tokenizer_revision",
                       "bundle_id", "weights_path", "preprocessing_config_path", "tokenizer_path", "model_config_path",
                       "model_directory", "input_component_path")):
        raise ValueError("Bundle identity fields must be explicitly nonempty")
    component_sha = identity["input_component_sha256"]
    if not isinstance(component_sha, str) or len(component_sha) != 64 or any(c not in "0123456789abcdef" for c in component_sha):
        raise ValueError("input_component_sha256 must be a lowercase SHA-256 digest")
    if not isinstance(identity["dependencies"], dict) or not identity["dependencies"]:
        raise ValueError("Pinned runtime dependencies are required")
    if not isinstance(identity["runtime_requirements"], dict) or not identity["runtime_requirements"]:
        raise ValueError("Runtime requirements are required")
    if not identity["license"]:
        raise ValueError("Provide a license or explicit unresolved-license status")
    if not files or len(set(files)) != len(files):
        raise ValueError("Provide a nonempty unique file list")
    entries = []
    for relative in sorted(files):
        path = _safe_file(root, relative)
        entries.append({"path": PurePosixPath(relative).as_posix(), "sha256": sha256_file(path),
                        "size_bytes": path.stat().st_size})
    weights_hash = next(item["sha256"] for item in entries if item["path"] == identity["weights_path"])
    evaluation = identity["evaluation_identity"]
    if evaluation:
        if (not isinstance(completed_evaluation, _CompletedEvaluationEvidence)
                or completed_evaluation.identity != evaluation):
            raise ValueError("A ready bundle requires evaluation identity derived from completed evaluation records")
        if not isinstance(evaluation, dict) or evaluation.get("weights_sha256") != weights_hash:
            raise ValueError("Evaluation identity must bind the exact evaluated weights checksum")
        if not evaluation.get("artifact_id"):
            raise ValueError("Evaluation identity must identify its final evaluation artifact")
        for key in ("selected_config_sha256", "final_evaluation_report_sha256",
                    "evaluation_protocol_sha256", "metrics_sha256", "completion_marker_sha256",
                    "review_audit_sha256", "reviewed_errors_sha256", "native_artifact_manifest_sha256"):
            value = evaluation.get(key)
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(f"Evaluation identity must include a valid {key}")
    manifest = {"schema_version": SCHEMA_VERSION,
                "bundle_status": "pending_parity" if not identity["evaluation_identity"] else "ready_for_parity",
                "identity": identity, "files": entries}
    errors = validate_manifest(root, manifest)
    if errors:
        raise ValueError("Manifest validation failed: " + "; ".join(errors))
    return manifest


def write_manifest(bundle_dir, manifest, filename="artifact_manifest.json"):
    root = Path(bundle_dir).resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Bundle root does not exist: {root}")
    posix = PurePosixPath(filename)
    if posix.is_absolute() or ".." in posix.parts or not posix.parts:
        raise ValueError(f"Unsafe manifest path: {filename!r}")
    path = root.joinpath(*posix.parts)
    if path.parent.resolve() != root and root not in path.parent.resolve().parents:
        raise ValueError("Manifest path escapes bundle root")
    if path.is_symlink() or path.exists():
        raise FileExistsError(f"Refusing to replace an existing bundle manifest: {path}")
    errors = validate_manifest(root, manifest)
    if errors:
        raise ValueError("Refusing invalid manifest: " + "; ".join(errors))
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def validate_manifest(bundle_dir, manifest):
    """Validate required identities and detect missing, changed or unsafe files."""
    root = Path(bundle_dir)
    errors = []
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported schema_version")
    identity = manifest.get("identity")
    if not isinstance(identity, dict):
        errors.append("identity must be an object")
        identity = {}
    for key in REQUIRED_IDENTITY:
        if key not in identity:
            errors.append(f"missing identity.{key}")
    for key in ("candidate", "checkpoint", "revision", "model_code_revision", "tokenizer_revision",
                "bundle_id", "weights_path", "preprocessing_config_path", "tokenizer_path", "model_config_path",
                "model_directory", "input_component_path"):
        if not isinstance(identity.get(key), str) or not identity[key].strip():
            errors.append(f"identity.{key} must be a nonempty string")
    for key in ("dependencies", "runtime_requirements"):
        if not isinstance(identity.get(key), dict) or not identity[key]:
            errors.append(f"identity.{key} must be a nonempty object")
    if not isinstance(identity.get("license"), (str, dict)) or not identity["license"]:
        errors.append("identity.license must contain an explicit license record (use an explicit unknown status if unresolved)")
    digest = identity.get("preprocessing_config_sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        errors.append("identity.preprocessing_config_sha256 must be a lowercase SHA-256 digest")
    component_digest = identity.get("input_component_sha256")
    if not isinstance(component_digest, str) or len(component_digest) != 64 or any(c not in "0123456789abcdef" for c in component_digest):
        errors.append("identity.input_component_sha256 must be a lowercase SHA-256 digest")
    if identity.get("threshold") != 0.5:
        errors.append("threshold must be 0.5")
    if identity.get("label_mapping") != {"Not Scam": 0, "Scam": 1}:
        errors.append("label mapping mismatch")
    names = {entry.get("path") for entry in manifest.get("files", []) if isinstance(entry, dict)}
    for key in ("weights_path", "preprocessing_config_path", "tokenizer_path", "model_config_path", "input_component_path"):
        if identity.get(key) not in names:
            errors.append(f"identity.{key} is not listed in files")
    model_directory = identity.get("model_directory")
    if isinstance(model_directory, str):
        prefix = model_directory.rstrip("/") + "/"
        for key in ("weights_path", "tokenizer_path", "model_config_path"):
            if isinstance(identity.get(key), str) and not identity[key].startswith(prefix):
                errors.append(f"identity.{key} must reside under model_directory")
    if isinstance(identity.get("input_component_path"), str):
        try:
            component_path = _safe_file(root, identity["input_component_path"])
            if sha256_file(component_path) != component_digest:
                errors.append("shared input-preparation component checksum mismatch")
        except (ValueError, OSError) as exc:
            errors.append(f"cannot validate shared input-preparation component: {exc}")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        errors.append("files must be a nonempty list")
        files = []
    seen = set()
    for entry in files:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            errors.append("malformed file entry")
            continue
        relative = entry["path"]
        if relative in seen:
            errors.append(f"duplicate file entry: {relative}")
            continue
        seen.add(relative)
        try:
            path = _safe_file(root, relative)
            if entry.get("sha256") != sha256_file(path):
                errors.append(f"checksum mismatch: {relative}")
            if entry.get("size_bytes") != path.stat().st_size:
                errors.append(f"size mismatch: {relative}")
        except (ValueError, OSError) as exc:
            errors.append(str(exc))
    declared = {entry.get("path") for entry in files if isinstance(entry, dict) and isinstance(entry.get("path"), str)}
    if root.exists():
        for path in root.rglob("*"):
            if path.is_symlink():
                errors.append(f"symlink in bundle: {path.relative_to(root).as_posix()}")
                continue
            if not path.is_file() or path.relative_to(root).as_posix() == "artifact_manifest.json":
                continue
            relative = path.relative_to(root).as_posix()
            try:
                _safe_file(root, relative)
                if relative not in declared:
                    errors.append(f"unmanifested bundle file: {relative}")
            except (ValueError, OSError) as exc:
                errors.append(str(exc))
    file_hashes = {entry.get("path"): entry.get("sha256") for entry in files if isinstance(entry, dict)}
    weight_hash = file_hashes.get(identity.get("weights_path"))
    evaluation = identity.get("evaluation_identity")
    status = manifest.get("bundle_status")
    if status not in ("pending_parity", "ready_for_parity"):
        errors.append("bundle_status must be pending_parity or ready_for_parity")
    if status == "ready_for_parity":
        if (not isinstance(evaluation, dict) or not evaluation.get("artifact_id")
                or not evaluation.get("evaluation_id") or not evaluation.get("authorization_reference")):
            errors.append("ready_for_parity requires a final evaluation artifact identity")
        elif evaluation.get("weights_sha256") != weight_hash:
            errors.append("evaluated weight checksum does not match bundle weights")
        elif any(not isinstance(evaluation.get(key), str) or len(evaluation[key]) != 64
                 or any(c not in "0123456789abcdef" for c in evaluation[key])
                 for key in ("selected_config_sha256", "final_evaluation_report_sha256",
                             "evaluation_protocol_sha256", "metrics_sha256", "completion_marker_sha256",
                             "review_audit_sha256", "reviewed_errors_sha256", "native_artifact_manifest_sha256")):
            errors.append("evaluation identity must checksum the selected config and final report")
        if not evaluation.get("evaluation_id") or not evaluation.get("authorization_reference"):
            errors.append("evaluation identity must include evaluation and authorization references")
    elif evaluation not in ({}, None):
        errors.append("pending_parity must not claim a completed final evaluation identity")
    config_path = identity.get("preprocessing_config_path")
    if isinstance(config_path, str):
        try:
            config_file = _safe_file(root, config_path)
            if sha256_file(config_file) != digest:
                errors.append("preprocessing configuration checksum mismatch")
            config = json.loads(config_file.read_text(encoding="utf-8"))
            entry = config.get("models", {}).get(identity.get("candidate"), {})
            if entry.get("checkpoint") != identity.get("checkpoint") or entry.get("revision") != identity.get("revision"):
                errors.append("frozen input configuration checkpoint identity mismatch")
            if identity.get("tokenizer_revision") != identity.get("revision"):
                errors.append("tokenizer revision differs from model checkpoint revision")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"cannot validate preprocessing configuration: {exc}")
    model_config_path = identity.get("model_config_path")
    if isinstance(model_config_path, str):
        try:
            model_config = json.loads(_safe_file(root, model_config_path).read_text(encoding="utf-8"))
            if model_config.get("num_labels") not in (None, 2):
                errors.append("model config num_labels must be 2")
            if model_config.get("id2label") != {"0": "Not Scam", "1": "Scam"}:
                errors.append("model config id2label order mismatch")
            if model_config.get("label2id") != {"Not Scam": 0, "Scam": 1}:
                errors.append("model config label2id mismatch")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"cannot validate model configuration: {exc}")
    return errors


def manifest_identity(manifest):
    """SHA-256 of canonical identity+file entries, not the manifest file bytes.

    This stable model_version changes when artifact provenance or any declared
    file checksum changes, while remaining independent of JSON whitespace/key
    formatting and the pending/ready lifecycle status.
    """
    payload = {"identity": manifest.get("identity"), "files": manifest.get("files")}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
