"""Asynchronous classic rumble output for a physical DualSense.

The virtual XInput controller reports vibration through the ViGEm callback.
Writing the DualSense HID output report is deliberately kept on a small,
dedicated worker so the normal HID input -> XInput path never waits for it.
"""

from __future__ import annotations

import threading
import zlib

import hid

from core.dualsense_output import (
    dualsense_output_lock,
    next_dualsense_bt_sequence,
)


SONY_VENDOR_ID = 0x054C
DUALSENSE_PRODUCT_ID = 0x0CE6

USB_OUTPUT_REPORT_ID = 0x02
USB_OUTPUT_REPORT_LENGTH = 63

BT_OUTPUT_REPORT_ID = 0x31
BT_OUTPUT_REPORT_LENGTH = 78
BT_OUTPUT_CRC_SEED = 0xA2

DUALSENSE_MOTOR_MAX = 0xFF
XINPUT_VIBRATION_MAX = 0xFFFF


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, int(value)))


def xinput_to_dualsense_intensity(value: int) -> int:
    """Convert one XInput 16-bit motor value to a DualSense byte."""
    value = _clamp(value, 0, XINPUT_VIBRATION_MAX)
    return (value * DUALSENSE_MOTOR_MAX + XINPUT_VIBRATION_MAX // 2) // XINPUT_VIBRATION_MAX


def dualsense_bt_crc(report_without_crc: bytes) -> int:
    """Return the DualSense Bluetooth output CRC."""
    return zlib.crc32(bytes((BT_OUTPUT_CRC_SEED,)) + report_without_crc) & 0xFFFFFFFF


def build_usb_report(left_motor: int, right_motor: int) -> bytearray:
    """Build the working USB classic-rumble report used by the test tool."""
    report = bytearray(USB_OUTPUT_REPORT_LENGTH)
    report[0] = USB_OUTPUT_REPORT_ID
    report[1] = 0x03
    report[3] = _clamp(right_motor, 0, DUALSENSE_MOTOR_MAX)
    report[4] = _clamp(left_motor, 0, DUALSENSE_MOTOR_MAX)
    return report


def build_bt_report(sequence: int, left_motor: int, right_motor: int) -> bytearray:
    """Build the working Bluetooth classic-rumble report used by the test tool."""
    report = bytearray(BT_OUTPUT_REPORT_LENGTH)
    report[0] = BT_OUTPUT_REPORT_ID
    report[1] = (sequence & 0x0F) << 4
    report[2] = 0x10
    report[3] = 0x03
    report[5] = _clamp(right_motor, 0, DUALSENSE_MOTOR_MAX)
    report[6] = _clamp(left_motor, 0, DUALSENSE_MOTOR_MAX)

    crc = dualsense_bt_crc(bytes(report[:-4]))
    report[-4:] = crc.to_bytes(4, "little")
    return report


class DualSenseRumble:
    """Coalescing, asynchronous DualSense rumble writer."""

    def __init__(self, device_path: str, transport=None, controller_key=None):
        self.device_path = device_path
        self._controller_key = controller_key or device_path
        self._condition = threading.Condition()
        self._pending: tuple[int, int] | None = None
        self._stopping = False
        self._device = None
        self._last_sent: tuple[int, int] | None = None
        self._bluetooth = self._is_bluetooth_transport(transport, device_path)

        self._thread = threading.Thread(
            target=self._run,
            name="DualSenseRumble",
            daemon=True,
        )
        self._thread.start()

    @staticmethod
    def _is_bluetooth_transport(transport, device_path: str) -> bool:
        # HIDAPI's hid_bus_type values are USB=1 and Bluetooth=2.
        if transport == 2 or str(transport) == "2":
            return True
        if transport == 1 or str(transport) == "1":
            return False

        transport_text = str(transport or "").upper()
        if "BLUETOOTH" in transport_text or transport_text in {"BT", "BTH"}:
            return True
        if "USB" in transport_text:
            return False

        path = str(device_path).upper()
        return "BTHENUM" in path or "BLUETOOTH" in path

    @property
    def is_bluetooth(self) -> bool:
        return self._bluetooth

    def set_xinput_vibration(self, left_motor: int, right_motor: int) -> None:
        """Queue two independent XInput 0..65535 motor values."""
        left = xinput_to_dualsense_intensity(left_motor)
        right = xinput_to_dualsense_intensity(right_motor)
        self.set_dualsense_motors(left, right)

    def set_dualsense_motors(self, left_motor: int, right_motor: int) -> None:
        """Queue two independent DualSense 0..255 motor values."""
        command = (
            _clamp(left_motor, 0, DUALSENSE_MOTOR_MAX),
            _clamp(right_motor, 0, DUALSENSE_MOTOR_MAX),
        )
        with self._condition:
            if self._stopping:
                return
            self._pending = command
            self._condition.notify()

    def stop(self) -> None:
        """Stop the writer and best-effort send a final all-off report."""
        with self._condition:
            if self._stopping:
                return
            self._stopping = True
            # Replace any queued vibration with all-off so shutdown can never
            # leave a queued non-zero command active on the controller.
            self._pending = (0, 0)
            self._condition.notify()

        self._thread.join(timeout=1.0)
        if self._thread.is_alive():
            self._close_device()

    def _run(self) -> None:
        while True:
            with self._condition:
                while self._pending is None and not self._stopping:
                    self._condition.wait()

                if self._pending is None:
                    break

                command = self._pending
                self._pending = None

            if command == self._last_sent:
                continue

            if self._send(command[0], command[1]):
                self._last_sent = command

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
            print(f"[DualSenseRumble] Failed to open device: {exc}")
            self._close_device()
            return False

    def _send(self, left_motor: int, right_motor: int) -> bool:
        if not self._ensure_device():
            return False

        try:
            # Bluetooth sequence numbers belong to the controller's shared
            # output stream, so serialize them with Lightbar reports too.
            with dualsense_output_lock(self._controller_key):
                if self._bluetooth:
                    sequence = next_dualsense_bt_sequence(self._controller_key)
                    report = build_bt_report(sequence, left_motor, right_motor)
                else:
                    report = build_usb_report(left_motor, right_motor)

                self._device.write(bytes(report))
            return True
        except Exception as exc:
            print(f"[DualSenseRumble] Output report failed: {exc}")
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
