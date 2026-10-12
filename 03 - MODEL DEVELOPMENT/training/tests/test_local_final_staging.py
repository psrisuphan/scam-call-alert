import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_factory import make_config
import trainer


def config(tmp_path):
    c = make_config(tmp_path)
    c.update(mode="final_training", fold=None)
    c["validation"] = {"enabled": False}
    c["selection"].update(final_candidate_approved=True, selected_config_sha256="synthetic",
        selection_report_sha256="synthetic", warmup_conversion_reference="approved-three-epoch-rule")
    c["training"]["epochs"] = 2
    c["paths"]["staging_runs"] = "/content/local-final-runs"
    c["persistence"] = {"mode": "local_first_verified_transfer", "owner_approved": True,
        "approval_reference": "owner-approved Plan 03/02 repair",
        "verified_transfer_required": True}
    c["approval"]["approved_settings_sha256"] = trainer.approved_settings_digest(c)
    return c


def test_approved_final_staging_is_digest_bound(tmp_path):
    c = config(tmp_path)
    trainer.validate_config(c)
    digest = trainer.approved_settings_digest(c)
    c["persistence"]["owner_approved"] = False
    assert trainer.approved_settings_digest(c) != digest


@pytest.mark.parametrize("change", ["unapproved", "no_transfer", "relative", "same_destination", "comparative"])
def test_invalid_staging_is_rejected(change, tmp_path):
    c = config(tmp_path)
    if change == "unapproved":
        c["persistence"]["owner_approved"] = False
    elif change == "no_transfer":
        c["persistence"]["verified_transfer_required"] = False
    elif change == "relative":
        c["paths"]["staging_runs"] = "local"
    elif change == "same_destination":
        c["paths"]["staging_runs"] = c["paths"]["persistent_runs"]
    else:
        c["mode"] = "comparative"; c["fold"] = 0
    c["approval"]["approved_settings_sha256"] = trainer.approved_settings_digest(c)
    with pytest.raises(ValueError):
        trainer.validate_config(c)
