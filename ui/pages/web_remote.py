"""Desktop controls for the secure, browser-based companion server."""
from __future__ import annotations

import io
import json

import qrcode
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.web_remote import WebRemoteServer


class WebRemotePage(QWidget):
    """Start/stop the HTTPS browser companion and display short-lived pairing credentials."""

    def __init__(self, settings, controllers_page, hotkey_page, server_page, status_changed=None):
        super().__init__()
        self.setObjectName("webCompanionPage")
        self._status_changed = status_changed
        self._last_client_count = -1
        self.web_server = WebRemoteServer(
            settings,
            controllers_page,
            hotkey_page,
            mapper_added=lambda instance: server_page.signals.remote_mapper_added.emit(instance),
        )
        self._build_ui()
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(1000)
        self._refresh_timer.timeout.connect(self._refresh_countdown)
        self._refresh_timer.start()
        self._set_running(False)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(14)

        intro = QFrame()
        intro.setObjectName("webHero")
        intro_layout = QVBoxLayout(intro)
        intro_layout.setContentsMargins(22, 20, 22, 20)
        intro_layout.setSpacing(8)
        eyebrow = QLabel("INPUTBRIDGE  /  LOCAL NETWORK")
        eyebrow.setObjectName("webEyebrow")
        title = QLabel("Web Companion")
        title.setObjectName("webTitle")
        description = QLabel(
            "Use a phone, tablet or another PC as an additional controller from its browser. "
            "No companion app or APK is required for the browser interface."
        )
        description.setWordWrap(True)
        description.setObjectName("webMuted")
        intro_layout.addWidget(eyebrow)
        intro_layout.addWidget(title)
        intro_layout.addWidget(description)
        root.addWidget(intro)

        setup = QFrame()
        setup.setObjectName("webCard")
        setup_layout = QGridLayout(setup)
        setup_layout.setContentsMargins(18, 16, 18, 16)
        setup_layout.setHorizontalSpacing(16)
        setup_layout.setVerticalSpacing(12)

        status_caption = QLabel("SERVER STATUS")
        status_caption.setObjectName("webCaption")
        self.status_badge = QLabel("●  STOPPED")
        self.status_badge.setObjectName("webStatusStopped")
        setup_layout.addWidget(status_caption, 0, 0)
        setup_layout.addWidget(self.status_badge, 0, 1)
        clients_caption = QLabel("CONNECTED BROWSER CONTROLLERS")
        clients_caption.setObjectName("webCaption")
        self.clients_label = QLabel("0 connected")
        self.clients_label.setObjectName("webMuted")
        setup_layout.addWidget(clients_caption, 5, 0)
        setup_layout.addWidget(self.clients_label, 5, 1)

        port_label = QLabel("HTTPS port")
        port_label.setObjectName("webLabel")
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(8765)
        self.port_spin.setFixedWidth(130)
        setup_layout.addWidget(port_label, 1, 0)
        setup_layout.addWidget(self.port_spin, 1, 1)

        self.url_label = QLabel("Start the server to generate a local URL.")
        self.url_label.setObjectName("webUrl")
        self.url_label.setWordWrap(True)
        self.url_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        setup_layout.addWidget(QLabel("BROWSER URL"), 2, 0)
        setup_layout.addWidget(self.url_label, 2, 1)

        self.fingerprint_label = QLabel("TLS fingerprint will appear after startup.")
        self.fingerprint_label.setObjectName("webFingerprint")
        self.fingerprint_label.setWordWrap(True)
        self.fingerprint_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        setup_layout.addWidget(QLabel("CERTIFICATE SHA-256"), 3, 0)
        setup_layout.addWidget(self.fingerprint_label, 3, 1)

        actions = QHBoxLayout()
        self.start_button = QPushButton("Start Web Server")
        self.start_button.setObjectName("webStartButton")
        self.start_button.setMinimumHeight(44)
        self.start_button.clicked.connect(self._toggle_server)
        self.copy_button = QPushButton("Copy URL")
        self.copy_button.setMinimumHeight(44)
        self.copy_button.clicked.connect(self._copy_url)
        actions.addWidget(self.start_button, 2)
        actions.addWidget(self.copy_button, 1)
        setup_layout.addLayout(actions, 4, 0, 1, 2)
        root.addWidget(setup)

        pairing = QFrame()
        pairing.setObjectName("webCard")
        pairing_layout = QHBoxLayout(pairing)
        pairing_layout.setContentsMargins(18, 18, 18, 18)
        pairing_layout.setSpacing(20)

        qr_column = QVBoxLayout()
        qr_title = QLabel("Pair a new browser")
        qr_title.setObjectName("webSectionTitle")
        qr_subtitle = QLabel("Scan the QR with your phone camera. Keep both devices on the same trusted LAN.")
        qr_subtitle.setWordWrap(True)
        qr_subtitle.setObjectName("webMuted")
        self.qr_image = QLabel("QR\nappears here")
        self.qr_image.setObjectName("webQrImage")
        self.qr_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_image.setFixedSize(226, 226)
        self.qr_image.setMinimumSize(180, 180)
        qr_column.addWidget(qr_title)
        qr_column.addWidget(qr_subtitle)
        qr_column.addWidget(self.qr_image, 0, Qt.AlignmentFlag.AlignLeft)
        pairing_layout.addLayout(qr_column, 0)

        code_column = QVBoxLayout()
        code_title = QLabel("Temporary pairing code")
        code_title.setObjectName("webSectionTitle")
        self.code_label = QLabel("— — — — — —")
        self.code_label.setObjectName("webPairCode")
        self.code_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.expiry_label = QLabel("Start the server to create a code.")
        self.expiry_label.setObjectName("webMuted")
        self.rotate_button = QPushButton("Generate new code")
        self.rotate_button.setMinimumHeight(42)
        self.rotate_button.clicked.connect(self._rotate_code)
        code_column.addWidget(code_title)
        code_column.addWidget(self.code_label)
        code_column.addWidget(self.expiry_label)
        code_column.addSpacing(8)
        code_column.addWidget(self.rotate_button)
        code_column.addStretch(1)
        pairing_layout.addLayout(code_column, 1)
        root.addWidget(pairing)

        security = QFrame()
        security.setObjectName("webSecurityNote")
        security_layout = QVBoxLayout(security)
        security_layout.setContentsMargins(15, 12, 15, 12)
        security_title = QLabel("Security notes")
        security_title.setObjectName("webSectionTitle")
        security_body = QLabel(
            "The web companion uses HTTPS, temporary pairing codes, per-browser session tokens, "
            "bounded input messages, an idle-session watchdog and the same desktop permissions as PC Remote. "
            "Browsers may warn about this app's self-signed certificate: compare the SHA-256 fingerprint "
            "above with the value shown by the PC, and only proceed on your trusted network. A web page "
            "cannot silently pin this certificate from JavaScript."
        )
        security_body.setWordWrap(True)
        security_body.setObjectName("webMuted")
        security_layout.addWidget(security_title)
        security_layout.addWidget(security_body)
        root.addWidget(security)
        root.addStretch(1)

        self.setStyleSheet("""
            QWidget#webCompanionPage { background: transparent; }
            QFrame#webHero { border: 1px solid #273b5a; border-radius: 18px;
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #14243d,stop:1 #17152f); }
            QFrame#webCard { border: 1px solid #293a53; border-radius: 16px; background: #111a2b; }
            QLabel { background: transparent; color: #eaf1ff; }
            QLabel#webEyebrow { color: #91aef5; font-size: 10px; font-weight: 800; letter-spacing: 2px; }
            QLabel#webTitle { font-size: 27px; font-weight: 800; }
            QLabel#webMuted { color: #a5b4cb; font-size: 12px; }
            QLabel#webCaption { color: #7e93b2; font-weight: 800; font-size: 10px; }
            QLabel#webLabel { color: #c7d6ed; }
            QLabel#webSectionTitle { color: #f0f4ff; font-size: 15px; font-weight: 750; }
            QLabel#webUrl { color: #7ab7ff; font-size: 15px; font-weight: 750; }
            QLabel#webFingerprint { color: #b2c2dc; font-family: Consolas; font-size: 10px; }
            QLabel#webStatusStopped { color: #ff9cac; font-size: 12px; font-weight: 800; }
            QLabel#webStatusRunning { color: #68e3b7; font-size: 12px; font-weight: 800; }
            QLabel#webPairCode { color: #8ab8ff; font-family: Consolas; font-size: 26px; font-weight: 900; letter-spacing: 3px; }
            QLabel#webQrImage { padding: 8px; color: #637996; background: white; border-radius: 12px; }
            QFrame#webSecurityNote { border: 1px solid #3d3a32; border-radius: 13px; background: #191a22; }
            QPushButton { border: 1px solid #354964; border-radius: 10px; padding: 9px 14px;
                color: #eef4ff; background: #1a2940; font-weight: 650; }
            QPushButton:hover:enabled { background: #263d5e; }
            QPushButton:disabled { color: #667790; background: #111a27; }
            QPushButton#webStartButton { background: #2769df; border-color: #4f8cff; }
            QSpinBox { padding: 7px; color: #edf4ff; background: #0b1423; border: 1px solid #30435f; border-radius: 8px; }
        """)

    def _toggle_server(self) -> None:
        if self.web_server.running:
            self.web_server.stop()
            self._set_running(False)
            self._notify_status_changed()
            return
        try:
            self.web_server.start(self.port_spin.value())
        except Exception as exc:
            QMessageBox.critical(
                self, "Web Companion could not start",
                "The HTTPS listener could not start. Check whether the port is already in use and "
                "whether Windows Firewall allows local-network access.\n\n" + str(exc),
            )
            return
        self._set_running(True)
        self._render_qr()
        self._refresh_countdown()
        self._notify_status_changed()

    def _set_running(self, running: bool) -> None:
        self.status_badge.setText("●  RUNNING" if running else "●  STOPPED")
        self.status_badge.setObjectName("webStatusRunning" if running else "webStatusStopped")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)
        self.start_button.setText("Stop Web Server" if running else "Start Web Server")
        self.start_button.setProperty("running", running)
        self.port_spin.setEnabled(not running)
        self.copy_button.setEnabled(running)
        self.rotate_button.setEnabled(running)
        if running:
            self.url_label.setText(self.web_server.pairing_url().split("#", 1)[0])
            self.fingerprint_label.setText(self.web_server.fingerprint)
        else:
            self.url_label.setText("Start the server to generate a local URL.")
            self.fingerprint_label.setText("TLS fingerprint will appear after startup.")
            self.qr_image.clear()
            self.qr_image.setText("QR\nappears here")
            self.code_label.setText("— — — — — —")
            self.expiry_label.setText("Start the server to create a code.")

    def _render_qr(self) -> None:
        if not self.web_server.running:
            return
        try:
            qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=3)
            qr.add_data(self.web_server.pairing_url())
            qr.make(fit=True)
            image = qr.make_image(fill_color="#07111f", back_color="#ffffff")
            stream = io.BytesIO()
            image.save(stream, format="PNG")
            pixmap = QPixmap()
            pixmap.loadFromData(stream.getvalue(), "PNG")
            if pixmap.isNull():
                raise RuntimeError("Could not render the QR image.")
            self.qr_image.setPixmap(pixmap.scaled(
                self.qr_image.size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
            self.qr_image.setText("")
            self.code_label.setText(self.web_server.pairing_code)
            self.url_label.setText(self.web_server.pairing_url().split("#", 1)[0])
        except Exception as exc:
            self.qr_image.setText("QR unavailable")
            QMessageBox.warning(self, "Pairing QR", "Could not render the pairing QR.\n\n" + str(exc))

    def _rotate_code(self) -> None:
        if not self.web_server.running:
            return
        self.web_server.rotate_pairing_code()
        self._render_qr()
        self._refresh_countdown()

    def _refresh_countdown(self) -> None:
        if not self.web_server.running:
            return
        import time
        count = self.web_server.client_count
        self.clients_label.setText(f"{count} connected browser controller" + ("" if count == 1 else "s"))
        if count != self._last_client_count:
            self._last_client_count = count
            self._notify_status_changed()
        remaining = max(0, int(self.web_server.pairing_deadline - time.monotonic()))
        self.expiry_label.setText(
            f"Code valid for {remaining // 60}:{remaining % 60:02d}. Generate a new code to revoke the old one."
            if remaining else "Pairing code expired. Generate a new code to pair another browser."
        )

    def _copy_url(self) -> None:
        if not self.web_server.running:
            return
        QApplication.clipboard().setText(self.web_server.pairing_url())
        self.copy_button.setText("Copied")
        QTimer.singleShot(1600, lambda: self.copy_button.setText("Copy URL") if self.web_server.running else None)

    def shutdown(self) -> None:
        self._refresh_timer.stop()
        self.web_server.stop()


    def _notify_status_changed(self) -> None:
        if self._status_changed is not None:
            try:
                self._status_changed()
            except Exception:
                # Tray UI should never prevent the browser server from starting.
                pass
