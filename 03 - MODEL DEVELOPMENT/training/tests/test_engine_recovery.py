"""End-to-end synthetic tests for the training engine, with no pretrained weights."""
from __future__ import annotations

import copy
import csv
import hashlib
import json
import sys
import types
from collections import Counter
from pathlib import Path

import pytest
import torch
from transformers import XLMRobertaConfig, XLMRobertaForSequenceClassification

TRAINING_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TRAINING_DIR))
sys.path.insert(0, str(TRAINING_DIR.parent / "selection"))
import trainer


def _files(tmp_path, monkeypatch):
    input_dir = tmp_path / "fake-inputs"
    input_dir.mkdir()
    (input_dir / "inputs.py").write_text("# synthetic module identity\n")
    (input_dir / "token_length_report.json").write_text("{}\n")
    exports = tmp_path / "exports"
    exports.mkdir()
    (exports / "manifest.json").write_text("{}\n")
    input_config_path = tmp_path / "preprocessing.json"
    input_config_path.write_text('{"models":{}}\n')
    monkeypatch.setattr(trainer, "INPUT_DIR", input_dir)
    return input_dir, exports, input_config_path


def _config(tmp_path, monkeypatch, run_id, *, mode="comparative", epochs=3):
    _, exports, input_config = _files(tmp_path, monkeypatch)
    config = {
        "schema_version": 1, "run_id": run_id, "mode": mode,
        "approval": {"status": "owner_approved", "reference": "synthetic-owner-record",
            "approved_settings_sha256": "pending", "selection_protocol_approved": True,
            "selection_protocol_reference": "synthetic-03-01-protocol",
            "final_training_approval": mode == "final_training"},
        "model": "xlmr", "checkpoint": {"id": "synthetic-random", "revision": "local-only",
            "custom_code_revision": None},
        "data": {"condition": "primary_plus_supplemental"}, "fold": None if mode == "final_training" else 0,
        "training": {"representation": "whole_conversation", "marker_condition": "role_marked",
            "seed": 67, "epochs": epochs, "effective_batch_size": 16, "microbatch_size": 4,
            "accumulation_steps": 4, "optimizer_updates_limit": None},
        "validation": {"enabled": False} if mode == "final_training" else {
            "representation": "whole_conversation", "marker_conditions": ["role_marked", "role_free"]},
        "optimizer": {"name": "AdamW", "learning_rate": 2e-5, "weight_decay": 0.01,
            "beta1": 0.9, "beta2": 0.999, "epsilon": 1e-8, "gradient_clip_norm": 1.0},
        "schedule": {"name": "linear_warmup_then_constant", "warmup_updates": 0},
        "precision": {"mode": "fp32", "auto_policy_approved": False},
        "evaluation": {"scam_threshold": 0.5}, "selection": {"max_epochs": 4,
            "grid_configuration_id": "synthetic-grid", "selection_protocol_reference": "synthetic-03-01-protocol"},
        "runtime": {"device": "cpu", "local_files_only": True},
        "paths": {"data": str(tmp_path / "data"), "input_config": str(input_config),
            "input_exports": str(exports), "persistent_runs": str(tmp_path / "runs"),
            "persistent_storage_verified": True, "storage_verification_reference": "synthetic temp directory"},
    }
    if mode == "final_training":
        config["selection"].update({"final_candidate_approved": True,
            "selected_config_sha256": "a" * 64, "selection_report_sha256": "b" * 64,
            "warmup_conversion_reference": "synthetic-full-pool-warmup-rule"})
    config["approval"]["approved_settings_sha256"] = trainer.approved_settings_digest(config)
    return trainer.validate_config(config, require_diagnostic_approval=False)


def _rows(prefix, n=4, *, source_offset=0):
    sources = ("primary", "primary", "supplemental", "supplemental")
    return [{"sample_id": f"{prefix}-{i}", "source_dataset": sources[(i + source_offset) % 4],
        "label": i % 2, "split": "train", "inputs": {"input_ids": [1, 3 + i % 32, 8 + i % 32],
        "attention_mask": [1, 1, 1]}} for i in range(n)]


