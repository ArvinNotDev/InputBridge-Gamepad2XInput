import tempfile
import unittest
from pathlib import Path

from core.settings import SettingsManager


class SettingsManagerTest(unittest.TestCase):
    def test_creates_default_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings_path = Path(tmp_dir) / "settings.conf"

            settings = SettingsManager(settings_path)

            self.assertTrue(settings_path.exists())
            self.assertEqual(settings.get_ui_theme(), "dark")
            self.assertEqual(settings.get_deadzones(), (0.1, 0.1))

    def test_normalizes_invalid_and_out_of_range_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings_path = Path(tmp_dir) / "settings.conf"
            settings_path.write_text(
                "\n".join(
                    [
                        "[device]",
                        "polling_rate = 0",
                        "left_stick_deadzone = 3",
                        "right_stick_deadzone = invalid",
                        "mouse_sensitivity = 99",
                        "invert_buttons = maybe",
                        "",
                        "[ui]",
                        "theme = ",
                    ]
                ),
                encoding="utf-8",
            )

            settings = SettingsManager(settings_path)

            self.assertEqual(settings.get_polling_rate(), 1.0)
            self.assertEqual(settings.get_deadzones(), (1.0, 0.1))
            self.assertEqual(settings.get_mouse_sensitivity(), 10.0)
            self.assertFalse(settings.get_button_inversion())
            self.assertEqual(settings.get_ui_theme(), "dark")

    def test_legacy_invertion_aliases_delegate_to_correct_spelling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings = SettingsManager(Path(tmp_dir) / "settings.conf")

            settings.set_joystick_invertion((True, False), (True, True))
            settings.set_button_invertion(True)

            self.assertEqual(settings.get_joystick_inversion(), ((True, False), (True, True)))
            self.assertTrue(settings.get_button_inversion())


if __name__ == "__main__":
    unittest.main()
