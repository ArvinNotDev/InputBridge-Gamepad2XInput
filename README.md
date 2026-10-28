# InputBridge-Gamepad2XInput

<p align="center">
  <strong>Remap Windows gamepads with a simple PySide6 desktop app.</strong><br>
  Send HID controller input to a virtual Xbox 360 (XInput) controller, mouse controls, or hotkeys, and manage mappings with profiles.
</p>

<p align="center">
  <a href="https://github.com/ArvinNotDev/InputBridge-Gamepad2XInput/releases/latest">
    <img src="https://img.shields.io/github/v/release/ArvinNotDev/InputBridge-Gamepad2XInput?style=flat-square&color=6f42c1" alt="Latest release">
  </a>
  <a href="https://github.com/ArvinNotDev/InputBridge-Gamepad2XInput/releases">
    <img src="https://img.shields.io/github/downloads/ArvinNotDev/InputBridge-Gamepad2XInput/total?style=flat-square&color=2ea44f" alt="Downloads">
  </a>
  <img src="https://img.shields.io/badge/platform-Windows-0078D4?style=flat-square" alt="Windows">
  <img src="https://img.shields.io/badge/PySide6-Qt%206-41CD52?style=flat-square" alt="PySide6">
  <img src="https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/license-Unlicensed-lightgrey?style=flat-square" alt="License">
</p>

---

## Overview

**InputBridge-Gamepad2XInput** is a Windows desktop application for remapping physical HID controllers to virtual **Xbox 360 / XInput** devices and responsive mouse controls.

It provides a graphical interface for configuring controller mappings without modifying source code. Profiles, hotkeys, analog settings, mouse emulation, and remote gamepad support are managed directly from the application.

The project is built with **PySide6** and packaged for Windows using **PyInstaller**.