class SyntheticInputs:
    def __init__(self, train_ids):
        self.train_ids = set(train_ids)
        self.train_seen = []
        self.pad_calls = []
        self.cfg = {"assignments_sha256": "a" * 64,
                    "training_csv_sha256": "b" * 64}

    def load_config(self, path):
        return self.cfg

    def load_tokenizer(self, *args, **kwargs):
        return SyntheticTokenizer()

    def pad_batch(self, items, tokenizer):
        self.pad_calls.append([item["sample_id"] for item in items])
        self.train_seen.extend(item["sample_id"] for item in items if item["sample_id"] in self.train_ids)
        width = max(len(item["inputs"]["input_ids"]) for item in items)
        ids, masks = [], []
        for item in items:
            row = list(item["inputs"]["input_ids"])
            mask = list(item["inputs"]["attention_mask"])
            ids.append(row + [0] * (width - len(row)))
            masks.append(mask + [0] * (width - len(mask)))
        return {"inputs": {"input_ids": ids, "attention_mask": masks},
            "labels": [row["label"] for row in items],
            "sample_ids": [row["sample_id"] for row in items]}


class SyntheticTokenizer:
    def save_pretrained(self, folder):
        folder = Path(folder)
        (folder / "tokenizer_config.json").write_text("{}\n")
        (folder / "tokenizer.json").write_text("{}\n")


def _model_factory(*args, **kwargs):
    config = XLMRobertaConfig(vocab_size=128, max_position_embeddings=24,
        hidden_size=8, num_hidden_layers=1, num_attention_heads=2,
        intermediate_size=16, hidden_dropout_prob=0.25, attention_probs_dropout_prob=0.1,
        num_labels=2, id2label={0: "Not Scam", 1: "Scam"},
        label2id={"Not Scam": 0, "Scam": 1})
    return XLMRobertaForSequenceClassification(config)


def _install_synthetic_run(config, monkeypatch, *, validation_prefix="val", train_size=32):
    train = _rows("train", n=train_size)
    val_base = _rows(validation_prefix)
    val = {"role_marked": copy.deepcopy(val_base), "role_free": copy.deepcopy(val_base)}
    for i, item in enumerate(val["role_free"]):
        item["inputs"]["input_ids"][-1] += 1
    train_ids = {item["sample_id"] for item in train}
    fake_inputs = SyntheticInputs(train_ids)
    input_module = types.ModuleType("inputs")
    input_module.load_config = fake_inputs.load_config
    input_module.load_tokenizer = fake_inputs.load_tokenizer
    input_module.pad_batch = fake_inputs.pad_batch
    monkeypatch.setitem(sys.modules, "inputs", input_module)

    def records(*args):
        training_records = copy.deepcopy(train)
        validation_records = [] if config["mode"] == "final_training" else copy.deepcopy(val_base)
        return training_records, validation_records, copy.deepcopy(train), ({} if config["mode"] == "final_training" else copy.deepcopy(val)), fake_inputs.cfg, {
            "training_sample_ids": sorted(train_ids),
            "validation_sample_ids": [] if config["mode"] == "final_training" else sorted(item["sample_id"] for item in val_base)}

    monkeypatch.setattr(trainer, "get_records", records)
    monkeypatch.setattr(trainer, "build_model", _model_factory)
    monkeypatch.setattr(trainer, "verify_model_artifact", trainer.verify_model_artifact)
    return fake_inputs


def _load_checkpoint(run_dir):
    return torch.load(Path(run_dir) / "checkpoints/latest.pt", map_location="cpu", weights_only=False)


def _assert_tree_equal(left, right):
    if isinstance(left, torch.Tensor):
        assert isinstance(right, torch.Tensor)
        assert torch.equal(left, right)
    elif isinstance(left, dict):
        assert isinstance(right, dict) and left.keys() == right.keys()
        for key in left:
            _assert_tree_equal(left[key], right[key])
    elif isinstance(left, (list, tuple)):
        assert type(left) is type(right) and len(left) == len(right)
        for a, b in zip(left, right):
            _assert_tree_equal(a, b)
    else:
        assert left == right


