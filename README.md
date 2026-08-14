# Universal Remapper

<p align="center">
  <strong>A modern Windows gamepad remapper built with PySide6.</strong><br>
  Map HID controllers to virtual Xbox 360 or keyboard inputs — with profiles, hotkeys, mouse mode, and remote gamepad support.
</p>

<p align="center">
  <a href="https://github.com/ArvinNotDev/python-universal-gamepad-remapper/releases/latest">
    <img src="https://img.shields.io/github/v/release/ArvinNotDev/python-universal-gamepad-remapper?style=flat-square&color=6f42c1" alt="Latest release">
  </a>
  <a href="https://github.com/ArvinNotDev/python-universal-gamepad-remapper/releases">
    <img src="https://img.shields.io/github/downloads/ArvinNotDev/python-universal-gamepad-remapper/total?style=flat-square&color=2ea44f" alt="Downloads">
  </a>
  <img src="https://img.shields.io/badge/platform-Windows-0078D4?style=flat-square" alt="Windows">
  <img src="https://img.shields.io/badge/PySide6-Qt%206-41CD52?style=flat-square" alt="PySide6">
</p>

## Overview

Universal Remapper turns physical HID controllers into configurable virtual gamepads or keyboard input. It is designed for users who want a lightweight, visual way to manage controller mappings without editing source code.

The latest release includes a self-contained Windows `.exe`. Python is not required to run the released application.

## Features

- HID controller discovery and live device monitoring
- Xbox 360 controller emulation through `vgamepad`
- Keyboard and media-key mapping
- Configurable controller profiles
- Custom controller hotkeys
- D-Pad and analog-stick mouse control
- Deadzone and axis-inversion settings
- Remote gamepad server
- System-tray integration
- Dark and light themes
- Settings persistence outside the bundled application resources

## Download

Download the latest executable from the [Releases](https://github.com/ArvinNotDev/python-universal-gamepad-remapper/releases) page.

For most users, download:

```text
UniversalRemapper.exe
```

Place the executable in a writable folder and launch it. The application creates its user settings next to the executable on first run.

## System requirement

The application itself is self-contained and does not require Python. Xbox 360 emulation additionally requires the system-level **ViGEmBus** driver. The packaged build contains the required `ViGEmClient.dll`; the driver may need to be installed separately on a clean Windows installation.

If you only need keyboard or mouse mapping, the virtual gamepad driver is not required.

## Quick start

1. Download `UniversalRemapper.exe` from the latest release.
2. Install ViGEmBus if Xbox 360 emulation is needed.
3. Connect a controller.
4. Open **Controller Emulation**.
5. Click **Add Controller**.
6. Select the HID device and the target emulation.
7. Configure profiles, hotkeys, mouse mode, or sensitivity in **Settings**.

## Configuration files

User-writable files are stored beside the executable:

```text
config/settings.conf
hotkeys.json
trusted_clients.json
```

Bundled read-only resources include:

```text
profiles/
ui/themes/
ui/assets/tray.png
```

This separation allows the same path logic to work in both source execution and PyInstaller builds.

## Build from source

### Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### Build the recommended onedir package

```powershell
python -m PyInstaller --clean --noconfirm UniversalRemapper.spec
```

Output:

```text
dist/
└── UniversalRemapper/
    └── UniversalRemapper.exe
```

### Build the single-file executable

```powershell
python -m PyInstaller --clean --noconfirm `
  --distpath dist\onefile `
  --workpath build\UniversalRemapper_onefile `
  UniversalRemapper_onefile.spec
```

Output:

```text
dist/
└── onefile/
    └── UniversalRemapper.exe
```

## Project structure

```text
.
├── core/                  # HID, mapping, emulation, settings, utilities
├── ui/                    # PySide6 windows, pages, themes, and assets
├── profiles/              # Controller profile definitions
├── config/                # Default application configuration
├── main.py                # Application entry point
├── UniversalRemapper.spec
└── UniversalRemapper_onefile.spec
```

## Troubleshooting

### The application starts, but virtual Xbox input does not work

Install or repair the ViGEmBus driver, then restart the application.

### The controller is not listed

Check that Windows detects the device, reconnect it, and reopen **Add Controller**. Some devices expose multiple HID interfaces; select the interface that provides the controller reports.

### Settings are not saved

Move the executable to a writable directory. Avoid launching it directly from a protected folder such as `C:\Program Files` unless the application has write permission.

## Development notes

- Entry point: `main.py`
- GUI framework: PySide6
- Packaging: PyInstaller
- Build target: Windows x64
- The separate `phone_client_with_auth.py` file is not part of the desktop application's entry-point dependency graph.

## License

No license file is currently included in the repository. Add a license before redistributing the project.
