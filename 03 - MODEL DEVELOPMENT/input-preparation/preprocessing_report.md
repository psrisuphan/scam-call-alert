# Preprocessing report

## Implementation and verification scope

The shared procedure supports whole-conversation and caller-only representations, each rendered with neutral role markers or without structural markers. Source parsing and all prior owner-approved checkpoint preparation and fixed limits are unchanged. App text uses an unlabeled entry point and never runs source-prefix detection.

Only the 1,164 training records are used for design, coverage, export and parity checks. No held-out project transcript is loaded; the verification suite explicitly rejects reads of the actual held-out CSV while permitting synthetic fixtures. Final-test loader checks use invented records; the frozen test checksum is taken from the previously committed file bytes without decoding or inspecting them. That checksum adds a guard for later authorized evaluation; it does not select any preprocessing setting.

The owner explicitly authorized replacing the superseded two-condition generation on 2026-10-04: "keep only the one that meets the Plan criteria itself" and remove/replace previous generations. The replacement is generated at separate temporary paths and verified before installation at the Plan 02 paths. No archive is added to the project. Existing canonical CSVs and split assignments remain unchanged. This replaces the earlier preservation instruction for this generation only; future generation commands still refuse to overwrite existing exports and reports.

## Source-role findings

Primary standard tags: ผู้โทร -> Caller, ผู้รับ -> Receiver, caller -> Caller. Supplemental tags: Call -> Caller, User -> Receiver, based on source tag meaning, not first-speaker position or target label.
Supplemental training records: 82 with Call and User, 61 with Call only. Caller-only calls remain valid in both representations.
Primary formatting removes source-marker colon spacing and inter-turn edge whitespace; turn content, punctuation, numbers, URLs, and mixed languages are otherwise preserved. Supplemental parsing preserves parentheses inside speech and removes only source wrappers.

| Variant | Occurrences | Training sample IDs | Approved handling |
|---|---:|---|---|
| ผู้รับสาย | 22 | hf_000058, hf_000059, hf_000070, hf_000158, hf_000184, hf_000193, hf_000223, hf_000261, hf_000298, hf_000300, hf_000338, hf_000342, hf_000376, hf_000382, hf_000424, hf_000541, hf_000580, hf_000587, hf_000758, hf_000793, hf_000961 | Receiver |
| คนรับ | 3 | hf_000058, hf_000167, hf_000396 | Receiver |
| ผู้รับเงิน | 1 | hf_000105 | Receiver |
| ตัวรับสัญญาณ | 2 | hf_000108, hf_000150 | Receiver |
| R | 1 | hf_000424 | Boundary recovery required; not a simple alias |
| ผู้โทรเข้า | 1 | hf_000638 | Caller |
| ราเชล | 1 | hf_001029 | Caller |

Three training conversations end with an empty source marker: hf_000382, hf_000484, hf_000512. Approved handling preserves the empty neutral turn without adding dialogue or changing the population. Only these trailing empty turns are allowed; unexpected empty turns still fail.

The 30 previously blocked training records now parse. No records have been excluded or changed in the source CSVs.

Selected original English fields were inspected only for eligible training IDs (hf_000105, hf_000108, hf_000150, hf_000424, hf_001029). They confirm receiver roles for ผู้รับเงิน and ตัวรับสัญญาณ. The named Rachel turn also appears in the original source, while the conversation opens with a different caller name. The owner approved the contextual Caller mapping; this does not establish that names are generally reliable role indicators.

hf_000424 has a malformed boundary: Thai contains `Windows บวกกับตัวรับ R: โอเค...`, while English contains `Windows key plus R. receiver: Okay...`. Blindly mapping `R:` to Receiver would remove the keyboard key R from caller speech. Approved structural recovery replaces `ตัวรับ R:` with `R ผู้รับ:` in the representation copy, keeping R in caller speech and recovering the Receiver boundary. It applies only to hf_000424 with transcript SHA-256 `880a7f2d68adeef8f48a7fa556efae1b7fa5b415ae2316cb86ac7fb682f2806e` and exactly one matching fragment. Altered source text fails. This removes the misplaced translated receiver marker, not dialogue content; the original CSV remains unchanged.

## Official checkpoint findings

Tokenizers were loaded without model weights or remote code. All revisions are pinned in preprocessing_config.json.

