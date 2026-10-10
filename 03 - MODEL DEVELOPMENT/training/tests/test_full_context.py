import importlib.util
import hashlib
import json
import csv
from pathlib import Path
import sys

import pytest

INPUT_DIR = Path(__file__).resolve().parents[2] / "input-preparation"
MODULE = Path(__file__).resolve().parents[1] / "full_context.py"
sys.path.insert(0, str(INPUT_DIR))
import inputs
sys.path.insert(0, str(MODULE.parent))
import trainer
from create_approved_diagnostics import create as create_diagnostic_configs

spec = importlib.util.spec_from_file_location("full_context_under_test", MODULE)
full_context = importlib.util.module_from_spec(spec)
spec.loader.exec_module(full_context)


@pytest.mark.parametrize("length,expected", [(1, [1]), (508, [508]), (509, [508, 128]),
    (889, [508, 508]), (890, [508, 508, 128]), (1200, [508, 508, 438])])
def test_windows_preserve_full_order_and_expected_overlap(length, expected):
    tokens = list(range(length))
    windows = full_context.make_windows(tokens)
    assert [len(window) for window in windows] == expected
    assert windows[0][0] == 0
    assert windows[-1][-1] == length - 1
    assert all(windows[index][-1] >= windows[index + 1][0]
               for index in range(len(windows) - 1))


def test_window_policy_handles_empty_input_as_one_special_token_window():
    assert full_context.make_windows([]) == [[]]


def test_pooling_aggregates_classwise_logits_and_retains_gradient():
    torch = pytest.importorskip("torch")
    logits = torch.tensor([[1.0, 2.0], [3.0, 0.0], [4.0, 2.0]], requires_grad=True)
    pooled_max = full_context.pool_logits(logits, [0, 0, 1], 2, "max")
    pooled_mean = full_context.pool_logits(logits, [0, 0, 1], 2, "mean")
    assert pooled_max.tolist() == [[3.0, 2.0], [4.0, 2.0]]
    assert pooled_mean.tolist() == [[2.0, 1.0], [4.0, 2.0]]
    pooled_mean.sum().backward()
    assert logits.grad is not None


def test_rejects_invalid_window_ownership_and_pooling():
    torch = pytest.importorskip("torch")
    with pytest.raises(ValueError):
        full_context.pool_logits(torch.zeros((2, 2)), [0], 1, "mean")
    with pytest.raises(ValueError):
        full_context.pool_logits(torch.zeros((2, 2)), [0, 0], 1, "median")


