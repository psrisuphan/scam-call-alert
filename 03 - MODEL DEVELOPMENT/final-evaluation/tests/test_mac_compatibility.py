import importlib.util
import json
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "check_mac_compatibility.py"
spec = importlib.util.spec_from_file_location("mac_check", MODULE)
mac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mac)


def test_exact_host_and_stt_identity():
    mac.validate_host("Darwin", "arm64", {"machine_name": "MacBook Air", "chip_type": "Apple M2"})
    config = json.loads((mac.STT_DIR / "stt_config.json").read_text())
    assert mac.validate_stt(config, "2.3.0")["checkpoint_revision"] == mac.REVISION


@pytest.mark.parametrize("system,machine,name,chip", [
    ("Linux", "aarch64", "MacBook Air", "Apple M2"),
    ("Darwin", "x86_64", "MacBook Air", "Apple M2"),
    ("Darwin", "arm64", "MacBook Pro", "Apple M2"),
    ("Darwin", "arm64", "MacBook Air", "Apple M3"),
])
def test_other_hosts_fail(system, machine, name, chip):
    with pytest.raises(ValueError):
        mac.validate_host(system, machine, {"machine_name": name, "chip_type": chip})


@pytest.mark.parametrize("field,value", [
    ("checkpoint_revision", "main"),
    ("checkpoint", "another/model"),
    ("package_version", "2.2.0"),
])
def test_changed_stt_fails(field, value):
    config = json.loads((mac.STT_DIR / "stt_config.json").read_text())
    config["selected_candidate"][field] = value
    with pytest.raises(ValueError):
        mac.validate_stt(config, "2.3.0")


def test_audio_must_be_exactly_one_manifest_entry_inside_data_dir(tmp_path):
    manifest = tmp_path / "manifest.csv"
    manifest.write_text("audio_filename,audio_path\nclip.wav,audio/clip.wav\n")
    path, _ = mac.select_audio(manifest, "clip.wav", tmp_path)
    assert path == tmp_path / "audio/clip.wav"
    with pytest.raises(ValueError):
        mac.select_audio(manifest, "unknown.wav", tmp_path)
    manifest.write_text("audio_filename,audio_path\nclip.wav,../clip.wav\n")
    with pytest.raises(ValueError):
        mac.select_audio(manifest, "clip.wav", tmp_path)
    manifest.write_text("audio_filename,audio_path\nclip.wav,audio/clip.wav\nclip.wav,audio/clip.wav\n")
    with pytest.raises(ValueError):
        mac.select_audio(manifest, "clip.wav", tmp_path)