| Model | Revision | Tokenizer reported limit | Configuration bound | Approved budget |
|---|---|---:|---:|---:|
| wangchanberta | b81d38df6b4755dbedec0bfea863c9956cbb963e | Unset sentinel | 510 | 510 |
| phayathaibert | a81ece95beb7a24271905d30c23887d343193c62 | 510 | 510 | 510 |
| hplt | a7876746d32bf9ee5b2cc00bbb4acd4714b1c88a | Unset sentinel | 16384 | 512 |
| xlmr | e73636d4f797dec63c3081bb6ed5c7b0bb3f2089 | 512 | 512 | 512 |

WangchanBERTa was pretrained at sequence length 416. Its RoBERTa-style position table has 512 rows with pad index 1, giving 510 usable non-padding positions. The tokenizer's huge max-length value is an unset sentinel, not a supported limit.
PhayaThaiBERT explicitly advertises tokenizer limit 510 and a 512-position table. Its card demonstrates the existing <_> space marker but provides little preparation detail. The linked Colab required Google sign-in in the research fetch; no account interaction was attempted.
HPLT configuration declares max_sequence_length=16384. This is not a verified local runtime/memory budget. The card requires custom remote MODEL code and transformers 4.57.6; its tokenizer loads natively without remote code. No model code or weights were executed. Static inspection of the pinned sequence-classification forward method (lines 934-976) confirms input_ids and attention_mask; tokenizer-produced token_type_ids are unused, so the component omits them from model inputs.
XLM-RoBERTa advertises tokenizer limit 512 and 514 positions with pad index 1.

## Checkpoint preparation conflict

WangchanBERTa's official process_transformers helper lowercases, normalizes HTML/whitespace, removes empty brackets, reduces repeated characters and words, and uses dictionary tokenization. Repetition removal can alter OTPs, numbers, or other scam evidence, conflicting with Plan 02.
Owner-approved alternative for WangchanBERTa and PhayaThaiBERT: retain all characters/words and source-neutral role markers; only turn newlines into spaces and encode spaces with the existing <_> marker. No new vocabulary tokens. This is a deliberate project deviation from full upstream preprocessing. Model-native tokenizer normalization still applies.
HPLT and XLM-RoBERTa use their native pretrained tokenizer normalization with no manual rewriting.

## Length checkpoint

Approved fixed prefix budgets, including special tokens: WangchanBERTa 510, PhayaThaiBERT 510, HPLT 512, XLM-RoBERTa 512. HPLT's 512 is an owner-approved conservative resource budget, not its architectural maximum.

Measurement uses approved speaker/checkpoint preparation, matching pinned tokenizers, special tokens, no padding, and explicitly no truncation. The full training pool is covered for each of the sixteen model/representation/marker-condition combinations.

| Model | Representation | Markers | Median | p90 | p95 | Maximum | Limit | Above limit | Estimated content tokens lost |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| wangchanberta | whole_conversation | role_marked | 368.0 | 555.0 | 584.0 | 706 | 510 | 209 (17.96%) | 2.93% |
| wangchanberta | whole_conversation | role_free | 275.0 | 400.0 | 424.0 | 491 | 510 | 0 (0.0%) | 0.0% |
| wangchanberta | caller_only | role_marked | 212.5 | 302.7 | 324.0 | 388 | 510 | 0 (0.0%) | 0.0% |
| wangchanberta | caller_only | role_free | 167.0 | 235.7 | 257.0 | 311 | 510 | 0 (0.0%) | 0.0% |
| phayathaibert | whole_conversation | role_marked | 353.0 | 531.0 | 560.0 | 668 | 510 | 156 (13.4%) | 1.88% |
| phayathaibert | whole_conversation | role_free | 270.0 | 396.0 | 419.0 | 479 | 510 | 0 (0.0%) | 0.0% |
| phayathaibert | caller_only | role_marked | 202.5 | 288.7 | 309.0 | 369 | 510 | 0 (0.0%) | 0.0% |
| phayathaibert | caller_only | role_free | 164.0 | 232.0 | 253.0 | 309 | 510 | 0 (0.0%) | 0.0% |
| hplt | whole_conversation | role_marked | 261.0 | 395.7 | 423.0 | 587 | 512 | 5 (0.43%) | 0.04% |
| hplt | whole_conversation | role_free | 187.5 | 280.7 | 303.0 | 449 | 512 | 0 (0.0%) | 0.0% |
| hplt | caller_only | role_marked | 141.0 | 215.0 | 235.0 | 329 | 512 | 0 (0.0%) | 0.0% |
| hplt | caller_only | role_free | 103.0 | 157.0 | 174.85 | 257 | 512 | 0 (0.0%) | 0.0% |
| xlmr | whole_conversation | role_marked | 345.5 | 524.0 | 553.85 | 630 | 512 | 141 (12.11%) | 1.5% |
| xlmr | whole_conversation | role_free | 273.0 | 407.0 | 435.7 | 488 | 512 | 0 (0.0%) | 0.0% |
| xlmr | caller_only | role_marked | 188.0 | 275.7 | 300.0 | 352 | 512 | 0 (0.0%) | 0.0% |
| xlmr | caller_only | role_free | 157.0 | 229.0 | 251.0 | 299 | 512 | 0 (0.0%) | 0.0% |

