"""Focused tests for relative mouse moves at PyAutoGUI's emergency corner.

The web-only CI job has no desktop session, so load core/mouse.py with a tiny
PyAutoGUI double instead of importing a real desktop backend.
"""
import importlib.util
import sys
import types
from pathlib import Path


def _load_mouse_module(pyautogui_double):
    path = Path(__file__).resolve().parents[1] / "core" / "mouse.py"
    spec = importlib.util.spec_from_file_location("vpad_mouse_failsafe_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get("pyautogui")
    sys.modules["pyautogui"] = pyautogui_double
    try:
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            sys.modules.pop("pyautogui", None)
        else:
            sys.modules["pyautogui"] = previous
    return module


def test_relative_mouse_move_can_leave_failsafe_corner_and_restore_safeguard():
    calls = []
    cursor = {"position": (0, 0)}
    pyautogui = types.ModuleType("pyautogui")
    pyautogui.PAUSE = 1.0
    pyautogui.FAILSAFE = True
    pyautogui.FAILSAFE_POINTS = [(0, 0)]
    pyautogui.position = lambda: cursor["position"]
    pyautogui.moveRel = lambda dx, dy, duration=0: calls.append(
        (pyautogui.FAILSAFE, dx, dy, duration)
    )

    mouse_module = _load_mouse_module(pyautogui)
    mouse_module.Mouse.moveRel(14, 7)
    assert calls == [(False, 14, 7, 0.0)]
    assert pyautogui.FAILSAFE is True

    cursor["position"] = (20, 30)
    mouse_module.Mouse.moveRel(-4, 3)
    assert calls[-1] == (True, -4, 3, 0.0)
    assert pyautogui.FAILSAFE is True
