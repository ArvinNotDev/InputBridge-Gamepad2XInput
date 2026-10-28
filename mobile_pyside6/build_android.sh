#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
qtpip download PySide6 --android --arch aarch64
PYSIDE_WHEEL="$(find . -type f -iname 'PySide6-*-android_aarch64.whl' -print -quit)"
SHIBOKEN_WHEEL="$(find . -type f -iname 'shiboken6-*-android_aarch64.whl' -print -quit)"
test -n "$PYSIDE_WHEEL" && test -n "$SHIBOKEN_WHEEL"
pyside6-android-deploy --name "InputBridge Mobile" \
  --wheel-pyside="$PYSIDE_WHEEL" \
  --wheel-shiboken="$SHIBOKEN_WHEEL" \
  --extra-modules=Network,Multimedia,MultimediaWidgets,Sensors \
  --force
