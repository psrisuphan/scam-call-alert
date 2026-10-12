"""Inference must not require a local copy of training or test datasets."""
import importlib.util
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "evaluation.py"
spec = importlib.util.spec_from_file_location("frozen_warmup_evaluation", MODULE)
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)
import trainer


def frozen_config():
    ids = [f"primary-{i:04}" for i in range(1021)]
    return {"paths": {"data": "/nonexistent/original/Colab/dataset"},
        "identities": {"training_sample_ids": ids, "training_membership_sha256": trainer.canonical_hash(ids)}}


def selected():
    return {"training_settings": {"training": {"effective_batch_size": 16}},
        "selected_duration_epochs": 2, "warmup_rule": {"fraction": .1, "rounding": "ceil"}}


def test_frozen_membership_gives_three_epoch_horizon_without_dataset_access(monkeypatch):
    monkeypatch.setattr(evaluation, "read_csv", lambda *a: pytest.fail("Deployment read a dataset"))
    assert evaluation.expected_frozen_training_warmup(selected(), frozen_config()) == 20


@pytest.mark.parametrize("change", ["missing", "duplicates", "unsorted", "changed_hash", "non_string"])
def test_missing_or_tampered_membership_is_rejected(change):
    config = frozen_config()
    ids = config["identities"]["training_sample_ids"]
    if change == "missing":
        config["identities"].pop("training_sample_ids")
    elif change == "duplicates":
        ids.append(ids[0])
    elif change == "unsorted":
        ids.reverse()
    elif change == "changed_hash":
        config["identities"]["training_membership_sha256"] = "wrong"
    else:
        ids[0] = 1
    with pytest.raises(ValueError):
        evaluation.expected_frozen_training_warmup(selected(), config)
