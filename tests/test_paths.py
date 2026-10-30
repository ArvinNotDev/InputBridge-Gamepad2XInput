from __future__ import annotations

import sys
from pathlib import Path

from core.utils import paths


def _set_installed_app(monkeypatch, install_dir: Path, app_data: Path) -> None:
    install_dir.mkdir(parents=True, exist_ok=True)
    (install_dir / paths.INSTALL_MARKER).write_text("installed\n", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(install_dir / "VPadConnect.exe"))
    monkeypatch.setenv("LOCALAPPDATA", str(app_data))


def test_installed_data_root_migrates_legacy_files_and_directories(monkeypatch, tmp_path):
    install_dir = tmp_path / "Program Files" / "VPadConnect"
    app_data = tmp_path / "Local AppData"
    _set_installed_app(monkeypatch, install_dir, app_data)

    legacy_settings = install_dir / "config" / "settings.conf"
    legacy_settings.parent.mkdir()
    legacy_settings.write_text("[ui]\ntheme = light\n", encoding="utf-8")
    legacy_profile = install_dir / "profiles" / "user" / "Racing.json"
    legacy_profile.parent.mkdir(parents=True)
    legacy_profile.write_text('{"name": "Racing"}\n', encoding="utf-8")
    legacy_key = install_dir / "remote_security" / "server.key"
    legacy_key.parent.mkdir()
    legacy_key.write_text("private key material", encoding="utf-8")
    legacy_log = install_dir / "logs" / "mapper.log"
    legacy_log.parent.mkdir()
    legacy_log.write_text("log entries", encoding="utf-8")

    expected_root = app_data / "VPadConnect"
    assert paths.data_root() == expected_root
    assert (expected_root / "config" / "settings.conf").read_text(encoding="utf-8") == (
        "[ui]\ntheme = light\n"
    )
    assert (expected_root / "profiles" / "user" / "Racing.json").is_file()
    assert (expected_root / "remote_security" / "server.key").read_text(
        encoding="utf-8"
    ) == "private key material"
    assert (expected_root / "logs" / "mapper.log").is_file()

    # The migration is repeatable and retains all source data for recovery.
    assert paths.data_root() == expected_root
    assert legacy_profile.is_file()
    assert legacy_key.is_file()


def test_migration_keeps_existing_destination_data_and_copies_nonconflicting_files(
    tmp_path,
):
    legacy = tmp_path / "legacy"
    destination = tmp_path / "new"
    (legacy / "profiles" / "user").mkdir(parents=True)
    (destination / "profiles" / "user").mkdir(parents=True)
    (legacy / "profiles" / "user" / "Default.json").write_text(
        "legacy profile", encoding="utf-8"
    )
    (legacy / "profiles" / "user" / "New.json").write_text(
        "new profile", encoding="utf-8"
    )
    (destination / "profiles" / "user" / "Default.json").write_text(
        "current profile", encoding="utf-8"
    )

    paths._migrate_legacy_data(legacy, destination)
    paths._migrate_legacy_data(legacy, destination)

    assert (destination / "profiles" / "user" / "Default.json").read_text(
        encoding="utf-8"
    ) == "current profile"
    assert (destination / "profiles" / "user" / "New.json").read_text(
        encoding="utf-8"
    ) == "new profile"
    assert (legacy / "profiles" / "user" / "Default.json").is_file()


def test_portable_frozen_build_keeps_data_beside_executable(monkeypatch, tmp_path):
    install_dir = tmp_path / "Portable VPadConnect"
    install_dir.mkdir()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(install_dir / "VPadConnect.exe"))
    monkeypatch.delenv("LOCALAPPDATA", raising=False)

    assert paths.data_root() == install_dir


def test_installed_data_root_supports_non_ascii_localappdata(monkeypatch, tmp_path):
    install_dir = tmp_path / "应用" / "VPadConnect"
    app_data = tmp_path / "使用者数据"
    _set_installed_app(monkeypatch, install_dir, app_data)

    assert paths.data_path("profiles", "user").as_posix().endswith(
        "使用者数据/VPadConnect/profiles/user"
    )
