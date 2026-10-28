# InputBridge Mobile — PySide6 (recommended)

This is the current Android companion client. The previous Kivy implementation is retained separately under `mobile_kivy_legacy/`.

## Install without building locally

1. Download **[InputBridge Mobile — latest APK](https://github.com/ArvinNotDev/InputBridge-Gamepad2XInput/releases/tag/mobile-latest)**.
2. Install `InputBridge-Mobile-Android-arm64.apk` on an ARM64 Android device. Approve the Android “install unknown apps” prompt for the app you use to open the APK, if Android shows it.
3. Update and start the InputBridge desktop app on Windows, open **Server**, start the server, and choose **Show Phone Pairing QR**.
4. On your phone, open **Connect → Scan pairing QR** and approve camera access. The phone verifies the QR's SHA-256 TLS fingerprint before sending controller state.
5. Enter the per-device pairing code shown by the desktop app on first connection. Then use **Gamepad**, **Mouse**, or **Remote**.

Every successful Android workflow run publishes a replacement APK to the rolling `mobile-latest` prerelease. The workflow also retains a downloadable artifact for 14 days. You do not need to install the Android build toolchain locally.

The build downloads the official Qt for Python Android ARM64 wheels for the same pinned Qt/PySide6 version used by the host deployment tool. It does not rebuild CPython or the host Shiboken generator from source; this avoids the unrelated Android `_ctypes/libffi` and host LLVM/Clang generator failures seen in the previous workflow.

## Included screens and features

- Secure connection with TLS certificate pinning, retry handling, saved PC endpoint, and persistent phone identity.
- On-screen gamepad with face buttons, bumpers, menu/system buttons, D-pad, dual analogue sticks, analogue L2/R2 triggers, Standard/Driving modes, and optional accelerometer steering with centre calibration.
- Mouse trackpad with relative cursor movement, tap-to-click, left/right/middle buttons, one-finger movement, two-finger scrolling, and sensitivity settings.
- Remote PC text entry, special keys, modifiers, allowlisted keyboard shortcuts, media keys, explicit clipboard read/write, approved app launch shortcuts, presentation controls, PC status, and confirmation-gated power actions.
- Phone-side controls are enabled only when the desktop server reports that the corresponding permission is allowed. Power actions remain gated by the desktop setting and phone confirmation.
- Camera QR scan with Android runtime permission handling and a manual JSON/clipboard fallback.
- Responsive dark Qt Widgets interface designed for touch use.

## Security and compatibility

- The desktop server and mobile client must both be updated to the current TLS protocol.
- The QR supplies the server address and public SHA-256 certificate fingerprint. It never exports the private TLS key.
- Remote actions require explicit permission on the Windows desktop. Only approved app shortcuts and keyboard shortcuts are accepted by the server.
- The Android workflow currently targets **ARM64 (arm64-v8a)**.
- Camera and motion-sensor availability depends on the physical device and Android permissions.

## Run the source on desktop for development

Install the dependencies and launch the same Qt Widgets client:

```bash
python -m pip install -r requirements.txt
python main.py
```

An Android APK still has to bundle Qt/Python and declare platform permissions. This repository's GitHub Actions workflow creates that APK for you; no local Android build is required.