[token_length_report.json](token_length_report.json) records distributions and coverage by source and binary label, input/configuration hashes, revisions, and dependencies. Percentiles use linear interpolation at (n-1)*p and are descriptive only.

Estimated loss is the number of content tokens beyond the prefix capacity, divided by all training content tokens for that representation. Required special tokens are accounted for. Marked-condition content-token totals include neutral role-prefix tokens as well as spoken text. This is a token-count estimate, not a measure of semantic loss or prediction performance. No conversation has been excluded. The full-length measurement remains untruncated; prepared model-input copies apply the approved limits.

### Approved policy

Use fixed prefix limits shared across folds: WangchanBERTa **510**, PhayaThaiBERT **510**, HPLT **512**, XLM-RoBERTa **512**. Keep the beginning plus required special tokens when a conversation exceeds its approved limit. All policies and the owner approval reference are recorded in configuration. The tokenizer truncation side is checked as right, so the end is removed.

WangchanBERTa at its approved limit of 510 exceeds the limit for 209 training conversations (17.96%), with estimated content-token loss of 2.93%, compared with 437 (37.54%) and 10.19% at 416. The tradeoff is using positions beyond its documented 416-token pretraining length. Model-forward compatibility, runtime cost, and performance at 510 have not been tested.

All caller-only training inputs fit the approved limits. Whole-conversation inputs lose more context, so later representation comparisons also reflect different truncation exposure. Prefix truncation can remove late scam demands. Keeping the end could instead remove opening context; chunking requires later plans to settle labels and prediction aggregation before implementation.

The approved values come from checkpoint configuration bounds or an explicit resource budget, not a fitted training percentile. No strategy has been selected using prediction scores. No globally fitted data-derived length rule is implemented; any such rule would require fold- and condition-specific training-only fitting. Test data does not determine these decisions.

## Evidence and limitations

Runnable scripts live under scripts/ as steps 6–9, following dataset scripts 1–5. This revision implements the owner-approved four-condition Plan 02 and shared unlabeled interface; seed-67 memberships and earlier approved source/length/checkpoint decisions are preserved.

Official model cards, config.json, and tokenizer_config.json are referenced at pinned revisions in preprocessing_config.json. Documentation file hashes and dependency versions are recorded there.
Upstream source inspected: https://github.com/vistec-AI/thai2transformers/blob/458fcd28911cc1d433a820907e468b66e7751ae3/thai2transformers/preprocess.py#L218
Transformers 4.57.6 installed AutoTokenizer and PreTrainedTokenizerBase definitions were inspected for revision pinning, special tokens, truncation, and dynamic padding. SentencePiece-to-fast-tokenizer conversion also requires protobuf.
Dependencies: transformers 4.57.6, tokenizers 0.22.2, huggingface_hub 0.36.2, sentencepiece 0.2.2, protobuf 7.36.2. No Torch/TensorFlow backend or GPU was required for tokenizer inspection.
Native normalization can normalize Unicode or whitespace; canonical CSVs remain unchanged. Long-context model feasibility and task performance are untested.
The expanded input checks cover all 18,624 record/model/condition conversions (1,164 × 4 × 4): neutral rendering, content/order preservation, roles and boundary approvals, numeric labels, fixed prefix truncation, special tokens, unpadded exports, attention masks, dynamic batch padding and assignment/source/group/fold metadata. The marked token arrays are also compared against the previous generation to verify unchanged behavior. Configuration identities intentionally change with the component/configuration and marker condition.

