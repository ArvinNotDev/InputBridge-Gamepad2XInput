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
import re
import sys
import zipfile
from configparser import ConfigParser
from email.parser import BytesParser
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


def _normalise_distribution(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _validate_android_wheel(path: Path, expected_distribution: str, expected_version: str) -> None:
    """Reject corrupt, wrong-architecture, or mismatched Qt Android wheels early."""
    if not path.is_file():
        raise FileNotFoundError(f"Android wheel not found: {path}")
    if not path.name.lower().endswith("-android_aarch64.whl"):
        raise ValueError(f"Expected an ARM64 Android wheel, got: {path.name}")
    if not path.name.lower().startswith(f"{expected_distribution}-{expected_version}-"):
        raise ValueError(f"Expected {expected_distribution} {expected_version}, got: {path.name}")

    try:
        with zipfile.ZipFile(path) as archive:
            corrupt_member = archive.testzip()
            if corrupt_member:
                raise ValueError(f"Corrupt wheel member in {path.name}: {corrupt_member}")
            metadata_paths = [
                item for item in archive.namelist()
                if item.lower().endswith(".dist-info/metadata")
            ]
            if not metadata_paths:
                raise ValueError(f"No wheel metadata found in {path.name}")
            metadata = BytesParser().parsebytes(archive.read(metadata_paths[0]))
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Downloaded wheel is not a valid ZIP archive: {path.name}") from exc

    actual_name = _normalise_distribution(metadata.get("Name", ""))
    actual_version = metadata.get("Version", "")
    if actual_name != _normalise_distribution(expected_distribution):
        raise ValueError(
            f"Wheel distribution mismatch in {path.name}: expected {expected_distribution}, got {actual_name or 'missing'}"
        )
    if actual_version != expected_version:
        raise ValueError(
            f"Wheel version mismatch in {path.name}: expected {expected_version}, got {actual_version or 'missing'}"
        )


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
    toolkit_version = PySide6.__version__
    _validate_android_wheel(pyside_wheel, "pyside6", toolkit_version)
    _validate_android_wheel(shiboken_wheel, "shiboken6", toolkit_version)

    cache = Path.home() / ".pyside6_android_deploy"
    ndk_root = cache / "android-ndk"
    # The downloader may leave an archive or stale directory whose name
    # matches android-ndk-r*. Pick only an extracted NDK that actually contains
    # the LLVM utilities required by Qt's dependency scanner.
    ndk_candidates = []
    if ndk_root.is_dir():
        for candidate in ndk_root.glob("android-ndk-r*"):
            if not candidate.is_dir():
                continue
            readobj = list(candidate.glob("toolchains/llvm/prebuilt/*/bin/llvm-readobj"))
            clang = list(candidate.glob("toolchains/llvm/prebuilt/*/bin/clang"))
            if readobj and clang:
                ndk_candidates.append(candidate)
    sdk_path = cache / "android-sdk"
    if not ndk_candidates:
        found = ", ".join(path.name for path in ndk_root.glob("android-ndk-r*")) if ndk_root.is_dir() else "directory missing"
        raise FileNotFoundError(
            f"No extracted Android NDK with llvm-readobj and clang was found under {ndk_root}. "
            f"Entries seen: {found}. Re-run the SDK/NDK download step and remove stale archives if necessary."
        )
    if not sdk_path.is_dir():
        raise FileNotFoundError(f"Android SDK was not found under {sdk_path}")

    project_dir = Path.cwd()
    output_dir = project_dir / "dist"
    before_apks: dict[Path, tuple[int, int]] = {}
    if output_dir.is_dir():
        for apk in output_dir.rglob("*.apk"):
            if apk.is_file():
                stat = apk.stat()
                before_apks[apk.resolve()] = (stat.st_size, stat.st_mtime_ns)

    android_deploy.main(
        name="InputBridge Mobile",
        pyside_wheel=pyside_wheel,
        shiboken_wheel=shiboken_wheel,
        ndk_path=ndk_candidates[-1],
        sdk_path=sdk_path,
        config_file=project_dir / "pysidedeploy.spec",
        loglevel=logging.INFO,
        force=True,
        extra_modules_grouped="Network,Multimedia,MultimediaWidgets,Sensors",
    )

    # Some upstream deploy-tool versions log Buildozer failures and return
    # without propagating a non-zero code. Do not let CI mark that run as
    # successful unless it produced a fresh, structurally valid APK.
    apks = sorted(
        (apk for apk in output_dir.rglob("*.apk") if apk.is_file()),
        key=lambda apk: apk.stat().st_mtime_ns,
        reverse=True,
    ) if output_dir.is_dir() else []
    fresh_apks = []
    for apk in apks:
        stat = apk.stat()
        previous = before_apks.get(apk.resolve())
        if previous != (stat.st_size, stat.st_mtime_ns):
            fresh_apks.append(apk)
    if not fresh_apks:
        seen = ", ".join(str(path.relative_to(project_dir)) for path in apks) or "none"
        raise RuntimeError(
            f"Qt Android Deploy returned without producing a fresh APK under {output_dir}. "
            f"APK files found: {seen}. Check the Buildozer/python-for-android messages above; "
            "the upstream deployment tool may have logged a build error without raising it."
        )

    built_apk = fresh_apks[0]
    try:
        with zipfile.ZipFile(built_apk) as archive:
            corrupt_member = archive.testzip()
            if corrupt_member:
                raise RuntimeError(f"New APK contains a corrupt archive member: {corrupt_member}")
            if "AndroidManifest.xml" not in archive.namelist():
                raise RuntimeError(f"Output is not an Android APK (missing AndroidManifest.xml): {built_apk}")
    except zipfile.BadZipFile as exc:
        raise RuntimeError(f"Output file is not a valid APK archive: {built_apk}") from exc

    print(f"Validated Android APK: {built_apk} ({built_apk.stat().st_size} bytes)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
