#!/usr/bin/env python3
"""Run Qt's Android deploy tool and add application runtime dependencies.

Qt's stock deployer generates a Buildozer requirements list containing only
Python, PySide6 and Shiboken6. This client also needs NumPy + pyzbar to decode
the desktop pairing QR using the phone camera. Patch the generated spec just
before Buildozer starts, preserving Qt's generated local recipes and pinned
python-for-android commit.
"""
from __future__ import annotations

import logging
import sys
from configparser import ConfigParser
from pathlib import Path

import PySide6

script_dir = Path(PySide6.__file__).resolve().parent / "scripts"
if not (script_dir / "android_deploy.py").is_file():
    raise RuntimeError(f"Qt Android deploy script is missing from {script_dir}")
sys.path.insert(0, str(script_dir))

# Match the prerequisite check performed by Qt's console-script wrapper. The
# helper calls android_deploy.main() directly so it can patch the generated
# Buildozer config before the Android build starts.
import importlib.util
import subprocess

requirements_file = script_dir / "requirements-android.txt"
if requirements_file.is_file():
    missing = []
    for line in requirements_file.read_text(encoding="utf-8").splitlines():
        package = line.strip().split("==", 1)[0]
        if package and not package.startswith("#") and not importlib.util.find_spec(package):
            missing.append(package)
    if missing:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)])

from deploy_lib.android.buildozer import Buildozer  # noqa: E402
import android_deploy  # noqa: E402


_original_create_executable = Buildozer.create_executable


def _create_executable_with_runtime_packages(mode: str) -> None:
    spec_path = Path.cwd() / "buildozer.spec"
    if not spec_path.is_file():
        raise FileNotFoundError(f"Qt did not generate {spec_path}")

    config = ConfigParser(interpolation=None, comment_prefixes="#", strict=False, allow_no_value=True)
    with spec_path.open("r", encoding="utf-8") as handle:
        config.read_file(handle)

    if not config.has_section("app"):
        raise RuntimeError("Generated Buildozer config has no [app] section")

    requirements = [item.strip() for item in config.get("app", "requirements", fallback="").split(",") if item.strip()]
    for package in ("python3", "shiboken6", "PySide6", "numpy", "pyzbar"):
        if package.lower() not in {item.lower() for item in requirements}:
            requirements.append(package)
    config.set("app", "requirements", ",".join(requirements))

    permissions = [item.strip() for item in config.get("app", "android.permissions", fallback="").split(",") if item.strip()]
    for permission in ("android.permission.INTERNET", "android.permission.CAMERA"):
        if permission.lower() not in {item.lower() for item in permissions}:
            permissions.append(permission)
    config.set("app", "android.permissions", ",".join(permissions))

    with spec_path.open("w", encoding="utf-8") as handle:
        config.write(handle)

    print("Android runtime packages:", ",".join(requirements), flush=True)
    print("Android permissions:", ",".join(permissions), flush=True)
    _original_create_executable(mode)


Buildozer.create_executable = staticmethod(_create_executable_with_runtime_packages)


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python deploy_android.py PATH_TO_PYSIDE_WHEEL PATH_TO_SHIBOKEN_WHEEL")
    pyside_wheel, shiboken_wheel = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    if not pyside_wheel.is_file() or not shiboken_wheel.is_file():
        raise FileNotFoundError("The PySide6 and Shiboken6 Android wheels must both exist.")

    android_deploy.main(
        name="InputBridge Mobile",
        pyside_wheel=pyside_wheel,
        shiboken_wheel=shiboken_wheel,
        config_file=Path.cwd() / "pysidedeploy.spec",
        loglevel=logging.INFO,
        force=True,
        extra_modules_grouped="Network,Multimedia,MultimediaWidgets,Sensors",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
