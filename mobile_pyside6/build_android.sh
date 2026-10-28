#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt qtpip
qtpip download PySide6==6.12.0 --android --arch aarch64
PYSIDE_WHEEL="$(find . -type f -iname 'PySide6-*-android_aarch64.whl' -print -quit)"
SHIBOKEN_WHEEL="$(find . -type f -iname 'shiboken6-*-android_aarch64.whl' -print -quit)"
test -n "$PYSIDE_WHEEL" && test -n "$SHIBOKEN_WHEEL"
python deploy_android.py "$PYSIDE_WHEEL" "$SHIBOKEN_WHEEL"
