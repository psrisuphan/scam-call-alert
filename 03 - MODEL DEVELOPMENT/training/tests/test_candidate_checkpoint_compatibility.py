"""Regression checks for pinned checkpoint loading and verification memory."""
import json
from types import SimpleNamespace
import unittest
import trainer


class CandidateCheckpointCompatibilityTests(unittest.TestCase):
    def test_exact_pinned_exceptions_keep_backbone_guards(self):
        prep = json.loads((trainer.INPUT_DIR / "preprocessing_config.json").read_text())
        for key, model_type, architecture, count in (
            ("phayathaibert", "camembert", "CamembertForMaskedLM", 5),
            ("xlmr", "xlm-roberta", "XLMRobertaForMaskedLM", 7),
        ):
            with self.subTest(model=key):
                pin = prep["models"][key]
                config = SimpleNamespace(model_type=model_type, architectures=[architecture])
                extras = trainer.approved_candidate_extra_keys(
                    key, pin["checkpoint"], pin["revision"], config)
                self.assertEqual(len(extras), count)
                loading = {"missing_keys": ["classifier.dense.weight"],
                           "unexpected_keys": list(extras)}
                trainer.validate_pretrained_loading_info(
                    key, loading, ["classifier"], approved_extra_keys=extras)
                for change in (
                    {"missing_keys": ["roberta.embeddings.word_embeddings.weight"]},
                    {"unexpected_keys": ["unknown.weight"]},
                    {"mismatched_keys": [("roberta.embeddings.word_embeddings.weight", (1,), (2,))]},
                ):
                    with self.assertRaises(RuntimeError):
                        trainer.validate_pretrained_loading_info(
                            key, {**loading, **change}, ["classifier"],
                            approved_extra_keys=extras)
                for checkpoint, revision, cfg in (
                    ("wrong", pin["revision"], config),
                    (pin["checkpoint"], "wrong", config),
                    (pin["checkpoint"], pin["revision"],
                     SimpleNamespace(model_type="wrong", architectures=[architecture])),
                    (pin["checkpoint"], pin["revision"],
                     SimpleNamespace(model_type=model_type, architectures=["wrong"])),
                ):
                    self.assertFalse(trainer.approved_candidate_extra_keys(
                        key, checkpoint, revision, cfg))

    def test_hplt_has_no_extra_key_exception(self):
        self.assertFalse(trainer.approved_candidate_extra_keys(
            "hplt", "anything", "anything", SimpleNamespace()))

    def test_checkpoint_verification_returns_only_metadata(self):
        loaded = {"run_identity": "run", "optimizer_updates": 156,
                  "model": {"large_tensor": object()},
                  "optimizer": {"large_state": object()}}
        torch = SimpleNamespace(load=lambda *args, **kwargs: loaded)
        metadata = trainer._verify_recovery_checkpoint(
            "unused", {"run_identity": "run"}, torch)
        self.assertEqual(metadata, {"run_identity": "run", "optimizer_updates": 156})
        self.assertNotIn("model", metadata)
        self.assertNotIn("optimizer", metadata)


if __name__ == "__main__":
    unittest.main()