All 4,656 role-free whole-conversation record/model pairs are passed through both the dataset adapter and the unlabeled entry point; inputs, configuration identities and processing notices must agree. Synthetic ordinary text containing role-like words and prefixes must retain them and must not call a dataset loader or role parser. Marker removal is tested before tokenization/truncation, with a small synthetic budget. Condition mixing, invalid text, stale export manifests, modified cache files, mismatched tokenizer checkpoints, expanded vocabularies, changed source records and changed synthetic held-out content are rejected. Cached tokenizers load from the exact pinned revision snapshot, preventing incidental remote metadata probes; verification can run fully offline after caching assets.

The readable CSV stores four pre-checkpoint conditions and the unchanged original transcript. Sixteen JSONL files contain unpadded model fields plus separate label/provenance/condition/notices metadata. The manifest binds these to training data, assignments, configuration, component/export code, dependency versions and tokenizer revisions. `load_prepared` retrieves only unchanged training records selected from authoritative assignments and rejects stale artifacts. Tests rebuild separately and compare every file byte-for-byte. Existing generation commands refuse replacement.

Exact role-free whole-conversation collision review across all 1,164 training records found zero duplicate rendered strings. No records were deleted and assignments were not regenerated. This is an exact rendered-text check, not proof that no semantic variants exist. Caller-only coincidences are not grounds for deleting complete conversations.

Model weights, model-forward execution, hardware feasibility, training, and task performance are outside this stage and remain untested. Final-test source issues may still surface during later evaluation; they must be handled explicitly, not used to redesign this training-only pipeline.

Population is unchanged. No augmentation, resampling, learned preprocessing, model training, tuning, or final test evaluation has occurred.

## Verification results (2026-10-04)

- Script 6 verified cached official-documentation hashes and pinned tokenizer properties for all four checkpoints, fully offline; no weights or remote model code were loaded.
- Script 9 passed **18 tests** against the installed project outputs with `HF_HUB_OFFLINE=1`. This includes all **18,624** record/model/condition conversions, all **4,656** dataset/unlabeled role-free whole-conversation parity pairs, exact length-report reproduction and byte-identical separate export regeneration.
- All **9,312** marked record/model inputs match the previous generation in predictive fields, numeric labels, sample/source/group IDs and fold/split metadata. New condition/configuration identities and notices are intentional.
- Exact role-free whole-conversation collision count: **0** across **1,164** training records. No canonical record or saved assignment changed.
- Normal export/report regeneration refuses to overwrite existing outputs. Replacing the superseded generation used the explicit owner exception recorded above.
- Final-test loader behavior was tested only with invented temporary records. The suite rejects actual held-out CSV reads. No final-test export, learned fit, augmentation, resampling, training or performance evaluation was performed.

The only completion states are recorded in `01 - PLANs/README.md`. Model-forward compatibility, training feasibility and paired validation remain responsibilities of model-development plans.

## Owner-approved padding correction and verification (2026-10-04)

A further audit reproduced a missing batch-assembly guard: the prior `pad_batch` accepted another checkpoint's tokenizer or changed padding settings. The existing exports were correct, but the previous 18 tests did not cover this misuse. The owner authorized correction with "yes make sure everything meets the Plan's criteria." No selected preprocessing method, dataset, membership, tokenizer revision or token limit changed.

Each prepared item now carries a serializable `padding_contract` outside predictive fields. Batch assembly compares the provided tokenizer's checkpoint/revision, class, padding token/side, truncation side, special-token count and added-token identity with every frozen contract. It rejects missing contracts, mismatched checkpoints (including tokenizers sharing class/pad ID), changed settings/vocabulary, invalid field lengths and non-unpadded attention masks. Metadata remains outside `inputs`.

The corrected generation was built separately, checked, then installed with the owner's corrective authorization. All **18,624** predictive inputs, labels, source/sample/group IDs, saved split/fold assignments, representation/marker conditions and processing notices match the previous generation. Added contract metadata and updated component/configuration identities are intentional; old caches are rejected.

The final installed generation passed **20 Plan 02 tests fully offline**, including the new padding regressions, full population conversion, dataset/STT parity, exact export and length-report reproduction, stale-artifact rejection and frozen membership. Plans 00 and 01 also passed their **10** and **7** tests again: **37 tests passed in total**. No required-output or current-plan compliance issue remains identified by this audit. Canonical data and saved splits remain unchanged. Project held-out transcripts were not used for input design or Plan 02 tests; Plan 01 verification only checks their fixed partition integrity.

Completion states are recorded only in the plans README. Training feasibility/model forward checks remain outside these three tasks.
