"""Owner-gated pruning of unselected CV epoch model snapshots."""
import argparse
from pathlib import Path

from trainer import prune_epoch_model_snapshots


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--selected-config", required=True, type=Path)
    args = parser.parse_args(argv)
    ledger = prune_epoch_model_snapshots(args.run_dir, args.selected_config)
    print(f"Recorded epoch-snapshot pruning: {Path(args.run_dir) / 'epoch_snapshot_pruning.json'}")
    print(f"Retained selected epoch {ledger['selected_duration_epochs']} and latest/previous recovery checkpoints.")


if __name__ == "__main__":
    main()
