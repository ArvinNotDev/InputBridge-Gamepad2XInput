from __future__ import annotations

import configparser

from core.settings import SettingsManager


def test_reduced_motion_setting_defaults_false_and_round_trips(tmp_path):
    settings = SettingsManager.__new__(SettingsManager)
    settings.path = tmp_path / "settings.conf"
    settings.config = configparser.ConfigParser()

    assert settings.get_ui_reduced_motion() is False
    settings.set_ui_reduced_motion(True)
    assert settings.get_ui_reduced_motion() is True
    settings.save()

    restored = SettingsManager.__new__(SettingsManager)
    restored.path = settings.path
    restored.config = configparser.ConfigParser()
    restored.config.read(restored.path, encoding="utf-8")
    assert restored.get_ui_reduced_motion() is True


def test_normalize_adds_reduced_motion_to_older_settings_files(tmp_path):
    settings = SettingsManager.__new__(SettingsManager)
    settings.path = tmp_path / "settings.conf"
    settings.config = configparser.ConfigParser()
    settings.config["device"] = {}
    settings.config["ui"] = {"language": "eng", "theme": "dark"}
    settings.config["developer"] = {}

    settings.normalize()

    assert settings.config.getboolean("ui", "reduced_motion") is False
    assert settings.path.exists()


def test_mouse_deadzone_is_bounded_and_persisted(tmp_path):
    settings = SettingsManager.__new__(SettingsManager)
    settings.path = tmp_path / "settings.conf"
    settings.config = configparser.ConfigParser()
    settings.config["device"] = {}

    assert settings.get_mouse_deadzone() == 0.10
    settings.set_mouse_deadzone(0.27)
    assert settings.get_mouse_deadzone() == 0.27
    settings.set_mouse_deadzone(0.90)
    assert settings.get_mouse_deadzone() == 0.50
    settings.set_mouse_deadzone(-0.1)
    assert settings.get_mouse_deadzone() == 0.0

    settings.set_mouse_deadzone(0.22)
    settings.save()
    restored = SettingsManager.__new__(SettingsManager)
    restored.path = settings.path
    restored.config = configparser.ConfigParser()
    restored.config.read(restored.path, encoding="utf-8")
    assert restored.get_mouse_deadzone() == 0.22
