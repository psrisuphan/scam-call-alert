"""Test Stage 02 mechanisms without using held-out project transcripts."""
from copy import deepcopy
from pathlib import Path
import csv
import json
import tempfile
import os
from unittest.mock import patch
import unittest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import inputs

# Fail the verification run if any check tries to load actual held-out rows.
# Synthetic final-test fixtures under temporary directories remain allowed.
_read_csv = inputs.read_csv

def training_only_read_csv(path, columns):
    if Path(path).resolve() == (inputs.DEFAULT_DATA / "1 - test/dataset.csv").resolve():
        raise AssertionError("Plan 02 checks must not read project held-out transcripts")
    return _read_csv(path, columns)

inputs.read_csv = training_only_read_csv
import importlib.util
spec = importlib.util.spec_from_file_location("measure_lengths", Path(__file__).with_name("7.measure_lengths.py"))
measure_lengths = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measure_lengths)
PREPARED = Path(os.environ.get("SCAM_INPUT_CHECK_EXPORT", inputs.DEFAULT_CONFIG.parent / "prepared"))
LENGTH_REPORT = Path(os.environ.get("SCAM_INPUT_CHECK_LENGTHS", inputs.DEFAULT_CONFIG.with_name("token_length_report.json")))


def write_csv(path, columns, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def row(cid, source="primary", text="ผู้โทร: OTP 123456? ผู้รับ: ไม่"):
    return dict(zip(inputs.COLUMNS, (cid, source, cid, "1", "Scam", text)))


class InputTests(unittest.TestCase):
    def test_representations_and_nested_parentheses(self):
        record = row("synthetic", text="ผู้รับ: สวัสดี ผู้โทร : ไม่ส่ง OTP 123456 https://example.com ผู้รับ: ไม่ส่ง")
        self.assertEqual(inputs.representation(record, "whole_conversation"),
                         "[Receiver]: สวัสดี\n[Caller]: ไม่ส่ง OTP 123456 https://example.com\n[Receiver]: ไม่ส่ง")
        self.assertEqual(inputs.representation(record, "caller_only"),
                         "[Caller]: ไม่ส่ง OTP 123456 https://example.com")
        record = row("synthetic", "supplemental", "[Call](ส่ง (OTP) 123456) [User](ไม่)")
        self.assertEqual(inputs.parse_turns(record), [("Caller", "ส่ง (OTP) 123456"), ("Receiver", "ไม่")])
        self.assertEqual(record["transcript"], "[Call](ส่ง (OTP) 123456) [User](ไม่)")
        self.assertEqual(inputs.parse_turns(row("synthetic", "supplemental", "[Call](ข้อความเดียว)")),
                         [("Caller", "ข้อความเดียว")])

    def test_unresolved_or_malformed_roles_fail(self):
        for text in ("สวัสดี ผู้โทร: ไม่", "ผู้โทร: สวัสดี R: ไม่",
                     "ผู้โทร: สวัสดี ผู้รับ:", "Scammer: สวัสดี",
                     "ผู้โทร: ข้อความ Scammer: ไม่"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                inputs.parse_turns(row("synthetic", text=text))
        with self.assertRaisesRegex(ValueError, "wrapper"):
            inputs.parse_turns(row("synthetic", "supplemental", "[Call](ไม่ได้ปิด"))
        with self.assertRaises(ValueError):
            inputs.representation(row("synthetic"), "unknown")

    def test_partition_membership_and_training_condition(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            records = [row("a"), row("b", "supplemental", "[Call](OTP 123456)"), row("c")]
            assignments = [
                {"sample_id": "a", "source_dataset": "primary", "group_id": "a", "split": "train", "cv_fold": "0"},
                {"sample_id": "b", "source_dataset": "supplemental", "group_id": "b", "split": "train", "cv_fold": "1"},
                {"sample_id": "c", "source_dataset": "primary", "group_id": "c", "split": "train", "cv_fold": "1"},
                {"sample_id": "t", "source_dataset": "primary", "group_id": "t", "split": "test", "cv_fold": ""}]
            write_csv(root / "0 - train/dataset.csv", inputs.COLUMNS, records)
            write_csv(root / "split_assignments.csv", inputs.ASSIGNMENT_COLUMNS, assignments)
            config = {"training_csv_sha256": inputs.checksum(root / "0 - train/dataset.csv"),
                      "assignments_sha256": inputs.checksum(root / "split_assignments.csv")}
            self.assertEqual([r["sample_id"] for r in inputs.load_partition("fold_train", data=root, fold=0,
                condition="primary_only", config=config)], ["c"])
            first = inputs.load_partition("fold_validation", data=root, fold=1, condition="primary_only", config=config)
            second = inputs.load_partition("fold_validation", data=root, fold=1, config=config)
            self.assertEqual(first, second)
            self.assertEqual([r["sample_id"] for r in first], ["b", "c"])
            with self.assertRaisesRegex(ValueError, "authorization"):
                inputs.load_partition("test", data=root, config=config)
            # Explicit test loading is exercised with invented data only.
            write_csv(root / "1 - test/dataset.csv", inputs.COLUMNS, [row("t")])
            config["test_csv_sha256"] = inputs.checksum(root / "1 - test/dataset.csv")
            self.assertEqual(len(inputs.load_partition("test", data=root, allow_final_test=True, config=config)), 1)
            altered = row("t", text="ผู้โทร: changed content")
            write_csv(root / "1 - test/dataset.csv", inputs.COLUMNS, [altered])
            with self.assertRaisesRegex(ValueError, "Test records differ"):
                inputs.load_partition("test", data=root, allow_final_test=True, config=config)
            records[0]["source_dataset"] = "supplemental"
            write_csv(root / "0 - train/dataset.csv", inputs.COLUMNS, records)
            with self.assertRaisesRegex(ValueError, "configured"):
                inputs.load_partition("train_pool", data=root, config=config)
            config["training_csv_sha256"] = inputs.checksum(root / "0 - train/dataset.csv")
            with self.assertRaisesRegex(ValueError, "source identities"):
                inputs.load_partition("train_pool", data=root, config=config)

    def test_label_maps_and_approval_gates(self):
        self.assertEqual({inputs.ID_TO_LABEL[v]: v for v in inputs.ID_TO_LABEL}, inputs.LABEL_TO_ID)
        config = inputs.load_config()
        config["role_review"]["status"] = "pending"
        with self.assertRaisesRegex(ValueError, "Source-role"):
            inputs.tokenized_record(row("synthetic"), "whole_conversation", "hplt", config, None)
        config["role_review"]["status"] = "approved"
        config["models"]["hplt"]["length_policy"]["status"] = "pending"
        with self.assertRaisesRegex(ValueError, "Length policy"):
            inputs.tokenized_record(row("synthetic"), "whole_conversation", "hplt", config, None)
        config["models"]["wangchanberta"]["checkpoint_preparation"]["status"] = "pending"
        with self.assertRaisesRegex(ValueError, "Checkpoint-specific"):
            inputs.tokenized_record(row("synthetic"), "whole_conversation", "wangchanberta", config, None)

    def test_training_population_checks(self):
        config = inputs.load_config()
        rows = inputs.load_partition("train_pool")
        self.assertEqual(len(rows), 1164)
        successes, pending = 0, []
        for record in rows:
            try:
                turns = inputs.parse_turns(record)
                caller = inputs.representation(record, "caller_only")
                self.assertEqual(caller, "\n".join(f"[Caller]: {body}" for role, body in turns if role == "Caller"))
                self.assertNotIn("source_dataset", caller)
                successes += 1
            except ValueError:
                pending.append(record["sample_id"])
        self.assertEqual((successes, pending), (1164, []))
        recovery_row = next(r for r in rows if r["sample_id"] == "hf_000424")
        before = recovery_row["transcript"]
        turns = inputs.parse_turns(recovery_row, config)
        caller = next(body for role, body in turns if role == "Caller" and "Windows" in body)
        self.assertTrue(caller.endswith("Windows บวกกับR"))
        self.assertTrue(any(role == "Receiver" and body.startswith("โอเค") for role, body in turns))
        self.assertEqual(recovery_row["transcript"], before)
        altered = dict(recovery_row, transcript=before + " changed")
        with self.assertRaisesRegex(ValueError, "source text has changed"):
            inputs.parse_turns(altered, config)
        for cid in config["role_review"]["trailing_empty_turns"]["sample_ids"]:
            record = next(r for r in rows if r["sample_id"] == cid)
            self.assertEqual(inputs.parse_turns(record, config)[-1][1], "")
        for alias, role in config["role_review"]["proposals"].items():
            text = f"ผู้โทร: สวัสดี {alias}: ไม่ส่ง OTP 123456"
            self.assertEqual(inputs.parse_turns(row("synthetic", text=text), config)[-1],
                             (role, "ไม่ส่ง OTP 123456"))
        for fold in range(5):
            first = inputs.load_partition("fold_validation", fold=fold, condition="primary_only")
            second = inputs.load_partition("fold_validation", fold=fold)
            self.assertEqual(first, second)
            train = inputs.load_partition("fold_train", fold=fold, condition="primary_only")
            self.assertTrue(all(r["source_dataset"] == "primary" for r in train))
            self.assertTrue({r["sample_id"] for r in train}.isdisjoint(r["sample_id"] for r in first))

    def test_training_length_report(self):
        summary = measure_lengths.summarize([10, 416, 420], 416, 2)
        self.assertEqual(summary["exceeding_budget"], 1)
        self.assertEqual(summary["estimated_dropped_content_tokens"], 4)
        self.assertEqual(summary["estimated_dropped_content_percent"], .48)
        self.assertEqual(summary["p90"], 419.2)
        config = inputs.load_config()
        report = json.loads(LENGTH_REPORT.read_text())
        self.assertEqual(report["population"], 1164)
        self.assertEqual(report["configuration_sha256"], inputs.checksum(inputs.DEFAULT_CONFIG))
        self.assertEqual(report["training_csv_sha256"], config["training_csv_sha256"])
        self.assertEqual(report["assignments_sha256"], config["assignments_sha256"])
        for model, entry in report["models"].items():
            self.assertEqual(entry["revision"], config["models"][model]["revision"])
            self.assertEqual(set(entry["representations"]),
                             {f"{mode}.{marker}" for mode in config["representations"]
                              for marker in config["marker_conditions"]})
            for mode, values in entry["representations"].items():
                self.assertEqual(values["all"]["records"], 1164)
                self.assertEqual(sum(values["subsets"][source]["records"] for source in (
                    "primary", "supplemental")), 1164)
                self.assertEqual(values["all"]["budget"],
                                 config["models"][model]["length_policy"]["max_length"])
                if mode.startswith("caller_only."):
                    self.assertEqual(values["all"]["exceeding_budget"], 0)
        self.assertTrue(all(e["length_policy"]["status"] == "approved" for e in config["models"].values()))
        self.assertEqual(config["truncation_side"], "right")
        self.assertEqual(config["models"]["wangchanberta"]["length_policy"]["max_length"], 510)

    def test_checkpoint_text_preserves_evidence(self):
        config = inputs.load_config()
        record = row("synthetic", text="ผู้โทร: OTP 111111 ไม่ ไม่ ส่ง ผู้รับ: ไม่")
        plain = inputs.representation(record, "whole_conversation", config)
        for model in config["models"]:
            expected = plain.replace("\n", " ").replace(" ", "<_>") if model in (
                "wangchanberta", "phayathaibert") else plain
            self.assertEqual(inputs.checkpoint_text(record, "whole_conversation", model, config), expected)
        self.assertEqual(record["transcript"], "ผู้โทร: OTP 111111 ไม่ ไม่ ส่ง ผู้รับ: ไม่")

    def test_approved_inputs_for_full_training_pool(self):
        config = inputs.load_config()
        records = inputs.load_partition("train_pool", config=config)
        before = [dict(record) for record in records]
        for model, entry in config["models"].items():
            tokenizer = inputs.load_tokenizer(model, config, local_files_only=True)
            limit = entry["length_policy"]["max_length"]
            for mode in config["representations"]:
                for marker_condition in config["marker_conditions"]:
                    with self.subTest(model=model, representation=mode, marker_condition=marker_condition):
                        saved = [json.loads(line) for line in (PREPARED / f"{model}.{mode}.{marker_condition}.jsonl").read_text().splitlines()]
                        self.assertEqual(len(saved), len(records))
                        saved_by_id = {item["sample_id"]: item for item in saved}
                        assignments = {r["sample_id"]: r for r in inputs.read_csv(
                            inputs.DEFAULT_DATA / "split_assignments.csv", inputs.ASSIGNMENT_COLUMNS)}
                        items = []
                        exceeding, dropped = 0, 0
                        for record in records:
                            item = inputs.tokenized_record(record, mode, model, config, tokenizer, marker_condition=marker_condition)
                            full = tokenizer(inputs.checkpoint_text(record, mode, model, config, marker_condition=marker_condition),
                                             add_special_tokens=True, padding=False, truncation=False,
                                             return_special_tokens_mask=True, verbose=False)
                            self.assertEqual(full["special_tokens_mask"][0], 1)
                            self.assertEqual(full["special_tokens_mask"][-1], 1)
                            self.assertEqual(sum(full["special_tokens_mask"]), 2)
                            expected = full["input_ids"]
                            if len(expected) > limit:
                                exceeding += 1
                                dropped += len(expected) - limit
                                expected = expected[:limit - 1] + expected[-1:]
                            self.assertEqual(item["inputs"]["input_ids"], expected)
                            self.assertEqual(item["inputs"]["attention_mask"], [1] * len(expected))
                            self.assertEqual(item["notices"], {
                                "original_token_count": len(full["input_ids"]),
                                "prepared_token_count": len(expected),
                                "dropped_token_count": len(full["input_ids"]) - len(expected),
                                "truncated": len(full["input_ids"]) > limit})
                            self.assertEqual(set(item["inputs"]), set(entry["model_input_fields"]))
                            self.assertEqual(item["sample_id"], record["sample_id"])
                            self.assertEqual(item["label"], inputs.LABEL_TO_ID[record["label"]])
                            stored = dict(saved_by_id[record["sample_id"]])
                            membership = assignments[record["sample_id"]]
                            self.assertEqual(stored.pop("split"), "train")
                            self.assertEqual(stored.pop("cv_fold"), int(membership["cv_fold"]))
                            self.assertEqual(stored.pop("group_id"), membership["group_id"])
                            self.assertEqual(stored.pop("source_dataset"), record["source_dataset"])
                            self.assertEqual(stored, item)
                            items.append(item)
                        summary = json.loads(LENGTH_REPORT.read_text())[
                            "models"][model]["representations"][f"{mode}.{marker_condition}"]["all"]
                        self.assertEqual(exceeding, summary["exceeding_budget"])
                        self.assertEqual(dropped, summary["estimated_dropped_content_tokens"])
                        self.assertEqual(len(items), 1164)
                        self.assertEqual(len({item["sample_id"] for item in items}), 1164)
                        self.assertEqual(len({item["configuration_id"] for item in items}), 1)
                        # Different lengths in a real-record batch must be padded only
                        # to the longest item, with compatible IDs and masks.
                        batch = [min(items, key=lambda item: len(item["inputs"]["input_ids"])),
                                 max(items, key=lambda item: len(item["inputs"]["input_ids"]))]
                        padded = inputs.pad_batch(batch, tokenizer)
                        width = max(len(item["inputs"]["input_ids"]) for item in batch)
                        for item, ids, mask in zip(batch, padded["inputs"]["input_ids"],
                                                    padded["inputs"]["attention_mask"]):
                            size = len(item["inputs"]["input_ids"])
                            self.assertEqual(ids, item["inputs"]["input_ids"] + [tokenizer.pad_token_id] * (width - size))
                            self.assertEqual(mask, [1] * size + [0] * (width - size))
        self.assertEqual(records, before)

    def test_readable_export_manifest_and_rebuild(self):
        config = inputs.load_config()
        folder = PREPARED
        manifest = json.loads((folder / "manifest.json").read_text())
        self.assertEqual(manifest["records"], 1164)
        expected_files = {f"{model}.{mode}.{marker}.jsonl" for model in config["models"]
                          for mode in config["representations"] for marker in config["marker_conditions"]}
        self.assertEqual(set(manifest["files"]), expected_files | {"training_text.csv"})
        self.assertEqual(manifest["marker_conditions"], config["marker_conditions"])
        self.assertEqual(manifest["configuration_sha256"], inputs.checksum(inputs.DEFAULT_CONFIG))
        self.assertEqual(manifest["component_sha256"], inputs.checksum(Path(inputs.__file__)))
        self.assertEqual(manifest["export_script_sha256"], inputs.checksum(Path(__file__).with_name("8.export_inputs.py")))
        for name, entry in manifest["files"].items():
            self.assertEqual(inputs.checksum(folder / name), entry["sha256"])
        with (folder / "training_text.csv").open(encoding="utf-8", newline="") as file:
            readable = list(csv.DictReader(file))
        records = inputs.load_partition("train_pool", config=config)
        self.assertEqual(len(readable), len(records))
        for stored, record in zip(readable, records):
            self.assertEqual(stored["sample_id"], record["sample_id"])
            self.assertEqual(stored["original_transcript"], record["transcript"])
            self.assertEqual(int(stored["label_id"]), inputs.LABEL_TO_ID[record["label"]])
            for mode in config["representations"]:
                for marker in config["marker_conditions"]:
                    self.assertEqual(stored[f"{mode}.{marker}"], inputs.representation(
                        record, mode, config, marker_condition=marker))
        spec = importlib.util.spec_from_file_location("export_inputs", Path(__file__).with_name("8.export_inputs.py"))
        exporter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(exporter)
        with tempfile.TemporaryDirectory(prefix="scam-input-export-test-") as temporary:
            target = Path(temporary) / "prepared"
            exporter.export(target)
            self.assertEqual({p.name: inputs.checksum(p) for p in target.iterdir()},
                             {p.name: inputs.checksum(p) for p in folder.iterdir()})
            with self.assertRaisesRegex(FileExistsError, "separate output"):
                exporter.export(target)

    def test_real_tokenizers_and_dynamic_padding_on_synthetic_inputs(self):
        config = inputs.load_config()
        for model in config["models"]:
            with self.subTest(model=model):
                tokenizer = inputs.load_tokenizer(model, config, local_files_only=True)
                self.assertEqual(tokenizer.num_special_tokens_to_add(), config["models"][model]["special_tokens_count"])
                # A small synthetic budget exercises truncation and padding without
                # changing the saved owner-approved project configuration.
                synthetic = deepcopy(config)
                synthetic["role_review"]["status"] = "approved"
                synthetic["models"][model]["checkpoint_preparation"] = {"status": "approved", "method": "native_tokenizer"}
                synthetic["models"][model]["length_policy"] = {"status": "approved", "kind": "fixed_prefix", "max_length": 8}
                prepared = inputs.tokenized_record(row("synthetic"), "whole_conversation", model, synthetic, tokenizer)
                caller = inputs.tokenized_record(row("synthetic"), "caller_only", model, synthetic, tokenizer)
                self.assertLessEqual(len(prepared["inputs"]["input_ids"]), 8)
                self.assertEqual(prepared["label"], 1)
                self.assertNotEqual(prepared["configuration_id"], caller["configuration_id"])
                self.assertEqual(set(prepared["inputs"]), {"input_ids", "attention_mask"})
                samples = [row("invented_a"), row("invented_b", text="ผู้โทร: สวัสดี")]
                items = []
                for sample in samples:
                    text = inputs.representation(sample, "whole_conversation")
                    encoded = tokenizer(text, add_special_tokens=True, padding=False, truncation=False)
                    items.append({"inputs": dict(encoded), "sample_id": sample["sample_id"], "label": 1,
                                  "configuration_id": model, "padding_contract": inputs.padding_contract(tokenizer)})
                result = inputs.pad_batch(items, tokenizer)
                width = max(len(item["inputs"]["input_ids"]) for item in items)
                self.assertTrue(all(len(ids) == width for ids in result["inputs"]["input_ids"]))
                for item, mask, ids in zip(items, result["inputs"]["attention_mask"], result["inputs"]["input_ids"]):
                    size = len(item["inputs"]["input_ids"])
                    self.assertEqual(mask, [1]*size + [0]*(width-size))
                    self.assertEqual(ids[:size], item["inputs"]["input_ids"])
                    self.assertEqual(ids[size:], [tokenizer.pad_token_id]*(width-size))
                self.assertNotIn("sample_ids", result["inputs"])
                items[0]["configuration_id"] = "different"
                with self.assertRaisesRegex(ValueError, "mixes"):
                    inputs.pad_batch(items, tokenizer)

    def test_role_free_rendering_preserves_spoken_role_words(self):
        record = row("synthetic", "supplemental",
                     "[User](พูดว่า [Caller]: และ Receiver เป็นคำในบทสนทนา) [Call](ไม่ส่ง OTP 111111 ไม่ ไม่)")
        self.assertEqual(inputs.representation(record, "whole_conversation", marker_condition="role_free"),
                         "พูดว่า [Caller]: และ Receiver เป็นคำในบทสนทนา\nไม่ส่ง OTP 111111 ไม่ ไม่")
        self.assertEqual(inputs.representation(record, "caller_only", marker_condition="role_free"),
                         "ไม่ส่ง OTP 111111 ไม่ ไม่")
        with self.assertRaises(ValueError):
            inputs.representation(record, "whole_conversation", marker_condition="unknown")

    def test_unlabeled_interface_and_dataset_parity(self):
        config = inputs.load_config()
        records = inputs.load_partition("train_pool", config=config)
        for model in config["models"]:
            tokenizer = inputs.load_tokenizer(model, config, local_files_only=True)
            for record in records:
                text = inputs.representation(record, "whole_conversation", config, marker_condition="role_free")
                direct = inputs.prepare_text(text, model, config, tokenizer)
                dataset = inputs.tokenized_record(record, "whole_conversation", model, config, tokenizer,
                                                  marker_condition="role_free")
                self.assertEqual(dataset, dict(direct, label=inputs.LABEL_TO_ID[record["label"]],
                                               sample_id=record["sample_id"]))
            with patch.object(inputs, "parse_turns", side_effect=AssertionError("STT must not parse roles")), \
                 patch.object(inputs, "load_partition", side_effect=AssertionError("STT must not load data")):
                text = "ผู้โทร: spoken text [Caller]: ไม่ส่ง OTP 111111 ไม่ ไม่"
                item = inputs.prepare_text(text, model, config, tokenizer)
                expected = tokenizer(inputs.checkpoint_prepare_text(text, model, config),
                                     add_special_tokens=True, padding=False, truncation=True,
                                     max_length=config["models"][model]["length_policy"]["max_length"])
                self.assertEqual(item["inputs"]["input_ids"], expected["input_ids"])
                self.assertNotIn("label", item)
                self.assertNotIn("sample_id", item)
                padded = inputs.pad_batch([item], tokenizer)
                self.assertNotIn("labels", padded)
                for bad in (None, "", "   "):
                    with self.assertRaises(ValueError):
                        inputs.prepare_text(bad, model, config, tokenizer)

    def test_marker_removal_before_truncation_and_condition_identity(self):
        config = inputs.load_config()
        record = row("synthetic", text="ผู้โทร: สวัสดี ไม่ ส่ง OTP 111111 ผู้รับ: ไม่ ไม่")
        for model in config["models"]:
            tokenizer = inputs.load_tokenizer(model, config, local_files_only=True)
            config["models"][model]["length_policy"]["max_length"] = 8
            items = [inputs.tokenized_record(record, mode, model, config, tokenizer, marker_condition=marker)
                     for mode in config["representations"] for marker in config["marker_conditions"]]
            self.assertEqual(len({item["configuration_id"] for item in items}), 4)
            for item in items:
                text = inputs.checkpoint_text(record, item["representation"], model, config,
                                              marker_condition=item["marker_condition"])
                full = tokenizer(text, add_special_tokens=True, padding=False, truncation=False)
                expected = full["input_ids"]
                if len(expected) > 8:
                    expected = expected[:7] + expected[-1:]
                self.assertEqual(item["inputs"]["input_ids"], expected)
                self.assertEqual(item["notices"]["dropped_token_count"], len(full["input_ids"]) - len(expected))
                self.assertEqual(item["notices"]["truncated"], len(full["input_ids"]) > 8)
            with self.assertRaisesRegex(ValueError, "mixes configurations"):
                inputs.pad_batch(items[:2], tokenizer)

    def test_role_free_collision_review_and_source_hashes(self):
        config = inputs.load_config()
        records = inputs.load_partition("train_pool", config=config)
        seen = {}
        collisions = []
        for record in records:
            text = inputs.representation(record, "whole_conversation", config, marker_condition="role_free")
            if text in seen:
                collisions.append([seen[text], record["sample_id"]])
            else:
                seen[text] = record["sample_id"]
        self.assertEqual(collisions, [])
        self.assertEqual(inputs.checksum(inputs.DEFAULT_DATA / "0 - train/dataset.csv"), config["training_csv_sha256"])
        self.assertEqual(inputs.checksum(inputs.DEFAULT_DATA / "split_assignments.csv"), config["assignments_sha256"])

    def test_cache_retrieval_and_stale_rejection(self):
        config = inputs.load_config()
        records = inputs.load_partition("fold_train", fold=0, condition="primary_only", config=config)
        for model in config["models"]:
            for mode in config["representations"]:
                for marker in config["marker_conditions"]:
                    items = inputs.load_prepared(records, mode, model, config,
                                                 marker_condition=marker, folder=PREPARED)
                    self.assertEqual([item["sample_id"] for item in items], [r["sample_id"] for r in records])
        altered = deepcopy(records[0])
        altered["transcript"] += " changed"
        with self.assertRaisesRegex(ValueError, "unchanged training record"):
            inputs.load_prepared([altered], "whole_conversation", "hplt", config, folder=PREPARED)
        with self.assertRaisesRegex(ValueError, "Duplicate requested"):
            inputs.load_prepared([records[0], records[0]], "whole_conversation", "hplt", config, folder=PREPARED)
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            manifest = json.loads((PREPARED / "manifest.json").read_text())
            manifest["component_sha256"] = "outdated"
            (folder / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "Stale prepared manifest"):
                inputs.load_prepared(records, "whole_conversation", "hplt", config, folder=folder)
            manifest["component_sha256"] = inputs.checksum(Path(inputs.__file__))
            (folder / "manifest.json").write_text(json.dumps(manifest))
            (folder / "hplt.whole_conversation.role_marked.jsonl").write_text("tampered")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                inputs.load_prepared(records, "whole_conversation", "hplt", config, folder=folder)

    def test_length_report_and_export_refuse_replacement(self):
        with patch.object(sys, "argv", ["7.measure_lengths.py", "--output", str(LENGTH_REPORT)]), \
             patch.object(measure_lengths, "measure", side_effect=AssertionError("Do not recompute existing output")):
            with self.assertRaisesRegex(FileExistsError, "separate output"):
                measure_lengths.main()

    def test_wrong_tokenizer_and_vocabulary_changes_fail(self):
        config = inputs.load_config()
        tokenizer = inputs.load_tokenizer("wangchanberta", config, local_files_only=True)
        with self.assertRaisesRegex(ValueError, "Tokenizer differs"):
            inputs.prepare_text("ไม่ส่ง OTP 111111", "phayathaibert", config, tokenizer)
        tokenizer.add_tokens(["<scam-test-unapproved-token>"])
        with self.assertRaisesRegex(ValueError, "Tokenizer differs"):
            inputs.prepare_text("ไม่ส่ง OTP 111111", "wangchanberta", config, tokenizer)

    def test_length_report_exact_reproduction(self):
        self.assertEqual(measure_lengths.measure(inputs.load_config()), json.loads(LENGTH_REPORT.read_text()))

    def test_padding_rejects_wrong_checkpoint_or_changed_settings(self):
        config = inputs.load_config()
        correct = inputs.load_tokenizer("wangchanberta", config, local_files_only=True)
        items = [inputs.prepare_text(text, "wangchanberta", config, correct)
                 for text in ("ไม่ส่ง OTP 111111 ไม่ส่ง OTP 111111", "สวัสดี")]
        for model in ("phayathaibert", "hplt", "xlmr"):
            wrong = inputs.load_tokenizer(model, config, local_files_only=True)
            with self.assertRaisesRegex(ValueError, "padding differs"):
                inputs.pad_batch(items, wrong)
        for setting, value in (("padding_side", "left"), ("pad_token_id", 0), ("truncation_side", "left")):
            original = getattr(correct, setting)
            setattr(correct, setting, value)
            with self.assertRaisesRegex(ValueError, "padding differs"):
                inputs.pad_batch(items, correct)
            setattr(correct, setting, original)
        correct.add_tokens(["<unapproved-padding-vocabulary>"])
        with self.assertRaisesRegex(ValueError, "padding differs"):
            inputs.pad_batch(items, correct)

    def test_padding_requires_contract_and_valid_unpadded_fields(self):
        config = inputs.load_config()
        tokenizer = inputs.load_tokenizer("hplt", config, local_files_only=True)
        item = inputs.prepare_text("ไม่ส่ง OTP 111111", "hplt", config, tokenizer)
        altered = deepcopy(item)
        altered.pop("padding_contract")
        with self.assertRaisesRegex(ValueError, "padding differs"):
            inputs.pad_batch([altered], tokenizer)
        altered = deepcopy(item)
        altered["inputs"]["attention_mask"][0] = 0
        with self.assertRaisesRegex(ValueError, "unpadded inputs"):
            inputs.pad_batch([altered], tokenizer)
        altered = deepcopy(item)
        altered["inputs"]["attention_mask"].pop()
        with self.assertRaisesRegex(ValueError, "field lengths"):
            inputs.pad_batch([altered], tokenizer)
        self.assertNotIn("padding_contract", inputs.pad_batch([item], tokenizer)["inputs"])


if __name__ == "__main__":
    unittest.main()
