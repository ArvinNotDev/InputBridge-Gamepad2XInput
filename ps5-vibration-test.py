"""Standalone DualSense vibration / HID report test tool.

This file intentionally does not import or modify the application's controller
mapping code.  It uses the same hidapi/PySide6 dependencies as the project and
is meant for protocol investigation only.

Important details:
* On connection, the same initialization read used by core/hid_manager.py is
  performed: get_feature_report(0x05, 65).
* The report editor includes the HID Report ID as byte 0.
* Feature Report sends use hidapi.send_feature_report().
* Output Report sends use hidapi.write(), which is the normal DualSense path.
* Bluetooth DualSense output reports include the protocol CRC32 automatically
  in the built-in Bluetooth presets.
"""

from __future__ import annotations

import sys
import time
import zlib
from dataclasses import dataclass
from typing import Any

import hid
from PySide6.QtCore import QSignalBlocker, QTimer, Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


SONY_VENDOR_ID = 0x054C
DUALSENSE_PRODUCT_ID = 0x0CE6
INITIAL_FEATURE_REPORT_ID = 0x05
INITIAL_FEATURE_REPORT_LENGTH = 65


def hex_bytes(data: bytes | bytearray | list[int]) -> str:
    return " ".join(f"{value:02X}" for value in data)


def parse_hex_bytes(text: str) -> bytearray:
    tokens = text.replace(",", " ").split()
    result = bytearray()
    for token in tokens:
        token = token.strip()
        if token.lower().startswith("0x"):
            token = token[2:]
        if not token or len(token) > 2:
            raise ValueError(f"Invalid byte: {token!r}")
        value = int(token, 16)
        if not 0 <= value <= 0xFF:
            raise ValueError(f"Byte out of range: {token!r}")
        result.append(value)
    if not result:
        raise ValueError("Report cannot be empty.")
    return result


def dualsense_bt_crc(report_without_crc: bytes) -> int:
    """Return the DualSense Bluetooth output CRC as a little-endian integer."""
    # Linux hid-playstation uses the output seed 0xA2 and a CRC32 over the
    # seed followed by the report, with the final value inverted.
    return zlib.crc32(bytes((0xA2,)) + report_without_crc) ^ 0xFFFFFFFF


@dataclass(frozen=True)
class ReportPreset:
    name: str
    report_id: int
    length: int
    bluetooth: bool
    valid_flag0: int
    valid_flag2: int = 0

    def build(self, left_motor: int, right_motor: int, report_id: int | None = None) -> bytearray:
        report = bytearray(self.length)
        report[0] = self.report_id if report_id is None else report_id

        # The common DualSense output section starts after the USB report ID,
        # or after report ID + sequence/tag on Bluetooth.
        common = 3 if self.bluetooth else 1
        if self.bluetooth:
            report[1] = 0x00  # sequence/tag nibble; changed only when needed
            report[2] = 0x10  # required Bluetooth output tag

        report[common + 0] = self.valid_flag0
        report[common + 2] = right_motor & 0xFF
        report[common + 3] = left_motor & 0xFF
        report[common + 38] = self.valid_flag2

        if self.bluetooth:
            crc = dualsense_bt_crc(bytes(report[:-4]))
            report[-4:] = crc.to_bytes(4, "little")
        return report


PRESETS = (
    ReportPreset(
        "USB classic rumble (0x02, haptics + compatible vibration)",
        report_id=0x02,
        length=63,
        bluetooth=False,
        valid_flag0=0x03,
    ),
    ReportPreset(
        "USB vibration v2 (0x02, haptics + vibration-v2 flag)",
        report_id=0x02,
        length=63,
        bluetooth=False,
        valid_flag0=0x02,
        valid_flag2=0x04,
    ),
    ReportPreset(
        "USB motor-only flag (0x02, debug variant)",
        report_id=0x02,
        length=63,
        bluetooth=False,
        valid_flag0=0x01,
    ),
    ReportPreset(
        "Bluetooth classic rumble + CRC (0x31)",
        report_id=0x31,
        length=78,
        bluetooth=True,
        valid_flag0=0x03,
    ),
    ReportPreset(
        "Bluetooth vibration v2 + CRC (0x31)",
        report_id=0x31,
        length=78,
        bluetooth=True,
        valid_flag0=0x02,
        valid_flag2=0x04,
    ),
    ReportPreset(
        "Bluetooth motor-only + CRC (0x31, debug variant)",
        report_id=0x31,
        length=78,
        bluetooth=True,
        valid_flag0=0x01,
    ),
)


