"""Detect the optional ViGEmBus virtual-gamepad driver on Windows.

Physical HID reading, mouse control, hotkeys and the Web Companion's PC Remote
features do not depend on this driver. Only virtual Xbox/XInput output does.
"""
from __future__ import annotations

import os

VIGEMBUS_RELEASES_URL = "https://github.com/nefarius/ViGEmBus/releases/latest"
VIGEMBUS_SERVICE_KEY = r"SYSTEM\CurrentControlSet\Services\ViGEmBus"


def is_vigem_installed() -> bool:
    """Return whether Windows has registered the ViGEmBus kernel service.

    This is intentionally a lightweight availability check and does not create a
    virtual controller. The actual emulation path still handles driver startup
    or runtime failures separately.
    """
    if os.name != "nt":
        return False

    try:
        import winreg
    except ImportError:
        return False

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, VIGEMBUS_SERVICE_KEY):
            return True
    except OSError:
        return False
