# Google Colab execution notes

Use the approved plans and [`training/README.md`](../README.md) as the procedure. The old notebooks described fixed-prefix diagnostics or an obsolete 60-fit matrix and are not approved execution entry points. Do not run them.

The current implementation is plain Python. In a Colab runtime, provide a checkout/source archive from the approved repository revision, verify its commit and source hashes, mount only the approved persistent output folder, and confirm the actual accelerator and writable storage before a run. Follow `training/requirements.txt` without replacing Colab's PyTorch; record the installed versions and device in each run's environment evidence.

After the owning plan's run gates are resolved, launch only a separately owner-approved config:

```bash
python "03 - MODEL DEVELOPMENT/training/train.py" --config /content/drive/MyDrive/<approved-folder>/configs/<approved-run>.json
```

The command does not mount Drive, create approval, choose a device, or authorize an experiment. Keep run output and sample-level evidence in the approved Drive folder, never in Git. If a runtime ends before an approved target completes, retain its partial evidence and start a fresh run ID from the pretrained checkpoint; mid-epoch resume was dropped by the project owner.

The local `build_training_source_zip.py` is a historical source-bundle builder. Its allowlist and legacy baseline-archive behavior have not been reconciled with the current approved handoff; do not use it to publish an archive until it is reviewed and updated. A repository checkout is the current source of truth.
