# Application architecture

## Execution topology

```text
Android Emulator (Pixel 6, API 36)
  React Native + Expo embedded release demo build
  - recorded-audio and live-microphone modes
  - playback and host-capture controls, live transcript
  - current classifier result and Android notifications
            |
            | configurable local request endpoint
            | emulator-to-host connectivity must be verified
            v
MacBook Air M2 (local host)
  Local service
  - session-bound Mac microphone capture and progressive recorded input
  - selected Thai STT adapter
  - transcript reconciliation and app-context assembly
  - interim/official classifier adapter as permitted by Plan 03/03
```

The application owns interaction, recorded playback, host-capture controls, transcript and result display, session state, and system notifications. The local service owns physical Mac microphone capture, speech recognition, transcript reconciliation, context assembly, and classifier invocation. It accepts only audio already captured or reached by playback and returns chronological role-free text and classification results. It must never receive future audio or source role markers.

## Current host and emulator

- Host: project owner's MacBook Air M2, macOS 27.0.1, 8 GiB unified memory.
- Emulator: Pixel 6 profile, Android 16 / API 36, Google APIs ARM64 system image.
- The host is below Android's recommended emulator memory level. API 36 selected software graphics on this host during first boot. CPU classifier / MPS STT passed live acoustic and recorded short-tail functional checks; emulator freezes and the emulator-first startup sequence remain documented limitations. These checks do not establish broader resource robustness or formal app freeze.
- The AVD uses a 4 GiB virtual data partition and a 256 MiB SD card to fit the available disk. This is an emulator-host setting, not a change to dataset or model storage policy.

## Model and speech components

- STT selected for integration: PyThaiASR's Wav2Vec2 large XLSR Thai checkpoint, pinned in `../stt/stt_config.json`. Its standalone benchmark excluded the classifier; subsequent combined functional checks are distinct from that benchmark.
- Current classifier: owner-approved interim final-trained PhayaThaiBERT; the same weights have completed held-out text evaluation, while official packaging/parity remains separate. Plan 04/01 permits the provisional development context screen and accumulated demo choice with disclosed limitations. The official evaluated bundle is still required if formal release is pursued. The earlier WangchanBERTa app fixture is retired; its historical evidence is retained.
- The Python service is implemented on host loopback port 8765, reached by the emulator at `10.0.2.2:8765`. It loads the selected STT on MPS and the temporary classifier on CPU. This execution configuration and diagnostic settings are not yet frozen for experiments. The model adapter can be replaced explicitly with the official handoff loader; affected checks must be repeated.

## Permissions and background operation

Request Android notification permission through visible app interaction; Mac microphone access belongs to the host Python process and its macOS permission flow. Android live mode does not request microphone access or open AudioRecord. Accept starts a host capture session; Decline creates none. Start monitoring while the application is visible, then retain native polling and warnings when backgrounded. Live mode uses a data-sync foreground service; recorded mode uses media playback. The ongoing service notification is separate from the Scam warning. This demonstrates live host speech analysis and emulator interaction, not physical Android microphone or cellular-call capture.

## Deliberately unresolved integration settings

The base runtime pins were approved. Diagnostic implementations/settings are in `integration_config.json` and `interface_contract.md`; endpoint, windows/reconciliation, segmentation/revisions, context bounds, queues, timeouts/retries and combined compatibility still require the plan's evidence/confirmation before formal experiments. A staged background recording has completed with actual recognition/classification and an observed Android banner; this does not freeze the integration or establish broader reliability.

The native module uses `MediaPlayer` for recorded WAV playback and sends only ranges already reached. For live mode it sends Start/Stop commands and polls the host; it does not capture or upload microphone PCM. A native scheduled worker polls results and posts warnings while the activity is backgrounded; a separate local watchdog can pause recorded playback during blocked networking. The host preserves ordered windows and runs a separate segment scheduler/classifier worker. JS timers only refresh the display.

The owner approved direct Mac capture on 2026-10-14 after built-in forwarding and authenticated injectAudio trials failed to provide sustained production AudioRecord input. Their evidence remains in integration_checks.md. The current path uses sounddevice/CoreAudio at 16 kHz mono PCM16, maximum conversion quality and change_device_parameters=False, preserving the Mac's original 96 kHz hardware rate. It does not require emulator audio forwarding or gRPC injection. Stop, failures and lease expiry must close the physical input and discard unsaved queued content. Full app acceptance remains governed by the recorded runtime checks, not successful capture initialization alone.
