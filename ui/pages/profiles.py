"""
Profiles Page – manage saved application settings profiles.

Provides a split-pane view: saved profiles on the left with action buttons,
and a details / current-settings summary on the right.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ProfilesPage(QWidget):
    """
    Main Profiles page widget.

    Signals:
        profile_loaded: Emitted with the profile name when a profile is
            successfully activated.
    """

    profile_loaded = Signal(str)

    def __init__(self, profile_manager, settings_manager) -> None:
        super().__init__()
        self.pm = profile_manager
        self.settings = settings_manager

        self._build_ui()
        self._connect_signals()
        self.refresh_list()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # ---- Left pane: profile list + actions ----
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 12, 0)
        left_layout.setSpacing(10)

        header = QLabel("Profiles")
        header.setStyleSheet("font-size:20px; font-weight:700;")
        left_layout.addWidget(header)

        subtitle = QLabel("Manage your application settings profiles")
        subtitle.setStyleSheet("font-size:12px; color:#888899; margin-bottom:4px;")
        left_layout.addWidget(subtitle)

        self.profile_list = QListWidget()
        self.profile_list.setStyleSheet(
            "QListWidget { font-size:13px; }"
        )
        left_layout.addWidget(self.profile_list, 1)

        # Action buttons row 1
        btn_row1 = QHBoxLayout()
        btn_row1.setSpacing(6)

        self.btn_new = QPushButton("＋ New")
        self.btn_new.setProperty("class", "primary")
        self.btn_new.setObjectName("profiles_new_btn")
        self.btn_new.setFixedHeight(34)
        btn_row1.addWidget(self.btn_new)

        self.btn_duplicate = QPushButton("⧉ Copy")
        self.btn_duplicate.setProperty("class", "secondary")
        self.btn_duplicate.setFixedHeight(34)
        btn_row1.addWidget(self.btn_duplicate)

        left_layout.addLayout(btn_row1)

        # Action buttons row 2
        btn_row2 = QHBoxLayout()
        btn_row2.setSpacing(6)

        self.btn_rename = QPushButton("✎ Rename")
        self.btn_rename.setProperty("class", "secondary")
        self.btn_rename.setFixedHeight(34)
        btn_row2.addWidget(self.btn_rename)

        self.btn_delete = QPushButton("🗑 Delete")
        self.btn_delete.setProperty("class", "danger")
        self.btn_delete.setObjectName("profiles_delete_btn")
        self.btn_delete.setFixedHeight(34)
        btn_row2.addWidget(self.btn_delete)

        left_layout.addLayout(btn_row2)

        # ---- Right pane: details ----
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 0, 0, 0)
        right_layout.setSpacing(12)

        self.detail_title = QLabel("Select a profile")
        self.detail_title.setStyleSheet("font-size:18px; font-weight:700;")
        right_layout.addWidget(self.detail_title)

        self.detail_status = QLabel("")
        self.detail_status.setStyleSheet("font-size:12px; color:#888899;")
        right_layout.addWidget(self.detail_status)

        # Description
        desc_group = QGroupBox("Description")
        desc_layout = QVBoxLayout(desc_group)
        self.detail_desc = QLabel("—")
        self.detail_desc.setWordWrap(True)
        self.detail_desc.setStyleSheet("font-size:13px;")
        desc_layout.addWidget(self.detail_desc)
        right_layout.addWidget(desc_group)

        # Timestamps
        meta_group = QGroupBox("Metadata")
        meta_layout = QVBoxLayout(meta_group)

        self.detail_created = QLabel("Created: —")
        self.detail_created.setStyleSheet("font-size:13px;")
        meta_layout.addWidget(self.detail_created)

        self.detail_modified = QLabel("Modified: —")
        self.detail_modified.setStyleSheet("font-size:13px;")
        meta_layout.addWidget(self.detail_modified)

        right_layout.addWidget(meta_group)

        # Settings summary
        summary_group = QGroupBox("Settings Summary")
        summary_layout = QVBoxLayout(summary_group)
        self.detail_summary = QTextEdit()
        self.detail_summary.setReadOnly(True)
        self.detail_summary.setStyleSheet("font-size:12px; border:none; background:transparent;")
        summary_layout.addWidget(self.detail_summary)
        right_layout.addWidget(summary_group, 1)

        # Load button
        load_row = QHBoxLayout()
        load_row.addStretch()

        self.btn_load = QPushButton("Activate Profile")
        self.btn_load.setProperty("class", "primary")
        self.btn_load.setObjectName("profiles_activate_btn")
        self.btn_load.setFixedWidth(180)
        self.btn_load.setFixedHeight(38)
        self.btn_load.setEnabled(False)
        load_row.addWidget(self.btn_load)

        right_layout.addLayout(load_row)

        # Add to splitter
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        root.addWidget(splitter)

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self.profile_list.currentRowChanged.connect(self._on_selection_changed)
        self.btn_new.clicked.connect(self._on_new)
        self.btn_duplicate.clicked.connect(self._on_duplicate)
        self.btn_rename.clicked.connect(self._on_rename)
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_load.clicked.connect(self._on_activate)

    # ------------------------------------------------------------------
    # Refresh / Selection
    # ------------------------------------------------------------------

    def refresh_list(self) -> None:
        """Reload the profile list from disk."""
        self.profile_list.clear()
        profiles = self.pm.list_profiles()
        active = self.pm.get_active_profile_name()

        for p in profiles:
            name = p.get("name", p.get("filename", "Unknown"))
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, name)

            if name == active:
                item.setText(f"  ●  {name}  (active)")
                font = item.font()
                font.setBold(True)
                item.setFont(font)

            self.profile_list.addItem(item)

    def _on_selection_changed(self, row: int) -> None:
        item = self.profile_list.item(row)
        if item is None:
            self._clear_detail()
            return

        name = item.data(Qt.UserRole)
        data = self.pm.get_profile(name)
        if data is None:
            self._clear_detail()
            return

        meta = data.get("_meta", {})
        active_name = self.pm.get_active_profile_name()

        self.detail_title.setText(name)

        if name == active_name:
            self.detail_status.setText("●  Active profile")
            self.detail_status.setStyleSheet("font-size:12px; color:#4ecdc4; font-weight:600;")
        else:
            self.detail_status.setText("")
            self.detail_status.setStyleSheet("font-size:12px; color:#888899;")

        self.detail_desc.setText(meta.get("description", "—") or "—")
        self.detail_created.setText(f"Created: {meta.get('created', '—') or '—'}")
        self.detail_modified.setText(f"Modified: {meta.get('modified', '—') or '—'}")

        self.detail_summary.setPlainText(self._format_summary(data))

        self.btn_load.setEnabled(True)
        self.btn_load.setText(
            "✓ Active" if name == active_name else "Activate Profile"
        )

    def _clear_detail(self) -> None:
        self.detail_title.setText("Select a profile")
        self.detail_status.setText("")
        self.detail_desc.setText("—")
        self.detail_created.setText("Created: —")
        self.detail_modified.setText("Modified: —")
        self.detail_summary.clear()
        self.btn_load.setEnabled(False)
        self.btn_load.setText("Activate Profile")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_new(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self, "New Profile", "Profile name:", QLineEdit.Normal
        )
        if not ok or not name.strip():
            return

        name = name.strip()

        # Check for duplicate
        if self.pm.get_profile(name) is not None:
            QMessageBox.warning(
                self,
                "Profile Exists",
                f'A profile named "{name}" already exists.\n'
                "Please choose a different name.",
            )
            return

        if self.pm.save_profile(name, description=""):
            self.refresh_list()
            self._select_profile(name)
        else:
            QMessageBox.critical(
                self, "Error", f'Failed to create profile "{name}".'
            )

    def _on_duplicate(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        item = self.profile_list.currentItem()
        if item is None:
            QMessageBox.information(
                self, "No Selection", "Select a profile to duplicate first."
            )
            return

        source = item.data(Qt.UserRole)
        name, ok = QInputDialog.getText(
            self,
            "Duplicate Profile",
            "New profile name:",
            QLineEdit.Normal,
            f"{source} (copy)",
        )
        if not ok or not name.strip():
            return

        name = name.strip()
        if self.pm.get_profile(name) is not None:
            QMessageBox.warning(
                self,
                "Profile Exists",
                f'A profile named "{name}" already exists.',
            )
            return

        if self.pm.duplicate_profile(source, name):
            self.refresh_list()
            self._select_profile(name)
        else:
            QMessageBox.critical(
                self, "Error", f'Failed to duplicate profile "{source}".'
            )

    def _on_rename(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        item = self.profile_list.currentItem()
        if item is None:
            QMessageBox.information(
                self, "No Selection", "Select a profile to rename first."
            )
            return

        old_name = item.data(Qt.UserRole)
        new_name, ok = QInputDialog.getText(
            self, "Rename Profile", "New name:", QLineEdit.Normal, old_name
        )
        if not ok or not new_name.strip():
            return

        new_name = new_name.strip()
        if new_name == old_name:
            return

        if self.pm.get_profile(new_name) is not None:
            QMessageBox.warning(
                self,
                "Profile Exists",
                f'A profile named "{new_name}" already exists.',
            )
            return

        if self.pm.rename_profile(old_name, new_name):
            self.refresh_list()
            self._select_profile(new_name)
        else:
            QMessageBox.critical(
                self, "Error", f'Failed to rename profile "{old_name}".'
            )

    def _on_delete(self) -> None:
        item = self.profile_list.currentItem()
        if item is None:
            QMessageBox.information(
                self, "No Selection", "Select a profile to delete first."
            )
            return

        name = item.data(Qt.UserRole)
        active = self.pm.get_active_profile_name()

        if name == active:
            QMessageBox.warning(
                self,
                "Cannot Delete",
                "Cannot delete the currently active profile.\n"
                "Activate a different profile first.",
            )
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f'Delete profile "{name}"?\n\nThis cannot be undone.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        if self.pm.delete_profile(name):
            self.refresh_list()
            self._clear_detail()
        else:
            QMessageBox.critical(
                self, "Error", f'Failed to delete profile "{name}".'
            )

    def _on_activate(self) -> None:
        item = self.profile_list.currentItem()
        if item is None:
            return

        name = item.data(Qt.UserRole)
        active = self.pm.get_active_profile_name()

        if name == active:
            return

        if self.pm.activate_profile(name):
            self.refresh_list()
            self._select_profile(name)
            self.profile_loaded.emit(name)
        else:
            QMessageBox.critical(
                self, "Error", f'Failed to activate profile "{name}".'
            )

    def _select_profile(self, name: str) -> None:
        """Select a profile in the list by name."""
        for i in range(self.profile_list.count()):
            item = self.profile_list.item(i)
            if item.data(Qt.UserRole) == name:
                self.profile_list.setCurrentItem(item)
                return

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _format_summary(self, data: dict) -> str:
        """Build a human-readable summary of a profile's settings."""
        lines: list[str] = []

        sections = {
            "device": "Device Settings",
            "ui": "UI Settings",
            "developer": "Developer Settings",
        }

        label_map = {
            "polling_rate": "Polling Rate",
            "auto_reconnect": "Auto Reconnect",
            "dpad_as_mouse": "D-Pad as Mouse",
            "mouse_mode": "Mouse Mode",
            "mouse_sensitivity": "Mouse Sensitivity",
            "left_stick_deadzone": "Left Stick Deadzone",
            "right_stick_deadzone": "Right Stick Deadzone",
            "left_stick_invert_x": "Left Stick Invert X",
            "left_stick_invert_y": "Left Stick Invert Y",
            "right_stick_invert_x": "Right Stick Invert X",
            "right_stick_invert_y": "Right Stick Invert Y",
            "invert_buttons": "Invert Buttons",
            "language": "Language",
            "theme": "Theme",
            "debug": "Debug",
            "raw_hid_debug": "Raw HID Debug",
            "log_to_file": "Log to File",
            "log_file_path": "Log File Path",
        }

        for section_key, section_label in sections.items():
            values = data.get(section_key)
            if not isinstance(values, dict):
                continue

            lines.append(f"── {section_label} ──")
            for key, value in values.items():
                display_label = label_map.get(key, key.replace("_", " ").title())
                display_value = value
                if value in ("true", "false"):
                    display_value = "Enabled" if value == "true" else "Disabled"
                lines.append(f"  {display_label}: {display_value}")
            lines.append("")

        return "\n".join(lines) if lines else "No settings recorded."
