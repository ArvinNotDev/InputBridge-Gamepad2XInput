# Changelog

All notable user-facing changes to VPadConnect are documented
here. Version numbers follow semantic-versioning conventions where practical.

## [0.2.1-beta.1] — 2026-10-29

This is the first pre-1.0 beta under the VPadConnect version line. It gathers the
current desktop and Web Companion work into a fresh downloadable Windows release.

### Raw HID live terminal and developer diagnostics

- Added a dedicated dark live terminal for timestamped hexadecimal HID reports,
  with packet count, receive rate, last-report size, and controller name.
- Added pause/resume, clear, copy-latest, save-capture, and optional auto-scroll
  controls. Terminal history is bounded to 1,600 lines.
- Limited UI report delivery to 30 updates per second and disabled delivery while
  the terminal is hidden, avoiding unnecessary pressure on the UI thread.
- Kept file diagnostics separate, rate-limited, and rotated to bound disk usage.

### Settings and input responsiveness

- Made Device, UI, and Developer Settings scroll independently in compact windows.
- Added a persistent Reduce interface animations option and an adjustable mouse
  deadzone for physical-controller mouse mode.
- Removed the redundant OS cursor-position query before every relative mouse move,
  while retaining recovery from PyAutoGUI's fail-safe corner.
- Added visible developer logging controls for choosing, opening, and clearing
  diagnostic logs.

### Web Companion and desktop experience

- Improved the mobile Web Companion's touch gamepad, touch mouse, scrolling,
  PC Remote, connection handling, and browser-local preferences.
- Kept the input stream persistent over an authenticated WebSocket when available,
  with an HTTP state fallback and cleanup of held inputs on disconnect.
- Added the current indigo/cyan desktop motion polish and reduced-motion support.
- Gated virtual XInput output on the optional ViGEmBus driver while keeping
  touch mouse and PC Remote features available without it.

### Distribution and validation

- Reset the application version line to `0.2.1-beta.1` to mark the VPadConnect
  beta as a pre-1.0 release.
- The release workflow builds a Windows x64 **one-file** `VPadConnect.exe`,
  runs automated tests before publishing, and attaches a SHA-256 checksum file.
- This is a beta: automated checks do not replace testing on every Windows PC
  and with every physical controller. Please report reproducible issues.

## [Unreleased]

### PySide6 desktop motion polish

- Added short slide-and-crossfade transitions between the main desktop pages and the
  Device/UI/Developer sections in Settings.
- Added a smoothly moving indigo-to-cyan active-tab indicator and subtle animated
  hover glow for buttons in the desktop interface.
- Added a reduced-motion override via `VPADCONNECT_REDUCED_MOTION=1`.



### Web Companion motion polish

- Added smooth animated transitions when switching tabs and entering content panels,
  plus subtle press, hover, focus, and mode-selection feedback across interactive controls.
- Added lightweight staggered entrances for remote-action and Settings cards, with a
  reduced-motion mode for users who prefer minimal animation.


### Mobile Settings and touchpad scrolling

- Added a dedicated mobile Settings tab with pointer sensitivity, scroll sensitivity,
  reverse touchpad scrolling, tap-to-click, gyro sensitivity, Xbox/PlayStation layout
  selection, optional haptic feedback, screen wake lock, and a restore-defaults action.
- Added browser-local persistence for the new preferences. Reversed scrolling affects
  both two-finger touchpad gestures and mouse-wheel events; explicit Scroll Up/Down
  buttons remain literal and keep their displayed direction.


### Mobile controller and desktop UI refinements

- Replaced per-move HTTPS requests and the 1.8-second application heartbeat
  with one authenticated persistent WebSocket per browser. Input snapshots travel
  over the open connection without waiting for an HTTP response after every move;
  disconnect cleanup releases held controls.
- Replaced custom layout editing with native-style Xbox and PlayStation controller
  layouts. A single selector switches face-button symbols, shoulder/trigger labels,
  and the controller's visual arrangement, with the selection saved per browser.
- Corrected the horizontal gyro-steering direction in landscape and kept the
  driving calibration and sensitivity controls accessible next to the layout selector.
- Added richer coordinated gradients to both PySide6 themes and updated the
  README with current controller and driving instructions.


### VPadConnect branding

- Rebranded the application and Windows executable as VPadConnect while
  retaining the existing `.ibprofile` portable profile format for compatibility.
- Added vector logo and social-preview artwork using the indigo-and-cyan visual identity.

### Web Companion and desktop integration
### Web Companion desktop refresh

- Combined Web Companion into the primary feature navigation and removed the old
  native remote-controller page from the desktop shell.
- Added a compact Apple-inspired frameless title bar, app/tray icon, horizontal
  Settings sections, and profile/settings shortcuts in the header.
- Moved Web Companion startup and shutdown to a worker thread and fixed its
  listener to HTTPS port 8765. The app can request a private-network Windows
  Firewall rule to make browser connections available over the LAN.
- Simplified pairing UI, disabled pairing controls until startup completes, and
  added a scrollable list of connected browsers.


- Improved the browser gamepad layout for portrait and landscape screens,
  including a full-screen Gamepad Focus mode and touch-safe scrolling.
- Added pointer-cancellation and connection-loss cleanup so touch controls are
  released when input ends unexpectedly.
- Kept browser controllers independent, with per-browser virtual gamepads and
  serialized input and cleanup for each session.
- Added quick keyboard navigation controls and persistent browser preferences
  for the device name, gamepad mode, and touch-control settings. Session tokens
  remain scoped to the browser tab.
- Removed the separate Kivy and mobile PySide6 clients and their mobile-only
  build files. The Windows PySide6 desktop application remains supported.

### Remote-control foundation

- Added a versioned, bounded request/response schema for allowlisted remote
  actions while preserving the existing gamepad and touchpad state payload.
- Added a per-installation TLS identity on the desktop and a browser pairing
  flow that displays and checks the expected SHA-256 certificate fingerprint.
  Browser JavaScript cannot independently pin the TLS certificate; users must
  compare the certificate details with the desktop value before accepting a
  self-signed certificate warning.
- Added PC-side permission controls in Web Companion. Remote-action permissions
  are enabled by default and can be changed at any time; power actions still require
  confirmation in the browser.
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

- `python -m pytest -q` — 75 passed with no warnings.
- Both PyInstaller specifications completed on Windows 11 with Python 3.12.
  The built executables were not launched, and no controller hardware was
  tested. 

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
  historical `UniversalRemapper` name to `VPadConnect` during an earlier release.

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

[0.2.1-beta.1]: https://github.com/ArvinNotDev/VPadConnect/releases/tag/v0.2.1-beta.1
[2.0.8]: https://github.com/ArvinNotDev/VPadConnect/tree/v2.0.8
[2.0.7]: https://github.com/ArvinNotDev/VPadConnect/tree/v2.0.7
[2.0.6]: https://github.com/ArvinNotDev/VPadConnect/tree/v2.0.6
[2.0.5]: https://github.com/ArvinNotDev/VPadConnect/tree/v2.0.5
