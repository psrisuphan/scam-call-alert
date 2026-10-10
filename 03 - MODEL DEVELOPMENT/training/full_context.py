"""WangchanBERTa-only full-context windows and conversation-level pooling."""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

WINDOW_CONTENT_TOKENS = 508
WINDOW_STEP = 381
MAX_TOTAL_TOKENS = 510


def make_windows(token_ids, *, window_size=WINDOW_CONTENT_TOKENS, step=WINDOW_STEP):
    """Return ordered overlapping content-token slices covering the complete input."""
    count = len(token_ids)
    if count == 0:
        return [[]]
    starts = [0]
    while starts[-1] + window_size < count:
        starts.append(starts[-1] + step)
    windows = [token_ids[start:min(start + window_size, count)] for start in starts]
    if any(not window for window in windows) or sum(map(len, windows)) < count:
        raise AssertionError("Window policy failed to cover content tokens")
    if windows[0] != token_ids[:len(windows[0])] or windows[-1][-1] != token_ids[-1]:
        raise AssertionError("Window policy changed token order or omitted final token")
    return windows


def add_special_tokens(tokenizer, content_ids):
    result = tokenizer.build_inputs_with_special_tokens(content_ids)
    if len(result) > MAX_TOTAL_TOKENS:
        raise ValueError("Window exceeds the approved 510 total-token limit")
    return {"input_ids": result, "attention_mask": [1] * len(result)}


def verify_prepared_manifest(input_config, input_module, folder):
    """Validate Plan 02 export identities without changing its frozen verifier module."""
    import importlib.metadata
    import json

    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    config_digest = hashlib.sha256((json.dumps(input_config, ensure_ascii=False, indent=2) + "\n").encode()).hexdigest()
    input_component = Path(input_module.__file__).resolve()
    export_script = Path(input_module.DEFAULT_CONFIG).resolve().parent / "scripts/8.export_inputs.py"
    expected = {
        "configuration_sha256": config_digest,
        "component_sha256": hashlib.sha256(input_component.read_bytes()).hexdigest(),
        "training_csv_sha256": input_config["training_csv_sha256"],
        "assignments_sha256": input_config["assignments_sha256"],
        "export_script_sha256": hashlib.sha256(export_script.read_bytes()).hexdigest(),
    }
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise ValueError("Stale prepared manifest; regenerate separately")
    if manifest.get("models") != input_config["models"] or manifest.get("dependencies") != input_config["dependencies"]:
        raise ValueError("Prepared tokenizer/dependency configuration differs")
    for package, version in input_config["dependencies"].items():
        if importlib.metadata.version(package) != version:
            raise ValueError(f"Use {package}=={version}")
    return manifest


def pool_logits(window_logits, owners, conversation_count, method):
    """Differentiable class-wise pooling; every conversation receives one 2-logit row."""
    if method not in ("max", "mean"):
        raise ValueError("pooling method must be max or mean")
    if window_logits.ndim != 2 or window_logits.shape[1] != 2:
        raise ValueError("Expected two raw logits per window")
    if len(owners) != len(window_logits) or conversation_count < 1:
        raise ValueError("Window ownership does not match logits")
    pooled = []
    for index in range(conversation_count):
        indices = [window_index for window_index, owner in enumerate(owners) if owner == index]
        if not indices:
            raise ValueError("Every conversation must have at least one window")
        selected = window_logits[indices]
        pooled.append(selected.max(dim=0).values if method == "max" else selected.mean(dim=0))
    return __import__("torch").stack(pooled)


def load_full_text_inputs(records, *, model, representation, marker_condition, fold,
                          input_config, input_dir, tokenizer, input_module, validation=False):
    """Load full untruncated text only from Plan 02 training_text.csv and verify provenance."""
    if model != "wangchanberta" or representation != "whole_conversation":
        raise ValueError("Full-context windowing is currently approved only for WangchanBERTa whole conversations")
    if marker_condition not in ("role_marked", "role_free"):
        raise ValueError("Unexpected marker condition")
    model_config = input_config["models"][model]
    if (model_config.get("special_tokens_count") != 2
            or model_config.get("verified_config_limit", 0) < MAX_TOTAL_TOKENS
            or tokenizer.num_special_tokens_to_add() != 2
            or getattr(tokenizer, "_scam_checkpoint_identity", None)
                != (model_config["checkpoint"], model_config["revision"])):
        raise ValueError("Full-context windows require the approved Wangchan tokenizer, two special tokens, and 510-token capacity")
    folder = Path(input_dir)
    text_path = folder / "training_text.csv"
    # Match the prepared-export identity/dependency gate used by fixed-prefix inputs.
    # The extra training_text.csv hash check below binds the full-context export itself.
    manifest = verify_prepared_manifest(input_config, input_module, folder)
    text_digest = hashlib.sha256(text_path.read_bytes()).hexdigest()
    if manifest.get("files", {}).get("training_text.csv", {}).get("sha256") != text_digest:
        raise ValueError("training_text.csv does not match its Plan 02 manifest")
    if manifest.get("assignments_sha256") != input_config["assignments_sha256"]:
        raise ValueError("Prepared manifest uses different frozen assignments")
    with text_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    by_id = {row["sample_id"]: row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError("Duplicate sample_id in full training text")
    selected = []
    for record in records:
        sample_id = record["sample_id"]
        row = by_id.get(sample_id)
        if row is None:
            raise ValueError(f"Missing full training text for {sample_id}")
        row_fold = int(row["cv_fold"])
        fold_matches = row_fold == int(fold) if validation else row_fold != int(fold)
        if (row["source_dataset"] != record["source_dataset"]
                or row["label"] != record["label"] or not fold_matches):
            raise ValueError(f"Full-text source/label/fold mismatch for {sample_id}")
        text = input_module.checkpoint_prepare_text(row[f"whole_conversation.{marker_condition}"], model, input_config)
        prepared = tokenizer(text, add_special_tokens=False, padding=False,
                             truncation=False, verbose=False)["input_ids"]
        windows = [add_special_tokens(tokenizer, ids) for ids in make_windows(prepared)]
        if not windows or any(len(item["input_ids"]) > MAX_TOTAL_TOKENS for item in windows):
            raise ValueError("Invalid window set")
        selected.append({"sample_id": sample_id, "source_dataset": record["source_dataset"],
            "label": int(record["label"] == "Scam"), "windows": windows,
            "content_token_count": len(prepared), "chunk_count": len(windows)})
    return selected, {"training_text_sha256": text_digest, "window_content_tokens": WINDOW_CONTENT_TOKENS,
        "window_step_tokens": WINDOW_STEP, "overlap_tokens": WINDOW_CONTENT_TOKENS-WINDOW_STEP,
        "max_total_tokens": MAX_TOTAL_TOKENS, "token_order": "preserved", "coverage": "complete"}
