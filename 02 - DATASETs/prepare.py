"""Prepare the CSV handoff defined by Plan 00.

Run --review-only to export near-duplicate candidates without finalizing data.
Normal builds require complete, input-bound review decisions.
"""
from collections import Counter, defaultdict
from pathlib import Path
import argparse
import csv
import hashlib
import importlib.metadata
import json

import pyarrow.parquet as pq
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

DATA = Path(__file__).resolve().parent
COLUMNS = ["sample_id", "source_dataset", "source_record_id", "original_label", "label", "transcript"]
AUDIT_COLUMNS = ["sample_id", "source_dataset", "source_file", "source_row_index",
                 "source_record_id", "original_label", "original_category", "action",
                 "reason", "evidence", "recovery_attempt", "related_sample_id",
                 "review_status", "reviewer", "final_decision"]
METHOD = {"representation": "char_tfidf", "ngram_range": [3, 5], "lowercase": False,
          "similarity_threshold": 0.90, "coverage": "all valid raw rows across both sources",
          "comparison": "line endings and edge whitespace only"}
SUPPLEMENTAL_LABELS = {"Scam": "Scam", "General": "Not Scam", "Official": "Not Scam",
                       "Verification-call": "Not Scam", "Unknow": "Not Scam"}


def digest(value):
    return hashlib.sha256(value).hexdigest()


def write_csv(path, columns, rows):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows({key: row[key] for key in columns} for row in rows)


def comparison_copy(text):
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def load_sources():
    manifest = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    for source in manifest["datasets"]:
        for item in source["files"]:
            path = DATA / item["path"]
            if not path.is_file():
                raise FileNotFoundError(f"Missing {path}; run download.py first")
            if digest(path.read_bytes()) != item["sha256"]:
                raise ValueError(f"Source checksum mismatch: {item['path']}")
    primary_file = "raw/scam-dialogue-thai-translated/data/train-00000-of-00001.parquet"
    supplemental_file = "raw/thai-call-center-call-log/Dataset.csv"
    primary = pq.read_table(DATA / primary_file).to_pylist()
    with (DATA / supplemental_file).open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != ["Id", "Text", "Type"]:
            raise ValueError("Unexpected supplemental schema; owner review required")
        supplemental = list(reader)
    if len(primary) != 1280 or len(supplemental) != 198:
        raise ValueError("Source counts differ from proposal; owner review required")
    categories = Counter(row["type"] for row in primary)
    if len(categories) != 8 or set(categories.values()) != {160}:
        raise ValueError("Primary categories differ from proposal; owner review required")
    expected = {"Scam": 73, "General": 49, "Official": 37, "Verification-call": 26, "Unknow": 13}
    if Counter(row["Type"] for row in supplemental) != expected:
        raise ValueError("Supplemental categories differ from proposal; owner review required")
    rows = []
    for index, source in enumerate(primary):
        if type(source["label"]) is not int or source["label"] not in (0, 1):
            raise ValueError("Unexpected primary label; owner review required")
        rows.append(dict(sample_id=f"hf_{index:06d}", source_dataset="primary",
                         source_record_id=f"{primary_file}#row={index}",
                         original_label=str(source["label"]), label=("Not Scam", "Scam")[source["label"]],
                         transcript=source["translated dialogue"], source_file=primary_file,
                         source_row_index=index, original_category=source["type"],
                         original_text=source["dialogue"]))
    if Counter(row["label"] for row in rows) != {"Scam": 640, "Not Scam": 640}:
        raise ValueError("Primary label counts differ from proposal; owner review required")
    for index, source in enumerate(supplemental):
        rows.append(dict(sample_id=f"kaggle_{index:06d}", source_dataset="supplemental",
                         source_record_id=source["Id"], original_label=source["Type"],
                         label=SUPPLEMENTAL_LABELS[source["Type"]], transcript=source["Text"],
                         source_file=supplemental_file, source_row_index=index,
                         original_category=source["Type"], original_text=""))
    for row in rows:
        if not isinstance(row["transcript"], str) or not row["transcript"].strip():
            raise ValueError(f"{row['sample_id']}: invalid transcript; log and obtain owner review")
    return manifest, rows


def candidates(rows):
    texts = [comparison_copy(row["transcript"]) for row in rows]
    features = TfidfVectorizer(analyzer="char", ngram_range=(3, 5), lowercase=False).fit_transform(texts)
    neighbors = NearestNeighbors(metric="cosine", algorithm="brute", radius=0.1000000001).fit(features)
    distances, indices = neighbors.radius_neighbors(features)
    pairs = []
    for i, (ds, js) in enumerate(zip(distances, indices)):
        for distance, j in zip(ds, js):
            j = int(j)
            if j <= i or texts[i] == texts[j] or 1 - distance < 0.90:
                continue
            pairs.append(dict(left=rows[i]["sample_id"], right=rows[j]["sample_id"],
                              similarity=round(float(1 - distance), 6),
                              left_sha256=digest(rows[i]["transcript"].encode()),
                              right_sha256=digest(rows[j]["transcript"].encode())))
    return sorted(pairs, key=lambda pair: (pair["left"], pair["right"]))


