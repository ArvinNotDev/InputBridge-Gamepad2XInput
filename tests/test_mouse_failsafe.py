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
    position_queries = []
    pyautogui = types.ModuleType("pyautogui")

    class FailSafeException(Exception):
        pass

    pyautogui.PAUSE = 1.0
    pyautogui.FAILSAFE = True
    pyautogui.FAILSAFE_POINTS = [(0, 0)]
    pyautogui.FailSafeException = FailSafeException
    pyautogui.position = lambda: position_queries.append(cursor["position"]) or cursor["position"]

    def move_rel(dx, dy, duration=0):
        calls.append((pyautogui.FAILSAFE, dx, dy, duration))
        if pyautogui.FAILSAFE and cursor["position"] in pyautogui.FAILSAFE_POINTS:
            raise FailSafeException("cursor is at the fail-safe corner")
        x, y = cursor["position"]
        cursor["position"] = (x + dx, y + dy)

    pyautogui.moveRel = move_rel

    mouse_module = _load_mouse_module(pyautogui)
    mouse_module.Mouse.moveRel(14, 7)
    assert calls == [(True, 14, 7, 0.0), (False, 14, 7, 0.0)]
    assert cursor["position"] == (14, 7)
    assert pyautogui.FAILSAFE is True

    # Away from a fail-safe corner, normal movement must avoid an extra
    # cursor-position query in the hot path.
    cursor["position"] = (20, 30)
    mouse_module.Mouse.moveRel(-4, 3)
    assert calls[-1] == (True, -4, 3, 0.0)
    assert pyautogui.FAILSAFE is True
    assert position_queries == []
