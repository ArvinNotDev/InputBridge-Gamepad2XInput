from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QDialog, QGridLayout, QFrame, QPushButton, QSpinBox
)
from PySide6.QtCore import Qt, QTimer, Signal

from core import emulator


class X360MonitorDialog(QDialog):
    def __init__(self, instance, name):
        super().__init__()
        self.instance = instance
        self.setWindowTitle(f"Monitoring: {name}")
        self.resize(500, 400)

        # ====== Global style for the dialog ======
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #f0f0f0;
                font-size: 11px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # ====== Title ======
        title = QLabel(f"Xbox 360 Controller Monitor - {name}")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        main_layout.addWidget(title)

        # ====== Frame (border) around controller grid ======
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet("QFrame { border: 1px solid #555; border-radius: 6px; }")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(8, 8, 8, 8)
        frame_layout.setSpacing(6)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        frame_layout.addLayout(grid)

        # ====== Labels ======
        # Face Buttons
        self.lbl_a = QLabel("A")
        self.lbl_b = QLabel("B")
        self.lbl_x = QLabel("X")
        self.lbl_y = QLabel("Y")

        # Bumpers
        self.lbl_lb = QLabel("LB")
        self.lbl_rb = QLabel("RB")

        # Triggers (analog)
        self.lbl_lt = QLabel("LT: 0")
        self.lbl_rt = QLabel("RT: 0")

        # D-Pad
        self.lbl_up = QLabel("↑")
        self.lbl_down = QLabel("↓")
        self.lbl_left = QLabel("←")
        self.lbl_right = QLabel("→")

        # Start/Back (option)
        self.lbl_start = QLabel("START")
        self.lbl_back = QLabel("BACK")

        # Joysticks (analog position)
        self.lbl_lj = QLabel("LJ: 0 , 0")
        self.lbl_rj = QLabel("RJ: 0 , 0")

        # Joystick click buttons (digital)
        self.lbl_l3 = QLabel("L3")
        self.lbl_r3 = QLabel("R3")

        # Binary display
        self.lbl_binary = QLabel("Buttons: 000000000000")
        self.lbl_binary.setAlignment(Qt.AlignCenter)
        self.lbl_binary.setStyleSheet("font-family: Consolas, monospace;")

        # Common style for button labels (digital)
        button_widgets = [
            self.lbl_a, self.lbl_b, self.lbl_x, self.lbl_y,
            self.lbl_lb, self.lbl_rb,
            self.lbl_up, self.lbl_down, self.lbl_left, self.lbl_right,
            self.lbl_start, self.lbl_back,
            self.lbl_l3, self.lbl_r3
        ]
        for w in button_widgets:
            w.setAlignment(Qt.AlignCenter)
            w.setMinimumWidth(40)
            w.setStyleSheet("""
                background:#444;
                color:white;
                border-radius:6px;
                padding:4px 6px;
            """)

        # Joysticks + triggers styling (analog info)
        for w in [self.lbl_lj, self.lbl_rj, self.lbl_lt, self.lbl_rt]:
            w.setAlignment(Qt.AlignCenter)
            w.setStyleSheet("""
                background:#333;
                color:#f0f0f0;
                border-radius:6px;
                padding:4px 6px;
            """)

        # ====== Layout (controller-like) ======

        # D-Pad block (left side)
        grid.addWidget(self.lbl_up,    1, 1, Qt.AlignCenter)
        grid.addWidget(self.lbl_left,  2, 0, Qt.AlignCenter)
        grid.addWidget(self.lbl_right, 2, 2, Qt.AlignCenter)
        grid.addWidget(self.lbl_down,  3, 1, Qt.AlignCenter)

        # Start / Back in the middle (shifted a bit to the right)
        grid.addWidget(self.lbl_back,  2, 3, Qt.AlignCenter)   # option/back (bit 5)
        grid.addWidget(self.lbl_start, 2, 4, Qt.AlignCenter)   # start (bit 4)

        # Face buttons block (right side)
        #   Y
        # X   B
        #   A
        grid.addWidget(self.lbl_y, 1, 6, Qt.AlignCenter)
        grid.addWidget(self.lbl_x, 2, 5, Qt.AlignCenter)
        grid.addWidget(self.lbl_b, 2, 7, Qt.AlignCenter)
        grid.addWidget(self.lbl_a, 3, 6, Qt.AlignCenter)

        # Row 0: LT / LB ...... RB / RT (shifted to match new columns)
        grid.addWidget(self.lbl_lt, 0, 0, 1, 2, Qt.AlignLeft)
        grid.addWidget(self.lbl_lb, 0, 2, 1, 1, Qt.AlignLeft)
        grid.addWidget(self.lbl_rb, 0, 5, 1, 1, Qt.AlignRight)
        grid.addWidget(self.lbl_rt, 0, 7, 1, 1, Qt.AlignRight)

        # Joysticks row (analog labels)
        grid.addWidget(self.lbl_lj, 4, 0, 1, 3, Qt.AlignLeft)
        grid.addWidget(self.lbl_rj, 4, 5, 1, 3, Qt.AlignRight)

        # L3 / R3 near sticks
        grid.addWidget(self.lbl_l3, 5, 0, 1, 1, Qt.AlignLeft)
        grid.addWidget(self.lbl_r3, 5, 6, 1, 1, Qt.AlignRight)

        # Add frame and binary line
        main_layout.addWidget(frame)
        main_layout.addWidget(self.lbl_binary)

        # ====== Monitor loop ======
        self.instance.is_monitoring = True
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_view)
        self.timer.start(30)

    def closeEvent(self, event):
        self.instance.is_monitoring = False
        self.timer.stop()
        super().closeEvent(event)

    def update_view(self):
        """
        Mapper calls emulator.update()
        when monitoring it returns:
        binary, rt, lt, ljx, ljy, rjx, rjy
        """
        try:
            data = getattr(self.instance, "_last_monitor", None)
            if not data:
                return

            binary, rt, lt, ljx, ljy, rjx, rjy = data

            self.lbl_binary.setText(f"Buttons: {binary}")
            self.lbl_rt.setText(f"RT: {rt}")
            self.lbl_lt.setText(f"LT: {lt}")
            self.lbl_lj.setText(f"LJ: {ljx} , {ljy}")
            self.lbl_rj.setText(f"RJ: {rjx} , {rjy}")

            # === Binary bit mapping ===
            # cls, a, b, y, x, start, option, r3, l3,
            # dpu, dpd, dpr, dpl, rb, lb, rt, lt, jlx, jly, jrx, jry
            # indices: 0     1  2  3  4    5      6    7   8   9   10  11  12  13  ...
            # You mapped:
            # a: 0, b: 1, y: 2, x: 3, start: 4, back(option): 5,
            # r3: 6, l3: 7, dpu: 8, dpd: 9, dpr: 10, dpl: 11, rb: 12, lb: 13
            mapping = [
                (self.lbl_a,    0),
                (self.lbl_b,    1),
                (self.lbl_y,    2),
                (self.lbl_x,    3),
                (self.lbl_start, 4),
                (self.lbl_back,  5),
                (self.lbl_r3,   6),
                (self.lbl_l3,   7),
                (self.lbl_up,   8),
                (self.lbl_down, 9),
                (self.lbl_right, 10),
                (self.lbl_left,  11),
                (self.lbl_rb,   12),
                (self.lbl_lb,   13),
            ]

            for label, index in mapping:
                pressed = len(binary) > index and binary[index] == "1"
                self._set_pressed(label, pressed)

        except Exception:
            pass

    def _set_pressed(self, label, pressed: bool):
        if pressed:
            label.setStyleSheet("""
                background:#2ecc71;
                color:black;
                border-radius:6px;
                padding:4px 6px;
            """)
        else:
            label.setStyleSheet("""
                background:#444;
                color:white;
                border-radius:6px;
                padding:4px 6px;
            """)