def review_inputs(manifest, rows):
    approvals = json.loads((DATA / "preparation_decisions.json").read_text(encoding="utf-8"))
    checksums = {item["path"]: item["sha256"] for source in manifest["datasets"] for item in source["files"]}
    if approvals["source_checksums"] != checksums:
        raise ValueError("Approvals belong to different raw files; owner review required")
    mapping_review = approvals["source_mapping_review"]
    if mapping_review["status"] != "approved" or not all(mapping_review.get(key) for key in ("reviewer", "rationale")):
        raise ValueError("Source mapping is not approved")
    if approvals["method"] != METHOD or approvals["method_review"]["status"] != "approved":
        raise ValueError("Near-duplicate method is not approved")
    for key in ["reviewer", "rationale"]:
        if not approvals["method_review"].get(key):
            raise ValueError(f"Missing method approval {key}")
    by_id = {row["sample_id"]: row for row in rows}
    defects = {row["sample_id"] for row in rows if "\ufffd" in row["transcript"]}
    defects.add("hf_000439")  # Source ends mid-question in both language fields.
    if set(approvals["integrity"]) != defects:
        raise ValueError("Integrity review coverage differs from observed defects")
    for cid, decision in approvals["integrity"].items():
        if decision["transcript_sha256"] != digest(by_id[cid]["transcript"].encode()):
            raise ValueError(f"{cid}: stale integrity review")
        if decision["decision"] not in ("retain", "exclude") or not all(
                decision.get(key) for key in ("reviewer", "rationale", "evidence", "recovery_attempt")):
            raise ValueError(f"{cid}: unresolved integrity review")
    return approvals


def resolve_pairs(pairs, approvals):
    reviews = {(row["left"], row["right"]): row for row in approvals["relationships"]}
    if len(reviews) != len(approvals["relationships"]) or set(reviews) != {(p["left"], p["right"]) for p in pairs}:
        raise ValueError("Near-duplicate review coverage incomplete or stale; run --review-only")
    for pair in pairs:
        decision = reviews[pair["left"], pair["right"]]
        if any(decision[key] != pair[key] for key in ("left_sha256", "right_sha256", "similarity")):
            raise ValueError("Relationship review does not match current transcripts")
        if decision["decision"] not in ("confirmed_related", "independent") or not all(
                decision.get(key) for key in ("reviewer", "rationale", "evidence")):
            raise ValueError(f"Unresolved relationship: {pair['left']} / {pair['right']}")
    return reviews


def prepare_records(rows, approvals, pairs):
    reviews = resolve_pairs(pairs, approvals)
    audit, kept = [], []
    representatives = {}
    ordered = sorted(rows, key=lambda row: (row["source_dataset"] != "primary", row["source_row_index"]))
    labels_by_text = defaultdict(set)
    for row in ordered:
        labels_by_text[comparison_copy(row["transcript"])].add(row["label"])
    if any(len(labels) > 1 for labels in labels_by_text.values()):
        raise ValueError("Exact duplicate label conflict; owner review required")

    def event(row, action, reason, evidence="", related="", reviewer="prepare.py",
              recovery="", final="", status="resolved"):
        audit.append(dict(sample_id=row["sample_id"], source_dataset=row["source_dataset"],
                          source_file=row["source_file"], source_row_index=row["source_row_index"],
                          source_record_id=row["source_record_id"], original_label=row["original_label"],
                          original_category=row["original_category"], action=action, reason=reason,
                          evidence=evidence, recovery_attempt=recovery, related_sample_id=related,
                          review_status=status, reviewer=reviewer, final_decision=final or action))

    for row in ordered:
        cid = row["sample_id"]
        integrity = approvals["integrity"].get(cid)
        if integrity:
            event(row, "integrity_review", integrity["rationale"], integrity["evidence"],
                  reviewer=integrity["reviewer"], recovery=integrity["recovery_attempt"],
                  final=integrity["decision"])
        if integrity and integrity["decision"] == "exclude":
            event(row, "exclude", integrity["rationale"], integrity["evidence"],
                  reviewer=integrity["reviewer"], recovery=integrity["recovery_attempt"])
            continue
        key = comparison_copy(row["transcript"])
        if key in representatives:
            event(row, "remove_duplicate", "Same comparison text and label; retain primary then lowest row.",
                  "Exact equality after line-ending normalization and edge trimming only.",
                  related=representatives[key])
        else:
            representatives[key] = cid
            kept.append(row)
            event(row, "retain", "Confirmed source-to-project label mapping; transcript unchanged.",
                  f"Original label {row['original_label']!r} maps to {row['label']!r}.")
    by_id = {row["sample_id"]: row for row in rows}
    for pair in pairs:
        review = reviews[pair["left"], pair["right"]]
        for cid, related in ((pair["left"], pair["right"]), (pair["right"], pair["left"])):
            event(by_id[cid], "relationship", review["rationale"],
                  f"cosine={pair['similarity']}; {review['evidence']}", related=related,
                  reviewer=review["reviewer"], final=review["decision"])
    return kept, audit


