# Scam Call Alert application

This directory contains the React Native + Expo Android application and its local inference service integration. The app is being developed for the approved Android emulator workflow in [Plan 04/01](../../01%20-%20PLANs/04%20-%20APPLICATION%20DEVELOPMENT/01%20-%20MOBILE%20EMULATOR%20PROTOTYPE%20AND%20INTEGRATION.md).

The service now uses the final-trained PhayaThaiBERT model through the owner-approved `interim` adapter (2026-10-14; see Plan 03/03). It replaced the temporary WangchanBERTa bundle after a passed Mac compatibility check. It is not yet test-evaluated. The provisional context screen and owner demo choice are complete; official evaluated-model handoff, formal runtime/fidelity requirements and affected compatibility checks still govern release. This app is not frozen for Plan 05.

The owner subsequently approved a narrow provisional development screening exception in Plan 04/01 §11: run the existing 12 recordings under all three contexts once, using the recorded interim artifact and explicitly approved settings. Recording fidelity remains unverified; the screening does not authorize final context freeze, final-test access or Plan 05. Repeat affected checks if the official bundle differs. Preserve all assigned attempts and limitations.

The owner has selected bounded accumulated context for the demo from the completed provisional screen. Keep newest eligible text within the matching 510-token budget. The comparison report contains all 36 attempts (27 completed, nine infrastructure/automation failures) and a matched eight-recording comparison; no failed assignment was retried. Demo microphone and recorded functional checks are documented separately from formal evaluated-bundle release requirements.

**To start the demo, follow [RUN_DEMO.md](RUN_DEMO.md).**

## Project layout

The owner-approved interface refinement uses a restrained phone-call layout: grouped recording rows, a two-mode selector, a dark incoming-call confirmation and circular call controls. Starting either mode opens the simulated incoming screen. Decline creates no session; Accept requests the necessary permissions and starts audio. The active screen keeps live transcription, classification/failure feedback and retained warnings visible. Save is opt-in for microphone sessions. Developer settings open in a bottom sheet from the overflow (•••) button. Icons keep accessible action labels; accept/decline also retain short visible labels. No cellular-call interception is implied.

