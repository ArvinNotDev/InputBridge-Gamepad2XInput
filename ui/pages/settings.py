import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QPushButton, QSlider, QFrame, QListWidget, QStackedWidget,
    QSpinBox, QCheckBox, QComboBox, QLineEdit, QMessageBox, QGroupBox,
    QSizePolicy, QSpacerItem, QDoubleSpinBox, QInputDialog, QSplitter
)
from PySide6.QtCore import Qt


class SettingsPage(QWidget):
    def __init__(self, theme_manager, settings: object, profile_manager=None):
        super().__init__()
        self.theme_manager = theme_manager
        self.settings = settings
        self.profile_manager = profile_manager

        # Make sure config is normalized (all keys exist / sane) before we read anything
        if hasattr(self.settings, "normalize"):
            try:
                self.settings.normalize()
            except Exception:
                pass

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(0)

        # ====== Top area: menu + pages (splitter) ======
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # ====== Left menu ======
        self.menu = QListWidget()
        self.menu.addItem("Device")
        self.menu.addItem("UI")
        self.menu.addItem("Developer")
        self.menu.setFixedWidth(160)
        self.menu.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        splitter.addWidget(self.menu)

        # ====== Pages stack ======
        self.pages = QStackedWidget()
        splitter.addWidget(self.pages)

        root.addWidget(splitter, 1)

        # ==========================================================
        # DEVICE PAGE
        # ==========================================================
        device_page = QWidget()
        device_layout = QVBoxLayout(device_page)
        device_layout.setContentsMargins(0, 0, 0, 0)
        device_layout.setSpacing(12)

        header = QLabel("Device Settings")
        header.setObjectName("header")
        header.setProperty("class", "header")
        header.setAlignment(Qt.AlignLeft)
        header.setStyleSheet("QLabel { font-size:18px; font-weight:700; }")
        device_layout.addWidget(header)

        device_group = QGroupBox()
        device_form = QFormLayout()
        device_form.setLabelAlignment(Qt.AlignLeft)
        device_form.setFormAlignment(Qt.AlignLeft)
        device_form.setHorizontalSpacing(18)
        device_form.setVerticalSpacing(12)

        # Polling rate
        poll_row = QHBoxLayout()
        self.spin_poll = QSpinBox()
        self.spin_poll.setRange(0, 1000)
        self.spin_poll.setFixedWidth(110)
        poll_row.addWidget(self.spin_poll)
        poll_row.addStretch()
        device_form.addRow("Polling rate (Hz)", poll_row)

        # Checkboxes
        self.chk_reconnect = QCheckBox("Auto reconnect")
        device_form.addRow(self.chk_reconnect)

        self.chk_dpad_mouse = QCheckBox("D-Pad as mouse")
        device_form.addRow(self.chk_dpad_mouse)

        self.chk_mouse_mode = QCheckBox("Mouse mode")
        device_form.addRow(self.chk_mouse_mode)

        # Mouse sensitivity
        sens_row = QHBoxLayout()
        self.spin_mouse_sens = QDoubleSpinBox()
        self.spin_mouse_sens.setRange(0.1, 10.0)
        self.spin_mouse_sens.setSingleStep(0.1)
        self.spin_mouse_sens.setDecimals(2)
        self.spin_mouse_sens.setFixedWidth(110)
        sens_row.addWidget(self.spin_mouse_sens)
        sens_row.addStretch()
        device_form.addRow("Mouse sensitivity", sens_row)

        # Deadzones
        deadzone_layout = QGridLayout()
        deadzone_layout.setHorizontalSpacing(12)
        deadzone_layout.setVerticalSpacing(10)

        lbl_left = QLabel("Left joystick deadzone")
        self.left_slider = QSlider(Qt.Horizontal)
        self.left_slider.setRange(0, 1000)
        self.left_slider.setSingleStep(1)
        self.left_slider.setPageStep(10)
        self.left_val = QLabel()
        self.left_val.setFixedWidth(50)
        self.left_val.setAlignment(Qt.AlignRight)
        deadzone_layout.addWidget(lbl_left, 0, 0)
        deadzone_layout.addWidget(self.left_slider, 0, 1)
        deadzone_layout.addWidget(self.left_val, 0, 2)

        lbl_right = QLabel("Right joystick deadzone")
        self.right_slider = QSlider(Qt.Horizontal)
        self.right_slider.setRange(0, 1000)
        self.right_slider.setSingleStep(1)
        self.right_slider.setPageStep(10)
        self.right_val = QLabel()
        self.right_val.setFixedWidth(50)
        self.right_val.setAlignment(Qt.AlignRight)
        deadzone_layout.addWidget(lbl_right, 1, 0)
        deadzone_layout.addWidget(self.right_slider, 1, 1)
        deadzone_layout.addWidget(self.right_val, 1, 2)

        deadzone_container = QWidget()
        deadzone_container.setLayout(deadzone_layout)
        device_form.addRow(deadzone_container)

        # Axis inversion group
        inv_group = QGroupBox("Axis inversion")
        inv_layout = QGridLayout()
        inv_layout.setHorizontalSpacing(18)
        inv_layout.setVerticalSpacing(8)

        left_label = QLabel("Left")
        left_label.setAlignment(Qt.AlignCenter)
        right_label = QLabel("Right")
        right_label.setAlignment(Qt.AlignCenter)

        inv_layout.addWidget(QLabel(""), 0, 0)
        inv_layout.addWidget(left_label, 0, 1)
        inv_layout.addWidget(right_label, 0, 2)

        inv_layout.addWidget(QLabel("Invert X joystick"), 1, 0)
        self.chk_left_invert_x = QCheckBox()
        self.chk_right_invert_x = QCheckBox()
        inv_layout.addWidget(self.chk_left_invert_x, 1, 1, alignment=Qt.AlignCenter)
        inv_layout.addWidget(self.chk_right_invert_x, 1, 2, alignment=Qt.AlignCenter)

        inv_layout.addWidget(QLabel("Invert Y joystick"), 2, 0)
        self.chk_left_invert_y = QCheckBox()
        self.chk_right_invert_y = QCheckBox()
        inv_layout.addWidget(self.chk_left_invert_y, 2, 1, alignment=Qt.AlignCenter)
        inv_layout.addWidget(self.chk_right_invert_y, 2, 2, alignment=Qt.AlignCenter)

        self.chk_button_invert = QCheckBox()
        inv_layout.addWidget(self.chk_button_invert, 3, 1, alignment=Qt.AlignCenter)
        inv_layout.addWidget(QLabel("Invert buttons"), 3, 0)

        inv_group.setLayout(inv_layout)
        device_form.addRow(inv_group)

        device_group.setLayout(device_form)
        device_layout.addWidget(device_group)

        # Device bottom buttons
        device_buttons = QHBoxLayout()
        device_buttons.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.dev_restore = QPushButton("Restore Default")
        self.dev_restore.setObjectName("secondary")
        self.dev_restore.setProperty("class", "secondary")
        self.dev_restore.setFixedWidth(140)
        self.dev_apply = QPushButton("Apply")
        self.dev_apply.setObjectName("primary")
        self.dev_apply.setFixedWidth(110)
        device_buttons.addWidget(self.dev_restore)
        device_buttons.addWidget(self.dev_apply)
        device_layout.addLayout(device_buttons)

        self.pages.addWidget(device_page)

        # ==========================================================
        # UI PAGE
        # ==========================================================
        ui_page = QWidget()
        ui_layout = QVBoxLayout(ui_page)
        ui_layout.setContentsMargins(0, 0, 0, 0)
        ui_layout.setSpacing(12)

        header_ui = QLabel("UI Settings")
        header_ui.setAlignment(Qt.AlignLeft)
        header_ui.setStyleSheet("font-size:18px; font-weight:700;")
        ui_layout.addWidget(header_ui)

        ui_group = QGroupBox()
        ui_form = QFormLayout()
        ui_form.setLabelAlignment(Qt.AlignLeft)
        ui_form.setHorizontalSpacing(18)
        ui_form.setVerticalSpacing(12)

        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["eng", "fa", "es"])
        self.combo_lang.setMinimumWidth(120)
        self.combo_lang.view().setMinimumWidth(140)
        ui_form.addRow("Language", self.combo_lang)

        self.combo_theme = QComboBox()
        self.combo_theme.setMinimumWidth(120)
        self.combo_theme.view().setMinimumWidth(140)

        theme_names = []
        try:
            base = getattr(self.theme_manager, "base_path", None)
            if base and os.path.isdir(base):
                for f in os.listdir(base):
                    if f.endswith(".qss"):
                        theme_names.append(os.path.splitext(f)[0])
        except Exception:
            theme_names = []
        if not theme_names:
            theme_names = ["dark", "light"]
        self.combo_theme.addItems(theme_names)
        ui_form.addRow("Theme", self.combo_theme)

        ui_group.setLayout(ui_form)
        ui_layout.addWidget(ui_group)

        ui_buttons = QHBoxLayout()
        ui_buttons.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.ui_restore = QPushButton("Restore Default")
        self.ui_restore.setObjectName("secondary")
        self.ui_restore.setFixedWidth(140)
        self.ui_apply = QPushButton("Apply")
        self.ui_apply.setObjectName("primary")
        self.ui_apply.setFixedWidth(110)
        ui_buttons.addWidget(self.ui_restore)
        ui_buttons.addWidget(self.ui_apply)
        ui_layout.addLayout(ui_buttons)

        self.pages.addWidget(ui_page)

        # ==========================================================
        # DEVELOPER PAGE
        # ==========================================================
        dev_page = QWidget()
        dev_layout = QVBoxLayout(dev_page)
        dev_layout.setContentsMargins(0, 0, 0, 0)
        dev_layout.setSpacing(12)

        header_dev = QLabel("Developer Settings")
        header_dev.setAlignment(Qt.AlignLeft)
        header_dev.setStyleSheet("font-size:18px; font-weight:700;")
        dev_layout.addWidget(header_dev)

        dev_group = QGroupBox()
        dev_form = QFormLayout()
        dev_form.setLabelAlignment(Qt.AlignLeft)
        dev_form.setHorizontalSpacing(18)
        dev_form.setVerticalSpacing(12)

        self.chk_debug = QCheckBox("Debug")
        dev_form.addRow(self.chk_debug)

        self.chk_raw_hid = QCheckBox("Raw HID debug")
        dev_form.addRow(self.chk_raw_hid)

        self.chk_log_to_file = QCheckBox("Log to file")
        dev_form.addRow(self.chk_log_to_file)

        log_row = QHBoxLayout()
        lbl_path = QLabel("Log file path")
        self.edit_log_path = QLineEdit()
        self.edit_log_path.setMinimumWidth(240)
        log_row.addWidget(self.edit_log_path)
        dev_form.addRow(lbl_path, log_row)

        dev_group.setLayout(dev_form)
        dev_layout.addWidget(dev_group)

        dev_buttons = QHBoxLayout()
        dev_buttons.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.dev_restore2 = QPushButton("Restore Default")
        self.dev_restore2.setObjectName("secondary")
        self.dev_restore2.setFixedWidth(140)
        self.dev_apply2 = QPushButton("Apply")
        self.dev_apply2.setObjectName("primary")
        self.dev_apply2.setFixedWidth(110)
        dev_buttons.addWidget(self.dev_restore2)
        dev_buttons.addWidget(self.dev_apply2)
        dev_layout.addLayout(dev_buttons)

        self.pages.addWidget(dev_page)

        # ==========================================================
        # SHARED BOTTOM BAR – Save to Profile
        # ==========================================================
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("QFrame { color: #444455; margin: 4px 0; }")
        root.addWidget(separator)

        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(0, 6, 0, 0)
        bottom_bar.setSpacing(8)

        self.lbl_profile_status = QLabel("")
        self.lbl_profile_status.setStyleSheet("font-size:12px; color:#888899;")
        bottom_bar.addWidget(self.lbl_profile_status)
        bottom_bar.addStretch()

        self.btn_save_to_profile = QPushButton("  Save Settings to Profile  ")
        self.btn_save_to_profile.setObjectName("settings_save_profile")
        self.btn_save_to_profile.setProperty("class", "primary")
        self.btn_save_to_profile.setFixedHeight(36)
        bottom_bar.addWidget(self.btn_save_to_profile)

        root.addLayout(bottom_bar)

        # ==========================================================
        # MENU → STACK CONNECTION
        # ==========================================================
        self.menu.currentRowChanged.connect(self.pages.setCurrentIndex)

        # ==========================================================
        # INITIAL LOAD FROM SETTINGS
        # ==========================================================
        try:
            polling = int(self.settings.get_polling_rate())
        except Exception:
            polling = 1
        self.spin_poll.setValue(polling)

        try:
            self.chk_reconnect.setChecked(self.settings.get_auto_reconnect())
        except Exception:
            self.chk_reconnect.setChecked(False)

        try:
            self.chk_dpad_mouse.setChecked(self.settings.get_dpad_as_mouse())
        except Exception:
            self.chk_dpad_mouse.setChecked(True)

        try:
            self.chk_mouse_mode.setChecked(self.settings.get_mouse_mode())
        except Exception:
            self.chk_mouse_mode.setChecked(False)

        try:
            self.spin_mouse_sens.setValue(self.settings.get_mouse_sensitivity())
        except Exception:
            self.spin_mouse_sens.setValue(1.0)

        try:
            left_dz, right_dz = self.settings.get_deadzones()
        except Exception:
            left_dz, right_dz = 0.1, 0.1

        self.left_slider.setValue(int(left_dz * 1000))
        self.right_slider.setValue(int(right_dz * 1000))
        self.left_val.setText(f"{left_dz:.2f}")
        self.right_val.setText(f"{right_dz:.2f}")

        try:
            left_inv, right_inv = self.settings.get_joystick_invertion()
        except Exception:
            left_inv, right_inv = (False, False), (False, False)

        self.chk_left_invert_x.setChecked(bool(left_inv[0]))
        self.chk_left_invert_y.setChecked(bool(left_inv[1]))
        self.chk_right_invert_x.setChecked(bool(right_inv[0]))
        self.chk_right_invert_y.setChecked(bool(right_inv[1]))

        try:
            self.chk_button_invert.setChecked(self.settings.get_button_invertion())
        except Exception:
            self.chk_button_invert.setChecked(False)

        try:
            lang = self.settings.get_ui_language()
        except Exception:
            lang = "eng"
        if lang not in [self.combo_lang.itemText(i) for i in range(self.combo_lang.count())]:
            lang = "eng"
        self.combo_lang.setCurrentText(lang)

        try:
            current_theme = self.settings.get_ui_theme()
        except Exception:
            current_theme = "dark"
        if current_theme in [self.combo_theme.itemText(i) for i in range(self.combo_theme.count())]:
            self.combo_theme.setCurrentText(current_theme)

        try:
            dbg = self.settings.get_developer_debug()
        except Exception:
            dbg = False
        self.chk_debug.setChecked(dbg)

        try:
            raw_hid = self.settings.get_raw_hid_debug()
        except Exception:
            raw_hid = False
        self.chk_raw_hid.setChecked(raw_hid)

        try:
            log_to_file = self.settings.get_log_to_file()
        except Exception:
            log_to_file = False
        self.chk_log_to_file.setChecked(log_to_file)

        try:
            log_path = self.settings.get_log_file_path()
        except Exception:
            log_path = "logs/mapper.log"
        self.edit_log_path.setText(log_path)

        # Apply theme from settings
        try:
            if hasattr(self.theme_manager, "apply_theme"):
                self.theme_manager.apply_theme(self.settings.get_ui_theme())
        except Exception:
            pass

        # Update active profile label
        self._update_profile_label()

        # ==========================================================
        # SIGNALS
        # ==========================================================
        self.left_slider.valueChanged.connect(
            lambda v: self.left_val.setText(f"{v/1000:.2f}")
        )
        self.right_slider.valueChanged.connect(
            lambda v: self.right_val.setText(f"{v/1000:.2f}")
        )

        self.dev_restore.clicked.connect(self.restore_device_defaults)
        self.dev_apply.clicked.connect(self.apply_device)

        self.ui_restore.clicked.connect(self.restore_ui_defaults)
        self.ui_apply.clicked.connect(self.apply_ui)

        self.dev_restore2.clicked.connect(self.restore_dev_defaults)
        self.dev_apply2.clicked.connect(self.apply_dev)

        self.btn_save_to_profile.clicked.connect(self._on_save_to_profile)

    # ==========================================================
    # PROFILE HELPERS
    # ==========================================================

    def set_profile_manager(self, profile_manager):
        """Set or update the profile manager reference (called after init)."""
        self.profile_manager = profile_manager
        self._update_profile_label()

    def _update_profile_label(self):
        """Refresh the status label showing the active profile name."""
        if self.profile_manager is None:
            self.lbl_profile_status.setText("")
            return
        name = self.profile_manager.get_active_profile_name()
        if name:
            self.lbl_profile_status.setText(f"Active profile: {name}")
        else:
            self.lbl_profile_status.setText("No profile active")

    def _apply_all_current_values(self):
        """
        Push every visible UI control value into the SettingsManager
        (without writing to disk — the caller decides when to save).
        """
        # Device
        self.settings.set_polling_rate(self.spin_poll.value())
        self.settings.set_auto_reconnect(self.chk_reconnect.isChecked())
        self.settings.set_dpad_as_mouse(self.chk_dpad_mouse.isChecked())
        self.settings.set_mouse_mode(self.chk_mouse_mode.isChecked())
        self.settings.set_mouse_sensitivity(self.spin_mouse_sens.value())

        left = self.left_slider.value() / 1000.0
        right = self.right_slider.value() / 1000.0
        self.settings.set_deadzones(left, right)

        left_inv = (self.chk_left_invert_x.isChecked(), self.chk_left_invert_y.isChecked())
        right_inv = (self.chk_right_invert_x.isChecked(), self.chk_right_invert_y.isChecked())
        self.settings.set_joystick_invertion(left_inv, right_inv)
        self.settings.set_button_invertion(self.chk_button_invert.isChecked())

        # UI
        self.settings.set_ui_language(self.combo_lang.currentText())
        self.settings.set_ui_theme(self.combo_theme.currentText())

        # Developer
        self.settings.set_developer_debug(self.chk_debug.isChecked())
        self.settings.set_raw_hid_debug(self.chk_raw_hid.isChecked())
        self.settings.set_log_to_file(self.chk_log_to_file.isChecked())
        self.settings.set_log_file_path(self.edit_log_path.text() or "logs/mapper.log")

    def _on_save_to_profile(self):
        """Apply current UI values, then let the user pick or create a profile to save to."""
        if self.profile_manager is None:
            QMessageBox.information(
                self,
                "Profiles Not Available",
                "Profile manager is not initialized.",
            )
            return

        # First apply all current values into the settings config
        self._apply_all_current_values()
        self.settings.save()

        # Build choice list: existing profiles + "Create new…"
        profiles = self.profile_manager.list_profiles()
        active = self.profile_manager.get_active_profile_name()
        items = [p.get("name", "Unknown") for p in profiles]

        # Ask user what to do
        from PySide6.QtWidgets import QMenu, QPushButton

        # Show a context-menu style picker anchored to the button
        menu = QMenu(self)
        menu.setObjectName("settings_profile_menu")

        if items:
            for name in items:
                label = f"  {name}  (overwrite)" if name == active else f"  {name}"
                action = menu.addAction(label)
                action.setData(name)
            menu.addSeparator()

        new_action = menu.addAction("  ＋ Save as new profile…")
        new_action.setData("__new__")

        chosen = menu.exec(self.btn_save_to_profile.mapToGlobal(
            self.btn_save_to_profile.rect().bottomLeft()
        ))

        if chosen is None:
            return

        target = chosen.data()

        if target == "__new__":
            name, ok = QInputDialog.getText(
                self,
                "New Profile",
                "Profile name:",
                QLineEdit.Normal,
            )
            if not ok or not name.strip():
                return
            name = name.strip()

            if self.profile_manager.get_profile(name) is not None:
                reply = QMessageBox.question(
                    self,
                    "Overwrite Profile?",
                    f'A profile named "{name}" already exists.\nOverwrite it?',
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return

            if self.profile_manager.save_profile(name, description="", overwrite=True):
                self.profile_manager.activate_profile(name)
                self._update_profile_label()
                QMessageBox.information(
                    self,
                    "Profile Saved",
                    f'Settings saved to profile "{name}".',
                )
            else:
                QMessageBox.critical(
                    self, "Error", f'Failed to save profile "{name}".'
                )
        else:
            # Overwrite existing
            if self.profile_manager.save_profile(target, description="", overwrite=True):
                self.profile_manager.activate_profile(target)
                self._update_profile_label()
                QMessageBox.information(
                    self,
                    "Profile Updated",
                    f'Settings saved to profile "{target}".',
                )
            else:
                QMessageBox.critical(
                    self, "Error", f'Failed to update profile "{target}".'
                )

    # ==========================================================
    # DEVICE ACTIONS
    # ==========================================================
    def restore_device_defaults(self):
        self.spin_poll.setValue(0)
        self.chk_reconnect.setChecked(True)
        self.chk_dpad_mouse.setChecked(True)
        self.chk_mouse_mode.setChecked(False)
        self.spin_mouse_sens.setValue(1.0)
        self.left_slider.setValue(100)
        self.right_slider.setValue(100)
        self.left_val.setText("0.10")
        self.right_val.setText("0.10")
        self.chk_left_invert_x.setChecked(False)
        self.chk_left_invert_y.setChecked(False)
        self.chk_right_invert_x.setChecked(False)
        self.chk_right_invert_y.setChecked(False)
        self.chk_button_invert.setChecked(False)

    def apply_device(self):
        old_polling = self.settings.get_polling_rate()
        polling = self.spin_poll.value()
        self.settings.set_polling_rate(polling)
        self.settings.set_auto_reconnect(self.chk_reconnect.isChecked())
        self.settings.set_dpad_as_mouse(self.chk_dpad_mouse.isChecked())
        self.settings.set_mouse_mode(self.chk_mouse_mode.isChecked())
        self.settings.set_mouse_sensitivity(self.spin_mouse_sens.value())

        left = self.left_slider.value() / 1000.0
        right = self.right_slider.value() / 1000.0
        self.settings.set_deadzones(left, right)

        left_inv = (self.chk_left_invert_x.isChecked(), self.chk_left_invert_y.isChecked())
        right_inv = (self.chk_right_invert_x.isChecked(), self.chk_right_invert_y.isChecked())
        self.settings.set_joystick_invertion(left_inv, right_inv)

        self.settings.set_button_invertion(self.chk_button_invert.isChecked())

        self.settings.save()

        if polling != old_polling:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Restart Required")
            msg.setText(
                "Polling rate has changed. Please restart the application for the changes to take effect."
            )
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()

    # ==========================================================
    # UI ACTIONS
    # ==========================================================
    def restore_ui_defaults(self):
        self.combo_lang.setCurrentText("eng")
        if "dark" in [self.combo_theme.itemText(i) for i in range(self.combo_theme.count())]:
            self.combo_theme.setCurrentText("dark")
        else:
            if self.combo_theme.count() > 0:
                self.combo_theme.setCurrentIndex(0)

    def apply_ui(self):
        self.settings.set_ui_language(self.combo_lang.currentText())
        theme = self.combo_theme.currentText()
        self.settings.set_ui_theme(theme)
        self.settings.save()
        try:
            if hasattr(self.theme_manager, "apply_theme"):
                self.theme_manager.apply_theme(theme)
        except Exception:
            pass

    # ==========================================================
    # DEVELOPER ACTIONS
    # ==========================================================
    def restore_dev_defaults(self):
        self.chk_debug.setChecked(False)
        self.chk_raw_hid.setChecked(False)
        self.chk_log_to_file.setChecked(False)
        self.edit_log_path.setText("logs/mapper.log")

    def apply_dev(self):
        self.settings.set_developer_debug(self.chk_debug.isChecked())
        self.settings.set_raw_hid_debug(self.chk_raw_hid.isChecked())
        self.settings.set_log_to_file(self.chk_log_to_file.isChecked())
        self.settings.set_log_file_path(self.edit_log_path.text() or "logs/mapper.log")
        self.settings.save()
