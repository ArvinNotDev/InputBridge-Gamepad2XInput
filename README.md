# InputBridge-Gamepad2XInput

<p align="center">
  <strong>A modern Windows gamepad remapper built with PySide6.</strong><br>
  Map HID controllers to virtual Xbox 360 (XInput) devices or mouse controls — with profiles, hotkeys, and remote gamepad support.
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

The latest release includes a self-contained Windows `.exe`, so Python is **not required** to run the packaged application.

> **Current release: v2.0.8** — per-controller DualSense Lightbar colors,
> optional battery and charging indications, and USB/Bluetooth output support.
> Read the complete [v2.0.8 release notes](RELEASE_NOTES_2.0.8.md) and the full [changelog](CHANGELOG.md)
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
* Remote gamepad server support
* System-tray integration
* Dark and light themes
* Persistent application settings
* Per-controller DualSense Lightbar colors with optional battery and charging indication
* DualSense USB and Bluetooth Lightbar output reports
* DualSense Edge support for Lightbar output (PID `0x0DF2`)
* Automatic settings save with per-section reset controls
* English, فارسی, and Español UI languages
* Portable profile export/import (`.ibprofile`) with avatar support
* In-app About page with developer and project links
* Portable/self-contained Windows executable
* Separate writable user configuration from bundled application resources

Keyboard emulation is intentionally not enabled in the current release. The
keyboard target remains reserved for a future implementation; controller
hotkeys and media/custom commands are available independently.

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
not required. Keyboard emulation itself is not enabled in the current release.

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
10. If the device is a DualSense, open its **Lightbar** settings and choose the
    Lightbar state, color, battery mode, and charging indication.
11. Start the emulation.

Once configured, the physical controller can be translated into a virtual XInput controller, mouse movement, or hotkey actions.

## DualSense Lightbar

InputBridge-Gamepad2XInput provides a compact Lightbar panel for each supported
DualSense controller. The settings belong to the selected physical controller,
so changing one controller does not change another controller's Lightbar.

### Supported devices

| Device | Vendor ID | Product ID | Lightbar output |
| --- | ---: | ---: | --- |
| Sony DualSense | `0x054C` | `0x0CE6` | USB and Bluetooth |
| Sony DualSense Edge | `0x054C` | `0x0DF2` | USB and Bluetooth |

The current desktop setup is commonly used over Bluetooth. USB Lightbar output
is implemented as well, so a cable connection uses the correct DualSense
report format without using DualShock 4 output packets. USB hardware
verification requires a controller connected by cable.

### Configure a controller

1. Open **Controller Emulation**.
2. Add the DualSense controller and select **Emulate** if it is not already running.
3. Click **Lightbar** on that controller's row.
4. Choose **Lightbar On**, select a color, and confirm the HEX value in the preview.
5. Optionally enable **Battery Lightbar** and/or **Charging indication**.
6. Click **Save**.

The color selector stores a six-digit RGB HEX value such as `#8B5CF6`. The
Lightbar button is shown only for supported DualSense devices, and the dialog
identifies the controller being edited.

### Custom color and temporary battery colors

The saved custom color is kept separately from temporary status colors.

When **Battery Lightbar** is enabled, the Lightbar uses this progression:

| Battery level | Lightbar color |
| --- | --- |
| High (`70–100%`) | Green |
| Medium (`40–69%`) | Yellow |
| Low (`20–39%`) | Orange |
| Critical (`0–19%`) | Red |

When charging indication is enabled and the controller is charging, a subtle
cyan charging color is used. When charging stops, the Lightbar returns to the
current battery color or the saved custom color, depending on the selected
mode. Temporary colors never replace the saved custom HEX value.

### Persistence and reconnects

Lightbar settings are stored in the existing application settings file. The
application prefers the controller's serial number, then a Bluetooth address
found in the HID path, and finally the HID path itself as a fallback. This
allows settings to return after a reconnect when Windows/HIDAPI exposes a
stable controller identity.

Each controller keeps its own:

* Lightbar enabled state
* Saved custom RGB color
* Battery Lightbar mode
* Charging indication setting

### Output report behavior

Lightbar reports are sent only when the effective state changes, when the
controller reconnects, or when the user changes a Lightbar setting. Identical
reports are not continuously resent.

USB output uses the DualSense report ID `0x02` and a 63-byte HIDAPI buffer.
Bluetooth output uses report ID `0x31` and a 78-byte HIDAPI buffer. Bluetooth
sequence numbers are kept per controller and wrap from `15` to `0`. The CRC
is calculated with the `0xA2` seed, while the seed is excluded from the buffer
passed to `hid_write()`.

The implementation deliberately does not use DualShock 4 output report IDs
`0x05` or `0x11`, and the existing `led_brightness` concept is not treated as
Lightbar RGB brightness. A Lightbar brightness control should scale the RGB
channels in software.

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

## Remote Gamepad Support

InputBridge-Gamepad2XInput includes support for a remote gamepad server.

This allows controller input to be received remotely and processed by the application as part of its input/remapping pipeline.

Remote access functionality can be configured separately from local controller mappings.

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
├── RELEASE_NOTES_2.0.8.md                 # Release-ready notes for v2.0.8
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

### DualSense Lightbar settings do not appear

The Lightbar control is shown only for Sony DualSense devices with VID
`0x054C` and PID `0x0CE6`, or DualSense Edge devices with PID `0x0DF2`.
Reconnect the controller and reopen **Add Controller** if Windows has exposed a
different HID interface.

### The Lightbar color does not change

Check that **Lightbar On** is enabled and that the selected controller is the
one being configured. The application coalesces duplicate output reports, so
it will not resend an identical color continuously. On Bluetooth, reconnecting
the controller can be necessary after a failed HID connection.

### Battery colors are not visible

Enable **Battery Lightbar** in that controller's Lightbar dialog. Battery mode
is separate from the saved custom color and only changes the temporary output
color while battery data is available. If the controller report does not
expose battery status, the saved custom color remains the fallback.

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

The repository may also contain remote-controller functionality such as:

```text
phone_client_with_auth.py
```

This component is not part of the desktop application's primary entry-point dependency graph.

The desktop application can therefore be built and executed independently of the remote client component.

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
tracked independently from source checkouts. The repository keeps a matching
`RELEASE_NOTES_<version>.md` file that can be pasted into the GitHub release
description when the executable is uploaded.

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
  Physical controller → virtual XInput, keyboard, and mouse input.
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
