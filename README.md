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
- `04 - APPLICATION DEVELOPMENT/` - mobile application prototype
