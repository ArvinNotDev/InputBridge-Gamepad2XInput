# VPadConnect

<p align="center">
  <img src="ui/assets/vpadconnect-icon.png" alt="VPadConnect application icon" width="88">
</p>

<p align="center">
  <img src="docs/branding/vpadconnect-logo.svg" alt="VPadConnect — Virtual Gamepad. Connected Control." width="640">
</p>

<p align="center"><strong>Virtual Gamepad. Connected Control.</strong></p>

**VPadConnect** is a Windows desktop app that maps physical HID controllers to virtual Xbox/XInput output, mouse controls, and hotkeys. It also includes a browser-based companion for mobile gamepad and PC remote controls.

## Download the beta

**[Download VPadConnect 0.2.1 Beta 1](https://github.com/ArvinNotDev/VPadConnect/releases/tag/v0.2.1-beta.1)** · [All releases](https://github.com/ArvinNotDev/VPadConnect/releases)

Download `VPadConnect.exe` from the release assets. It is a Windows x64, PyInstaller one-file build; Python is not needed to run it. `SHA256SUMS.txt` is provided to verify the executable.

### Requirements and installation

- Windows 10 or later, 64-bit.
- Save the executable in a folder your Windows account can write to.
- Install **ViGEmBus** only if you want virtual Xbox/XInput controller emulation. Mouse controls, hotkeys, and Web Companion PC Remote features do not require it.

1. Download `VPadConnect.exe` from the [beta release](https://github.com/ArvinNotDev/VPadConnect/releases/tag/v0.2.1-beta.1).
2. Install ViGEmBus if you need virtual XInput output.
3. Connect your physical controller and launch `VPadConnect.exe`.
4. Open **Controller Emulation → Add Controller**, choose the controller's HID interface, configure its mapping, and start emulation.

For a quick tour, see [Quick start](#quick-start). Read [What's new in this beta](.github/release-notes/0.2.1-beta.1.md) and the [full changelog](CHANGELOG.md).

> **Beta:** Controller and Windows compatibility can vary. Back up important profiles before testing and report reproducible problems. Automated checks do not mean every controller has been manually tested.

## Quick start

1. Connect a controller and open **Controller Emulation → Add Controller**.
2. Select the HID interface that supplies its input reports.
3. Choose virtual XInput output, mouse control, or hotkeys and configure the mapping.
4. Install ViGEmBus before using virtual XInput output; other modes do not need that driver.
5. Start emulation. Use **Settings → Developer** for diagnostics, including the live Raw HID terminal.

To use a phone or tablet, open **Web Companion** in the desktop app, start its web server, and open the displayed HTTPS address on a device on the same trusted network. Browser gamepad, touch mouse, scrolling, and permission-controlled PC Remote features are available. A browser may warn about the local self-signed certificate; compare its fingerprint with the one shown by the desktop app.

## Features

- Physical HID controller discovery and configurable profiles.
- Virtual Xbox 360/XInput output through ViGEmBus.
- Controller-driven mouse movement, adjustable mouse deadzone and sensitivity, and hotkeys.
- Responsive Settings sections, persistent reduced-motion preference, and rotating developer log files.
- Live Raw HID terminal with timestamped hexadecimal reports, packet statistics, pause/resume, copy, and capture save.
- Mobile Web Companion with touch gamepad, touch mouse, scrolling, and authenticated persistent input when WebSocket is available.

Virtual XInput requires the system-level ViGEmBus driver. The driver is not bundled with VPadConnect. Mouse and Web Companion PC Remote features that do not use virtual XInput can be used without it.

## Run from source / command line

`main.py` starts the PySide6 desktop GUI. This repository does **not** provide a separate headless command-line controller-remapping app; the commands below are for running, testing, and building the GUI from source. These PowerShell commands use Python 3.12 and stable packages from PyPI:

```powershell
git clone https://github.com/ArvinNotDev/VPadConnect.git
cd VPadConnect
py -3.12 -m venv .venv
$python = ".\.venv\Scripts\python.exe"
& $python -m pip install --upgrade pip

# Keep the optional Python 3.15 Qt development index out of this Python 3.12 install.
$requirements = Join-Path $env:TEMP 'vpadconnect-requirements-py312.txt'
$lines = Get-Content requirements.txt | Where-Object { $_ -notmatch '^\s*--extra-index-url\b' }
[System.IO.File]::WriteAllLines($requirements, [string[]]$lines, [System.Text.UTF8Encoding]::new($false))
& $python -m pip install --isolated --index-url https://pypi.org/simple -r $requirements pytest

# Run the desktop GUI.
& $python main.py

# Run the Python and browser regression checks.
& $python -m compileall -q core ui tests main.py
& $python -m pytest -q
node --check ui/web/static/app.js
node --test tests/test_web_frontend.cjs

# Build the Windows x64 one-file executable.
& $python -m PyInstaller --clean --noconfirm VPadConnect_onefile.spec
```

The one-file build is written to `dist\VPadConnect.exe`. The application entry point launches the desktop GUI; no terminal-only controller-remapping commands are currently available.

## Known limitations

- Physical-controller-to-keyboard mapping is not currently available. Web Companion keyboard input is a separate, permission-controlled remote feature.
- Virtual XInput output depends on ViGEmBus being installed and working on the PC.
- HID interfaces and behavior vary between controller models; check the [beta notes](.github/release-notes/0.2.1-beta.1.md) for validation details and current limitations.

## Links

- [Download Beta](https://github.com/ArvinNotDev/VPadConnect/releases/tag/v0.2.1-beta.1)
- [Full changelog](CHANGELOG.md)
- [Beta release notes](.github/release-notes/0.2.1-beta.1.md)
- [GitHub repository](https://github.com/ArvinNotDev/VPadConnect)

## License

No license file is currently included in the repository.
