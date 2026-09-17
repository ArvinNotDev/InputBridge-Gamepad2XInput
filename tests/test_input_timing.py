from configparser import ConfigParser

from core.mouse import MouseMotion
from core.settings import SettingsManager


def test_poll_interval_uses_legacy_key_and_clamps_zero():
    settings = SettingsManager.__new__(SettingsManager)
    settings.config = ConfigParser()
    settings.config["device"] = {"polling_rate": "0"}

    assert settings.get_poll_interval_ms() == 1.0
    settings.set_poll_interval_ms(0)
    assert settings.config.get("device", "poll_interval_ms") == "1.000"
    assert not settings.config.has_option("device", "polling_rate")


def test_mouse_motion_accumulates_fractional_pixels_without_stalling():
    motion = MouseMotion(smoothing_ms=10.0)
    outputs = [motion.update(240.0, 0.0, now=i * 0.002) for i in range(1, 21)]

    assert sum(dx for dx, _ in outputs) > 0
    assert all(isinstance(dx, int) and isinstance(dy, int) for dx, dy in outputs)
