from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def clamp(value: int | float, minimum: int | float, maximum: int | float) -> int | float:
    return max(minimum, min(maximum, value))


def scale_axis_0_255_to_x360(value: int, invert: bool = False) -> int:
    """Convert an unsigned 0-255 axis value to XInput signed 16-bit space."""
    centered = float(value) - 128.0
    normalized = -centered / 127.0 if invert else centered / 127.0
    scaled = int(round(normalized * 32767.0))
    return int(clamp(scaled, -32768, 32767))


def apply_deadzone(
    raw_x: int,
    raw_y: int,
    deadzone: float,
    inversion: tuple[bool, bool],
) -> tuple[int, int]:
    """Apply an axis deadzone and inversion before scaling to XInput space."""
    invert_x, invert_y = inversion
    threshold = clamp(float(deadzone), 0.0, 1.0) * 127

    centered_x = raw_x - 128
    centered_y = raw_y - 128

    if abs(centered_x) < threshold:
        centered_x = 0
    if abs(centered_y) < threshold:
        centered_y = 0

    return (
        scale_axis_0_255_to_x360(centered_x + 128, invert_x),
        scale_axis_0_255_to_x360(centered_y + 128, invert_y),
    )


def invert_button(button: bool, invert: bool) -> bool:
    return not button if invert else button


def read_report_byte(report: Sequence[int], index: int | None) -> int:
    if index is None or index < 0 or index >= len(report):
        return 0
    return int(report[index])


def parse_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError:
            return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_button_state(report: Sequence[int], config: Mapping[str, Any] | None) -> bool:
    """Decode a digital button from a report using a profile entry."""
    if not config:
        return False

    byte_index = config.get("index", config.get("byte"))
    value = read_report_byte(report, parse_int(byte_index, -1))

    if "mask" in config:
        value &= parse_int(config.get("mask"), 0)

    if "value" in config:
        return value == parse_int(config.get("value"))
    return value != 0


def get_dpad_from_hat(report: Sequence[int], config: Mapping[str, Any] | None) -> tuple[bool, bool, bool, bool]:
    """Decode a hat-switch DPad to up, down, left, right booleans."""
    if not config:
        return False, False, False, False

    raw_value = read_report_byte(report, parse_int(config.get("byte"), -1))
    hat_value = raw_value & parse_int(config.get("mask", 0x0F), 0x0F)

    up = hat_value in (0, 1, 7)
    down = hat_value in (3, 4, 5)
    right = hat_value in (1, 2, 3)
    left = hat_value in (5, 6, 7)

    return up, down, left, right
