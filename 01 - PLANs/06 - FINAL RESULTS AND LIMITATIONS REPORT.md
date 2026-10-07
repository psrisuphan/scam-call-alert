# 06 - FINAL RESULTS AND LIMITATIONS REPORT

## Purpose and scope

Prepare the final presentation and shared-cloud project package from evidence produced by Plans 00–05. Emphasize Pattern Recognition model development while connecting the scam-call problem, data handling, justified decisions, application usefulness and complete system evaluation.

Deliver main/backup slides, presentation notes/rehearsal outline, a shared-cloud package with README/reproduction information, and a demo guide with a clearly labeled fallback recording. Earlier stage reports remain supporting evidence; a separate full academic report is not required by the supplied assignment.

Do not introduce experiments, change the selected pipeline or conceal negative findings. Evidence gaps requiring implementation/new experiments return to their owning task for owner discussion. Planning approval alone does not authorize creating or submitting the deliverables.

## 1. Establish requirements and grading coverage

Use the supplied Term Project Submission instructions and owner clarification:

- Deadline: October 14, 2026, 11:59 PM (project local time, Asia/Bangkok).
- Slide presentation: approximately 8–10 minutes.
- Slides plus demo: target approximately 12 minutes, maximum 15 minutes.
- Q&A: separate 5-minute session per owner's clarified timing.
- Thai explanations with English technical terms.
- Editable PowerPoint and exported PDF; Canva permitted for final design edits.

Record the timing clarification because it differs from the originally pasted grouping of presentation/demo/Q&A within 15 minutes. Approximately nine minutes of slides and three minutes of demo is a flexible rehearsal target, not fixed section timing or slide count.

Required slide topics: problem/solution; ML problem; system overview including diagram; dataset details; models/configurations; experimental design/results; conclusions/discussion.

Work grading includes problem analysis, data handling, training/tuning, experimental design, UX/UI, pipeline consistency and user needs. Slide grading includes completeness, correctness and explanatory visual quality. Individual presentation grading motivates each collaborator's explanation practice. Do not invent rubric weights.

Cloud deliverables must be accessible to the professor. Cloud provider, final access account and speaker allocation are delivery checkpoints, not guessed choices.

## 2. Gather authoritative evidence and prepare early

| Evidence | Purpose |
|---|---|
| Preparation/split reports | Sources, labels, exclusions, duplicates/groups and leakage prevention. |
| Input configuration/report | Representations, tokenization, lengths and shared inference preparation. |
| Training histories/configurations | Training method, loss, optimizer, epoch effects, runtime/recovery. |
| CV comparison/selection | Models, data conditions, tuning, variation and selected configuration rationale. |
| Final text evaluation | Held-out metrics, confusion matrices, all errors/failures and limitations. |
| Model handoff | Frozen contract, identities and actual local compatibility. |
| STT report | CER, runtime/resources/failures and selected component. |
| Application evidence | UX/UI, modes, progressive flow and development context comparison. |
| System evaluation | Foreground/background quality, warnings, timing and failure evidence. |

Verify source revisions/checksums and actual completion. Planned run counts are not completed experiment counts. Preserve unsuccessful comparisons/missing results; do not invent scores or describe unexecuted work as completed.

Preparation may start before experiments finish: outline, diagrams and method explanations can use approved instructions, with unavailable results explicitly marked pending. Final approval requires verified results or owner-approved disclosure of incomplete work. A missing result does not authorize an agent to alter experiment scope.

## 3. Organize main and backup slides

Use this content sequence, adjusting slide count/layout to readability:

1. Scam-call problem and user need.
2. ML formulation and solution.
3. System overview diagram.
4. Datasets, preparation, labels and leakage-safe splits.
5. Models/configurations/training.
6. Hyperparameter tuning and experimental design.
7. CV results, variability and selection.
8. Final text-test results/errors.
9. STT and development context comparison.
10. Application UX/UI and system results.
11. Conclusions, limitations and proposed future work.

### Main slides

Include key candidate/data comparisons, tuning/epoch effects, CV mean/sample SD, selected configuration/rationale, final text-test metrics/errors, STT tradeoffs, application flow and foreground/background system outcomes. Material negative findings and limitations belong here, not only in backup slides. Give model development substantial attention without omitting the end-to-end usefulness required by the assignment.

### Backup slides

Keep individual folds, full configurations, learning curves, marked/role-free validation diagnostics, limited caller-only research, source breakdowns, detailed STT/context/system evidence, failures/interruptions, extra examples and bibliography. These support Q&A and collaborators' recall and are outside the usual timed presentation.

## 4. Explain methods and distinctions accurately