def test_engine_interruption_persists_partial_observability_and_rejects_resume(tmp_path, monkeypatch):
    config = _config(tmp_path, monkeypatch, "synthetic-interrupted")
    config["schedule"]["warmup_updates"] = 2
    config["approval"]["approved_settings_sha256"] = trainer.approved_settings_digest(config)
    config = trainer.validate_config(config, require_diagnostic_approval=False)
    _install_synthetic_run(config, monkeypatch)
    real_train_group = trainer._train_group
    calls = {"count": 0}

    def interrupt_during_second_update(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 2:
            raise KeyboardInterrupt
        return real_train_group(*args, **kwargs)

    monkeypatch.setattr(trainer, "_train_group", interrupt_during_second_update)
    with pytest.raises(KeyboardInterrupt):
        trainer.run_training(copy.deepcopy(config))
    run_dir = Path(config["paths"]["persistent_runs"]) / config["run_id"]
    summary = json.loads((run_dir / "run_summary.json").read_text())
    assert summary["status"] == "interrupted"
    assert summary["optimizer_updates"] == 1
    assert summary["attempt_progress_log"]
    progress = [json.loads(line) for line in Path(summary["attempt_progress_log"]).read_text().splitlines()]
    assert len(progress) == 1 and progress[0]["optimizer_updates"] == 1
    assert progress[0]["learning_rate"] == pytest.approx(config["optimizer"]["learning_rate"] / 2)
    assert progress[0]["conversations_processed_in_epoch"] == 16
    assert progress[0]["resource_snapshot"]["process_peak_rss_bytes"] > 0
    partial_history = list(csv.DictReader(Path(summary["attempt_training_history"]).open(newline="")))
    assert any(row["status"] == "interrupted_partial_epoch" for row in partial_history)
    assert not list((run_dir / "checkpoints").glob("*.pt"))

    extended = copy.deepcopy(config)
    extended["training"]["epochs"] = 4
    extended["approval"]["approved_settings_sha256"] = trainer.approved_settings_digest(extended)
    with pytest.raises(ValueError, match="Failed or interrupted fits cannot be resumed"):
        trainer.run_training(extended, resume=True, extend_to_epoch=4)


def test_optimizer_progress_records_fraction_for_full_and_final_partial_groups(tmp_path, monkeypatch):
    config = _config(tmp_path, monkeypatch, "synthetic-fractional-progress")
    _install_synthetic_run(config, monkeypatch, train_size=30)

    run_dir = trainer.run_training(copy.deepcopy(config))
    attempt_state = next(run_dir.glob("attempt_evidence/*/attempt_state.json"))
    progress_path = Path(json.loads(attempt_state.read_text())["progress_log"])
    progress = [json.loads(line) for line in progress_path.read_text().splitlines()]
    assert [row["conversations_processed_in_epoch"] for row in progress] == [16, 30] * 3
    assert [row["epoch_progress_fraction"] for row in progress] == pytest.approx([16 / 30, 1.0] * 3)
    assert all(0.0 <= row["epoch_progress_fraction"] <= 1.0 for row in progress)


def test_attempt_state_json_writer_replaces_atomically_without_filesystem_fsync(tmp_path, monkeypatch):
    path = tmp_path / "attempt_state.json"
    monkeypatch.setattr(trainer.os, "fsync", lambda *_: (_ for _ in ()).throw(AssertionError("fsync must not be required")))
    trainer._atomic_write_json(path, {"status": "running", "target_epochs": 3})
    trainer._atomic_write_json(path, {"status": "completed", "target_epochs": 3})

    assert json.loads(path.read_text(encoding="utf-8")) == {"status": "completed", "target_epochs": 3}
    assert list(tmp_path.glob(".attempt_state.json.*.tmp")) == []


def test_engine_rejects_resume_when_attempt_summary_is_failed_before_mutating_files(tmp_path, monkeypatch):
    config = _config(tmp_path, monkeypatch, "synthetic-failed-no-resume")
    run_dir = Path(config["paths"]["persistent_runs"]) / config["run_id"]
    run_dir.mkdir(parents=True)
    (run_dir / "run_config.json").write_text(json.dumps(config), encoding="utf-8")
    summary_path = run_dir / "run_summary.json"
    summary_path.write_text(json.dumps({"run_id": config["run_id"], "status": "failed",
        "epochs_completed": 1, "failure_or_interruption": "synthetic"}), encoding="utf-8")
    before = {path.name: path.read_bytes() for path in run_dir.iterdir() if path.is_file()}
    extended = copy.deepcopy(config)
    extended["training"]["epochs"] = 4
    extended["approval"]["approved_settings_sha256"] = trainer.approved_settings_digest(extended)
    with pytest.raises(ValueError, match="Failed or interrupted fits cannot be resumed"):
        trainer.run_training(extended, resume=True, extend_to_epoch=4)
    assert {path.name: path.read_bytes() for path in run_dir.iterdir() if path.is_file()} == before


def test_engine_extension_preserves_old_history_and_fixed_warmup(tmp_path, monkeypatch):
    config = _config(tmp_path, monkeypatch, "synthetic-extension")
    _install_synthetic_run(config, monkeypatch)
    run_dir = trainer.run_training(copy.deepcopy(config))
    history_path = Path(run_dir) / "training_history.csv"
    with history_path.open(newline="", encoding="utf-8") as stream:
        before = list(csv.DictReader(stream))
    assert len(before) == 3 * 2
    assert all(row["checkpoint_reference"] and Path(row["checkpoint_reference"]).is_file() for row in before)
    prior_summary = json.loads((Path(run_dir) / "run_summary.json").read_text())
    extended = copy.deepcopy(config)
    extended["training"]["epochs"] = 4
    extended["approval"]["approved_settings_sha256"] = trainer.approved_settings_digest(extended)
    _install_synthetic_run(extended, monkeypatch)
    trainer.run_training(extended, resume=True, extend_to_epoch=4)
    with history_path.open(newline="", encoding="utf-8") as stream:
        after = list(csv.DictReader(stream))
    assert after[:len(before)] == before
    assert len(after) == 4 * 2
    extended_summary = json.loads((Path(run_dir) / "run_summary.json").read_text())
    assert extended_summary["attempt_elapsed_seconds"] > 0
    assert extended_summary["elapsed_seconds"] >= prior_summary["elapsed_seconds"] + extended_summary["attempt_elapsed_seconds"] - 0.02
    assert [float(row["elapsed_seconds"]) for row in after] == sorted(float(row["elapsed_seconds"]) for row in after)
    assert extended_summary["attempt_phase_durations_seconds"]["data_and_prepared_input_loading"] >= 0
    assert extended_summary["attempt_phase_durations_seconds"]["tokenizer_loading"] >= 0
    assert extended_summary["attempt_phase_durations_seconds"]["model_loading_and_checkpoint_restore"] >= 0
    run_config = json.loads((Path(run_dir) / "run_config.json").read_text())
    assert run_config["schedule"]["warmup_updates"] == 0
    assert run_config["epoch_extensions"] == [{
        "from_epoch_target": 3, "to_epoch_target": 4,
        "approval_reference": "synthetic-03-01-protocol",
        "prior_approved_settings_sha256": trainer.approved_settings_digest(config),
        "approved_settings_sha256": trainer.approved_settings_digest(extended)}]
    assert all(row["checkpoint_reference"] and Path(row["checkpoint_reference"]).is_file() for row in after)
    assert all(len(row["checkpoint_sha256"]) == 64 for row in after)


def test_extension_rejects_an_old_run_id_with_an_unfinished_target_attempt(tmp_path, monkeypatch):
    config = _config(tmp_path, monkeypatch, "synthetic-interrupted-extension")
    _install_synthetic_run(config, monkeypatch)
    run_dir = Path(trainer.run_training(copy.deepcopy(config)))
    attempt_state = run_dir / "attempt_evidence" / "abrupt-runtime" / "attempt_state.json"
    attempt_state.parent.mkdir(parents=True)
    attempt_state.write_text(json.dumps({"status": "running", "target_epochs": 4}), encoding="utf-8")

    extended = copy.deepcopy(config)
    extended["training"]["epochs"] = 4
    extended["approval"]["approved_settings_sha256"] = trainer.approved_settings_digest(extended)
    before = {path.name: path.read_bytes() for path in run_dir.iterdir() if path.is_file()}
    with pytest.raises(ValueError, match="epoch-extension attempt was interrupted"):
        trainer.run_training(extended, resume=True, extend_to_epoch=4)
    assert {path.name: path.read_bytes() for path in run_dir.iterdir() if path.is_file()} == before


def test_recovery_rotation_is_bounded_and_epoch_pruning_requires_frozen_five_fold_selection(tmp_path, monkeypatch):
    config = _config(tmp_path, monkeypatch, "synthetic-retention")
    _install_synthetic_run(config, monkeypatch)
    run_dir = Path(trainer.run_training(copy.deepcopy(config)))
    checkpoints = list((run_dir / "checkpoints").glob("*.pt"))
    assert {path.name for path in checkpoints} == {"latest.pt", "previous.pt"}
    snapshot_dir = run_dir / "epoch_models"
    assert {path.name for path in snapshot_dir.glob("*.safetensors")} == {
        "epoch-001.safetensors", "epoch-002.safetensors", "epoch-003.safetensors"}
    history_path = run_dir / "training_history.csv"
    predictions_path = run_dir / "validation_predictions.csv"
    history_before, predictions_before = history_path.read_bytes(), predictions_path.read_bytes()
    run_cfg_path = run_dir / "run_config.json"
    run_cfg_digest = hashlib.sha256(run_cfg_path.read_bytes()).hexdigest()
    selected = {"status": "frozen_by_human_approval", "configuration_id": "xlmr__combined__lr-2e-5",
        "model_key": "xlmr", "data_condition": "primary_plus_supplemental", "learning_rate": 2e-5,
        "selected_duration_epochs": 2, "training_representation": "whole_conversation",
        "training_marker_condition": "role_marked", "inference_representation": "whole_conversation",
        "inference_marker_condition": "role_free", "threshold": 0.5,
        "selection_artifacts": {"selected_cv_runs": [
            {"run_id": "synthetic-retention", "fold": 0, "run_config_sha256": run_cfg_digest},
            *[{"run_id": f"synthetic-fold-{fold}", "fold": fold, "run_config_sha256": str(fold) * 64}
              for fold in range(1, 5)]]}}
    selected_path = tmp_path / "selected_config.json"
    selected_path.write_text(json.dumps(selected))
    ledger = trainer.prune_epoch_model_snapshots(run_dir, selected_path)
    assert ledger["selected_duration_epochs"] == 2
    assert len(ledger["pruned_snapshots"]) == 2
    assert {path.name for path in snapshot_dir.glob("*.safetensors")} == {"epoch-002.safetensors"}
    assert history_path.read_bytes() == history_before
    assert predictions_path.read_bytes() == predictions_before
    assert {path.name for path in (run_dir / "checkpoints").glob("*.pt")} == {"latest.pt", "previous.pt"}
    assert len(ledger["retained_snapshot"]["sha256"]) == 64
    # Interrupted pruning can be safely replayed from its checksum ledger.
    assert trainer.prune_epoch_model_snapshots(run_dir, selected_path) == ledger


def test_epoch_snapshot_pruning_rejects_unfrozen_selection(tmp_path, monkeypatch):
    config = _config(tmp_path, monkeypatch, "synthetic-retention-gate")
    _install_synthetic_run(config, monkeypatch)
    run_dir = Path(trainer.run_training(copy.deepcopy(config)))
    selected_path = tmp_path / "unfrozen.json"
    selected_path.write_text(json.dumps({"status": "draft"}))
    with pytest.raises(ValueError, match="human-frozen"):
        trainer.prune_epoch_model_snapshots(run_dir, selected_path)
    assert len(list((run_dir / "epoch_models").glob("*.safetensors"))) == 3


def test_engine_load_failure_is_summarized_without_losing_existing_evidence(tmp_path, monkeypatch):
    config = _config(tmp_path, monkeypatch, "synthetic-load-failure")
    _install_synthetic_run(config, monkeypatch)
    monkeypatch.setattr(trainer, "build_model", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("synthetic load failure")))
    with pytest.raises(RuntimeError, match="synthetic load failure"):
        trainer.run_training(config)
    run_dir = Path(config["paths"]["persistent_runs"]) / config["run_id"]
    summary = json.loads((run_dir / "run_summary.json").read_text())
    assert summary["status"] == "failed"
    assert "synthetic load failure" in summary["failure_or_interruption"]
    original = {"run_id": config["run_id"], "status": "completed", "marker": "keep"}
    (run_dir / "run_summary.json").write_text(json.dumps(original))
    with pytest.raises(FileExistsError):
        trainer.run_training(config)
    assert json.loads((run_dir / "run_summary.json").read_text()) == original
    failures = (run_dir / "attempt_failures.jsonl").read_text().splitlines()
    assert len(failures) >= 2


