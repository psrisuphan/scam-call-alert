"""Render training-only class/source truncation evidence from Plan 02 report."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = ROOT / "03 - MODEL DEVELOPMENT/input-preparation/token_length_report.json"


def render(path=DEFAULT_REPORT):
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    lines = ["## Training-pool marked whole-conversation truncation exposure", "",
        f"Source: `{Path(path).name}`; population {report['population']}; scope: {report['scope']}", "",
        "Affected count is the number of records exceeding the fixed input budget. Token loss is the report's estimated dropped content tokens, not semantic or predictive loss.", "",
        "| Model | Source/class | Records | Affected count | Affected (%) | Estimated dropped content tokens |",
        "|---|---|---:|---:|---:|---:|"]
    for model_key, model in report["models"].items():
        group = model["representations"]["whole_conversation.role_marked"]["subsets"]
        for key in ("primary:Scam", "primary:Not Scam", "supplemental:Scam", "supplemental:Not Scam"):
            values = group[key]
            lines.append(f"| {model_key} | {key} | {values['records']} | {values['exceeding_budget']} | {values['exceeding_percent']:.2f}% | {values['estimated_dropped_content_tokens']} |")
    lines += ["", "These are record fractions and token-count estimates, not fractions of spoken content lost or measured prediction damage. The fixed-prefix policy remains as approved. Do not inspect or load held-out test transcripts for this report."]
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    print(render(parser.parse_args().report))