For consequential choices, state selection, rationale, alternatives/tradeoffs, evidence and limitations using approved plans. Do not invent post-hoc reasons.

Distinguish source-supported principles from project conventions; fixed settings from tuned values; CV from final evaluation; marked training from role-free inference; source-assisted caller research from deployable app input; and measured results from proposed future capabilities.

Use the actual approved classification loss and optimizer configuration. Do not carry an obsolete provisional BCE description into slides when the implementation follows approved Cross-Entropy/AdamW. Verify loss/regularization explanations against actual artifacts and sources.

Do not claim supporting research establishes receiver-context superiority, calibrated risk or project-specific optimal settings. Published results are not directly comparable project baselines unless protocols match. Explain approved deviations from proposal/plan with recorded reasons.

## 5. Produce traceable visuals

Derive figures/tables from preserved machine-readable artifacts. Include a diagram matching the implemented emulator/local-host boundaries and progressive audio/STT/text/classifier/notification flow.

Recommended visuals: dataset/split counts; configuration table; learning/tuning curves; candidate/data CV comparison with SD; final text confusion matrix; STT quality/runtime tradeoff; development context comparison; separate foreground/background system quality, warning coverage, timing, failures/resources.

Every visual identifies units, metric/class order, averaging, sample counts and conditions. Keep CV, final text, STT benchmark and final system scores separately labeled. Reproduce exported numbers from authoritative data; presentation rounding must not change selection rationale.

Preserve all results in supporting evidence; main/backup selection is presentation editing, not deletion of unfavorable findings.

### Statistical and timing rules

- CV SD is fold variability, not final-test confidence or seed robustness.
- Preserve system descriptive mean/sample SD/median and contributing counts as Plan 05 defines.
- Do not introduce confidence intervals, extra seeds or new experiments.
- System classification metrics use completed eligible runs/raw confusion matrices; coverage/timing follow call-weighted aggregation.
- Separate foreground/background results, failures and unknown observations.
- Notification posting is not exact visible-banner latency. Human observations are visible/not visible/uncertain.
- Live microphone demos contribute no formal accuracy/latency scores.
- Retain paired reference diagnostic limitations, including completed-utterance omissions and differing segment boundaries.

## 6. Include traceable examples

Use a few short examples illustrating actual false positives, missed scams or transcription issues. Do not show only favorable outcomes or treat example selection as overall accuracy evidence.

Keep originals unchanged. Redact personal details only in labeled presentation copies. Evidence index links examples to original artifact IDs and explains display transformations. Respect existing attribution/sharing rules for underlying sources.

## 7. Prepare primary and fallback demonstrations

Primary demonstration uses prerecorded mode: introduce simulation, Answer, show playback/live transcript/classification, background app, show real notification if triggered, and explain model output/limitations. Rehearse documented audio/build/settings. Do not force a scripted warning or guarantee one independently of model output.

Optional live microphone demonstration is experimental/functional if time permits, not quantitative evaluation. Reserved final recordings stay out of rehearsals until final evaluation completes. Demo provenance and rehearsal use are recorded.

Prepare a recording of the verified prototype, clearly labeled as recorded demonstration evidence with audio/build/configuration identities. On live failure, explain it and use the fallback; never portray fallback as live operation or replace evaluation results with it.

## 8. Build the shared-cloud package

```text
Submission/
├── README.md
├── slides/
│   ├── Editable final deck
│   └── Matching presentation PDF
├── demo/
│   ├── Demo guide
│   └── Fallback recording
├── evidence/
│   └── Selected reports, tables and figures
└── reproduction/
    └── Setup instructions and versioned code/artifact locations
```

README covers problem/ML task, navigation, actual capabilities/limitations, setup/prototype launch, code version, dataset/model retrieval, evidence locations and result conditions. Use versioned links/checksums; delivery exports identify authoritative originals. Avoid copying full datasets/checkpoints/run evidence merely to fill the package.

Verify linked dependencies as well as the top-level folder. A private GitHub URL alone is insufficient unless the professor can access it; provide accessible versioned source export if needed. Preserve required licenses/attribution and exclude credentials.

Select cloud service and final professor account before sharing. Verify access for seksan.m@ku.th or seksan.m@live.ku.th, as supplied by the owner. Record access-check evidence without credentials. Do not claim verification solely because a link was generated.

Upload/access grants/submission require owner authorization when performed. Multiple submissions are permitted by the assignment; revisions still preserve identities and owner review rather than silently replacing reviewed content.

## 9. Citations and evidence index

Use numbered citations matching proposal style: short references beside sourced claims/datasets/borrowed visuals, bibliography in backup slides, and lecture filename plus PDF page. Distinguish PDF pages from printed slide numbers.