def test_bad_extension_checkpoint_does_not_rewrite_run_config(tmp_path, monkeypatch):
    config = _config(tmp_path, monkeypatch, "synthetic-bad-extension")
    _install_synthetic_run(config, monkeypatch)
    run_dir = Path(trainer.run_training(copy.deepcopy(config)))
    config_path = run_dir / "run_config.json"
    original_bytes = config_path.read_bytes()
    prior_summary = json.loads((run_dir / "run_summary.json").read_text())
    checkpoint_path = run_dir / "checkpoints/latest.pt"
    state = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    state["run_identity"] = "wrong-checkpoint-identity"
    torch.save(state, checkpoint_path)
    extended = copy.deepcopy(config)
    extended["training"]["epochs"] = 4
    extended["approval"]["approved_settings_sha256"] = trainer.approved_settings_digest(extended)
    with pytest.raises(ValueError, match="verified checkpoint at the last completed target"):
        trainer.run_training(extended, resume=True, extend_to_epoch=4)
    assert config_path.read_bytes() == original_bytes
    failed_summary = json.loads((run_dir / "run_summary.json").read_text())
    assert failed_summary["status"] == "failed"
    assert failed_summary["attempt_elapsed_seconds"] > 0
    assert failed_summary["elapsed_seconds"] >= prior_summary["elapsed_seconds"] + failed_summary["attempt_elapsed_seconds"] - 0.02


