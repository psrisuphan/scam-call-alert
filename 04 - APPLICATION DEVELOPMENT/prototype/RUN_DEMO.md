# Run the demo

This guide starts the Scam Call Alert demo on the project Mac. It runs the Android emulator, the local STT and classifier service, and the app. For architecture, evidence rules and diagnostics, see [README.md](README.md).

The demo has three parts, each in its own terminal:

| Terminal | Runs | Ready when |
|---|---|---|
| 1 | Android emulator | The Android home screen appears |
| 2 | STT + classifier service on the Mac | It prints a JSON line with `"status": "ready"` |
| 3 | The app (and Metro for a development build) | The app shows its home screen |

Run every command from the repository root (the folder containing `AGENTS.md`).

## Before the first run

These are already set up on the owner's MacBook Air. Check them only on a new machine or after cleanup.

- Node 24, Android command-line tools with API 36, JDK 21 and the AVD `scam-call-alert-api36`. See `integration_checks.md` for exact versions.
- STT environment and cached weights in `~/Library/Application Support/scam-call-alert/application-development/stt/` (`env/` and `huggingface-cache/`).
- Final-trained PhayaThaiBERT model, extracted from the verified handoff archive into `~/Library/Application Support/scam-call-alert/model-development/mac-compatibility-transfer/`. Keep the folder layout: the loader checks `run_config.json` beside `final_model/`.
- Development recordings in `~/Library/Application Support/scam-call-alert/application-development/prototype/development-recordings/`.
- JavaScript dependencies: run `npm ci` once inside `04 - APPLICATION DEVELOPMENT/prototype/`.

The Mac has 8 GB of memory. Close heavy apps (browsers, IDEs) before starting. Never run two STT services at once.

## Environment for every terminal

Paste this into each new terminal first:

```sh
export PATH="/opt/homebrew/opt/node@24/bin:$PATH"
export ANDROID_HOME="/opt/homebrew/share/android-commandlinetools"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export JAVA_HOME="$HOME/Library/Java/JavaVirtualMachines/temurin-21.jdk/Contents/Home"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"
export APP_STORAGE="$HOME/Library/Application Support/scam-call-alert/application-development/prototype"
export STT_STORAGE="$HOME/Library/Application Support/scam-call-alert/application-development/stt"
export FINAL_MODEL="$HOME/Library/Application Support/scam-call-alert/model-development/mac-compatibility-transfer/phaya-final-replacement-primary-epoch2-20261012T050936Z/final_model"
```

## Prepare the standalone app before starting the models

On a fresh clone, `android/` and APKs are absent because generated projects and builds are ignored. Generate and build them before loading STT/classifier weights. Repeat the build after application/native changes; skip it when the installed APK is already current.

```sh
cd "04 - APPLICATION DEVELOPMENT/prototype"
npm ci
npx expo prebuild --platform android --no-install
cd android
./gradlew app:assembleRelease -x test -x lint -PreactNativeArchitectures=arm64-v8a --console=plain
./gradlew --stop
```

Return to the repository root before the launch steps below. Do not build while both models are running on the 8 GB Mac. Prebuild uses the tracked Expo configuration/plugin and local native module; it does not require committing generated `android/` files.

## 1. Start the emulator (terminal 1)

```sh
sh "04 - APPLICATION DEVELOPMENT/prototype/scripts/start-emulator.sh"
```

Leave it running. Booting takes one to two minutes. Snapshots are disabled, so each start is a cold boot. To check from another terminal:

```sh
adb shell getprop sys.boot_completed
```

It prints `1` when Android is ready.

## 2. Start the STT and classifier service (terminal 2)

```sh
"$STT_STORAGE/env/bin/python" "04 - APPLICATION DEVELOPMENT/prototype/service/server.py" \
  --diagnostic --model-kind interim --classifier-device cpu \
  --bundle "$FINAL_MODEL" \
  --stt-cache "$STT_STORAGE/huggingface-cache" --storage "$APP_STORAGE" \
  --recordings "$APP_STORAGE/development-recordings"
```

Wait for a line like `{"status": "ready", "port": 8765, ...}`. Load time varies with memory pressure; a warning alone is not readiness. The owner-approved demo split is CPU classifier / MPS STT. Start the emulator before loading the models; this split passed live-microphone and recorded short-tail functional checks.

