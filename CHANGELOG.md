# Changelog

All notable user-facing changes to InputBridge-Gamepad2XInput are documented
here. Version numbers follow semantic-versioning conventions where practical.

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

[2.0.7]: https://github.com/ArvinNotDev/InputBridge-Gamepad2XInput/releases/tag/v2.0.7
[2.0.6]: https://github.com/ArvinNotDev/InputBridge-Gamepad2XInput/releases/tag/v2.0.6
[2.0.5]: https://github.com/ArvinNotDev/InputBridge-Gamepad2XInput/releases/tag/v2.0.5
