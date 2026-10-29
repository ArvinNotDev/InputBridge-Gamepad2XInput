from __future__ import annotations

import math
import time
import threading
from collections import deque
from collections.abc import Callable

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


class MouseDeltaSmoother:
    """Spread relative mouse deltas over a few short ticks to mask packet jitter.

    This is a mouse-only worker. Gamepad and joystick input do not pass through
    it. Three weighted steps span about 8 ms and keep latency low; bursts are
    coalesced so the queue cannot grow without bound.
    """

    _WEIGHTS = (0.25, 0.5, 0.25)

    def __init__(
        self,
        move_callback: Callable[[int, int], None],
        interval_ms: float = 4.0,
        max_queued_segments: int = 9,
    ) -> None:
        self._move_callback = move_callback
        self._interval_seconds = max(0.001, float(interval_ms) / 1000.0)
        self._max_queued_segments = max(3, int(max_queued_segments))
        self._condition = threading.Condition()
        self._segments: deque[tuple[float, float]] = deque()
        self._next_tick: float | None = None
        self._fraction_x = 0.0
        self._fraction_y = 0.0
        self._closed = False
        self._worker = threading.Thread(
            target=self._run,
            name="VPadMouseMotionSmoother",
            daemon=True,
        )
        self._worker.start()

    def _append_batch(self, dx: float, dy: float) -> None:
        for weight in self._WEIGHTS:
            self._segments.append((dx * weight, dy * weight))

    def add(self, dx: int, dy: int) -> None:
        """Queue relative movement without blocking the network receiver."""
        dx, dy = int(dx), int(dy)
        if not dx and not dy:
            return
        with self._condition:
            if self._closed:
                return
            was_empty = not self._segments
            self._append_batch(dx, dy)
            if len(self._segments) > self._max_queued_segments:
                # Preserve total displacement while bounding burst latency.
                total_x = sum(segment[0] for segment in self._segments)
                total_y = sum(segment[1] for segment in self._segments)
                self._segments.clear()
                self._append_batch(total_x, total_y)
            if was_empty:
                self._next_tick = None
            self._condition.notify()

    def clear_pending(self) -> None:
        """Discard queued motion when mouse output changes or disconnects."""
        with self._condition:
            self._segments.clear()
            self._next_tick = None
            self._fraction_x = 0.0
            self._fraction_y = 0.0
            self._condition.notify_all()

    def close(self) -> None:
        """Stop the daemon worker and discard movement not yet applied."""
        with self._condition:
            self._closed = True
            self._segments.clear()
            self._next_tick = None
            self._fraction_x = 0.0
            self._fraction_y = 0.0
            self._condition.notify_all()
        if threading.current_thread() is not self._worker:
            self._worker.join(timeout=0.2)

    def _run(self) -> None:
        while True:
            with self._condition:
                while not self._closed and not self._segments:
                    self._condition.wait()
                if self._closed:
                    return

                now = time.monotonic()
                if self._next_tick is not None and now < self._next_tick:
                    self._condition.wait(timeout=self._next_tick - now)
                    continue

                step_x, step_y = self._segments.popleft()
                self._fraction_x += step_x
                self._fraction_y += step_y
                move_x = math.trunc(self._fraction_x)
                move_y = math.trunc(self._fraction_y)
                self._fraction_x -= move_x
                self._fraction_y -= move_y
                self._next_tick = (
                    time.monotonic() + self._interval_seconds
                    if self._segments
                    else None
                )

            if move_x or move_y:
                try:
                    self._move_callback(move_x, move_y)
                except Exception:
                    # A backend hiccup must not kill future mouse movement.
                    continue


class Mouse:
    @staticmethod
    def move(x: int, y: int, duration: float = 0.0):
        pyautogui.moveTo(x, y, duration=duration)
        
    @staticmethod
    def moveRel(dx, dy, duration=0.0):
        dx, dy = int(dx), int(dy)
        if not dx and not dy:
            return

        # PyAutoGUI raises FailSafeException at its emergency corner (normally
        # the top-left pixel). A relative mouse move must still be able to move
        # the cursor away from that point; otherwise remote mouse input is
        # silently ignored until a physical mouse moves it out.
        failsafe_enabled = bool(pyautogui.FAILSAFE)
        at_failsafe_point = False
        if failsafe_enabled:
            try:
                current_position = tuple(pyautogui.position())
                failsafe_points = getattr(pyautogui, "FAILSAFE_POINTS", [(0, 0)])
                at_failsafe_point = current_position in {
                    tuple(point) for point in failsafe_points
                }
            except Exception:
                at_failsafe_point = False

        if at_failsafe_point:
            # Disable the safeguard for this one relative move only, then
            # restore it even if the platform's mouse backend raises.
            try:
                pyautogui.FAILSAFE = False
                pyautogui.moveRel(dx, dy, duration=duration)
            finally:
                pyautogui.FAILSAFE = failsafe_enabled
            return

        pyautogui.moveRel(dx, dy, duration=duration)

    @staticmethod
    def leftClick():
        pyautogui.click(button="left")

    @staticmethod
    def rightClick():
        pyautogui.click(button="right")


    @staticmethod
    def buttonDown(button: str):
        pyautogui.mouseDown(button=button)

    @staticmethod
    def buttonUp(button: str):
        pyautogui.mouseUp(button=button)

    @staticmethod
    def scroll(amount: int):
        pyautogui.scroll(int(amount))
