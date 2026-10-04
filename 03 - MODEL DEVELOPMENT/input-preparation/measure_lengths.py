"""Measure full training-only token lengths; never apply a length policy."""
from collections import defaultdict
from pathlib import Path
import importlib.metadata
import json
import statistics

import inputs


def summarize(lengths, budget, special_tokens):
    ordered = sorted(lengths)
    if not ordered:
        raise ValueError("Cannot summarize an empty training subset")

    def percentile(fraction):
        position = (len(ordered) - 1) * fraction
        lo = int(position)
        hi = min(lo + 1, len(ordered) - 1)
        return round(ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo), 2)

    dropped = sum(max(0, length - budget) for length in ordered)
    content = sum(length - special_tokens for length in ordered)
    exceeding = sum(length > budget for length in ordered)
    return {
        "records": len(ordered), "min": min(ordered), "median": statistics.median(ordered),
        "p90": percentile(.9), "p95": percentile(.95), "max": max(ordered),
        "budget": budget, "exceeding_budget": exceeding,
        "exceeding_percent": round(100 * exceeding / len(ordered), 2),
        "estimated_dropped_content_tokens": dropped,
        "estimated_dropped_content_percent": round(100 * dropped / content, 2) if content else 0,
    }


def measure(config):
    for package, version in config["dependencies"].items():
        if importlib.metadata.version(package) != version:
            raise ValueError(f"Use {package}=={version}")
    records = inputs.load_partition("train_pool", config=config)
    # Establish coverage before loading any tokenizer.
    for record in records:
        inputs.parse_turns(record, config)
    result = {
        "training_csv_sha256": config["training_csv_sha256"],
        "assignments_sha256": config["assignments_sha256"],
        "configuration_sha256": inputs.checksum(inputs.DEFAULT_CONFIG),
        "population": len(records),
        "scope": "Full training pool only. No final-test file is loaded.",
        "percentiles": "Linear interpolation at (n-1)*p; descriptive only, not fitted limits.",
        "loss_estimate": "For a fixed prefix, retain budget minus required special tokens. Token loss is not semantic or prediction loss.",
        "dependencies": config["dependencies"],
        "models": {},
    }
    for model, entry in config["models"].items():
        tokenizer = inputs.load_tokenizer(model, config, local_files_only=True)
        special = tokenizer.num_special_tokens_to_add()
        if special != entry["special_tokens_count"]:
            raise ValueError("Tokenizer special-token count changed")
        result["models"][model] = {"revision": entry["revision"],
                                  "length_policy": entry["length_policy"], "representations": {}}
        for mode in config["representations"]:
            lengths, subsets = [], defaultdict(list)
            for record in records:
                text = inputs.checkpoint_text(record, mode, model, config)
                encoded = tokenizer(text, add_special_tokens=True, padding=False,
                                    truncation=False, return_attention_mask=False, verbose=False)
                length = len(encoded["input_ids"])
                lengths.append(length)
                subsets[record["source_dataset"]].append(length)
                subsets[record["source_dataset"] + ":" + record["label"]].append(length)
            budget = entry["length_policy"]["max_length"]
            result["models"][model]["representations"][mode] = {
                "all": summarize(lengths, budget, special),
                "at_config_bound": summarize(lengths, entry["verified_config_limit"], special),
                "subsets": {name: summarize(values, budget, special)
                            for name, values in sorted(subsets.items())},
            }
    return result


def main():
    result = measure(inputs.load_config())
    destination = Path(__file__).with_name("token_length_report.json")
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Measured", result["population"], "training records. No truncation or test loading.")
    for model, entry in result["models"].items():
        for mode, values in entry["representations"].items():
            print(model, mode, json.dumps(values["all"]))


if __name__ == "__main__":
    main()
