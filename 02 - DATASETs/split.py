"""Create the owner-approved Stage 01 partitions without changing canonical CSV."""
from collections import Counter, defaultdict
from pathlib import Path
import csv
import hashlib
import importlib.metadata
import json

from sklearn.model_selection import StratifiedGroupKFold

DATA = Path(__file__).resolve().parent
RECORD_COLUMNS = ["sample_id", "source_dataset", "source_record_id", "original_label", "label", "transcript"]
ASSIGNMENT_COLUMNS = ["sample_id", "source_dataset", "group_id", "split", "cv_fold"]
LABELS = {"Scam", "Not Scam"}
SOURCES = ("primary", "supplemental")


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path, columns=None):
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if columns is not None and reader.fieldnames != columns:
            raise ValueError(f"Unexpected CSV schema: {path}")
        return list(reader)


def write_csv(path, columns, rows):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def group_ids(records, audit):
    ids = [row["sample_id"] for row in records]
    if any(not cid for cid in ids) or len(set(ids)) != len(ids):
        raise ValueError("Canonical sample IDs must be unique and nonempty")
    if any(row["review_status"] != "resolved" for row in audit):
        raise ValueError("Preparation review cases remain unresolved")
    dispositions = [row for row in audit if row["action"] in ("retain", "exclude", "remove_duplicate")]
    if len({row["sample_id"] for row in dispositions}) != len(dispositions):
        raise ValueError("Preparation has multiple final dispositions for a sample")
    if {row["sample_id"] for row in dispositions if row["action"] == "retain"} != set(ids):
        raise ValueError("Canonical IDs disagree with the preparation audit")
    parent = {row["sample_id"]: row["sample_id"] for row in dispositions}

    def find(cid):
        if cid not in parent:
            raise ValueError(f"Audit relationship references an unknown ID: {cid}")
        while parent[cid] != cid:
            parent[cid] = parent[parent[cid]]
            cid = parent[cid]
        return cid

    for row in audit:
        if row["action"] == "remove_duplicate" or (
                row["action"] == "relationship" and row["final_decision"] == "confirmed_related"):
            a, b = find(row["sample_id"]), find(row["related_sample_id"])
            parent[max(a, b)] = min(a, b)
    # Removed exact copies can connect retained variants; form components first,
    # then project onto retained IDs. The minimum raw ID remains the stable root.
    return {cid: "group_" + find(cid) for cid in ids}


def counts(records):
    result = {source: {label: 0 for label in sorted(LABELS)} for source in SOURCES}
    for row in records:
        if row["source_dataset"] not in SOURCES or row["label"] not in LABELS:
            raise ValueError(f"Unexpected source or label: {row['sample_id']}")
        result[row["source_dataset"]][row["label"]] += 1
    return result


def assign(records, groups, config):
    records = sorted(records, key=lambda row: row["sample_id"])
    strata = [row["source_dataset"] + ":" + row["label"] for row in records]
    group_values = [groups[row["sample_id"]] for row in records]
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=config["seed"])
    train_indices, test_indices = next(splitter.split(records, strata, group_values))
    train = [records[i] for i in train_indices]
    test = [records[i] for i in test_indices]
    assignments = {row["sample_id"]: dict(sample_id=row["sample_id"], source_dataset=row["source_dataset"],
        group_id=groups[row["sample_id"]], split="test", cv_fold="") for row in test}
    train_groups = [groups[row["sample_id"]] for row in train]
    labels = [row["label"] for row in train]
    for fold, (_, validation) in enumerate(splitter.split(train, labels, train_groups)):
        for i in validation:
            row = train[i]
            assignments[row["sample_id"]] = dict(sample_id=row["sample_id"], source_dataset=row["source_dataset"],
                group_id=groups[row["sample_id"]], split="train", cv_fold=str(fold))
    return [assignments[row["sample_id"]] for row in records]


