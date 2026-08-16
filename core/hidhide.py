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
        return str(value or "").strip().replace("/", "\\").lower()

    @classmethod
    def _device_matches_hidapi(cls, hid_device: dict[str, Any], hidhide_device: dict[str, Any]) -> bool:
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
        if hid_serial and hh_serial and hid_serial == hh_serial:
            return True
        if hid_serial and hh_serial and hid_serial != hh_serial:
            return False

        return True

    def match_devices(self, hid_devices: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        available = self.gaming_devices()
        matched: list[dict[str, Any]] = []
        seen: set[str] = set()
        for hid_device in hid_devices:
            for candidate in available:
                if self._device_matches_hidapi(hid_device, candidate):
                    instance = str(candidate.get("deviceInstancePath") or "").strip()
                    if instance and instance.lower() not in seen:
                        seen.add(instance.lower())
                        matched.append(candidate)
                    break
        return matched

    def hide_hid_devices(self, hid_devices: Iterable[dict[str, Any]]) -> list[str]:
        targets = self.match_devices(hid_devices)
        if not targets:
            raise HidHideError(
                "No compatible connected controller could be matched by HidHide. "
                "Reconnect the controller and try again."
            )

        self.whitelist_application()

        added: list[str] = []
        existing = {path.lower() for path in self.list_blacklisted()}
        for target in targets:
            instance_path = str(target.get("deviceInstancePath") or "").strip()
            if not instance_path:
                continue
            if instance_path.lower() not in existing:
                self.run(["--dev-hide", instance_path])
                existing.add(instance_path.lower())
                added.append(instance_path)
            self._added_device_paths.add(instance_path)

        active_before = self.cloak_state()
        if not active_before:
            self.run(["--cloak-on"])
            self._enabled_by_inputbridge = True
        return added

    def unhide_our_devices(self) -> list[str]:
        paths = list(self._added_device_paths)
        removed: list[str] = []
        for path in paths:
            try:
                self.run(["--dev-unhide", path])
                removed.append(path)
            except HidHideError:
                # Keep going; one stale device entry must not block others.
                continue
        self._added_device_paths.clear()

        # Do not disable a cloak that was already active before InputBridge
        # touched HidHide.  Only restore the state we changed ourselves.
        if self._enabled_by_inputbridge:
            try:
                self.run(["--cloak-off"])
            finally:
                self._enabled_by_inputbridge = False
        return removed

    def current_state_for(self, hid_devices: Iterable[dict[str, Any]]) -> tuple[bool, int]:
        if not self.find_cli():
            return False, 0
        try:
            active = self.cloak_state()
            if not active:
                return False, 0
            matches = self.match_devices(hid_devices)
            blacklisted = {path.lower() for path in self.list_blacklisted()}
            hidden_count = sum(
                1
                for device in matches
                if str(device.get("deviceInstancePath") or "").lower() in blacklisted
            )
            return hidden_count > 0, hidden_count
        except HidHideError:
            return False, 0

    def toggle_for_hid_devices(self, hid_devices: Iterable[dict[str, Any]]) -> tuple[bool, int]:
        devices = list(hid_devices)
        if not devices:
            raise HidHideError("No supported controller is currently connected.")

        enabled, hidden_count = self.current_state_for(devices)
        if enabled:
            self.unhide_our_devices()
            return False, 0

        self.hide_hid_devices(devices)
        return True, len(self._added_device_paths)
