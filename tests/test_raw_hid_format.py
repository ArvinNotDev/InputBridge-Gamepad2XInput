from __future__ import annotations

import re

from core.raw_hid import format_raw_hid_report


def test_format_raw_hid_report_shows_timestamp_device_length_and_hex():
    line = format_raw_hid_report("DualSense", bytes([0x00, 0x0A, 0xFF]), timestamp=0)

    assert re.match(r"^\[\d{2}:\d{2}:\d{2}\.\d{3}\] RX", line)
    assert "DualSense" in line
    assert "3 B" in line
    assert line.endswith("│  00 0A FF")


def test_format_raw_hid_report_sanitizes_controller_name_and_stays_single_line():
    line = format_raw_hid_report("Pad\x1b[31m\nName", b"\x01\x02", timestamp=0)

    assert "\x1b" not in line
    assert "\n" not in line
    assert "Pad[31mName" in line


def test_format_raw_hid_report_bounds_preview_but_reports_original_length():
    line = format_raw_hid_report("HID", bytes(range(10)), timestamp=0, max_bytes=4)

    assert "10 B" in line
    assert line.endswith("│  00 01 02 03 … (+6 bytes)")


def test_format_raw_hid_report_handles_empty_packet():
    line = format_raw_hid_report("HID", b"", timestamp=0)

    assert "0 B" in line
    assert line.endswith("│  ∅")
