"""Manages named user profiles that snapshot the full application settings.

Profiles are stored as individual JSON files under ``profiles/user/`` (writable
data directory).  An ``active_profile.json`` file in the same directory tracks
which profile is currently active so the app can restore it on next launch.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.utils.paths import data_path, resource_path


class ProfileManager:
    """CRUD + activation for user setting profiles."""

    _PROFILE_DIR_NAME = "profiles"
    _USER_SUBDIR = "user"
    _ACTIVE_FILE = "active_profile.json"

    def __init__(self) -> None:
        self._base_dir: Path = data_path(self._PROFILE_DIR_NAME, self._USER_SUBDIR)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._active_path: Path = self._base_dir / self._ACTIVE_FILE

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_profiles(self) -> List[str]:
        """Return sorted list of profile names."""
        names: List[str] = []
        if not self._base_dir.is_dir():
            return names
        for p in self._base_dir.iterdir():
            if p.suffix == ".json" and p.name != self._ACTIVE_FILE:
                names.append(p.stem)
        names.sort()
        return names

    def profile_exists(self, name: str) -> bool:
        return self._profile_path(name).exists()

    def load_profile(self, name: str) -> Optional[Dict]:
        """Load profile data by name. Returns *None* if not found / corrupt."""
        path = self._profile_path(name)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                return None
            return data
        except (json.JSONDecodeError, OSError):
            return None

    def save_profile(self, name: str, data: Dict) -> bool:
        """Persist *data* as a named profile. Returns True on success."""
        if not name or not name.strip():
            return False
        safe_name = self._sanitise_name(name)
        path = self._profile_path(safe_name)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
            return True
        except OSError:
            return False

    def delete_profile(self, name: str) -> bool:
        """Delete a profile by name. Returns True if removed."""
        path = self._profile_path(name)
        if not path.exists():
            return False
        try:
            path.unlink()
            # If the deleted profile was active, clear active
            if self.get_active_profile() == name:
                self.set_active_profile(None)
            return True
        except OSError:
            return False

    def rename_profile(self, old_name: str, new_name: str) -> bool:
        """Rename a profile. Returns True on success."""
        if not new_name or not new_name.strip():
            return False
        old_path = self._profile_path(old_name)
        if not old_path.exists():
            return False
        new_safe = self._sanitise_name(new_name)
        new_path = self._profile_path(new_safe)
        if new_path.exists() and old_name != new_safe:
            return False
        try:
            old_path.rename(new_path)
            # Update active reference if needed
            if self.get_active_profile() == old_name:
                self.set_active_profile(new_safe)
            return True
        except OSError:
            return False

    def get_active_profile(self) -> Optional[str]:
        """Return the name of the currently active profile (or None)."""
        if not self._active_path.exists():
            return None
        try:
            with open(self._active_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data.get("name") if isinstance(data, dict) else None
        except (json.JSONDecodeError, OSError):
            return None

    def set_active_profile(self, name: Optional[str]) -> None:
        """Mark *name* as the active profile. Pass *None* to clear."""
        payload = {"name": name, "updated_at": time.time()}
        try:
            with open(self._active_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
        except OSError:
            pass

    def create_profile_from_settings(self, name: str, settings) -> bool:
        """Snapshot the current SettingsManager state into a named profile."""
        data = self._snapshot_settings(settings)
        return self.save_profile(name, data)

    def apply_profile_to_settings(self, name: str, settings) -> bool:
        """Load a named profile and push its values into *settings*."""
        data = self.load_profile(name)
        if data is None:
            return False
        self._apply_to_settings(data, settings)
        settings.save()
        self.set_active_profile(name)
        return True

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _profile_path(self, name: str) -> Path:
        safe = self._sanitise_name(name)
        return self._base_dir / f"{safe}.json"

    @staticmethod
    def _sanitise_name(name: str) -> str:
        """Remove path separators and other unsafe characters."""
        return name.replace("/", "_").replace("\\", "_").replace("..", "_").strip()

    @staticmethod
    def _snapshot_settings(settings) -> Dict:
        """Read every setting from *settings* into a plain dict."""
        snap: Dict = {"device": {}, "ui": {}, "developer": {}, "_meta": {}}

        # Device section
        d = snap["device"]
        d["polling_rate"] = settings.get_polling_rate()
        d["auto_reconnect"] = settings.get_auto_reconnect()
        d["dpad_as_mouse"] = settings.get_dpad_as_mouse()
        left_dz, right_dz = settings.get_deadzones()
        d["left_stick_deadzone"] = left_dz
        d["right_stick_deadzone"] = right_dz
        left_inv, right_inv = settings.get_joystick_invertion()
        d["left_stick_invert_x"] = left_inv[0]
        d["left_stick_invert_y"] = left_inv[1]
        d["right_stick_invert_x"] = right_inv[0]
        d["right_stick_invert_y"] = right_inv[1]
        d["invert_buttons"] = settings.get_button_invertion()
        d["mouse_mode"] = settings.get_mouse_mode()
        d["mouse_sensitivity"] = settings.get_mouse_sensitivity()

        # UI section
        u = snap["ui"]
        u["language"] = settings.get_ui_language()
        u["theme"] = settings.get_ui_theme()

        # Developer section
        dev = snap["developer"]
        dev["debug"] = settings.get_developer_debug()
        dev["raw_hid_debug"] = settings.get_raw_hid_debug()
        dev["log_to_file"] = settings.get_log_to_file()
        dev["log_file_path"] = settings.get_log_file_path()

        # Metadata
        snap["_meta"]["created_at"] = time.time()
        snap["_meta"]["updated_at"] = time.time()

        return snap

    @staticmethod
    def _apply_to_settings(data: Dict, settings) -> None:
        """Push *data* values into *settings* (does NOT call save)."""
        d = data.get("device", {})
        if "polling_rate" in d:
            settings.set_polling_rate(d["polling_rate"])
        if "auto_reconnect" in d:
            settings.set_auto_reconnect(d["auto_reconnect"])
        if "dpad_as_mouse" in d:
            settings.set_dpad_as_mouse(d["dpad_as_mouse"])
        if "left_stick_deadzone" in d and "right_stick_deadzone" in d:
            settings.set_deadzones(d["left_stick_deadzone"], d["right_stick_deadzone"])
        if all(k in d for k in ("left_stick_invert_x", "left_stick_invert_y",
                                 "right_stick_invert_x", "right_stick_invert_y")):
            settings.set_joystick_invertion(
                (d["left_stick_invert_x"], d["left_stick_invert_y"]),
                (d["right_stick_invert_x"], d["right_stick_invert_y"]),
            )
        if "invert_buttons" in d:
            settings.set_button_invertion(d["invert_buttons"])
        if "mouse_mode" in d:
            settings.set_mouse_mode(d["mouse_mode"])
        if "mouse_sensitivity" in d:
            settings.set_mouse_sensitivity(d["mouse_sensitivity"])

        u = data.get("ui", {})
        if "language" in u:
            settings.set_ui_language(u["language"])
        if "theme" in u:
            settings.set_ui_theme(u["theme"])

        dev = data.get("developer", {})
        if "debug" in dev:
            settings.set_developer_debug(dev["debug"])
        if "raw_hid_debug" in dev:
            settings.set_raw_hid_debug(dev["raw_hid_debug"])
        if "log_to_file" in dev:
            settings.set_log_to_file(dev["log_to_file"])
        if "log_file_path" in dev:
            settings.set_log_file_path(dev["log_file_path"])
