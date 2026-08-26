"""
Profiles Page – manage saved application settings profiles.

Provides a split-pane view: saved profiles on the left with action buttons,
and a details / settings summary on the right with editable description
and profile image support.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap, QPainter, QBrush, QPen, QColor
from PySide6.QtWidgets import (
    QFileDialog,
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
from ui.i18n import tr


class CircularAvatar(QLabel):
    """A label that displays a circular cropped image."""

    def __init__(self, size: int = 80, parent=None):
        super().__init__(parent)
        self._avatar_size = size
        self.setFixedSize(size, size)
        self.setText("")
        self.setStyleSheet("background: transparent;")
        self._pixmap: QPixmap | None = None

    def set_image(self, path: str | None) -> None:
        """Load an image and display it as a circle."""
        if path and Path(path).is_file():
            self._pixmap = QPixmap(path)
        else:
            self._pixmap = None
        self.update()

    def clear_image(self) -> None:
        self._pixmap = None
        self.update()

    def paintEvent(self, event) -> None:
        if self._pixmap is None or self._pixmap.isNull():
            # Draw a placeholder circle with initial
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            size = self._avatar_size
            painter.setBrush(QBrush(QColor("#3a3a5a")))
            painter.setPen(QPen(QColor("#555577"), 2))
            painter.drawEllipse(1, 1, size - 2, size - 2)
            painter.setPen(QColor("#aaaaBB"))
            font = QFont()
            font.setPixelSize(size // 3)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, "?")
            painter.end()
            return

        # Circular crop
        size = self._avatar_size
        scaled = self._pixmap.scaled(
            size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
        )
        # Center crop
        x = (scaled.width() - size) // 2
        y = (scaled.height() - size) // 2
        cropped = scaled.copy(x, y, size, size)

        # Create circular mask
        mask = QPixmap(size, size)
        mask.fill(QColor(0, 0, 0, 0))
        painter_mask = QPainter(mask)
        painter_mask.setRenderHint(QPainter.Antialiasing)
        painter_mask.setBrush(QBrush(QColor(0, 0, 0)))
        painter_mask.setPen(Qt.NoPen)
        painter_mask.drawEllipse(0, 0, size, size)
        painter_mask.end()

        cropped.setMask(mask.mask())

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawPixmap(0, 0, cropped)

        # Border ring
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#5a5af0"), 2))
        painter.drawEllipse(1, 1, size - 2, size - 2)
        painter.end()


class ProfilesPage(QWidget):
    """
    Main Profiles page widget.

    Signals:
        profile_loaded: Emitted with the profile name when a profile is
            successfully activated.
        profile_changed: Emitted when any profile metadata changes (name,
            description, image) so the sidebar avatar can refresh.
    """

    profile_loaded = Signal(str)
    profile_changed = Signal()

    def __init__(self, profile_manager, settings_manager) -> None:
        super().__init__()
        self.pm = profile_manager
        self.settings = settings_manager
        self._current_image_path: str = ""
        self._language = self.settings.get_ui_language()

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
        self.profile_list.setObjectName("profiles_list")
        self.profile_list.setFont(QFont("Segoe UI", 13))
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

        # Portable profile actions
        io_row = QHBoxLayout()
        io_row.setSpacing(6)
        self.btn_import = QPushButton("⬇ Import")
        self.btn_import.setObjectName("profiles_import_btn")
        self.btn_import.setFixedHeight(32)
        self.btn_export = QPushButton("⬆ Export")
        self.btn_export.setObjectName("profiles_export_btn")
        self.btn_export.setFixedHeight(32)
        io_row.addWidget(self.btn_import)
        io_row.addWidget(self.btn_export)
        left_layout.addLayout(io_row)

        # ---- Right pane: details ----
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 0, 0, 0)
        right_layout.setSpacing(12)

        # --- Top row: avatar + title + status ---
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        # Avatar
        avatar_col = QVBoxLayout()
        avatar_col.setSpacing(6)
        avatar_col.setAlignment(Qt.AlignTop)

        self.avatar = CircularAvatar(80)
        avatar_col.addWidget(self.avatar, alignment=Qt.AlignCenter)

        img_btn_row = QHBoxLayout()
        img_btn_row.setSpacing(4)
        self.btn_set_image = QPushButton("📷 Set Image")
        self.btn_set_image.setObjectName("profiles_set_image_btn")
        self.btn_set_image.setFixedHeight(28)
        img_btn_row.addWidget(self.btn_set_image)

        self.btn_remove_image = QPushButton("✕")
        self.btn_remove_image.setObjectName("profiles_remove_image_btn")
        self.btn_remove_image.setFixedSize(28, 28)
        self.btn_remove_image.setToolTip("Remove profile image")
        img_btn_row.addWidget(self.btn_remove_image)

        avatar_col.addLayout(img_btn_row)
        top_row.addLayout(avatar_col)

        # Title + status
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        title_col.setAlignment(Qt.AlignTop)

        self.detail_title = QLabel("Select a profile")
        self.detail_title.setStyleSheet("font-size:18px; font-weight:700;")
        title_col.addWidget(self.detail_title)

        self.detail_status = QLabel("")
        self.detail_status.setStyleSheet("font-size:12px; color:#888899;")
        title_col.addWidget(self.detail_status)

        top_row.addLayout(title_col, 1)
        right_layout.addLayout(top_row)

        # --- Description (editable) ---
        desc_group = QGroupBox("Description")
        desc_outer = QVBoxLayout(desc_group)
        desc_outer.setContentsMargins(8, 12, 8, 8)

        self.detail_desc = QTextEdit()
        self.detail_desc.setPlaceholderText("Add a description for this profile…")
        self.detail_desc.setFixedHeight(70)
        self.detail_desc.setStyleSheet("font-size:13px;")
        self.detail_desc.textChanged.connect(self._on_desc_text_changed)
        desc_outer.addWidget(self.detail_desc)

        desc_btn_row = QHBoxLayout()
        desc_btn_row.addStretch()
        self.btn_save_desc = QPushButton("Save Description")
        self.btn_save_desc.setObjectName("profiles_save_desc_btn")
        self.btn_save_desc.setFixedHeight(28)
        self.btn_save_desc.setEnabled(False)
        desc_btn_row.addWidget(self.btn_save_desc)
        desc_outer.addLayout(desc_btn_row)

        right_layout.addWidget(desc_group)

        # --- Metadata ---
        meta_group = QGroupBox("Metadata")
        meta_layout = QVBoxLayout(meta_group)

        self.detail_created = QLabel("Created: —")
        self.detail_created.setStyleSheet("font-size:13px;")
        meta_layout.addWidget(self.detail_created)

        self.detail_modified = QLabel("Modified: —")
        self.detail_modified.setStyleSheet("font-size:13px;")
        meta_layout.addWidget(self.detail_modified)

        right_layout.addWidget(meta_group)

        # --- Settings summary ---
        summary_group = QGroupBox("Settings Summary")
        summary_layout = QVBoxLayout(summary_group)
        self.detail_summary = QTextEdit()
        self.detail_summary.setReadOnly(True)
        self.detail_summary.setStyleSheet(
            "font-size:12px; border:none; background:transparent;"
        )
        summary_layout.addWidget(self.detail_summary)
        right_layout.addWidget(summary_group, 1)

        # --- Load button ---
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

    def _t(self, text: str) -> str:
        return tr(text, self.settings.get_ui_language())

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self.profile_list.currentRowChanged.connect(self._on_selection_changed)
        self.btn_new.clicked.connect(self._on_new)
        self.btn_duplicate.clicked.connect(self._on_duplicate)
        self.btn_rename.clicked.connect(self._on_rename)
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_import.clicked.connect(self._on_import)
        self.btn_export.clicked.connect(self._on_export)
        self.btn_load.clicked.connect(self._on_activate)
        self.btn_set_image.clicked.connect(self._on_set_image)
        self.btn_remove_image.clicked.connect(self._on_remove_image)
        self.btn_save_desc.clicked.connect(self._on_save_description)

    def _on_desc_text_changed(self) -> None:
        """Enable the save-description button when text changes."""
        name = self._selected_profile_name()
        if name is not None:
            self.btn_save_desc.setEnabled(True)

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

        if self.profile_list.count():
            self._select_profile(active if active else profiles[0].get("name", ""))
        else:
            self._clear_detail()

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
            self.detail_status.setText(f"●  {self._t('Active profile')}")
            self.detail_status.setStyleSheet(
                "font-size:12px; color:#4ecdc4; font-weight:600;"
            )
        else:
            self.detail_status.setText("")
            self.detail_status.setStyleSheet("font-size:12px; color:#888899;")

        # Description
        self.detail_desc.setPlainText(meta.get("description", "") or "")
        self.btn_save_desc.setEnabled(False)

        # Timestamps
        self.detail_created.setText(
            f"{self._t('Created')}: {meta.get('created', '—') or '—'}"
        )
        self.detail_modified.setText(
            f"{self._t('Modified')}: {meta.get('modified', '—') or '—'}"
        )

        # Image
        img_path = self.pm.get_profile_image_path(name)
        self._current_image_path = img_path or ""
        self.avatar.set_image(img_path)
        self.btn_remove_image.setEnabled(bool(img_path))

        # Settings summary
        self.detail_summary.setPlainText(self._format_summary(data))

        self.btn_load.setEnabled(True)
        self.btn_load.setText(
            "✓ Active" if name == active_name else "Activate Profile"
        )

    def _clear_detail(self) -> None:
        self.detail_title.setText("Select a profile")
        self.detail_status.setText("")
        self.detail_desc.setPlainText("")
        self.btn_save_desc.setEnabled(False)
        self.detail_created.setText("Created: —")
        self.detail_modified.setText("Modified: —")
        self.detail_summary.clear()
        self.btn_load.setEnabled(False)
        self.btn_load.setText("Activate Profile")
        self.avatar.clear_image()
        self.btn_remove_image.setEnabled(False)
        self._current_image_path = ""

    def _selected_profile_name(self) -> str | None:
        """Return the currently selected profile name, or None."""
        item = self.profile_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.UserRole)

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
            self.profile_changed.emit()
        else:
            QMessageBox.critical(
                self, "Error", f'Failed to create profile "{name}".'
            )

    def _on_duplicate(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        source = self._selected_profile_name()
        if source is None:
            QMessageBox.information(
                self, "No Selection", "Select a profile to duplicate first."
            )
            return

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

        old_name = self._selected_profile_name()
        if old_name is None:
            QMessageBox.information(
                self, "No Selection", "Select a profile to rename first."
            )
            return

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
            self.profile_changed.emit()
        else:
            QMessageBox.critical(
                self, "Error", f'Failed to rename profile "{old_name}".'
            )

    def _on_delete(self) -> None:
        name = self._selected_profile_name()
        if name is None:
            QMessageBox.information(
                self, "No Selection", "Select a profile to delete first."
            )
            return

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
            self.profile_changed.emit()
        else:
            QMessageBox.critical(
                self, "Error", f'Failed to delete profile "{name}".'
            )

    def _on_export(self) -> None:
        name = self._selected_profile_name()
        if name is None:
            QMessageBox.information(
                self, "No Selection", "Select a profile to export first."
            )
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Profile",
            f"{name}.ibprofile",
            "InputBridge Profile (*.ibprofile)",
        )
        if not path:
            return

        if self.pm.export_profile(name, path):
            QMessageBox.information(
                self,
                "Profile Exported",
                f'Profile "{name}" was exported successfully.',
            )
        else:
            QMessageBox.critical(self, "Error", "Failed to export profile.")

    def _on_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Profile",
            "",
            "InputBridge Profile (*.ibprofile *.json);;All Files (*)",
        )
        if not path:
            return

        imported_name = self.pm.import_profile(path)
        if imported_name is None:
            # A duplicate name is the common recoverable case.
            source_name = self.pm.get_import_profile_name(path) or Path(path).stem
            if self.pm.get_profile(source_name) is not None:
                confirm = QMessageBox.question(
                    self,
                    "Profile Exists",
                    f'A profile named "{source_name}" already exists. Overwrite it?',
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if confirm == QMessageBox.Yes:
                    imported_name = self.pm.import_profile(
                        path, overwrite=True
                    )

        if imported_name is None:
            QMessageBox.critical(
                self,
                "Import Failed",
                "The profile file is invalid or could not be imported.",
            )
            return

        self.refresh_list()
        self._select_profile(imported_name)
        self.profile_changed.emit()
        QMessageBox.information(
            self,
            "Profile Imported",
            f'Profile "{imported_name}" was imported successfully.',
        )

    def _on_activate(self) -> None:
        name = self._selected_profile_name()
        if name is None:
            return

        active = self.pm.get_active_profile_name()
        if name == active:
            return

        if self.pm.activate_profile(name):
            self.refresh_list()
            self._select_profile(name)
            self.profile_loaded.emit(name)
            self.profile_changed.emit()
        else:
            QMessageBox.critical(
                self, "Error", f'Failed to activate profile "{name}".'
            )

    def _on_set_image(self) -> None:
        name = self._selected_profile_name()
        if name is None:
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Profile Image",
            "",
            "Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp);;All Files (*)",
        )
        if not path:
            return

        if self.pm.set_profile_image(name, path):
            img = self.pm.get_profile_image_path(name)
            self._current_image_path = img or ""
            self.avatar.set_image(img)
            self.btn_remove_image.setEnabled(bool(img))
            self.profile_changed.emit()
        else:
            QMessageBox.critical(
                self, "Error", "Failed to set profile image."
            )

    def _on_remove_image(self) -> None:
        name = self._selected_profile_name()
        if name is None:
            return

        if self.pm.remove_profile_image(name):
            self._current_image_path = ""
            self.avatar.clear_image()
            self.btn_remove_image.setEnabled(False)
            self.profile_changed.emit()

    def _on_save_description(self) -> None:
        name = self._selected_profile_name()
        if name is None:
            return

        desc = self.detail_desc.toPlainText().strip()
        if self.pm.update_profile_description(name, desc):
            self.btn_save_desc.setEnabled(False)
            self.profile_changed.emit()

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
                display_label = label_map.get(
                    key, key.replace("_", " ").title()
                )
                display_value = value
                if value in ("true", "false"):
                    display_value = "Enabled" if value == "true" else "Disabled"
                lines.append(f"  {display_label}: {display_value}")
            lines.append("")

        return "\n".join(lines) if lines else "No settings recorded."