class X360TestRow(QWidget):
    """Per-controller XInput vibration controls for the test page."""

    def __init__(self, instance, name: str, parent=None):
        super().__init__(parent)
        self.instance = instance

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 6)
        root.setSpacing(5)

        header = QHBoxLayout()
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet("font-weight: bold;")
        header.addWidget(self.name_label)

        self.battery_label = QLabel("Battery: —")
        self.battery_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(self.battery_label)
        root.addLayout(header)

        motor_row = QHBoxLayout()
        motor_row.setSpacing(6)

        motor_row.addWidget(QLabel("Left Motor"))
        self.left_spin = self._make_value_spin()
        motor_row.addWidget(self.left_spin)
        self.left_button = QPushButton("Test Left")
        self.left_button.clicked.connect(self._test_left)
        motor_row.addWidget(self.left_button)

        motor_row.addSpacing(10)
        motor_row.addWidget(QLabel("Right Motor"))
        self.right_spin = self._make_value_spin()
        motor_row.addWidget(self.right_spin)
        self.right_button = QPushButton("Test Right")
        self.right_button.clicked.connect(self._test_right)
        motor_row.addWidget(self.right_button)
        root.addLayout(motor_row)

        action_row = QHBoxLayout()
        self.both_button = QPushButton("Both Motors")
        self.both_button.clicked.connect(self._test_both)
        action_row.addWidget(self.both_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self._stop)
        action_row.addWidget(self.stop_button)
        action_row.addStretch(1)
        root.addLayout(action_row)

        self.set_rumble_enabled(bool(getattr(instance, "supports_rumble", False)))

    @staticmethod
    def _make_value_spin() -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(0, 0xFFFF)
        spin.setSingleStep(4096)
        spin.setValue(0xFFFF)
        spin.setMaximumWidth(95)
        return spin

    def set_name(self, name: str) -> None:
        self.name_label.setText(name)

    def set_battery(self, percent: int | None, charging: bool = False) -> None:
        if percent is None:
            self.battery_label.setText("Battery: —")
            return
        suffix = " (charging)" if charging else ""
        self.battery_label.setText(f"Battery: {percent}%{suffix}")

    def set_rumble_enabled(self, enabled: bool) -> None:
        for widget in (
            self.left_spin,
            self.right_spin,
            self.left_button,
            self.right_button,
            self.both_button,
            self.stop_button,
        ):
            widget.setEnabled(enabled)
        if not enabled:
            self.battery_label.setToolTip("Rumble output is available for DualSense controllers.")

    def _send(self, left: int, right: int) -> None:
        try:
            self.instance.set_xinput_vibration(left, right)
        except Exception as exc:
            print(f"[ControllersPage] Vibration test failed: {exc}")

    def _test_left(self) -> None:
        self._send(self.left_spin.value(), 0)

    def _test_right(self) -> None:
        self._send(0, self.right_spin.value())

    def _test_both(self) -> None:
        self._send(self.left_spin.value(), self.right_spin.value())

    def _stop(self) -> None:
        self._send(0, 0)


