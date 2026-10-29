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


def test_mouse_delta_smoother_spreads_relative_motion_without_losing_pixels():
    import threading
    import time
    import types

    fake_pyautogui = types.ModuleType("pyautogui")
    fake_pyautogui.PAUSE = 1.0
    mouse_module = _load_mouse_module(fake_pyautogui)
    calls = []
    completed = threading.Event()

    def move(dx, dy):
        calls.append((dx, dy, time.monotonic()))
        if len(calls) >= 3:
            completed.set()

    smoother = mouse_module.MouseDeltaSmoother(move, interval_ms=3)
    try:
        smoother.add(12, -6)
        assert completed.wait(0.5), "mouse smoothing ticks did not complete"
    finally:
        smoother.close()

    assert len(calls) >= 3
    assert sum(dx for dx, _, _ in calls) == 12
    assert sum(dy for _, dy, _ in calls) == -6
    assert calls[-1][2] - calls[0][2] >= 0.003


def test_mouse_delta_smoother_coalesces_bursts_without_unbounded_backlog():
    import threading
    import types

    fake_pyautogui = types.ModuleType("pyautogui")
    fake_pyautogui.PAUSE = 1.0
    mouse_module = _load_mouse_module(fake_pyautogui)
    calls = []
    reached_total = threading.Event()
    expected_dx = 120
    expected_dy = -60

    def move(dx, dy):
        calls.append((dx, dy))
        if sum(x for x, _ in calls) >= expected_dx:
            reached_total.set()

    smoother = mouse_module.MouseDeltaSmoother(move, interval_ms=2, max_queued_segments=6)
    try:
        for _ in range(30):
            smoother.add(4, -2)
        assert reached_total.wait(0.5), "coalesced mouse motion did not drain"
    finally:
        smoother.close()

    assert sum(dx for dx, _ in calls) == expected_dx
    assert sum(dy for _, dy in calls) == expected_dy