Map own figures/results through evidence_index.csv: slide/figure/table/claim ID; source artifact and version/checksum; evaluated condition; transformation; scope/limitations. Check every cited source actually supports the associated claim. Never replace primary methodological support with unexplained result assertions.

## 10. Working outputs and authoritative exports

Store working outputs under project-root `06 - REPORT/`, distinct from `01 - PLANs/`.

| Output | Purpose |
|---|---|
| `README.md` | File purposes, reproduction and persistent evidence/media locations. |
| `presentation_outline.md` | Required topic mapping, evidence gaps and flexible timing. |
| `presentation_notes.md` | Thai explanation points, speaker transitions and Q&A preparation. |
| `evidence_index.csv` | Claims/visuals mapped to authoritative artifacts. |
| `slides/` | Editable final PowerPoint and matching PDF, main/backup sections. |
| `figures/` | Exported evidence-derived visuals and reproducible generation instructions/code. |
| `references.md` | Verified numbered bibliography. |
| `demo_guide.md` | Primary flow, optional microphone, assumptions and fallback. |
| `submission/` | Cloud-ready package following section 8. |
| `submission_manifest.json` | Reviewed final file versions/checksums, artifact links and delivery export relationships. |
| `rehearsal_and_access_checks.md` | Timing, visual checks, live/fallback readiness and professor access. |

Large media may reside in documented persistent storage linked by manifest. Earlier data/models/detailed evidence stay in owning locations. Submission copies are delivery exports, not new canonical experiment artifacts. Track suitable instructions/sources/approved presentation artifacts; keep credentials and unredacted sample evidence out of Git.

If Canva edits occur, identify the authoritative final version and make final editable deck/PDF exports reflect the same content. Recheck all numbers/citations/fonts/layout after the last export. Do not deliver an old PowerPoint beside a newer PDF as if they match. Preserve reviewed releases/identities when revising rather than overwriting provenance.

## 11. Rehearse and audit

Rehearse slides plus demo around the 12-minute target, within the owner-confirmed limits. Agree speaker transitions; both collaborators understand the entire pipeline and individually practice their explanations.

Prepare backup-supported answers for methods/models, leakage, tuning/epochs, F1/SD, selection, STT/context, false alarms/misses/failures and prototype limitations.

Audit all seven required topics; actual numeric evidence; implemented architecture; Thai/English rendering; readable figures/tables; citations/links; matched exports; demo/fallback; and cloud/dependency access. Inspect final slide/PDF rendering using appropriate presentation tools when actual authoring is authorized; planning does not perform that verification.

Ensure narrative clearly connects user problem → ML task → data → development → selection → application → measured outcome. A failed outcome must be explained, not concealed for presentation polish.

## 12. Completion and limitations

Complete when required deliverables are accurate, traceable/readable/reproducible, rehearsal/access checks recorded, and the owner reviews the final package. Verified results or explicit owner-approved incomplete-work disclosure are required before final approval. Submission is a separate authorized action.

Discuss applicable simulated/translated-data limitations; supplemental non-Scam/Unknow mapping not independently verified benign; small controlled/synthetic speech sample; single seed; descriptive SD; marked training/role-free inference; privileged caller research; context loss/STT errors; failures/interruptions; local/emulator rather than physical-phone/cellular-call operation; uncalibrated scores; and no demonstrated financial-loss prevention. Use actual evidence and label future work as proposed.

## References and rationale

- Owner-supplied Term Project Submission instructions: seven slide topics, cloud/README, grading and deadline; owner's subsequent clarification controls presentation/demo/Q&A planning.
- [Full Proposal](../00%20-%20DOCUMENTs/Full%20Proposal/Phoebe_FullProposal.pdf), PDF pp. 1–4, §§2–7: task, scope, rationale and development pipeline.
- [Pattern Recognition L06_Experimental Design and System Evaluation.pdf](course-lecture-sheets/Pattern%20Recognition%20L06_Experimental%20Design%20and%20System%20Evaluation.pdf), PDF pp. 19, 43, 45–50: reproducibility, condition-specific performance, component/system distinction, latency/resources/failures and reporting.
- Approved Plans 00–05 supply authoritative methods/evidence/limitations; use their primary references for actual method claims.

Main/backup slides fit presentation time while retaining detail for Q&A and collaborators. Evidence mapping makes results inspectable without new experiments. The package, matched exports and fallback support accessible delivery. Language, citations, output layout and rehearsal targets are confirmed project conventions, not prescribed experimental methods. Actual experiment completion and deadline feasibility depend on owning-plan runtime checkpoints, not this plan's approval.