def test_full_context_manifest_verifier_checks_prepared_identities(tmp_path):
    config = {"training_csv_sha256": "a" * 64, "assignments_sha256": "b" * 64,
              "models": {"wangchanberta": {"checkpoint": "pinned"}}, "dependencies": {}}
    config_digest = hashlib.sha256((json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode()).hexdigest()
    manifest = {"configuration_sha256": config_digest,
        "component_sha256": hashlib.sha256(Path(inputs.__file__).read_bytes()).hexdigest(),
        "training_csv_sha256": config["training_csv_sha256"],
        "assignments_sha256": config["assignments_sha256"],
        "export_script_sha256": hashlib.sha256((INPUT_DIR / "scripts/8.export_inputs.py").read_bytes()).hexdigest(),
        "models": config["models"], "dependencies": config["dependencies"]}
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert full_context.verify_prepared_manifest(config, inputs, tmp_path) == manifest

    for field, bad_value in (("configuration_sha256", "0" * 64),
                             ("component_sha256", "0" * 64),
                             ("training_csv_sha256", "0" * 64),
                             ("assignments_sha256", "0" * 64),
                             ("export_script_sha256", "0" * 64)):
        changed = dict(manifest, **{field: bad_value})
        manifest_path.write_text(json.dumps(changed), encoding="utf-8")
        with pytest.raises(ValueError, match="Stale prepared manifest"):
            full_context.verify_prepared_manifest(config, inputs, tmp_path)

    for field in ("models", "dependencies"):
        changed = dict(manifest, **{field: {"unexpected": "identity"}})
        manifest_path.write_text(json.dumps(changed), encoding="utf-8")
        with pytest.raises(ValueError, match="Prepared tokenizer/dependency"):
            full_context.verify_prepared_manifest(config, inputs, tmp_path)


def test_full_context_manifest_matches_frozen_committed_inputs_component(monkeypatch):
    prepared = INPUT_DIR / "prepared"
    config = inputs.load_config()
    manifest = json.loads((prepared / "manifest.json").read_text(encoding="utf-8"))
    component_sha256 = hashlib.sha256(Path(inputs.__file__).read_bytes()).hexdigest()
    assert component_sha256 == "50d8707a38b4b8e9a09f808158cb3b330618fd13eb4402a08a29e6413169be5e"
    assert component_sha256 == manifest["component_sha256"]

    import importlib.metadata
    monkeypatch.setattr(importlib.metadata, "version", lambda package: config["dependencies"][package])
    assert full_context.verify_prepared_manifest(config, inputs, prepared) == manifest


def test_full_text_loader_checks_manifest_hash_columns_and_fold_membership(tmp_path):
    class FakeTokenizer:
        _scam_checkpoint_identity = ("checkpoint", "revision")

        def num_special_tokens_to_add(self):
            return 2

        def build_inputs_with_special_tokens(self, ids):
            return [101, *ids, 102]

        def __call__(self, text, **kwargs):
            assert kwargs["truncation"] is False
            ids = list(range(1, len(text.split()) + 1))
            return {"input_ids": ids}

    class FakeInputModule:
        __file__ = inputs.__file__
        DEFAULT_CONFIG = inputs.DEFAULT_CONFIG

        @staticmethod
        def checkpoint_prepare_text(text, model, config):
            return text

    input_config = {
        "training_csv_sha256": "a" * 64,
        "assignments_sha256": "b" * 64,
        "dependencies": {},
        "models": {"wangchanberta": {"checkpoint": "checkpoint", "revision": "revision",
            "special_tokens_count": 2, "verified_config_limit": 510}},
    }
    rows = [{"sample_id": "synthetic-1", "source_dataset": "primary", "label": "Scam",
        "cv_fold": "3", "whole_conversation.role_marked": "marked token text",
        "whole_conversation.role_free": "free token"}]
    text_path = tmp_path / "training_text.csv"
    with text_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    config_hash = hashlib.sha256((json.dumps(input_config, ensure_ascii=False, indent=2) + "\n").encode()).hexdigest()
    manifest = {"configuration_sha256": config_hash,
        "component_sha256": hashlib.sha256(Path(inputs.__file__).read_bytes()).hexdigest(),
        "training_csv_sha256": input_config["training_csv_sha256"],
        "assignments_sha256": input_config["assignments_sha256"],
        "export_script_sha256": hashlib.sha256((INPUT_DIR / "scripts/8.export_inputs.py").read_bytes()).hexdigest(),
        "models": input_config["models"], "dependencies": input_config["dependencies"],
        "files": {"training_text.csv": {"sha256": hashlib.sha256(text_path.read_bytes()).hexdigest()}}}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    record = {"sample_id": "synthetic-1", "source_dataset": "primary", "label": "Scam"}
    tokenizer = FakeTokenizer()
    marked, _ = full_context.load_full_text_inputs([record], model="wangchanberta",
        representation="whole_conversation", marker_condition="role_marked", fold=2,
        input_config=input_config, input_dir=tmp_path, tokenizer=tokenizer,
        input_module=FakeInputModule)
    role_free, _ = full_context.load_full_text_inputs([record], model="wangchanberta",
        representation="whole_conversation", marker_condition="role_free", fold=3,
        input_config=input_config, input_dir=tmp_path, tokenizer=tokenizer,
        input_module=FakeInputModule, validation=True)
    assert marked[0]["chunk_count"] == 1 and marked[0]["label"] == 1
    assert marked[0]["windows"][0]["input_ids"] == [101, 1, 2, 3, 102]
    assert role_free[0]["windows"][0]["input_ids"] == [101, 1, 2, 102]
    with pytest.raises(ValueError, match="source/label/fold mismatch"):
        full_context.load_full_text_inputs([dict(record, source_dataset="supplemental")],
            model="wangchanberta", representation="whole_conversation", marker_condition="role_marked",
            fold=2, input_config=input_config, input_dir=tmp_path, tokenizer=tokenizer,
            input_module=FakeInputModule)
    with pytest.raises(ValueError, match="source/label/fold mismatch"):
        full_context.load_full_text_inputs([dict(record, label="Not Scam")],
            model="wangchanberta", representation="whole_conversation", marker_condition="role_marked",
            fold=2, input_config=input_config, input_dir=tmp_path, tokenizer=tokenizer,
            input_module=FakeInputModule)
    with pytest.raises(ValueError, match="Missing full training text"):
        full_context.load_full_text_inputs([dict(record, sample_id="synthetic-missing")],
            model="wangchanberta", representation="whole_conversation", marker_condition="role_marked",
            fold=2, input_config=input_config, input_dir=tmp_path, tokenizer=tokenizer,
            input_module=FakeInputModule)
    with pytest.raises(ValueError, match="source/label/fold mismatch"):
        full_context.load_full_text_inputs([record], model="wangchanberta",
            representation="whole_conversation", marker_condition="role_marked", fold=2,
            input_config=input_config, input_dir=tmp_path, tokenizer=tokenizer,
            input_module=FakeInputModule, validation=True)
    manifest["configuration_sha256"] = "0" * 64
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="Stale prepared manifest"):
        full_context.load_full_text_inputs([record], model="wangchanberta",
            representation="whole_conversation", marker_condition="role_marked", fold=2,
            input_config=input_config, input_dir=tmp_path, tokenizer=tokenizer,
            input_module=FakeInputModule)


def test_full_context_requires_explicit_gradient_checkpointing_setting(tmp_path):
    paths = create_diagnostic_configs(tmp_path / "configs", tmp_path / "runs", 8,
        "cuda", "TEST ONLY: temporary config fixture")
    config = next(json.loads(path.read_text()) for path in paths
                  if json.loads(path.read_text()).get("model") == "wangchanberta")
    config["training"]["window_policy"] = "wangchan_full_context_v1"
    config["training"]["pooling_method"] = "max"
    config["approval"]["approved_settings_sha256"] = trainer.approved_settings_digest(config)
    with pytest.raises(ValueError, match="training.gradient_checkpointing"):
        trainer.validate_config(config)

    config["training"]["gradient_checkpointing"] = False
    config["approval"]["approved_settings_sha256"] = trainer.approved_settings_digest(config)
    assert trainer.validate_config(config)["training"]["gradient_checkpointing"] is False