def verify(records, assignments, groups, train, test):
    canonical = {row["sample_id"]: row for row in records}
    ids = [row["sample_id"] for row in assignments]
    if len(ids) != len(set(ids)) or set(ids) != set(canonical):
        raise ValueError("Each canonical ID must have exactly one assignment")
    by_id = {row["sample_id"]: row for row in assignments}
    membership = defaultdict(set)
    for assignment in assignments:
        cid = assignment["sample_id"]
        if assignment["source_dataset"] != canonical[cid]["source_dataset"]:
            raise ValueError(f"Source identity mismatch: {cid}")
        if assignment["group_id"] != groups[cid]:
            raise ValueError(f"Group identity mismatch: {cid}")
        if assignment["split"] == "train":
            if assignment["cv_fold"] not in ("0", "1", "2", "3", "4"):
                raise ValueError(f"Invalid training fold: {cid}")
        elif assignment["split"] == "test":
            if assignment["cv_fold"] != "":
                raise ValueError(f"Test record has a CV fold: {cid}")
        else:
            raise ValueError(f"Invalid partition: {cid}")
        membership[assignment["group_id"]].add((assignment["split"], assignment["cv_fold"]))
    if any(len(values) != 1 for values in membership.values()):
        raise ValueError("Related group crosses partition or CV-fold boundaries")
    observed = []
    for split, subset in (("train", train), ("test", test)):
        if {row["label"] for row in subset} != LABELS:
            raise ValueError(f"Both classes required in {split}")
        subset_ids = [row["sample_id"] for row in subset]
        expected = {row["sample_id"] for row in assignments if row["split"] == split}
        if len(subset_ids) != len(set(subset_ids)) or set(subset_ids) != expected:
            raise ValueError(f"Derived {split} membership differs from assignments")
        for row in subset:
            if row != canonical[row["sample_id"]]:
                raise ValueError(f"Derived record differs from canonical: {row['sample_id']}")
        observed.extend(subset_ids)
    if len(observed) != len(records) or len(set(observed)) != len(records):
        raise ValueError("Train/test must cover canonical records exactly once")
    for fold in range(5):
        validation = [row for row in train if by_id[row["sample_id"]]["cv_fold"] == str(fold)]
        training = [row for row in train if by_id[row["sample_id"]]["cv_fold"] != str(fold)]
        primary = [row for row in training if row["source_dataset"] == "primary"]
        for name, subset in (("validation", validation), ("training", training), ("primary-only training", primary)):
            if {row["label"] for row in subset} != LABELS:
                raise ValueError(f"Fold {fold} {name} lacks a class")


def report(records, audit, groups, assignments, config):
    by_id = {row["sample_id"]: row for row in assignments}
    sizes = Counter(groups.values())
    lines = ["# Split report", "", "## Procedure and approval", "",
        "Bukutsu approved the procedure and previewed allocation in the conversation: 'yep all good'.",
        "Sort sample_id; use scikit-learn StratifiedGroupKFold with n_splits=5, shuffle=True, random_state=67.",
        "Holdout stratifies on source_dataset + label. The first returned fold is test; the other four form the training pool. No alternate folds or seeds were searched.",
        "Within the training pool, use five StratifiedGroupKFold folds stratified on binary label, shuffle=True, random_state=67.",
        "Confirmed relationships and exact-copy links form connected components across the complete raw-ID audit, then are projected onto retained records.",
        "Stable group IDs are group_ plus the minimum raw sample_id in the component; unrelated records are singleton groups. IDs are not renumbered.",
        f"Related multi-record groups: {sum(n > 1 for n in sizes.values())}; retained members: {sum(n for n in sizes.values() if n > 1)}; largest: {max(sizes.values())}.",
        "Group separation takes priority over ratios. This input contains no cross-source related groups; the implementation also connects cross-source evidence.",
        "Assignment CSV is authoritative. It is reused for all models and both training data conditions.",
        "", "## Provenance", "",
        f"scikit-learn version: {importlib.metadata.version('scikit-learn')}; seed: 67.",
        f"split.py SHA-256: {checksum(Path(__file__))}",
        f"split_config.json SHA-256: {checksum(DATA / 'split_config.json')}"]
    for name, value in config["input_checksums"].items():
        lines.append(f"{name} SHA-256: {value}")
    for item in read_csv(DATA / "prepared/source_manifest.csv"):
        lines.append(f"Source: {item['source_dataset']}; file: {item['source_file']}; version: {item['version']}; SHA-256: {item['checksum']}.")
    lines += ["", "## Allocations", "",
        "Scam and Not Scam percentages use the total in each row. Source shares use the full prepared source population, including for fold rows.", "",
        "| Partition | Source | Scam | Not Scam | Total | Scam % | Not Scam % | Share of that source |",
        "|---|---|---:|---:|---:|---:|---:|---:|"]
    subsets = [("train", [row for row in records if by_id[row["sample_id"]]["split"] == "train"]),
               ("test", [row for row in records if by_id[row["sample_id"]]["split"] == "test"])]
    for fold in range(5):
        subsets += [(f"fold {fold} validation", [row for row in records if by_id[row["sample_id"]]["split"] == "train" and by_id[row["sample_id"]]["cv_fold"] == str(fold)]),
                    (f"fold {fold} training", [row for row in records if by_id[row["sample_id"]]["split"] == "train" and by_id[row["sample_id"]]["cv_fold"] != str(fold)])]
    totals = counts(records)
    for name, subset in subsets:
        values = counts(subset)
        for source in SOURCES:
            value = values[source]
            size = sum(value.values())
            scam_percent = 100 * value["Scam"] / size if size else 0
            not_scam_percent = 100 * value["Not Scam"] / size if size else 0
            lines.append(f"| {name} | {source} | {value['Scam']} | {value['Not Scam']} | {size} | {scam_percent:.2f}% | {not_scam_percent:.2f}% | {100*size/sum(totals[source].values()):.2f}% |")
    lines += ["", "## Verification and use", "",
        "Every canonical ID appears once in train/test; IDs are disjoint; related groups never cross holdout or validation-fold boundaries.",
        "Each training record validates exactly once; test records have no fold. Both classes occur in every training/validation subset, including primary-only fold training.",
        "Derived rows match canonical records exactly. Canonical preparation files remain unchanged. test_split.py checks these invariants, boundary failures, and deterministic rebuild.",
        "For fold k, both conditions validate on all training-pool records with cv_fold=k.",
        "Primary-only trains on primary-source records with cv_fold!=k; primary + supplemental trains on all records with cv_fold!=k.",
        "Retrieve final test only for later final evaluation. Use one-to-one joins by sample_id and verify source_dataset equality.",
        "", "## Limitations", "",
        "Primary test fraction is 255/1276 (19.98%); supplemental is 36/179 (20.11%). Whole-record rounding and unbroken groups constrain exact source proportions. Owner approved these deviations.",
        "CV stratifies on binary label, not source; per-source validation counts vary and are listed above, including zeros if any.",
        "scikit-learn group shuffling is restricted to groups with similar class distributions; it is not an unrestricted shuffle. Saved membership, pinned implementation, and hashes establish reproducibility.",
        "Confirmed relationships come from lexical candidate detection and contextual assistant review. Undetected relationships remain possible.",
        "The test set represents these simulated sources, not real calls or unseen scam categories.",
        "No tokenization, augmentation, resampling, learned preprocessing, model selection, or training has occurred.", ""]
    return "\n".join(lines)


