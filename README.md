# อย่าเอาเงินชั้นไป - Scam Call Alert

A Thai scam call detection prototype for a pattern recognition course project. The model classifies call transcripts as `Scam` or `Not Scam` and alerts the user when a call looks suspicious.

## Project scope

- Classify Thai conversation transcripts after speech-to-text conversion.
- Compare Thai and multilingual transformer models on identical data splits.
- Evaluate using precision, recall, F1, accuracy, and confusion matrices, focusing on scam recall and scam F1.
- Demonstrate audio to transcript to classification in a mobile emulator using test audio files.
- Live call interception and carrier call blocking are out of scope.

## Data and models

The primary dataset is Scam Dialogue Thai Translated (Hugging Face). The supplemental dataset is Thai Call Center Call Log (Kaggle).

Candidate models:
- WangchanBERTa
- PhayaThaiBERT
- HPLT 3.0 GPT-BERT Thai
- XLM-RoBERTa-base

Both datasets contain simulated calls. Test scores evaluate prototype behavior on simulated dialogues, not detection rates on live phone scam networks.

## Repository layout

- `00 - DOCUMENTs/`: proposal and course submission files
- `01 - PLANs/`: step-by-step engineering and experiment plans
- `02 - DATASETs/`: raw downloads, review queues, audit logs, and cleaned exports
- `03 - MODEL DEVELOPMENT/`: model training, tuning, selection, and frozen weights
- `04 - APPLICATION DEVELOPMENT/`: STT testing and mobile emulator prototype

## Current status

Section 00 (data preparation) is finished for local dataset version v1.

Summary:
- 1,273 primary conversations and 167 supplemental conversations retained (1,440 total).
- 38 conversations excluded (19 duplicate copies, 13 ambiguous Unknow calls, 5 corrupted texts, 1 truncated dialogue).
- Supplemental label mapping: Scam -> 1 (55 retained); General, Official, Verification-call -> 0 (112 retained).
- 14 multi-dialogue template groups created to prevent test leakage in Stage 01.

See [the data preparation findings report](02%20-%20DATASETs/reports/data_preparation_findings_v1.md) for full counts, category breakdowns, and presentation slides. Model training and emulator integration have not started.
