"""Shared sequencing and write serialization for DualSense output reports."""

from __future__ import annotations

import threading


_states_lock = threading.Lock()
_controller_states: dict[str, dict] = {}


def _state_for(controller_key) -> dict:
    key = str(controller_key).lower()
    with _states_lock:
        return _controller_states.setdefault(
            key,
            {"write_lock": threading.RLock(), "sequence": 0},
        )


def dualsense_output_lock(controller_key):
    """Serialize HID output writes from vibration and Lightbar workers."""
    return _state_for(controller_key)["write_lock"]


def next_dualsense_bt_sequence(controller_key) -> int:
    """Return the next Bluetooth sequence nibble for this controller path."""
    state = _state_for(controller_key)
    with _states_lock:
        sequence = state["sequence"]
        state["sequence"] = (sequence + 1) & 0x0F
    return sequence