def build(review_only=False):
    manifest, rows = load_sources()
    approvals = review_inputs(manifest, rows)
    pairs = candidates(rows)
    if review_only:
        review_dir = DATA / "review/plan00"
        review_dir.mkdir(parents=True, exist_ok=True)
        write_csv(review_dir / "near_candidates.csv",
                  ["left", "right", "similarity", "left_sha256", "right_sha256"], pairs)
        by_id = {row["sample_id"]: row for row in rows}
        lines = ["# Near-duplicate candidates", ""]
        for pair in pairs:
            lines.extend([f"## {pair['left']} / {pair['right']} ({pair['similarity']})", ""])
            for cid in (pair["left"], pair["right"]):
                lines.extend([f"### {cid}", "", by_id[cid]["transcript"], ""])
        (review_dir / "near_candidates.md").write_text("\n".join(lines), encoding="utf-8")
        print(f"{len(pairs)} candidates written to {review_dir}; no final dataset created")
        return

    kept, audit = prepare_records(rows, approvals, pairs)
    output = DATA / "prepared"
    names = ["prepared.csv", "source_manifest.csv", "record_audit.csv", "preparation_report.md", "README.md"]
    if any((output / name).exists() for name in names):
        raise FileExistsError("Prepared output exists; do not overwrite a completed preparation")
    output.mkdir(parents=True, exist_ok=True)
    source_manifest = []
    for source in manifest["datasets"]:
        for item in source["files"]:
            source_manifest.append(dict(source_dataset=source["role"], source_url=source["source_url"],
                file_url=item.get("url", source.get("download_url", "Unavailable; extracted from pinned archive")),
                download_date=manifest["retrieved_at_utc"], version=source.get("revision", source.get("version")),
                source_file=item["path"], checksum_algorithm="SHA-256", checksum=item["sha256"],
                license=source["license"], original_record_count=source["rows"],
                file_role="archive" if item["path"].endswith(".zip") else "records"))
    write_csv(output / "prepared.csv", COLUMNS, kept)
    write_csv(output / "record_audit.csv", AUDIT_COLUMNS, audit)
    write_csv(output / "source_manifest.csv", list(source_manifest[0]), source_manifest)

    dispositions = Counter(row["action"] for row in audit if row["action"] in ("retain", "exclude", "remove_duplicate"))
    lines = ["# Data preparation report", "",
        f"Preparation version: {approvals['preparation_version']}. Canonical CSV preparation follows Plan 00 on main. The earlier JSONL v1 is superseded.",
        "", "## Rules and provenance", "",
        "Primary: translated dialogue -> transcript; source label 0 -> Not Scam, 1 -> Scam.",
        "Supplemental: Text -> transcript; Type = Scam -> Scam, all other confirmed categories -> Not Scam.",
        "Original labels are preserved as CSV values. Unknow means not labeled Scam by the source; benignity is not independently verified.",
        "IDs are zero-based raw-row IDs (hf_000000 / kaggle_000000), assigned before filtering, never renumbered.",
        "Primary source_record_id is the source file plus #row=N. Supplemental uses original Id; audit row locators disambiguate repeated IDs.",
        "Transcripts are unchanged, including speaker markers, internal whitespace, punctuation, and replacement characters.",
        "Exact comparison normalizes line endings and trims whole-text edges only. Primary, then lowest source row wins.",
        "Three supplemental Id values repeat across different conversations. Stable sample IDs and source row locators prevent collisions.",
        "Short calls, silence/audio-complaint logs, and English-only text are retained when readable; none is excluded merely for length, language, or Unknow category.",
        "No labels conflict among exact copies. Every input has one final disposition; no repairs occurred.",
        "", "## Review and relationships", "",
        "Bukutsu approved the candidate method and six integrity dispositions in the conversation ('yea'). Details are tracked in preparation_decisions.json.",
        "Character 3-5 gram TF-IDF, case preserved; cosine >= 0.90; brute-force coverage across both raw sources.",
        "Candidate matching normalizes line endings and edge whitespace only. The audit vectorizer is discarded, not used for model preprocessing.",
        "Each candidate was compared in context by the coding assistant. Reviews record evidence and reviewer identity; they do not claim independent human verification.",
        f"Candidate pairs: {len(pairs)}. Confirmed related: {sum(r['decision'] == 'confirmed_related' for r in approvals['relationships'])}.",
        "Changed spans for each reviewed pair are preserved in preparation_decisions.json; audit entries identify both related records.",
        "Confirmed relationships appear in record_audit.csv in both directions. Plan 01 constructs connected groups among retained IDs and obtains approval of its holdout procedure.",
        "Lexical detection can miss paraphrases or find coincidental overlap. No assertion is made that all related conversations were found.",
        "", "## Before and after counts", "",
        "| Source | Input | Retained | Excluded | Duplicate removals | Scam | Not Scam |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for source in ("primary", "supplemental"):
        before = [r for r in rows if r["source_dataset"] == source]
        after = [r for r in kept if r["source_dataset"] == source]
        acts = Counter(r["action"] for r in audit if r["source_dataset"] == source)
        counts = Counter(r["label"] for r in after)
        lines.append(f"| {source} | {len(before)} | {len(after)} | {acts['exclude']} | {acts['remove_duplicate']} | {counts['Scam']} | {counts['Not Scam']} |")
    lines += ["", "| Source | Project label | Input | Retained |", "|---|---|---:|---:|"]
    for source in ("primary", "supplemental"):
        for label in ("Scam", "Not Scam"):
            before = sum(r["source_dataset"] == source and r["label"] == label for r in rows)
            after = sum(r["source_dataset"] == source and r["label"] == label for r in kept)
            lines.append(f"| {source} | {label} | {before} | {after} |")
    lines += ["", "| Source | Original category | Input | Retained | Project label |",
              "|---|---|---:|---:|---|"]
    for (source, category), count in sorted(Counter((r["source_dataset"], r["original_category"]) for r in rows).items()):
        after = [r for r in kept if r["source_dataset"] == source and r["original_category"] == category]
        labels = ", ".join(sorted({r["label"] for r in after}))
        lines.append(f"| {source} | {category} | {count} | {len(after)} | {labels} |")
    lines += ["", "## Checks and limitations", "",
        f"Accounting: {len(rows)} = {dispositions['retain']} retained + {dispositions['exclude']} excluded + {dispositions['remove_duplicate']} duplicate removals.",
        "Validation: unique IDs, labels, raw-content preservation, CSV roundtrip, audit accounting, source hashes, review completeness, and deterministic reproduction are checked by test_prepare.py.",
        "Three truncated primary calls are excluded; three readable calls with replacement characters are retained unchanged by owner approval.",
        "Both datasets are simulated. Foreign scenarios and translated dialogue do not establish real-call performance.",
        "Primary license is undeclared; supplemental is CC BY-NC-ND 4.0. Prepared data stays local and ignored. Distribution rights require separate confirmation.",
        "Splitting, tokenization, augmentation, resampling, learned preprocessing, and model selection have not occurred.",
        "", "## Build provenance", "",
        f"prepare.py SHA-256: {digest(Path(__file__).read_bytes())}",
        f"Decisions SHA-256: {digest((DATA / 'preparation_decisions.json').read_bytes())}",
        f"Dependencies: pyarrow {importlib.metadata.version('pyarrow')}; scikit-learn {importlib.metadata.version('scikit-learn')}.", ""]
    (output / "preparation_report.md").write_text("\n".join(lines), encoding="utf-8")
    (output / "README.md").write_text(
        "# Prepared conversations\n\n"
        "prepared.csv is the canonical six-column CSV, with one retained conversation per row. Read with Python csv.DictReader and newline=''.\n\n"
        "source_manifest.csv records source versions, download dates, hashes, licenses, and counts. Archive and extracted CSV counts describe the same source, not additional samples.\n\n"
        "record_audit.csv logs each disposition and integrity/relationship review, with source locators and evidence. Multiple audit entries may refer to one sample.\n\n"
        "preparation_report.md explains rules, counts, limitations, and build provenance.\n\n"
        "Acquisition, mapping, integrity review, exact deduplication, candidate review, and CSV export are complete. No splitting, tokenization, augmentation, resampling, learned preprocessing, or model selection has occurred.\n\n"
        "Next: [Plan 01](../../01%20-%20PLANs/01%20-%20DATA%20SPLIT%20AND%20EXPERIMENT%20DESIGN.md). It uses confirmed relationship audit entries to construct groups; holdout allocation still requires owner approval. The splits/ directories contain placeholders only.\n",
        encoding="utf-8")
    print(f"Prepared {len(kept)} records from {len(rows)} inputs; dispositions: {dict(dispositions)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-only", action="store_true")
    build(parser.parse_args().review_only)
