from __future__ import annotations

import configparser
from pathlib import Path
from typing import Any, Mapping


DEFAULT_SETTINGS: dict[str, dict[str, str]] = {
    "device": {
        "polling_rate": "1.0",
        "auto_reconnect": "false",
        "dpad_as_mouse": "true",
        "left_stick_deadzone": "0.100000",
        "right_stick_deadzone": "0.100000",
        "right_stick_invert_x": "false",
        "right_stick_invert_y": "false",
        "left_stick_invert_x": "false",
        "left_stick_invert_y": "true",
        "invert_buttons": "false",
        "mouse_mode": "false",
        "mouse_sensitivity": "1.000000",
    },
    "ui": {
        "language": "eng",
        "theme": "dark",
    },
    "developer": {
        "debug": "false",
        "raw_hid_debug": "false",
        "log_to_file": "false",
        "log_file_path": "logs/mapper.log",
    },
}


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


class SettingsManager:
    """Read, validate, and persist application settings."""

    DEVICE = "device"
    UI = "ui"
    DEVELOPER = "developer"

    def __init__(self, path: str | Path = "config/settings.conf") -> None:
        self.path = Path(path)
        self.config = configparser.ConfigParser()
        self._load()
        self.normalize()

    def _load(self) -> None:
        if not self.path.exists():
            self._load_defaults()
            self.save()
            return

        try:
            self.config.read(self.path, encoding="utf-8")
        except configparser.Error:
            self._load_defaults()
            self.save()

    def _load_defaults(self) -> None:
        self.config.clear()
        self.config.read_dict(DEFAULT_SETTINGS)

    def _ensure_section(self, section: str) -> None:
        if not self.config.has_section(section):
            self.config.add_section(section)

    def _ensure_defaults(self) -> None:
        for section, values in DEFAULT_SETTINGS.items():
            self._ensure_section(section)
            for key, value in values.items():
                if not self.config.has_option(section, key):
                    self.config.set(section, key, value)

    def _get_float(
        self,
        section: str,
        key: str,
        fallback: float,
        *,
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> float:
        try:
            value = self.config.getfloat(section, key, fallback=fallback)
        except ValueError:
            value = fallback

        if minimum is not None:
            value = max(minimum, value)
        if maximum is not None:
            value = min(maximum, value)
        return value

    def _set_float(self, section: str, key: str, value: float, *, precision: int = 6) -> None:
        self._ensure_section(section)
        self.config.set(section, key, f"{float(value):.{precision}f}")

    def _get_bool(self, section: str, key: str, fallback: bool) -> bool:
        try:
            return self.config.getboolean(section, key, fallback=fallback)
        except ValueError:
            return fallback

    def _set_bool(self, section: str, key: str, enabled: bool) -> None:
        self._ensure_section(section)
        self.config.set(section, key, "true" if bool(enabled) else "false")

    def _get_text(self, section: str, key: str, fallback: str) -> str:
        return self.config.get(section, key, fallback=fallback).strip() or fallback

    def _set_text(self, section: str, key: str, value: Any) -> None:
        self._ensure_section(section)
        self.config.set(section, key, str(value).strip())

    # -------- device --------
    def get_polling_rate(self) -> float:
        return self._get_float(self.DEVICE, "polling_rate", 1.0, minimum=1.0, maximum=1000.0)

    def set_polling_rate(self, value: float) -> None:
        self._set_float(self.DEVICE, "polling_rate", _clamp(float(value), 1.0, 1000.0), precision=1)

    def get_auto_reconnect(self) -> bool:
        return self._get_bool(self.DEVICE, "auto_reconnect", False)

    def set_auto_reconnect(self, enabled: bool) -> None:
        self._set_bool(self.DEVICE, "auto_reconnect", enabled)

    def get_dpad_as_mouse(self) -> bool:
        return self._get_bool(self.DEVICE, "dpad_as_mouse", True)

    def set_dpad_as_mouse(self, enabled: bool) -> None:
        self._set_bool(self.DEVICE, "dpad_as_mouse", enabled)

    def get_deadzones(self) -> tuple[float, float]:
        left = self._get_float(self.DEVICE, "left_stick_deadzone", 0.1, minimum=0.0, maximum=1.0)
        right = self._get_float(self.DEVICE, "right_stick_deadzone", 0.1, minimum=0.0, maximum=1.0)
        return left, right

    def set_deadzones(self, left: float, right: float) -> None:
        self._set_float(self.DEVICE, "left_stick_deadzone", _clamp(float(left), 0.0, 1.0))
        self._set_float(self.DEVICE, "right_stick_deadzone", _clamp(float(right), 0.0, 1.0))

    def get_joystick_inversion(self) -> tuple[tuple[bool, bool], tuple[bool, bool]]:
        left_x = self._get_bool(self.DEVICE, "left_stick_invert_x", False)
        left_y = self._get_bool(self.DEVICE, "left_stick_invert_y", True)
        right_x = self._get_bool(self.DEVICE, "right_stick_invert_x", False)
        right_y = self._get_bool(self.DEVICE, "right_stick_invert_y", False)
        return (left_x, left_y), (right_x, right_y)

    def set_joystick_inversion(self, left: tuple[bool, bool], right: tuple[bool, bool]) -> None:
        self._set_bool(self.DEVICE, "left_stick_invert_x", left[0])
        self._set_bool(self.DEVICE, "left_stick_invert_y", left[1])
        self._set_bool(self.DEVICE, "right_stick_invert_x", right[0])
        self._set_bool(self.DEVICE, "right_stick_invert_y", right[1])

    def get_joystick_invertion(self) -> tuple[tuple[bool, bool], tuple[bool, bool]]:
        return self.get_joystick_inversion()

    def set_joystick_invertion(self, left: tuple[bool, bool], right: tuple[bool, bool]) -> None:
        self.set_joystick_inversion(left, right)

    def get_button_inversion(self) -> bool:
        return self._get_bool(self.DEVICE, "invert_buttons", False)

    def set_button_inversion(self, invert: bool) -> None:
        self._set_bool(self.DEVICE, "invert_buttons", invert)

    def get_button_invertion(self) -> bool:
        return self.get_button_inversion()

    def set_button_invertion(self, invert: bool) -> None:
        self.set_button_inversion(invert)

    def get_mouse_mode(self) -> bool:
        return self._get_bool(self.DEVICE, "mouse_mode", False)

    def set_mouse_mode(self, enabled: bool) -> None:
        self._set_bool(self.DEVICE, "mouse_mode", enabled)

    def get_mouse_sensitivity(self) -> float:
        return self._get_float(self.DEVICE, "mouse_sensitivity", 1.0, minimum=0.1, maximum=10.0)

    def set_mouse_sensitivity(self, sensitivity: float) -> None:
        self._set_float(self.DEVICE, "mouse_sensitivity", _clamp(float(sensitivity), 0.1, 10.0))

    # -------- ui --------
    def get_ui_language(self) -> str:
        return self._get_text(self.UI, "language", "eng")

    def set_ui_language(self, language: str) -> None:
        self._set_text(self.UI, "language", language or "eng")

    def get_ui_theme(self) -> str:
        return self._get_text(self.UI, "theme", "dark")

    def set_ui_theme(self, theme_name: str) -> None:
        self._set_text(self.UI, "theme", theme_name or "dark")

    # -------- developer --------
    def get_developer_debug(self) -> bool:
        return self._get_bool(self.DEVELOPER, "debug", False)

    def set_developer_debug(self, enabled: bool) -> None:
        self._set_bool(self.DEVELOPER, "debug", enabled)

    def get_raw_hid_debug(self) -> bool:
        return self._get_bool(self.DEVELOPER, "raw_hid_debug", False)

    def set_raw_hid_debug(self, enabled: bool) -> None:
        self._set_bool(self.DEVELOPER, "raw_hid_debug", enabled)

    def get_log_to_file(self) -> bool:
        return self._get_bool(self.DEVELOPER, "log_to_file", False)

    def set_log_to_file(self, enabled: bool) -> None:
        self._set_bool(self.DEVELOPER, "log_to_file", enabled)

    def get_log_file_path(self) -> str:
        return self._get_text(self.DEVELOPER, "log_file_path", "logs/mapper.log")

    def set_log_file_path(self, path: str) -> None:
        self._set_text(self.DEVELOPER, "log_file_path", path or "logs/mapper.log")

    # -------- save/load --------
    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as config_file:
            self.config.write(config_file)

    def normalize(self) -> None:
        """Ensure expected keys exist and persisted values are parseable."""
        self._ensure_defaults()

        normalizers: Mapping[str, tuple[Any, ...]] = {
            "polling_rate": (self.set_polling_rate, self.get_polling_rate()),
            "auto_reconnect": (self.set_auto_reconnect, self.get_auto_reconnect()),
            "dpad_as_mouse": (self.set_dpad_as_mouse, self.get_dpad_as_mouse()),
            "mouse_mode": (self.set_mouse_mode, self.get_mouse_mode()),
            "mouse_sensitivity": (self.set_mouse_sensitivity, self.get_mouse_sensitivity()),
            "invert_buttons": (self.set_button_inversion, self.get_button_inversion()),
            "ui_language": (self.set_ui_language, self.get_ui_language()),
            "ui_theme": (self.set_ui_theme, self.get_ui_theme()),
            "developer_debug": (self.set_developer_debug, self.get_developer_debug()),
            "raw_hid_debug": (self.set_raw_hid_debug, self.get_raw_hid_debug()),
            "log_to_file": (self.set_log_to_file, self.get_log_to_file()),
            "log_file_path": (self.set_log_file_path, self.get_log_file_path()),
        }

        for setter, value in normalizers.values():
            setter(value)

        left_deadzone, right_deadzone = self.get_deadzones()
        self.set_deadzones(left_deadzone, right_deadzone)

        left_inversion, right_inversion = self.get_joystick_inversion()
        self.set_joystick_inversion(left_inversion, right_inversion)

        self.save()
