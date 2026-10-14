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

The structure below contains the approved plans and an optional high-level outline. Runtime-dependent confirmation checkpoints remain in their owning plans and must be resolved before affected execution. A Planned task is not implemented; planning approval alone does not authorize implementation.

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
│   ├── 03 - MODEL FREEZE AND APP HANDOFF.md
│   └── 04 - OPTIONAL LLM DATA AUGMENTATION.md
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
- **Skipped:** the owner explicitly omitted execution; retain the plan and disclose the missing evaluation rather than marking it Finished.

Update a task when its plan is saved or its implementation is completed. A written plan alone does not mean the task is finished. Individual plan files do not need status fields.

| Plan | Purpose | State |
|---|---|---|
| [00 - Data Preparation](00%20-%20DATA%20PREPARATION.md) | Obtain the datasets and prepare labeled, audited conversation records ready for splitting. | Finished |
| [01 - Data Split and Experiment Design](01%20-%20DATA%20SPLIT%20AND%20EXPERIMENT%20DESIGN.md) | Define train/test separation, cross-validation, conditional grouping, and shared experiment data conditions. | Finished |
| [02 - Data Preprocessing and Model Inputs](02%20-%20DATA%20PREPROCESSING%20AND%20MODEL%20INPUTS.md) | Define preprocessing, model input preparation, and where each operation is applied. | Finished |
| [03/00 - Model Training](03%20-%20MODEL%20DEVELOPMENT/00%20-%20MODEL%20TRAINING.md) | Define the procedure for training candidate models using the approved data and input pipeline. | Finished |
| [03/01 - Hyperparameter Tuning and Model Selection](03%20-%20MODEL%20DEVELOPMENT/01%20-%20HYPERPARAMETER%20TUNING%20AND%20MODEL%20SELECTION.md) | Define how to search configurations and select the model using validation results. | Finished |
| [03/02 - Final Model Evaluation and Error Analysis](03%20-%20MODEL%20DEVELOPMENT/02%20-%20FINAL%20MODEL%20EVALUATION%20AND%20ERROR%20ANALYSIS.md) | Evaluate the selected model on held-out data and examine its errors. | Finished |
| [03/03 - Model Freeze and App Handoff](03%20-%20MODEL%20DEVELOPMENT/03%20-%20MODEL%20FREEZE%20AND%20APP%20HANDOFF.md) | Prepare the model and supporting artifacts for application integration. | Planned |
| [03/04 - Optional LLM Data Augmentation](03%20-%20MODEL%20DEVELOPMENT/04%20-%20OPTIONAL%20LLM%20DATA%20AUGMENTATION.md) | Reserve an optional development branch if original-data CV results are unsatisfactory; finalize its detailed protocol only if needed. | Unplanned |
| [04/00 - Speech-to-Text Evaluation](04%20-%20APPLICATION%20DEVELOPMENT/00%20-%20SPEECH-TO-TEXT%20EVALUATION.md) | Define how to evaluate Thai transcription from prepared audio. | Planned |
| [04/01 - Mobile Emulator Prototype and Integration](04%20-%20APPLICATION%20DEVELOPMENT/01%20-%20MOBILE%20EMULATOR%20PROTOTYPE%20AND%20INTEGRATION.md) | Integrate microphone/recorded audio, live transcripts and system warnings; compare and freeze the context approach. | Planned |
| [05 - End-to-End System Evaluation](05%20-%20END-TO-END%20SYSTEM%20EVALUATION.md) | Formal system evaluation omitted by owner decision due to the deadline; preserve the protocol and disclose the omission. | Skipped |
| [06 - Final Results and Limitations Report](06%20-%20FINAL%20RESULTS%20AND%20LIMITATIONS%20REPORT.md) | Prepare Thai presentation/backup slides, traceable evidence, the cloud submission package and rehearsed demo. | Planned |

## How to follow the plans

Read the relevant plan and its prerequisite deliverables before implementing a task. Follow its selected methods, ordered steps, decision rules, output definitions, and completion checks.

The main sequence is:

**Data preparation → splitting and experiment design → preprocessing → model development → application integration → end-to-end evaluation → final reporting.**

Owner-approved deadline scope change (2026-10-14): omit Plan 05 execution and proceed from application demo evidence to Plan 06. The recorded and live-microphone functional checks support the demo; they do not establish final end-to-end accuracy, warning latency, delivery reliability or prevention. Retain the Plan 05 protocol and its definitions used by development analysis. Do not generate its reserved recordings, 36-run final workload or paired-reference diagnostics solely to satisfy the former handoff. Model final-text evaluation and other unmodified tasks are not waived by this decision.

Training and tuning are iterative. Owner-approved early app wiring may use the temporary WangchanBERTa bundle specified in Plan 03/03 while candidate comparisons continue; official context comparison, integration freeze, and Plan 05 still require the selected/final-evaluated model handoff and speech-to-text procedure. Individual plans define the exact dependencies and permitted parallel work. Forward references to later approved protocols supply method definitions, not a requirement to execute final evaluation before development.

Optional Plan 03/04 has an owner-confirmed high-level outline, but remains **Unplanned** because its implementation protocol is not finalized. Consider activation after original-data CV review and before final-test access, regardless of filename numbering. It may remain unused. Existing no-augmentation instructions remain effective until the detailed protocol and affected changes receive owner approval.

### Implementation entry and release gates

Begin an authorized task with its completed prerequisites and recorded artifact identities. Model training may implement its component and owner-configured diagnostics before the tuning matrix is launched. Resolve training settings, combined feasibility and local-execution preflight before full comparison/final candidate release. Resolve STT selection, recording-script fidelity, staged context screening/window/completion settings and selected-background compatibility before system evaluation. Develop recorded mode first, but release the frozen application to Plan 05 only after both mandatory modes pass functional checks; formal system metrics still use recordings exclusively. Keep the full model matrix unless measured feasibility justifies an owner-approved reduction. Resolve presentation/access checkpoints before delivery.

No final audio/results may resolve a design choice. Distinguish ready to begin implementation from ready to launch experiments: numeric/runtime settings needing measurements stay explicit, owner-reviewed gates rather than guessed defaults. Historical local decision notes are not authoritative instructions; use approved plans and their referenced configurations/reports. Before generating stage evidence, configure its documented persistent location and specific Git ignore rules; protect sample-level logs/media as well as weights, while preserving tracked instructions/manifests/approved aggregates.

If implementation reveals an unexpected issue or a flaw in a plan, document the issue and discuss any consequential method change with the project owner. Update the affected instructions and record the reason for the agreed change. Continue unaffected work where possible.

Dataset scripts live in `02 - DATASETs/scripts/`, with numbered filenames and [a short reproduction guide](../02%20-%20DATASETs/scripts/README.md). Raw sources and completed Stage 00/01 outputs are included for the private project handoff. Source licenses still govern sharing; review scratch files and executed notebooks stay local.

Directory numbering indicates workflow order, not calendar dates. This README is a directory guide; task details and methodological decisions belong in the individual plans.

## Reference material

- [Full Proposal](../00%20-%20DOCUMENTs/Full%20Proposal/Phoebe_FullProposal.docx): project scope and proposed workflow.
- [Initial Idea](../00%20-%20DOCUMENTs/Strong%20Idea/Phoebe_strongidea.pdf): project motivation and initial approach.
- `course-lecture-sheets/`: course guidance, particularly Chapters 2-6. These lecture files are local, ignored by Git, and may be unavailable in a fresh clone.
