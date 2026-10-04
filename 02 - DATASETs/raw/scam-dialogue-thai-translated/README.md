---
size_categories: n<1K
dataset_info:
  features:
  - name: dialogue
    dtype: string
  - name: type
    dtype: string
  - name: label
    dtype: int64
  - name: translated dialogue
    dtype: string
  - name: translated type
    dtype: string
  splits:
  - name: train
    num_bytes: 6507916
    num_examples: 1280
  download_size: 2029004
  dataset_size: 6507916
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*
tags:
- synthetic
- distilabel
- rlaif
---

<p align="left">
  <a href="https://github.com/argilla-io/distilabel">
    <img src="https://raw.githubusercontent.com/argilla-io/distilabel/main/docs/assets/distilabel-badge-light.png" alt="Built with Distilabel" width="200" height="32"/>
  </a>
</p>

# Dataset Card for scam-dialogue-thai-translated

This dataset has been created with [distilabel](https://distilabel.argilla.io/).



## Dataset Summary

This dataset contains a `pipeline.yaml` which can be used to reproduce the pipeline that generated it in distilabel using the `distilabel` CLI:

```console
distilabel pipeline run --config "https://huggingface.co/datasets/thirdExec/scam-dialogue-thai-translated/raw/main/pipeline.yaml"
```

or explore the configuration:

```console
distilabel pipeline info --config "https://huggingface.co/datasets/thirdExec/scam-dialogue-thai-translated/raw/main/pipeline.yaml"
```

## Dataset structure

The examples have the following structure per configuration:


<details><summary> Configuration: default </summary><hr>

```json
{
    "dialogue": "caller: Hello, is this John? receiver: Yes, it is. Who\u0027s calling? caller: My name is Officer Johnson from the Social Security Administration. How are you today? receiver: I\u0027m fine, thank you. What can I do for you? caller: We\u0027ve been trying to reach you about a very important matter. Your social security number has been compromised and we need to take immediate action to protect your identity. receiver: Oh no, what happened? caller: We\u0027ve received reports of suspicious activity on your account and we need to verify some information to ensure your benefits aren\u0027t interrupted. receiver: Okay, what do you need to know? caller: Can you please confirm your social security number for me? receiver: Wait, I\u0027m not comfortable giving that out over the phone. Is this really the Social Security Administration? caller: Ma\u0027am, I assure you this is a legitimate call. We\u0027re trying to help you. If you don\u0027t cooperate, we\u0027ll have to suspend your benefits. receiver: I don\u0027t think so. I\u0027m going to hang up and call the SSA myself to verify this. caller: Ma\u0027am, don\u0027t hang up! You need to take care of this now or you\u0027ll be sorry!",
    "label": 1,
    "thai_dialogue": "caller: \u0e2a\u0e27\u0e31\u0e2a\u0e14\u0e35\u0e04\u0e48\u0e30 \u0e19\u0e35\u0e48\u0e04\u0e37\u0e2d\u0e08\u0e2d\u0e2b\u0e4c\u0e19\u0e43\u0e0a\u0e48\u0e44\u0e2b\u0e21\u0e04\u0e30\nreceiver: \u0e43\u0e0a\u0e48\u0e04\u0e48\u0e30 \u0e43\u0e04\u0e23\u0e40\u0e23\u0e35\u0e22\u0e01\u0e2b\u0e19\u0e48\u0e2d\u0e22\u0e04\u0e48\u0e30\ncaller: \u0e0a\u0e37\u0e48\u0e2d\u0e02\u0e2d\u0e07\u0e09\u0e31\u0e19\u0e04\u0e37\u0e2d Officer Johnson \u0e08\u0e32\u0e01\u0e2a\u0e33\u0e19\u0e31\u0e01\u0e07\u0e32\u0e19 Social Security Administration \u0e04\u0e48\u0e30 \u0e27\u0e31\u0e19\u0e19\u0e35\u0e49\u0e04\u0e38\u0e13\u0e2a\u0e1a\u0e32\u0e22\u0e14\u0e35\u0e44\u0e2b\u0e21\u0e04\u0e48\u0e30\nreceiver: \u0e2a\u0e1a\u0e32\u0e22\u0e14\u0e35\u0e04",
    "thai_type": "\u0e2b\u0e21\u0e32\u0e22\u0e40\u0e25\u0e02\u0e1b\u0e23\u0e30\u0e01\u0e31\u0e19\u0e2a\u0e31\u0e07\u0e04\u0e21",
    "type": "ssn"
}
```

This subset can be loaded as:

```python
from datasets import load_dataset

ds = load_dataset("thirdExec/scam-dialogue-thai-translated", "default")
```

Or simply as it follows, since there's only one configuration and is named `default`: 

```python
from datasets import load_dataset

ds = load_dataset("thirdExec/scam-dialogue-thai-translated")
```


</details>




