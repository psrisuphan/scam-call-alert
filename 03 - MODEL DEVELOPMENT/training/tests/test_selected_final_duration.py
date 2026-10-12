"""Final duration is selected from common CV epochs, not the pilot target."""
import copy
import pytest
import trainer
from config_factory import make_config

def test_two_epoch_final_selection_keeps_approval_guards(tmp_path):
    config=make_config(tmp_path)
    config.update(mode="final_training",fold=None)
    config["training"]["epochs"]=2
    config["validation"]={"enabled":False}
    config["selection"].update(final_candidate_approved=True,selected_config_sha256="synthetic-config",
        selection_report_sha256="synthetic-report",warmup_conversion_reference="synthetic-rule")
    config["approval"]["approved_settings_sha256"]=trainer.approved_settings_digest(config)
    trainer.validate_config(config)
    unapproved=copy.deepcopy(config)
    unapproved["selection"]["final_candidate_approved"]=False
    unapproved["approval"]["approved_settings_sha256"]=trainer.approved_settings_digest(unapproved)
    with pytest.raises(ValueError):trainer.validate_config(unapproved)
    invalid=copy.deepcopy(config)
    invalid["training"]["epochs"]=0
    invalid["approval"]["approved_settings_sha256"]=trainer.approved_settings_digest(invalid)
    with pytest.raises(ValueError):trainer.validate_config(invalid)
