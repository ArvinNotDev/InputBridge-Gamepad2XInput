import ast
import json
import math
import os
import tempfile
import time
from pathlib import Path


PHONE_CLIENT_PATH = Path(__file__).resolve().parents[1] / "phone_client_with_auth.py"
PHONE_CLIENT_TREE = ast.parse(PHONE_CLIENT_PATH.read_text(encoding="utf-8"))
_HELPER_NAMES = {
    "MOUSE_SETTINGS_FILE",
    "DEFAULT_MOUSE_SENSITIVITY",
    "load_mouse_preferences",
    "save_mouse_preferences",
    "MouseGestureTracker",
}


def _defines_helper(node):
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        return node.name in _HELPER_NAMES
    if isinstance(node, ast.Assign):
        return any(
            isinstance(target, ast.Name) and target.id in _HELPER_NAMES
            for target in node.targets
        )
    return False


_HELPER_NODES = [
    node for node in PHONE_CLIENT_TREE.body if _defines_helper(node)
]
_HELPERS = {
    "json": json,
    "math": math,
    "os": os,
    "tempfile": tempfile,
    "time": time,
}
exec(
    compile(ast.Module(body=_HELPER_NODES, type_ignores=[]), str(PHONE_CLIENT_PATH), "exec"),
    _HELPERS,
)
DEFAULT_MOUSE_SENSITIVITY = _HELPERS["DEFAULT_MOUSE_SENSITIVITY"]
MouseGestureTracker = _HELPERS["MouseGestureTracker"]
load_mouse_preferences = _HELPERS["load_mouse_preferences"]
save_mouse_preferences = _HELPERS["save_mouse_preferences"]


def test_mouse_tracker_reports_cursor_motion_and_distinguishes_drag_from_tap():
    tracker = MouseGestureTracker(scroll_step=40, tap_slop=8, tap_timeout=0.25)

    assert tracker.begin("finger", 10, 10, now=1.0)
    assert tracker.move("finger", 14, 10, 4, 0) == ("move", 4.0, 0.0)
    assert tracker.end("finger", now=1.1)

    assert tracker.begin("finger", 10, 10, now=2.0)
    assert tracker.move("finger", 30, 10, 20, 0) == ("move", 20.0, 0.0)
    assert not tracker.end("finger", now=2.1)


def test_mouse_tracker_converts_two_finger_swipes_to_scroll_not_clicks():
    tracker = MouseGestureTracker(scroll_step=40)
    assert tracker.begin("one", 0, 100, now=1.0)
    assert tracker.begin("two", 20, 100, now=1.01)

    assert tracker.move("one", 0, 140, 0, 40) is None
    assert tracker.move("two", 20, 140, 0, 40) == ("scroll", 1)
    assert not tracker.end("one", now=1.1)
    assert not tracker.end("two", now=1.1)


def test_mouse_tracker_rejects_a_third_concurrent_touch():
    tracker = MouseGestureTracker()
    assert tracker.begin(1, 0, 0, now=1.0)
    assert tracker.begin(2, 10, 0, now=1.0)
    assert not tracker.begin(3, 20, 0, now=1.0)


def test_mouse_preferences_round_trip_and_sanitize(tmp_path):
    settings_path = tmp_path / "mouse_settings.json"
    save_mouse_preferences(2.75, False, settings_path)

    assert load_mouse_preferences(settings_path) == {
        "sensitivity": 2.75,
        "tap_to_click": False,
    }

    settings_path.write_text(
        json.dumps({"sensitivity": 500, "tap_to_click": "yes"}),
        encoding="utf-8",
    )
    assert load_mouse_preferences(settings_path) == {
        "sensitivity": 4.0,
        "tap_to_click": True,
    }

    settings_path.write_text("not json", encoding="utf-8")
    assert load_mouse_preferences(settings_path) == {
        "sensitivity": DEFAULT_MOUSE_SENSITIVITY,
        "tap_to_click": True,
    }


def test_phone_client_mouse_helpers_are_self_contained():
    assert not (PHONE_CLIENT_PATH.parent / "phone_mouse.py").exists()
    assert not any(
        isinstance(node, ast.ImportFrom) and node.module == "phone_mouse"
        for node in ast.walk(PHONE_CLIENT_TREE)
    )
