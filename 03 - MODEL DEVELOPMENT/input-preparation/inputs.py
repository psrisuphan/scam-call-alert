"""Training-only record retrieval and neutral speaker representations.

Model input conversion refuses unresolved checkpoint-preparation or length policy.
No model weights or remote model code are loaded.
"""
from pathlib import Path
import csv
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = ROOT / "02 - DATASETs/prepared/splits"
DEFAULT_CONFIG = Path(__file__).with_name("preprocessing_config.json")
COLUMNS = ["sample_id", "source_dataset", "source_record_id", "original_label", "label", "transcript"]
ASSIGNMENT_COLUMNS = ["sample_id", "source_dataset", "group_id", "split", "cv_fold"]
LABEL_TO_ID = {"Not Scam": 0, "Scam": 1}
ID_TO_LABEL = {0: "Not Scam", 1: "Scam"}
PRIMARY = re.compile(r"(?<!\S)(ผู้โทร|ผู้รับ|caller|receiver|ผู้รับสาย|คนรับ|ตัวรับสัญญาณ|ผู้รับเงิน|ผู้โทรเข้า|R|ราเชล)\s*:", re.IGNORECASE)
SUPPLEMENTAL = re.compile(r"\[(Call|User)\]\(")


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path, columns):
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != columns:
            raise ValueError(f"Unexpected CSV schema: {path}")
        return list(reader)


def load_partition(partition, *, data=DEFAULT_DATA, fold=None,
                   condition="primary_plus_supplemental", allow_final_test=False, config=None):
    data = Path(data)
    if condition not in ("primary_only", "primary_plus_supplemental"):
        raise ValueError("Unexpected training condition")
    if partition not in ("train_pool", "fold_train", "fold_validation", "test"):
        raise ValueError("Unexpected partition")
    if partition == "test" and not allow_final_test:
        raise ValueError("Final-test loading requires explicit evaluation authorization")
    if partition.startswith("fold_"):
        if type(fold) is not int or fold not in range(5):
            raise ValueError("Fold must be an integer from 0 to 4")
    elif fold is not None:
        raise ValueError("Fold is only valid for fold partitions")
    config = load_config() if config is None else config
    if checksum(data / "split_assignments.csv") != config["assignments_sha256"]:
        raise ValueError("Assignments differ from the configured frozen split")
    if partition != "test" and checksum(data / "0 - train/dataset.csv") != config["training_csv_sha256"]:
        raise ValueError("Training records differ from the configured frozen split")
    assignments = read_csv(data / "split_assignments.csv", ASSIGNMENT_COLUMNS)
    by_id = {row["sample_id"]: row for row in assignments}
    if len(by_id) != len(assignments) or any(not cid for cid in by_id):
        raise ValueError("Duplicate or empty assignment ID")
    for row in assignments:
        if row["split"] == "train" and row["cv_fold"] not in ("0", "1", "2", "3", "4"):
            raise ValueError("Invalid saved validation fold")
        if row["split"] == "test" and row["cv_fold"]:
            raise ValueError("Test records must not have validation folds")
        if row["split"] not in ("train", "test"):
            raise ValueError("Invalid saved partition")
    split_name = "test" if partition == "test" else "train"
    filename = "1 - test/dataset.csv" if partition == "test" else "0 - train/dataset.csv"
    records = read_csv(data / filename, COLUMNS)
    ids = [row["sample_id"] for row in records]
    expected = {row["sample_id"] for row in assignments if row["split"] == split_name}
    if len(ids) != len(set(ids)) or set(ids) != expected:
        raise ValueError("Records do not match saved assignment membership")
    for row in records:
        if row["source_dataset"] != by_id[row["sample_id"]]["source_dataset"]:
            raise ValueError("Record and assignment source identities differ")
        if row["label"] not in LABEL_TO_ID:
            raise ValueError("Unexpected readable label")
    if partition == "fold_validation":
        return [row for row in records if by_id[row["sample_id"]]["cv_fold"] == str(fold)]
    if partition == "fold_train":
        records = [row for row in records if by_id[row["sample_id"]]["cv_fold"] != str(fold)]
    if partition in ("fold_train", "train_pool") and condition == "primary_only":
        records = [row for row in records if row["source_dataset"] == "primary"]
    return records


