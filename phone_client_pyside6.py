# -*- coding: utf-8 -*-
"""InputBridge Mobile Client - single-file PySide6 edition.

The file intentionally has no project-local imports so it can be copied to a
phone build environment and packaged as one application. It speaks the same
newline-delimited JSON protocol as the Kivy client and the desktop server.
"""

from __future__ import annotations

import json
import os
import socket
import threading
import uuid
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, Qt, QSettings, Signal, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush
from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QFormLayout, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QPlainTextEdit, QProgressBar, QSlider, QSpinBox, QStackedWidget,
    QTabWidget, QVBoxLayout, QWidget,
)


DEFAULT_PORT = 5000
MAX_TEXT = 256


def clamp(value, low, high):
    return max(low, min(high, value))


class BridgeState(QObject):
    connected_changed = Signal(bool, str)
    pairing_requested = Signal()
    toast = Signal(str)

    def __init__(self):
        super().__init__()
        settings = QSettings("InputBridge", "MobileClient")
        self.uuid = settings.value("uuid", "") or str(uuid.uuid4())
        settings.setValue("uuid", self.uuid)
        self.name = settings.value("name", "PySide6 Mobile") or "PySide6 Mobile"
        self.ip = settings.value("ip", "192.168.1.100") or "192.168.1.100"
        self.port = int(settings.value("port", DEFAULT_PORT) or DEFAULT_PORT)
        self.sock = None
        self.connected = False
        self._lock = threading.RLock()
        self._send_lock = threading.Lock()
        self._stop = threading.Event()
        self._generation = 0
        self.buttons = {key: 0 for key in (
            "A", "B", "X", "Y", "LB", "RB", "BACK", "START", "GUIDE", "L3", "R3",
            "DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT",
        )}
        self.analog = {"L2": 0, "R2": 0}
        self.joystick = {"left_x": 128, "left_y": 128, "right_x": 128, "right_y": 128}
        self.mouse = {"dx": 0, "dy": 0, "scroll": 0, "left": 0, "right": 0, "middle": 0}

    def _payload(self, extra=None):
        payload = {
            "uuid": self.uuid, "name": self.name, "mode": "standard",
            "buttons": dict(self.buttons), "analog": dict(self.analog),
            "joystick": dict(self.joystick), "mouse": dict(self.mouse),
        }
        if extra:
            payload.update(extra)
        return payload

    def connect(self, ip, port, name):
        with self._lock:
            if self.connected:
                self.disconnect()
            self.ip, self.name, self.port = ip.strip(), name.strip() or "PySide6 Mobile", int(port)
            self._generation += 1
            generation = self._generation
            self._stop.clear()
        QSettings("InputBridge", "MobileClient").setValue("ip", self.ip)
        QSettings("InputBridge", "MobileClient").setValue("port", self.port)
        QSettings("InputBridge", "MobileClient").setValue("name", self.name)
        threading.Thread(target=self._connect_worker, args=(generation,), daemon=True).start()

    def _connect_worker(self, generation):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(5)
            sock.connect((self.ip, self.port))
            sock.settimeout(0.5)
            with self._lock:
                if generation != self._generation:
                    sock.close(); return
                self.sock, self.connected = sock, True
            self.connected_changed.emit(True, "Connected — waiting for pairing")
            self._send(self._payload(), generation)
            buffer = bytearray()
            while not self._stop.is_set():
                try:
                    data = sock.recv(4096)
                except socket.timeout:
                    continue
                if not data:
                    break
                buffer.extend(data)
                while b"\n" in buffer:
                    line, _, rest = buffer.partition(b"\n")
                    buffer = bytearray(rest)
                    if not line:
                        continue
                    try:
                        event = json.loads(line.decode("utf-8"))
                    except (ValueError, UnicodeDecodeError):
                        continue
                    if event.get("type") == "pairing_required":
                        self.pairing_requested.emit()
        except Exception as exc:
            self.toast.emit(f"Connection failed: {exc}")
        finally:
            try: sock.close()
            except Exception: pass
            with self._lock:
                current = generation == self._generation
                if current:
                    self.sock, self.connected = None, False
            if current:
                self.connected_changed.emit(False, "Disconnected")

    def disconnect(self):
        with self._lock:
            self._generation += 1
            self._stop.set()
            sock, self.sock, self.connected = self.sock, None, False
        if sock:
            try: sock.shutdown(socket.SHUT_RDWR)
            except OSError: pass
            try: sock.close()
            except OSError: pass
        self.connected_changed.emit(False, "Disconnected")

    def _send(self, payload, generation=None):
        data = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
        with self._send_lock:
            with self._lock:
                if not self.connected or not self.sock or (generation is not None and generation != self._generation):
                    return False
                sock = self.sock
            try:
                sock.sendall(data); return True
            except OSError:
                self.disconnect(); return False

    def send(self, extra=None):
        return self._send(self._payload(extra))

    def set_button(self, key, pressed):
        if key in self.buttons:
            self.buttons[key] = int(bool(pressed)); self.send()

    def send_keyboard(self, text="", key="", action="text"):
        if action == "text" and (not text or len(text) > MAX_TEXT): return False
        return self.send({"keyboard": {"action": action, "key": key[:32], "text": text[:MAX_TEXT]}})

    def send_mouse(self, dx=0, dy=0, scroll=0, **buttons):
        self.mouse.update({"dx": int(clamp(dx, -2048, 2048)), "dy": int(clamp(dy, -2048, 2048)),
                           "scroll": int(clamp(scroll, -20, 20)), **buttons})
        sent = self.send()
        self.mouse.update({"dx": 0, "dy": 0, "scroll": 0})
        return sent


