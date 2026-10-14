# Authorized final held-out text evaluation

**Evaluation:** `phaya-final-heldout-20261014T195035Z-15182dca`

**Final run:** `phaya-final-replacement-primary-epoch2-20261012T050936Z`

**Run window:** 2026-10-14T19:50:41+07:00 to 2026-10-14T19:52:54+07:00 (Asia/Bangkok)

**Evidence:** `03 - MODEL DEVELOPMENT/final-evaluation/evaluations/phaya-final-heldout-20261014T195035Z-15182dca`

## Results

The frozen test assignment contains 291 conversations. The model produced 290 predictions (99.66% completion); one assigned primary Scam record failed during input role normalization before classifier inference. Classification scores use successful predictions only. Completion uses all assignments. The frozen threshold is 0.5; true labels are rows and class order is Not Scam, Scam.

| Scope | Assigned | Success | Failed | Completion | Scam precision | Scam recall | Scam F1 | Macro-F1 | Accuracy | TN | FP | FN | TP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Combined | 291 | 290 | 1 | 0.9966 | 0.9779 | 0.9708 | 0.9744 | 0.9758 | 0.9759 | 150 | 3 | 4 | 133 |
| Primary | 255 | 254 | 1 | 0.9961 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 128 | 0 | 0 | 126 |
| Supplemental | 36 | 36 | 0 | 1.0000 | 0.7000 | 0.6364 | 0.6667 | 0.7647 | 0.8056 | 22 | 3 | 4 | 7 |

Primary-only training produced 254 successful predictions on 255 primary test assignments; all 254 were correct. The one remaining primary assignment is the preprocessing failure described below, so these results do not mean all 255 were correctly classified. Supplemental data had 36 successful predictions, with 3 false positives and 4 false negatives. The seven classification errors were reviewed by an authorized project worker; the original generated error file is preserved unchanged, and the reviewed copy plus coverage/hash audit are in the private evidence directory.

## Protocol and provenance

Inference used the frozen PhayaThaiBERT final export (`phaya-final-replacement-primary-epoch2-20261012T050936Z`), whole-conversation role-free text, and threshold 0.5. Training was primary-only, whole-conversation with role markers, two epochs, without validation. The selected config SHA-256 is `53824363fce53b915fba658892f742d0bbb61f0bed6646086b5393712dfcb88b`; model weights SHA-256 is `af64d3a917d5db82bc9dfe794c8f29125bbf13ad9060f726c75ac001f99d838b`; artifact-manifest SHA-256 is `2acfa4f1413c58716b29f250909c6ed1456f274b5dad19f944e96d9fb6b0c8ab`. The approved assignment/test identities and exact outputs are bound in [the private authorization and evaluation artifacts](evaluations/phaya-final-heldout-20261014T195035Z-15182dca/owner_authorization.json).

The run used Python 3.12.15, PyTorch 2.14.1, Transformers 4.57.6, tokenizers 0.22.2, CPU inference on macOS, and tokenizer class `CamembertTokenizerFast`. The inference process emitted a generic Transformers warning about a regex pattern; the frozen tokenizer uses Metaspace preparation. Hugging Face has documented [false warnings for locally loaded non-Mistral tokenizers](https://github.com/huggingface/transformers/issues/42591); this is context, not proof about this run's tokenizer. No regex or tokenizer setting was changed, and the warning alone does not establish corrupted tokenization. The selected model/STT Mac compatibility record passed for development audio; that is not evidence of held-out audio accuracy.

## Failure and limits

`hf_000418` is an execution failure, not a classification error: the frozen input preparation rejected source role value `r` and required owner confirmation. It has no model probability or predicted class. The source and role mapping were not changed and the record was not rerun. Its assigned truth is retained in the failure review; the confusion matrix therefore uses 290 successful predictions.

This is one held-out text evaluation at a frozen threshold. No confidence interval is reported, and no model, threshold, preprocessing, or context setting was changed from these results. Because training used only primary data and the supplemental subset has 36 records, the supplemental scores are limited transfer-domain evidence. These metrics do not establish end-to-end audio performance, real-call accuracy, production readiness, or completion of other app-context and fidelity gates.
