import importlib.util
from pathlib import Path
import json
import pytest

spec = importlib.util.spec_from_file_location("reduced_evaluation", Path(__file__).parents[1]/"evaluation.py")
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)

def test_reduced_scope_requires_counts_and_bound_approval(tmp_path):
    p=tmp_path/"approval.md"
    p.write_text("owner-approved reduction")
    record={"main_fit_count":45,"excluded_main_fit_count":30,"caller_only_fit_count":0,"supplemental_fit_count":0,
            "scope_approval":{"status":"owner_approved","reference":"synthetic approval","path":str(p),"sha256":evaluation.sha256(p)}}
    evaluation.validate_selection_scope(record)
    for field,value in [("main_fit_count",120),("excluded_main_fit_count",0),("caller_only_fit_count",5),("supplemental_fit_count",5)]:
        with pytest.raises(ValueError):
            evaluation.validate_selection_scope({**record,field:value})
    p.write_text("changed")
    with pytest.raises(ValueError): evaluation.validate_selection_scope(record)

def test_mac_evidence_must_match_final_weights_and_development_partition(tmp_path):
    p=tmp_path/"compatibility.json"
    record={"status":"passed","host":"MacBook Air M2","stt_checkpoint":"airesearch/wav2vec2-large-xlsr-53-th",
            "stt_checkpoint_revision":"3155938c549b23eee16b1d4b55dcb161b7fe4bcf","audio_partition":"development",
            "execution_evidence":{"synthetic":True},"selected_config_sha256":"config","model_safetensors_sha256":"weights"}
    def auth():
        p.write_text(json.dumps(record))
        return {"selected_config_sha256":"config","model_safetensors_sha256":"weights",
                "mac_compatibility":{"path":str(p),"sha256":evaluation.sha256(p)}}
    evaluation.validate_mac_compatibility(auth())
    for field,value in [("status","pending"),("audio_partition","test"),("model_safetensors_sha256","other"),("host","Linux")]:
        original=record[field];record[field]=value
        with pytest.raises(ValueError): evaluation.validate_mac_compatibility(auth())
        record[field]=original
    with pytest.raises(ValueError): evaluation.validate_mac_compatibility({})

def test_scope_approval_recorded_on_another_host_relocates_but_stays_hash_bound(tmp_path, monkeypatch):
    plan=tmp_path/"01 - PLANs"/"approval.md"
    plan.parent.mkdir()
    plan.write_text("owner-approved reduction")
    monkeypatch.setattr(evaluation,"ROOT",tmp_path)
    record={"main_fit_count":45,"excluded_main_fit_count":30,"caller_only_fit_count":0,"supplemental_fit_count":0,
            "scope_approval":{"status":"owner_approved","reference":"synthetic approval",
                              "path":"/home/other-host/Projects/repo/01 - PLANs/approval.md","sha256":evaluation.sha256(plan)}}
    evaluation.validate_selection_scope(record)
    plan.write_text("changed")
    with pytest.raises(ValueError): evaluation.validate_selection_scope(record)
