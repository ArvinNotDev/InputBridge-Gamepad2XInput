from __future__ import annotations

import sys
import time
import zlib
from dataclasses import dataclass
from typing import Any

import hid
from PySide6.QtCore import QSignalBlocker, QTimer
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

BT_OUTPUT_REPORT_ID = 0x31
BT_OUTPUT_REPORT_LENGTH = 78
BT_OUTPUT_CRC_SEED = 0xA2

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

        try:
            value = int(token, 16)
        except ValueError as exc:
            raise ValueError(f"Invalid byte: {token!r}") from exc

        if not 0 <= value <= 0xFF:
            raise ValueError(f"Byte out of range: {token!r}")

        result.append(value)

    if not result:
        raise ValueError("Report cannot be empty.")

    return result


def dualsense_bt_crc(report_without_crc: bytes) -> int:
    """
    DualSense Bluetooth output CRC.

    CRC input:
        0xA2 + report bytes 0..73

    CRC is stored little-endian in bytes 74..77.
    """
    return zlib.crc32(
        bytes((BT_OUTPUT_CRC_SEED,)) + report_without_crc
    ) & 0xFFFFFFFF


def build_bt_report(
    sequence: int,
    valid_flag_0: int,
    valid_flag_1: int,
    right_motor: int,
    left_motor: int,
    valid_flag_2: int,
) -> bytearray:
    report = bytearray(BT_OUTPUT_REPORT_LENGTH)

    # Bluetooth report header
    report[0] = BT_OUTPUT_REPORT_ID
    report[1] = (sequence & 0x0F) << 4
    report[2] = 0x10

    # Output flags
    report[3] = valid_flag_0 & 0xFF
    report[4] = valid_flag_1 & 0xFF

    # Rumble motors
    report[5] = right_motor & 0xFF
    report[6] = left_motor & 0xFF

    # Additional output flag
    report[41] = valid_flag_2 & 0xFF

    # CRC
    crc = dualsense_bt_crc(bytes(report[:-4]))
    report[-4:] = crc.to_bytes(4, "little")

    return report


@dataclass(frozen=True)
class VibrationPreset:
    name: str
    flag0: int
    flag2: int
    right_motor: int
    left_motor: int


PRESETS = (
    VibrationPreset(
        name="Classic rumble: flag0=0x03",
        flag0=0x03,
        flag2=0x00,
        right_motor=0xFF,
        left_motor=0xFF,
    ),
    VibrationPreset(
        name="Compatible vibration only: flag0=0x01",
        flag0=0x01,
        flag2=0x00,
        right_motor=0xFF,
        left_motor=0xFF,
    ),
    VibrationPreset(
        name="Haptics only: flag0=0x02",
        flag0=0x02,
        flag2=0x00,
        right_motor=0xFF,
        left_motor=0xFF,
    ),
    VibrationPreset(
        name="Vibration + improved rumble: flag0=0x03 flag2=0x04",
        flag0=0x03,
        flag2=0x04,
        right_motor=0xFF,
        left_motor=0xFF,
    ),
    VibrationPreset(
        name="Compatible + improved rumble: flag0=0x01 flag2=0x04",
        flag0=0x01,
        flag2=0x04,
        right_motor=0xFF,
        left_motor=0xFF,
    ),
    VibrationPreset(
        name="Haptics + improved rumble: flag0=0x02 flag2=0x04",
        flag0=0x02,
        flag2=0x04,
        right_motor=0xFF,
        left_motor=0xFF,
    ),
)


