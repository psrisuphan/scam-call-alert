# Project Plans

## Mandatory implementation instructions for workers and AI agents

**You MUST follow the approved plans when implementing this project.** Read the relevant plan and its prerequisite plans before starting. Provisional drafts do not authorize implementation.

If a plan cannot be followed, or an issue requires changing a planned method, setting, scope, sequence, or output:

1. Pause the affected work and document the issue, evidence, proposed change, and its effects on other plans.
2. Obtain explicit confirmation from the human project owner before changing the plan or implementing a deviation. Silence is not approval.
3. After confirmation, update the affected instructions and record the approved change and rationale before continuing.

**Workers and AI agents MUST NOT change any approved plan details to match an implementation without first notifying the human project owner and receiving explicit confirmation.** Before editing, explain the mismatch, the proposed plan changes, why they are needed, and their downstream effects. This applies to methods, settings, scope, sequence, file/directory layouts, required outputs, and storage or Git-tracking rules. An implementation already being written, working, tested, or committed does not authorize changing its plan. Do not retroactively rewrite a plan to make an unapproved deviation appear compliant.

**Do not independently replace, bypass, or reinterpret a planned decision.** Resolve any required owner-confirmation checkpoint before performing the work it governs. Continue unaffected work only when it remains consistent with the approved plans.

Implementation details explicitly left flexible by a plan may be chosen within its stated boundaries; this does not authorize changing its required behavior or methods.


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
| [02 - Data Preprocessing and Model Inputs](02%20-%20DATA%20PREPROCESSING%20AND%20MODEL%20INPUTS.md) | Define preprocessing, model input preparation, and where each operation is applied. | Finished |
| [03/00 - Model Training](03%20-%20MODEL%20DEVELOPMENT/00%20-%20MODEL%20TRAINING.md) | Define the procedure for training candidate models using the approved data and input pipeline. | Planned |
| [03/01 - Hyperparameter Tuning and Model Selection](03%20-%20MODEL%20DEVELOPMENT/01%20-%20HYPERPARAMETER%20TUNING%20AND%20MODEL%20SELECTION.md) | Define how to search configurations and select the model using validation results. | Planned |
| [03/02 - Final Model Evaluation and Error Analysis](03%20-%20MODEL%20DEVELOPMENT/02%20-%20FINAL%20MODEL%20EVALUATION%20AND%20ERROR%20ANALYSIS.md) | Evaluate the selected model on held-out data and examine its errors. | Planned |
| [03/03 - Model Freeze and App Handoff](03%20-%20MODEL%20DEVELOPMENT/03%20-%20MODEL%20FREEZE%20AND%20APP%20HANDOFF.md) | Prepare the model and supporting artifacts for application integration. | Planned |
| [04/00 - Speech-to-Text Evaluation](04%20-%20APPLICATION%20DEVELOPMENT/00%20-%20SPEECH-TO-TEXT%20EVALUATION.md) | Define how to evaluate Thai transcription from prepared audio. | Planned |
| [04/01 - Mobile Emulator Prototype and Integration](04%20-%20APPLICATION%20DEVELOPMENT/01%20-%20MOBILE%20EMULATOR%20PROTOTYPE%20AND%20INTEGRATION.md) | Integrate microphone/recorded audio, live transcripts and system warnings; compare and freeze the context approach. | Planned |
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
