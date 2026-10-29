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

> **Current beta: VPadConnect 0.2.1 Beta 1** — a fresh pre-1.0 baseline with
> responsive desktop Settings, a live Raw HID terminal, improved mouse latency,
> and the mobile Web Companion.
>
> **Recommended:** [Download the Windows one-file EXE](https://github.com/ArvinNotDev/VPadConnect/releases/tag/v0.2.1-beta.1).
> This is a **pre-release**; back up important profiles and report any issues.
> See [What's new](.github/release-notes/0.2.1-beta.1.md) and the
> [changelog](CHANGELOG.md).

## Support VPadConnect ☕

VPadConnect is free to use, and its source code is publicly available on GitHub. If it has made your controller setup easier, consider buying me a coffee. Your support helps fund compatibility testing, bug fixes, and new controller features — and helps me spend more time maintaining the project.

<p align="center">
  <a href="https://reymit.ir/arvinnotdev">
    <img src="https://img.shields.io/badge/Buy%20me%20a%20coffee-Support%20VPadConnect-FFB86B?style=for-the-badge&labelColor=202633" alt="Buy me a coffee to support VPadConnect">
  </a>
</p>

Thank you for helping VPadConnect keep growing. Using the app without donating is always welcome; support is entirely optional.

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
* Responsive HTTPS browser companion with a persistent low-latency input stream, touch gamepad, touch mouse, remote keyboard, media, clipboard, launch shortcuts, presentation and permission-gated power controls
* Native-style Xbox and PlayStation controller layouts with on-screen face-button, shoulder and trigger labels that follow the selected console style
* Full-screen Gamepad Focus with stable portrait/landscape ABXY layout, gyro-assisted Driving, larger analog throttle/brake controls, and a Shooter preset with digital hold-to-aim/fire triggers
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

## Choose how to use VPadConnect

### Option A — Download the ready-to-run Windows app (recommended)

**[Download VPadConnect 0.2.1 Beta 1](https://github.com/ArvinNotDev/VPadConnect/releases/tag/v0.2.1-beta.1)** · [All Releases](https://github.com/ArvinNotDev/VPadConnect/releases)

Download **`VPadConnect.exe`** from the release assets. It is a Windows x64 **PyInstaller one-file build**: you do not need to install Python, pip, or the project's dependencies.

1. Download `VPadConnect.exe` to a folder where your Windows account can write files.
2. If you need a virtual Xbox/XInput controller, install the system-level **ViGEmBus** driver first. It is not bundled into the executable. Mouse controls and the Web Companion's PC Remote features can work without it.
3. Double-click `VPadConnect.exe` and follow [Quick Start](#quick-start).

The first beta also includes `SHA256SUMS.txt` in the release assets. Use it to verify the downloaded executable's SHA-256 checksum. Since this is a beta, keep backups of important profiles and settings before testing.

### Option B — Run from the command line (source/developer setup)

Choose this option if you want to inspect the code, run tests, or build the executable yourself. These commands use PowerShell on Windows:

```powershell
git clone https://github.com/ArvinNotDev/VPadConnect.git
cd VPadConnect
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

`python main.py` starts the **desktop GUI**. The repository does **not** currently contain a separate headless CLI application that provides controller remapping entirely through terminal commands; the terminal workflow is for installing, running, testing, and building the desktop app.

To build the same single-file executable locally, after installing the dependencies run:

```powershell
python -m PyInstaller --clean --noconfirm VPadConnect_onefile.spec
```

The executable will be written to `dist\\VPadConnect.exe`. The official release workflow additionally runs automated tests, builds the one-file EXE on Windows, generates the checksum file, publishes the beta release, and cleans up older releases and non-main branches after the new release is available.

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

1. Download `VPadConnect.exe` from the [current beta release](https://github.com/ArvinNotDev/VPadConnect/releases/tag/v0.2.1-beta.1).
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

Use **Web Companion** to turn a phone, tablet, or another computer into a controller
for the Windows desktop. It serves the mobile-friendly interface over HTTPS; no
separate mobile app is required.

1. Start VPadConnect and open **Web Companion**.
2. Select **Start Web Server**, then open the displayed HTTPS URL or scan the QR
   code. Keep both devices on the same Wi-Fi/LAN; the server uses port **8765**.
3. The QR link carries a short-lived pairing code and the public TLS certificate
   fingerprint. The browser fills the code automatically. When pairing manually,
   enter the desktop code and compare the SHA-256 fingerprint before proceeding.
4. Use **Gamepad**, **Touch mouse**, or **PC Remote**. Optional PC actions remain
   controlled by the desktop permission settings.

### Mobile gamepad

**Gamepad Focus** expands the controller for play in portrait or landscape. Choose
between **Xbox** and **PlayStation** layouts using the controller-style button beside
the driving and calibration controls. The face-button symbols, shoulder labels and
trigger labels update to match the selected style, while input is mapped to the
corresponding XInput controls.

Choose **Standard**, **Driving**, or **Shooter** from the Gamepad preset selector.
Standard keeps the usual controls. Driving retains analog L2/R2 and gives the
throttle/brake sliders larger touch targets. Shooter replaces those sliders with
digital hold controls: L2 acts as aim and R2 as fire, each releasing to zero and
reaching full input while held. The selected preset is saved in that browser.

**Driving** mode supports phone-tilt steering. Enable motion access when requested,
hold the device at a comfortable neutral angle, and select **Calibrate center**.
Steering sensitivity can be adjusted without leaving the controller. Open the
mobile **Settings** tab for additional options, including Xbox/PlayStation layout,
pointer sensitivity, tap-to-click, scroll speed, reversed touchpad scrolling,
optional haptic feedback, screen wake lock, and restoring defaults. Preferences are
saved locally in that browser.

The **Touch mouse** uses a two-finger swipe to scroll. Enable **Reverse scrolling
direction** in Settings to invert both gesture scrolling and mouse-wheel scrolling;
adjust **Scroll speed** independently to make scrolling slower or faster.

Controller input travels over an authenticated persistent WebSocket per paired
browser, so changes do not wait for an HTTP response after every stick movement.
The server supports up to eight concurrent browser sessions, each with an
independent virtual controller. If the WebSocket is unavailable, the browser retains
an HTTP state fallback. Idle sessions expire automatically and release held inputs.

### Connection and certificate notes

The QR carries a public certificate fingerprint, never the private TLS key. A browser
may show a self-signed certificate warning on first connection. Compare its SHA-256
fingerprint with the value shown on the desktop before proceeding. JavaScript in the
browser cannot independently pin the TLS certificate, so do not bypass a warning if
the fingerprints do not match or cannot be checked. Use Web Companion only on a
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

The commands below are intended for contributors and users who want to inspect or package the application themselves. For the simplest install, use the pre-built one-file executable linked in [Choose how to use VPadConnect](#choose-how-to-use-vpadconnect).

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
