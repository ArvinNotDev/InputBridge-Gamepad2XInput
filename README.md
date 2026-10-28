# VPadConnect

<p align="center">
  <img src="ui/assets/vpadconnect-icon.png" alt="VPadConnect application icon" width="88">
</p>

<p align="center">
  <img src="docs/branding/vpadconnect-logo.svg" alt="VPadConnect — Virtual Gamepad. Connected Control." width="700">
</p>

<p align="center">
  <strong>Virtual Gamepad. Connected Control.</strong><br>
  Virtual XInput gamepad emulation and remote PC control for Windows.
</p>

<p align="center">
  <a href="https://github.com/ArvinNotDev/VPadConnect/releases/latest">
    <img src="https://img.shields.io/github/v/release/ArvinNotDev/VPadConnect?style=flat-square&color=635bff" alt="Latest release">
  </a>
  <a href="https://github.com/ArvinNotDev/VPadConnect/releases">
    <img src="https://img.shields.io/github/downloads/ArvinNotDev/VPadConnect/total?style=flat-square&color=20b8d4" alt="Downloads">
  </a>
  <img src="https://img.shields.io/badge/platform-Windows-0078D4?style=flat-square" alt="Windows">
  <img src="https://img.shields.io/badge/PySide6-Qt%206-41CD52?style=flat-square" alt="PySide6">
  <img src="https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/license-Unlicensed-lightgrey?style=flat-square" alt="License">
</p>

---
## Overview

**VPadConnect** is a Windows desktop application for remapping physical HID controllers to virtual **Xbox 360 / XInput** devices and responsive mouse controls.

It provides a graphical interface for configuring controller mappings without modifying source code. Profiles, hotkeys, analog settings, mouse emulation, and remote gamepad support are managed directly from the application.

The project is built with **PySide6** and packaged for Windows using **PyInstaller**.

