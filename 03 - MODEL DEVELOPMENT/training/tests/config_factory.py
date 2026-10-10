"""Synthetic config fixtures for trainer tests; never used to authorize runs."""
from __future__ import annotations

import json
from pathlib import Path

import trainer

ROOT = Path(__file__).resolve().parents[3]


def make_config(temp_root: Path, *, full_context: bool = False) -> dict:
    config = json.loads(trainer.CONFIG_TEMPLATE.read_text(encoding="utf-8"))
    prep_path = ROOT / "03 - MODEL DEVELOPMENT/input-preparation/preprocessing_config.json"
    prep = json.loads(prep_path.read_text(encoding="utf-8"))
    checkpoint = prep["models"]["wangchanberta"]
    config.update({"run_id": "synthetic-training-test", "mode": "comparative", "model": "wangchanberta",
                  "checkpoint": {"id": checkpoint["checkpoint"], "revision": checkpoint["revision"],
                                 "custom_code_revision": None}, "fold": 0})
    config["approval"].update({"status": "owner_approved", "reference": "synthetic test fixture",
        "selection_protocol_approved": True, "selection_protocol_reference": "synthetic test protocol"})
    config["data"]["condition"] = "primary_only"
    config["training"].update({"representation": "whole_conversation", "marker_condition": "role_marked",
        "seed": 67, "epochs": 3, "effective_batch_size": 16, "microbatch_size": 8,
        "accumulation_steps": 2, "optimizer_updates_limit": None})
    config["validation"].update({"representation": "whole_conversation",
        "marker_conditions": ["role_marked", "role_free"]})
    config["optimizer"].update({"name": "AdamW", "learning_rate": 2e-5, "weight_decay": 0.01,
        "beta1": 0.9, "beta2": 0.999, "epsilon": 1e-8, "gradient_clip_norm": 1.0})
    config["schedule"].update({"name": "linear_warmup_then_constant", "warmup_updates": 0})
    config["precision"].update({"mode": "fp32", "auto_policy_approved": False})
    config["evaluation"]["scam_threshold"] = 0.5
    config["selection"].update({"max_epochs": 4, "grid_configuration_id": "synthetic-grid",
        "selection_protocol_reference": "synthetic test protocol"})
    config["runtime"].update({"device": "cpu", "local_files_only": True})
    config["paths"].update({
        "data": str(ROOT / "02 - DATASETs/prepared/splits"),
        "input_config": str(prep_path),
        "input_exports": str(ROOT / "03 - MODEL DEVELOPMENT/input-preparation/prepared"),
        "persistent_runs": str((temp_root / "runs").resolve()),
        "persistent_storage_verified": True,
        "storage_verification_reference": "synthetic test fixture",
    })
    if full_context:
        config["training"].update({"window_policy": "wangchan_full_context_v1", "pooling_method": "max"})
    config["approval"]["approved_settings_sha256"] = trainer.approved_settings_digest(config)
    return config
