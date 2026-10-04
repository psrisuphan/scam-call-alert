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
    if partition == "test" and checksum(data / "1 - test/dataset.csv") != config["test_csv_sha256"]:
        raise ValueError("Test records differ from the configured frozen split")
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


def representation(row, mode, config=None, *, marker_condition="role_marked"):
    if mode not in ("whole_conversation", "caller_only"):
        raise ValueError("Unexpected representation")
    if marker_condition not in ("role_marked", "role_free"):
        raise ValueError("Unexpected marker condition")
    turns = parse_turns(row, config)
    return "\n".join(f"[{role}]: {text}" if marker_condition == "role_marked" else text
                     for role, text in turns if mode == "whole_conversation" or role == "Caller")


def load_config(path=DEFAULT_CONFIG):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def added_token_identity(tokenizer):
    """Check added vocabulary without copying the entire base vocabulary per input."""
    return tuple((index, token.content, token.single_word, token.lstrip, token.rstrip,
                  token.normalized, token.special)
                 for index, token in sorted(tokenizer.backend_tokenizer.get_added_tokens_decoder().items()))


def load_tokenizer(model, config, *, local_files_only=False):
    from transformers import AutoTokenizer
    entry = config["models"][model]
    location = entry["checkpoint"]
    if local_files_only:
        # Loading the pinned snapshot path also prevents library metadata probes
        # that otherwise bypass local_files_only for some fast tokenizers.
        from huggingface_hub import snapshot_download
        location = snapshot_download(entry["checkpoint"], revision=entry["revision"],
                                     local_files_only=True, token=False)
    tokenizer = AutoTokenizer.from_pretrained(location, revision=entry["revision"],
        trust_remote_code=False, token=False, use_fast=True, local_files_only=local_files_only)
    if type(tokenizer).__name__ != entry["tokenizer_class"] or tokenizer.pad_token_id != entry["pad_token_id"]:
        raise ValueError("Tokenizer configuration differs from the inspected checkpoint")
    if tokenizer.padding_side != entry["padding_side"]:
        raise ValueError("Tokenizer padding side differs from the inspected checkpoint")
    if tokenizer.truncation_side != config["truncation_side"]:
        raise ValueError("Tokenizer truncation side differs from the approved prefix policy")
    tokenizer._scam_checkpoint_identity = (entry["checkpoint"], entry["revision"])
    tokenizer._scam_added_token_identity = added_token_identity(tokenizer)
    return tokenizer


