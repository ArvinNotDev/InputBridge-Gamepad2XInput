import json
import unittest

from main import BridgeClient, normalize_fingerprint, parse_pairing_qr_payload


class FingerprintTests(unittest.TestCase):
    def test_normalizes_plain_and_colon_delimited_fingerprint(self):
        pin = "ab" * 32
        self.assertEqual(normalize_fingerprint(pin.upper()), pin)
        self.assertEqual(
            normalize_fingerprint(":".join(pin[i:i + 2] for i in range(0, 64, 2))),
            pin,
        )

    def test_rejects_short_or_invalid_fingerprint_without_silently_stripping_junk(self):
        self.assertEqual(normalize_fingerprint("AA:BB"), "")
        self.assertEqual(normalize_fingerprint(("ab" * 32) + "z"), "")
        self.assertEqual(normalize_fingerprint("ab" * 31 + "zz"), "")
        self.assertEqual(normalize_fingerprint(None), "")


class PairingPayloadTests(unittest.TestCase):
    def setUp(self):
        self.pin = "ab" * 32
        self.payload = {
            "schema": "inputbridge-pairing",
            "version": 1,
            "host": "192.168.1.25",
            "port": 5000,
            "tls_sha256": ":".join(self.pin[i:i + 2] for i in range(0, 64, 2)),
        }

    def test_accepts_desktop_pairing_payload_from_text_or_bytes(self):
        expected = {
            "host": "192.168.1.25",
            "port": "5000",
            "fingerprint": self.pin,
        }
        raw = json.dumps(self.payload)
        self.assertEqual(parse_pairing_qr_payload(raw), expected)
        self.assertEqual(parse_pairing_qr_payload(raw.encode("utf-8")), expected)

    def test_rejects_wrong_schema_or_version(self):
        for key, value in (("schema", "other"), ("version", 2), ("version", True)):
            payload = dict(self.payload)
            payload[key] = value
            with self.subTest(key=key, value=value):
                self.assertIsNone(parse_pairing_qr_payload(json.dumps(payload)))

    def test_rejects_invalid_port_and_host(self):
        for key, value in (
            ("port", 0), ("port", 65536), ("port", True),
            ("host", ""), ("host", ".pc.local"), ("host", "pc.local/evil"),
        ):
            payload = dict(self.payload)
            payload[key] = value
            with self.subTest(key=key, value=value):
                self.assertIsNone(parse_pairing_qr_payload(json.dumps(payload)))

    def test_rejects_invalid_fingerprint_json_and_oversized_payload(self):
        payload = dict(self.payload, tls_sha256="ab" * 31 + "zz")
        self.assertIsNone(parse_pairing_qr_payload(json.dumps(payload)))
        self.assertIsNone(parse_pairing_qr_payload("{not json"))
        self.assertIsNone(parse_pairing_qr_payload(b"\xff"))
        self.assertIsNone(parse_pairing_qr_payload(" " * 2049))


class ControllerStateTests(unittest.TestCase):
    def setUp(self):
        self.client = BridgeClient()

    def test_state_message_has_expected_protocol_and_neutral_axes(self):
        state = self.client.build_state_message()
        self.assertEqual(state["protocol_version"], 1)
        self.assertEqual(state["message_type"], "state")
        self.assertEqual(state["joystick"], {
            "left_x": 128, "left_y": 128, "right_x": 128, "right_y": 128,
        })
        self.assertEqual(state["analog"], {"L2": 0, "R2": 0})
        self.assertTrue(all(value == 0 for value in state["buttons"].values()))

    def test_disconnect_returns_all_controls_to_neutral(self):
        self.client.buttons["A"] = 1
        self.client.buttons["DPAD_LEFT"] = 1
        self.client.analog["L2"] = 255
        self.client.joystick.update(left_x=255, left_y=1, right_x=0, right_y=200)
        self.client.gyro_enabled = True
        self.client.gyro_neutral = 1.3
        self.client.gyro_steer = 0.9
        with self.client._mouse_lock:
            self.client._mouse_dx = 24
            self.client._mouse_dy = -7
            self.client._mouse_scroll = 4
            self.client.mouse_buttons["right"] = 1

        self.client.disconnect()

        self.assertTrue(all(value == 0 for value in self.client.buttons.values()))
        self.assertEqual(self.client.analog, {"L2": 0, "R2": 0})
        self.assertEqual(self.client.joystick, {
            "left_x": 128, "left_y": 128, "right_x": 128, "right_y": 128,
        })
        self.assertFalse(self.client.gyro_enabled)
        self.assertIsNone(self.client.gyro_neutral)
        self.assertEqual(self.client.gyro_steer, 0.0)
        with self.client._mouse_lock:
            self.assertEqual((self.client._mouse_dx, self.client._mouse_dy, self.client._mouse_scroll), (0, 0, 0))
            self.assertEqual(self.client.mouse_buttons, {"left": 0, "right": 0, "middle": 0})


if __name__ == "__main__":
    unittest.main()
