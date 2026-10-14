# อย่าเอาเงินชั้นไป - Scam Call Alert

Version: v1.0
Created: October 2026
Course: Pattern Recognition (term project)
Institution: Kasetsart University, Kamphaeng Saen Campus
Team: Phoebe

## 1. Project description

A prototype that warns Thai users when a call looks like a scam. We transcribe the call audio with
speech-to-text (STT), then classify the transcript as `Scam` or `Not Scam`. If the model predicts
`Scam`, the app on the Android emulator shows a warning. The app does not intercept or block real
phone calls.

* ML task: binary text classification (fraud call detection)
* Input: Thai call transcript from STT
* Output: `Scam` or `Not Scam`, threshold 0.5
* Final model: PhayaThaiBERT, trained on the primary dataset only for 2 epochs

## 2. Class labels

| Label | Description |
| ----- | ----------- |
| 0 | Not Scam |
| 1 | Scam |

The supplemental dataset has an `Unknow` category, which we map to `Not Scam` by owner decision.
This only means the source did not label the call as a scam. Nobody checked that those calls are
actually safe.

## 3. Repository structure

```text
scam-call-alert/
├── 00 - DOCUMENTs/              # Strong idea and full proposal
├── 01 - PLANs/                  # Approved implementation plans and task status
├── 02 - DATASETs/
│   ├── raw/                     # Pinned, unchanged source files
│   ├── prepared/prepared.csv    # Canonical dataset (1,455 conversations)
│   ├── prepared/splits/         # Frozen train/test and 5-fold assignments
│   └── scripts/                 # Numbered download, prepare, split and test scripts
├── 03 - MODEL DEVELOPMENT/      # Input preparation, training, selection, final evaluation
├── 04 - APPLICATION DEVELOPMENT/
│   └── prototype/               # Expo/Android app and local STT + classifier service
└── 06 - REPORT/                 # Presentation, demo guide and submission materials
```

## 4. Data sources

| Dataset | Role | Records used | License |
| ------- | ---- | -----------: | ------- |
| [Scam Dialogue Thai Translated](https://huggingface.co/datasets/thirdExec/scam-dialogue-thai-translated) | Primary | 1,276 | Not declared |
| [Thai Call Center Call Log Dataset](https://www.kaggle.com/datasets/jxxn03x/thai-call-center-call-log-dataset) | Supplemental | 179 | CC BY-NC-ND 4.0 |

Both datasets are simulated conversations, and the primary one was translated from English. So
treat our results as prototype evidence, not as proof the model works on real Thai scam calls.
Source revisions and checksums are in `02 - DATASETs/sources.json`.

## 5. Labelling and data preparation

Labels come from the sources and follow our
[labelling guideline](02%20-%20DATASETs/labeling_guideline.md). We removed exact duplicates and
three calls that were cut off and could not be recovered. We did not edit any transcript text.
We reviewed all 46 near-duplicate pairs and grouped them, so related records never end up on both
sides of the train/test split. More detail is in the
[preparation report](02%20-%20DATASETs/prepared/preparation_report.md).

| Source | Not Scam | Scam | Total |
| ------ | -------: | ---: | ----: |
| Primary | 639 | 637 | 1,276 |
| Supplemental | 124 | 55 | 179 |
| Total | 763 | 692 | 1,455 |

## 6. Data split

| Subset | Records | Share |
| ------ | ------: | ----: |
| Training pool (5 group-aware CV folds, seed 67) | 1,164 | 80% |
| Held-out test | 291 | 20% |

We picked the model with cross-validation only and opened the test set once, for the final
evaluation. See the [split report](02%20-%20DATASETs/prepared/splits/split_report.md).

## 7. Results (final held-out text evaluation)

| Scope | Scam precision | Scam recall | Scam F1 | Macro-F1 | Accuracy |
| ----- | -------------: | ----------: | ------: | -------: | -------: |
| Combined (290 of 291 predicted) | 0.978 | 0.971 | 0.974 | 0.976 | 0.976 |
| Primary (254 of 255) | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Supplemental (36 of 36) | 0.700 | 0.636 | 0.667 | 0.765 | 0.806 |

One test record failed during input preparation, and we did not rerun it. These numbers measure
text classification only. We did not formally evaluate the full audio pipeline, real calls or
warning latency, because the owner dropped Plan 05 to meet the deadline. Full results are in the
[evaluation report](03%20-%20MODEL%20DEVELOPMENT/final-evaluation/evaluation_report.md).

## 8. Run the demo

Follow [RUN_DEMO.md](04%20-%20APPLICATION%20DEVELOPMENT/prototype/RUN_DEMO.md).

## 9. Version history

| Version | Description |
| ------- | ----------- |
| v0.1 | Dataset preparation and frozen split |
| v0.2 | Model training, cross-validation and selection |
| v0.3 | Final held-out evaluation of PhayaThaiBERT |
| v1.0 | Mobile emulator prototype and presentation submission |

## 10. Authors

Team Phoebe
1. Kongyut Klongklaew (คงยุทธ คล่องแคล่ว), 6620501303
2. Phudispat Srisuphan (ภูดิสพัฒน์ ศรีสุพรรณ์), 6620503535

This is a course project for academic use. The dataset licenses in section 4 still apply, and the
supplemental data is non-commercial with no derivatives allowed.