The latest release includes a self-contained Windows `.exe`, so Python is **not required** to run the packaged application. For source setup and build instructions, see [Build From Source](#build-from-source).

> **Current release: v2.0.8** — per-controller DualSense Lightbar colors,
> optional battery and charging indications, and USB/Bluetooth output support.
> See the full [changelog](CHANGELOG.md)
> and the [latest release](https://github.com/ArvinNotDev/InputBridge-Gamepad2XInput/releases/latest).

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
* Remote phone touchpad with cursor movement, left/right/middle buttons, and scrolling
* Remote phone keyboard typing with text, editing, navigation, and special-key events
* Per-phone choice between XInput gamepad output and direct Windows mouse output
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
work. This is separate from **phone-to-PC remote keyboard input**, which is
available through the companion phone client's Remote screen after explicit
permission is enabled on the PC.

## Download

Download the latest version from the [Releases](https://github.com/ArvinNotDev/InputBridge-Gamepad2XInput/releases) page.

For most users, download:

```text
InputBridge-Gamepad2XInput.exe
```

The packaged application is intended to run directly on Windows without requiring a Python installation.

Place the executable in a writable directory and launch it. On first run, InputBridge-Gamepad2XInput creates its required user configuration files automatically.

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
not required. Direct physical-controller-to-keyboard mapping is not enabled; phone remote-keyboard input is a separate feature and requires its PC permission.

## Quick Start

1. Download `InputBridge-Gamepad2XInput.exe` from the latest [Release](https://github.com/ArvinNotDev/InputBridge-Gamepad2XInput/releases).
2. Install **ViGEmBus** if you want virtual Xbox 360 / XInput emulation.
3. Connect your physical controller.
4. Launch **InputBridge-Gamepad2XInput**.
5. Open **Controller Emulation**.
6. Click **Add Controller**.
7. Select the HID controller interface you want to use.
8. Select the target emulation mode.
9. Configure mappings, profiles, hotkeys, mouse mode, and sensitivity as needed.
10. Start the emulation.

Once configured, the physical controller can be translated into a virtual XInput controller, mouse movement, or hotkey actions.

## Controller Mapping

InputBridge-Gamepad2XInput separates the physical input device from the virtual output device.

A typical configuration looks like:

```text
Physical HID Controller
        │
        ▼
InputBridge-Gamepad2XInput
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

InputBridge-Gamepad2XInput can use controller inputs as mouse controls.

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

## Phone-to-PC Remote Control

InputBridge now provides two separately named mobile clients:

- **PySide6 Mobile (recommended):** the modern Qt for Python client in `mobile_pyside6/`. It contains Connect, Gamepad, Mouse, Remote and Settings screens with a touch-first dark interface.
- **Legacy Kivy Mobile:** the previous client is preserved in `mobile_kivy_legacy/main.py`, along with its legacy Buildozer configuration and dependency list. It is kept separate so the two approaches cannot be confused.

### PySide6 mobile source and Android runtime

The PySide6 client source is maintained in `mobile_pyside6/`. This repository intentionally does **not** build or publish a mobile APK/AAB. CI only validates the Python source and tests.

A Python source file using PySide6 cannot directly become a native Android application by itself: Android does not provide the Python interpreter and Qt/PySide runtime required by the source. Qt documents the packaging requirement in its [official Android deployment guide](https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-android-deploy.html).

For source development, follow [the PySide6 mobile README](mobile_pyside6/README.md). The interface, controller-state protocol, pairing validation, and remote-action flow can be tested on a desktop. Real Android camera/sensor behavior and native phone deployment cannot be verified by source-only tests.

### Secure pairing and connection

1. Start the updated InputBridge desktop app and open **Server**.
2. Start the server and choose **Show Phone Pairing QR**.
3. On the phone, open **Connect → Scan pairing QR**. If scanning is unavailable, paste the complete QR JSON payload or enter the PC address, port, and SHA-256 certificate fingerprint manually.
4. Keep the phone and PC on the same local network. The mobile client verifies the live TLS certificate against the QR/saved SHA-256 pin before it sends controller state or pairing data.
5. If the phone has not been trusted, enter the short pairing code shown beside that device in the desktop Server page.
6. Use **Gamepad**, **Mouse**, or **Remote**. Remote actions remain gated by the individual permissions explicitly enabled in the desktop app.

The QR contains only the PC endpoint and public certificate fingerprint; the private TLS key is never exported. If the desktop certificate is replaced, verify the new fingerprint deliberately and scan the new QR. Do not accept a fingerprint sent through an untrusted channel.

### PySide6 mobile features

- Gamepad buttons, bumpers, menu/system buttons, D-pad, dual analogue sticks and L2/R2 triggers.
- Standard and Driving modes with optional accelerometer steering and centre calibration when QtSensors is available.
- Touchpad cursor movement, left/right/middle clicks, tap-to-click, scrolling and pointer sensitivity.
- Remote text input, special keys, modifiers, approved shortcuts, media controls, explicit clipboard read/write, approved app shortcuts, presentation controls, PC status, and confirmation-gated power actions.
- Pinned TLS transport, retry handling, device identity persistence, and server capability/permission awareness.

### Legacy Kivy client

The previous Kivy implementation lives at `mobile_kivy_legacy/main.py`. Its Buildozer file and phone dependencies were moved with it. Use this legacy directory only if you specifically want the Kivy version; the recommended client is `mobile_pyside6/`.

### Remote actions currently implemented

* Remote text input, common special keys, modifier keys, and allowlisted shortcuts.
* System media keys for volume, mute, playback, previous/next track, and stop.
* Explicit clipboard send/read actions (automatic background clipboard
  synchronization is not implemented).
* Fixed, approved app shortcuts (browser, File Explorer, Calculator, Notepad,
  and the Downloads folder); arbitrary shell commands are not accepted.
* Presentation key controls, PC name/OS/local-time status, and permission-gated
  power actions. Disruptive power actions require confirmation on the phone.
* A desktop permission panel. All remote-action permissions, including power,
  start disabled and must be enabled by the PC user.

### Current scope and compatibility

This update changes the remote transport from raw TCP to TLS. **The desktop
server and phone client must be updated together**; an older phone client that
expects an unencrypted connection will not connect to the updated server.
The existing pairing code still establishes device trust after the TLS pin is
verified. The TLS certificate pin provides transport identity, while the
pairing flow provides the app's trusted-device authorization.

Automatic LAN discovery, automatic reconnection, bidirectional file transfers,
URL sharing/history, screenshots/live screen preview, Windows notification
forwarding, battery/CPU/RAM telemetry, custom user-defined app shortcuts, and
a dedicated presentation UI are not implemented by this milestone and are not
advertised as available features. Clipboard synchronization is explicit only;
there is no background clipboard polling.

### Mobile clients

`phone_client_with_auth.py` remains the Kivy/Android-friendly client. It now has
a dedicated **Keyboard** tab and opens a focused **Secure pairing** popup for
the code shown in the desktop Server page.

`phone_client_pyside6.py` is a completely self-contained PySide6 client. It
contains Connect, Controller, Mouse, Keyboard, and Settings tabs in one file,
persists the device identity and last server, and uses the same authenticated
newline-delimited protocol. Run it with:

```text
python phone_client_pyside6.py
```

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
InputBridge-Gamepad2XInput.exe
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
git clone https://github.com/ArvinNotDev/InputBridge-Gamepad2XInput.git
cd InputBridge-Gamepad2XInput
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
python -m PyInstaller --clean --noconfirm InputBridge-Gamepad2XInput.spec
```

Output:

```text
dist/
└── InputBridge-Gamepad2XInput/
    └── InputBridge-Gamepad2XInput.exe
```

The **onedir** build is generally recommended for development and distribution when fast startup and easier troubleshooting are preferred.

### Build the single-file executable

```powershell
python -m PyInstaller --clean --noconfirm `
  --distpath dist\onefile `
  --workpath build\InputBridge-Gamepad2XInput_onefile `
  InputBridge-Gamepad2XInput_onefile.spec
```

Output:

```text
dist/
└── onefile/
    └── InputBridge-Gamepad2XInput.exe
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
├── InputBridge-Gamepad2XInput.spec         # PyInstaller onedir specification
├── InputBridge-Gamepad2XInput_onefile.spec # PyInstaller onefile specification
├── requirements.txt                       # Python dependencies
└── README.md
```

## Troubleshooting

### Virtual Xbox controller does not appear

Make sure **ViGEmBus** is installed correctly.

Then:

1. Close InputBridge-Gamepad2XInput.
2. Verify the ViGEmBus installation.
3. Restart Windows if required by the driver installation.
4. Launch InputBridge-Gamepad2XInput again.
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
                 │   InputBridge Core  │
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

## Remote Client

The recommended phone-client source is the **PySide6 Mobile** client in
`mobile_pyside6/main.py`. Its current CI workflow validates the source and unit tests only; it does not build or publish an APK/AAB. To run this as a native Android app, the Python, Qt and PySide runtime still has to be packaged as documented by [Qt for Python](https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-android-deploy.html).

The previous Kivy implementation remains available separately in
`mobile_kivy_legacy/main.py` as the **Legacy Kivy Mobile** version. The two clients
share the desktop protocol, while the PySide6 source provides Connect, Gamepad,
Mouse and Settings screens, secure QR pairing, one-finger pointer
movement, two-finger scrolling, optional tap-to-click and adjustable mouse
sensitivity. The mobile UI supports portrait and landscape layouts, touch scrolling,
and a full-screen Gamepad Focus mode. Source-only tests do not prove access to real
phone camera/sensors.

## Browser Web Companion

The desktop app includes a separate **Web Companion** tab. It starts an HTTPS
Flask server that lets a phone, tablet, or another PC use a browser as a controller;
no native phone app or APK is needed for this browser interface.

1. Install the desktop requirements and start InputBridge on Windows.
2. Open **Web Companion**, select a local HTTPS port (default 8765), and choose
   **Start Web Server**.
3. Scan its QR code with the phone camera, or open the displayed URL and enter
   the short-lived pairing code. Both devices need to be on the same trusted LAN.
4. If the browser warns about the self-signed HTTPS certificate, compare its
   SHA-256 fingerprint against the one displayed in the desktop tab before
   proceeding. The native client verifies its certificate pin in-app; browser
   certificate trust must be handled by the browser itself.
5. Use the browser's **Gamepad**, **Touch mouse**, and **PC Remote** tabs. Keyboard,
   media, clipboard, approved app shortcuts, presentation and power commands
   continue to obey the permissions configured on the desktop **Server** tab.

Each paired browser gets a separate virtual XInput controller. The web service
supports up to eight browser sessions at once and runs on port 8765 by default,
separately from the native phone socket server on port 5000. Stop the Web
Companion server when it is no longer needed and do not expose it to untrusted
networks. Its temporary pairing code expires after five minutes; inactive browser
sessions release input state automatically.

## Project Status

InputBridge-Gamepad2XInput is an actively developed Windows controller-remapping project.

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
https://github.com/ArvinNotDev/InputBridge-Gamepad2XInput

**Releases:**
https://github.com/ArvinNotDev/InputBridge-Gamepad2XInput/releases

---

<p align="center">
  <strong>InputBridge-Gamepad2XInput</strong><br>
  Physical controller → virtual XInput, mouse controls, and hotkeys.
</p>

## HidHide integration

InputBridge includes an optional HidHide integration on Windows. From the Controller Emulation page, the HidHide control:

- detects the installed HidHide configuration CLI without requiring a hard-coded install path;
- opens the official Nefarius release page when HidHide is not installed;
- registers the running InputBridge executable in HidHide's application whitelist;
- matches connected supported controllers against HidHide's own `symbolicLink` / `deviceInstancePath` data;
- adds only missing controller blacklist entries and enables HidHide's cloak;
- keeps configuration changes idempotent and does not disable or overwrite an already-active HidHide cloak owned by another application.

The official HidHide releases are available at:
https://github.com/nefarius/HidHide/releases
