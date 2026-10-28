#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt aqtinstall
QT_ROOT="\${QT_ROOT:-$HOME/Qt}"
NDK_ROOT="\${ANDROID_NDK_ROOT:-$HOME/.pyside6_android_deploy/android-ndk}"
SDK_ROOT="\${ANDROID_SDK_ROOT:-$HOME/.pyside6_android_deploy/android-sdk}"
aqt install-qt linux desktop 6.12.0 gcc_64 -O "$QT_ROOT" -m qtmultimedia qtsensors
aqt install-qt linux android 6.12.0 android_arm64_v8a -O "$QT_ROOT" -m qtmultimedia qtsensors
git clone --depth 1 --branch 6.12 https://code.qt.io/pyside/pyside-setup.git "$HOME/pyside-setup-6.12"
cd "$HOME/pyside-setup-6.12"
python -m pip install -r requirements.txt -r tools/cross_compile_android/requirements.txt
python tools/cross_compile_android/main.py --plat-name aarch64 --download-only --skip-update --auto-accept-license
python tools/cross_compile_android/main.py \
  --plat-name aarch64 \
  --qt-install-path "$QT_ROOT/6.12.0" \
  --ndk-path "$NDK_ROOT" \
  --sdk-path "$SDK_ROOT" \
  --skip-update --auto-accept-license
PYSIDE_WHEEL="$(find "$HOME/pyside-setup-6.12/dist_android" -type f -iname 'PySide6-*-android_aarch64.whl' -print -quit)"
SHIBOKEN_WHEEL="$(find "$HOME/pyside-setup-6.12/dist_android" -type f -iname 'shiboken6-*-android_aarch64.whl' -print -quit)"
test -n "$PYSIDE_WHEEL" && test -n "$SHIBOKEN_WHEEL"
cd "$(dirname "$0")"
python deploy_android.py "$PYSIDE_WHEEL" "$SHIBOKEN_WHEEL"
