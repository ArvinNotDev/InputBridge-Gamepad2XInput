# Changelog

All notable user-facing changes to InputBridge-Gamepad2XInput are documented
here. Version numbers follow semantic-versioning conventions where practical.

## [Unreleased]

### Phone remote-control foundation

- Added a versioned, bounded request/response schema for allowlisted remote
  actions while preserving the existing gamepad and touchpad state payload.
- Added a per-installation TLS identity on the desktop and SHA-256 certificate
  pin verification on the phone. The desktop exposes the fingerprint needed
  for first-time connection setup; both clients must be updated together.
- Added PC-side permission controls. All remote-action permissions default to
  disabled; power actions additionally require confirmation on the phone.
- Added remote keyboard/text input, special keys and approved shortcuts,
  Windows media keys, explicit clipboard send/read, approved app launching,
  presentation key commands, and PC status information.
- Added bounded response frames, request IDs, server-side input validation,
  timeout/error feedback, and cleanup of held remote modifiers and controller
  state when a session ends.
- Added protocol, action-dispatch, TLS identity, and saved-fingerprint tests.
- Updated dependencies and both PyInstaller specifications for TLS and clipboard
  support.

### Scope note

Automatic discovery/reconnection, file transfer, URL sharing, screenshots/live
screen viewing, notification forwarding, automatic clipboard synchronization,
system telemetry beyond basic identity/time, and configurable custom shortcuts
remain future work; they are not represented as implemented here.

### Validation

- Test and compile commands must be run in a Python environment with the
  project's dependencies before this change is considered verified.

## [2.0.8] — 2026-09-26

### What's new

- Added per-controller DualSense and DualSense Edge Lightbar color settings,
  saved and restored using each controller's stable HID identity when available.
- Added optional battery-level colors and a charging indication for the
  Lightbar.
- Added DualSense USB and Bluetooth Lightbar output reports with Bluetooth
  sequence and CRC handling.

### Validation

- Added focused checks for USB/Bluetooth Lightbar reports, Bluetooth CRC and
  sequence handling, per-controller settings persistence, and temporary
  battery colors.

## [2.0.7] — 2026-09-17

### What's new

- Reworked HID input timing for a more responsive active-input path.
- Removed the unnecessary wait after every received HID report.
- Added adaptive idle backoff so empty HID reads do not become a busy loop or
  unnecessarily consume CPU.
- Improved mouse mode responsiveness by reducing motion smoothing latency.
- Added a fixed 10% mouse deadzone to filter tiny stick noise and accidental
  cursor movement.
- Remapped deadzone output to preserve full mouse speed after the deadzone.
- Kept time-based motion, fractional-pixel accumulation, nonlinear response,
  D-Pad movement, and controller-button mouse clicks together in one smoother
  mouse path.

### Reliability and compatibility

- Added validation coverage for mouse deadzone behavior and input timing.
- Existing `polling_rate` settings remain readable and are normalized to the
  clearer `poll_interval_ms` setting.
- Keyboard emulation remains intentionally disabled in this release.
- Renamed PyInstaller specification files from the historical
  `UniversalRemapper` name to `InputBridge-Gamepad2XInput`.

### Validation

- `python -m pytest -q` — 26 tests passed.
- `python -m compileall -q core tests ui` — passed.
- `git diff --check` — passed.

## [2.0.6] — 2026-09-01

- Fixed DualShock 4 connection stability by limiting the DualSense-only
  feature-report request to DualSense devices.
- Preserved DualSense feature reports used for additional data such as battery
  status.

## [2.0.5] — 2026-08-26

- Added live vibration settings and XInput vibration testing.

[2.0.8]: https://github.com/ArvinNotDev/InputBridge-Gamepad2XInput/releases/tag/v2.0.8
[2.0.7]: https://github.com/ArvinNotDev/InputBridge-Gamepad2XInput/releases/tag/v2.0.7
[2.0.6]: https://github.com/ArvinNotDev/InputBridge-Gamepad2XInput/releases/tag/v2.0.6
[2.0.5]: https://github.com/ArvinNotDev/InputBridge-Gamepad2XInput/releases/tag/v2.0.5
