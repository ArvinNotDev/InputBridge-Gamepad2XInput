"""HidHide integration for InputBridge.

This module intentionally talks to HidHide through its official CLI instead of
writing HidHide's registry configuration directly.  HidHide exposes a stable
CLI for application whitelisting, device blacklisting and cloak activation.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys
try:
    import winreg
except ImportError:  # pragma: no cover - non-Windows development environments
    winreg = None  # type: ignore[assignment]
from typing import Any, Iterable


HIDHIDE_RELEASES_URL = "https://github.com/nefarius/HidHide/releases"


class HidHideError(RuntimeError):
    """Raised when HidHide cannot be queried or configured."""


@dataclass(frozen=True)
class HidHideDetection:
    installed: bool
    cli_path: Path | None = None
    version: str | None = None
    cloak_enabled: bool = False
    message: str = ""


class HidHideManager:
    """Small, conservative wrapper around HidHideCLI.exe."""

    _PATH_REGISTRY_KEYS = (
        r"SOFTWARE\Nefarius Software Solutions e.U.\Nefarius Software Solutions e.U. HidHide",
        r"SOFTWARE\Nefarius Software Solutions e.U.\HidHide",
    )

    def __init__(self) -> None:
        self._cli_path: Path | None = None
        self._enabled_by_inputbridge = False
        self._added_device_paths: set[str] = set()

    # ------------------------------------------------------------------
    # Detection / discovery
    # ------------------------------------------------------------------
    @staticmethod
    def _is_windows() -> bool:
        return sys.platform == "win32"

    @staticmethod
    def _read_registry_value(
        root: int, key_path: str, value_name: str, access: int = 0
    ) -> str | None:
        if not sys.platform == "win32" or winreg is None:
            return None

        accesses = [access]
        if access == 0:
            accesses = [0, winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY]

        for wow_flag in accesses:
            try:
                with winreg.OpenKey(root, key_path, 0, winreg.KEY_READ | wow_flag) as key:
                    value, _ = winreg.QueryValueEx(key, value_name)
                    if value is not None:
                        return str(value)
            except OSError:
                continue
        return None

    @classmethod
    def _registry_install_path(cls) -> Path | None:
        if not cls._is_windows() or winreg is None:
            return None

        # This is the documented third-party integration location.
        try:
            with winreg.OpenKey(
                winreg.HKEY_CLASSES_ROOT,
                r"SOFTWARE\Nefarius Software Solutions e.U.\Nefarius Software Solutions e.U. HidHide",
                0,
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
            ) as key:
                value, _ = winreg.QueryValueEx(key, "Path")
                path = Path(os.path.expandvars(str(value)))
                if path.exists():
                    return path
        except OSError:
            pass

        for key_path in cls._PATH_REGISTRY_KEYS:
            for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CLASSES_ROOT):
                value = cls._read_registry_value(root, key_path, "Path")
                if value:
                    path = Path(os.path.expandvars(value))
                    if path.exists():
                        return path
        return None

    @classmethod
    def _candidate_cli_paths(cls) -> Iterable[Path]:
        registry_path = cls._registry_install_path()
        if registry_path:
            yield registry_path / "HidHideCLI.exe"
            yield registry_path / "x64" / "HidHideCLI.exe"
            yield registry_path / "HidHideCLI" / "HidHideCLI.exe"
            yield registry_path / "x64" / "HidHideCLI" / "HidHideCLI.exe"

        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        roots = [Path(program_files), Path(program_files_x86)]
        relative_paths = (
            Path("Nefarius Software Solutions e.U.") / "HidHideCLI" / "HidHideCLI.exe",
            Path("Nefarius Software Solutions e.U.") / "HidHide" / "HidHideCLI.exe",
            Path("Nefarius Software Solutions e.U.") / "HidHide" / "x64" / "HidHideCLI.exe",
            Path("Nefarius Software Solutions") / "HidHideCLI" / "HidHideCLI.exe",
            Path("Nefarius Software Solutions") / "HidHide" / "x64" / "HidHideCLI.exe",
        )
        for root in roots:
            for relative in relative_paths:
                yield root / relative

    def find_cli(self) -> Path | None:
        if self._cli_path and self._cli_path.is_file():
            return self._cli_path

        for candidate in self._candidate_cli_paths():
            try:
                if candidate.is_file() and candidate.name.lower() == "hidhidecli.exe":
                    self._cli_path = candidate
                    return candidate
            except OSError:
                continue
        return None

    def detect(self) -> HidHideDetection:
        cli = self.find_cli()
        if not cli:
            return HidHideDetection(
                installed=False,
                message="HidHide was not found on this PC.",
            )

        try:
            version = self.run(["--version"], cli=cli).strip() or None
            cloak_state = self.cloak_state(cli=cli)
        except HidHideError as exc:
            return HidHideDetection(
                installed=True,
                cli_path=cli,
                message=str(exc),
            )

        return HidHideDetection(
            installed=True,
            cli_path=cli,
            version=version,
            cloak_enabled=cloak_state,
            message="HidHide detected.",
        )

    # ------------------------------------------------------------------
    # CLI helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _creationflags() -> int:
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)

    def run(self, args: list[str], *, cli: Path | None = None) -> str:
        if not self._is_windows():
            raise HidHideError("HidHide is only available on Windows.")

        executable = cli or self.find_cli()
        if not executable:
            raise HidHideError("HidHideCLI.exe could not be located.")

        try:
            completed = subprocess.run(
                [str(executable), *args],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=self._creationflags(),
                timeout=15,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise HidHideError(f"Unable to run HidHideCLI: {exc}") from exc

        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()
        if completed.returncode != 0:
            detail = stderr or stdout or f"CLI exited with code {completed.returncode}."
            raise HidHideError(detail)
        return stdout

    def cloak_state(self, *, cli: Path | None = None) -> bool:
        output = self.run(["--cloak-state"], cli=cli).lower()
        return "--cloak-on" in output or "on" in output and "off" not in output

    def whitelist_application(self, executable: str | Path | None = None) -> None:
        path = Path(executable) if executable else Path(sys.executable)
        # When frozen, sys.executable is the application's actual .exe.
        if not path.is_absolute():
            path = path.resolve()
        if not path.is_file():
            raise HidHideError(f"Application path does not exist: {path}")
        self.run(["--app-reg", str(path)])

    def list_blacklisted(self) -> list[str]:
        output = self.run(["--dev-list"])
        paths: list[str] = []
        for line in output.splitlines():
            line = line.strip()
            if line.lower().startswith("--dev-hide"):
                value = line[len("--dev-hide") :].strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                    value = value[1:-1]
                if value:
                    paths.append(value)
        return paths

    def gaming_devices(self) -> list[dict[str, Any]]:
        output = self.run(["--dev-gaming"])
        try:
            value = json.loads(output)
        except json.JSONDecodeError as exc:
            raise HidHideError(f"HidHide returned invalid device data: {exc}") from exc
        return self._flatten_device_json(value)

    @staticmethod
    def _flatten_device_json(value: Any) -> list[dict[str, Any]]:
        if isinstance(value, list):
            flattened: list[dict[str, Any]] = []
            for item in value:
                flattened.extend(HidHideManager._flatten_device_json(item))
            return flattened
        if isinstance(value, dict):
            if "devices" in value and isinstance(value["devices"], list):
                result: list[dict[str, Any]] = []
                for device in value["devices"]:
                    if isinstance(device, dict):
                        record = dict(device)
                        if "friendlyName" in value:
                            record.setdefault("friendlyName", value.get("friendlyName"))
                        result.append(record)
                return result
            if "deviceInstancePath" in value:
                return [dict(value)]
        return []

    @staticmethod
    def _norm(value: Any) -> str:
        """Normalize Windows HID identifiers.

        hidapi returns some device paths as bytes while HidHideCLI returns
        strings. Windows device identifiers are case-insensitive.
        """
        if value is None:
            return ""
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="ignore")
        return str(value).strip().replace("/", "\\").lower()

    @classmethod
    def _device_matches_hidapi(
        cls,
        hid_device: dict[str, Any],
        hidhide_device: dict[str, Any],
    ) -> bool:
        """Match one hidapi record to one HidHide record robustly."""
        hid_path = cls._norm(hid_device.get("path"))
        symbolic_link = cls._norm(hidhide_device.get("symbolicLink"))
        if hid_path and symbolic_link and hid_path == symbolic_link:
            return True

        try:
            hid_vid = int(hid_device.get("vendor_id"))
            hid_pid = int(hid_device.get("product_id"))
        except (TypeError, ValueError):
            return False

        instance_path = cls._norm(hidhide_device.get("deviceInstancePath"))
        if not instance_path:
            return False

        vid = f"vid_{hid_vid:04x}"
        pid = f"pid_{hid_pid:04x}"
        if vid not in instance_path or pid not in instance_path:
            return False

        hid_serial = cls._norm(hid_device.get("serial_number"))
        hh_serial = cls._norm(hidhide_device.get("serialNumber"))
        if hid_serial and hh_serial:
            return hid_serial == hh_serial

        return True

    def match_devices(
        self,
        hid_devices: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Return HidHide records corresponding to the supplied HIDAPI devices."""
        available = self.gaming_devices()
        matched: list[dict[str, Any]] = []
        seen: set[str] = set()

        for hid_device in hid_devices:
            for candidate in available:
                if self._device_matches_hidapi(hid_device, candidate):
                    instance = str(candidate.get("deviceInstancePath") or "").strip()
                    key = self._norm(instance)
                    if key and key not in seen:
                        seen.add(key)
                        matched.append(candidate)
                    break

        return matched

    def _match_single_device(self, hid_device: dict[str, Any]) -> dict[str, Any]:
        matches = self.match_devices([hid_device])
        if not matches:
            name = (
                hid_device.get("product_string")
                or hid_device.get("manufacturer_string")
                or "controller"
            )
            raise HidHideError(
                f"HidHide could not match the connected device: {name}."
            )
        return matches[0]

    def _blacklist_set(self) -> set[str]:
        return {self._norm(path) for path in self.list_blacklisted() if path}

    @staticmethod
    def device_label(hid_device: dict[str, Any], hidhide_device: dict[str, Any] | None = None) -> str:
        if hidhide_device:
            return str(
                hidhide_device.get("friendlyName")
                or hidhide_device.get("product")
                or hidhide_device.get("description")
                or hid_device.get("product_string")
                or "Controller"
            )
        return str(
            hid_device.get("product_string")
            or hid_device.get("manufacturer_string")
            or "Controller"
        )

    def device_state(self, hid_device: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """Resolve one HIDAPI device and return (HidHide record, hidden state)."""
        target = self._match_single_device(hid_device)
        instance = self._norm(target.get("deviceInstancePath"))
        if not instance:
            raise HidHideError("HidHide returned a controller without a device instance path.")
        return target, instance in self._blacklist_set()

    def controller_states(self, hid_devices: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        """Resolve supported HIDAPI devices into UI-friendly HidHide state records."""
        devices = list(hid_devices)
        if not devices:
            return []

        available = self.gaming_devices()
        blacklisted = self._blacklist_set()
        states: list[dict[str, Any]] = []
        seen: set[str] = set()

        for hid_device in devices:
            for candidate in available:
                if not self._device_matches_hidapi(hid_device, candidate):
                    continue

                instance = str(candidate.get("deviceInstancePath") or "").strip()
                key = self._norm(instance)
                if not key or key in seen:
                    break
                seen.add(key)

                states.append(
                    {
                        "hid": hid_device,
                        "hidhide": candidate,
                        "hidden": key in blacklisted,
                        "label": self.device_label(hid_device, candidate),
                    }
                )
                break

        return states

    def _disable_owned_cloak_if_unused(self) -> None:
        """Turn off cloak only when InputBridge owns it and no blacklist entries remain."""
        if not self._enabled_by_inputbridge:
            return
        try:
            if self.list_blacklisted():
                return
            if self.cloak_state():
                self.run(["--cloak-off"])
        finally:
            self._enabled_by_inputbridge = False

    def hide_hid_device(self, hid_device: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """Hide exactly one controller.

        Returns ``(target, added_by_inputbridge)``. If it was already hidden,
        no duplicate rule is created and it is not marked as InputBridge-owned.
        """
        target = self._match_single_device(hid_device)
        instance_path = str(target.get("deviceInstancePath") or "").strip()
        normalized = self._norm(instance_path)
        if not normalized:
            raise HidHideError("HidHide returned a controller without a device instance path.")

        self.whitelist_application()
        existing = self._blacklist_set()
        added = False

        if normalized not in existing:
            self.run(["--dev-hide", instance_path])
            self._added_device_paths.add(instance_path)
            added = True

        # InputBridge only owns the cloak if it had to enable it.
        if not self.cloak_state() and self._added_device_paths:
            self.run(["--cloak-on"])
            self._enabled_by_inputbridge = True

        return target, added

    def unhide_hid_device(self, hid_device: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """Unhide exactly one controller and return (target, was_hidden)."""
        target = self._match_single_device(hid_device)
        instance_path = str(target.get("deviceInstancePath") or "").strip()
        normalized = self._norm(instance_path)
        if not normalized:
            raise HidHideError("HidHide returned a controller without a device instance path.")

        existing = self._blacklist_set()
        was_hidden = normalized in existing

        if was_hidden:
            self.run(["--dev-unhide", instance_path])

        self._added_device_paths = {
            path for path in self._added_device_paths
            if self._norm(path) != normalized
        }

        if self._enabled_by_inputbridge and not self._added_device_paths:
            self._disable_owned_cloak_if_unused()

        return target, was_hidden

    def hide_hid_devices(self, hid_devices: Iterable[dict[str, Any]]) -> list[str]:
        """Hide all supplied controllers; returns only paths newly added by InputBridge."""
        targets = list(hid_devices)
        if not targets:
            raise HidHideError("No supported controller is currently connected.")

        added: list[str] = []
        for device in targets:
            _, was_added = self.hide_hid_device(device)
            if was_added:
                # Re-resolve to return the canonical HidHide instance path.
                target = self._match_single_device(device)
                instance = str(target.get("deviceInstancePath") or "").strip()
                if instance:
                    added.append(instance)
        return added

    def unhide_our_devices(self) -> list[str]:
        """Restore only device rules created by this InputBridge session."""
        paths = list(self._added_device_paths)
        removed: list[str] = []
        for path in paths:
            try:
                if self._norm(path) in self._blacklist_set():
                    self.run(["--dev-unhide", path])
                    removed.append(path)
            except HidHideError:
                # Keep going; one stale device entry must not block others.
                continue

        self._added_device_paths.clear()

        if self._enabled_by_inputbridge:
            self._disable_owned_cloak_if_unused()

        return removed

    def unhide_all_hid_devices(self, hid_devices: Iterable[dict[str, Any]]) -> list[str]:
        """Explicit user action: unhide only the supported controllers currently detected by InputBridge."""
        targets = self.match_devices(hid_devices)
        removed: list[str] = []
        blacklisted = self._blacklist_set()

        for target in targets:
            instance_path = str(target.get("deviceInstancePath") or "").strip()
            normalized = self._norm(instance_path)
            if not instance_path or normalized not in blacklisted:
                continue
            try:
                self.run(["--dev-unhide", instance_path])
                removed.append(instance_path)
            except HidHideError:
                continue

            self._added_device_paths = {
                path for path in self._added_device_paths
                if self._norm(path) != normalized
            }

        if self._enabled_by_inputbridge and not self._added_device_paths:
            self._disable_owned_cloak_if_unused()

        return removed

    def current_state_for(self, hid_devices: Iterable[dict[str, Any]]) -> tuple[bool, int]:
        if not self.find_cli():
            return False, 0
        try:
            if not self.cloak_state():
                return False, 0
            matches = self.match_devices(hid_devices)
            blacklisted = self._blacklist_set()
            hidden_count = sum(
                1
                for device in matches
                if self._norm(device.get("deviceInstancePath")) in blacklisted
            )
            return hidden_count > 0, hidden_count
        except HidHideError:
            return False, 0

    def toggle_for_hid_devices(
        self,
        hid_devices: Iterable[dict[str, Any]],
    ) -> tuple[bool, int]:
        """Backward-compatible bulk toggle used by older callers."""
        devices = list(hid_devices)
        if not devices:
            raise HidHideError("No supported controller is currently connected.")

        current, count = self.current_state_for(devices)
        if current:
            for device in devices:
                self.unhide_hid_device(device)
            return False, 0

        added = self.hide_hid_devices(devices)
        return True, len(added)
