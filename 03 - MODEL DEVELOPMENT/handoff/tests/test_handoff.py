import math
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import nullcontext
import sys

HANDOFF_DIR = Path(__file__).resolve().parents[1]
if str(HANDOFF_DIR) not in sys.path:
    sys.path.insert(0, str(HANDOFF_DIR))
from bundle_manifest import build_manifest, validate_manifest
from inference import LocalClassifier, assemble_bundle
from parity import FinalEvaluationAdapter, compare_parity, run_live_parity, training_pool_fixtures


class Tensor:
    def __init__(self, values):
        self.values = values
        self.shape = (len(values), len(values[0])) if values and isinstance(values[0], list) else (len(values),)
        self.ndim = len(self.shape)

    def to(self, device):
        return self

    def __getitem__(self, index):
        return Tensor(self.values[index])

    def detach(self):
        return self

    def cpu(self):
        return self

    def tolist(self):
        return self.values[0] if len(self.values) == 1 else self.values


class FakeTorch:
    @staticmethod
    def as_tensor(values, device=None):
        return Tensor(values)

    @staticmethod
    def inference_mode():
        return nullcontext()

    @staticmethod
    def softmax(tensor, dim=-1):
        values = tensor.values[0] if tensor.values and isinstance(tensor.values[0], list) else tensor.values
        exps = [math.exp(value - max(values)) for value in values]
        total = sum(exps)
        return Tensor([[value / total for value in exps]])


class FakeModel:
    def __init__(self, logits=(0.0, 0.0), failure=None):
        self.values, self.failure = logits, failure
        self.evaluated = False

    def to(self, device):
        self.device = device
        return self

    def eval(self):
        self.evaluated = True

    def __call__(self, **inputs):
        if self.failure:
            raise self.failure
        return {"logits": Tensor([list(self.values)])}


