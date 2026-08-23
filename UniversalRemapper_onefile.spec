# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs


project_root = Path(SPECPATH)

datas = [
    (str(project_root / "config"), "config"),
    (str(project_root / "profiles"), "profiles"),
    (str(project_root / "ui" / "themes"), "ui/themes"),
    (str(project_root / "ui" / "assets"), "ui/assets"),
]

binaries = collect_dynamic_libs("vgamepad")
datas += collect_data_files("vgamepad")

hiddenimports = [
    "hid",
    "vgamepad.win",
    "vgamepad.win.vigem_client",
    "vgamepad.win.vigem_commons",
    "vgamepad.win.virtual_gamepad",
    "keyboard",
    "pyautogui",
]


a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["kivy", "phone_client_with_auth"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="InputBridge-Gamepad2XInput",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)
