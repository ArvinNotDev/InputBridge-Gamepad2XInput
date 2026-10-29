"""Reusable UI gate for features that require ViGEmBus."""
from __future__ import annotations

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsBlurEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from core.vigem import VIGEMBUS_RELEASES_URL


class VigemGate(QWidget):
    """Blur and disable a feature until ViGEmBus is detected."""

    recheck_requested = Signal()

    def __init__(
        self,
        content: QWidget,
        *,
        title: str = "Virtual gamepad unavailable",
        description: str = (
            "ViGEmBus is required to create a virtual Xbox/XInput controller. "
            "Install the driver on this Windows PC, then recheck or restart "
            "VPadConnect. Other application features remain available."
        ),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.content = content
        self._blur = QGraphicsBlurEffect(self.content)
        self._blur.setBlurRadius(5.5)
        self._available = True

        self._stack = QStackedLayout(self)
        self._stack.setStackingMode(QStackedLayout.StackingMode.StackAll)
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._stack.addWidget(self.content)

        self.overlay = QWidget(self)
        self.overlay.setObjectName("vigemGateOverlay")
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        overlay_layout = QVBoxLayout(self.overlay)
        overlay_layout.setContentsMargins(20, 18, 20, 18)
        overlay_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame(self.overlay)
        card.setObjectName("vigemGateCard")
        card.setMaximumWidth(540)
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 22, 24, 22)
        card_layout.setSpacing(11)

        self.icon_label = QLabel("⌁")
        self.icon_label.setObjectName("vigemGateIcon")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.icon_label)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("vigemGateTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        card_layout.addWidget(self.title_label)

        self.description_label = QLabel(description)
        self.description_label.setObjectName("vigemGateDescription")
        self.description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.description_label.setWordWrap(True)
        card_layout.addWidget(self.description_label)

        self.detail_label = QLabel(
            "Mouse control, hotkeys, physical HID detection, and Web Companion "
            "PC Remote are not blocked by this requirement."
        )
        self.detail_label.setObjectName("vigemGateDetail")
        self.detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_label.setWordWrap(True)
        card_layout.addWidget(self.detail_label)

        actions = QHBoxLayout()
        actions.setSpacing(9)
        self.install_button = QPushButton("Install ViGEmBus ↗")
        self.install_button.setObjectName("vigemInstallButton")
        self.install_button.setMinimumHeight(40)
        self.install_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.install_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(VIGEMBUS_RELEASES_URL))
        )
        actions.addWidget(self.install_button)

        self.recheck_button = QPushButton("Recheck status")
        self.recheck_button.setObjectName("vigemRecheckButton")
        self.recheck_button.setMinimumHeight(40)
        self.recheck_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.recheck_button.clicked.connect(self.recheck_requested.emit)
        actions.addWidget(self.recheck_button)
        card_layout.addLayout(actions)

        overlay_layout.addWidget(card, 0, Qt.AlignmentFlag.AlignCenter)
        self._stack.addWidget(self.overlay)

        self.setStyleSheet("""
            QWidget#vigemGateOverlay { background: rgba(7, 13, 24, 112); }
            QFrame#vigemGateCard {
                background: rgba(17, 28, 45, 248);
                border: 1px solid #395275;
                border-radius: 17px;
            }
            QLabel#vigemGateIcon {
                color: #91b9ff; font-size: 27px; font-weight: 800;
                background: rgba(91, 132, 208, 28);
                border: 1px solid rgba(126, 166, 239, 60);
                border-radius: 24px; min-width: 48px; max-width: 48px;
                min-height: 48px; max-height: 48px;
                qproperty-alignment: AlignCenter;
            }
            QLabel#vigemGateTitle {
                color: #f2f6ff; font-size: 18px; font-weight: 800;
            }
            QLabel#vigemGateDescription {
                color: #d5e2f6; font-size: 12px; line-height: 1.3;
            }
            QLabel#vigemGateDetail {
                color: #91a6c3; font-size: 11px; line-height: 1.3;
            }
            QPushButton#vigemInstallButton {
                color: white; background: #386fe8; border: 1px solid #5d8eff;
                border-radius: 9px; padding: 8px 12px; font-weight: 750;
            }
            QPushButton#vigemInstallButton:hover { background: #4a80f3; }
            QPushButton#vigemRecheckButton {
                color: #d9e6fa; background: #1c2a40; border: 1px solid #3b506e;
                border-radius: 9px; padding: 8px 12px; font-weight: 650;
            }
            QPushButton#vigemRecheckButton:hover { background: #273b58; }
        """)
        self.set_vigem_available(True)

    @property
    def vigem_available(self) -> bool:
        return self._available

    def set_vigem_available(self, available: bool) -> None:
        self._available = bool(available)
        if self._available:
            self.content.setGraphicsEffect(None)
            self.content.setEnabled(True)
            self.overlay.hide()
        else:
            self.content.setGraphicsEffect(self._blur)
            self.content.setEnabled(False)
            self.overlay.show()
        self.overlay.raise_()
