"""Synthetic checks for training safety/math; never loads pretrained weights."""
import copy
import json
import pickle
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import trainer
sys.path.insert(0, str(HERE / "tests"))
from config_factory import make_config


class TinyTokenizer:
    def pad(self, inputs, padding, return_tensors):
        import torch
        return {key: torch.tensor([item[key] for item in inputs], dtype=torch.float32)
                for key in inputs[0]}


class TinyInputModule:
    @staticmethod
    def pad_batch(items, tokenizer):
        padded = tokenizer.pad([item["inputs"] for item in items], padding="longest", return_tensors="pt")
        padded = {key: value.float() if key == "input_ids" else value for key, value in padded.items()}
        return {"inputs": padded, "labels": [item["label"] for item in items],
                "sample_ids": [item["sample_id"] for item in items]}


class TinyModel:
    def __init__(self, torch):
        self.layer = torch.nn.Linear(2, 2, bias=True)

    def __call__(self, input_ids, attention_mask):
        from types import SimpleNamespace
        return SimpleNamespace(logits=self.layer(input_ids))

    def parameters(self):
        return self.layer.parameters()


class FakeTorchSerialization:
    """Small serialization double for recovery-rotation tests without PyTorch."""
    @staticmethod
    def is_tensor(_value):
        return False

    @staticmethod
    def save(payload, path):
        with Path(path).open("wb") as stream:
            pickle.dump(payload, stream)

    @staticmethod
    def load(path, **_kwargs):
        with Path(path).open("rb") as stream:
            return pickle.load(stream)


class StateLoadDouble:
    def __init__(self):
        self.loaded = None
        self.load_calls = 0

    def load_state_dict(self, value):
        self.loaded = copy.deepcopy(value)
        self.load_calls += 1

    def state_dict(self):
        return copy.deepcopy(self.loaded)


class TrainerChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_template_is_not_runnable(self):
        with self.assertRaises(ValueError):
            trainer.load_config(trainer.CONFIG_TEMPLATE)

    def test_actual_training_only_retrieval_and_paired_validation(self):
        config = trainer.validate_config(make_config(self.root), require_diagnostic_approval=False)
        sys.path.insert(0, str(ROOT / "03 - MODEL DEVELOPMENT/input-preparation"))
        import inputs
        training_records, validation_records, train, validation, _, membership = trainer.get_records(config, inputs)
        self.assertEqual(len(train), len(membership["training_sample_ids"]))
        self.assertTrue(all(item["source_dataset"] == "primary" for item in train))
        self.assertEqual(set(validation), {"role_marked", "role_free"})
        self.assertEqual(len(validation["role_marked"]), len(validation_records))
        self.assertEqual(len(validation["role_free"]), len(validation_records))
        self.assertEqual(len(membership["training_sample_ids"]), len(train))
        self.assertFalse(set(membership["training_sample_ids"]) & set(membership["validation_sample_ids"]))
        self.assertTrue(all(item["split"] == "train" for item in train))

    def test_actual_conversation_weighted_accumulation_matches_full_batch(self):
        import torch
        from torch.nn.utils import clip_grad_norm_
        from torch.nn import functional as F

        torch.manual_seed(4)
        accumulated = TinyModel(torch)
        full = TinyModel(torch)
        full.layer.load_state_dict(copy.deepcopy(accumulated.layer.state_dict()))
        rows = [
            {"inputs": {"input_ids": [0.2, 0.7], "attention_mask": [1, 1]}, "label": 0,
             "sample_id": "a", "source_dataset": "primary"},
            {"inputs": {"input_ids": [0.9, -0.3], "attention_mask": [1, 1]}, "label": 1,
             "sample_id": "b", "source_dataset": "primary"},
            {"inputs": {"input_ids": [-0.5, 0.4], "attention_mask": [1, 1]}, "label": 1,
             "sample_id": "c", "source_dataset": "supplemental"},
        ]
        opt_acc = torch.optim.SGD(accumulated.parameters(), lr=0.05)
        opt_full = torch.optim.SGD(full.parameters(), lr=0.05)
        opt_acc.zero_grad(set_to_none=True)
        trainer._train_group([[rows[0]], rows[1:]], TinyTokenizer(), accumulated, opt_acc,
            torch.amp.GradScaler("cpu", enabled=False), torch, F, torch.device("cpu"), "fp32",
            clip_grad_norm_, 1000.0, 3, input_module=TinyInputModule)
        batch = trainer.pad_collate(rows, TinyTokenizer(), torch, TinyInputModule)
        x = torch.tensor([row["inputs"]["input_ids"] for row in rows], dtype=torch.float32)
        y = torch.tensor([row["label"] for row in rows], dtype=torch.long)
        F.cross_entropy(full.layer(x), y).backward()
        opt_full.step()
        for left, right in zip(accumulated.parameters(), full.parameters()):
            torch.testing.assert_close(left, right, rtol=1e-6, atol=1e-7)

    def test_checkpoint_is_verified_before_latest_replacement(self):
        torch = FakeTorchSerialization
        payload = {"run_identity": "synthetic", "epoch": 1, "optimizer_updates": 3}
        path = trainer.save_recovery(self.root / "run", payload, torch)
        self.assertTrue(Path(path).is_file())
        latest = torch.load(self.root / "run/checkpoints/latest.pt", map_location="cpu", weights_only=False)
        self.assertEqual(latest["run_identity"], "synthetic")
        self.assertEqual(latest["optimizer_updates"], 3)

    def test_failed_final_latest_verification_restores_latest_and_preserves_previous(self):
        from unittest.mock import patch
        torch = FakeTorchSerialization

        run_dir = self.root / "run"
        trainer.save_recovery(run_dir, {"run_identity": "synthetic", "epoch": 1,
            "optimizer_updates": 1}, torch)
        trainer.save_recovery(run_dir, {"run_identity": "synthetic", "epoch": 2,
            "optimizer_updates": 2}, torch)
        latest_path = run_dir / "checkpoints/latest.pt"
        previous_path = run_dir / "checkpoints/previous.pt"
        latest_before = latest_path.read_bytes()
        previous_before = previous_path.read_bytes()
        real_load = torch.load

        def fail_only_for_published_candidate(file, *args, **kwargs):
            loaded = real_load(file, **kwargs)
            if (Path(file) == latest_path
                    and loaded.get("optimizer_updates") == 3):
                raise RuntimeError("simulated unreadable final destination")
            return loaded

        with patch.object(torch, "load", side_effect=fail_only_for_published_candidate):
            with self.assertRaisesRegex(RuntimeError, "simulated unreadable final destination"):
                trainer.save_recovery(run_dir, {"run_identity": "synthetic", "epoch": 3,
                    "optimizer_updates": 3}, torch)

        self.assertEqual(latest_path.read_bytes(), latest_before)
        self.assertEqual(previous_path.read_bytes(), previous_before)
        self.assertEqual(real_load(latest_path, map_location="cpu", weights_only=False)["optimizer_updates"], 2)
        self.assertEqual(real_load(previous_path, map_location="cpu", weights_only=False)["optimizer_updates"], 1)

    def test_corrupt_latest_does_not_replace_valid_previous_checkpoint(self):
        torch = FakeTorchSerialization

        run_dir = self.root / "run"
        trainer.save_recovery(run_dir, {"run_identity": "synthetic", "epoch": 1,
            "optimizer_updates": 1}, torch)
        trainer.save_recovery(run_dir, {"run_identity": "synthetic", "epoch": 2,
            "optimizer_updates": 2}, torch)
        latest_path = run_dir / "checkpoints/latest.pt"
        previous_path = run_dir / "checkpoints/previous.pt"
        previous_before = previous_path.read_bytes()
        latest_path.write_bytes(b"not a torch archive")

        trainer.save_recovery(run_dir, {"run_identity": "synthetic", "epoch": 3,
            "optimizer_updates": 3}, torch)

        self.assertEqual(previous_path.read_bytes(), previous_before)
        self.assertEqual(torch.load(latest_path, map_location="cpu", weights_only=False)["optimizer_updates"], 3)
        self.assertEqual(torch.load(previous_path, map_location="cpu", weights_only=False)["optimizer_updates"], 1)

    def test_resume_uses_previous_when_latest_is_corrupt(self):
        torch = FakeTorchSerialization
        checkpoint_dir = self.root / "run/checkpoints"
        checkpoint_dir.mkdir(parents=True)
        state = {"run_identity": "expected", "model": {}, "optimizer": {}, "scheduler": {},
            "epoch": 1, "optimizer_updates": 2, "rng": {}}
        (checkpoint_dir / "latest.pt").write_bytes(b"broken latest archive")
        torch.save(state, checkpoint_dir / "previous.pt")

        restored, slot = trainer.load_recovery_checkpoint(self.root / "run", "expected", torch)

        self.assertEqual(slot, "previous")
        self.assertEqual(restored["optimizer_updates"], 2)

    def test_pinned_restore_selector_rejects_tampered_previous_before_torch_load(self):
        from unittest.mock import patch
        checkpoint_dir = self.root / "run/checkpoints"
        checkpoint_dir.mkdir(parents=True)
        (checkpoint_dir / "latest.pt").write_bytes(b"known corrupt latest")
        (checkpoint_dir / "previous.pt").write_bytes(b"tampered previous")
        with patch.object(FakeTorchSerialization, "load") as load_checkpoint:
            with self.assertRaisesRegex(RuntimeError, "SHA-256 mismatch"):
                trainer.load_recovery_checkpoint_with_evidence(
                    self.root / "run", "expected", FakeTorchSerialization,
                    expected_slot_sha256={"previous": "0" * 64},
                    rejected_slots={"latest": "recorded unreadable CP01 latest slot"})
        load_checkpoint.assert_not_called()

    def test_restore_application_loads_all_state_and_progress_without_step_methods(self):
        from unittest.mock import patch
        model, optimizer, scheduler, scaler = (StateLoadDouble() for _ in range(4))
        state = {
            "model": {"weights": [1, 2]},
            "optimizer": {"state": {"step": 2}},
            "scheduler": {"last_epoch": 2},
            "scaler": {"scale": 1.0},
            "epoch": 1,
            "epoch_complete": False,
            "optimizer_updates": 2,
            "next_batch_cursor": 3,
            "epoch_loss_sum": 4.5,
            "epoch_conversations_processed": 16,
            "history": [{"epoch": 1, "optimizer_updates": 2}],
            "predictions": [{"epoch": 1, "evaluation_point": "diagnostic_limit"}],
            "rng": {"python": (1, 2, 3)},
        }
        with patch.object(trainer, "restore_rng_state") as restore_rng:
            progress = trainer.apply_recovery_state(
                state, model, optimizer, scheduler, scaler, FakeTorchSerialization)

        for target, expected in zip((model, optimizer, scheduler, scaler),
                                    (state["model"], state["optimizer"], state["scheduler"], state["scaler"])):
            self.assertEqual(target.loaded, expected)
            self.assertEqual(target.load_calls, 1)
        restore_rng.assert_called_once_with(state["rng"], FakeTorchSerialization)
        self.assertEqual(progress["start_epoch"], 0)
        self.assertEqual(progress["optimizer_updates"], 2)
        self.assertEqual(progress["next_batch_cursor"], 3)
        self.assertEqual(progress["epoch_loss_sum"], 4.5)
        self.assertEqual(progress["epoch_conversations_processed"], 16)
        self.assertEqual(progress["history"], state["history"])
        self.assertEqual(progress["predictions"], state["predictions"])

    def test_restore_only_guard_is_limited_to_two_update_local_wangchan_resume(self):
        self.assertEqual(trainer.CP01_RECORDED_TRAINER_SHA256,
            "22578e136d33ebae07374152c8bcbaaa75e51790184f1788b2b9f2dc3aa3b726")
        approved = {
            "run_id": trainer.CP01_RESTORE_RUN_ID,
            "mode": "diagnostic", "model": "wangchanberta",
            "checkpoint": {"id": trainer.CP01_RESTORE_MODEL_ID,
                "revision": trainer.CP01_RESTORE_MODEL_REVISION, "custom_code_revision": None},
            "data": {"condition": "primary_plus_supplemental"},
            "fold": 0,
            "training": {"representation": "whole_conversation", "marker_condition": "role_marked",
                "seed": 67, "epochs": 1, "optimizer_updates_limit": 2,
                "effective_batch_size": 16, "microbatch_size": 8,
                "accumulation_steps": 2, "recovery_interval_updates": 1},
            "diagnostic_sample_selection": {"strategy": "longest_by_prepared_tokens",
                "source": "eligible fold_train records, marked whole-conversation prepared tokens",
                "sample_count": 32, "tie_break": "ascending sample_id"},
            "validation": {"representation": "whole_conversation",
                "marker_conditions": ["role_marked", "role_free"]},
            "optimizer": {"name": "AdamW", "learning_rate": 3e-5, "weight_decay": 0.01,
                "beta1": 0.9, "beta2": 0.999, "epsilon": 1e-8, "gradient_clip_norm": 1.0},
            "schedule": {"name": "linear_warmup_then_constant", "warmup_updates": 0},
            "precision": {"mode": "auto", "auto_policy_approved": True},
            "evaluation": {"scam_threshold": 0.5},
            "approval": {"status": "owner_approved", "diagnostic_numeric_settings": True,
                "selection_protocol_approved": False,
                "reference": trainer.CP01_RESTORE_APPROVAL_REFERENCE},
            "runtime": {"device": "cuda", "local_files_only": False},
        }
        trainer.validate_restore_only_request(approved, resume=True, extend_to_epoch=None)
        changes = [
            ("run_id", trainer.CP01_RESTORE_RUN_ID + "-other"),
            ("model", "xlmr"),
            ("checkpoint.id", "other/checkpoint"),
            ("checkpoint.revision", "different-revision"),
            ("training.optimizer_updates_limit", 3),
            ("training.seed", 68),
            ("training.effective_batch_size", 8),
            ("optimizer.learning_rate", 2e-5),
            ("schedule.warmup_updates", 1),
            ("data.condition", "primary_only"),
            ("mode", "comparative"),
        ]
        for dotted_key, value in changes:
            changed = copy.deepcopy(approved)
            target = changed
            parts = dotted_key.split(".")
            for part in parts[:-1]:
                target = target[part]
            target[parts[-1]] = value
            with self.subTest(dotted_key=dotted_key, value=value), self.assertRaises(ValueError):
                trainer.validate_restore_only_request(changed, resume=True, extend_to_epoch=None)
        with self.assertRaisesRegex(ValueError, "requires --resume"):
            trainer.validate_restore_only_request(approved, resume=False, extend_to_epoch=None)
        with self.assertRaisesRegex(ValueError, "without epoch extension"):
            trainer.validate_restore_only_request(approved, resume=True, extend_to_epoch=2)

    def test_restore_only_pins_previous_checkpoint_hash_and_reports_scheduler_initialization(self):
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "checkpoints" / "previous.pt"
            checkpoint.parent.mkdir()
            checkpoint.write_bytes(b"not the reviewed CP01 checkpoint")
            before = checkpoint.read_bytes()
            with self.assertRaisesRegex(ValueError, "SHA-256 differs"):
                trainer.validate_cp01_previous_checkpoint(directory)
            self.assertEqual(checkpoint.read_bytes(), before)
        evidence = trainer.restore_only_step_evidence()
        self.assertEqual(evidence["forward_calls"], 0)
        self.assertEqual(evidence["backward_calls"], 0)
        self.assertEqual(evidence["optimizer_steps"], 0)
        self.assertEqual(evidence["explicit_scheduler_steps"], 0)
        self.assertIn("may perform its standard implicit initialization",
                      evidence["scheduler_constructor_initialization"])

    def test_public_restore_only_exit_preserves_run_files_and_caller_rng_on_failure(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        approved = self._approved_cp01_restore_config()
        run_dir = self.root / "persistent" / trainer.CP01_RESTORE_RUN_ID
        run_dir.mkdir(parents=True)
        marker = run_dir / "preserved.bin"
        marker.write_bytes(b"preserve exact bytes")
        before = {path.relative_to(run_dir).as_posix(): path.read_bytes()
                  for path in run_dir.rglob("*") if path.is_file()}
        torch_stub = SimpleNamespace()
        with patch.dict(sys.modules, {"torch": torch_stub}), \
             patch.object(trainer, "environment_rng_state", return_value={"caller": "rng"}), \
             patch.object(trainer, "restore_rng_state") as restore_rng, \
             patch.object(trainer, "_run_training_impl", side_effect=RuntimeError("synthetic restore failure")):
            with self.assertRaisesRegex(RuntimeError, "synthetic restore failure"):
                trainer.run_training(approved, resume=True, restore_only=True)
        after = {path.relative_to(run_dir).as_posix(): path.read_bytes()
                 for path in run_dir.rglob("*") if path.is_file()}
        self.assertEqual(after, before)
        restore_rng.assert_called_once_with({"caller": "rng"}, torch_stub)

    def test_restore_only_end_to_end_applies_state_without_writes_or_training_steps(self):
        import hashlib
        import pickle
        import types
        from unittest.mock import patch

        config = self._approved_cp01_restore_config()
        config["paths"].update({
            "input_config": str(self.root / "input_config.json"),
            "input_exports": str(self.root / "exports"),
            "persistent_runs": str(self.root / "runs"),
        })
        input_config_path = Path(config["paths"]["input_config"])
        input_config_path.write_text("{}", encoding="utf-8")
        exports = Path(config["paths"]["input_exports"])
        exports.mkdir()
        (exports / "manifest.json").write_text("{}", encoding="utf-8")
        input_dir = self.root / "input-preparation"
        input_dir.mkdir()
        (input_dir / "inputs.py").write_text("# synthetic", encoding="utf-8")
        (input_dir / "token_length_report.json").write_text("{}", encoding="utf-8")
        run_dir = Path(config["paths"]["persistent_runs"]) / config["run_id"]
        checkpoint_dir = run_dir / "checkpoints"
        checkpoint_dir.mkdir(parents=True)

        input_identities = {"assignments_sha256": "a" * 64, "training_csv_sha256": "b" * 64}
        membership = {"training_sample_ids": ["train-1"], "validation_sample_ids": ["validation-1"]}
        original_config = copy.deepcopy(config)
        original_config["identities"] = {
            "preprocessing_config_sha256": hashlib.sha256(input_config_path.read_bytes()).hexdigest(),
            "input_component_sha256": hashlib.sha256((input_dir / "inputs.py").read_bytes()).hexdigest(),
            "input_manifest_sha256": hashlib.sha256((exports / "manifest.json").read_bytes()).hexdigest(),
            "input_length_report_sha256": hashlib.sha256((input_dir / "token_length_report.json").read_bytes()).hexdigest(),
            "training_component_sha256": trainer.CP01_RECORDED_TRAINER_SHA256,
            "assignments_sha256": input_identities["assignments_sha256"],
            "training_csv_sha256": input_identities["training_csv_sha256"],
            "training_membership_sha256": trainer.canonical_hash(membership["training_sample_ids"]),
            "validation_membership_sha256": trainer.canonical_hash(membership["validation_sample_ids"]),
            "training_sample_ids": membership["training_sample_ids"],
            "validation_sample_ids": membership["validation_sample_ids"],
            "training_count": 1, "validation_count": 1,
        }
        original_config["configuration_id"] = trainer.configuration_id(config)
        (run_dir / "run_config.json").write_text(json.dumps(original_config), encoding="utf-8")
        (run_dir / "training_history.csv").write_text("history bytes", encoding="utf-8")
        (run_dir / "validation_predictions.csv").write_text("prediction bytes", encoding="utf-8")
        (checkpoint_dir / "latest.pt").write_bytes(b"known corrupt latest")
        state = {
            "run_identity": trainer.recovery_identity(original_config),
            "run_config": original_config,
            "model": {"weight": [1, 2]},
            "optimizer": {"state": {"one": 1}, "param_groups": []},
            "scheduler": {"last_epoch": 2}, "scaler": {},
            "rng": {"python": "checkpoint-rng"},
            "epoch": 1, "epoch_complete": False, "optimizer_updates": 2,
            "next_batch_cursor": 3, "epoch_loss_sum": 2.5,
            "epoch_conversations_processed": 16,
            "history": [{"epoch": 1, "optimizer_updates": 2}],
            "predictions": [{"epoch": 1, "evaluation_point": "diagnostic_limit"}],
        }
        previous_path = checkpoint_dir / "previous.pt"
        with previous_path.open("wb") as stream:
            pickle.dump(state, stream)
        expected_previous_sha = hashlib.sha256(previous_path.read_bytes()).hexdigest()
        before = trainer._artifact_tree_sha256(run_dir)

        class FakeModel(StateLoadDouble):
            def __init__(self):
                super().__init__()
                self.config = types.SimpleNamespace(architectures=["CamembertForSequenceClassification"],
                    to_dict=lambda: {})
                self.forward_calls = 0

            def to(self, _device):
                return self

            def named_modules(self):
                return []

            def named_parameters(self):
                return []

            def __call__(self, **_kwargs):
                self.forward_calls += 1
                raise AssertionError("Restore-only path called model forward")

        class FakeOptimizer(StateLoadDouble):
            def __init__(self, *_args, **_kwargs):
                super().__init__()
                self.step_calls = 0

            def step(self, *_args, **_kwargs):
                self.step_calls += 1
                raise AssertionError("Restore-only path stepped optimizer")

        class FakeScheduler(StateLoadDouble):
            def __init__(self, *_args, **_kwargs):
                super().__init__()
                self.step_calls = 0

            def step(self, *_args, **_kwargs):
                self.step_calls += 1
                raise AssertionError("Restore-only path explicitly stepped scheduler")

        class FakeScaler(StateLoadDouble):
            def __init__(self, *_args, **_kwargs):
                super().__init__()
                self.enabled = False

        torch_module = types.ModuleType("torch")
        torch_module.is_tensor = lambda _value: False
        torch_module.equal = lambda left, right: left == right
        torch_module.device = lambda _device: types.SimpleNamespace(type="cuda", index=None)
        torch_module.cuda = types.SimpleNamespace(is_available=lambda: True,
            reset_peak_memory_stats=lambda *_args: None)
        torch_module.amp = types.SimpleNamespace(GradScaler=FakeScaler)
        torch_module.load = FakeTorchSerialization.load
        torch_module.save = FakeTorchSerialization.save
        nn_module = types.ModuleType("torch.nn")
        nn_module.functional = types.SimpleNamespace()
        nn_utils_module = types.ModuleType("torch.nn.utils")
        nn_utils_module.clip_grad_norm_ = lambda *_args, **_kwargs: None
        optim_module = types.ModuleType("torch.optim")
        optim_module.AdamW = FakeOptimizer
        scheduler_module = types.ModuleType("torch.optim.lr_scheduler")
        scheduler_module.LambdaLR = FakeScheduler
        inputs_module = types.ModuleType("inputs")
        inputs_module.load_tokenizer = lambda *_args, **_kwargs: object()

        with patch.object(trainer, "CP01_RESTORE_PREVIOUS_SHA256", expected_previous_sha), \
             patch.object(trainer, "INPUT_DIR", input_dir), \
             patch.object(trainer, "validate_config"), \
             patch.object(trainer, "get_records", return_value=([], [{}], [{}], {}, input_identities, membership)), \
             patch.object(trainer, "build_model", return_value=FakeModel()), \
             patch.object(trainer, "adamw_parameter_groups", return_value=[]), \
             patch.object(trainer, "optimizer_group_names", return_value=[]), \
             patch.object(trainer, "resolve_precision", return_value="fp32"), \
             patch.object(trainer, "describe_environment", return_value={}), \
             patch.object(trainer, "synchronize_device"), \
             patch.object(trainer, "seed_everything"), \
             patch.object(trainer, "environment_rng_state",
                          side_effect=[{"python": "caller-rng"}, {"python": "checkpoint-rng"},
                                      {"python": "caller-rng-rejection"}]), \
             patch.object(trainer, "restore_rng_state") as restore_rng, \
             patch.object(torch_module, "load", wraps=torch_module.load) as load_checkpoint, \
             patch.dict(sys.modules, {
                 "torch": torch_module,
                 "torch.nn": nn_module,
                 "torch.nn.utils": nn_utils_module,
                 "torch.optim": optim_module,
                 "torch.optim.lr_scheduler": scheduler_module,
                 "inputs": inputs_module,
             }):
            report = trainer.run_training(config, resume=True, restore_only=True)
            saved_run_config_bytes = (run_dir / "run_config.json").read_bytes()
            wrong_creator_config = copy.deepcopy(original_config)
            wrong_creator_config["identities"]["training_component_sha256"] = (
                "0da4d552d5fe93ace44e3d6b3d00c90a639fd7c64e5d6448149518100dc7d2df")
            (run_dir / "run_config.json").write_text(json.dumps(wrong_creator_config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not created by the reviewed CP01 trainer"):
                trainer.run_training(config, resume=True, restore_only=True)
            self.assertEqual(load_checkpoint.call_count, 1)
            (run_dir / "run_config.json").write_bytes(saved_run_config_bytes)

        self.assertEqual(report["status"], "restore_verified")
        self.assertEqual(report["checkpoint_slot"], "previous")
        self.assertEqual(report["previous_checkpoint_sha256"], expected_previous_sha)
        self.assertTrue(report["rng_state_applied_exactly"])
        self.assertTrue(report["run_artifacts_unchanged"])
        self.assertEqual(report["optimizer_updates"], 2)
        self.assertEqual(report["next_batch_cursor"], 3)
        self.assertEqual(report["history_count"], 1)
        self.assertEqual(report["prediction_count"], 1)
        self.assertEqual(report["training_steps"]["explicit_scheduler_steps"], 0)
        self.assertIn("implicit initialization", report["training_steps"]["scheduler_constructor_initialization"])
        self.assertEqual(trainer._artifact_tree_sha256(run_dir), before)
        self.assertEqual(load_checkpoint.call_count, 1)
        self.assertEqual(Path(load_checkpoint.call_args.args[0]).resolve(), previous_path.resolve())
        self.assertEqual(restore_rng.call_args_list[0].args[0], state["rng"])
        self.assertEqual(restore_rng.call_args_list[-2].args[0], {"python": "caller-rng"})
        self.assertEqual(restore_rng.call_args_list[-1].args[0], {"python": "caller-rng-rejection"})
        self.assertEqual(report["training_steps"]["forward_calls"], 0)
        self.assertEqual(report["training_steps"]["backward_calls"], 0)
        self.assertEqual(report["training_steps"]["optimizer_steps"], 0)

    @staticmethod
    def _approved_cp01_restore_config():
        return {
            "run_id": trainer.CP01_RESTORE_RUN_ID,
            "mode": "diagnostic", "model": "wangchanberta",
            "checkpoint": {"id": trainer.CP01_RESTORE_MODEL_ID,
                "revision": trainer.CP01_RESTORE_MODEL_REVISION, "custom_code_revision": None},
            "data": {"condition": "primary_plus_supplemental"}, "fold": 0,
            "training": {"representation": "whole_conversation", "marker_condition": "role_marked",
                "seed": 67, "epochs": 1, "optimizer_updates_limit": 2,
                "effective_batch_size": 16, "microbatch_size": 8,
                "accumulation_steps": 2, "recovery_interval_updates": 1},
            "diagnostic_sample_selection": {"strategy": "longest_by_prepared_tokens",
                "source": "eligible fold_train records, marked whole-conversation prepared tokens",
                "sample_count": 32, "tie_break": "ascending sample_id"},
            "validation": {"representation": "whole_conversation",
                "marker_conditions": ["role_marked", "role_free"]},
            "optimizer": {"name": "AdamW", "learning_rate": 3e-5, "weight_decay": 0.01,
                "beta1": 0.9, "beta2": 0.999, "epsilon": 1e-8, "gradient_clip_norm": 1.0},
            "schedule": {"name": "linear_warmup_then_constant", "warmup_updates": 0},
            "precision": {"mode": "auto", "auto_policy_approved": True},
            "evaluation": {"scam_threshold": 0.5},
            "approval": {"status": "owner_approved", "diagnostic_numeric_settings": True,
                "selection_protocol_approved": False,
                "reference": trainer.CP01_RESTORE_APPROVAL_REFERENCE},
            "runtime": {"device": "cuda", "local_files_only": False},
            "paths": {"persistent_runs": str(Path("/tmp/unused"))},
        }

    def test_resume_fails_safely_when_both_recovery_slots_are_invalid(self):
        torch = FakeTorchSerialization
        checkpoint_dir = self.root / "run/checkpoints"
        checkpoint_dir.mkdir(parents=True)
        (checkpoint_dir / "latest.pt").write_bytes(b"broken latest archive")
        torch.save({"run_identity": "different"}, checkpoint_dir / "previous.pt")

        with self.assertRaisesRegex(RuntimeError, "neither recovery checkpoint is valid"):
            trainer.load_recovery_checkpoint(self.root / "run", "expected", torch)

    def test_failed_publish_and_rollback_retains_backup_and_previous_slot(self):
        from unittest.mock import patch
        torch = FakeTorchSerialization
        run_dir = self.root / "run"
        trainer.save_recovery(run_dir, {"run_identity": "synthetic", "epoch": 1,
            "optimizer_updates": 1}, torch)
        trainer.save_recovery(run_dir, {"run_identity": "synthetic", "epoch": 2,
            "optimizer_updates": 2}, torch)
        latest_path = run_dir / "checkpoints/latest.pt"
        previous_path = run_dir / "checkpoints/previous.pt"
        previous_before = previous_path.read_bytes()
        real_load = torch.load
        latest_reads = 0

        def fail_final_slot_readback(file, **kwargs):
            nonlocal latest_reads
            loaded = real_load(file, **kwargs)
            if Path(file) == latest_path:
                latest_reads += 1
            if Path(file) == latest_path and latest_reads >= 2:
                raise RuntimeError("simulated persistent destination readback failure")
            return loaded

        with patch.object(torch, "load", side_effect=fail_final_slot_readback):
            with self.assertRaisesRegex(trainer.RecoveryPublishError, "preserve backup"):
                trainer.save_recovery(run_dir, {"run_identity": "synthetic", "epoch": 3,
                    "optimizer_updates": 3}, torch)

        self.assertEqual(previous_path.read_bytes(), previous_before)
        backups = list((run_dir / "checkpoints").glob("latest-backup.*.tmp"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(real_load(backups[0], map_location="cpu", weights_only=False)["optimizer_updates"], 2)

    def test_synthetic_xlmr_factory_reinitializes_only_head_and_runs_forward(self):
        import torch
        from transformers import XLMRobertaConfig, XLMRobertaForSequenceClassification
        cfg = XLMRobertaConfig(vocab_size=32, max_position_embeddings=24, hidden_size=16,
            num_hidden_layers=1, num_attention_heads=2, intermediate_size=32, num_labels=2)
        source = XLMRobertaForSequenceClassification(cfg)
        original_embedding = source.roberta.embeddings.word_embeddings.weight.detach().clone()
        original_head = source.classifier.out_proj.weight.detach().clone()
        source_dir = self.root / "random-source-checkpoint"
        source.save_pretrained(source_dir, safe_serialization=True)
        model = trainer.build_model("xlmr", str(source_dir), "synthetic-local", local_files_only=True)
        torch.testing.assert_close(model.roberta.embeddings.word_embeddings.weight, original_embedding)
        self.assertFalse(torch.equal(model.classifier.out_proj.weight, original_head))
        logits = model(input_ids=torch.tensor([[0, 4, 5, 2]]), attention_mask=torch.ones(1, 4, dtype=torch.long)).logits
        self.assertEqual(tuple(logits.shape), (1, 2))

    def test_wangchan_known_checkpoint_extras_are_only_ignored_when_unexpected(self):
        known_extra_keys = [
            "lm_head.bias", "lm_head.dense.weight", "lm_head.dense.bias",
            "lm_head.layer_norm.weight", "lm_head.layer_norm.bias",
            "lm_head.decoder.weight", "roberta.pooler.dense.bias",
            "roberta.pooler.dense.weight",
        ]
        trainer.validate_pretrained_loading_info(
            "wangchanberta", {"unexpected_keys": known_extra_keys}, ["classifier"],
            allow_wangchan_checkpoint_extras=True)
        with self.assertRaisesRegex(RuntimeError, "unexpected_backbone"):
            trainer.validate_pretrained_loading_info(
                "wangchanberta", {"unexpected_keys": ["lm_head.unrecognized.weight"]}, ["classifier"],
                allow_wangchan_checkpoint_extras=True)
        with self.assertRaisesRegex(RuntimeError, "unexpected_backbone"):
            trainer.validate_pretrained_loading_info(
                "wangchanberta", {"unexpected_keys": ["roberta.pooler.dense.extra"]}, ["classifier"],
                allow_wangchan_checkpoint_extras=True)
        with self.assertRaisesRegex(RuntimeError, "unexpected_backbone"):
            trainer.validate_pretrained_loading_info(
                "wangchanberta", {"unexpected_keys": ["roberta.pooler.dense.weight"]}, ["classifier"])
        with self.assertRaisesRegex(RuntimeError, "unexpected_backbone"):
            trainer.validate_pretrained_loading_info(
                "xlmr", {"unexpected_keys": ["roberta.pooler.dense.weight"]}, ["classifier"],
                allow_wangchan_checkpoint_extras=True)

    def test_checkpoint_extras_never_hide_missing_or_mismatched_weights(self):
        with self.assertRaisesRegex(RuntimeError, "missing_backbone"):
            trainer.validate_pretrained_loading_info(
                "wangchanberta", {"missing_keys": ["lm_head.bias"]}, ["classifier"],
                allow_wangchan_checkpoint_extras=True)
        with self.assertRaisesRegex(RuntimeError, "missing_backbone"):
            trainer.validate_pretrained_loading_info(
                "wangchanberta", {"missing_keys": ["roberta.pooler.dense.bias"]}, ["classifier"],
                allow_wangchan_checkpoint_extras=True)
        with self.assertRaisesRegex(RuntimeError, "mismatched_backbone"):
            trainer.validate_pretrained_loading_info(
                "wangchanberta", {"mismatched_keys": [("lm_head.decoder.weight", (1,), (2,))]}, ["classifier"],
                allow_wangchan_checkpoint_extras=True)
        with self.assertRaisesRegex(RuntimeError, "mismatched_backbone"):
            trainer.validate_pretrained_loading_info(
                "wangchanberta", {"mismatched_keys": [("roberta.pooler.dense.weight", (1,), (2,))]}, ["classifier"],
                allow_wangchan_checkpoint_extras=True)

    def test_wangchan_extras_exception_requires_exact_frozen_checkpoint_identity(self):
        from types import SimpleNamespace
        config_path = trainer.INPUT_DIR / "preprocessing_config.json"
        frozen = json.loads(config_path.read_text(encoding="utf-8"))["models"]["wangchanberta"]
        model_config = SimpleNamespace(model_type="camembert", architectures=["RobertaForMaskedLM"])
        self.assertTrue(trainer.is_approved_wangchan_checkpoint(
            "wangchanberta", frozen["checkpoint"], frozen["revision"], model_config))
        self.assertFalse(trainer.is_approved_wangchan_checkpoint(
            "wangchanberta", frozen["checkpoint"], "different-revision", model_config))
        self.assertFalse(trainer.is_approved_wangchan_checkpoint(
            "xlmr", frozen["checkpoint"], frozen["revision"], model_config))
        wrong_architecture = SimpleNamespace(model_type="camembert", architectures=["CamembertForSequenceClassification"])
        self.assertFalse(trainer.is_approved_wangchan_checkpoint(
            "wangchanberta", frozen["checkpoint"], frozen["revision"], wrong_architecture))

    def test_loading_info_exempts_only_exact_discovered_classification_head(self):
        trainer.validate_pretrained_loading_info(
            "xlmr", {"missing_keys": ["classifier.dense.weight"],
                     "mismatched_keys": [("classifier.out_proj.weight", (2, 8), (3, 8))]},
            ["classifier"])
        with self.assertRaisesRegex(RuntimeError, "unexpected_backbone"):
            trainer.validate_pretrained_loading_info(
                "xlmr", {"unexpected_keys": ["roberta.encoder.layer.0.attention_score.weight"]},
                ["classifier"])

    def test_native_synthetic_inference_export_verifies_and_loads(self):
        import hashlib
        import torch
        from tokenizers import Tokenizer, models, pre_tokenizers
        from transformers import (PreTrainedTokenizerFast, XLMRobertaConfig,
                                 XLMRobertaForSequenceClassification)
        artifact = self.root / "native-final-model"
        artifact.mkdir()
        raw = Tokenizer(models.WordLevel({"[UNK]": 0, "[PAD]": 1, "[CLS]": 2, "[SEP]": 3}, unk_token="[UNK]"))
        raw.pre_tokenizer = pre_tokenizers.Whitespace()
        tokenizer = PreTrainedTokenizerFast(tokenizer_object=raw, unk_token="[UNK]", pad_token="[PAD]",
            cls_token="[CLS]", sep_token="[SEP]")
        cfg = XLMRobertaConfig(vocab_size=4, max_position_embeddings=24, hidden_size=8,
            num_hidden_layers=1, num_attention_heads=2, intermediate_size=16, num_labels=2)
        cfg.id2label = {0: "Not Scam", 1: "Scam"}
        cfg.label2id = {"Not Scam": 0, "Scam": 1}
        model = XLMRobertaForSequenceClassification(cfg)
        model.save_pretrained(artifact, safe_serialization=True)
        tokenizer.save_pretrained(artifact)
        files = {str(path.relative_to(artifact)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in artifact.rglob("*") if path.is_file()}
        manifest = {"schema_version": 1, "run_id": "synthetic-final", "configuration_id": "synthetic-config",
            "model": "xlmr", "checkpoint_id": "synthetic", "checkpoint_revision": "synthetic-revision",
            "custom_code_revision": None, "preprocessing_config_sha256": "synthetic-prep",
            "assignments_sha256": "synthetic-assignments", "training_membership_sha256": "synthetic-membership",
            "training_seed": 67, "training_data_condition": "primary_plus_supplemental",
            "training_representation": "whole_conversation", "training_marker_condition": "role_marked",
            "num_labels": 2, "id2label": model.config.id2label, "label2id": model.config.label2id,
            "head_modules": ["classifier"], "dropout_config": {"hidden_dropout_prob": 0.1}, "files": files}
        (artifact / "artifact_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.assertEqual(trainer.verify_model_artifact(artifact)["num_labels"], 2)
        loaded, loaded_manifest = trainer.load_model_for_inference(artifact)
        self.assertEqual(loaded.config.num_labels, 2)
        self.assertEqual(loaded_manifest["run_id"], "synthetic-final")
        out = loaded(input_ids=torch.tensor([[2, 3]]), attention_mask=torch.ones(1, 2, dtype=torch.long)).logits
        self.assertEqual(tuple(out.shape), (1, 2))

    def test_test_partition_is_rejected_without_reading_it(self):
        config = make_config(self.root)
        config["data"]["partition"] = "test"
        config["approval"]["approved_settings_sha256"] = trainer.approved_settings_digest(config)
        with self.assertRaisesRegex(ValueError, "test partition"):
            trainer.validate_config(config)

    def test_configuration_id_is_shared_across_saved_cv_folds(self):
        config = trainer.validate_config(make_config(self.root), require_diagnostic_approval=False)
        original = trainer.configuration_id(config)
        config["fold"] = 3
        config["approval"]["approved_settings_sha256"] = trainer.approved_settings_digest(config)
        trainer.validate_config(config)
        self.assertEqual(original, trainer.configuration_id(config))

    def test_inference_artifact_manifest_rejects_tampering_and_unlisted_files(self):
        import hashlib
        artifact = self.root / "final_model"
        artifact.mkdir()
        content = {"model.safetensors": b"synthetic weights", "config.json": b'{"id2label":{"0":"Not Scam","1":"Scam"},"label2id":{"Not Scam":0,"Scam":1}}',
            "tokenizer_config.json": b"{}", "tokenizer.json": b"{}"}
        for name, data in content.items():
            (artifact / name).write_bytes(data)
        manifest = {"schema_version": 1, "num_labels": 2, "id2label": {"0": "Not Scam", "1": "Scam"},
            "run_id": "run", "configuration_id": "config", "model": "xlmr",
            "checkpoint_id": "checkpoint", "checkpoint_revision": "revision",
            "preprocessing_config_sha256": "preprocessing", "assignments_sha256": "assignments",
            "training_membership_sha256": "membership",
            "files": {name: hashlib.sha256(data).hexdigest() for name, data in content.items()}}
        (artifact / "artifact_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.assertEqual(trainer.verify_model_artifact(artifact)["model"], "xlmr")
        (artifact / "extra.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unmanifested"):
            trainer.verify_model_artifact(artifact)


if __name__ == "__main__":
    unittest.main()