class DualSenseVibrationTest(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PS5 DualSense Vibration / HID Report Test")
        self.resize(980, 760)

        self.device: Any | None = None
        self.device_info: dict[str, Any] | None = None
        self.last_sent: tuple[bytearray, str] | None = None
        self._refreshing_devices = False

        self.device_combo = QComboBox()
        self.device_combo.currentIndexChanged.connect(self._device_selection_changed)
        self.refresh_button = QPushButton("Refresh / Auto-connect")
        self.refresh_button.clicked.connect(self.refresh_devices)
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect_device)
        self.status_label = QLabel("No DualSense connected.")
        self.status_label.setWordWrap(True)

        device_row = QHBoxLayout()
        device_row.addWidget(self.device_combo, 1)
        device_row.addWidget(self.refresh_button)
        device_row.addWidget(self.disconnect_button)

        device_box = QGroupBox("DualSense device")
        device_layout = QVBoxLayout(device_box)
        device_layout.addLayout(device_row)
        device_layout.addWidget(self.status_label)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems([preset.name for preset in PRESETS])
        self.preset_combo.currentIndexChanged.connect(self.apply_selected_preset)
        self.apply_button = QPushButton("Apply preset to editor")
        self.apply_button.clicked.connect(self.apply_selected_preset)

        self.transport_combo = QComboBox()
        self.transport_combo.addItems(
            [
                "Feature Report (send_feature_report)",
                "Output Report (write; normal DualSense path)",
            ]
        )

        self.report_id = QSpinBox()
        self.report_id.setRange(0, 0xFF)
        self.report_id.setDisplayIntegerBase(16)
        self.report_id.setPrefix("0x")
        self.report_id.valueChanged.connect(self._report_id_changed)

        self.left_motor = QSpinBox()
        self.left_motor.setRange(0, 255)
        self.left_motor.setValue(255)
        self.left_motor.valueChanged.connect(self._motor_value_changed)
        self.right_motor = QSpinBox()
        self.right_motor.setRange(0, 255)
        self.right_motor.setValue(255)
        self.right_motor.valueChanged.connect(self._motor_value_changed)

        self.report_editor = QPlainTextEdit()
        self.report_editor.setPlaceholderText("Example: 02 03 00 FF FF ...")
        self.report_editor.setMinimumHeight(150)
        self.report_editor.setLineWrapMode(QPlainTextEdit.WidgetWidth)

        editor_form = QFormLayout()
        editor_form.addRow("Preset:", self.preset_combo)
        editor_form.addRow("Transport:", self.transport_combo)
        editor_form.addRow("Report ID (byte 0):", self.report_id)
        editor_form.addRow("Strong / left motor:", self.left_motor)
        editor_form.addRow("Weak / right motor:", self.right_motor)
        editor_form.addRow("Full report bytes:", self.report_editor)

        editor_box = QGroupBox("Report editor")
        editor_layout = QVBoxLayout(editor_box)
        editor_layout.addLayout(editor_form)
        editor_layout.addWidget(self.apply_button)

        self.send_current_feature_button = QPushButton("Send current as Feature Report")
        self.send_current_feature_button.clicked.connect(lambda: self.send_current("feature"))
        self.send_current_output_button = QPushButton("Send current as Output Report")
        self.send_current_output_button.clicked.connect(lambda: self.send_current("output"))
        self.on_button = QPushButton("Test vibration ON")
        self.on_button.clicked.connect(self.send_on)
        self.off_button = QPushButton("Test vibration OFF")
        self.off_button.clicked.connect(self.send_off)
        self.repeat_button = QPushButton("Repeat last exact report")
        self.repeat_button.clicked.connect(self.repeat_last)

        action_grid = QGridLayout()
        action_grid.addWidget(self.send_current_feature_button, 0, 0)
        action_grid.addWidget(self.send_current_output_button, 0, 1)
        action_grid.addWidget(self.on_button, 1, 0)
        action_grid.addWidget(self.off_button, 1, 1)
        action_grid.addWidget(self.repeat_button, 2, 0, 1, 2)

        action_box = QGroupBox("Send")
        action_layout = QVBoxLayout(action_box)
        action_layout.addLayout(action_grid)

        self.read_id = QSpinBox()
        self.read_id.setRange(0, 0xFF)
        self.read_id.setDisplayIntegerBase(16)
        self.read_id.setPrefix("0x")
        self.read_id.setValue(INITIAL_FEATURE_REPORT_ID)
        self.read_length = QSpinBox()
        self.read_length.setRange(1, 256)
        self.read_length.setValue(INITIAL_FEATURE_REPORT_LENGTH)
        self.read_button = QPushButton("Read Feature Report")
        self.read_button.clicked.connect(self.read_feature_report)

        read_form = QFormLayout()
        read_form.addRow("Feature Report ID:", self.read_id)
        read_form.addRow("Read length:", self.read_length)
        read_form.addRow(self.read_button)
        read_box = QGroupBox("Feature Report reader")
        read_layout = QVBoxLayout(read_box)
        read_layout.addLayout(read_form)
        read_layout.addWidget(
            QLabel("On first connection this automatically reproduces the project's get_feature_report(0x05, 65).")
        )

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(170)
        log_box = QGroupBox("Exact report log")
        log_layout = QVBoxLayout(log_box)
        log_layout.addWidget(self.log)

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.addWidget(device_box)
        root_layout.addWidget(editor_box)
        root_layout.addWidget(action_box)
        root_layout.addWidget(read_box)
        root_layout.addWidget(log_box, 1)
        self.setCentralWidget(root)

        self.apply_selected_preset()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_devices)
        self.refresh_timer.start(1000)
        QTimer.singleShot(0, self.refresh_devices)

    def _devices(self) -> list[dict[str, Any]]:
        devices = hid.enumerate(SONY_VENDOR_ID, DUALSENSE_PRODUCT_ID)
        return [device for device in devices if device.get("path")]

    @staticmethod
    def _device_label(device: dict[str, Any]) -> str:
        product = device.get("product_string") or "DualSense"
        path = device.get("path")
        if isinstance(path, bytes):
            path = path.decode(errors="replace")
        interface = device.get("interface_number", "?")
        return f"{product} | interface {interface} | {path}"

    def refresh_devices(self) -> None:
        if self._refreshing_devices:
            return
        self._refreshing_devices = True
        try:
            devices = self._devices()
            current_path = self.device_info.get("path") if self.device_info else None
            selected = -1
            with QSignalBlocker(self.device_combo):
                self.device_combo.clear()
                for index, device in enumerate(devices):
                    self.device_combo.addItem(self._device_label(device), device)
                    if device.get("path") == current_path:
                        selected = index
                if selected >= 0:
                    self.device_combo.setCurrentIndex(selected)

            if not devices:
                if self.device is not None:
                    self.disconnect_device()
                self.status_label.setText("No supported DualSense found (VID 0x054C, PID 0x0CE6).")
            elif self.device is None:
                self.device_combo.setCurrentIndex(0)
                self.connect_to_device(devices[0])
        except Exception as exc:
            self.status_label.setText(f"Enumeration failed: {exc}")
            self._log(f"[ERROR] Enumeration failed: {exc}")
        finally:
            self._refreshing_devices = False

    def _device_selection_changed(self, index: int) -> None:
        if self._refreshing_devices or index < 0:
            return
        device = self.device_combo.itemData(index)
        if device:
            self.connect_to_device(device)

    def connect_to_device(self, info: dict[str, Any]) -> None:
        self.disconnect_device(silent=True)
        handle = hid.device()
        try:
            handle.open_path(info["path"])
            self.device = handle
            self.device_info = info
            self.status_label.setText(f"Connected: {self._device_label(info)}")
            self._log(f"[CONNECT] {self._device_label(info)}")
            self._log(
                f"[INIT GET] Feature ID=0x{INITIAL_FEATURE_REPORT_ID:02X}, "
                f"length={INITIAL_FEATURE_REPORT_LENGTH}"
            )
            response = handle.get_feature_report(
                INITIAL_FEATURE_REPORT_ID, INITIAL_FEATURE_REPORT_LENGTH
            )
            self._log(f"[INIT RESPONSE] {hex_bytes(response)}")
            self.status_label.setText(
                f"Connected and initialized. Initial Feature Report returned {len(response)} bytes."
            )
        except Exception as exc:
            try:
                handle.close()
            except Exception:
                pass
            self.device = None
            self.device_info = None
            self.status_label.setText(f"Could not open DualSense: {exc}")
            self._log(f"[ERROR] Open/initialization failed: {exc}")

    def disconnect_device(self, silent: bool = False) -> None:
        if self.device is not None:
            try:
                self.device.close()
            except Exception as exc:
                if not silent:
                    self._log(f"[ERROR] Close failed: {exc}")
        self.device = None
        self.device_info = None
        if not silent:
            self.status_label.setText("Disconnected.")

    def _report_id_changed(self, value: int) -> None:
        try:
            data = parse_hex_bytes(self.report_editor.toPlainText())
        except ValueError:
            return
        if data:
            data[0] = value
            self.report_editor.setPlainText(hex_bytes(data))

    def _motor_value_changed(self) -> None:
        # Motor controls are used when rebuilding a selected preset.  They do
        # not silently overwrite manually edited report bytes.
        return

    def apply_selected_preset(self) -> None:
        preset = PRESETS[self.preset_combo.currentIndex()]
        with QSignalBlocker(self.report_id):
            self.report_id.setValue(preset.report_id)
        report = preset.build(
            self.left_motor.value(), self.right_motor.value(), self.report_id.value()
        )
        self.report_editor.setPlainText(hex_bytes(report))
        self._log(f"[PRESET] {preset.name} -> {hex_bytes(report)}")

    def _preset_report(self, left: int, right: int) -> bytearray:
        preset = PRESETS[self.preset_combo.currentIndex()]
        return preset.build(left, right, self.report_id.value())

    def _current_report(self) -> bytearray:
        report = parse_hex_bytes(self.report_editor.toPlainText())
        report[0] = self.report_id.value()
        return report

    def _send(self, report: bytearray, transport: str, label: str) -> bool:
        if self.device is None:
            self._log("[ERROR] No DualSense is connected.")
            QMessageBox.warning(self, "No controller", "Connect a DualSense first.")
            return False
        try:
            if transport == "feature":
                written = self.device.send_feature_report(bytes(report))
                method = "send_feature_report"
            else:
                written = self.device.write(bytes(report))
                method = "write"
            exact = bytearray(report)
            self.last_sent = (exact, transport)
            self._log(f"[{label}] {method}, returned={written}, bytes={hex_bytes(exact)}")
            return True
        except Exception as exc:
            self._log(f"[ERROR] {label} failed for bytes={hex_bytes(report)}: {exc}")
            self.status_label.setText(f"Send failed: {exc}")
            return False

    def send_current(self, transport: str) -> None:
        try:
            report = self._current_report()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid report", str(exc))
            return
        self._send(report, transport, "SEND CURRENT")

    def send_on(self) -> None:
        report = self._preset_report(self.left_motor.value(), self.right_motor.value())
        transport = "feature" if self.transport_combo.currentIndex() == 0 else "output"
        self.report_editor.setPlainText(hex_bytes(report))
        self._send(report, transport, "VIBRATION ON")

    def send_off(self) -> None:
        report = self._preset_report(0, 0)
        transport = "feature" if self.transport_combo.currentIndex() == 0 else "output"
        self.report_editor.setPlainText(hex_bytes(report))
        self._send(report, transport, "VIBRATION OFF")

    def repeat_last(self) -> None:
        if self.last_sent is None:
            self._log("[REPEAT] No report has been sent yet.")
            return
        report, transport = self.last_sent
        self._send(report, transport, "REPEAT LAST")

    def read_feature_report(self) -> None:
        if self.device is None:
            QMessageBox.warning(self, "No controller", "Connect a DualSense first.")
            return
        report_id = self.read_id.value()
        length = self.read_length.value()
        try:
            self._log(f"[GET] Feature ID=0x{report_id:02X}, length={length}")
            response = self.device.get_feature_report(report_id, length)
            self._log(f"[GET RESPONSE] {hex_bytes(response)}")
        except Exception as exc:
            self._log(f"[ERROR] Feature read failed: {exc}")

    def _log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log.appendPlainText(f"{timestamp} {message}")
        scrollbar = self.log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API name
        self.refresh_timer.stop()
        self.disconnect_device(silent=True)
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    window = DualSenseVibrationTest()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