class Card(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.layout = QVBoxLayout(self); self.layout.setContentsMargins(16, 14, 16, 14); self.layout.setSpacing(10)
        heading = QLabel(title); heading.setObjectName("CardTitle"); self.layout.addWidget(heading)


class PairDialog(QDialog):
    def __init__(self, state, parent=None):
        super().__init__(parent); self.state = state
        self.setWindowTitle("Secure pairing"); self.setModal(True); self.setMinimumWidth(320)
        layout = QVBoxLayout(self)
        label = QLabel("Enter the 4-digit code shown in InputBridge on the computer."); label.setWordWrap(True); layout.addWidget(label)
        self.code = QLineEdit(); self.code.setPlaceholderText("Pairing code"); self.code.setMaxLength(32); self.code.setInputMethodHints(Qt.ImhDigitsOnly); layout.addWidget(self.code)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok); buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons)

    def accept(self):
        if not self.code.text().strip():
            QMessageBox.warning(self, "Pairing", "Enter the code first."); return
        self.state.send({"auth_code": self.code.text().strip()}); super().accept()


class ConnectPage(QWidget):
    def __init__(self, state):
        super().__init__(); self.state = state
        root = QVBoxLayout(self); root.setSpacing(14)
        hero = Card("InputBridge Mobile")
        hero.layout.addWidget(QLabel("A polished remote controller, mouse and keyboard for your PC."))
        self.status = QLabel("Disconnected"); self.status.setObjectName("Status"); hero.layout.addWidget(self.status); root.addWidget(hero)
        form = Card("PC connection")
        grid = QGridLayout(); self.ip = QLineEdit(state.ip); self.port = QSpinBox(); self.port.setRange(1, 65535); self.port.setValue(state.port); self.name = QLineEdit(state.name)
        grid.addWidget(QLabel("Server IP"), 0, 0); grid.addWidget(self.ip, 0, 1); grid.addWidget(QLabel("Port"), 1, 0); grid.addWidget(self.port, 1, 1); grid.addWidget(QLabel("Device name"), 2, 0); grid.addWidget(self.name, 2, 1); form.layout.addLayout(grid)
        row = QHBoxLayout(); self.connect_btn = QPushButton("Connect"); self.connect_btn.clicked.connect(self.toggle); self.pair_btn = QPushButton("Enter PC code"); self.pair_btn.clicked.connect(self.pair); row.addWidget(self.connect_btn); row.addWidget(self.pair_btn); form.layout.addLayout(row); root.addWidget(form)
        info = Card("How it works"); info.layout.addWidget(QLabel("Start the desktop server, connect on the same network, then enter the code displayed beside this phone in the Server page.")); root.addWidget(info); root.addStretch()
        state.connected_changed.connect(self._status)

    def toggle(self):
        if self.state.connected: self.state.disconnect()
        else: self.state.connect(self.ip.text(), self.port.value(), self.name.text())

    def pair(self): PairDialog(self.state, self).exec()

    def _status(self, connected, text):
        self.status.setText(text); self.status.setStyleSheet(f"color: {'#53d769' if connected else '#ff6b6b'};")
        self.connect_btn.setText("Disconnect" if connected else "Connect")


