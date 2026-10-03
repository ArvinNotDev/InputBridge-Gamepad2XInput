"""Small, UI-independent helpers for the companion phone mouse pad."""

from __future__ import annotations

import json
import math
import os
import tempfile
import time


DEFAULT_MOUSE_SENSITIVITY = 1.8
MOUSE_SETTINGS_FILE = "mouse_settings.json"


def load_mouse_preferences(path=MOUSE_SETTINGS_FILE) -> dict:
    """Load and sanitize mouse preferences, falling back safely on bad data."""
    preferences = {
        "sensitivity": DEFAULT_MOUSE_SENSITIVITY,
        "tap_to_click": True,
    }
    try:
        with open(path, "r", encoding="utf-8") as settings_file:
            stored = json.load(settings_file)
        if not isinstance(stored, dict):
            return preferences

        sensitivity = stored.get("sensitivity", preferences["sensitivity"])
        if isinstance(sensitivity, (int, float)) and not isinstance(sensitivity, bool):
            sensitivity = float(sensitivity)
            if math.isfinite(sensitivity):
                preferences["sensitivity"] = max(0.5, min(4.0, sensitivity))
        if isinstance(stored.get("tap_to_click"), bool):
            preferences["tap_to_click"] = stored["tap_to_click"]
    except (OSError, ValueError, TypeError):
        pass
    return preferences


def save_mouse_preferences(sensitivity, tap_to_click, path=MOUSE_SETTINGS_FILE) -> None:
    """Atomically persist sanitized mouse preferences."""
    sensitivity = float(sensitivity)
    if not math.isfinite(sensitivity):
        sensitivity = DEFAULT_MOUSE_SENSITIVITY
    sensitivity = max(0.5, min(4.0, sensitivity))
    directory = os.path.dirname(os.fspath(path)) or "."
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=directory,
            prefix="mouse_settings.", suffix=".tmp", delete=False,
        ) as settings_file:
            temporary_path = settings_file.name
            json.dump(
                {"sensitivity": sensitivity, "tap_to_click": bool(tap_to_click)},
                settings_file,
                indent=2,
            )
            settings_file.flush()
            os.fsync(settings_file.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except OSError:
                pass


class MouseGestureTracker:
    """Track one-finger cursor moves, two-finger scrolls, and tap gestures."""

    def __init__(self, scroll_step: float = 42.0, tap_slop: float = 10.0,
                 tap_timeout: float = 0.28):
        self.scroll_step = max(1.0, float(scroll_step))
        self.tap_slop = max(0.0, float(tap_slop))
        self.tap_timeout = max(0.0, float(tap_timeout))
        self.reset()

    def reset(self) -> None:
        self._touches = {}
        self._primary_touch = None
        self._scrolling = False
        self._scroll_remainder = 0.0

    def contains(self, touch_id) -> bool:
        return touch_id in self._touches

    def begin(self, touch_id, x: float, y: float, now: float | None = None) -> bool:
        if touch_id in self._touches or len(self._touches) >= 2:
            return False
        now = time.monotonic() if now is None else float(now)
        self._touches[touch_id] = {
            "origin": (float(x), float(y)),
            "position": (float(x), float(y)),
            "began": now,
            "moved": False,
        }
        if len(self._touches) == 1:
            self._primary_touch = touch_id
            self._scrolling = False
        else:
            self._primary_touch = None
            self._scrolling = True
            self._scroll_remainder = 0.0
            for touch in self._touches.values():
                touch["moved"] = True
        return True

    def move(self, touch_id, x: float, y: float, dx: float, dy: float):
        touch = self._touches.get(touch_id)
        if touch is None:
            return None
        x, y = float(x), float(y)
        old_x, old_y = touch["position"]
        touch["position"] = (x, y)
        origin_x, origin_y = touch["origin"]
        if math.hypot(x - origin_x, y - origin_y) > self.tap_slop:
            touch["moved"] = True

        if self._scrolling and len(self._touches) == 2:
            self._scroll_remainder += (y - old_y) / 2.0
            steps = math.trunc(self._scroll_remainder / self.scroll_step)
            if steps:
                self._scroll_remainder -= steps * self.scroll_step
                return ("scroll", steps)
            return None
        if touch_id == self._primary_touch:
            return ("move", float(dx), float(dy))
        return None

    def end(self, touch_id, now: float | None = None) -> bool:
        touch = self._touches.pop(touch_id, None)
        if touch is None:
            return False
        now = time.monotonic() if now is None else float(now)

        if self._scrolling:
            self._scroll_remainder = 0.0
            if self._touches:
                self._primary_touch = next(iter(self._touches))
                self._scrolling = False
                self._touches[self._primary_touch]["moved"] = True
            else:
                self._primary_touch = None
                self._scrolling = False
            return False

        self._primary_touch = None
        return (
            not touch["moved"]
            and now - touch["began"] <= self.tap_timeout
        )
