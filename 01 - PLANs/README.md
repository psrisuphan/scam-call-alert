# Project Plans

This directory contains implementation plans for the **อย่าเอาเงินชั้นไป - Scam Call Alert** Pattern Recognition term project.

Each plan explains what to do, how to do it, why the methods were selected, the required outputs, and how to check completion. The plans use the project proposal and course lecture sheets as their source material.

## Directory structure

The structure below is the intended organization. Future plan files remain proposed until their structure and contents are confirmed.

```text
01 - PLANs/
├── README.md
├── 00 - DATA PREPARATION.md
├── 01 - DATA SPLIT AND EXPERIMENT DESIGN.md
├── 02 - DATA PREPROCESSING AND MODEL INPUTS.md
├── 03 - MODEL DEVELOPMENT/
│   ├── 00 - MODEL TRAINING.md
│   ├── 01 - HYPERPARAMETER TUNING AND MODEL SELECTION.md
│   ├── 02 - FINAL MODEL EVALUATION AND ERROR ANALYSIS.md
│   └── 03 - MODEL FREEZE AND APP HANDOFF.md
├── 04 - APPLICATION DEVELOPMENT/
│   ├── 00 - SPEECH-TO-TEXT EVALUATION.md
│   └── 01 - MOBILE EMULATOR PROTOTYPE AND INTEGRATION.md
├── 05 - END-TO-END SYSTEM EVALUATION.md
├── 06 - FINAL RESULTS AND LIMITATIONS REPORT.md
└── course-lecture-sheets/
```

## Tasks and planning progress

Each plan is one task. Use these states:

- **Unplanned:** the plan has not been confirmed and written.
- **Planned:** the plan is confirmed and written; implementation is not complete.
- **Finished:** implementation meets the plan's completion criteria.

Update a task when its plan is saved or its implementation is completed. A written plan alone does not mean the task is finished. Individual plan files do not need status fields.

| Plan | Purpose | State |
|---|---|---|
| [00 - Data Preparation](00%20-%20DATA%20PREPARATION.md) | Obtain the datasets and prepare labeled, audited conversation records ready for splitting. | Finished |
| [01 - Data Split and Experiment Design](01%20-%20DATA%20SPLIT%20AND%20EXPERIMENT%20DESIGN.md) | Define train/test separation, cross-validation, conditional grouping, and shared experiment data conditions. | Finished |
| [02 - Data Preprocessing and Model Inputs](02%20-%20DATA%20PREPROCESSING%20AND%20MODEL%20INPUTS.md) | Define preprocessing, model input preparation, and where each operation is applied. | Planned |
| [03/00 - Model Training](03%20-%20MODEL%20DEVELOPMENT/00%20-%20MODEL%20TRAINING.md) | Define the procedure for training candidate models using the approved data and input pipeline. | Planned |
| [03/01 - Hyperparameter Tuning and Model Selection](03%20-%20MODEL%20DEVELOPMENT/01%20-%20HYPERPARAMETER%20TUNING%20AND%20MODEL%20SELECTION.md) | Define how to search configurations and select the model using validation results. | Planned |
| 03/02 - Final Model Evaluation and Error Analysis | Evaluate the selected model on held-out data and examine its errors. | Unplanned |
| 03/03 - Model Freeze and App Handoff | Prepare the model and supporting artifacts for application integration. | Unplanned |
| 04/00 - Speech-to-Text Evaluation | Define how to evaluate Thai transcription from prepared audio. | Unplanned |
| 04/01 - Mobile Emulator Prototype and Integration | Connect audio, transcription, classification, and warnings in the prototype. | Unplanned |
| 05 - End-to-End System Evaluation | Evaluate the complete audio-to-warning workflow and its system behavior. | Unplanned |
| 06 - Final Results and Limitations Report | Assemble the methods, experimental results, system measurements, and limitations into the final report. | Unplanned |

## How to follow the plans

Read the relevant plan and its prerequisite deliverables before implementing a task. Follow its selected methods, ordered steps, decision rules, output definitions, and completion checks.

The main sequence is:

**Data preparation → splitting and experiment design → preprocessing → model development → application integration → end-to-end evaluation → final reporting.**

Training and tuning are iterative. Application integration depends on both the model handoff and the speech-to-text procedure. Individual plans define the exact dependencies and permitted parallel work.

If implementation reveals an unexpected issue or a flaw in a plan, document the issue and discuss any consequential method change with the project owner. Update the affected instructions and record the reason for the agreed change. Continue unaffected work where possible.

Dataset scripts live in `02 - DATASETs/scripts/`, with numbered filenames and [a short reproduction guide](../02%20-%20DATASETs/scripts/README.md). Raw sources and completed Stage 00/01 outputs are included for the private project handoff. Source licenses still govern sharing; review scratch files and executed notebooks stay local.

Directory numbering indicates workflow order, not calendar dates. This README is a directory guide; task details and methodological decisions belong in the individual plans.

## Reference material

- [Full Proposal](../00%20-%20DOCUMENTs/Full%20Proposal/Phoebe_FullProposal.docx): project scope and proposed workflow.
- [Initial Idea](../00%20-%20DOCUMENTs/Strong%20Idea/Phoebe_strongidea.pdf): project motivation and initial approach.
- `course-lecture-sheets/`: course guidance, particularly Chapters 2-6. These lecture files are local, ignored by Git, and may be unavailable in a fresh clone.
