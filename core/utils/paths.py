"""Application paths that work both from source and from a PyInstaller build."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


APP_NAME = "VPadConnect"
INSTALL_MARKER = "vpadconnect.installed"

# These paths contain mutable data in releases before the installer migration.
# Keep the list explicit so migration never copies application binaries or
# bundled, read-only resources out of the installation directory.
_LEGACY_DATA_PATHS = (
    Path("config/settings.conf"),
    Path("hotkeys.json"),
    Path("trusted_clients.json"),
    Path("remote_permissions.json"),
    Path("remote_security"),
    Path("profiles/user"),
    Path("profiles/GenericGamepads.json"),
    Path("logs"),
)


def _source_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resource_root() -> Path:
    """Return the read-only root containing bundled application resources."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return _source_root()


def data_root() -> Path:
    """Return the directory used for user-writable application data."""
    if getattr(sys, "frozen", False):
        executable_dir = Path(sys.executable).resolve().parent
        if (executable_dir / INSTALL_MARKER).is_file():
            local_app_data = _local_app_data_root()
            if local_app_data is not None:
                _migrate_legacy_data(executable_dir, local_app_data)
                return local_app_data
        return executable_dir
    return _source_root()


def _local_app_data_root() -> Path | None:
    """Return the current user's local application-data directory, if set."""
    import os

    base = os.environ.get("LOCALAPPDATA")
    return Path(base) / APP_NAME if base else None


def _copy_file_if_missing(source: Path, destination: Path) -> bool:
    """Copy one legacy file without replacing an existing destination."""
    import os
    import tempfile

    if destination.exists() or not source.is_file() or source.is_symlink():
        return False

    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".migrating", dir=destination.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        shutil.copy2(source, temporary)
        try:
            # A hard link creates the destination atomically and fails if a
            # concurrent app instance has already created it.
            os.link(temporary, destination)
        except FileExistsError:
            return False
        except OSError:
            # On filesystems without hard-link support, use a non-overwriting
            # rename on Windows and an exclusive create elsewhere.
            if os.name == "nt":
                try:
                    os.rename(temporary, destination)
                    return True
                except FileExistsError:
                    return False
            try:
                with destination.open("xb") as output, temporary.open("rb") as input_file:
                    shutil.copyfileobj(input_file, output)
                shutil.copystat(temporary, destination)
                return True
            except FileExistsError:
                return False
            except OSError:
                try:
                    destination.unlink()
                except OSError:
                    pass
                raise
        return True
    finally:
        try:
            temporary.unlink()
        except OSError:
            pass


def _copy_legacy_item(source: Path, destination: Path) -> None:
    """Copy a file or tree while preserving all existing destination data."""
    if source.is_symlink() or not source.exists():
        return
    if source.is_file():
        _copy_file_if_missing(source, destination)
        return
    if not source.is_dir():
        return

    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        _copy_legacy_item(item, destination / item.name)


def _migrate_legacy_data(legacy_root: Path, destination_root: Path) -> None:
    """Copy known writable data from a prior beside-the-exe layout.

    The source is intentionally retained. Existing destination files win, so
    the migration is safe to run on every launch and never overwrites settings
    or profiles already in Local AppData.
    """
    for relative_path in _LEGACY_DATA_PATHS:
        try:
            _copy_legacy_item(
                legacy_root / relative_path,
                destination_root / relative_path,
            )
        except OSError:
            # A locked or inaccessible legacy item must not stop the app from
            # starting or prevent the remaining paths from being copied.
            continue


def resource_path(*parts: str) -> Path:
    """Build a path to a bundled/read-only resource."""
    return resource_root().joinpath(*parts)


def data_path(*parts: str) -> Path:
    """Build a path to a user-writable data file."""
    return data_root().joinpath(*parts)


def resolve_data_path(path: str | Path) -> Path:
    """Resolve relative data paths against the app data directory."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else data_path(*candidate.parts)


def ensure_user_file(relative_path: str, default_resource: str | None = None) -> Path:
    """Create a writable user file from a bundled default when needed."""
    target = data_path(*Path(relative_path).parts)
    if not target.exists() and default_resource:
        source = resource_path(*Path(default_resource).parts)
        if source.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    return target