class ControllerPage(QWidget):
    def __init__(self, state):
        super().__init__(); self.state = state
        root = QVBoxLayout(self); root.addWidget(QLabel("Controller", objectName="PageTitle"))
        card = Card("Gamepad controls"); grid = QGridLayout()
        for row, labels in enumerate((("Y", "X"), ("B", "A"))):
            for col, key in enumerate(labels):
                btn = QPushButton(key); btn.setMinimumSize(QSize(72, 52)); btn.pressed.connect(lambda k=key: state.set_button(k, True)); btn.released.connect(lambda k=key: state.set_button(k, False)); grid.addWidget(btn, row, col)
        dpad = (("DPAD_UP", "↑", 0, 1), ("DPAD_LEFT", "←", 1, 0), ("DPAD_RIGHT", "→", 1, 2), ("DPAD_DOWN", "↓", 2, 1))
        for key, text, row, col in dpad:
            btn = QPushButton(text); btn.pressed.connect(lambda k=key: state.set_button(k, True)); btn.released.connect(lambda k=key: state.set_button(k, False)); grid.addWidget(btn, row, col + 3)
        for col, key in enumerate(("LB", "RB", "BACK", "START")):
            btn = QPushButton(key); btn.pressed.connect(lambda k=key: state.set_button(k, True)); btn.released.connect(lambda k=key: state.set_button(k, False)); grid.addWidget(btn, 3, col)
        card.layout.addLayout(grid); root.addWidget(card); root.addStretch()


class TouchPad(QWidget):
    moved = Signal(int, int); clicked = Signal(str)
    def __init__(self, state, parent=None):
        super().__init__(parent); self.state = state; self._last = None; self.setMinimumHeight(260); self.setCursor(Qt.CrossCursor)
    def paintEvent(self, event):
        p = QPainter(self); p.fillRect(self.rect(), QColor("#111827")); p.setPen(QPen(QColor("#334155"), 2)); p.drawRoundedRect(self.rect().adjusted(4, 4, -4, -4), 14, 14); p.setPen(QColor("#64748b")); p.drawText(self.rect(), Qt.AlignCenter, "Touchpad\nDrag to move • tap to click")
    def mousePressEvent(self, event): self._last = event.position()
    def mouseMoveEvent(self, event):
        if self._last is not None:
            now = event.position(); self.moved.emit(int(now.x() - self._last.x()), int(now.y() - self._last.y())); self._last = now
    def mouseReleaseEvent(self, event):
        if self._last is not None and (event.position() - self._last).manhattanLength() < 8: self.clicked.emit("left")
        self._last = None


class MousePage(QWidget):
    def __init__(self, state):
        super().__init__(); self.state = state; root = QVBoxLayout(self); root.addWidget(QLabel("Mouse", objectName="PageTitle")); card = Card("Remote touchpad"); pad = TouchPad(state); pad.moved.connect(lambda dx, dy: state.send_mouse(dx=dx, dy=dy)); pad.clicked.connect(lambda _: state.send_mouse(left=1)); card.layout.addWidget(pad); row = QHBoxLayout()
        for name in ("left", "right", "middle"):
            btn = QPushButton(name.title()); btn.pressed.connect(lambda n=name: state.send_mouse(**{n: 1})); btn.released.connect(lambda n=name: state.send_mouse(**{n: 0})); row.addWidget(btn)
        card.layout.addLayout(row); root.addWidget(card); root.addStretch()


