"""DualSense USB/Bluetooth Lightbar output reports."""

from __future__ import annotations

import re
import threading
import zlib

import hid

from core.dualsense_output import (
    dualsense_output_lock,
    next_dualsense_bt_sequence,
)


SONY_VENDOR_ID = 0x054C
DUALSENSE_PRODUCT_IDS = (0x0CE6, 0x0DF2)  # DualSense and optional Edge support.

USB_OUTPUT_REPORT_ID = 0x02
USB_OUTPUT_REPORT_LENGTH = 63
BT_OUTPUT_REPORT_ID = 0x31
BT_OUTPUT_REPORT_LENGTH = 78
BT_OUTPUT_CRC_SEED = 0xA2

DEFAULT_LIGHTBAR_COLOR = "#8B5CF6"
CHARGING_LIGHTBAR_COLOR = (56, 189, 248)


def is_dualsense_device(vendor_id, product_id) -> bool:
    try:
        return int(vendor_id) == SONY_VENDOR_ID and int(product_id) in DUALSENSE_PRODUCT_IDS
    except (TypeError, ValueError):
        return False


def dualsense_bt_crc(report_without_crc: bytes) -> int:
    """Compute the Bluetooth output CRC; 0xA2 is not part of the HID buffer."""
    return zlib.crc32(bytes((BT_OUTPUT_CRC_SEED,)) + bytes(report_without_crc)) & 0xFFFFFFFF


def _rgb(color) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(channel))) for channel in color)


def build_usb_lightbar_report(color, enabled: bool = True) -> bytearray:
    """Build the 63-byte DualSense USB output report (report ID included)."""
    report = bytearray(USB_OUTPUT_REPORT_LENGTH)
    report[0] = USB_OUTPUT_REPORT_ID
    report[2] = 0x04  # valid_flag1: enable Lightbar color control.
    report[39] = 0x02  # valid_flag2: enable Lightbar setup control.
    report[42] = 0x01  # Lightbar on/setup value required by this report.
    report[45:48] = bytes(_rgb(color) if enabled else (0, 0, 0))
    return report


def build_bt_lightbar_report(sequence: int, color, enabled: bool = True) -> bytearray:
    """Build the 78-byte DualSense Bluetooth output report (without CRC seed)."""
    report = bytearray(BT_OUTPUT_REPORT_LENGTH)
    report[0] = BT_OUTPUT_REPORT_ID
    report[1] = (int(sequence) & 0x0F) << 4
    report[2] = 0x10
    report[4] = 0x04  # valid_flag1: enable Lightbar color control.
    report[41] = 0x02  # valid_flag2: enable Lightbar setup control.
    report[44] = 0x01  # Lightbar on/setup value required by this report.
    report[47:50] = bytes(_rgb(color) if enabled else (0, 0, 0))
    report[74:78] = dualsense_bt_crc(bytes(report[:-4])).to_bytes(4, "little")
    return report


def resolve_lightbar_color(settings: dict, battery_state=None) -> tuple[tuple[int, int, int], bool]:
    """Return the effective RGB and enabled state without altering saved color."""
    if not settings.get("enabled", False):
        return (0, 0, 0), False

    if battery_state is not None:
        percent, charging = battery_state
        if settings.get("charging_indication", False) and charging:
            return CHARGING_LIGHTBAR_COLOR, True
        if settings.get("battery_mode", False):
            percent = max(0, min(100, int(percent)))
            if percent >= 70:
                return (34, 197, 94), True       # green
            if percent >= 40:
                return (234, 179, 8), True       # yellow
            if percent >= 20:
                return (249, 115, 22), True      # orange
            return (239, 68, 68), True           # critical red

    color = str(settings.get("color", DEFAULT_LIGHTBAR_COLOR)).strip()
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        color = DEFAULT_LIGHTBAR_COLOR
    return tuple(bytes.fromhex(color[1:])), True


class DualSenseLightbar:
    """Coalescing per-controller writer; sends only changed Lightbar states."""

    def __init__(self, device_path, transport=None, controller_key=None):
        self.device_path = device_path
        self._controller_key = controller_key or device_path
        self._bluetooth = self._is_bluetooth_transport(transport, device_path)
        self._condition = threading.Condition()
        self._pending = None
        self._stopping = False
        self._device = None
        self._last_sent = None
        self._in_flight = None
        self._thread = threading.Thread(
            target=self._run,
            name="DualSenseLightbar",
            daemon=True,
        )
        self._thread.start()

    @staticmethod
    def _is_bluetooth_transport(transport, device_path) -> bool:
        if transport == 2 or str(transport) == "2":
            return True
        if transport == 1 or str(transport) == "1":
            return False
        text = str(transport or "").upper()
        if "BLUETOOTH" in text or text in {"BT", "BTH"}:
            return True
        if "USB" in text:
            return False
        path = str(device_path).upper()
        return "BTHENUM" in path or "BLUETOOTH" in path

    def set_color(self, color, enabled: bool = True) -> None:
        command = (bool(enabled), _rgb(color))
        with self._condition:
            if self._stopping:
                return
            if command == self._pending:
                return
            if command == self._last_sent and self._in_flight is None:
                self._pending = None
                return
            self._pending = command
            self._condition.notify()

    def stop(self) -> None:
        """Finish any queued update and close the handle without changing color."""
        with self._condition:
            self._stopping = True
            self._condition.notify()
        self._thread.join(timeout=1.0)
        if self._thread.is_alive():
            self._close_device()

    def _run(self) -> None:
        while True:
            with self._condition:
                while self._pending is None and not self._stopping:
                    self._condition.wait()
                if self._pending is None and self._stopping:
                    break
                command = self._pending
                self._pending = None
                self._in_flight = command

            sent = command == self._last_sent or self._send(command)
            with self._condition:
                if sent:
                    self._last_sent = command
                self._in_flight = None
        self._close_device()

    def _ensure_device(self) -> bool:
        if self._device is not None:
            return True
        try:
            device = hid.device()
            device.open_path(self.device_path)
            self._device = device
            return True
        except Exception as exc:
            print(f"[DualSenseLightbar] Failed to open device: {exc}")
            self._close_device()
            return False

    def _send(self, command) -> bool:
        enabled, color = command
        if not self._ensure_device():
            return False
        try:
            with dualsense_output_lock(self._controller_key):
                if self._bluetooth:
                    sequence = next_dualsense_bt_sequence(self._controller_key)
                    report = build_bt_lightbar_report(sequence, color, enabled)
                else:
                    report = build_usb_lightbar_report(color, enabled)
                written = self._device.write(bytes(report))
                if written is not None and written != len(report):
                    raise OSError(
                        f"Short HID output report: wrote {written} of {len(report)} bytes"
                    )
            return True
        except Exception as exc:
            print(f"[DualSenseLightbar] Output report failed: {exc}")
            self._close_device()
            return False

    def _close_device(self) -> None:
        device = self._device
        self._device = None
        if device is not None:
            try:
                device.close()
            except Exception:
                pass
