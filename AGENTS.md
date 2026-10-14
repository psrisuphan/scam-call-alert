# Project Working Instructions

## Purpose

Develop **อย่าเอาเงินชั้นไป — Scam Call Alert**, an intermediate-level Pattern Recognition term project.

Keep work practical, reproducible, and grounded in the project proposal and course lectures. Preserve the evidence needed to explain decisions, compare results, recover interrupted work, and prepare the final report.

## Establish the task and its sources

Before starting:

1. Read `01 - PLANs/README.md`.
2. Read the relevant approved plan and prerequisite plans.
3. Inspect relevant implementation configurations, reports, and artifact identities.
4. Confirm the requested work is authorized.

Read the proposals and relevant lectures when planning methods, checking scope, or resolving conflicts:

- `00 - DOCUMENTs/Full Proposal/Phoebe_FullProposal.docx`, or its equivalent PDF.
- `00 - DOCUMENTs/Strong Idea/Phoebe_strongidea.pdf`.
- Relevant files under `01 - PLANs/course-lecture-sheets/`, when available locally.

The proposal defines scope; lectures guide methodological rigor; approved plans define agreed implementation.

If sources conflict, explain the conflict and obtain owner confirmation before affected work. If required lecture material is unavailable, request access rather than inventing its contents.

## Identify approved work

A saved file alone does not establish approval. Check the plan’s provisional notice, README task state, and relevant recorded decisions.

Provisional drafts do not authorize implementation. If approval evidence or documentation disagrees, clarify before proceeding.

Task states belong only in `01 - PLANs/README.md`:

- **Unplanned:** not approved/finalized.
- **Planned:** approved and written; implementation incomplete.
- **Finished:** implementation satisfies completion criteria.
- **Skipped:** the owner explicitly omitted execution; this does not mean completion.

Do not place changing progress summaries, owners, or task statuses in AGENTS.md or individual plans.

## Follow plans and obtain approval for changes

Follow the mandatory instructions in `01 - PLANs/README.md`.

**Workers and AI agents MUST NOT change approved plan details to match implementation without first notifying the human project owner and receiving explicit confirmation.**

This includes methods, settings, scope, sequence, layouts, outputs, and storage or Git-tracking rules.

When a deviation is necessary:

1. Pause affected work.
2. Explain the issue, evidence, proposed change, rationale, and downstream effects.
3. Obtain explicit owner confirmation. Silence is not approval.
4. Record the approved change and rationale in the affected plan or its referenced configuration/report.
5. Update affected instructions before continuing.

Working code, passing tests, or existing commits do not authorize retroactive plan changes.

Continue unaffected work within approved boundaries. Choices explicitly left flexible may be made without changing required behavior.

## Planning workflow

Follow the order and dependencies in the plans README.

For each task:

1. Review relevant sources, prerequisites, and existing drafts.
2. Identify consequential unknowns.
3. Explain options, recommendation, evidence, and tradeoffs.
4. Discuss preferably one consequential question at a time.
5. Obtain confirmation instead of guessing.
6. Show the complete revised draft.
7. Check feasibility, practicality, scope, leakage, outputs, and cross-plan consistency.
8. Save/finalize only after owner approval.
9. Update the README task row.

Plans must provide ordered instructions, selected methods and rationale, dependencies, file/field purposes, decision rules, deliverables, and completion checks.

Keep code/library choices flexible where they do not affect required behavior. Do not reopen confirmed decisions without new evidence or an owner request.

**Planning approval alone does not authorize implementation.**

## Explain methodological decisions

For methods with meaningful alternatives, document:

- What was selected and why.
- Relevant alternatives and tradeoffs.
- Supporting evidence and its limitations.

Cite proposal sections and lecture filenames with PDF page numbers. Distinguish PDF pages from printed slide numbers.

Use primary research or official documentation where helpful. Separate source-supported principles from project conventions; do not claim that a source prescribes an exact setting or proves superiority without evidence.

## Implementation and verification

Before implementation, verify prerequisites, recorded approvals, and configuration/artifact identities. Resolve required owner-confirmation checkpoints.

During implementation:

- Follow the approved sequence and behavior.
- Reuse authoritative datasets, assignments, and shared components.
- Preserve required provenance, configurations, predictions, failures, and recovery evidence.
- Keep artifacts in their owning locations.
- Do not independently edit derived datasets or regenerate frozen assignments.

**When implementation or verification is authorized, agents may run existing checks required by the relevant plan and add tests within the task to verify required behavior.** This does not authorize changing methods, evaluation protocols, datasets, or experiment scope.

Do not spawn subagents without explicit authorization.

Before declaring completion, verify the plan’s completion criteria and ensure documentation matches the delivered artifacts.

If README says Finished but artifacts conflict with the current plan, pause affected use, explain the mismatch, and obtain confirmation of corrective action. Preserve existing evidence; old tests and status claims do not override current requirements.

## Protect evaluation integrity

Follow each plan’s training, validation, and final-evaluation boundaries:

- Fit learned transformations only on eligible training data.
- Apply frozen transformations to validation/test inputs.
- Preserve approved membership and related-record separation.
- Use development evidence for selection and debugging.
- Never tune models, preprocessing, thresholds, context settings, or labels from final evaluation results.
- Separate prediction errors from execution failures.
- Preserve original evidence when correcting evaluation bugs.
- Report counts, denominators, failures, conditions, and limitations.

Do not describe CV variability as final-test uncertainty or broader robustness without supporting experiments.

## Respect task boundaries

Each plan owns its stated responsibilities and outputs.

Identify dependencies early and resolve choices in their owning plans. Reuse prerequisite artifacts without duplicating their procedures.

Do not expand scope or claim capabilities unsupported by implementation and evaluation.

## Git and artifact handling

- Commit/push only when requested.
- Use `<category>: <description>` commit messages.
- Make separate atomic commits by task.
- Stage precisely; exclude unauthorized drafts and local materials.
- Inspect collaborator changes and preserve local work when integrating them.
- Never force-push over collaborator work.
- Follow approved tracking and storage rules.
- Keep credentials and personal information out of commits.
- Store required large/ignored artifacts in documented persistent storage.

Keep session notes and temporary handoffs separate from shared instructions. Approved plans override superseded discussion notes.

## Communication

Explain what changed, why, how it was verified, and remaining limitations.

Ask about consequential unknowns rather than inventing requirements. Report blockers honestly and continue authorized, unaffected work.
