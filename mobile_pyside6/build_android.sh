#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
QT_VERSION="6.11.0"
QT_ROOT="$HOME/Qt"
PYSIDE_SETUP_DIR="$HOME/pyside-setup-6.11"
WHEEL_DIR="$HOME/.cache/inputbridge-android-wheels/$QT_VERSION"

cd "$PROJECT_DIR"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt aqtinstall

# Keep the host Qt SDK, Android Qt SDK, and the downloaded Python wheels on
# the same Qt for Python patch version.
aqt install-qt linux desktop "$QT_VERSION" linux_gcc_64 -O "$QT_ROOT" -m qtmultimedia qtsensors
aqt install-qt linux android "$QT_VERSION" android_arm64_v8a -O "$QT_ROOT" -m qtmultimedia qtsensors

# This script is used only to obtain the Android SDK/NDK. Do not invoke its
# wheel cross-compilation path: Qt publishes matching ARM64 Android wheels.
if [ ! -d "$PYSIDE_SETUP_DIR/.git" ]; then
  git clone --depth 1 --branch 6.11 https://code.qt.io/pyside/pyside-setup.git "$PYSIDE_SETUP_DIR"
else
  git -C "$PYSIDE_SETUP_DIR" fetch --depth 1 origin 6.11
  git -C "$PYSIDE_SETUP_DIR" checkout -B 6.11 FETCH_HEAD
fi
cd "$PYSIDE_SETUP_DIR"
python -m pip install -r requirements.txt -r tools/cross_compile_android/requirements.txt
python tools/cross_compile_android/main.py --plat-name aarch64 --download-only --skip-update --auto-accept-license

NDK_ROOT="$(find "$HOME/.pyside6_android_deploy/android-ndk" -mindepth 1 -maxdepth 1 -type d -name 'android-ndk-r*' -print -quit)"
SDK_ROOT="$HOME/.pyside6_android_deploy/android-sdk"
test -n "$NDK_ROOT" && test -d "$SDK_ROOT"

# Use the official Qt for Python wheels. The CPython _ctypes/libffi and
# host Clang/Shiboken generator source builds are intentionally avoided.
mkdir -p "$WHEEL_DIR"
PYSIDE_WHEEL="$WHEEL_DIR/pyside6-$QT_VERSION-$QT_VERSION-cp311-cp311-android_aarch64.whl"
SHIBOKEN_WHEEL="$WHEEL_DIR/shiboken6-$QT_VERSION-$QT_VERSION-cp311-cp311-android_aarch64.whl"
curl --fail --location --show-error --retry 4 --retry-all-errors --connect-timeout 30 \
  "https://download.qt.io/official_releases/QtForPython/pyside6/$(basename "$PYSIDE_WHEEL")" \
  --output "$PYSIDE_WHEEL"
curl --fail --location --show-error --retry 4 --retry-all-errors --connect-timeout 30 \
  "https://download.qt.io/official_releases/QtForPython/shiboken6/$(basename "$SHIBOKEN_WHEEL")" \
  --output "$SHIBOKEN_WHEEL"
python -m zipfile -t "$PYSIDE_WHEEL"
python -m zipfile -t "$SHIBOKEN_WHEEL"
sha256sum "$PYSIDE_WHEEL" "$SHIBOKEN_WHEEL"

cd "$PROJECT_DIR"
python deploy_android.py "$PYSIDE_WHEEL" "$SHIBOKEN_WHEEL"