class ControllersPage(QWidget):
    battery_updated = Signal(object, int, bool)  # path, percent, charging

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        title = QLabel("Emulated Devices")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight:bold; font-size: 12px;")

        self.list_widget = QListWidget()

        layout.addWidget(title)
        layout.addWidget(self.list_widget)

        self.x360_instances = {}
        self.battery_states = {}
        self._items = {}
        self._rows = {}
        self.battery_updated.connect(self._store_battery)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_list)
        self.refresh_timer.start(1000)

        self.list_widget.itemDoubleClicked.connect(self.open_monitor)

    def add_x360_instance(self, instance):
        if hasattr(instance, 'device_path'):
            self.x360_instances[instance.device_path] = instance
        self.refresh_list()

    def update_battery(self, device_path: str, percent: int, charging: bool) -> None:
        self.battery_states[device_path] = (int(percent), bool(charging))
        self.battery_updated.emit(device_path, int(percent), bool(charging))
        self.refresh_list()

    def _store_battery(self, device_path: str, percent: int, charging: bool) -> None:
        self.battery_states[device_path] = (int(percent), bool(charging))
        self.refresh_list()

    def clear_battery(self, device_path) -> None:
        self.battery_states.pop(device_path, None)
        row = self._rows.get(device_path)
        if row is not None:
            row.set_battery(None)
        self.refresh_list()

    def refresh_list(self):
        with emulator.ListOfAllControllers.lock:
            active_paths = list(emulator.ListOfAllControllers.controllers_path)
            active_names = list(emulator.ListOfAllControllers.controllers_name)

        active = {
            path: active_names[index]
            for index, path in enumerate(active_paths)
            if index < len(active_names)
        }

        for path in set(self._items) - set(active):
            item = self._items.pop(path)
            self._rows.pop(path, None)
            row = self.list_widget.row(item)
            if row >= 0:
                self.list_widget.takeItem(row)

        for path in set(self.x360_instances) - set(active):
            del self.x360_instances[path]

        for path, name in active.items():
            instance = self.x360_instances.get(path)
            if instance is None:
                continue

            item = self._items.get(path)
            if item is None:
                item = QListWidgetItem(name)
                item.setData(Qt.UserRole, path)
                widget = X360TestRow(instance, name)
                item.setSizeHint(widget.sizeHint())
                self.list_widget.addItem(item)
                self.list_widget.setItemWidget(item, widget)
                self._items[path] = item
                self._rows[path] = widget
            else:
                widget = self._rows[path]
                widget.instance = instance
                widget.set_name(name)
                widget.set_rumble_enabled(bool(getattr(instance, "supports_rumble", False)))
                item.setText(name)

            battery = self.battery_states.get(path)
            if battery is None:
                widget.set_battery(None)
            else:
                widget.set_battery(*battery)

    def open_monitor(self, item):
        device_path = item.data(Qt.UserRole)

        if device_path not in self.x360_instances:
            return

        instance = self.x360_instances[device_path]
        dialog = X360MonitorDialog(instance, item.text())
        dialog.exec()
