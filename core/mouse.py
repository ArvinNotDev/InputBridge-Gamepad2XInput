from __future__ import annotations

import math
import time

import pyautogui


# PyAutoGUI otherwise inserts its global PAUSE after every operation. That
# default is useful for scripts but makes a high-frequency gamepad mouse feel
# delayed and sticky.
pyautogui.PAUSE = 0.0


class MouseMotion:
    """Frame-rate independent, fractional and smoothly filtered mouse motion."""

    def __init__(self, smoothing_ms: float = 10.0):
        self.smoothing_seconds = max(0.001, float(smoothing_ms) / 1000.0)
        self.reset()

    def reset(self) -> None:
        self._last_time: float | None = None
        self._velocity_x = 0.0
        self._velocity_y = 0.0
        self._remainder_x = 0.0
        self._remainder_y = 0.0

    def update(self, target_x: float, target_y: float, now: float | None = None) -> tuple[int, int]:
        now = time.monotonic() if now is None else float(now)
        if self._last_time is None:
            dt = 1.0 / 120.0
        else:
            dt = max(0.0005, min(0.05, now - self._last_time))
        self._last_time = now

        alpha = 1.0 - math.exp(-dt / self.smoothing_seconds)
        self._velocity_x += (float(target_x) - self._velocity_x) * alpha
        self._velocity_y += (float(target_y) - self._velocity_y) * alpha

        self._remainder_x += self._velocity_x * dt
        self._remainder_y += self._velocity_y * dt

        dx = math.trunc(self._remainder_x)
        dy = math.trunc(self._remainder_y)
        self._remainder_x -= dx
        self._remainder_y -= dy
        return dx, dy


class Mouse:
    @staticmethod
    def move(x: int, y: int, duration: float = 0.0):
        pyautogui.moveTo(x, y, duration=duration)
        
    @staticmethod
    def moveRel(dx, dy, duration=0.0):
        pyautogui.moveRel(int(dx), int(dy), duration=duration)

    @staticmethod
    def leftClick():
        pyautogui.click(button="left")

    @staticmethod
    def rightClick():
        pyautogui.click(button="right")
