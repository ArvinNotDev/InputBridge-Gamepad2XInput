import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from core.utils.hotkeys import Hotkey


class HotkeyTest(unittest.TestCase):
    def test_set_and_get_hotkey(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            hotkey = Hotkey(str(Path(tmp_dir) / "hotkeys.json"))

            ok, message = hotkey.set_hotkey("10000000000000", "volume up")
            found, function, _ = hotkey.get_hotkey("10000000000000")

            self.assertTrue(ok, message)
            self.assertTrue(found)
            self.assertEqual(function, "volume up")

    def test_invalid_binary_input_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            hotkey = Hotkey(str(Path(tmp_dir) / "hotkeys.json"))

            ok, message = hotkey.set_hotkey("10x0", "volume up")
            found, function, lookup_message = hotkey.get_hotkey("10x0")

            self.assertFalse(ok)
            self.assertIn("only '0' or '1'", message)
            self.assertFalse(found)
            self.assertEqual(function, "")
            self.assertIn("only '0' or '1'", lookup_message)

    def test_reload_when_hotkey_file_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "hotkeys.json"
            hotkey = Hotkey(str(path))
            hotkey.set_hotkey("10000000000000", "volume up")

            path.write_text(json.dumps({"01000000000000": "volume mute"}), encoding="utf-8")
            future = time.time() + 2
            os.utime(path, (future, future))

            found, function, _ = hotkey.get_hotkey("01000000000000")

            self.assertTrue(found)
            self.assertEqual(function, "volume mute")


if __name__ == "__main__":
    unittest.main()
