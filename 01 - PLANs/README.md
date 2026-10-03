# Engineering and experiment plans

Step-by-step implementation plans for Scam Call Alert. Each stage defines its inputs, checks, outputs, and stop conditions.

## Plan structure

```text
01 - PLANs/
├── README.md
├── 00 - DATA PREPARATION.md
├── 01 - DATA SPLIT AND EXPERIMENT DESIGN.md
├── 02 - TEXT PREPROCESSING AND MODEL INPUTS.md
├── 03 - MODEL DEVELOPMENT/
│   ├── 00 - MODEL TRAINING.md
│   ├── 01 - HYPERPARAMETER TUNING AND MODEL SELECTION.md
│   ├── 02 - FINAL MODEL EVALUATION AND ERROR ANALYSIS.md
│   └── 03 - MODEL FREEZE AND APP HANDOFF.md
├── 04 - APPLICATION DEVELOPMENT/
│   ├── 00 - SPEECH-TO-TEXT EVALUATION.md
│   └── 01 - MOBILE EMULATOR PROTOTYPE AND INTEGRATION.md
├── 05 - END-TO-END SYSTEM EVALUATION.md
└── 06 - FINAL RESULTS AND LIMITATIONS REPORT.md
```

## Status

| Stage | Document | Status | Output |
| --- | --- | --- | --- |
| 00 | `00 - DATA PREPARATION.md` | Complete (v1) | `02 - DATASETs/processed/v1/` (1,401 rows) |
| 01 | `01 - DATA SPLIT AND EXPERIMENT DESIGN.md` | Ready to start | Fixed group-aware splits and evaluation rules |
| 02 | `02 - TEXT PREPROCESSING AND MODEL INPUTS.md` | Pending 01 | Speaker tag harmonization and tokenization format |
| 03 | `03 - MODEL DEVELOPMENT/` | Pending 02 | Baseline runs, tuning, evaluation, frozen artifact |
| 04 | `04 - APPLICATION DEVELOPMENT/` | Pending 03 | Whisper Thai STT and mobile emulator app |
| 05 | `05 - END-TO-END SYSTEM EVALUATION.md` | Pending 04 | Pipeline latency and end-to-end failure metrics |
| 06 | `06 - FINAL RESULTS AND LIMITATIONS REPORT.md` | Final stage | Course final report and presentation slides |

## Rules across all plans

1. Never fit transformations on test data. Fit vocabulary, scalers, tokenizers, or thresholds inside training folds only.
2. Keep related conversations in the same split. Template variants and chunked calls must never cross between train and test sets.
3. Keep raw data read-only. Cleaned exports write to versioned folders with decision logs.
4. Distinguish verified facts from assumptions. State simulation limits and sample sizes clearly.
