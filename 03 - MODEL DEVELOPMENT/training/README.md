# Model training implementation

This is the reusable implementation for Plans [03/00](../../01%20-%20PLANs/03%20-%20MODEL%20DEVELOPMENT/00%20-%20MODEL%20TRAINING.md) and [03/01](../../01%20-%20PLANs/03%20-%20MODEL%20DEVELOPMENT/01%20-%20HYPERPARAMETER%20TUNING%20AND%20MODEL%20SELECTION.md). Read those plans and the current [implementation notes](../IMPLEMENTATION%20NOTES.md) before running anything. A config file does not itself authorize a run; resolve the owning plan's approval and runtime gates first.

## Active source files

- `train.py` is the command-line entry point.
- `trainer.py` implements approved training, validation, logging, and artifact checks.
- `full_context.py` implements WangchanBERTa's approved overlapping-window path.
- `../input-preparation/inputs.py` is the authoritative frozen input/membership loader.
- `../selection/runtime.py` supplies focused aggregation and saved-fold membership validation for the trainer. `../selection/workflow.py` is the current primary-only-first manifest/import path.
- `run_config.template.json` is a deliberately non-runnable template. Copy it outside `runs/`, fill every required field, and bind the owner approval and settings digest.
- `requirements.txt` pins the tokenizer/input Python dependencies. PyTorch is supplied by the selected runtime and must be recorded from that runtime; this file intentionally does not replace Colab's PyTorch installation.

All six WangchanBERTa configurations (30 fold fits) are complete and included in the 75-row primary-only matrix. Reuse their existing run IDs and persistent evidence; do not rerun them. The current result summary is in `../selection/comparison_report.md`, with metric trajectories in `../selection/cv_results.csv`. The complete Plan 03/01 report still requires chunk-count/source stratification and timing/error breakdowns from verified run predictions and histories. **Do not run the current `selection/workflow.py manifest` or `import-verified-export` commands against the tracked manifest/results:** manifest generation would erase completed identities and the original-export importer handles only the initial max/LR 2e-5 configuration.

## Reproducing or launching a run

All six completed configurations used WangchanBERTa revision `b81d38df6b4755dbedec0bfea863c9956cbb963e`, primary-only whole-conversation role-marked training, 508-token windows at stride 381 (127-token overlap), class-wise max or mean pooling, one conversation-level cross-entropy loss, learning rates `2e-5`, `3e-5`, and `5e-5`, seed 67, effective batch 16, three epochs, 10% warmup rounded up, paired role-free/role-marked validation, threshold 0.5, and Colab T4 FP16. The exact settings, scores, per-fold run IDs, artifact paths, and hashes are in `../selection/experiment_manifest.csv`, `../selection/cv_results.csv`, and `../selection/WANGCHANBERTA REPRODUCTION GUIDE.md`.

Detailed run configs, environment records, histories, sample-level predictions, model weights and checkpoints remain in the approved persistent Drive folder identified by the manifest. They are intentionally not committed. Verify their SHA-256 values against the manifest before reuse. The repository's aggregate scores are a summary; they do not replace those original run files.

After the required gates are resolved and a separate owner-approved config is saved in persistent storage, launch one run with:

```bash
python "03 - MODEL DEVELOPMENT/training/train.py" --config /persistent/path/owner-approved-run.json
```

Install the pinned dependencies with `pip install -r "03 - MODEL DEVELOPMENT/training/requirements.txt"` while preserving the runtime's installed PyTorch. Record Python, PyTorch, Transformers, tokenizer, CUDA/device, checkpoint revision, and the hashes of the source, input exports, assignments, and config for each new run. Do not infer a hardware/runtime setting from this historical run.

## Interruption and evidence policy

Mid-epoch recovery was dropped after implementation attempts failed. If a fit is interrupted before its target completes, retain its partial progress, history, metrics, predictions, logs, timing/resources, config and failure reason; restart from the pinned pretrained checkpoint with fresh state and a new run ID, using the same approved configuration and membership. Do not resume a failed/interrupted fit. An epoch extension after a successfully completed target is a separate, explicitly approved operation.

The runner records flushed scalar progress after optimizer updates. This supports progress review but is not a checkpoint. Keep run outputs in the approved persistent storage, outside Git. Do not place held-out data, sample-level predictions, credentials, checkpoints or model weights in the source repository.

## Historical records and limitations

`training_report.md` retains the failed recovery investigation, discarded fixed-prefix diagnostic history, and implementation decisions as provenance. The discarded Colab recovery probes and stale notebooks are not part of the active handoff. The completed run used trainer SHA-256 `49753b7d6c1a9465c4e5434fbb43a6da9e0c152f82136f2244a66eb9578fcb24`; the current trainer is `f62c0b4373f7853337ab94cb8cca5e1aa19a9b8e9e45a40304c8f07f5daea64a`. The refactor loads aggregation/membership validation from focused `selection/runtime.py` rather than the legacy selection CLI. Its regression tests pass, but this new source identity did not produce the completed run. The original source archive and hash remain in Drive and are the authority for the exact executed source. Re-running a configuration is a new stochastic execution, not a bit-for-bit recreation of its original weights or scores.

The current repository provides source and aggregate-result provenance for the six completed WangchanBERTa configurations. The other three candidate comparisons are still pending; these results do not select the final candidate. Exact replay additionally requires the original Drive run artifacts named in the manifest. No final-test data or results are included in this component.
