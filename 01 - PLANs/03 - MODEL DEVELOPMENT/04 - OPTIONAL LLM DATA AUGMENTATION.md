# 04 - OPTIONAL LLM DATA AUGMENTATION

## Purpose and activation

This owner-confirmed outline reserves an optional branch for improving training-data diversity if the original-data cross-validation results are unsatisfactory after owner review. It is not an executable implementation plan. Finalize the methods, experiment scope, outputs and approval checkpoints with the owner before generating data or training augmented models.

Complete the approved 120-run original-data main CV comparison first, before final candidate selection. The five caller-only runs depend on that selection and are not an activation prerequisite. Review validation Scam F1, fold SD, supporting metrics and errors before deciding whether to activate this branch. No numerical activation threshold is fixed. The branch may remain unused.

Decide before final-test access. Final-test results must not trigger augmentation or guide generation, filtering, model selection or settings. Preserve the original-data experiment evidence as the comparison baseline.

## High-level scope

1. **Select a supported generation method.** Review primary research and choose a procedure appropriate to Thai scam-call dialogues. Explain the selected method, alternatives, evidence and limitations. Define grounding sources, structured scenarios, prompt construction and constraints; do not rely on an unspecified request to generate more calls.
2. **Confirm generation scope and resources.** Agree which datasets/classes to augment, permitted scenario variations, generator/access, settings, sample counts, review effort and compute/time budget. Reassess deadline feasibility before execution.
3. **Generate only within eligible training partitions.** During CV, prompts, examples and any data-derived generation/filtering decisions must use the corresponding fold-training records. Validation and test examples must not be generation seeds or prompt examples. Preserve parent/scenario provenance and related-record separation; do not add synthetic samples to validation or test or regenerate frozen original assignments.
4. **Verify quality before acceptance.** Establish checks for Thai language quality, realistic dialogue, speaker consistency, evidence supporting the intended label, diversity, exact/near duplicates and contamination. Confirm review responsibilities and acceptance/rejection rules. An LLM-generated label alone is not verified ground truth.
5. **Run a controlled development comparison.** Compare original training data against original plus accepted synthetic data under a separately confirmed protocol. Preserve unchanged validation membership and consistent metrics; confirm models/configurations, mixing ratios, tuning/epoch opportunities and comparisons before running them.
6. **Decide and report.** Review CV Scam F1, SD, supporting metrics, cost and limitations with the owner. Improvement is not guaranteed. Preserve unsuccessful outcomes and justify adopting or rejecting augmentation. If adopted, approve its full-training-pool generation procedure and update affected instructions before final retraining and final evaluation.

## Dependencies and boundaries

- Existing Plans 00–02 remain the authoritative original-data preparation, assignments and input pipeline.
- Plan 03/01 owns baseline comparison evidence and final candidate selection; this optional branch is considered during development, before candidate release and final-test access, despite its filename numbering.
- The existing no-augmentation policy remains in effect until the owner approves a detailed optional protocol and corresponding changes to affected plans/configurations. This outline does not authorize changing completed data artifacts or reducing the original comparison matrix.
- Reuse the approved input/training/evaluation components. Resolve necessary integration changes with the owner; do not silently mix synthetic records into canonical datasets.
- Final evaluation, packaging, STT, application development and system evaluation remain in their owning plans.
- Existing datasets are simulated/translated. More synthetic dialogues do not establish performance on real telephone calls.

## Deliverables to define when activated

Specify the exact owning paths, schemas and Git/persistent-storage rules before implementation. The detailed plan should cover:

- Research rationale, approved generation/quality/experiment protocol and activation decision.
- Generator identity/settings, prompts, grounding sources, parent/scenario IDs and fold eligibility.
- Accepted synthetic records and all rejection reasons, with traceable labels and review evidence.
- Separate original/augmented run identities, CV comparison results, resource evidence and adoption rationale.

## Deferred confirmation checkpoints

Generation method; grounding/scenarios; dataset/class coverage; generator and access/cost; settings and quantities; quality-review rules; fold-specific generation and final-pool procedure; comparison scope and adoption criteria; output layout and storage rules.

Discuss these when activation is considered, show the complete detailed draft, verify feasibility/leakage/cross-plan consistency, and obtain owner approval before saving it as an implementation-ready plan. Planning approval alone does not authorize execution.

## Evidence to revisit when finalizing

- L03, `Pattern Recognition L03_Data Preprocessing and Feature Engineering_final.pdf`, PDF pp. 20, 22 and 43: augmentation/diversity, intended-label preservation and leakage boundaries. The lecture supports these principles, not a specific LLM generation protocol.
- L05, `Pattern Recognition L05_Model Selection & Hyperparameter Tuning.pdf`, PDF pp. 37–38: development selection before final evaluation; do not select methods from test results.
- [Li et al., EMNLP 2023](https://aclanthology.org/2023.emnlp-main.647/): synthetic-data effectiveness varies across classification tasks, supporting a measured comparison rather than assuming improvement.

These references motivate the branch and its safeguards. The exact generation method remains unselected; verify suitable research when preparing the detailed protocol.