The latest release includes a self-contained Windows `.exe`, so Python is **not required** to run the packaged application. For source setup and build instructions, see [Build From Source](#build-from-source).

> **Current release: v2.0.8** — per-controller DualSense Lightbar colors,
> optional battery and charging indications, and USB/Bluetooth output support.
> See the full [changelog](CHANGELOG.md)
> and the [latest release](https://github.com/ArvinNotDev/VPadConnect/releases/latest).

## Features

* HID controller discovery and live device monitoring
* Virtual Xbox 360 controller emulation through `vgamepad`
* XInput-compatible controller output
* Controller hotkeys, media keys, and custom commands
* Configurable controller profiles
* Profile-based input configuration
* D-Pad and analog-stick mouse control
* Low-latency, time-based mouse motion with fractional-pixel accumulation
* Fixed 10% mouse deadzone to filter stick noise and accidental cursor drift
* Adjustable mouse sensitivity with nonlinear fine-control response
* Configurable gamepad deadzones and axis inversion
* Browser touch mouse with cursor movement, left/right/middle buttons, and scrolling
* Browser keyboard input with text, editing, navigation, and special-key events
* Per-session choice between XInput gamepad output and direct Windows mouse output
* Responsive HTTPS browser companion with touch gamepad, touch mouse, remote keyboard, media, clipboard, launch shortcuts, presentation and permission-gated power controls
* Independent browser gamepad sessions, so multiple phones/tablets can create separate virtual XInput devices
* System-tray integration
* Dark and light themes
* Persistent application settings
* Per-controller DualSense Lightbar colors with optional battery and charging indication
* Automatic settings save with per-section reset controls
* English, فارسی, and Español UI languages
* Portable profile export/import (`.ibprofile`) with avatar support
* In-app About page with developer and project links
* Portable/self-contained Windows executable
* Separate writable user configuration from bundled application resources

The physical-controller-to-keyboard mapping target remains reserved for future
work. This is separate from **browser-to-PC remote keyboard input**, which is
available through the Web Companion's PC Remote tab after the PC user enables
the relevant permission.

## Download

Download the latest version from the [Releases](https://github.com/ArvinNotDev/VPadConnect/releases) page.

For most users, download:

```text
VPadConnect.exe
```

The packaged application is intended to run directly on Windows without requiring a Python installation.

Place the executable in a writable directory and launch it. On first run, VPadConnect creates its required user configuration files automatically.

## System Requirements

### Operating System

* Windows 10 or later
* Windows x64

### For virtual Xbox / XInput emulation

Xbox 360 controller emulation requires the system-level **ViGEmBus** driver.

The packaged application includes the required:

```text
ViGEmClient.dll
```

However, the **ViGEmBus driver itself may need to be installed separately**, especially on a clean Windows installation.

### For mouse control and hotkeys

If you only use mouse mode or controller hotkeys, the virtual gamepad driver is
not required. Direct physical-controller-to-keyboard mapping is not enabled;
browser remote-keyboard input is a separate feature and requires its PC
permission.

## Quick Start

1. Download `VPadConnect.exe` from the latest [Release](https://github.com/ArvinNotDev/VPadConnect/releases).
2. Install **ViGEmBus** if you want virtual Xbox 360 / XInput emulation.
3. Connect your physical controller.
4. Launch **VPadConnect**.
5. Open **Controller Emulation**.
6. Click **Add Controller**.
7. Select the HID controller interface you want to use.
8. Select the target emulation mode.
9. Configure mappings, profiles, hotkeys, mouse mode, and sensitivity as needed.
10. Start the emulation.

Once configured, the physical controller can be translated into a virtual XInput controller, mouse movement, or hotkey actions.

## Controller Mapping

VPadConnect separates the physical input device from the virtual output device.

A typical configuration looks like:

```text
Physical HID Controller
        │
        ▼
VPadConnect
        │
        ├──► Virtual Xbox 360 / XInput Controller
        │
        ├──► Controller Hotkeys
        │
        └──► Mouse Input
```

This allows the same physical controller to be configured for different games and applications through profiles.

## Profiles

Controller profiles allow you to maintain different mappings for different games, applications, or use cases.

A profile can define:

* Button mappings
* Analog-stick behavior
* D-Pad mappings
* Axis inversion
* Deadzones
* Mouse behavior
* Hotkeys
* Other controller-specific configuration

Profiles are stored separately from the application binaries so they can be modified without rebuilding the application.

Profiles can be exported as portable `.ibprofile` files. An exported profile
contains its settings snapshot and optional avatar image, making it easy to
back up configurations or move them to another installation. JSON profile files
from older versions can also be imported.

Application settings are saved automatically after changes. Each Settings
section also includes a Reset control for quickly returning that section to
its defaults.

## Languages

The interface is available in English, فارسی, and Español. Change the language
from **Settings → UI**; the layout direction remains unchanged for a familiar
desktop experience.

## Mouse Mode

VPadConnect can use controller inputs as mouse controls.

Supported functionality includes:

* Analog-stick mouse movement
* D-Pad mouse control
* Adjustable sensitivity
* A fixed 10% center deadzone that removes small stick noise while preserving
  the full-speed range
* Time-based smoothing that stays consistent across HID report rates
* Fractional-pixel accumulation so slow movement does not stall
* Nonlinear response for precise small movements and fast travel at larger
  stick deflections
* Axis inversion

Mouse mode is designed for responsive desktop control. The cursor path avoids
an unnecessary delay after active HID reports, while a short adaptive idle wait
keeps CPU usage controlled when no input is arriving.

## Input timing

Settings names the timing control **Input poll interval (ms)**. It is an idle
polling interval, not a polling rate in Hz. The default is `1 ms`; values below
`1 ms` are clamped to `1 ms` to avoid a CPU-heavy busy loop. Existing settings
using the old `polling_rate` key are read automatically and normalized to
`poll_interval_ms` when saved.

This can be useful for desktop navigation, media-center systems, remote-control setups, and games that do not provide adequate controller support.

## Hotkeys

Custom controller hotkeys can be configured to trigger actions from controller input combinations.

Hotkeys can be used independently of standard controller mappings and are stored in the application's persistent configuration.

## Browser Web Companion

Use the desktop app's **Web Companion** tab to control the PC from a phone,
tablet, or another computer. It serves the touch-friendly interface over HTTPS;
no native mobile app is required.

1. Start VPadConnect on Windows, open **Web Companion**, and choose **Start Web Server**.
2. Open the displayed HTTPS URL or scan the QR code. Both devices must be on the
   same Wi-Fi/LAN; use the PC's displayed address on port **8765**.
3. The QR opens the browser at the Web Companion URL and carries the short-lived
   pairing code and certificate fingerprint in the URL fragment. The page fills
   the code automatically. If entering the URL manually, enter the code shown on
   the desktop and compare the displayed SHA-256 fingerprint before pairing.
4. Use **Gamepad**, **Touch mouse**, and **PC Remote**. The PC user controls
   keyboard, media, clipboard, app launch, presentation, and power permissions
   from the desktop.

The Gamepad tab supports portrait and landscape layouts and has a full-screen
**Gamepad Focus** mode with an **Edit layout** control. Drag the sticks, D-pad,
face buttons, and control groups to arrange them, or choose Classic, Racing,
Left-handed, or Compact presets. Layout changes persist in that browser.
Controller input uses one authenticated WebSocket per browser. Changed states are
sent at the browser's animation-frame cadence over that persistent connection, so
joystick movement does not wait for an HTTP response after every update. The normal
WebSocket path sends no periodic application-level HTTP heartbeat; an HTTP state
fallback remains available if WebSockets cannot connect.
Browser preferences are saved for that browser origin;
the pairing token stays in per-tab session storage. Each paired browser gets an
independent virtual controller. The server allows up to eight active browser
sessions; pairing codes expire after five minutes, and inactive sessions release
their inputs automatically.

The QR carries a public certificate fingerprint, never the private TLS key.
Browsers may first show a self-signed certificate warning. Before proceeding,
inspect the certificate details in the browser and compare its SHA-256
fingerprint with the value shown on the desktop. Browser JavaScript cannot
independently pin the TLS certificate, so do not bypass a warning when the
fingerprints do not match or cannot be checked. Use the Web Companion only on a
trusted network.

### Native-client parity checklist

| Native-client workflow or preference | Web Companion status and Phase 4 decision |
| --- | --- |
| Scan a pairing QR inside the app | The desktop QR is a browser URL with the pairing code and TLS fingerprint in its fragment. A phone's built-in QR scanner opens that URL and the browser pre-fills the code. No separate camera scanner is needed; users can also enter the code manually. |
| Device name | Available in the pairing form. Phase 4 persists the name in browser preferences so it is ready for later pairings. |
| Stable native device ID | Not carried over. The server assigns a separate session identity and token to each paired browser, which fits independent browser controllers. |
| Saved host, port, and certificate pin | The opened browser origin identifies the Web Companion host and port. The QR supplies the expected fingerprint; manual pairing asks the user to compare the desktop fingerprint. Separate native endpoint fields and pin storage are unnecessary for this workflow. |
| Gamepad mode and tilt steering | Standard/Driving modes, tilt enablement, and centre calibration are present. Phase 4 adds adjustable steering sensitivity and persists the mode and sensitivity. Tilt permission and calibration remain session-specific. |
| Pointer sensitivity and tap-to-click | Already adjustable in the browser. Phase 4 persists both settings. |
| Keyboard, media, clipboard, app shortcuts, presentation, PC status, and power | Available in PC Remote and governed by desktop-side permissions. Power actions that can disrupt the PC require confirmation in the browser. |

The useful native control preferences are now browser preferences stored by the
browser origin. Pairing tokens remain in per-tab session storage. The web
interface does not implement file transfer, live screen viewing, notification
forwarding, or LAN discovery. The current desktop remote protocol does not
expose those workflows for the browser to migrate.

### Supported remote actions

- Remote text, common keys, modifiers, and allowlisted keyboard shortcuts.
- Media keys for volume, mute, playback, and track controls.
- Explicit clipboard read/write; background clipboard synchronization is not
  implemented.
- Approved app shortcuts only; arbitrary shell commands are not accepted.
- Presentation controls, PC status, and permission-gated power actions.
- A desktop permission panel for remote actions. Permissions are enabled by default and can be changed from Web Companion settings.

## Configuration Files

User-writable configuration files are stored beside the executable.

Typical files include:

```text
config/
└── settings.conf

hotkeys.json
trusted_clients.json
```

Bundled application resources include:

```text
profiles/
ui/
├── themes/
└── assets/
    └── tray.png
```

The application keeps user-writable data separate from bundled resources. This allows the same path handling to work correctly in both source execution and PyInstaller builds.

> **Note:** The exact runtime files may vary depending on the current application configuration and installed features.

## Portable Usage

The packaged executable is designed to be portable.

You can place:

```text
VPadConnect.exe
```

in a writable directory and launch it directly.

For reliable persistence, avoid protected directories such as:

```text
C:\Program Files\
```

unless the application has the required write permissions.

## Build From Source

### Clone the repository

```powershell
git clone https://github.com/ArvinNotDev/VPadConnect.git
cd VPadConnect
```

### Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On Python 3.15, `requirements.txt` selects the official Qt for Python development
build of PySide6 because the latest stable PySide6 release does not yet declare
support for Python 3.15. This is a pre-release build, and Python 3.15 compatibility
is not guaranteed until Qt publishes its planned stable support in PySide6 6.12.1
or later. Use Python 3.14 for a fully stable PySide6 dependency in the meantime.

### Run from source

```powershell
python main.py
```

### Build the recommended onedir package

```powershell
python -m PyInstaller --clean --noconfirm VPadConnect.spec
```

Output:

```text
dist/
└── VPadConnect/
    └── VPadConnect.exe
```

The **onedir** build is generally recommended for development and distribution when fast startup and easier troubleshooting are preferred.

### Build the single-file executable

```powershell
python -m PyInstaller --clean --noconfirm `
  --distpath dist\onefile `
  --workpath build\VPadConnect_onefile `
  VPadConnect_onefile.spec
```

Output:

```text
dist/
└── onefile/
    └── VPadConnect.exe
```

The **onefile** build packages the application into a single executable and is more convenient for end users.

## Project Structure

```text
.
├── core/                                  # HID, mappings, emulation, settings, utilities
├── ui/                                    # PySide6 windows, pages, themes, and assets
├── profiles/                              # Controller profile definitions
├── config/                                # Default application configuration
├── main.py                                # Application entry point
├── VPadConnect.spec         # PyInstaller onedir specification
├── VPadConnect_onefile.spec # PyInstaller onefile specification
├── requirements.txt                       # Python dependencies
└── README.md
```

## Troubleshooting

### Virtual Xbox controller does not appear

Make sure **ViGEmBus** is installed correctly.

Then:

1. Close VPadConnect.
2. Verify the ViGEmBus installation.
3. Restart Windows if required by the driver installation.
4. Launch VPadConnect again.
5. Recreate or restart the virtual controller.

### The physical controller is not detected

Check that Windows detects the controller first.

Then:

1. Disconnect and reconnect the device.
2. Reopen **Add Controller**.
3. Check whether the device exposes multiple HID interfaces.
4. Select the interface that provides the actual controller input reports.

Some physical devices expose multiple HID interfaces for different functions. The correct interface must be selected for controller input.

### The application starts, but settings are not saved

Make sure the executable is located in a writable directory.

Avoid running the application directly from:

```text
C:\Program Files\
```

or another protected directory without appropriate permissions.

### Controller input works, but the game does not detect it

Make sure the virtual controller is actually created and visible to Windows.

You can verify this through Windows' controller/device management tools.

Also check:

* ViGEmBus installation
* Active controller profile
* Button/axis mappings
* Deadzone configuration
* Whether another virtual-controller application is conflicting with the device

### Multiple controllers appear

Some devices expose more than one HID interface.

Inspect the detected device list and choose the interface corresponding to the controller's actual input reports.

## Development

### Main technologies

| Component          | Technology                           |
| ------------------ | ------------------------------------ |
| GUI                | PySide6 / Qt 6                       |
| Language           | Python                               |
| HID input          | HID-compatible controller interfaces |
| Virtual controller | `vgamepad` / ViGEm                   |
| Packaging          | PyInstaller                          |
| Target platform    | Windows x64                          |

### Entry point

```text
main.py
```

### Automated tests

From the repository root, install the project dependencies and `pytest`, then
run the Python and browser checks:

```bash
python -m pip install -r requirements.txt pytest
python -m pytest -q
node --check ui/web/static/app.js
node --test tests/test_web_frontend.cjs
```

The Python suite covers shared protocol, permission, controller-mapping, and
configuration behavior. The Node tests cover browser touch-input behavior.
These checks do not replace testing the Windows executable with ViGEmBus and
real controllers.

### Packaging

The project uses PyInstaller specifications for both:

* `onedir`
* `onefile`

The packaged build is intended to keep the runtime independent from the local Python installation.

## Architecture

The application is organized around separate responsibilities for input acquisition, mapping, emulation, configuration, and the graphical interface.

Conceptually:

```text
                 ┌─────────────────────┐
                 │   Physical HID      │
                 │     Controller      │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │   VPadConnect Core  │
                 │                     │
                 │ Discovery           │
                 │ Mapping             │
                 │ Profiles            │
                 │ Hotkeys             │
                 │ Settings            │
                 └───────┬─────┬───────┘
                         │     │
               ┌─────────┘     └──────────┐
               ▼                          ▼
     ┌─────────────────┐        ┌─────────────────┐
     │ Virtual XInput  │        │ Mouse Output    │
     │ Xbox 360 Pad    │        │ and Hotkeys     │
     └─────────────────┘        └─────────────────┘
```

This separation makes it possible to extend the project with additional input and output methods without tightly coupling them to the GUI.

## Project Status

VPadConnect is an actively developed Windows controller-remapping and remote-control project.

Current focus includes:

* Stable controller detection
* Reliable XInput emulation
* Profile management
* Input customization
* Desktop mouse control
* Remote gamepad support
* Windows packaging and distribution

## Release policy

Tagged releases are published on GitHub with a self-contained Windows
one-file executable. Release notes call out user-visible changes, compatibility
notes, and validation results so the downloadable artifact can be tested and
tracked independently from source checkouts.

## License

No license file is currently included in the repository.

Without an explicit open-source license, the default copyright rules apply. Others may view and fork the repository through GitHub's platform features, but they should not assume they have permission to redistribute or modify the software beyond what applicable law or GitHub's terms permit.

Add an appropriate `LICENSE` file before presenting the project as open source or allowing third-party redistribution.

## Repository

**GitHub:**
https://github.com/ArvinNotDev/VPadConnect

**Releases:**
https://github.com/ArvinNotDev/VPadConnect/releases

---

<p align="center">
  <strong>VPadConnect</strong><br>
  Physical controller → virtual XInput, mouse controls, and hotkeys.
</p>

## HidHide integration

VPadConnect includes an optional HidHide integration on Windows. From the Controller Emulation page, the HidHide control:

- detects the installed HidHide configuration CLI without requiring a hard-coded install path;
- opens the official Nefarius release page when HidHide is not installed;
- registers the running VPadConnect executable in HidHide's application whitelist;
- matches connected supported controllers against HidHide's own `symbolicLink` / `deviceInstancePath` data;
- adds only missing controller blacklist entries and enables HidHide's cloak;
- keeps configuration changes idempotent and does not disable or overwrite an already-active HidHide cloak owned by another application.

The official HidHide releases are available at:
https://github.com/nefarius/HidHide/releases