class HandoffTests(unittest.TestCase):
    def make_service(self, model=None, prepare=None):
        calls = []
        def prepare_text(text, model_key, config, tokenizer, **kwargs):
            calls.append((text, model_key, kwargs))
            if prepare:
                return prepare(text)
            return {"inputs": {"input_ids": [[1, 2]], "attention_mask": [[1, 1]]},
                    "notices": {"truncated": False}}
        def pad_batch(items, tokenizer):
            return {"inputs": items[0]["inputs"]}
        svc = LocalClassifier(model or FakeModel(), object(), {}, model_key="xlmr",
                              model_version="bundle-test", device="cpu",
                              prepare_text_fn=prepare_text, pad_batch_fn=pad_batch,
                              torch_module=FakeTorch)
        return svc, calls

    def test_success_uses_shared_role_free_preparation_and_fixed_threshold(self):
        service, calls = self.make_service(FakeModel((0.0, 1.0)))
        service.checkpoint_prepare = lambda text, *_: text
        result = service.predict({"request_id": "r1", "transcript": "สวัสดี"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(set(result), {"request_id", "model_version", "status", "label", "probabilities",
                                       "threshold", "warnings", "error"})
        self.assertEqual(result["label"], "Scam")
        self.assertEqual(result["threshold"], 0.5)
        self.assertEqual(set(result["probabilities"]), {"Not Scam", "Scam"})
        self.assertEqual(calls[0][1], "xlmr")
        self.assertEqual(calls[0][2], {"mode": "whole_conversation", "marker_condition": "role_free"})

    def test_threshold_boundary_and_truncation_notice(self):
        service, _ = self.make_service(FakeModel((0.0, 0.0)),
            lambda text: {"inputs": {"input_ids": [[1]], "attention_mask": [[1]]},
                          "notices": {"truncated": True}})
        result = service.predict({"request_id": "r2", "transcript": "x"})
        self.assertEqual(result["label"], "Scam")
        self.assertEqual(result["warnings"], ["TRUNCATED_TO_APPROVED_LIMIT"])

    def test_stable_failures_never_return_not_scam(self):
        service, _ = self.make_service()
        cases = [
            ({"request_id": "r", "transcript": " "}, "E_TRANSCRIPT_INVALID"),
            ({"request_id": "r", "transcript": "x", "label": 0}, "E_INVALID_REQUEST"),
        ]
        for request, code in cases:
            response = service.predict(request)
            self.assertEqual(response["error"]["code"], code)
            self.assertIsNone(response["label"])
            self.assertIsNone(response["probabilities"])
        failed = self.make_service(prepare=lambda _: (_ for _ in ()).throw(ValueError()))[0]
        response = failed.predict({"request_id": "r", "transcript": "x"})
        self.assertEqual(response["error"]["code"], "E_PREPROCESSING_FAILED")
        self.assertIsNone(response["label"])
        class BadProbabilityTorch(FakeTorch):
            @staticmethod
            def softmax(tensor, dim=-1):
                return Tensor([[0.2, 0.2]])
        bad, _ = self.make_service(FakeModel((1.0, 2.0)))
        bad.torch = BadProbabilityTorch
        response = bad.predict({"request_id": "r", "transcript": "x"})
        self.assertEqual(response["error"]["code"], "E_INVALID_OUTPUT")
        for request in ({"transcript": "x"}, {"request_id": " ", "transcript": "x"},
                        {"request_id": 17, "transcript": "x"}):
            response = service.predict(request)
            self.assertEqual(response["error"]["code"], "E_INVALID_REQUEST")
            self.assertIsNone(response["request_id"])

    def test_manifest_creation_and_tamper_detection(self):
        config = {"models": {"xlmr": {"checkpoint": "repo", "revision": "commit"}}}
        config_bytes = json.dumps(config).encode()
        identity = {
            "candidate": "xlmr", "checkpoint": "repo", "revision": "commit",
            "model_code_revision": "commit", "tokenizer_revision": "commit",
            "preprocessing_config_sha256": hashlib.sha256(config_bytes).hexdigest(),
            "input_component_path": "runtime/inputs.py",
            "input_component_sha256": hashlib.sha256(b"synthetic shared preparation").hexdigest(),
            "label_mapping": {"Not Scam": 0, "Scam": 1}, "threshold": 0.5,
            "dependencies": {"transformers": "pinned"}, "license": "recorded license",
            "runtime_requirements": {"device": "host-configurable"},
            "evaluation_identity": {},
            "bundle_id": "synthetic-test", "weights_path": "model/model.safetensors",
            "preprocessing_config_path": "inputs.json",
            "tokenizer_path": "model/tokenizer.json", "model_config_path": "model/config.json",
            "model_directory": "model",
        }
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            (bundle / "model").mkdir()
            (bundle / "model/model.safetensors").write_bytes(b"synthetic only")
            (bundle / "inputs.json").write_bytes(config_bytes)
            (bundle / "model/tokenizer.json").write_text("synthetic tokenizer")
            model_config = {"num_labels": 2, "id2label": {"0": "Not Scam", "1": "Scam"},
                            "label2id": {"Not Scam": 0, "Scam": 1}}
            (bundle / "model/config.json").write_text(json.dumps(model_config))
            (bundle / "model/artifact_manifest.json").write_text("synthetic internal manifest")
            (bundle / "runtime").mkdir()
            (bundle / "runtime/inputs.py").write_bytes(b"synthetic shared preparation")
            manifest = build_manifest(bundle, identity, ["model/model.safetensors", "inputs.json",
                "model/tokenizer.json", "model/config.json", "model/artifact_manifest.json", "runtime/inputs.py"])
            self.assertEqual(manifest["bundle_status"], "pending_parity")
            self.assertEqual(validate_manifest(bundle, manifest), [])
            fabricated = {**identity, "evaluation_identity": {
                "artifact_id": "caller-supplied", "weights_sha256": hashlib.sha256(b"synthetic only").hexdigest(),
                "selected_config_sha256": "a" * 64, "final_evaluation_report_sha256": "b" * 64}}
            with self.assertRaisesRegex(ValueError, "derived from completed evaluation records"):
                build_manifest(bundle, fabricated, ["model/model.safetensors", "inputs.json",
                    "model/tokenizer.json", "model/config.json", "model/artifact_manifest.json", "runtime/inputs.py"])
            (bundle / "model/model.safetensors").write_bytes(b"changed")
            self.assertTrue(any("checksum mismatch" in error
                                for error in validate_manifest(bundle, manifest)))

    def test_bundle_assembly_preserves_native_model_bytes(self):
        config = {"models": {"xlmr": {"checkpoint": "repo", "revision": "commit"}}}
        config_bytes = json.dumps(config).encode()
        native_weights = b"native synthetic safetensors bytes"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "final_model"
            source.mkdir()
            (source / "model.safetensors").write_bytes(native_weights)
            (source / "config.json").write_text(json.dumps({"num_labels": 2,
                "id2label": {"0": "Not Scam", "1": "Scam"}, "label2id": {"Not Scam": 0, "Scam": 1}}))
            (source / "tokenizer_config.json").write_text("{}")
            (source / "tokenizer.json").write_text("synthetic tokenizer")
            source_files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in source.iterdir() if p.is_file()}
            (source / "artifact_manifest.json").write_text(json.dumps({
                "schema_version": 1, "run_id": "synthetic-run", "configuration_id": "synthetic-config",
                "assignments_sha256": "a" * 64, "training_membership_sha256": "b" * 64,
                "num_labels": 2, "model": "xlmr", "checkpoint_id": "repo",
                "checkpoint_revision": "commit", "custom_code_revision": None,
                "preprocessing_config_sha256": hashlib.sha256(config_bytes).hexdigest(),
                "id2label": {"0": "Not Scam", "1": "Scam"}, "files": source_files}))
            config_source = root / "approved-inputs.json"
            config_source.write_bytes(config_bytes)
            identity = {
                "candidate": "xlmr", "checkpoint": "repo", "revision": "commit",
                "model_code_revision": "commit", "tokenizer_revision": "commit",
                "preprocessing_config_sha256": hashlib.sha256(config_bytes).hexdigest(),
                "label_mapping": {"Not Scam": 0, "Scam": 1}, "threshold": 0.5,
                "dependencies": {"transformers": "pinned"}, "license": "unresolved_pending_review",
                "runtime_requirements": {"device": "owner-configured"},
                "evaluation_identity": {"artifact_id": "final-test-report", "weights_sha256": hashlib.sha256(native_weights).hexdigest(),
                    "selected_config_sha256": "a" * 64, "final_evaluation_report_sha256": "b" * 64},
                "bundle_id": "synthetic-release", "weights_path": "model/model.safetensors",
                "preprocessing_config_path": "preprocessing_config.json", "tokenizer_path": "model/tokenizer.json",
                "model_config_path": "model/config.json", "model_directory": "model",
            }
            with self.assertRaisesRegex(ValueError, "completed final-evaluation directory"):
                assemble_bundle(source, root / "handoff_bundle", identity,
                                preprocessing_config_source=config_source,
                                evaluation_dir=root / "missing-evaluation",
                                review_audit_path=root / "missing-review-audit.json")
            self.assertFalse((root / "handoff_bundle").exists())

    def test_parity_requires_approved_tolerance_provenance_and_exact_inputs(self):
        approval = {"status": "approved", "atol": 1e-5, "reviewer": "owner", "reference": "approval note"}
        context = {"reference_artifact": {"artifact_id": "final-run", "weights_sha256": "b" * 64},
                   "packaged_manifest_sha256": "a" * 64,
                   "environment": {"python_version": "synthetic", "platform": "test", "device": "cpu",
                                   "package_versions": {"torch": "fake"}},
                   "fixture_provenance": {"source": "development", "fixture_ids": ["dev-1"]}}
        fixture = {"fixture_id": "dev-1", "transcript": "synthetic"}
        ref, _ = self.make_service(FakeModel((0.0, 1.0)))
        pkg, _ = self.make_service(FakeModel((0.0, 1.0)))
        ref.model_version = context["reference_artifact"]["artifact_id"]
        pkg.model_version = context["packaged_manifest_sha256"]
        ref.checkpoint_prepare = pkg.checkpoint_prepare = lambda text, *_: text
        result = run_live_parity([fixture], ref, pkg, approved_tolerance=approval, comparison_context=context)
        self.assertTrue(result["passed"])
        with self.assertRaises(ValueError):
            run_live_parity([], ref, pkg, approved_tolerance=approval, comparison_context=context)
        with self.assertRaises(ValueError):
            run_live_parity([fixture], ref, pkg, approved_tolerance={**approval, "atol": float("nan")},
                            comparison_context=context)
        broken, _ = self.make_service(FakeModel((0.0, 1.0)))
        broken.model_version = context["reference_artifact"]["artifact_id"]
        broken.model_version = context["packaged_manifest_sha256"]
        broken.checkpoint_prepare = lambda text, *_: text
        broken.pad_batch = lambda items, tokenizer: {"inputs": {"input_ids": [[1]], "attention_mask": [[1]]}}
        broken.prepare_text = lambda *args, **kwargs: {"inputs": {"input_ids": [[1, 2]], "attention_mask": [[1, 0]]},
                                                       "notices": {"truncated": False}}
        failed = run_live_parity([fixture], ref, broken, approved_tolerance=approval,
                                 comparison_context=context)
        self.assertFalse(failed["passed"])
        self.assertTrue(any("attention_mask" in item for item in failed["mismatches"]))

        class Counter:
            calls = 0
            def predict_with_trace(self, request):
                self.calls += 1
                return ref.predict_with_trace(request)
        counter = Counter()
        with self.assertRaises(ValueError):
            run_live_parity([fixture], counter, pkg, approved_tolerance={"status": "pending"},
                            comparison_context=context)
        self.assertEqual(counter.calls, 0)

    def test_parity_fixture_selector_refuses_final_test_membership(self):
        with tempfile.TemporaryDirectory() as tmp:
            assignments = Path(tmp) / "split_assignments.csv"
            assignments.write_text("sample_id,source_dataset,group_id,split,cv_fold\ntrain-1,primary,g1,train,0\ntest-1,primary,g2,test,\n")
            records = [{"sample_id": "train-1", "transcript": "development only"}]
            fixtures, provenance = training_pool_fixtures(records, ["train-1"], assignments)
            self.assertEqual(fixtures[0]["transcript"], "development only")
            self.assertEqual(provenance["fixture_ids"], ["train-1"])
            self.assertEqual(len(provenance["assignments_sha256"]), 64)
            with self.assertRaises(ValueError):
                training_pool_fixtures(records, ["test-1"], assignments)

    def test_parity_rejects_transcript_mismatch_even_if_traces_and_scores_match(self):
        approval = {"status": "approved", "atol": 0.0, "reviewer": "owner", "reference": "approval"}
        context = {"reference_artifact": {"artifact_id": "run:artifact", "weights_sha256": "a" * 64},
                   "packaged_manifest_sha256": "b" * 64,
                   "environment": {"python_version": "test", "platform": "test", "device": "cpu",
                                   "package_versions": {"torch": "test"}},
                   "fixture_provenance": {"source": "development", "fixture_ids": ["dev-1"]}}
        record = {"fixture_id": "dev-1", "transcript": "source text",
                  "response": {"status": "success", "threshold": 0.5, "label": "Scam",
                               "probabilities": {"Not Scam": 0.1, "Scam": 0.9}},
                  "trace": {"prepared_text": "source text", "unpadded_input_ids": [1],
                            "attention_mask": [1], "padded_model_inputs": {"input_ids": [[1]]},
                            "batching": {"request_batch_size": 1}}}
        other = json.loads(json.dumps(record))
        other["transcript"] = "different source text"
        result = compare_parity([record], [other], approved_tolerance=approval,
                                comparison_context=context)
        self.assertFalse(result["passed"])
        self.assertIn("fixture[0].transcript_mismatch", result["mismatches"])

    def test_final_evaluation_adapter_only_maps_request_and_trace_names(self):
        class ExistingEvaluationPath:
            model_version = "evaluation-artifact"
            def predict_with_trace(self, request):
                self.request = request
                return ({"request_id": request["request_id"], "status": "success",
                         "label": "Scam", "probabilities": {"Not Scam": 0.2, "Scam": 0.8}},
                        {"prepared_text": "prepared", "unpad_input_ids": [1, 2],
                         "unpad_attention_mask": [1, 1], "batched_inputs": {"input_ids": [1, 2]},
                         "request_batch_size": 1, "padding": "right", "padded_length": 2})
        baseline = ExistingEvaluationPath()
        response, trace = FinalEvaluationAdapter(baseline).predict_with_trace(
            {"request_id": "dev", "transcript": "text"})
        self.assertEqual(baseline.request, {"request_id": "dev", "text": "text"})
        self.assertEqual(trace["unpadded_input_ids"], [1, 2])
        self.assertEqual(trace["padded_model_inputs"], {"input_ids": [1, 2]})
        self.assertEqual(trace["batching"]["padding"], "right")
        self.assertEqual(response["label"], "Scam")


if __name__ == "__main__":
    unittest.main()
