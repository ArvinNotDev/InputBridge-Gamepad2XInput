Universal Gamepad Remapper
==========================

A Python desktop application for remapping supported HID controllers and phone-based controller input to an emulated Xbox 360 controller. The desktop app is built with PySide6, uses `hidapi` for physical controller input, and uses `vgamepad` for XInput emulation.

Features
--------

- Physical controller detection for supported DualShock 4, DualSense, UnoJoy, and generic profiles.
- Xbox 360 controller emulation through `vgamepad`.
- Remote phone controller server with trusted-client authentication.
- Configurable deadzones, axis inversion, button inversion, mouse mode, themes, and developer settings.
- Hotkey bindings for common media controls.

Project Layout
--------------

- `main.py` - desktop application entry point.
- `core/` - controller models, HID polling, mapping, emulation, settings, and utility logic.
- `ui/` - PySide6 windows, pages, dialogs, themes, and assets.
- `profiles/` - JSON HID profiles for supported controller layouts.
- `phone_client_with_auth.py` - Kivy-based phone controller client.
- `config/settings.conf` - local desktop settings.
- `hotkeys.json` - local hotkey mapping storage.
- `trusted_clients.json` - local trusted remote client storage.
- `tests/` - unit tests for pure application logic.

Requirements
------------

- Python 3.10 or newer.
- Windows is recommended for XInput emulation.
- A working virtual gamepad backend compatible with `vgamepad`.
- HID access permissions for physical controller polling.

Install
-------

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install desktop dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the desktop app:

```powershell
python main.py
```

Run Tests
---------

```powershell
python -m unittest discover
python -m compileall core ui main.py phone_client_with_auth.py tests
```

Development Notes
-----------------

- Keep controller profile changes in `profiles/` small and verify them against real HID reports.
- Keep settings changes compatible with existing `config/settings.conf` files; `SettingsManager` normalizes missing and invalid values on load.
- Prefer adding pure helper modules and unit tests for mapping, parsing, and persistence logic before touching UI wiring.
- Avoid committing local runtime state unless it is intentionally part of the sample configuration.

Troubleshooting
---------------

- If emulation does not start, confirm the virtual gamepad backend required by `vgamepad` is installed and running.
- If physical controllers are not listed, confirm the device is visible to `hidapi` and not exclusively captured by another application.
- If settings become invalid, delete or edit `config/settings.conf`; the app will recreate missing values on the next start.
