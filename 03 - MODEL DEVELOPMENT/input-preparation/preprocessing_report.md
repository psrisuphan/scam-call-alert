# Preprocessing report

## Current state

Stage 02 is complete locally under Plan 02. The shared component retrieves assigned records, produces both approved speaker representations, encodes labels, tokenizes with matching pinned checkpoints, applies approved fixed prefix limits, and dynamically pads batches. All owner checkpoints are resolved.

All 1,164 training records produce both representations. The owner approved the speaker and checkpoint-preparation proposals with "ok lets go" after the implementation checkpoint summary. The owner approved limits 510/510/512/512 and the keep-the-beginning policy with "yep sound good". Full token lengths and prepared inputs have been checked using training data only. No held-out test transcript was inspected for input design. Stage 01 integrity tests reload saved train/test files only to check frozen membership and canonical-row equality; the length-measurement component never loads the final-test file.

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

Measurement uses approved speaker/checkpoint preparation, matching pinned tokenizers, special tokens, no padding, and explicitly no truncation. The full training pool is covered for each of the eight model/representation combinations.

| Model | Representation | Median | 90th percentile | 95th percentile | Maximum | Approved limit | Above limit | Estimated content tokens lost |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| wangchanberta | whole_conversation | 368 | 555 | 584 | 706 | 510 | 209 (17.96%) | 2.93% |
| wangchanberta | caller_only | 212.5 | 302.7 | 324 | 388 | 510 | 0 (0.00%) | 0.00% |
| phayathaibert | whole_conversation | 353 | 531 | 560 | 668 | 510 | 156 (13.40%) | 1.88% |
| phayathaibert | caller_only | 202.5 | 288.7 | 309 | 369 | 510 | 0 (0.00%) | 0.00% |
| hplt | whole_conversation | 261 | 395.7 | 423 | 587 | 512 | 5 (0.43%) | 0.04% |
| hplt | caller_only | 141 | 215 | 235 | 329 | 512 | 0 (0.00%) | 0.00% |
| xlmr | whole_conversation | 345.5 | 524 | 553.85 | 630 | 512 | 141 (12.11%) | 1.50% |
| xlmr | caller_only | 188 | 275.7 | 300 | 352 | 512 | 0 (0.00%) | 0.00% |

[token_length_report.json](token_length_report.json) records distributions and coverage by source and binary label, input/configuration hashes, revisions, and dependencies. Percentiles use linear interpolation at (n-1)*p and are descriptive only.

Estimated loss is the number of content tokens beyond the prefix capacity, divided by all training content tokens for that representation. Required special tokens are accounted for. This is a token-count estimate, not a measure of semantic loss or prediction performance. No conversation has been excluded. The full-length measurement remains untruncated; prepared model-input copies apply the approved limits.

### Approved policy

Use fixed prefix limits shared across folds: WangchanBERTa **510**, PhayaThaiBERT **510**, HPLT **512**, XLM-RoBERTa **512**. Keep the beginning plus required special tokens when a conversation exceeds its approved limit. All policies and the owner approval reference are recorded in configuration. The tokenizer truncation side is checked as right, so the end is removed.

WangchanBERTa at its approved limit of 510 exceeds the limit for 209 training conversations (17.96%), with estimated content-token loss of 2.93%, compared with 437 (37.54%) and 10.19% at 416. The tradeoff is using positions beyond its documented 416-token pretraining length. Model-forward compatibility, runtime cost, and performance at 510 have not been tested.

All caller-only training inputs fit the approved limits. Whole-conversation inputs lose more context, so later representation comparisons also reflect different truncation exposure. Prefix truncation can remove late scam demands. Keeping the end could instead remove opening context; chunking requires later plans to settle labels and prediction aggregation before implementation.

The approved values come from checkpoint configuration bounds or an explicit resource budget, not a fitted training percentile. No strategy has been selected using prediction scores. No globally fitted data-derived length rule is implemented; any such rule would require fold- and condition-specific training-only fitting. Test data does not determine these decisions.

## Evidence and limitations

Runnable scripts now live under scripts/ as steps 6-9, following the merged dataset layout. Current main was merged into the Stage 02 branch; all existing plans and the seed-67 memberships were preserved.

Official model cards, config.json, and tokenizer_config.json are referenced at pinned revisions in preprocessing_config.json. Documentation file hashes and dependency versions are recorded there.
Upstream source inspected: https://github.com/vistec-AI/thai2transformers/blob/458fcd28911cc1d433a820907e468b66e7751ae3/thai2transformers/preprocess.py#L218
Transformers 4.57.6 installed AutoTokenizer and PreTrainedTokenizerBase definitions were inspected for revision pinning, special tokens, truncation, and dynamic padding. SentencePiece-to-fast-tokenizer conversion also requires protobuf.
Dependencies: transformers 4.57.6, tokenizers 0.22.2, huggingface_hub 0.36.2, sentencepiece 0.2.2, protobuf 7.36.2. No Torch/TensorFlow backend or GPU was required for tokenizer inspection.
Native normalization can normalize Unicode or whitespace; canonical CSVs remain unchanged. Long-context model feasibility and task performance are untested.
Ten input-component tests cover approved speaker representations, malformed/pending roles, hash-bound boundary recovery, empty-turn handling, assignment retrieval and checksums, shared validation membership, label maps, approval gates, complete training-pool coverage, aggregate length checks, and content-preserving checkpoint preparation.

Full training-pool checks exercise all 9,312 record/model/representation conversions (1,164 x 4 x 2). Each output is compared with the full token sequence: unchanged when it fits, otherwise the approved prefix plus the final special token. Exact cut counts and dropped-token totals match the aggregate report. IDs, numeric labels, model-only fields, attention masks, and dynamic padding are checked; source rows stay unchanged. Invented examples separately exercise bad inputs and synthetic final-test retrieval. Readable training text and eight unpadded JSONL exports are saved under prepared/, with all membership/label metadata outside predictive fields. Each contains the same 1,164 training IDs and is bound by a manifest to input/configuration/component/export-script hashes, dependencies, and pinned revisions. The added test verifies original/readable text, file hashes, identical temporary rebuilds, and overwrite refusal. No final-test export is made.

Model weights, model-forward execution, hardware feasibility, training, and task performance are outside this stage and remain untested. Final-test source issues may still surface during later evaluation; they must be handled explicitly, not used to redesign this training-only pipeline.

Population is unchanged. No augmentation, resampling, learned preprocessing, model training, tuning, or final test evaluation has occurred.
