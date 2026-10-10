# Google Colab execution notes

Use the approved plans and [`training/README.md`](../README.md) as the procedure. The old notebooks described fixed-prefix diagnostics or an obsolete 60-fit matrix and are not approved execution entry points. Do not run them.

The current implementation is plain Python. Build a deterministic training-only archive from the approved repository checkout with:

```bash
python "03 - MODEL DEVELOPMENT/training/colab/build_training_source_zip.py" --output-dir /tmp/scam-call-alert-colab
```

The archive allowlist contains the current training and selection source, tests, plans, and only the training pool; it excludes the held-out test set, run artifacts, and unused caller-only input exports. Verify the generated inventory and archive SHA-256 before transfer. In Colab, provide that archive, verify its commit/source hashes, mount only the approved persistent output folder, and confirm the actual accelerator and writable storage before a run. Follow `training/requirements.txt` without replacing Colab's PyTorch; record installed versions and device in each run's environment evidence.

After the owning plan's run gates are resolved, launch only a separately owner-approved config:

```bash
python "03 - MODEL DEVELOPMENT/training/train.py" --config /content/drive/MyDrive/<approved-folder>/configs/<approved-run>.json
```

The command does not mount Drive, create approval, choose a device, or authorize an experiment. Keep run output and sample-level evidence in the approved Drive folder, never in Git. If a runtime ends before an approved target completes, retain its partial evidence and start a fresh run ID from the pretrained checkpoint; mid-epoch resume was dropped by the project owner.

A repository checkout remains the source of truth. The builder only packages its explicit allowlist and does not mount Drive, authorize or launch training, or publish artifacts.
