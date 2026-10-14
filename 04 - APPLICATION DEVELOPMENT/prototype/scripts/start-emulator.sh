#!/bin/sh
set -eu
TASK_ANDROID_SDK="${ANDROID_HOME:-/opt/homebrew/share/android-commandlinetools}"
# Live input is captured by the local host service; Android mic forwarding and
# authenticated emulator audio injection are not part of the current runtime.
# Disable snapshots so sessions and microphone buffers cannot survive a restart.
exec "$TASK_ANDROID_SDK/emulator/emulator" -avd scam-call-alert-api36 -no-snapshot -crash-report-mode disabled
