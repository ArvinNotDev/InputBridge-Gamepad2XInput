"""Application paths that work both from source and from a PyInstaller build."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


APP_NAME = "InputBridge-Gamepad2XInput"


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
        return Path(sys.executable).resolve().parent
    return _source_root()


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