def parse_turns(row, config=None):
    config = load_config() if config is None else config
    review = config["role_review"]
    if review["status"] != "approved":
        raise ValueError("Source-role handling awaits owner confirmation")
    text = row["transcript"]
    recovery = review["boundary_recovery"]
    if row["sample_id"] == recovery["sample_id"]:
        if recovery["status"] != "approved":
            raise ValueError("Boundary recovery awaits owner confirmation")
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != recovery["transcript_sha256"]:
            raise ValueError("Boundary recovery source text has changed")
        if text.count(recovery["before"]) != 1:
            raise ValueError("Boundary recovery requires exactly one matching fragment")
        text = text.replace(recovery["before"], recovery["after"], 1)
    roles = config["role_mappings"].get(row["source_dataset"], {})
    if row["source_dataset"] == "primary":
        pattern = PRIMARY
    elif row["source_dataset"] == "supplemental":
        pattern = SUPPLEMENTAL
    else:
        raise ValueError(f"Unknown source: {row['source_dataset']}")
    matches = list(pattern.finditer(text))
    if not matches or text[:matches[0].start()].strip():
        raise ValueError(f"{row['sample_id']}: unrecognized source roles or unassigned prefix")
    turns = []
    for i, match in enumerate(matches):
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        body = text[match.end():end]
        role = match.group(1)
        if pattern is SUPPLEMENTAL:
            # Match the last wrapper close, preserving nested parentheses in speech.
            closing = body.rfind(")")
            if closing < 0 or body[closing+1:].strip():
                raise ValueError(f"{row['sample_id']}: malformed source turn wrapper")
            content = body[:closing]
        else:
            # Source colon spacing and inter-tag whitespace are structural separators.
            content = body.strip()
            role = role.lower()
        if role not in roles:
            raise ValueError(f"{row['sample_id']}: source role {role!r} requires owner confirmation")
        if not content.strip():
            empty = review["trailing_empty_turns"]
            if (empty["status"] != "approved" or row["sample_id"] not in empty["sample_ids"]
                    or i != len(matches) - 1):
                raise ValueError(f"{row['sample_id']}: empty turn requires owner handling")
        if re.search(r"\[(?:Call|User)\]\(|(?<!\S)(?:Scammer|Victim)\s*:", content, re.I):
            raise ValueError(f"{row['sample_id']}: unparsed or label-revealing role marker")
        turns.append((roles[role], content))
    if not any(role == "Caller" for role, _ in turns):
        raise ValueError(f"{row['sample_id']}: caller role is not established")
    return turns


def representation(row, mode, config=None):
    if mode not in ("whole_conversation", "caller_only"):
        raise ValueError("Unexpected representation")
    turns = parse_turns(row, config)
    return "\n".join(f"[{role}]: {text}" for role, text in turns
                     if mode == "whole_conversation" or role == "Caller")


def load_config(path=DEFAULT_CONFIG):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_tokenizer(model, config, *, local_files_only=False):
    from transformers import AutoTokenizer
    entry = config["models"][model]
    tokenizer = AutoTokenizer.from_pretrained(entry["checkpoint"], revision=entry["revision"],
        trust_remote_code=False, token=False, use_fast=True, local_files_only=local_files_only)
    if type(tokenizer).__name__ != entry["tokenizer_class"] or tokenizer.pad_token_id != entry["pad_token_id"]:
        raise ValueError("Tokenizer configuration differs from the inspected checkpoint")
    if tokenizer.padding_side != entry["padding_side"]:
        raise ValueError("Tokenizer padding side differs from the inspected checkpoint")
    if tokenizer.truncation_side != config["truncation_side"]:
        raise ValueError("Tokenizer truncation side differs from the approved prefix policy")
    return tokenizer


def tokenized_record(row, mode, model, config, tokenizer):
    entry = config["models"][model]
    if config["role_review"]["status"] != "approved":
        raise ValueError("Source-role and empty-turn handling awaits owner confirmation")
    if entry["checkpoint_preparation"]["status"] != "approved":
        raise ValueError("Checkpoint-specific preparation awaits owner confirmation")
    policy = entry["length_policy"]
    if policy["status"] != "approved":
        raise ValueError("Length policy awaits owner confirmation")
    if policy["kind"] != "fixed_prefix" or type(policy["max_length"]) is not int:
        raise ValueError("Only an explicitly approved fixed prefix policy is implemented")
    if not 2 <= policy["max_length"] <= entry["verified_config_limit"]:
        raise ValueError("Approved length exceeds the verified checkpoint bound")
    text = checkpoint_text(row, mode, model, config)
    encoded = tokenizer(text, add_special_tokens=True, padding=False, truncation=True,
                        max_length=policy["max_length"], return_attention_mask=True)
    fields = {key: encoded[key] for key in entry["model_input_fields"]}
    if len(fields["input_ids"]) > policy["max_length"]:
        raise ValueError("Tokenizer failed to enforce the approved length")
    identity = hashlib.sha256(json.dumps({"config": config, "model": model, "representation": mode},
                                        sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if row["label"] not in LABEL_TO_ID:
        raise ValueError("Unexpected readable label")
    return {"inputs": fields, "label": LABEL_TO_ID[row["label"]], "sample_id": row["sample_id"],
            "configuration_id": identity}


def checkpoint_text(row, mode, model, config):
    """Shared approved text preparation, before any length policy is applied."""
    entry = config["models"][model]
    if entry["checkpoint_preparation"]["status"] != "approved":
        raise ValueError("Checkpoint-specific preparation awaits owner confirmation")
    text = representation(row, mode, config)
    preparation = entry["checkpoint_preparation"]["method"]
    if preparation == "space_marker_only":
        # Only permitted after approval; never collapse characters, words, or digits.
        text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", " ").replace(" ", "<_>")
    elif preparation != "native_tokenizer":
        raise ValueError("Unimplemented checkpoint-specific preparation")
    return text


def pad_batch(items, tokenizer):
    if not items:
        raise ValueError("Cannot pad an empty batch")
    identities = {item["configuration_id"] for item in items}
    if len(identities) != 1:
        raise ValueError("Batch mixes configurations")
    padded = tokenizer.pad([item["inputs"] for item in items], padding="longest",
                           return_attention_mask=True, return_tensors=None)
    return {"inputs": dict(padded), "labels": [item["label"] for item in items],
            "sample_ids": [item["sample_id"] for item in items],
            "configuration_id": items[0]["configuration_id"]}
