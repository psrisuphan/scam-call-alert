"""Build local prepared dataset v1 from raw sources.

Follows Phoebe_FullProposal.docx:
- Primary dataset: 1,280 rows across 8 categories (160 rows each; 640 Scam / 640 Not Scam).
  Prunes 1 duplicate and 6 corrupted/incomplete rows per proposal Section 5.
- Supplemental dataset: 198 rows across 5 categories (Scam 73, General 49, Official 37, Verification-call 26, Unknow 13).
  Maps Scam -> 1, General/Official/Verification-call -> 0 per proposal Section 4.1.
  Excludes Unknow (13 rows) per proposal Section 5 & 7.1 ("ตัดข้อมูลซ้ำหรือกำกวม").
  Prunes 18 duplicate Scam rows per proposal Section 5 & 7.1.
- Clusters template variants into group_id to prevent near-duplicate leakage in Stage 01.

Run: uv run --no-project --with pyarrow==25.0.1 --with scikit-learn==1.9.1 python '02 - DATASETs/prepare.py'
"""
from collections import Counter, defaultdict
from pathlib import Path
import csv
import hashlib
import json
import re

import pyarrow.parquet as pq
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

DATA = Path(__file__).resolve().parent

# Primary exclusions per proposal Section 5 ("จัดการข้อมูลซ้ำหรือไม่สมบูรณ์"):
# - 5 encoding corruption rows with \ufffd from source
# - 1 row cut off mid-sentence
# - 1 exact duplicate of hf_001138
PRIMARY_EXCLUSIONS = {
    "hf_000083": ("source_corruption", "Encoding replacement character (\ufffd) present in source text."),
    "hf_000191": ("source_corruption", "Encoding replacement character (\ufffd) present in source text."),
    "hf_000286": ("source_corruption", "Encoding replacement character (\ufffd) present in source text."),
    "hf_000308": ("source_corruption", "Encoding replacement character (\ufffd) present in source text."),
    "hf_000567": ("source_corruption", "Encoding replacement character (\ufffd) present in source text."),
    "hf_000439": ("incomplete_source", "Dialogue ends mid-sentence in source data ('Why should' / 'ทำไมควร')."),
    "hf_001143": ("exact_duplicate", "Redundant exact copy of hf_001138."),
}


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def fixed_format(text):
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def text_key(text):
    return re.sub(r"\s+", " ", fixed_format(text))