def build():
    prepared = DATA / "prepared"
    config = json.loads((DATA / "split_config.json").read_text(encoding="utf-8"))
    if config["approval"]["status"] != "approved" or not config["approval"]["reviewer"]:
        raise ValueError("Owner holdout approval is required")
    if config["seed"] != 67 or config["holdout_fold"] != 0 or config["n_splits"] != 5:
        raise ValueError("Configuration differs from the approved procedure")
    if importlib.metadata.version("scikit-learn") != config["scikit_learn_version"]:
        raise ValueError("Use the approved scikit-learn version to reproduce assignments")
    for name, expected in config["input_checksums"].items():
        if checksum(prepared / name) != expected:
            raise ValueError(f"Preparation changed: {name}; regenerate with renewed owner approval")
    records = sorted(read_csv(prepared / "prepared.csv", RECORD_COLUMNS), key=lambda row: row["sample_id"])
    audit = read_csv(prepared / "record_audit.csv")
    counts(records)
    groups = group_ids(records, audit)
    assignments = assign(records, groups, config)
    by_id = {row["sample_id"]: row for row in assignments}
    train = [row for row in records if by_id[row["sample_id"]]["split"] == "train"]
    test = [row for row in records if by_id[row["sample_id"]]["split"] == "test"]
    if {"train": counts(train), "test": counts(test)} != config["approved_allocation"]:
        raise ValueError("Achieved allocation differs from owner approval")
    verify(records, assignments, groups, train, test)
    folder = prepared / "splits"
    outputs = ["0 - train/dataset.csv", "1 - test/dataset.csv", "split_assignments.csv", "split_report.md"]
    if any((folder / name).exists() for name in outputs):
        raise FileExistsError("Split artifacts exist; do not overwrite frozen assignments")
    for name in ("0 - train", "1 - test"):
        (folder / name).mkdir(parents=True, exist_ok=True)
    write_csv(folder / outputs[0], RECORD_COLUMNS, train)
    write_csv(folder / outputs[1], RECORD_COLUMNS, test)
    write_csv(folder / outputs[2], ASSIGNMENT_COLUMNS, assignments)
    (folder / outputs[3]).write_text(report(records, audit, groups, assignments, config), encoding="utf-8")
    readme = prepared / "README.md"
    text = (
        "# Prepared conversations\n\n"
        "prepared.csv is the canonical six-column CSV. source_manifest.csv records versions, hashes, retrieval dates, licenses, and counts. record_audit.csv records each disposition and review with source locators. preparation_report.md records the Stage 00 snapshot before splitting.\n\n"
        "Canonical data and preparation provenance remain unchanged. Acquisition, label mapping, integrity review, duplicate handling, and relationship review are complete.\n\n"
        "## Frozen splits\n\n"
        "splits/0 - train/dataset.csv is the training pool; splits/1 - test/dataset.csv is the final holdout. Both keep the canonical schema.\n\n"
        "splits/split_assignments.csv records stable group_id, split, and cv_fold. Test records have blank cv_fold. splits/split_report.md records provenance, counts, algorithms, checks, and limitations.\n\n"
        "Join by sample_id with one-to-one membership and matching source identity. Fold k validates on train records with cv_fold=k; train on the other folds. Primary-only filters only fold training to primary, never validation. Primary + supplemental uses both sources. All models reuse these assignments.\n\n"
        "Canonical prepared.csv remains unchanged. Derived CSVs must not be edited independently. Preparation changes invalidate the split and require regenerated, verified artifacts.\n\n"
        "Next: Plan 02. Use the training pool only for input-design inspection; do not inspect final test text to design preprocessing. No model-oriented preprocessing has occurred.\n")
    readme.write_text(text, encoding="utf-8")
    print(f"Frozen split: {len(train)} training / {len(test)} test; 5 CV folds")


if __name__ == "__main__":
    build()
