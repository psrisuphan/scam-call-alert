#!/usr/bin/env python3
"""Assign approved first-pass runs; never execute or approve experiments."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from prepare_recordings import validate_provenance

APPROACHES = ('latest', 'recent', 'accumulated')


def schedule(rows):
    if len(rows) != 12 or any(row['partition'] != 'development' for row in rows):
        raise ValueError('First-pass schedule requires exactly 12 development recordings')
    if any(sum(row['label'] == label for row in rows) != 6 for label in ('Scam', 'Not Scam')):
        raise ValueError('Development membership must be 6 Scam and 6 Not Scam')
    if len({row['group_id'] for row in rows}) != 12:
        raise ValueError('Development groups must be distinct')
    assignments = []
    for index, row in enumerate(rows):
        rotation = index % 3
        order = APPROACHES[rotation:] + APPROACHES[:rotation]
        for approach in order:
            assignments.append({
                'assigned_run_id': f"first-pass-{index:02d}-{approach}",
                'order': len(assignments), 'recording_id': row['recording_id'],
                'sample_id': row['sample_id'], 'group_id': row['group_id'],
                'source_dataset': row['source_dataset'], 'label': row['label'],
                'approach': approach, 'repetition': 1, 'display_condition': 'foreground',
                'audio_sha256': row['audio_sha256'], 'script_sha256': row['script_sha256'],
            })
    return assignments


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recordings', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = args.recordings / 'audio_manifest.csv'
    with manifest.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    validate_provenance(args.recordings, rows)
    assignments = schedule(rows)
    output = {
        'scope': 'development first-pass assignments only; not execution approval',
        'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
        'order_rule': 'preserve manifest order; cyclically rotate latest/recent/accumulated by recording index',
        'execution_gates': ['official selected/final-evaluated bundle', 'verified audio/reference fidelity',
                            'owner-confirmed runtime configuration', 'combined feasibility approval'],
        'additional_repetitions': 'none assigned; owner nomination and a frozen repeat schedule required',
        'assignments': assignments,
    }
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(output, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'assigned_runs': len(assignments), 'launched_runs': 0}))


if __name__ == '__main__':
    main()
