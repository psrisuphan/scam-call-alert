# อย่าเอาเงินชั้นไป - Scam Call Alert

A Thai-language scam call detection prototype for a pattern recognition project. It classifies a call transcript as `Scam` or `Not Scam` and presents a warning when the conversation appears suspicious.

## Project scope

- Analyze Thai call dialogue after speech-to-text transcription.
- Compare Thai and multilingual transformer models using the same train/test split.
- Evaluate with precision, recall, F1-score, accuracy, and a confusion matrix, with particular attention to scam recall and F1.
- Demonstrate the audio-to-transcript-to-classification flow in a mobile emulator using prepared audio files.
- Do not intercept or block live phone calls.

## Proposed data and models

The proposal identifies Scam Dialogue Thai Translated as the primary dataset and Thai Call Center Call Log Dataset as supplemental data. The planned model comparison includes WangchanBERTa, PhayaThaiBERT, HPLT 3.0 GPT-BERT Thai, and XLM-RoBERTa-base.

The datasets contain simulated conversations. Results should therefore be interpreted as prototype evaluation, not evidence of performance on real scam calls.

## Repository layout

- `00 - DOCUMENTs/` - project idea and full proposal
- [01 - PLANs/](01%20-%20PLANs/README.md) - implementation plans and workflow guide
- `02 - DATASETs/` - dataset workspace
- `03 - MODEL DEVELOPMENT/` - model experiments
- `04 - APPLICATION DEVELOPMENT/` - mobile application prototype ([how to run the demo](04%20-%20APPLICATION%20DEVELOPMENT/prototype/RUN_DEMO.md))

## Current status

Stage 00 is complete. The included canonical CSV retains 1,455 conversations (1,276 primary, 179 supplemental), with source provenance, disposition audits, and reviewed relationships. Raw sources and prepared/split outputs are included for the private project handoff. See [dataset instructions](02%20-%20DATASETs/README.md), [the numbered script guide](02%20-%20DATASETs/scripts/README.md), and [the preparation report](02%20-%20DATASETs/prepared/preparation_report.md). Confirm source rights before public redistribution.

Stage 01 is complete: 1,164 training records, 291 test records, and five shared, group-aware CV folds using seed 67. See [the split report](02%20-%20DATASETs/prepared/splits/split_report.md).

[Stage 02: preprocessing and model inputs](01%20-%20PLANs/02%20-%20DATA%20PREPROCESSING%20AND%20MODEL%20INPUTS.md) is complete locally. Speaker handling, checkpoint preparation, and fixed prefix limits are approved. Both representations pass input checks across all 1,164 training records and four pinned tokenizers. Readable processed text and eight unpadded model-input exports are included at `03 - MODEL DEVELOPMENT/input-preparation/prepared/`, with numbered reproduction scripts 6-9. See [input-preparation instructions](03%20-%20MODEL%20DEVELOPMENT/input-preparation/README.md) and [the preprocessing report](03%20-%20MODEL%20DEVELOPMENT/input-preparation/preprocessing_report.md).

Model development has one verified WangchanBERTa primary-only five-fold configuration at epoch 3; it is preliminary evidence, not a completed candidate comparison or final model selection. The held-out test set remains unopened. See [model development implementation notes](03%20-%20MODEL%20DEVELOPMENT/IMPLEMENTATION%20NOTES.md) for the approved four-candidate sequence, WangchanBERTa implementation method, results, and handoff guidance. No augmentation, resampling, learned preprocessing, or final test evaluation has occurred.
