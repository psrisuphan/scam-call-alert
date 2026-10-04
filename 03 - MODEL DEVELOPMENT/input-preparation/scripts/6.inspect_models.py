"""Verify pinned model documentation and download tokenizers only."""
from pathlib import Path
from huggingface_hub import hf_hub_download
import importlib.metadata

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import inputs


def main():
    config = inputs.load_config()
    for package, version in config["dependencies"].items():
        if importlib.metadata.version(package) != version:
            raise ValueError(f"Use {package}=={version} from preprocessing_config.json")
    for name, entry in config["models"].items():
        for filename, expected in entry["documentation_sha256"].items():
            path = Path(hf_hub_download(entry["checkpoint"], filename,
                revision=entry["revision"], token=False))
            if inputs.checksum(path) != expected:
                raise ValueError(f"Pinned documentation checksum mismatch: {name}/{filename}")
        tokenizer = inputs.load_tokenizer(name, config)
        print(f"{name}: {entry['revision']}; {type(tokenizer).__name__}; pad={tokenizer.pad_token_id}; config limit={entry['verified_config_limit']}")
    print("Pinned documentation and tokenizer assets verified. No model weights or remote code loaded.")


if __name__ == "__main__":
    main()
