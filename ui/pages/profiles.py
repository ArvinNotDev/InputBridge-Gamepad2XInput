"""Profile management page for creating, loading, renaming, and deleting
user setting profiles."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


class ProfileListItemWidget(QWidget):
    """Custom widget for each profile row — shows name + active indicator."""

    def __init__(self, name: str, active: bool = False, parent=None):
        super().__init__(parent)
        self.profile_name = name
        self._active = active

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)

        # Active indicator dot
        self.dot = QLabel()
        self.dot.setFixedSize(10, 10)
        self._update_dot()
        layout.addWidget(self.dot, alignment=Qt.AlignVCenter)

        # Profile name
        self.lbl_name = QLabel(name)
        self.lbl_name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        font = QFont()
        font.setPointSize(11)
        self.lbl_name.setFont(font)
        layout.addWidget(self.lbl_name, alignment=Qt.AlignVCenter)

        # Active badge
        self.lbl_badge = QLabel("ACTIVE" if active else "")
        if active:
            self.lbl_badge.setStyleSheet(
                "background-color: #2ecc71; color: white; border-radius: 4px; "
                "padding: 2px 8px; font-size: 10px; font-weight: bold;"
            )
        else:
            self.lbl_badge.setStyleSheet("")
        self.lbl_badge.setFixedWidth(60)
        self.lbl_badge.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_badge, alignment=Qt.AlignVCenter)

    def set_active(self, active: bool):
        self._active = active
        self._update_dot()
        if active:
            self.lbl_badge.setText("ACTIVE")
            self.lbl_badge.setStyleSheet(
                "background-color: #2ecc71; color: white; border-radius: 4px; "
                "padding: 2px 8px; font-size: 10px; font-weight: bold;"
            )
        else:
            self.lbl_badge.setText("")
            self.lbl_badge.setStyleSheet("")

    def _update_dot(self):
        color = "#2ecc71" if self._active else "#9aa0a6"
        self.dot.setStyleSheet(
            f"border-radius: 5px; background-color: {color};"
        )


class ProfilesPage(QWidget):
    """Page for managing user setting profiles.

    Signals:
        profile_loaded — emitted after a profile is successfully applied
                         to settings. Carries the profile name.
    """

    profile_loaded = Signal(str)

    def __init__(self, profile_manager, settings, theme_manager=None):
        super().__init__()
        self.profile_manager = profile_manager
        self.settings = settings
        self.theme_manager = theme_manager

        self._build_ui()
        self.refresh_list()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        # Header
        header = QLabel("Profiles")
        header.setAlignment(Qt.AlignLeft)
        header.setStyleSheet("font-size: 18px; font-weight: 700;")
        root.addWidget(header)

        subtitle = QLabel(
            "Create and manage setting profiles. Each profile stores a complete "
            "snapshot of your device, UI, and developer settings."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #9aa0a6; font-size: 11px;")
        root.addWidget(subtitle)

        # Current profile indicator
        self._current_label = QLabel()
        self._refresh_current_label()
        root.addWidget(self._current_label)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #555;")
        root.addWidget(sep)

        # Profile list
        self.profile_list = QListWidget()
        self.profile_list.setStyleSheet(
            """
            QListWidget {
                border: 1px solid #555;
                border-radius: 6px;
            }
            QListWidget::item {
                padding: 0px;
                background-color: transparent;
            }
            QListWidget::item:selected {
                background-color: #3a3a3a;
            }
            """
        )
        root.addWidget(self.profile_list, 1)

        # --- Action row: Create ---
        create_row = QHBoxLayout()
        create_row.setSpacing(8)

        lbl_create = QLabel("New profile:")
        lbl_create.setStyleSheet("font-size: 11px;")
        create_row.addWidget(lbl_create, alignment=Qt.AlignVCenter)

        self.create_input = QLineEdit()
        self.create_input.setPlaceholderText("Enter profile name…")
        self.create_input.setFixedWidth(220)
        create_row.addWidget(self.create_input, alignment=Qt.AlignVCenter)

        self.btn_create = QPushButton("Create")
        self.btn_create.setFixedWidth(90)
        self.btn_create.setObjectName("primary")
        create_row.addWidget(self.btn_create, alignment=Qt.AlignVCenter)

        create_row.addStretch()
        root.addLayout(create_row)

        # --- Action buttons row ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_load = QPushButton("Load Profile")
        self.btn_load.setFixedWidth(120)
        self.btn_load.setToolTip("Apply the selected profile's settings")
        btn_row.addWidget(self.btn_load)

        self.btn_save = QPushButton("Overwrite")
        self.btn_save.setFixedWidth(120)
        self.btn_save.setToolTip("Overwrite the selected profile with current settings")
        btn_row.addWidget(self.btn_save)

        self.btn_rename = QPushButton("Rename")
        self.btn_rename.setFixedWidth(100)
        self.btn_rename.setToolTip("Rename the selected profile")
        btn_row.addWidget(self.btn_rename)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setFixedWidth(100)
        self.btn_delete.setToolTip("Permanently delete the selected profile")
        btn_row.addWidget(self.btn_delete)

        btn_row.addStretch()

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setFixedWidth(90)
        self.btn_refresh.setToolTip("Rescan the profiles directory")
        btn_row.addWidget(self.btn_refresh)

        root.addLayout(btn_row)

        # --- Save current as new (quick save) ---
        quick_row = QHBoxLayout()
        quick_row.setSpacing(8)

        self.btn_save_current = QPushButton("Save Current Settings as New Profile")
        self.btn_save_current.setFixedWidth(260)
        self.btn_save_current.setToolTip(
            "Snapshot the current application settings into a new profile"
        )
        quick_row.addWidget(self.btn_save_current)
        quick_row.addStretch()
        root.addLayout(quick_row)

        # Connect signals
        self.btn_create.clicked.connect(self._on_create)
        self.btn_load.clicked.connect(self._on_load)
        self.btn_save.clicked.connect(self._on_overwrite)
        self.btn_rename.clicked.connect(self._on_rename)
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_refresh.clicked.connect(self.refresh_list)
        self.btn_save_current.clicked.connect(self._on_save_current)
        self.create_input.returnPressed.connect(self._on_create)
        self.profile_list.itemDoubleClicked.connect(self._on_load)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def refresh_list(self):
        """Reload the profile list from disk."""
        self.profile_list.clear()
        active = self.profile_manager.get_active_profile()
        names = self.profile_manager.list_profiles()

        for name in names:
            item = QListWidgetItem()
            widget = ProfileListItemWidget(name, active=(name == active))
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.UserRole, name)
            self.profile_list.addItem(item)
            self.profile_list.setItemWidget(item, widget)

        self._refresh_current_label()

    # ------------------------------------------------------------------
    # Private slots
    # ------------------------------------------------------------------

    def _on_create(self):
        name = self.create_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Profile Name Required", "Please enter a name for the new profile.")
            return
        if self.profile_manager.profile_exists(name):
            overwrite = QMessageBox.question(
                self,
                "Profile Already Exists",
                f'A profile named "{name}" already exists. Overwrite it?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if overwrite != QMessageBox.Yes:
                return

        if self.profile_manager.create_profile_from_settings(name, self.settings):
            self.create_input.clear()
            self.refresh_list()
            self.profile_list.setCurrentRow(-1)
        else:
            QMessageBox.critical(self, "Error", "Failed to save profile. Check file permissions.")

    def _on_load(self):
        name = self._selected_profile_name()
        if not name:
            QMessageBox.information(self, "No Selection", "Select a profile from the list first.")
            return

        confirm = QMessageBox.question(
            self,
            "Load Profile",
            f'Load profile "{name}"?\n\nThis will replace all current settings.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        if self.profile_manager.apply_profile_to_settings(name, self.settings):
            self.refresh_list()
            self.profile_loaded.emit(name)
            QMessageBox.information(
                self,
                "Profile Loaded",
                f'Profile "{name}" loaded successfully.\nRestart may be required for some settings to take effect.',
            )
        else:
            QMessageBox.critical(self, "Error", "Failed to load profile data.")

    def _on_overwrite(self):
        name = self._selected_profile_name()
        if not name:
            QMessageBox.information(self, "No Selection", "Select a profile from the list first.")
            return

        confirm = QMessageBox.question(
            self,
            "Overwrite Profile",
            f'Overwrite profile "{name}" with current settings?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        if self.profile_manager.save_profile(name, self.profile_manager._snapshot_settings(self.settings)):
            self.refresh_list()
        else:
            QMessageBox.critical(self, "Error", "Failed to overwrite profile.")

    def _on_rename(self):
        name = self._selected_profile_name()
        if not name:
            QMessageBox.information(self, "No Selection", "Select a profile from the list first.")
            return

        from PySide6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(
            self, "Rename Profile", "New name:", text=name
        )
        if not ok or not new_name.strip():
            return

        if self.profile_manager.rename_profile(name, new_name.strip()):
            self.refresh_list()
        else:
            QMessageBox.critical(
                self,
                "Rename Failed",
                f'Could not rename to "{new_name}". A profile with that name may already exist.',
            )

    def _on_delete(self):
        name = self._selected_profile_name()
        if not name:
            QMessageBox.information(self, "No Selection", "Select a profile from the list first.")
            return

        confirm = QMessageBox.question(
            self,
            "Delete Profile",
            f'Permanently delete profile "{name}"?\n\nThis cannot be undone.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        if self.profile_manager.delete_profile(name):
            self.refresh_list()
        else:
            QMessageBox.critical(self, "Error", "Failed to delete profile.")

    def _on_save_current(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, "Save Profile", "Profile name:"
        )
        if not ok or not name.strip():
            return

        if self.profile_manager.create_profile_from_settings(name.strip(), self.settings):
            self.refresh_list()
        else:
            QMessageBox.critical(self, "Error", "Failed to save profile.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _selected_profile_name(self) -> Optional[str]:
        item = self.profile_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _refresh_current_label(self):
        active = self.profile_manager.get_active_profile()
        if active:
            self._current_label.setText(f"Active profile:  {active}")
            self._current_label.setStyleSheet(
                "font-size: 12px; font-weight: 600; color: #2ecc71;"
            )
        else:
            self._current_label.setText("Active profile:  (none — using default settings)")
            self._current_label.setStyleSheet(
                "font-size: 12px; color: #9aa0a6;"
            )