class DualSenseBluetoothVibrationTest(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("DualSense Bluetooth Vibration Test")
        self.resize(1100, 900)

        self.device: Any | None = None
        self.device_info: dict[str, Any] | None = None

        self.sequence = 0
        self.last_sent: tuple[bytearray, str] | None = None

        self.refreshing_devices = False

        self.repeat_timer = QTimer(self)
        self.repeat_timer.timeout.connect(self._repeat_tick)

        self.repeat_remaining_ms = 0

        self._build_ui()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_devices)
        self.refresh_timer.start(1500)

        QTimer.singleShot(0, self.refresh_devices)

    # ================================================================
    # UI
    # ================================================================

    def _build_ui(self) -> None:
        # ------------------------------------------------------------
        # Device
        # ------------------------------------------------------------

        self.device_combo = QComboBox()
        self.device_combo.currentIndexChanged.connect(
            self._device_selection_changed
        )

        self.refresh_button = QPushButton("Refresh devices")
        self.refresh_button.clicked.connect(
            self.refresh_devices
        )

        self.open_button = QPushButton("Open selected interface")
        self.open_button.clicked.connect(
            self.open_selected_device
        )

        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(
            self.disconnect_device
        )

        self.status_label = QLabel(
            "No DualSense connected."
        )
        self.status_label.setWordWrap(True)

        self.device_details_label = QLabel(
            "Select a detected HID interface to see its details."
        )
        self.device_details_label.setWordWrap(True)

        device_row = QHBoxLayout()
        device_row.addWidget(
            self.device_combo,
            1,
        )
        device_row.addWidget(
            self.refresh_button
        )
        device_row.addWidget(
            self.open_button
        )
        device_row.addWidget(
            self.disconnect_button
        )

        device_box = QGroupBox(
            "Bluetooth DualSense"
        )

        device_layout = QVBoxLayout(
            device_box
        )

        device_layout.addLayout(
            device_row
        )

        device_layout.addWidget(
            self.status_label
        )

        device_layout.addWidget(
            self.device_details_label
        )

        # ------------------------------------------------------------
        # Preset
        # ------------------------------------------------------------

        self.preset_combo = QComboBox()

        self.preset_combo.addItems(
            [
                preset.name
                for preset in PRESETS
            ]
        )

        self.preset_combo.currentIndexChanged.connect(
            self.apply_preset
        )

        self.apply_preset_button = QPushButton(
            "Load preset"
        )

        self.apply_preset_button.clicked.connect(
            self.apply_preset
        )

        preset_row = QHBoxLayout()

        preset_row.addWidget(
            self.preset_combo,
            1
        )

        preset_row.addWidget(
            self.apply_preset_button
        )

        # ------------------------------------------------------------
        # Report controls
        # ------------------------------------------------------------

        self.sequence_spin = QSpinBox()
        self.sequence_spin.setRange(
            0,
            15,
        )
        self.sequence_spin.setValue(
            0
        )

        self.auto_sequence_button = QPushButton(
            "Auto sequence: ON"
        )

        self.auto_sequence_button.setCheckable(
            True
        )

        self.auto_sequence_button.setChecked(
            True
        )

        self.auto_sequence_button.clicked.connect(
            self._toggle_auto_sequence
        )

        sequence_row = QHBoxLayout()
        sequence_row.addWidget(
            self.sequence_spin
        )
        sequence_row.addWidget(
            self.auto_sequence_button
        )

        self.flag0_spin = QSpinBox()
        self.flag0_spin.setRange(
            0,
            255,
        )
        self.flag0_spin.setDisplayIntegerBase(
            16
        )
        self.flag0_spin.setPrefix(
            "0x"
        )
        self.flag0_spin.valueChanged.connect(
            self._fields_changed
        )

        self.flag1_spin = QSpinBox()
        self.flag1_spin.setRange(
            0,
            255,
        )
        self.flag1_spin.setDisplayIntegerBase(
            16
        )
        self.flag1_spin.setPrefix(
            "0x"
        )
        self.flag1_spin.valueChanged.connect(
            self._fields_changed
        )

        self.flag2_spin = QSpinBox()
        self.flag2_spin.setRange(
            0,
            255,
        )
        self.flag2_spin.setDisplayIntegerBase(
            16
        )
        self.flag2_spin.setPrefix(
            "0x"
        )
        self.flag2_spin.valueChanged.connect(
            self._fields_changed
        )

        self.right_motor_spin = QSpinBox()
        self.right_motor_spin.setRange(
            0,
            255,
        )
        self.right_motor_spin.setValue(
            255
        )
        self.right_motor_spin.valueChanged.connect(
            self._fields_changed
        )

        self.left_motor_spin = QSpinBox()
        self.left_motor_spin.setRange(
            0,
            255,
        )
        self.left_motor_spin.setValue(
            255
        )
        self.left_motor_spin.valueChanged.connect(
            self._fields_changed
        )

        self.repeat_interval_spin = QSpinBox()
        self.repeat_interval_spin.setRange(
            5,
            1000,
        )
        self.repeat_interval_spin.setValue(
            30
        )
        self.repeat_interval_spin.setSuffix(
            " ms"
        )

        self.repeat_duration_spin = QSpinBox()
        self.repeat_duration_spin.setRange(
            0,
            60000,
        )
        self.repeat_duration_spin.setValue(
            1000
        )
        self.repeat_duration_spin.setSuffix(
            " ms"
        )

        field_form = QFormLayout()

        field_form.addRow(
            "Sequence:",
            sequence_row
        )

        field_form.addRow(
            "valid_flag_0 (byte 3):",
            self.flag0_spin
        )

        field_form.addRow(
            "valid_flag_1 (byte 4):",
            self.flag1_spin
        )

        field_form.addRow(
            "Right motor (byte 5):",
            self.right_motor_spin
        )

        field_form.addRow(
            "Left motor (byte 6):",
            self.left_motor_spin
        )

        field_form.addRow(
            "valid_flag_2 (byte 41):",
            self.flag2_spin
        )

        field_form.addRow(
            "Repeat interval:",
            self.repeat_interval_spin
        )

        field_form.addRow(
            "Repeat duration:",
            self.repeat_duration_spin
        )

        report_box = QGroupBox(
            "Bluetooth 0x31 report controls"
        )

        report_layout = QVBoxLayout(
            report_box
        )

        report_layout.addLayout(
            preset_row
        )

        report_layout.addLayout(
            field_form
        )

        # ------------------------------------------------------------
        # Hex editor
        # ------------------------------------------------------------

        self.report_editor = QPlainTextEdit()

        self.report_editor.setMinimumHeight(
            210
        )

        self.report_editor.setPlaceholderText(
            "78 bytes:\n"
            "31 00 10 03 00 FF FF 00 00 ..."
        )

        self.rebuild_button = QPushButton(
            "Rebuild from fields"
        )

        self.rebuild_button.clicked.connect(
            self.rebuild_report
        )

        self.send_raw_button = QPushButton(
            "Send current raw report"
        )

        self.send_raw_button.clicked.connect(
            self.send_current_raw
        )

        hex_row = QHBoxLayout()

        hex_row.addWidget(
            self.rebuild_button
        )

        hex_row.addWidget(
            self.send_raw_button
        )

        hex_box = QGroupBox(
            "Exact 78-byte Bluetooth report"
        )

        hex_layout = QVBoxLayout(
            hex_box
        )

        hex_layout.addWidget(
            self.report_editor
        )

        hex_layout.addLayout(
            hex_row
        )

        # ------------------------------------------------------------
        # Actions
        # ------------------------------------------------------------

        self.on_button = QPushButton(
            "VIBRATION ON"
        )

        self.on_button.clicked.connect(
            self.vibration_on
        )

        self.off_button = QPushButton(
            "VIBRATION OFF"
        )

        self.off_button.clicked.connect(
            self.vibration_off
        )

        self.repeat_on_button = QPushButton(
            "ON + repeat"
        )

        self.repeat_on_button.clicked.connect(
            self.vibration_on_repeat
        )

        self.stop_repeat_button = QPushButton(
            "Stop repeat"
        )

        self.stop_repeat_button.clicked.connect(
            self.stop_repeat
        )

        self.repeat_test_button = QPushButton(
            "Repeat last exact report"
        )

        self.repeat_test_button.clicked.connect(
            self.repeat_last
        )

        action_grid = QGridLayout()

        action_grid.addWidget(
            self.on_button,
            0,
            0
        )

        action_grid.addWidget(
            self.off_button,
            0,
            1
        )

        action_grid.addWidget(
            self.repeat_on_button,
            1,
            0
        )

        action_grid.addWidget(
            self.stop_repeat_button,
            1,
            1
        )

        action_grid.addWidget(
            self.repeat_test_button,
            2,
            0,
            1,
            2
        )

        action_box = QGroupBox(
            "Vibration actions"
        )

        action_layout = QVBoxLayout(
            action_box
        )

        action_layout.addLayout(
            action_grid
        )

        # ------------------------------------------------------------
        # Discovery
        # ------------------------------------------------------------

        self.single_flag_sweep_button = QPushButton(
            "Test flag0 0x01 / 0x02 / 0x03"
        )

        self.single_flag_sweep_button.clicked.connect(
            self.single_flag_sweep
        )

        self.flag_sweep_button = QPushButton(
            "Test vibration flag combinations"
        )

        self.flag_sweep_button.clicked.connect(
            self.flag_sweep
        )

        sweep_label = QLabel(
            "Tests likely vibration-related flags while keeping "
            "the motors at the selected values."
        )

        sweep_label.setWordWrap(
            True
        )

        sweep_box = QGroupBox(
            "Vibration discovery"
        )

        sweep_layout = QVBoxLayout(
            sweep_box
        )

        sweep_layout.addWidget(
            sweep_label
        )

        sweep_layout.addWidget(
            self.single_flag_sweep_button
        )

        sweep_layout.addWidget(
            self.flag_sweep_button
        )

        # ------------------------------------------------------------
        # Feature reports
        # ------------------------------------------------------------

        self.feature_id_spin = QSpinBox()
        self.feature_id_spin.setRange(
            0,
            255
        )
        self.feature_id_spin.setDisplayIntegerBase(
            16
        )
        self.feature_id_spin.setPrefix(
            "0x"
        )
        self.feature_id_spin.setValue(
            INITIAL_FEATURE_REPORT_ID
        )

        self.feature_length_spin = QSpinBox()
        self.feature_length_spin.setRange(
            1,
            256
        )
        self.feature_length_spin.setValue(
            INITIAL_FEATURE_REPORT_LENGTH
        )

        self.read_feature_button = QPushButton(
            "Read Feature Report"
        )

        self.read_feature_button.clicked.connect(
            self.read_feature_report
        )

        feature_form = QFormLayout()

        feature_form.addRow(
            "Feature Report ID:",
            self.feature_id_spin
        )

        feature_form.addRow(
            "Read length:",
            self.feature_length_spin
        )

        feature_box = QGroupBox(
            "Feature Report reader"
        )

        feature_layout = QVBoxLayout(
            feature_box
        )

        feature_layout.addLayout(
            feature_form
        )

        feature_layout.addWidget(
            self.read_feature_button
        )

        feature_note = QLabel(
            "The existing project initialization read "
            "0x05 / 65 bytes is performed automatically "
            "when the controller connects."
        )

        feature_note.setWordWrap(
            True
        )

        feature_layout.addWidget(
            feature_note
        )

        # ------------------------------------------------------------
        # Manual byte editor
        # ------------------------------------------------------------

        self.byte_index_spin = QSpinBox()
        self.byte_index_spin.setRange(
            0,
            BT_OUTPUT_REPORT_LENGTH - 1
        )

        self.byte_value_spin = QSpinBox()
        self.byte_value_spin.setRange(
            0,
            255
        )
        self.byte_value_spin.setDisplayIntegerBase(
            16
        )
        self.byte_value_spin.setPrefix(
            "0x"
        )

        self.set_byte_button = QPushButton(
            "Change byte"
        )

        self.set_byte_button.clicked.connect(
            self.set_byte
        )

        byte_form = QFormLayout()

        byte_form.addRow(
            "Byte index:",
            self.byte_index_spin
        )

        byte_form.addRow(
            "New value:",
            self.byte_value_spin
        )

        byte_box = QGroupBox(
            "Manual byte experiment"
        )

        byte_layout = QVBoxLayout(
            byte_box
        )

        byte_layout.addLayout(
            byte_form
        )

        byte_layout.addWidget(
            self.set_byte_button
        )

        # ------------------------------------------------------------
        # Log
        # ------------------------------------------------------------

        self.log = QPlainTextEdit()
        self.log.setReadOnly(
            True
        )
        self.log.setMinimumHeight(
            220
        )

        log_box = QGroupBox(
            "Exact send / receive log"
        )

        log_layout = QVBoxLayout(
            log_box
        )

        log_layout.addWidget(
            self.log
        )

        # ------------------------------------------------------------
        # Root
        # ------------------------------------------------------------

        root = QWidget()

        root_layout = QVBoxLayout(
            root
        )

        root_layout.addWidget(
            device_box
        )

        root_layout.addWidget(
            report_box
        )

        root_layout.addWidget(
            hex_box
        )

        root_layout.addWidget(
            action_box
        )

        root_layout.addWidget(
            sweep_box
        )

        root_layout.addWidget(
            feature_box
        )

        root_layout.addWidget(
            byte_box
        )

        root_layout.addWidget(
            log_box,
            1
        )

        self.setCentralWidget(
            root
        )

        self._load_preset_into_fields(
            PRESETS[0]
        )

        self.rebuild_report()

    # ================================================================
    # Device
    # ================================================================

    def _devices(self) -> list[dict[str, Any]]:
        devices = hid.enumerate(
            SONY_VENDOR_ID,
            DUALSENSE_PRODUCT_ID,
        )

        return [
            device
            for device in devices
            if device.get("path")
        ]

    @staticmethod
    def _device_path_text(
        device: dict[str, Any]
    ) -> str:
        path = device.get(
            "path",
            ""
        )

        if isinstance(path, bytes):
            return path.decode(
                errors="replace"
            )

        return str(path)

    @classmethod
    def _device_label(
        cls,
        device: dict[str, Any]
    ) -> str:
        product = (
            device.get(
                "product_string"
            )
            or "DualSense"
        )

        vendor_id = device.get("vendor_id")
        product_id = device.get("product_id")
        interface = device.get("interface_number", "not provided")
        usage_page = device.get("usage_page", "not provided")
        usage = device.get("usage", "not provided")
        transport = device.get("transport") or "not provided by HIDAPI"

        def hex_value(value: Any) -> str:
            try:
                return f"0x{int(value):04X}"
            except (TypeError, ValueError):
                return "not provided"

        return (
            f"{product} | "
            f"VID {hex_value(vendor_id)} | "
            f"PID {hex_value(product_id)} | "
            f"interface {interface} | "
            f"usage page {hex_value(usage_page)} | "
            f"usage {hex_value(usage)} | "
            f"transport {transport} | "
            f"path {cls._device_path_text(device)}"
        )

    def refresh_devices(self) -> None:
        if self.refreshing_devices:
            return

        self.refreshing_devices = True

        try:
            devices = self._devices()

            current_path = (
                self.device_info.get(
                    "path"
                )
                if self.device_info
                else None
            )

            selected_index = -1

            with QSignalBlocker(
                self.device_combo
            ):
                self.device_combo.clear()

                for index, device in enumerate(
                    devices
                ):
                    self.device_combo.addItem(
                        self._device_label(
                            device
                        ),
                        device
                    )

                    if (
                        device.get("path")
                        == current_path
                    ):
                        selected_index = index

                if selected_index >= 0:
                    self.device_combo.setCurrentIndex(
                        selected_index
                    )

            if not devices:
                self.disconnect_device(
                    silent=True
                )

                self.status_label.setText(
                    "No DualSense HID interface found "
                    f"for VID 0x{SONY_VENDOR_ID:04X}, "
                    f"PID 0x{DUALSENSE_PRODUCT_ID:04X}."
                )

                self.device_details_label.setText(
                    "No matching HID interface detected."
                )

            elif self.device is None:
                if selected_index < 0:
                    with QSignalBlocker(
                        self.device_combo
                    ):
                        self.device_combo.setCurrentIndex(
                            0
                        )

                selected_info = self.device_combo.itemData(
                    self.device_combo.currentIndex()
                )

                if selected_info:
                    self.device_details_label.setText(
                        self._device_label(selected_info)
                    )

                if len(devices) == 1:
                    self.connect_to_device(
                        devices[0]
                    )
                else:
                    self.status_label.setText(
                        f"{len(devices)} matching DualSense HID interfaces found. "
                        "Select the intended interface and click "
                        "Open selected interface."
                    )

        except Exception as exc:
            self._log(
                f"[ERROR] Enumeration failed: {exc}"
            )

            self.status_label.setText(
                f"Enumeration failed: {exc}"
            )

        finally:
            self.refreshing_devices = False

    def _device_selection_changed(
        self,
        index: int
    ) -> None:
        if self.refreshing_devices:
            return

        if index < 0:
            return

        info = self.device_combo.itemData(
            index
        )

        if info:
            self.device_details_label.setText(
                self._device_label(info)
            )

            if self.device is None:
                self.status_label.setText(
                    "Interface selected. Click Open selected interface "
                    "to connect to this HID path."
                )

    def open_selected_device(self) -> None:
        index = self.device_combo.currentIndex()

        if index < 0:
            QMessageBox.warning(
                self,
                "No interface selected",
                "Refresh the device list and select a DualSense HID interface first.",
            )
            return

        info = self.device_combo.itemData(index)

        if info:
            self.connect_to_device(info)

    def connect_to_device(
        self,
        info: dict[str, Any]
    ) -> None:
        self.disconnect_device(
            silent=True
        )

        handle = hid.device()

        try:
            self._log(
                "[OPEN] "
                f"interface={info.get('interface_number', 'not provided')}, "
                f"path={self._device_path_text(info)}"
            )

            handle.open_path(
                info["path"]
            )

            self.device = handle
            self.device_info = info

            self.status_label.setText(
                "Connected to DualSense.\n"
                + self._device_label(
                    info
                )
            )

            self._log(
                f"[OPENED] {self._device_label(info)}"
            )

            # Existing project initialization read.
            self._log(
                "[INIT GET] "
                f"Feature ID=0x"
                f"{INITIAL_FEATURE_REPORT_ID:02X}, "
                f"length={INITIAL_FEATURE_REPORT_LENGTH}"
            )

            response = handle.get_feature_report(
                INITIAL_FEATURE_REPORT_ID,
                INITIAL_FEATURE_REPORT_LENGTH,
            )

            self._log(
                "[INIT RESPONSE] "
                + hex_bytes(response)
            )

        except Exception as exc:
            try:
                handle.close()
            except Exception:
                pass

            self.device = None
            self.device_info = None

            self.status_label.setText(
                f"Could not open DualSense: {exc}"
            )

            self._log(
                f"[ERROR] Open failed: {exc}"
            )

    def disconnect_device(
        self,
        silent: bool = False
    ) -> None:
        self.stop_repeat()

        if self.device is not None:
            try:
                self.device.close()
            except Exception as exc:
                if not silent:
                    self._log(
                        f"[ERROR] Close failed: {exc}"
                    )

        self.device = None
        self.device_info = None

        if not silent:
            self.status_label.setText(
                "Disconnected."
            )

    # ================================================================
    # Presets
    # ================================================================

    def _load_preset_into_fields(
        self,
        preset: VibrationPreset
    ) -> None:
        with QSignalBlocker(
            self.flag0_spin
        ):
            self.flag0_spin.setValue(
                preset.flag0
            )

        with QSignalBlocker(
            self.flag1_spin
        ):
            self.flag1_spin.setValue(
                0
            )

        with QSignalBlocker(
            self.flag2_spin
        ):
            self.flag2_spin.setValue(
                preset.flag2
            )

        with QSignalBlocker(
            self.right_motor_spin
        ):
            self.right_motor_spin.setValue(
                preset.right_motor
            )

        with QSignalBlocker(
            self.left_motor_spin
        ):
            self.left_motor_spin.setValue(
                preset.left_motor
            )

    def apply_preset(self) -> None:
        index = self.preset_combo.currentIndex()

        if index < 0:
            return

        preset = PRESETS[index]

        self._load_preset_into_fields(
            preset
        )

        self.rebuild_report()

        self._log(
            f"[PRESET] {preset.name}"
        )

    # ================================================================
    # Report creation
    # ================================================================

    def _current_fields_report(
        self,
        advance_sequence: bool = False
    ) -> bytearray:
        sequence = self.sequence_spin.value()

        report = build_bt_report(
            sequence=sequence,
            valid_flag_0=self.flag0_spin.value(),
            valid_flag_1=self.flag1_spin.value(),
            right_motor=self.right_motor_spin.value(),
            left_motor=self.left_motor_spin.value(),
            valid_flag_2=self.flag2_spin.value(),
        )

        if (
            advance_sequence
            and self.auto_sequence_button.isChecked()
        ):
            next_sequence = (
                sequence + 1
            ) & 0x0F

            self.sequence = next_sequence

            with QSignalBlocker(
                self.sequence_spin
            ):
                self.sequence_spin.setValue(
                    next_sequence
                )

        return report

    def rebuild_report(self) -> None:
        report = self._current_fields_report()

        self.report_editor.setPlainText(
            hex_bytes(report)
        )

    def _fields_changed(self) -> None:
        self.rebuild_report()

    # ================================================================
    # Raw report
    # ================================================================

    def _current_raw_report(
        self
    ) -> bytearray:
        report = parse_hex_bytes(
            self.report_editor.toPlainText()
        )

        if len(report) != BT_OUTPUT_REPORT_LENGTH:
            raise ValueError(
                f"Bluetooth report must be exactly "
                f"{BT_OUTPUT_REPORT_LENGTH} bytes. "
                f"Current size: {len(report)}"
            )

        if report[0] != BT_OUTPUT_REPORT_ID:
            raise ValueError(
                f"Byte 0 must be "
                f"0x{BT_OUTPUT_REPORT_ID:02X}."
            )

        return report

    def set_byte(self) -> None:
        try:
            report = self._current_raw_report()

            index = self.byte_index_spin.value()
            value = self.byte_value_spin.value()

            report[index] = value

            # Recalculate CRC whenever one of the payload
            # bytes changes.
            if index < 74:
                crc = dualsense_bt_crc(
                    bytes(report[:-4])
                )

                report[-4:] = crc.to_bytes(
                    4,
                    "little"
                )

            self.report_editor.setPlainText(
                hex_bytes(report)
            )

            self._log(
                f"[BYTE EDIT] "
                f"byte {index} = 0x{value:02X}"
            )

        except ValueError as exc:
            QMessageBox.warning(
                self,
                "Invalid report",
                str(exc)
            )

    # ================================================================
    # Sending
    # ================================================================

    def _ensure_device(self) -> bool:
        if self.device is not None:
            return True

        QMessageBox.warning(
            self,
            "No controller",
            "Connect a Bluetooth DualSense first."
        )

        return False

    def _send_output_report(
        self,
        report: bytearray,
        label: str
    ) -> bool:
        if not self._ensure_device():
            return False

        try:
            written = self.device.write(
                bytes(report)
            )

            exact = bytearray(
                report
            )

            self.last_sent = (
                exact,
                "output"
            )

            sequence = (
                exact[1] >> 4
            ) & 0x0F

            self._log(
                f"[{label}] write() returned={written}"
            )

            self._log(
                f"[{label}] BYTES:"
            )

            self._log(
                hex_bytes(exact)
            )

            self._log(
                f"[{label}] "
                f"flag0=0x{exact[3]:02X}, "
                f"flag1=0x{exact[4]:02X}, "
                f"right={exact[5]}, "
                f"left={exact[6]}, "
                f"flag2=0x{exact[41]:02X}, "
                f"sequence={sequence}, "
                f"crc={hex_bytes(exact[-4:])}"
            )

            return True

        except Exception as exc:
            self._log(
                f"[ERROR] {label} failed: {exc}"
            )

            self.status_label.setText(
                f"Send failed: {exc}"
            )

            return False

    def send_current_raw(self) -> None:
        try:
            report = self._current_raw_report()

        except ValueError as exc:
            QMessageBox.warning(
                self,
                "Invalid report",
                str(exc)
            )

            return

        # Always keep the CRC correct for normal tests.
        crc = dualsense_bt_crc(
            bytes(report[:-4])
        )

        report[-4:] = crc.to_bytes(
            4,
            "little"
        )

        self.report_editor.setPlainText(
            hex_bytes(report)
        )

        self._send_output_report(
            report,
            "SEND RAW"
        )

    # ================================================================
    # Vibration
    # ================================================================

    def vibration_on(self) -> None:
        report = self._current_fields_report(
            advance_sequence=True
        )

        self.report_editor.setPlainText(
            hex_bytes(report)
        )

        self._send_output_report(
            report,
            "VIBRATION ON"
        )

    def vibration_off(self) -> None:
        report = self._current_fields_report(
            advance_sequence=True
        )

        report[5] = 0
        report[6] = 0

        crc = dualsense_bt_crc(
            bytes(report[:-4])
        )

        report[-4:] = crc.to_bytes(
            4,
            "little"
        )

        self.report_editor.setPlainText(
            hex_bytes(report)
        )

        self._send_output_report(
            report,
            "VIBRATION OFF"
        )

    # ================================================================
    # Repeat
    # ================================================================

    def vibration_on_repeat(self) -> None:
        if not self._ensure_device():
            return

        self.stop_repeat()

        self.repeat_remaining_ms = (
            self.repeat_duration_spin.value()
        )

        interval = (
            self.repeat_interval_spin.value()
        )

        self.repeat_timer.start(
            interval
        )

        self._log(
            "[REPEAT] Starting vibration repeat: "
            f"duration={self.repeat_remaining_ms} ms, "
            f"interval={interval} ms"
        )

        self._repeat_tick()

    def _repeat_tick(self) -> None:
        if self.device is None:
            self.stop_repeat()
            return

        if self.repeat_remaining_ms <= 0:
            self.repeat_timer.stop()

            self.vibration_off()

            self._log(
                "[REPEAT] Finished."
            )

            return

        report = self._current_fields_report(
            advance_sequence=True
        )

        self.report_editor.setPlainText(
            hex_bytes(report)
        )

        self._send_output_report(
            report,
            "REPEAT ON"
        )

        self.repeat_remaining_ms -= (
            self.repeat_interval_spin.value()
        )

    def stop_repeat(self) -> None:
        if self.repeat_timer.isActive():
            self.repeat_timer.stop()

            self._log(
                "[REPEAT] Stopped."
            )

            if self.device is not None:
                self.vibration_off()

        self.repeat_remaining_ms = 0

    def repeat_last(self) -> None:
        """
        Send the exact same report that was sent last time.

        This intentionally does NOT rebuild the report and does NOT
        change its sequence or CRC.
        """
        if not self._ensure_device():
            return

        if self.last_sent is None:
            self._log(
                "[REPEAT LAST] No report has been sent yet."
            )
            return

        report, transport = self.last_sent

        self._log(
            "[REPEAT LAST] Sending exact previous report."
        )

        if transport != "output":
            self._log(
                f"[REPEAT LAST] Unknown transport: {transport}"
            )

        self._send_output_report(
            bytearray(report),
            "REPEAT LAST"
        )

    # ================================================================
    # Discovery
    # ================================================================

    def single_flag_sweep(self) -> None:
        if not self._ensure_device():
            return

        tests = (
            (0x01, 0x00),
            (0x02, 0x00),
            (0x03, 0x00),
        )

        self._run_flag_tests(
            tests,
            "FLAG0 SWEEP"
        )

    def flag_sweep(self) -> None:
        if not self._ensure_device():
            return

        tests = (
            (0x01, 0x00),
            (0x02, 0x00),
            (0x03, 0x00),
            (0x01, 0x04),
            (0x02, 0x04),
            (0x03, 0x04),
        )

        self._run_flag_tests(
            tests,
            "FLAG COMBINATION SWEEP"
        )

    def _run_flag_tests(
        self,
        tests: tuple[tuple[int, int], ...],
        label: str
    ) -> None:
        self._log(
            f"[{label}] Starting {len(tests)} tests."
        )

        original_flag0 = (
            self.flag0_spin.value()
        )

        original_flag2 = (
            self.flag2_spin.value()
        )

        original_right = (
            self.right_motor_spin.value()
        )

        original_left = (
            self.left_motor_spin.value()
        )

        for number, (
            flag0,
            flag2
        ) in enumerate(
            tests,
            start=1
        ):
            self.flag0_spin.setValue(
                flag0
            )

            self.flag2_spin.setValue(
                flag2
            )

            self.right_motor_spin.setValue(
                original_right
                if original_right
                else 255
            )

            self.left_motor_spin.setValue(
                original_left
                if original_left
                else 255
            )

            report = self._current_fields_report(
                advance_sequence=True
            )

            self.report_editor.setPlainText(
                hex_bytes(report)
            )

            self._log(
                f"[{label}] TEST "
                f"{number}/{len(tests)} "
                f"flag0=0x{flag0:02X} "
                f"flag2=0x{flag2:02X}"
            )

            if not self._send_output_report(
                report,
                f"{label} TEST {number}"
            ):
                break

            QApplication.processEvents()

            time.sleep(
                0.35
            )

            # Send OFF with exactly the same flags,
            # only motors set to zero.
            off = bytearray(
                report
            )

            off[5] = 0
            off[6] = 0

            crc = dualsense_bt_crc(
                bytes(off[:-4])
            )

            off[-4:] = crc.to_bytes(
                4,
                "little"
            )

            self._send_output_report(
                off,
                f"{label} TEST {number} OFF"
            )

            QApplication.processEvents()

            time.sleep(
                0.15
            )

        self.flag0_spin.setValue(
            original_flag0
        )

        self.flag2_spin.setValue(
            original_flag2
        )

        self.right_motor_spin.setValue(
            original_right
        )

        self.left_motor_spin.setValue(
            original_left
        )

        self.rebuild_report()

        self._log(
            f"[{label}] Finished."
        )

    # ================================================================
    # Feature report reader
    # ================================================================

    def read_feature_report(self) -> None:
        if not self._ensure_device():
            return

        report_id = (
            self.feature_id_spin.value()
        )

        length = (
            self.feature_length_spin.value()
        )

        try:
            self._log(
                f"[GET] Feature ID="
                f"0x{report_id:02X}, "
                f"length={length}"
            )

            response = self.device.get_feature_report(
                report_id,
                length
            )

            self._log(
                "[GET RESPONSE] "
                + hex_bytes(response)
            )

        except Exception as exc:
            self._log(
                f"[ERROR] Feature read failed: {exc}"
            )

    # ================================================================
    # Sequence
    # ================================================================

    def _toggle_auto_sequence(self) -> None:
        enabled = (
            self.auto_sequence_button.isChecked()
        )

        self.auto_sequence_button.setText(
            "Auto sequence: ON"
            if enabled
            else "Auto sequence: OFF"
        )

    # ================================================================
    # Logging
    # ================================================================

    def _log(
        self,
        message: str
    ) -> None:
        timestamp = time.strftime(
            "%H:%M:%S"
        )

        self.log.appendPlainText(
            f"{timestamp} {message}"
        )

        scrollbar = (
            self.log.verticalScrollBar()
        )

        scrollbar.setValue(
            scrollbar.maximum()
        )

    # ================================================================
    # Close
    # ================================================================

    def closeEvent(
        self,
        event
    ) -> None:
        self.refresh_timer.stop()
        self.stop_repeat()
        self.disconnect_device(
            silent=True
        )

        event.accept()


def main() -> int:
    app = QApplication(
        sys.argv
    )

    window = DualSenseBluetoothVibrationTest()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