The visual reference is [Apple's button guidance](https://developer.apple.com/design/human-interface-guidelines/buttons): recognizable symbols, consistent controls and clear action hierarchy. This Android implementation uses Ionicons (bundled with `@expo/vector-icons`), not Apple system assets, and does not claim to be a native iOS Phone interface.

The owner-requested Liquid Glass-inspired call screen adds a floating transcript surface with real Android backdrop blur (`expo-blur`, shared `BlurTargetView`, API-31-plus blur method), restrained gradient highlights, a translucent rim and high-contrast transcript text. Controls use translucent surfaces; warning content retains a separate readable tint. It follows the visual idea of [Apple's materials](https://developer.apple.com/design/human-interface-guidelines/materials), while using Android rendering rather than Apple's native Liquid Glass engine. These rendering changes require fresh resource evidence before formal integration freeze.

Owner-requested GUI redesign (2026-10-14) extends this treatment to all screens and replaces non-essential text with symbols. A shared glass component (`ui/glass.tsx`) supplies the tint, top sheen and directional rim. The call screens use a quiet, near-flat charcoal-to-black backdrop with no decorative colour glows. The status pill and the red warning banner carry the result. Only the transcript panel uses live backdrop blur. Small controls and pills use the same material without blur, and the glass avoids inset shadows. Both choices follow emulator frame-time checks: blur on every control and inset glows each made frames much slower. Symbols with accessible labels now stand for the mode selector, recording rows (index, duration and an unverified mark), the connection state, playback phase, analysis delay, evidence saving and the empty-transcript placeholder. Classification, Transcribing/Analyzing state, failure messages, the scam warning and accept/decline labels remain visible text. The Background check option now uses a switch. This change is visual only: the session logic, native calls, permissions, notifications and data flow are unchanged.

Owner-approved copy trimming removes the simulated-call caption, footer disclaimer and redundant explanatory/warning sentences from the call screens. Source mode names and the recorded-call entry action identify the flow. Classification, transcript, processing/error feedback and the persistent primary scam warning remain. The project's documented Not Scam limitation still applies.

- `App.tsx` and `index.ts`: session state, permissions, native monitor calls and screen selection.
- `ui/`: presentation only. `glass.tsx` holds the shared material, buttons and backdrop. `HomeScreen.tsx`, `CallScreens.tsx` (incoming and active session) and `SettingsSheet.tsx` hold the screens.
- `modules/scam-monitor/`: local Expo Android module. Its foreground service owns recorded playback, microphone-session lifecycle, polling, background monitoring and notifications; JS timers render the screen only.
- `service/core.py`: ordered audio, STT windows/reconciliation, independent segment scheduler, coalesced classifier requests, cancellation and completion.
- `service/adapters.py`: pinned PyThaiASR plus interim and official classifier adapters; no fabricated model fallback.
- `service/server.py`: loopback HTTP transport, session-bound Mac CoreAudio capture, verified recording inventory, loading/warmup and persistent evidence.
- `service/prepare_recordings.py`: shared Plan 02 rendering, seed-67 selection, workload inspection and Kanya TTS generation; does not assert fidelity.
- `service/prepare_context_schedule.py`: validates development provenance and assigns the 36 foreground first-pass runs with cyclically rotated approach order. It neither launches runs nor approves settings. The rotation is a reproducible project convention implementing the approved plan's order control.
- `service/android_ui.py`: owner-authorized ADB/UIAutomator verification helper; saves evidence outside Git.
- `service/tests/`: isolated protocol/lifecycle/revision tests, not model-performance experiments.
- `integration_config.json`: draft diagnostic settings; not owner-confirmed experiment settings.
- `audio_manifest.csv`: twelve training-derived development recordings with source/group/checksum identities, pending human fidelity checks.
- `app.json`: app identity and Expo native configuration.
- `package.json` and `package-lock.json`: JavaScript dependencies and exact dependency resolution.
- `architecture.md`: host, emulator, app, and local-service responsibilities.
- `interface_contract.md`: agreed message/session invariants and integration fields still requiring confirmation.
- `integration_checks.md`: emulator/toolchain setup evidence and limitations.
- `assets/`: app icons and splash assets.

## Development machine setup

The current development host is the project owner's Apple Silicon MacBook Air. Node 24 LTS is installed for Expo work. Android command-line tools, Android API 36, and one Pixel 6 ARM64 virtual device are installed. See `integration_checks.md` for exact versions and the memory/storage caveats.

The backend must run on the Mac. Android Emulator requests to a service on the host must use a verified emulator-to-host address; do not assume Android's `localhost` reaches macOS. The base URL and port remain configurable and are not frozen yet.

For this Mac, put the installed Node LTS and Android SDK tools on the current shell's `PATH`:

```sh
export PATH="/opt/homebrew/opt/node@24/bin:$PATH"
export ANDROID_HOME="/opt/homebrew/share/android-commandlinetools"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export JAVA_HOME="$HOME/Library/Java/JavaVirtualMachines/temurin-21.jdk/Contents/Home"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"
```

The created AVD is named `scam-call-alert-api36`. Recheck available disk and memory before builds; 8 GiB unified memory is a real constraint.

Start it with `sh scripts/start-emulator.sh` before using the app. Live microphone audio is captured by the Mac service and sent directly to the selected STT; Android's emulator microphone forwarding is not part of the active path. Accept the macOS microphone permission prompt for the service when it appears.

## Commands

The owner approved the pinned runtime. The SDK-compatible native modules and development client are installed. Build and run the native development client with:

```sh
npm ci
npx expo prebuild --platform android --no-install
npx expo run:android --no-bundler
```

Start Metro in a separate terminal from this directory:

```sh
npm start -- --dev-client --localhost
```

Select Metro's actual localhost endpoint:

```sh
adb reverse tcp:8081 tcp:8081
adb shell am start -a android.intent.action.VIEW \
  -d 'exp+scam-call-alert://expo-development-client/?url=http%3A%2F%2Flocalhost%3A8081' \
  com.anonymous.scamcallalert
```

Expo's automatic LAN URL does not work while Metro binds localhost. The explicit launch avoids that mismatch. Expo Go cannot load the local module. Native changes require rebuilding; JS edits may refresh through Metro. The final demo build requires separate verification.

`plugins/withLocalService.js` reproduces the Android network policy during prebuild: cleartext is denied except for `10.0.2.2`, `127.0.0.1`, and `localhost`, matching the native endpoint restriction. Android backup is disabled so private microphone evidence is not included in automatic backups. This policy also applies to an embedded-JS build; that build still needs compilation and runtime verification before delivery.

### Build with embedded JavaScript

After native prebuild, from `prototype/android/` with the environment variables above:

```sh
./gradlew app:assembleRelease -x test -x lint -PreactNativeArchitectures=arm64-v8a --console=plain
adb install -r app/build/outputs/apk/release/app-release.apk
adb shell am start -n com.anonymous.scamcallalert/.MainActivity
```

This bundles JS into the APK and does not need Metro. The generated release variant uses Expo's development signing key: it is an emulator demo package, not a store-distribution release. The inference service must still run on the Mac. A successful build alone does not freeze the app or satisfy the official-model, microphone, fidelity, runtime-setting and context-selection gates. Record the APK hash with runtime evidence before claiming a delivered build.

## Start the interim-model service

From the repository root, reuse the verified STT environment pinned in `../stt/requirements-macos-arm64.lock` and cached weights:

```sh
APP_STORAGE="$HOME/Library/Application Support/scam-call-alert/application-development/prototype"
STT_STORAGE="$HOME/Library/Application Support/scam-call-alert/application-development/stt"
FINAL_MODEL="$HOME/Library/Application Support/scam-call-alert/model-development/mac-compatibility-transfer/phaya-final-replacement-primary-epoch2-20261012T050936Z/final_model"
"$STT_STORAGE/env/bin/python" "04 - APPLICATION DEVELOPMENT/prototype/service/server.py" \
  --diagnostic --model-kind interim --classifier-device cpu \
  --bundle "$FINAL_MODEL" \
  --stt-cache "$STT_STORAGE/huggingface-cache" --storage "$APP_STORAGE"
```

Wait for the JSON `ready` line. Loading and neutral warmup precede readiness. The service binds `127.0.0.1:8765`; the emulator reaches host loopback through `10.0.2.2:8765`. Formal runs require owner-confirmed settings and the official model. The interim loader reuses the final-evaluation identity checks and role-free 510-token reference path; the service keeps the most recent transcript text that fits the budget. The official evaluated bundle has a separate loader.

The 2026-10-14 owner-approved feasibility test passed, so the demo uses the classifier on CPU and STT on MPS, preserving weights and inference settings. Live acoustic verification produced a visible Thai transcript and Scam warning without overload, and recorded-mode regression processed every sample through natural completion. Boot the emulator and confirm it responds before loading both models. `/health` records actual component devices in its configuration identity. The earlier context comparison used both models on MPS; retain its original results and resource conditions. These functional checks do not establish accuracy, human-speech fidelity or formal system validation; see `integration_checks.md` for evidence and limitations.

Diagnostic mode exposes the two independent, marked synthetic fixtures. To inspect training-derived audio, add `--recordings "$APP_STORAGE/development-recordings"`. This flag alone does not approve fidelity or experiments; the 2026-10-14 owner-approved provisional screening exception supplies the specific first-pass authorization described above.

## Evidence and privacy

### Isolate host microphone and STT failures

`service/diagnose_host_microphone.py` checks the MacBook microphone independently
of Android and the classifier. Stop the app service first to avoid loading two
STT instances on the 8 GiB host. It captures only for the requested bounded
duration, keeps audio in memory, and saves no audio or transcript files. The
selected checkpoint, preprocessing and decoder are reused unchanged.

```sh
STT_STORAGE="$HOME/Library/Application Support/scam-call-alert/application-development/stt"
uv pip install --python "$STT_STORAGE/env/bin/python" sounddevice==0.5.6
"$STT_STORAGE/env/bin/python" "04 - APPLICATION DEVELOPMENT/prototype/service/diagnose_host_microphone.py" \
  --seconds 20 --stt --wait-for-start
```

Press Return only when the speaker is ready. Omit `--stt` for capture-only
measurements. Default console output contains signal levels and recognized
character counts, without speech text. `--show-text` is for an explicitly agreed
known diagnostic sentence/controlled fixture; do not use it for private speech.
The approved live path uses the same 16 kHz mono PCM16 CoreAudio settings,
without changing the host hardware sample rate. This diagnostic does not
substitute for verifying app-controlled session start, Stop, background polling
or notification behavior.

Detailed artifacts remain outside Git under `~/Library/Application Support/scam-call-alert/application-development/prototype/`:

- `recordings/`: independent synthetic diagnostic scripts/audio/manifest.
- `development-recordings/`: twelve training-derived shared-parser scripts and TTS audio, pending human fidelity verification.
- `development-recordings/selection_audit.json`: all eligible training records with selection/omission reasons, the unchanged selection order and replacement history. Reproduce this audit with `service/prepare_recordings.py --output <existing-development-recordings> --audit-only`; it validates the existing manifest and refuses to overwrite an audit.
- `runs/<session_id>/`: append-only events, accepted PCM and atomic latest snapshots for recorded sessions or explicitly saved microphone sessions.
- `ui-evidence/`: timestamped UIAutomator trees and screenshots.
- `development-context-first-pass-schedule.json`: preserved first-pass assignments, manifest identity and unresolved execution gates. Each recording receives latest/recent/accumulated once. Additional repetitions require owner nomination and a separately frozen schedule.

Microphone content remains temporary unless Save session evidence is selected. Ending an unsaved session clears it; default HTTP logging does not retain transcripts. Controlled recorded sessions preserve evidence. Build outputs/caches, audio, model weights and sample-level logs are excluded from Git.

Live microphone PCM is held temporarily in the host session and is cleared on Stop/failure unless Save session evidence was selected. No Android microphone PCM file is created in live mode. Opted-in host `runs/<session_id>/` evidence contains the accepted audio, transcript, predictions and events; unsaved sessions are not written to disk. Recorded playback and its separate evidence behavior remain unchanged.

## Checks

```sh
python3 -m unittest discover -s service/tests -v
npx tsc --noEmit
python3 service/android_ui.py --screenshot
```

Consult `integration_checks.md` before claiming a gate passed. Unit success, compilation and a diagnostic conversation do not establish full application completion or final system performance.