def checkpoint_prepare_text(text, model, config):
    """Prepare ordinary text without detecting source prefixes or altering roles."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Transcript must be nonempty text")
    entry = config["models"][model]
    if entry["checkpoint_preparation"]["status"] != "approved":
        raise ValueError("Checkpoint-specific preparation awaits owner confirmation")
    preparation = entry["checkpoint_preparation"]["method"]
    if preparation == "space_marker_only":
        return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", " ").replace(" ", "<_>")
    if preparation != "native_tokenizer":
        raise ValueError("Unimplemented checkpoint-specific preparation")
    return text


def configuration_id(model, config, mode, marker_condition):
    if mode not in config["representations"] or marker_condition not in config["marker_conditions"]:
        raise ValueError("Unexpected representation or marker condition")
    identity = {"config": config, "model": model, "representation": mode,
                "marker_condition": marker_condition, "component_sha256": checksum(Path(__file__))}
    return hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def padding_contract(tokenizer):
    """Serializable frozen tokenizer requirements carried outside model inputs."""
    checkpoint = getattr(tokenizer, "_scam_checkpoint_identity", None)
    if checkpoint is None:
        raise ValueError("Use the shared pinned tokenizer loader")
    return {"checkpoint": checkpoint[0], "revision": checkpoint[1],
            "tokenizer_class": type(tokenizer).__name__,
            "pad_token_id": tokenizer.pad_token_id, "padding_side": tokenizer.padding_side,
            "truncation_side": tokenizer.truncation_side,
            "special_tokens_count": tokenizer.num_special_tokens_to_add(),
            "added_tokens_sha256": hashlib.sha256(json.dumps(added_token_identity(tokenizer),
                                                             ensure_ascii=False).encode()).hexdigest()}


def prepare_text(text, model, config, tokenizer, *, mode="whole_conversation",
                 marker_condition="role_free"):
    """Convert already-rendered text; no labels, dataset identity or role parsing.

    Ordinary STT uses the defaults. The dataset adapter supplies its explicitly
    rendered research condition. Condition metadata never changes spoken text.
    """
    identity = configuration_id(model, config, mode, marker_condition)
    entry = config["models"][model]
    policy = entry["length_policy"]
    if policy["status"] != "approved":
        raise ValueError("Length policy awaits owner confirmation")
    if policy["kind"] != "fixed_prefix" or type(policy["max_length"]) is not int:
        raise ValueError("Only an explicitly approved fixed prefix policy is implemented")
    if not 2 <= policy["max_length"] <= entry["verified_config_limit"]:
        raise ValueError("Approved length exceeds the verified checkpoint bound")
    prepared = checkpoint_prepare_text(text, model, config)
    if (getattr(tokenizer, "_scam_checkpoint_identity", None) != (entry["checkpoint"], entry["revision"])
            or getattr(tokenizer, "_scam_added_token_identity", None) != added_token_identity(tokenizer)
            or type(tokenizer).__name__ != entry["tokenizer_class"]
            or tokenizer.pad_token_id != entry["pad_token_id"]
            or tokenizer.padding_side != entry["padding_side"]
            or tokenizer.truncation_side != config["truncation_side"]
            or tokenizer.num_special_tokens_to_add() != entry["special_tokens_count"]):
        raise ValueError("Tokenizer differs from frozen configuration")
    full = tokenizer(prepared, add_special_tokens=True, padding=False, truncation=False, verbose=False)
    encoded = tokenizer(prepared, add_special_tokens=True, padding=False, truncation=True,
                        max_length=policy["max_length"], return_attention_mask=True, verbose=False)
    fields = {key: encoded[key] for key in entry["model_input_fields"]}
    if len(fields["input_ids"]) > policy["max_length"]:
        raise ValueError("Tokenizer failed to enforce the approved length")
    dropped = len(full["input_ids"]) - len(fields["input_ids"])
    return {"inputs": fields, "configuration_id": identity, "padding_contract": padding_contract(tokenizer),
            "representation": mode, "marker_condition": marker_condition,
            "notices": {"original_token_count": len(full["input_ids"]),
                        "prepared_token_count": len(fields["input_ids"]),
                        "dropped_token_count": dropped, "truncated": dropped > 0}}


def tokenized_record(row, mode, model, config, tokenizer, *, marker_condition="role_marked"):
    if row["label"] not in LABEL_TO_ID:
        raise ValueError("Unexpected readable label")
    text = representation(row, mode, config, marker_condition=marker_condition)
    item = prepare_text(text, model, config, tokenizer, mode=mode, marker_condition=marker_condition)
    return dict(item, label=LABEL_TO_ID[row["label"]], sample_id=row["sample_id"])


def checkpoint_text(row, mode, model, config, *, marker_condition="role_marked"):
    """Dataset adapter renders first; shared preparation follows before truncation."""
    return checkpoint_prepare_text(representation(row, mode, config, marker_condition=marker_condition),
                                   model, config)


def load_prepared(records, mode, model, config, *, marker_condition="role_marked", folder=None):
    """Retrieve verified training-only exports for already-selected assigned rows.

    This cannot be used as a final-test loader. Select membership with
    load_partition first; all provenance/labels remain separate from inputs.
    """
    folder = DEFAULT_CONFIG.parent / "prepared" if folder is None else Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    config_digest = hashlib.sha256((json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode()).hexdigest()
    expected = {"configuration_sha256": config_digest, "component_sha256": checksum(Path(__file__)),
                "training_csv_sha256": config["training_csv_sha256"],
                "assignments_sha256": config["assignments_sha256"],
                "export_script_sha256": checksum(DEFAULT_CONFIG.parent / "scripts/8.export_inputs.py")}
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise ValueError("Stale prepared manifest; regenerate separately")
    if manifest.get("models") != config["models"] or manifest.get("dependencies") != config["dependencies"]:
        raise ValueError("Prepared tokenizer/dependency configuration differs")
    for package, version in config["dependencies"].items():
        import importlib.metadata
        if importlib.metadata.version(package) != version:
            raise ValueError(f"Use {package}=={version}")
    name = f"{model}.{mode}.{marker_condition}.jsonl"
    path = folder / name
    if checksum(path) != manifest["files"][name]["sha256"]:
        raise ValueError("Prepared file checksum mismatch")
    items = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    by_id = {item["sample_id"]: item for item in items}
    training = load_partition("train_pool", config=config)
    if len(items) != len(by_id) or set(by_id) != {row["sample_id"] for row in training}:
        raise ValueError("Prepared training membership differs")
    training_by_id = {row["sample_id"]: row for row in training}
    assignments = {row["sample_id"]: row for row in read_csv(DEFAULT_DATA / "split_assignments.csv", ASSIGNMENT_COLUMNS)}
    identity = configuration_id(model, config, mode, marker_condition)
    selected = []
    if len({row["sample_id"] for row in records}) != len(records):
        raise ValueError("Duplicate requested record")
    for record in records:
        cid = record["sample_id"]
        if cid not in training_by_id or record != training_by_id[cid]:
            raise ValueError("Requested record is not an unchanged training record")
        item = by_id[cid]
        assignment = assignments[cid]
        if (item["configuration_id"] != identity or item["representation"] != mode
                or item["marker_condition"] != marker_condition or item["split"] != "train"
                or item["source_dataset"] != record["source_dataset"]
                or item["label"] != LABEL_TO_ID[record["label"]]
                or item["cv_fold"] != int(assignment["cv_fold"])
                or item["group_id"] != assignment["group_id"]):
            raise ValueError("Prepared record identity or metadata differs")
        selected.append(item)
    return selected


def pad_batch(items, tokenizer):
    if not items:
        raise ValueError("Cannot pad an empty batch")
    identities = {item["configuration_id"] for item in items}
    if len(identities) != 1:
        raise ValueError("Batch mixes configurations")
    actual = padding_contract(tokenizer)
    if any(item.get("padding_contract") != actual for item in items):
        raise ValueError("Batch tokenizer/padding differs from frozen configuration")
    for item in items:
        fields = item["inputs"]
        size = len(fields["input_ids"])
        if not size or any(len(values) != size for values in fields.values()):
            raise ValueError("Invalid unpadded input field lengths")
        if fields.get("attention_mask") != [1] * size:
            raise ValueError("Batch requires unpadded inputs and valid attention masks")
    padded = tokenizer.pad([item["inputs"] for item in items], padding="longest",
                           return_attention_mask=True, return_tensors=None)
    result = {"inputs": dict(padded), "configuration_id": items[0]["configuration_id"]}
    for singular, plural in (("label", "labels"), ("sample_id", "sample_ids")):
        if any(singular in item for item in items):
            if not all(singular in item for item in items):
                raise ValueError("Batch mixes labeled and unlabeled metadata")
            result[plural] = [item[singular] for item in items]
    return result