def build():
    manifest = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))

    # Verify raw file checksums
    for source in manifest["datasets"]:
        for item in source["files"]:
            target = DATA / item["path"]
            if not target.is_file():
                raise FileNotFoundError(f"Missing raw file {target}. Run 'python 02 - DATASETs/download.py' first.")
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            if actual != item["sha256"]:
                raise ValueError(f"Source checksum mismatch: {item['path']}")

    output = DATA / "processed/v1"
    if output.exists():
        raise FileExistsError(f"{output} exists; do not overwrite a prepared version")

    raw_primary = pq.read_table(DATA / "raw/scam-dialogue-thai-translated/data/train-00000-of-00001.parquet").to_pylist()
    with (DATA / "raw/thai-call-center-call-log/Dataset.csv").open(encoding="utf-8-sig", newline="") as file:
        raw_supplemental = list(csv.DictReader(file))

    mapping = {"Scam": 1, "General": 0, "Official": 0, "Verification-call": 0, "Unknow": None}
    rows = []
    for index, r in enumerate(raw_primary):
        rows.append(dict(conversation_id=f"hf_{index:06d}", source="primary",
                         source_record_id=str(index), source_row_index=index,
                         text=r["translated dialogue"], original_label=r["label"],
                         original_category=r["type"], label=r["label"]))

    for index, r in enumerate(raw_supplemental):
        if r["Type"] not in mapping:
            raise ValueError(f"Unexpected source label: {r['Type']}")
        rows.append(dict(conversation_id=f"kaggle_{index:06d}", source="supplemental",
                         source_record_id=r["Id"], source_row_index=index,
                         text=r["Text"], original_label=r["Type"],
                         original_category=r["Type"], label=mapping[r["Type"]]))

    by_id = {r["conversation_id"]: r for r in rows}
    assert len(rows) == len(by_id) == 1478

    # Compute template clusters deterministically for Stage 01 group-aware splitting
    parent = {cid: cid for cid in by_id}

    def find(cid):
        while parent[cid] != cid:
            parent[cid] = parent[parent[cid]]
            cid = parent[cid]
        return cid

    def join(a, b):
        x, y = find(a), find(b)
        parent[max(x, y)] = min(x, y)

    # 1. Exact duplicates
    exact_groups = defaultdict(list)
    for r in rows:
        exact_groups[text_key(r["text"])].append(r["conversation_id"])
    for members in exact_groups.values():
        if len(members) > 1:
            for cid in members[1:]:
                join(members[0], cid)

    # 2. Near duplicates (char 3-5 gram TF-IDF cosine similarity >= 0.90)
    texts = [text_key(r["text"]) for r in rows]
    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(3, 5), lowercase=False)
    features = vectorizer.fit_transform(texts)
    nn = NearestNeighbors(metric="cosine", algorithm="brute", radius=0.1000000001).fit(features)
    distances, indices = nn.radius_neighbors(features)
    for i, (ds, js) in enumerate(zip(distances, indices)):
        for d, j in zip(ds, js):
            j = int(j)
            if j <= i or texts[i] == texts[j] or 1 - d < 0.90:
                continue
            join(rows[i]["conversation_id"], rows[j]["conversation_id"])

    logs, kept = [], []
    seen_supp = {}

    for r in rows:
        cid, text = r["conversation_id"], r["text"]
        reasons, reason_code = [], None
        label = r["label"]
        duplicate_of = None

        if not isinstance(text, str) or not text.strip():
            reason_code = "invalid_text"
            reasons.append("Missing or invalid text field.")
        elif cid in PRIMARY_EXCLUSIONS:
            code, reason_msg = PRIMARY_EXCLUSIONS[cid]
            reason_code = code
            reasons.append(reason_msg)
            if code == "exact_duplicate":
                duplicate_of = "hf_001138"
        elif r["source"] == "supplemental":
            key = text_key(text)
            if r["original_category"] == "Unknow":
                reason_code = "ambiguous_label"
                reasons.append("Unknow category dialogue excluded per proposal Section 5 & 7.1 ('ตัดข้อมูลซ้ำหรือกำกวม').")
            elif key in seen_supp:
                reason_code = "exact_duplicate"
                duplicate_of = seen_supp[key]
                reasons.append(f"Redundant exact copy of {duplicate_of}.")
            else:
                seen_supp[key] = cid

        status = "exclude" if reason_code else "keep"
        if status == "keep":
            if r["source"] == "primary":
                reasons.append("Retained per proposal Section 4: source Scam/Not Scam label.")
            else:
                reasons.append(f"Retained per proposal Section 4.1: {r['original_category']} mapped to {label}.")
            kept.append({**r, "text": fixed_format(text), "label": label,
                         "group_id": "group_" + find(cid), "human_verified": False})

        log = dict(conversation_id=cid, source=r["source"], source_record_id=r["source_record_id"],
                   source_row_index=r["source_row_index"], decision=status,
                   final_label=label if status == "keep" else None, original_label=r["original_label"],
                   original_category=r["original_category"], reason_code=reason_code or "retained",
                   reasons=reasons, duplicate_of=duplicate_of,
                   group_id="group_" + find(cid),
                   human_verified=False)
        logs.append(log)

    assert len(kept) + sum(l["decision"] == "exclude" for l in logs) == len(rows)
    assert len({r["conversation_id"] for r in kept}) == len(kept)
    assert len({text_key(r["text"]) for r in kept}) == len(kept)
    assert all(type(r["label"]) is int and r["label"] in (0, 1) for r in kept)

    counts = {}
    for source in ["primary", "supplemental"]:
        before = [r for r in rows if r["source"] == source]
        after = [r for r in kept if r["source"] == source]
        counts[source] = dict(original=len(before), retained=len(after), excluded=len(before)-len(after),
                              labels=dict(Counter(str(r["label"]) for r in after)),
                              original_categories=dict(Counter(r["original_category"] for r in before)),
                              retained_categories=dict(Counter(r["original_category"] for r in after)))

    groups = defaultdict(list)
    for r in kept:
        groups[r["group_id"]].append(r["conversation_id"])

    summary = dict(version="v1", status="prepared_per_proposal_docs",
                   counts=counts, excluded_reasons=dict(Counter(l["reason_code"] for l in logs if l["decision"] == "exclude")),
                   related_groups=sum(len(ids) > 1 for ids in groups.values()),
                   split_created=False, human_verified=False,
                   preparation_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())

    output.mkdir(parents=True)
    for source in ["primary", "supplemental"]:
        write_jsonl(output / f"{source}.jsonl", [r for r in kept if r["source"] == source])
    write_jsonl(output / "decisions.jsonl", logs)
    write_jsonl(output / "exclusions.jsonl", [l for l in logs if l["decision"] == "exclude"])
    write_jsonl(output / "groups.jsonl", [dict(group_id=g, members=ids) for g, ids in sorted(groups.items())])
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = DATA / "reports/preparation_v1.json"
    report.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    build()