- The service listens on `127.0.0.1:8765`. The emulator reaches it at `http://10.0.2.2:8765`, which the app uses by default.
- `--recordings` lists the twelve development recordings in the app. Leave it out to see only the two synthetic diagnostic fixtures.
- macOS microphone permission applies to the host capture process shown by the permission prompt (Python or its launching application). Allow that process; Android microphone forwarding is not used.
- This uses the final-trained PhayaThaiBERT model as an owner-approved interim model. It has not been evaluated on the held-out test set, so treat results as demo output, not formal evidence.

Check it from another terminal:

```sh
curl -s http://127.0.0.1:8765/health | head -c 200
```

## 3. Open the app (terminal 3)

Pick one option.

### Option A: standalone demo build (recommended for presenting)

The JavaScript is embedded in the APK, so Metro is not needed. Use the APK prepared above; an older APK shows the older interface.

```sh
cd "04 - APPLICATION DEVELOPMENT/prototype/android"
adb install -r app/build/outputs/apk/release/app-release.apk
adb shell am start -n com.anonymous.scamcallalert/.MainActivity
```

Stop Gradle daemons after builds to release their memory. If `adb install` reports a signature mismatch, review whether the existing app's data is needed before uninstalling it; uninstalling removes its on-device data.

### Option B: development build with live reload (for UI work)

Code changes appear on the emulator as soon as you save. Start Metro and leave it running:

```sh
cd "04 - APPLICATION DEVELOPMENT/prototype"
npm start -- --dev-client --localhost
```

In a fourth terminal, install the debug build once, then connect the app to Metro:

```sh
adb install -r "04 - APPLICATION DEVELOPMENT/prototype/android/app/build/outputs/apk/debug/app-debug.apk"
adb reverse tcp:8081 tcp:8081
adb shell am start -a android.intent.action.VIEW \
  -d 'exp+scam-call-alert://expo-development-client/?url=http%3A%2F%2Flocalhost%3A8081' \
  com.anonymous.scamcallalert
```

Prepare a fresh debug APK with `./gradlew app:assembleDebug -PreactNativeArchitectures=arm64-v8a` (inside `android/`) before starting the models and after native changes; stop Gradle daemons afterward. The first bundle load can show a blank screen while Metro bundles. The floating "Tools" button is Expo's developer menu, not part of the app.

## 4. Use the app

1. **Home.** A red cloud icon at the top left means the service is unreachable; tap it to retry once the service is ready. The ••• button opens developer settings (service URL, context approach, Background check).
2. **Pick a mode.** The play icon plays a prepared recording. The microphone icon listens through the Mac microphone.
3. **Recorded mode.** Choose a recording by number; the time is its length. The orange mark means its fidelity check is still pending.
4. **Start.** Tap the green call button, then **ตอบรับ** (accept) on the incoming-call screen. **ปฏิเสธ** (decline) cancels without creating a session. Allow notifications when Android asks, so the scam alert can appear as a system notification.
5. **During the call.** The transcript fills the glass panel. The pill shows กำลังถอดเสียง / กำลังวิเคราะห์ while processing, then **Scam** or **Not Scam**. The red banner **ระวัง! สายนี้อาจเป็นมิจฉาชีพ** appears on the first Scam result and stays for the session, and a system notification is posted once.
6. **Controls.** Pause/play controls recorded playback. The tray icon saves evidence for a microphone session; recorded sessions always save. The red button ends the session. After it ends, the close button returns to home.

Not Scam does not guarantee that a call is safe.

## 5. Shut down

1. End any active session in the app.
2. Press `Ctrl+C` in the service and Metro terminals.
3. Close the emulator window, or run `adb emu kill`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Red cloud icon stays on home | Wait for the service `ready` line, then tap the icon. Check `curl http://127.0.0.1:8765/health`. Under ••• the URL must be `http://10.0.2.2:8765`. |
| "App isn't responding" or very slow frames | Memory pressure contributed to observed emulator freezes, but an ANR alone does not prove the cause. End active capture, stop model services, close heavy apps and recover the same AVD before reloading models. Avoid building while the service runs. |
| App shows the old interface | You are running an older APK. Rebuild (Option A) or use Option B. |
| Blank white screen in Option B | Metro is still bundling; wait. If it stays blank, rerun `adb reverse tcp:8081 tcp:8081` and the `am start` command. |
| Microphone transcript stays empty | Allow the host capture process in macOS System Settings → Privacy & Security → Microphone. Check `/health` for signal, processed samples and errors; empty text can also indicate STT backlog. |
| `adb: no devices` | The emulator is still booting. Wait for `sys.boot_completed` to print `1`. |
| No scam notification | Android notifications were denied for the app. Enable them in Android Settings → Apps → Scam Call Alert → Notifications. The in-app banner still appears. |
