import json
import unittest

from main import normalize_fingerprint, parse_pairing_qr_payload


class PairingPayloadTests(unittest.TestCase):
    def test_accepts_desktop_pairing_payload(self):
        pin = "ab" * 32
        payload = {
            "schema": "inputbridge-pairing",
            "version": 1,
            "host": "192.168.1.25",
            "port": 5000,
            "tls_sha256": ":".join(pin[i:i+2] for i in range(0, 64, 2)),
        }
        self.assertEqual(
            parse_pairing_qr_payload(json.dumps(payload)),
            {"host": "192.168.1.25", "port": "5000", "fingerprint": pin},
        )

    def test_rejects_invalid_schema_or_port(self):
        payload = {
            "schema": "inputbridge-pairing", "version": 1,
            "host": "pc.local", "port": 0, "tls_sha256": "ab" * 32,
        }
        self.assertIsNone(parse_pairing_qr_payload(json.dumps(payload)))
        payload["port"] = 5000
        payload["schema"] = "other"
        self.assertIsNone(parse_pairing_qr_payload(json.dumps(payload)))

    def test_fingerprint_is_strict(self):
        self.assertEqual(normalize_fingerprint("AA:BB"), "")
        self.assertEqual(normalize_fingerprint("AB" * 32), "ab" * 32)


if __name__ == "__main__":
    unittest.main()