class KeyboardPage(QWidget):
    def __init__(self, state):
        super().__init__(); self.state = state; self._previous = ""; root = QVBoxLayout(self); root.addWidget(QLabel("Keyboard", objectName="PageTitle")); card = Card("Type on the computer"); self.editor = QPlainTextEdit(); self.editor.setPlaceholderText("Tap here and type…"); self.editor.textChanged.connect(self.changed); card.layout.addWidget(self.editor); keys = QHBoxLayout()
        for label, key in (("Backspace", "backspace"), ("Enter", "enter"), ("Tab", "tab"), ("Esc", "esc")):
            btn = QPushButton(label); btn.clicked.connect(lambda _, k=key: state.send_keyboard(key=k, action="key_down")); keys.addWidget(btn)
        card.layout.addLayout(keys); root.addWidget(card); root.addStretch()
    def changed(self):
        value = self.editor.toPlainText(); previous = self._previous
        if value.startswith(previous): self.state.send_keyboard(text=value[len(previous):])
        elif previous.startswith(value):
            for _ in range(len(previous) - len(value)): self.state.send_keyboard(key="backspace", action="key_down")
        elif value: self.state.send_keyboard(key="ctrl+a", action="key_down"); self.state.send_keyboard(text=value)
        self._previous = value


class SettingsPage(QWidget):
    def __init__(self, state):
        super().__init__(); root = QVBoxLayout(self); root.addWidget(QLabel("Settings", objectName="PageTitle")); card = Card("Device identity"); form = QFormLayout(); name = QLineEdit(state.name); save = QPushButton("Save name"); save.clicked.connect(lambda: (setattr(state, "name", name.text().strip() or "PySide6 Mobile"), QSettings("InputBridge", "MobileClient").setValue("name", state.name), state.send())); form.addRow("Name", name); form.addRow(save); card.layout.addLayout(form); root.addWidget(card); root.addStretch()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("InputBridge Mobile — PySide6"); self.resize(520, 760); self.state = BridgeState(); tabs = QTabWidget(); tabs.addTab(ConnectPage(self.state), "Connect"); tabs.addTab(ControllerPage(self.state), "Controller"); tabs.addTab(MousePage(self.state), "Mouse"); tabs.addTab(KeyboardPage(self.state), "Keyboard"); tabs.addTab(SettingsPage(self.state), "Settings"); self.setCentralWidget(tabs); self.state.pairing_requested.connect(self._pair); self.state.toast.connect(self._toast)
        self.setStyleSheet("""
            QWidget { background:#0b1120; color:#e5edf8; font-size:14px; }
            QTabWidget::pane { border:0; } QTabBar::tab { padding:10px 14px; background:#111827; color:#94a3b8; }
            QTabBar::tab:selected { color:#60a5fa; border-bottom:2px solid #60a5fa; }
            QFrame#Card { background:#111827; border:1px solid #26344a; border-radius:16px; }
            QLabel#CardTitle { color:#f8fafc; font-size:16px; font-weight:600; }
            QLabel#PageTitle { color:#f8fafc; font-size:22px; font-weight:700; padding:6px; }
            QLineEdit, QPlainTextEdit, QSpinBox { background:#172033; border:1px solid #334155; border-radius:8px; padding:8px; }
            QPushButton { background:#1e293b; border:1px solid #334155; border-radius:9px; padding:9px 12px; }
            QPushButton:hover { background:#263852; } QPushButton:pressed { background:#2563eb; }
        """)
    def _pair(self): PairDialog(self.state, self).exec()
    def _toast(self, message): self.statusBar().showMessage(message, 5000)
    def closeEvent(self, event): self.state.disconnect(); event.accept()


def main():
    app = QApplication([]); app.setApplicationName("InputBridge Mobile"); window = MainWindow(); window.show(); return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