def test_per_configuration_pruning_verifies_fivefold_cv_evidence(tmp_path, monkeypatch):
    from selection import PREDICTION_FIELDS

    configuration_id = "xlmr__primary_plus_supplemental__lr-2e-05"
    manifest_rows = []
    run_dirs = []
    for fold in range(5):
        fold_root = tmp_path / f"fold-{fold}"
        fold_root.mkdir()
        config = _config(fold_root, monkeypatch, f"synthetic-cv-{fold}")
        config["fold"] = fold
        shared_data = tmp_path / "authoritative-data"
        config["paths"]["data"] = str(shared_data)
        config["selection"]["max_epochs"] = 3
        config["selection"]["grid_configuration_id"] = configuration_id
        config["approval"]["approved_settings_sha256"] = trainer.approved_settings_digest(config)
        _install_synthetic_run(config, monkeypatch, validation_prefix=f"val{fold}")
        run_dir = Path(trainer.run_training(config))
        run_dirs.append(run_dir)
        manifest_rows.append({"run_id": config["run_id"], "configuration_id": configuration_id,
            "model_key": config["model"], "data_condition": config["data"]["condition"],
            "training_representation": "whole_conversation", "fold": fold,
            "learning_rate": config["optimizer"]["learning_rate"],
            "execution_state": "completed", "artifact_location": str(run_dir)})

    prediction_fields = [*PREDICTION_FIELDS, "evaluation_point", "learning_rate"]
    prediction_rows = []
    for fold, config in enumerate([json.loads((path / "run_config.json").read_text()) for path in run_dirs]):
        for epoch in range(1, 4):
            for marker in ("role_free", "role_marked"):
                for index, (sample_id, label, source) in enumerate((
                    (f"val{fold}-0", 0, "primary"), (f"val{fold}-1", 1, "primary"),
                    (f"val{fold}-2", 0, "supplemental"), (f"val{fold}-3", 1, "supplemental"),
                )):
                    # Make epoch 2 the best role-free epoch; role-marked is paired
                    # and complete at every epoch as required by the selection plan.
                    positive = (label == 1)
                    correct = marker == "role_marked" or epoch == 2
                    confidence = 0.9 if correct else 0.1
                    p_scam = confidence if positive else 1.0 - confidence
                    prediction_rows.append({"run_id": config["run_id"],
                        "configuration_id": configuration_id, "run_configuration_id": config["configuration_id"],
                        "model_key": "xlmr", "data_condition": "primary_plus_supplemental",
                        "training_representation": "whole_conversation", "training_marker_condition": "role_marked",
                        "validation_representation": "whole_conversation", "validation_marker_condition": marker,
                        "fold": fold, "epoch": epoch, "sample_id": sample_id, "source_dataset": source,
                        "true_label": "Scam" if label else "Not Scam", "p_not_scam": 1.0-p_scam, "p_scam": p_scam,
                        "prediction_state": "success", "failure_reason": "", "elapsed_seconds": 0.1,
                        "evaluation_point": "epoch_end", "learning_rate": 2e-5})

    predictions_path = tmp_path / "normalized_predictions.csv"
    with predictions_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=prediction_fields)
        writer.writeheader(); writer.writerows(prediction_rows)
    manifest_path = tmp_path / "experiment_manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(manifest_rows[0]))
        writer.writeheader(); writer.writerows(manifest_rows)
    data_root = tmp_path / "authoritative-data"
    (data_root / "0 - train").mkdir(parents=True)
    assignments, canonical = [], []
    for fold in range(5):
        for index, (label, source) in enumerate((("Not Scam", "primary"), ("Scam", "primary"),
                                                   ("Not Scam", "supplemental"), ("Scam", "supplemental"))):
            sample_id = f"val{fold}-{index}"
            assignments.append({"sample_id": sample_id, "split": "train", "cv_fold": fold,
                                "source_dataset": source})
            canonical.append({"sample_id": sample_id, "source_dataset": source, "label": label})
    with (data_root / "split_assignments.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(assignments[0]))
        writer.writeheader(); writer.writerows(assignments)
    with (data_root / "0 - train/dataset.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(canonical[0]))
        writer.writeheader(); writer.writerows(canonical)
    import argparse
    import runtime as selection
    results_path = tmp_path / "cv_results.csv"
    selection.aggregate(argparse.Namespace(predictions=str(predictions_path), output=str(results_path)))
    evidence = {"schema_version": 1, "cv_results_path": str(results_path),
        "cv_results_sha256": hashlib.sha256(results_path.read_bytes()).hexdigest(),
        "normalized_predictions_path": str(predictions_path),
        "normalized_predictions_sha256": hashlib.sha256(predictions_path.read_bytes()).hexdigest(),
        "experiment_manifest_path": str(manifest_path),
        "experiment_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "selection_protocol_reference": "synthetic-03-01-protocol"}

    # Neither an incomplete epoch budget nor a failed/incomplete attempt may
    # trigger deletion of run-state checkpoints (or model snapshots).
    first_summary_path = run_dirs[0] / "run_summary.json"
    first_summary_bytes = first_summary_path.read_bytes()
    first_summary = json.loads(first_summary_bytes)
    first_summary["epochs_completed"] = 2
    first_summary_path.write_text(json.dumps(first_summary))
    with pytest.raises(ValueError, match="full approved epoch budget"):
        trainer.prune_epoch_model_snapshots_for_cv_run(run_dirs[0], evidence, configuration_id)
    first_summary_path.write_bytes(first_summary_bytes)

    failed_attempt = run_dirs[1] / "attempt_evidence" / "synthetic-failed-attempt" / "attempt_state.json"
    failed_attempt.parent.mkdir(parents=True)
    failed_attempt.write_text(json.dumps({"run_id": "synthetic-cv-1", "attempt_id": "synthetic-failed-attempt",
        "status": "failed", "target_epochs": 3, "last_completed_epoch": 2}))
    with pytest.raises(ValueError, match="failed or incomplete attempt"):
        trainer.prune_epoch_model_snapshots_for_cv_run(run_dirs[0], evidence, configuration_id)
    failed_attempt.unlink()
    failed_attempt.parent.rmdir()

    # A failed startup invocation is logged separately and may not appear in
    # attempt_state.json or run_attempts.jsonl. It still blocks pruning.
    startup_failures = run_dirs[1] / "attempt_failures.jsonl"
    startup_failures.write_text(json.dumps({"status": "failed", "reason": "synthetic startup failure"}) + "\n")
    with pytest.raises(ValueError, match="failed startup invocation"):
        trainer.prune_epoch_model_snapshots_for_cv_run(run_dirs[0], evidence, configuration_id)
    startup_failures.unlink()

    for run_dir in run_dirs:
        assert {path.name for path in (run_dir / "checkpoints").glob("*.pt")} == {"latest.pt", "previous.pt"}
        assert len(list((run_dir / "epoch_models").glob("*.safetensors"))) == 3

    first_predictions = run_dirs[0] / "validation_predictions.csv"
    original_prediction_bytes = first_predictions.read_bytes()
    first_predictions.write_bytes(original_prediction_bytes + b"\n")
    with pytest.raises(ValueError, match="artifact checksum mismatch"):
        trainer.prune_epoch_model_snapshots_for_cv_run(run_dirs[0], evidence, configuration_id)
    assert len(list((run_dirs[0] / "epoch_models").glob("*.safetensors"))) == 3
    first_predictions.write_bytes(original_prediction_bytes)

    for run_dir in run_dirs:
        ledger = trainer.prune_epoch_model_snapshots_for_cv_run(run_dir, evidence, configuration_id)
        assert ledger["selected_duration_epochs"] == 2
        assert {path.name for path in (run_dir / "epoch_models").glob("*.safetensors")} == {"epoch-002.safetensors"}
        assert not list((run_dir / "checkpoints").glob("*.pt"))
        assert {Path(item["path"]).name for item in ledger["pruned_recovery_checkpoints"]} == {"latest.pt", "previous.pt"}
        assert all(len(item["sha256"]) == 64 and item["size_bytes"] > 0
                   for item in ledger["pruned_recovery_checkpoints"])
        assert len(ledger["pruner_checkpoint_inventory"]) == 10
        assert ledger["cv_results"]["sha256"] == evidence["cv_results_sha256"]
        assert ledger["normalized_predictions"]["sha256"] == evidence["normalized_predictions_sha256"]
        assert ledger["experiment_manifest"]["sha256"] == evidence["experiment_manifest_sha256"]
        history_before = (run_dir / "training_history.csv").read_bytes()
        assert trainer.prune_epoch_model_snapshots_for_cv_run(run_dir, evidence, configuration_id) == ledger
        assert (run_dir / "training_history.csv").read_bytes() == history_before


def test_final_training_has_no_validation_and_exports_exact_last_state(tmp_path, monkeypatch):
    config = _config(tmp_path, monkeypatch, "synthetic-final", mode="final_training", epochs=3)
    _install_synthetic_run(config, monkeypatch)
    run_dir = trainer.run_training(config)
    run_dir = Path(run_dir)
    checkpoint = _load_checkpoint(run_dir)
    assert checkpoint["epoch"] == 3 and checkpoint["epoch_complete"]
    assert checkpoint["optimizer_updates"] == 6
    assert checkpoint["predictions"] == [] and checkpoint["history"]
    assert all(row["validation_marker_condition"] == "unavailable" and row["validation_loss"] is None
               for row in checkpoint["history"])
    artifact = run_dir / "final_model"
    manifest = trainer.verify_model_artifact(artifact)
    assert manifest["run_id"] == config["run_id"]
    assert manifest["training_seed"] == config["training"]["seed"]
    from safetensors.torch import load_file
    exported = load_file(str(artifact / "model.safetensors"))
    for name, expected in checkpoint["model"].items():
        assert torch.equal(exported[name], expected.cpu()), name
    summary = json.loads((run_dir / "run_summary.json").read_text())
    assert summary["status"] == "completed"
    assert summary["inference_artifact"] == str(artifact)
