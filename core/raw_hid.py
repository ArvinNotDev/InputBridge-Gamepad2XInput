"""Formatting helpers for human-readable raw HID diagnostics.

This module deliberately has no Qt or device dependencies so report formatting
can be regression-tested without opening the desktop UI.
"""
from __future__ import annotations

from datetime import datetime
import time

MAX_TERMINAL_REPORT_BYTES = 256


def format_raw_hid_report(
    controller_name: str,
    report: bytes | bytearray | memoryview,
    timestamp: float | None = None,
    *,
    max_bytes: int = MAX_TERMINAL_REPORT_BYTES,
) -> str:
    """Return one safe, timestamped terminal line for a raw HID report."""
    raw = bytes(report)
    stamp_value = time.time() if timestamp is None else float(timestamp)
    stamp = datetime.fromtimestamp(stamp_value).astimezone().strftime("%H:%M:%S.%f")[:-3]

    # Device names are external metadata: strip control characters and bound
    # their width so malformed names cannot inject terminal-like control codes.
    name = "".join(ch for ch in str(controller_name) if ch.isprintable()).strip()
    name = (name or "Unknown device")[:48]
    limit = max(1, min(int(max_bytes), MAX_TERMINAL_REPORT_BYTES))
    preview = " ".join(f"{byte:02X}" for byte in raw[:limit])
    if not preview:
        preview = "∅"
    if len(raw) > limit:
        preview += f" … (+{len(raw) - limit} bytes)"
    return f"[{stamp}] RX  {name}  {len(raw):>3} B  │  {preview}"
