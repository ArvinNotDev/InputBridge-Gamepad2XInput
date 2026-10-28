# -*- coding: utf-8 -*-
"""InputBridge Mobile — PySide6 client for the existing InputBridge desktop server."""
from __future__ import annotations

import hashlib, hmac, json, math, os, socket, ssl, sys, threading, time, uuid
from pathlib import Path
from typing import Any

from PySide6.QtCore import QCoreApplication, QCameraPermission, QEvent, QObject, QPointF, QStandardPaths, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFormLayout, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
    QPushButton, QScrollArea, QSizePolicy, QSlider, QStackedWidget, QVBoxLayout, QWidget,
)
try:
    from PySide6.QtMultimedia import QCamera, QMediaCaptureSession, QMediaDevices
    from PySide6.QtMultimediaWidgets import QVideoWidget
except Exception:
    QCamera = QMediaCaptureSession = QMediaDevices = QVideoWidget = None
try:
    from PySide6.QtSensors import QAccelerometer
except Exception:
    QAccelerometer = None
try:
    import numpy as np
    from pyzbar.pyzbar import decode as decode_qr
except Exception:
    np = decode_qr = None

APP_NAME = "InputBridge Mobile"
PROTOCOL_VERSION = 1
MAX_FRAME_BYTES = 16 * 1024
PAIRING_SCHEMA = "inputbridge-pairing"
PAIRING_VERSION = 1
PALETTE = {
    "bg": "#080d18", "surface": "#111a2b", "line": "#263650",
    "text": "#f4f7ff", "muted": "#a5b4cb", "subtle": "#7789a5",
    "accent": "#4f8cff", "violet": "#9a7cff", "green": "#35d39a",
    "red": "#ff667c", "yellow": "#f5c65d",
}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def is_android_runtime() -> bool:
    """Detect Android in both CPython and python-for-android launch environments."""
    return sys.platform == "android" or any(
        key in os.environ for key in ("ANDROID_ARGUMENT", "ANDROID_ROOT", "ANDROID_DATA")
    )


def normalize_fingerprint(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = "".join(c for c in value.lower() if c in "0123456789abcdef")
    return value if len(value) == 64 else ""


def parse_pairing_qr_payload(raw: str | bytes) -> dict[str, str] | None:
    """Parse and validate a QR payload created by the desktop Server screen."""
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError:
            return None
    if not isinstance(raw, str) or len(raw) > 2048:
        return None
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(obj, dict) or obj.get("schema") != PAIRING_SCHEMA:
        return None
    if type(obj.get("version")) is not int or obj["version"] != PAIRING_VERSION:
        return None
    host, port = obj.get("host"), obj.get("port")
    pin = normalize_fingerprint(obj.get("tls_sha256"))
    if (not isinstance(host, str) or not host or len(host) > 253
            or host.startswith(".") or host.endswith(".")
            or any(not (c.isalnum() or c in ".-") for c in host)
            or type(port) is not int or not 1 <= port <= 65535 or not pin):
        return None
    return {"host": host, "port": str(port), "fingerprint": pin}


def _data_directory() -> Path:
    root = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    path = Path(root) if root else Path.home() / ".inputbridge-mobile"
    path.mkdir(parents=True, exist_ok=True)
    return path


DATA_DIR = _data_directory()
SETTINGS_FILE = DATA_DIR / "mobile-settings.json"
FINGERPRINTS_FILE = DATA_DIR / "server-fingerprints.json"


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


SETTINGS = _read_json(SETTINGS_FILE, {})
if not isinstance(SETTINGS, dict):
    SETTINGS = {}
for key, value in {
    "uuid": str(uuid.uuid4()), "name": APP_NAME, "last_host": "", "last_port": "5000",
    "mode": "standard", "steering_sensitivity": 1.5, "mouse_sensitivity": 1.8,
    "tap_to_click": True,
}.items():
    SETTINGS.setdefault(key, value)
_write_json(SETTINGS_FILE, SETTINGS)


def save_settings() -> None:
    _write_json(SETTINGS_FILE, SETTINGS)


def _pin_key(host: str, port: int | str) -> str:
    return f"{host.strip().lower()}:{int(port)}"


def load_pin(host: str, port: int | str) -> str:
    pins = _read_json(FINGERPRINTS_FILE, {})
    return normalize_fingerprint(pins.get(_pin_key(host, port), "")) if isinstance(pins, dict) else ""


def save_pin(host: str, port: int | str, pin: str) -> None:
    pin = normalize_fingerprint(pin)
    if not pin:
        raise ValueError("A valid SHA-256 fingerprint is required.")
    pins = _read_json(FINGERPRINTS_FILE, {})
    if not isinstance(pins, dict):
        pins = {}
    pins[_pin_key(host, port)] = pin
    _write_json(FINGERPRINTS_FILE, pins)


def label(text: str, role: str = "body") -> QLabel:
    widget = QLabel(text)
    widget.setWordWrap(True)
    widget.setProperty("role", role)
    return widget


def button(text: str, kind: str = "normal") -> QPushButton:
    widget = QPushButton(text)
    widget.setProperty("kind", kind)
    widget.setMinimumHeight(44)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    return widget


def card(title: str = "") -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(15, 14, 15, 15)
    layout.setSpacing(10)
    if title:
        layout.addWidget(label(title, "cardTitle"))
    return frame, layout


def scroll_page(title: str, description: str) -> tuple[QWidget, QVBoxLayout]:
    page = QWidget()
    outer = QVBoxLayout(page)
    outer.setContentsMargins(12, 12, 12, 10)
    outer.setSpacing(10)
    outer.addWidget(label(title, "pageTitle"))
    outer.addWidget(label(description, "muted"))
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    inside = QWidget()
    body = QVBoxLayout(inside)
    body.setContentsMargins(0, 2, 2, 8)
    body.setSpacing(11)
    scroll.setWidget(inside)
    outer.addWidget(scroll, 1)
    return page, body


class BridgeClient(QObject):
    """Existing JSON-line protocol, TLS pinning, retries and response receiver."""
    connectionChanged = Signal(bool, str)
    connectingChanged = Signal(bool)
    statusMessage = Signal(str)
    remoteResponse = Signal(dict)

    def __init__(self):
        super().__init__()
        self.device_uuid = str(SETTINGS["uuid"])
        self.device_name = str(SETTINGS["name"])
        self.mode = str(SETTINGS["mode"])
        self.steering_sensitivity = float(SETTINGS["steering_sensitivity"])
        self.mouse_sensitivity = float(SETTINGS["mouse_sensitivity"])
        self.tap_to_click = bool(SETTINGS["tap_to_click"])
        self.sock: socket.socket | ssl.SSLSocket | None = None
        self.connected = self.connecting = False
        self._lock = threading.RLock()
        self._send_lock = threading.Lock()
        self._generation = 0
        self._rx_stop = threading.Event()
        self._pending: dict[str, tuple[float, str]] = {}
        self._pending_lock = threading.Lock()
        self._mouse_lock = threading.Lock()
        self._mouse_dx = self._mouse_dy = 0.0
        self._mouse_scroll = 0
        self.mouse_buttons = {"left": 0, "right": 0, "middle": 0}
        self.buttons = {k: 0 for k in (
            "A", "B", "X", "Y", "LB", "RB", "BACK", "START", "GUIDE",
            "L3", "R3", "DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT")}
        self.analog = {"L2": 0, "R2": 0}
        self.joystick = {"left_x": 128, "left_y": 128, "right_x": 128, "right_y": 128}
        self.gyro_enabled = False
        self.gyro_neutral: float | None = None
        self.gyro_steer = 0.0

    def connect_to(self, host: str, port_text: str, name: str, fingerprint: str = "") -> None:
        host = (host or "").strip()
        name = (name or "").strip() or APP_NAME
        try:
            port = int(port_text)
        except (TypeError, ValueError):
            self.statusMessage.emit("Enter a valid port.")
            return
        if not host or len(host) > 253 or not 1 <= port <= 65535:
            self.statusMessage.emit("Enter a valid PC address and port between 1 and 65535.")
            return
        if len(name) > 64 or any(ord(c) < 32 or ord(c) == 127 for c in name):
            self.statusMessage.emit("Device name is invalid.")
            return
        expected = normalize_fingerprint(fingerprint) or load_pin(host, port)
        if not expected:
            self.statusMessage.emit("Scan the PC pairing QR or enter its SHA-256 certificate fingerprint.")
            return
        with self._lock:
            if self.connected:
                self.statusMessage.emit("Already connected. Disconnect before switching PCs.")
                return
            if self.connecting:
                self.statusMessage.emit("A secure connection attempt is already running.")
                return
            self.connecting = True
            self._generation += 1
            generation = self._generation
            self.device_name = name
        SETTINGS.update(last_host=host, last_port=str(port), name=name)
        save_settings()
        self.connectingChanged.emit(True)
        threading.Thread(
            target=self._connect_worker, args=(host, port, expected, generation),
            daemon=True, name="InputBridgeConnect",
        ).start()

    def _connect_worker(self, host: str, port: int, expected: str, generation: int) -> None:
        secure = None
        last_error: Exception | None = None
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            for attempt in range(3):
                raw = None
                try:
                    with self._lock:
                        if generation != self._generation or not self.connecting:
                            return
                    raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    raw.settimeout(3.5)
                    raw.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    try:
                        raw.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    except OSError:
                        pass
                    raw.connect((host, port))
                    raw.settimeout(8.0)
                    secure = context.wrap_socket(raw, server_hostname=host)
                    raw = None
                    actual = hashlib.sha256(secure.getpeercert(binary_form=True)).hexdigest()
                    if not hmac.compare_digest(actual, expected):
                        raise ValueError("The PC TLS fingerprint does not match the QR or saved pin. Verify the PC identity and scan its QR again.")
                    break
                except Exception as exc:
                    last_error = exc
                    for candidate in (secure, raw):
                        if candidate is not None:
                            try:
                                candidate.close()
                            except OSError:
                                pass
                    secure = None
                    if isinstance(exc, ValueError) or not isinstance(exc, (OSError, socket.timeout, ssl.SSLError)) or attempt == 2:
                        raise
                    time.sleep(0.35 * (attempt + 1))
            if secure is None:
                raise last_error or ConnectionError("Unable to establish a secure connection.")
            secure.settimeout(1.0)
            save_pin(host, port, expected)
            with self._lock:
                if generation != self._generation or not self.connecting:
                    secure.close()
                    return
                self.sock, self.connected, self.connecting = secure, True, False
                self._rx_stop.clear()
            self.connectingChanged.emit(False)
            self.connectionChanged.emit(True, "TLS certificate verified. First-time pairing may still be required.")
            threading.Thread(target=self._receive_loop, args=(generation, secure), daemon=True, name="InputBridgeReceiver").start()
            if not self.send_state():
                raise ConnectionError("Secure link opened, but initial controller state could not be sent.")
        except Exception as exc:
            if secure is not None:
                try:
                    secure.close()
                except OSError:
                    pass
            with self._lock:
                current = generation == self._generation
                if current:
                    self.sock, self.connected, self.connecting = None, False, False
            if current:
                self.connectingChanged.emit(False)
                self.connectionChanged.emit(False, str(exc) or "Connection failed.")

    def _receive_loop(self, generation: int, sock: ssl.SSLSocket) -> None:
        buffer = bytearray()
        try:
            while not self._rx_stop.is_set():
                with self._lock:
                    if generation != self._generation or not self.connected or self.sock is not sock:
                        return
                try:
                    data = sock.recv(4096)
                    if not data:
                        break
                    buffer.extend(data)
                    while b"\n" in buffer:
                        end = buffer.find(b"\n")
                        if end > MAX_FRAME_BYTES:
                            raise ValueError("Response exceeded protocol size limit.")
                        raw = bytes(buffer[:end]).strip()
                        del buffer[:end + 1]
                        if not raw:
                            continue
                        try:
                            obj = json.loads(raw.decode("utf-8"))
                        except (UnicodeDecodeError, json.JSONDecodeError):
                            continue
                        if (isinstance(obj, dict) and obj.get("message_type") == "remote_response"
                                and obj.get("protocol_version") == PROTOCOL_VERSION
                                and isinstance(obj.get("request_id"), str) and isinstance(obj.get("ok"), bool)):
                            with self._pending_lock:
                                self._pending.pop(obj["request_id"], None)
                            self.remoteResponse.emit(obj)
                    if len(buffer) > MAX_FRAME_BYTES:
                        raise ValueError("Response exceeded protocol size limit.")
                except socket.timeout:
                    self._expire_requests()
        except (OSError, ssl.SSLError, ValueError):
            pass
        finally:
            self._close_session(generation, sock, "Secure connection closed.")

    def _expire_requests(self) -> None:
        now = time.monotonic()
        with self._pending_lock:
            expired = [(rid, action) for rid, (sent, action) in self._pending.items() if now - sent >= 12]
            for rid, _ in expired:
                self._pending.pop(rid, None)
        for rid, action in expired:
            self.remoteResponse.emit({
                "message_type": "remote_response", "protocol_version": PROTOCOL_VERSION,
                "request_id": rid, "action": action, "ok": False,
                "error": "Request timed out. Check the PC connection and desktop permissions.",
            })

    def _close_session(self, generation=None, sock=None, message="Disconnected.") -> None:
        with self._lock:
            if generation is not None and generation != self._generation:
                return
            if sock is not None and self.sock is not sock:
                return
            old, active = self.sock, self.connected or self.connecting
            self._generation += 1
            self.sock, self.connected, self.connecting = None, False, False
            self._rx_stop.set()
        with self._mouse_lock:
            self._mouse_dx = self._mouse_dy = 0.0
            self._mouse_scroll = 0
            self.mouse_buttons = {"left": 0, "right": 0, "middle": 0}
        with self._pending_lock:
            self._pending.clear()
        if old is not None:
            try:
                old.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                old.close()
            except OSError:
                pass
        if active:
            self.connectingChanged.emit(False)
            self.connectionChanged.emit(False, message)

    def disconnect(self) -> None:
        self._close_session(message="Disconnected by user.")

    def build_state_message(self) -> dict[str, Any]:
        with self._mouse_lock:
            mouse = {
                "dx": int(clamp(round(self._mouse_dx), -2048, 2048)),
                "dy": int(clamp(round(self._mouse_dy), -2048, 2048)),
                "scroll": int(clamp(self._mouse_scroll, -20, 20)),
                **self.mouse_buttons,
            }
        return {
            "protocol_version": PROTOCOL_VERSION, "message_type": "state",
            "uuid": self.device_uuid, "name": self.device_name or APP_NAME,
            "mode": self.mode, "gyro_enabled": self.gyro_enabled,
            "buttons": dict(self.buttons), "analog": dict(self.analog),
            "joystick": dict(self.joystick), "mouse": mouse,
            "tilt": {"neutral_x": self.gyro_neutral, "steer": round(self.gyro_steer, 4)},
        }

    def _send_message(self, obj: dict[str, Any]) -> bool:
        encoded = (json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        if not encoded or len(encoded) > MAX_FRAME_BYTES:
            self.statusMessage.emit("Message exceeds the protocol size limit.")
            return False
        with self._lock:
            target, generation = self.sock, self._generation
            if not self.connected or target is None:
                return False
        try:
            with self._send_lock:
                with self._lock:
                    if not self.connected or self.sock is not target or self._generation != generation:
                        return False
                target.sendall(encoded)
            return True
        except (OSError, ssl.SSLError):
            self._close_session(generation, target, "Secure connection lost.")
            return False

    def send_state(self, extra: dict[str, Any] | None = None) -> bool:
        obj = self.build_state_message()
        if extra:
            obj.update(extra)
        sent = self._send_message(obj)
        if sent:
            with self._mouse_lock:
                self._mouse_dx -= obj["mouse"]["dx"]
                self._mouse_dy -= obj["mouse"]["dy"]
                self._mouse_scroll -= obj["mouse"]["scroll"]
        return sent

    def send_auth_code(self, code: str) -> None:
        code = (code or "").strip()
        if not code:
            self.statusMessage.emit("Enter the pairing code displayed on the PC.")
            return
        self.statusMessage.emit("Pairing code sent." if self.send_state({"auth_code": code}) else "Not connected.")

    def send_remote_action(self, action: str, payload: dict[str, Any] | None = None) -> str | None:
        if not self.connected:
            return None
        request_id = uuid.uuid4().hex
        request = {"protocol_version": PROTOCOL_VERSION, "request_id": request_id,
                   "action": action, "payload": payload or {}}
        with self._pending_lock:
            if len(self._pending) >= 32:
                oldest = min(self._pending, key=lambda rid: self._pending[rid][0])
                self._pending.pop(oldest, None)
            self._pending[request_id] = (time.monotonic(), action)
        if not self.send_state({"remote_request": request}):
            with self._pending_lock:
                self._pending.pop(request_id, None)
            return None
        return request_id

    def set_button(self, key: str, pressed: bool) -> None:
        if key in self.buttons:
            self.buttons[key] = int(bool(pressed))
            self.send_state()

    def set_trigger(self, key: str, value: int) -> None:
        if key.upper() in self.analog:
            self.analog[key.upper()] = int(clamp(value, 0, 255))
            self.send_state()

    def set_stick(self, side: str, x: float, y: float) -> None:
        prefix = "left" if side == "left" else "right"
        self.joystick[prefix + "_x"] = int(round(128 + clamp(x, -1, 1) * 127))
        self.joystick[prefix + "_y"] = int(round(128 + clamp(y, -1, 1) * 127))
        self.send_state()

    def set_mode(self, mode: str) -> None:
        if mode in ("standard", "driving"):
            self.mode = mode
            SETTINGS["mode"] = mode
            save_settings()
            self.send_state()

    def set_device_name(self, name: str) -> None:
        self.device_name = ((name or "").strip() or APP_NAME)[:64]
        SETTINGS["name"] = self.device_name
        save_settings()
        self.send_state()

    def move_mouse(self, dx: float, dy: float) -> None:
        if self.connected:
            with self._mouse_lock:
                self._mouse_dx += float(dx) * self.mouse_sensitivity
                self._mouse_dy += float(dy) * self.mouse_sensitivity

    def set_mouse_button(self, name: str, pressed: bool) -> None:
        if name in self.mouse_buttons:
            with self._mouse_lock:
                self.mouse_buttons[name] = int(bool(pressed) and self.connected)
            self.send_state()

    def scroll_mouse(self, amount: int) -> None:
        if self.connected:
            with self._mouse_lock:
                self._mouse_scroll = int(clamp(self._mouse_scroll + int(amount), -20, 20))


class StickPad(QWidget):
    def __init__(self, side: str, callback, parent=None):
        super().__init__(parent)
        self.side, self.callback = side, callback
        self.value = QPointF(0, 0)
        self.dragging = False
        self.setMinimumSize(108, 135)
        self.setFixedHeight(142)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width()/2, self.height()/2
        radius = min(self.width()*.37, self.height()*.34)
        p.setPen(QPen(QColor(PALETTE["line"]), 2))
        p.setBrush(QColor("#0a1220"))
        p.drawEllipse(QPointF(cx, cy), radius, radius)
        p.setPen(QPen(QColor("#283b58"), 1, Qt.PenStyle.DashLine))
        p.drawEllipse(QPointF(cx, cy), radius*.58, radius*.58)
        p.drawLine(QPointF(cx-radius, cy), QPointF(cx+radius, cy))
        p.drawLine(QPointF(cx, cy-radius), QPointF(cx, cy+radius))
        dot = QPointF(cx+self.value.x()*radius*.72, cy+self.value.y()*radius*.72)
        grad = QRadialGradient(dot, radius*.7)
        grad.setColorAt(0, QColor("#79b2ff"))
        grad.setColorAt(1, QColor(PALETTE["accent"]))
        p.setPen(QPen(QColor("#d5e6ff"), 1))
        p.setBrush(grad)
        p.drawEllipse(dot, radius*.3, radius*.3)
        p.setPen(QColor(PALETTE["muted"]))
        p.drawText(0, self.height()-3, self.width(), 20, Qt.AlignmentFlag.AlignHCenter,
                   "LEFT STICK" if self.side == "left" else "RIGHT STICK")

    def _move(self, point):
        radius = min(self.width()*.37, self.height()*.34)*.72
        x = clamp((point.x()-self.width()/2)/max(radius, 1), -1, 1)
        y = clamp((point.y()-self.height()/2)/max(radius, 1), -1, 1)
        magnitude = math.hypot(x, y)
        if magnitude > 1:
            x, y = x/magnitude, y/magnitude
        self.value = QPointF(x, y)
        self.callback(self.side, x, y)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self._move(event.position())
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self._move(event.position())
            event.accept()

    def mouseReleaseEvent(self, event):
        if self.dragging:
            self.dragging = False
            self.value = QPointF(0, 0)
            self.callback(self.side, 0, 0)
            self.update()
            event.accept()


class MousePad(QWidget):
    def __init__(self, client: BridgeClient, parent=None):
        super().__init__(parent)
        self.client = client
        self.last = self.origin = QPointF()
        self.pressed = self.moved = False
        self._touch_points = 0
        self._touch_scroll_y = None
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self.setMinimumHeight(205)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("MousePad{background:#0a1220;border:1px solid #2a3c59;border-radius:18px;}")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor("#6e83a5"))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "TOUCH & DRAG\nOne finger: move  ·  Two fingers: scroll")
        p.setPen(QPen(QColor("#1b2a42"), 1, Qt.PenStyle.DotLine))
        for x in range(20, self.width(), 28):
            p.drawLine(x, 18, x, self.height()-18)
        for y in range(18, self.height(), 28):
            p.drawLine(18, y, self.width()-18, y)

    def event(self, event):
        event_type = event.type()
        touch_types = (
            QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate,
            QEvent.Type.TouchEnd, QEvent.Type.TouchCancel,
        )
        if event_type not in touch_types:
            return super().event(event)

        points = event.points()
        if event_type == QEvent.Type.TouchBegin:
            self.pressed = bool(points)
            self.moved = False
            self._touch_points = len(points)
            self._touch_scroll_y = None
            if len(points) == 1:
                self.last = self.origin = points[0].position()
            elif len(points) >= 2:
                self.moved = True
                self._touch_scroll_y = sum(point.position().y() for point in points) / len(points)
        elif event_type == QEvent.Type.TouchUpdate and self.pressed:
            if len(points) >= 2:
                self.moved = True
                center_y = sum(point.position().y() for point in points) / len(points)
                if self._touch_scroll_y is not None:
                    delta = self._touch_scroll_y - center_y
                    if abs(delta) >= 3:
                        amount = int(delta / 18)
                        if amount:
                            self.client.scroll_mouse(amount)
                            self._touch_scroll_y = center_y
                else:
                    self._touch_scroll_y = center_y
            elif len(points) == 1 and self._touch_points == 1:
                point = points[0].position()
                dx, dy = point.x() - self.last.x(), point.y() - self.last.y()
                if abs(point.x() - self.origin.x()) + abs(point.y() - self.origin.y()) > 6:
                    self.moved = True
                if self.moved:
                    self.client.move_mouse(dx, dy)
                self.last = point
            self._touch_points = len(points)
        elif event_type in (QEvent.Type.TouchEnd, QEvent.Type.TouchCancel):
            if (event_type == QEvent.Type.TouchEnd and self.pressed
                    and not self.moved and self.client.tap_to_click and self.client.connected):
                self.client.set_mouse_button("left", True)
                QTimer.singleShot(90, lambda: self.client.set_mouse_button("left", False))
            self.pressed = False
            self.moved = False
            self._touch_points = 0
            self._touch_scroll_y = None
        event.accept()
        return True

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.pressed, self.moved = True, False
            self.last = self.origin = event.position()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.pressed:
            pos = event.position()
            dx, dy = pos.x()-self.last.x(), pos.y()-self.last.y()
            if abs(pos.x()-self.origin.x()) + abs(pos.y()-self.origin.y()) > 6:
                self.moved = True
            if self.moved:
                self.client.move_mouse(dx, dy)
            self.last = pos
            event.accept()

    def mouseReleaseEvent(self, event):
        if self.pressed:
            self.pressed = False
            if not self.moved and self.client.tap_to_click and self.client.connected:
                self.client.set_mouse_button("left", True)
                QTimer.singleShot(90, lambda: self.client.set_mouse_button("left", False))
            event.accept()

    def wheelEvent(self, event):
        amount = int(event.angleDelta().y()/120)
        if amount:
            self.client.scroll_mouse(amount)
        event.accept()


class PairingScanner(QDialog):
    pairingFound = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scan PC pairing QR")
        self.setMinimumSize(300, 440)
        self.camera = self.session = self.preview = None
        self.last_scan = 0.0
        self.decoder_failure_shown = False
        root = QVBoxLayout(self)
        root.addWidget(label("Secure PC pairing", "pageTitle"))
        root.addWidget(label("Aim the camera at the QR displayed in InputBridge → Server. The QR contains the PC address and public certificate fingerprint.", "muted"))
        if QVideoWidget is not None and QMediaCaptureSession is not None:
            self.preview = QVideoWidget()
            self.preview.setMinimumHeight(180)
            self.preview.setStyleSheet("background:#050811;border-radius:12px;")
            root.addWidget(self.preview)
            self._start_camera()
        else:
            root.addWidget(label("Qt Multimedia camera support is not available in this runtime.", "warning"))
        if decode_qr is None or np is None:
            status_text = "QR decoding support is unavailable in this runtime. Paste the complete pairing JSON below."
        else:
            status_text = "When you scan, Android will ask for camera access. Keep the full pairing QR centred in the frame."
        self.status = label(status_text, "muted")
        root.addWidget(self.status)
        self.text = QPlainTextEdit()
        self.text.setPlaceholderText("Paste complete InputBridge pairing JSON here")
        self.text.setMaximumHeight(95)
        root.addWidget(self.text)
        row = QHBoxLayout()
        use, paste, cancel = button("Use QR text", "primary"), button("Paste"), button("Cancel")
        use.clicked.connect(self._use_text)
        paste.clicked.connect(lambda: self.text.setPlainText(QApplication.clipboard().text()))
        cancel.clicked.connect(self.reject)
        row.addWidget(use, 2)
        row.addWidget(paste, 1)
        row.addWidget(cancel, 1)
        root.addLayout(row)

    def _start_camera(self):
        if QCamera is None or QMediaCaptureSession is None or QMediaDevices is None or self.preview is None:
            self.status.setText("This build does not include Qt Multimedia camera support. Paste the pairing JSON below.")
            return

        # Android permissions must be declared in the APK and requested only
        # after the user taps Scan. The CI-built package declares CAMERA.
        if is_android_runtime():
            app = QCoreApplication.instance()
            if app is None:
                self.status.setText("Camera permission service is unavailable. Paste the pairing JSON below.")
                return
            try:
                permission = QCameraPermission()
                status = app.checkPermission(permission)
                if status != Qt.PermissionStatus.Granted:
                    self.status.setText("Camera access is required to scan the pairing QR. Approve the Android permission prompt.")
                    app.requestPermission(permission, self, self._camera_permission_result)
                    return
            except Exception as exc:
                self.status.setText(f"Could not request camera permission: {exc}. Paste the pairing JSON below.")
                return

        self._open_camera()

    def _camera_permission_result(self, permission):
        if permission.status() != Qt.PermissionStatus.Granted:
            self.status.setText("Camera permission was denied. Enable Camera in Android app settings, or paste the complete pairing JSON below.")
            return
        self._open_camera()

    def _open_camera(self):
        if not self.isVisible() or self.camera is not None:
            return
        try:
            device = QMediaDevices.defaultVideoInput()
            if device.isNull():
                self.status.setText("No camera was found. Paste the complete pairing QR JSON below.")
                return
            self.camera = QCamera(self)
            self.camera.setCameraDevice(device)
            self.camera.errorOccurred.connect(self._camera_error)
            self.session = QMediaCaptureSession(self)
            self.session.setCamera(self.camera)
            self.session.setVideoOutput(self.preview)
            self.preview.videoSink().videoFrameChanged.connect(self._scan_frame)
            self.camera.start()
            if decode_qr is None or np is None:
                self.status.setText("Camera preview is running, but QR decoding is missing from this package. Paste the complete pairing JSON below.")
            else:
                self.status.setText("Camera active — centre the full QR code and hold the phone steady.")
        except Exception as exc:
            self.status.setText(f"Camera unavailable: {exc}. Paste the pairing JSON below.")

    def _camera_error(self, error, error_string):
        message = str(error_string).strip() or "The camera reported an error."
        self.status.setText(f"{message} Use the complete pairing JSON below if the camera cannot start.")

    def _scan_frame(self, frame):
        if decode_qr is None or np is None or time.monotonic()-self.last_scan < .3:
            return
        self.last_scan = time.monotonic()
        try:
            img = frame.toImage().convertToFormat(QImage.Format.Format_RGB888)
            width, height = img.width(), img.height()
            if width < 1 or height < 1:
                return
            raw = np.frombuffer(bytes(img.constBits()), dtype=np.uint8)
            stride = img.bytesPerLine()
            rows = raw[:height*stride].reshape((height, stride))
            rgb = rows[:, :width*3].reshape((height, width, 3))
            for code in decode_qr(np.ascontiguousarray(rgb)):
                payload = parse_pairing_qr_payload(code.data)
                if payload:
                    self.pairingFound.emit(payload)
                    self.accept()
                    return
        except Exception as exc:
            # Some Android builds can import pyzbar but lack its native zbar
            # dependency. Make this actionable instead of silently failing on
            # every video frame.
            if not self.decoder_failure_shown:
                self.decoder_failure_shown = True
                self.status.setText(f"QR decoding failed: {exc}. Paste the complete pairing JSON below.")
            return

    def _use_text(self):
        payload = parse_pairing_qr_payload(self.text.toPlainText())
        if not payload:
            QMessageBox.warning(self, "Invalid pairing QR", "Paste the full JSON payload from the desktop QR, not just its fingerprint.")
            return
        self.pairingFound.emit(payload)
        self.accept()

    def _stop_camera(self):
        if self.camera is not None:
            try:
                self.camera.stop()
            except Exception:
                pass

    def done(self, result):
        self._stop_camera()
        super().done(result)

    def closeEvent(self, event):
        self._stop_camera()
        super().closeEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(320, 580)
        self.client = BridgeClient()
        self.capabilities = {
            "pc_status": True, "keyboard": False, "media": False, "clipboard": False,
            "app_launch": False, "presentation": False, "power": False,
        }
        self.remote_controls: list[tuple[QPushButton, str]] = []
        self.sensor = None
        self.sensor_available = False
        self.last_accel_x = None
        self.client.connectionChanged.connect(self._connection_changed)
        self.client.connectingChanged.connect(self._connecting_changed)
        self.client.statusMessage.connect(self._status_message)
        self.client.remoteResponse.connect(self._remote_response)
        self._build_ui()
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self._periodic_state)
        self.timer.start()
        self._setup_sensor()
        self._connection_changed(False, "Ready — connect to the PC on the same Wi-Fi/LAN.")

    def _card(self, layout, title=""):
        frame, inside = card(title)
        layout.addWidget(frame)
        return inside

    def _build_ui(self):
        root = QWidget()
        v = QVBoxLayout(root)
        v.setContentsMargins(10, 9, 10, 9)
        v.setSpacing(9)
        header = QFrame()
        header.setObjectName("header")
        h = QHBoxLayout(header)
        h.setContentsMargins(14, 10, 14, 10)
        brand = QVBoxLayout()
        brand.addWidget(label("INPUTBRIDGE", "brand"))
        brand.addWidget(label("Mobile controller  ·  secure link", "tinyMuted"))
        h.addLayout(brand, 1)
        self.badge = label("DISCONNECTED", "badgeRed")
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setMinimumWidth(105)
        h.addWidget(self.badge)
        v.addWidget(header)
        self.stack = QStackedWidget()
        v.addWidget(self.stack, 1)
        nav = QFrame()
        nav.setObjectName("nav")
        nh = QHBoxLayout(nav)
        nh.setContentsMargins(4, 4, 4, 4)
        nh.setSpacing(4)
        self.nav_buttons = []
        for index, (symbol, name) in enumerate((("⌁", "Connect"), ("◎", "Gamepad"), ("▱", "Mouse"), ("⌨", "Remote"), ("⚙", "Settings"))):
            b = button(symbol + "\n" + name, "nav")
            b.setMinimumHeight(54)
            b.clicked.connect(lambda checked=False, i=index: self._select_tab(i))
            self.nav_buttons.append(b)
            nh.addWidget(b, 1)
        v.addWidget(nav)
        self.setCentralWidget(root)
        self.connect_page, self.connect_layout = scroll_page("Connect your PC", "Secure pairing with a saved certificate pin.")
        self.gamepad_page, self.gamepad_layout = scroll_page("Gamepad", "Responsive touch controls use the existing InputBridge protocol.")
        self.mouse_page, self.mouse_layout = scroll_page("Touch mouse", "A touchpad for Windows pointer movement, clicks and scrolling.")
        self.remote_page, self.remote_layout = scroll_page("PC Remote", "Only actions explicitly allowed by the desktop user are enabled.")
        self.settings_page, self.settings_layout = scroll_page("Preferences", "Tune controller motion, pointer feel and phone identity.")
        for page in (self.connect_page, self.gamepad_page, self.mouse_page, self.remote_page, self.settings_page):
            self.stack.addWidget(page)
        self._build_connect()
        self._build_gamepad()
        self._build_mouse()
        self._build_remote()
        self._build_settings()
        self._select_tab(0)

    def _build_connect(self):
        box = self._card(self.connect_layout, "Secure pairing")
        scan = button("▦  Scan pairing QR", "violet")
        scan.clicked.connect(self._scan_qr)
        box.addWidget(scan)
        self.name_input = QLineEdit(str(SETTINGS["name"]))
        self.host_input = QLineEdit(str(SETTINGS["last_host"]))
        self.host_input.setPlaceholderText("PC LAN IP address")
        self.port_input = QLineEdit(str(SETTINGS["last_port"]))
        self.port_input.setPlaceholderText("5000")
        self.pin_input = QLineEdit(load_pin(SETTINGS["last_host"], SETTINGS["last_port"]))
        self.pin_input.setPlaceholderText("SHA-256 fingerprint from the PC")
        form = QFormLayout()
        form.setSpacing(9)
        form.addRow("Device name", self.name_input)
        form.addRow("PC address", self.host_input)
        form.addRow("Server port", self.port_input)
        form.addRow("PC fingerprint", self.pin_input)
        box.addLayout(form)
        self.connect_button = button("Connect securely", "primary")
        self.connect_button.clicked.connect(self._connect_clicked)
        box.addWidget(self.connect_button)
        self.connect_status = label("Waiting for PC details.", "muted")
        box.addWidget(self.connect_status)
        auth = self._card(self.connect_layout, "First-time authorization")
        auth.addWidget(label("After TLS verification, enter the short pairing code shown beside this device in the desktop Server page.", "muted"))
        self.auth_input = QLineEdit()
        self.auth_input.setPlaceholderText("Pairing code")
        auth.addWidget(self.auth_input)
        submit = button("Submit pairing code", "primary")
        submit.clicked.connect(lambda: self.client.send_auth_code(self.auth_input.text()))
        auth.addWidget(submit)
        device = self._card(self.connect_layout, "Device identity")
        self.uuid_label = label("Device ID  ·  " + self.client.device_uuid, "tinyMuted")
        device.addWidget(self.uuid_label)
        device.addWidget(label("Device identity and server pins are saved in app-private storage.", "muted"))
        self.connect_layout.addStretch(1)

    def _build_gamepad(self):
        mode = self._card(self.gamepad_layout, "Controller mode")
        row = QHBoxLayout()
        self.standard_btn = button("Standard", "primary" if self.client.mode == "standard" else "normal")
        self.driving_btn = button("Driving", "primary" if self.client.mode == "driving" else "normal")
        self.standard_btn.clicked.connect(lambda: self._set_mode("standard"))
        self.driving_btn.clicked.connect(lambda: self._set_mode("driving"))
        row.addWidget(self.standard_btn)
        row.addWidget(self.driving_btn)
        mode.addLayout(row)
        sticks = self._card(self.gamepad_layout, "Analog sticks")
        row = QHBoxLayout()
        row.addWidget(StickPad("left", self.client.set_stick), 1)
        row.addWidget(StickPad("right", self.client.set_stick), 1)
        sticks.addLayout(row)
        triggers = self._card(self.gamepad_layout, "Analog triggers")
        for title, key in (("L2 · Left trigger", "L2"), ("R2 · Right trigger", "R2")):
            row = QHBoxLayout()
            row.addWidget(label(title))
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 255)
            slider.valueChanged.connect(lambda value, k=key: self.client.set_trigger(k, value))
            row.addWidget(slider, 1)
            triggers.addLayout(row)
        buttons = self._card(self.gamepad_layout, "Face buttons")
        grid = QGridLayout()
        for key, r, c, kind in (("Y", 0, 1, "yellow"), ("X", 1, 0, "violet"), ("B", 1, 2, "red"), ("A", 2, 1, "green")):
            b = button(key, kind)
            b.setMinimumHeight(53)
            b.pressed.connect(lambda k=key: self.client.set_button(k, True))
            b.released.connect(lambda k=key: self.client.set_button(k, False))
            grid.addWidget(b, r, c)
        buttons.addLayout(grid)
        extra = QGridLayout()
        for i, (title, key) in enumerate((("LB", "LB"), ("RB", "RB"), ("Back", "BACK"), ("Start", "START"), ("Guide", "GUIDE"), ("L3", "L3"), ("R3", "R3"))):
            b = button(title)
            b.pressed.connect(lambda k=key: self.client.set_button(k, True))
            b.released.connect(lambda k=key: self.client.set_button(k, False))
            extra.addWidget(b, i // 3, i % 3)
        buttons.addLayout(extra)
        buttons.addWidget(label("D-pad", "muted"))
        dpad = QGridLayout()
        for title, key, r, c in (("▲", "DPAD_UP", 0, 1), ("◀", "DPAD_LEFT", 1, 0), ("●", "", 1, 1), ("▶", "DPAD_RIGHT", 1, 2), ("▼", "DPAD_DOWN", 2, 1)):
            b = button(title, "primary" if key else "normal")
            if key:
                b.pressed.connect(lambda k=key: self.client.set_button(k, True))
                b.released.connect(lambda k=key: self.client.set_button(k, False))
            else:
                b.setEnabled(False)
            dpad.addWidget(b, r, c)
        buttons.addLayout(dpad)
        self.gamepad_layout.addStretch(1)

    def _build_mouse(self):
        pad = self._card(self.mouse_layout, "Trackpad")
        pad.addWidget(label("Drag to move the cursor. A short tap clicks when tap-to-click is enabled.", "muted"))
        pad.addWidget(MousePad(self.client))
        controls = self._card(self.mouse_layout, "Mouse buttons and wheel")
        row = QHBoxLayout()
        for title, key in (("Left", "left"), ("Right", "right"), ("Middle", "middle")):
            b = button(title, "primary" if key == "left" else "normal")
            b.pressed.connect(lambda k=key: self.client.set_mouse_button(k, True))
            b.released.connect(lambda k=key: self.client.set_mouse_button(k, False))
            row.addWidget(b)
        controls.addLayout(row)
        row = QHBoxLayout()
        up, down = button("Scroll up"), button("Scroll down")
        up.clicked.connect(lambda: self.client.scroll_mouse(3))
        down.clicked.connect(lambda: self.client.scroll_mouse(-3))
        row.addWidget(up)
        row.addWidget(down)
        controls.addLayout(row)
        self.mouse_layout.addStretch(1)

    def _remote_button(self, layout, title, action, payload=None, capability="keyboard", kind="normal", columns=3):
        b = button(title, kind)
        b.clicked.connect(lambda checked=False, a=action, p=payload or {}, c=capability: self._remote_request(a, p, c))
        if isinstance(layout, QGridLayout):
            count = layout.count()
            layout.addWidget(b, count // columns, count % columns)
        else:
            layout.addWidget(b)
        self.remote_controls.append((b, capability))
        return b

    def _build_remote(self):
        self.remote_controls = []
        pc = self._card(self.remote_layout, "Desktop status")
        self.pc_info = label("Connect to the PC and refresh its status.", "muted")
        pc.addWidget(self.pc_info)
        refresh = button("Refresh PC status", "primary")
        refresh.clicked.connect(lambda: self._remote_request("pc_status", {}, "pc_status"))
        pc.addWidget(refresh)
        keyboard = self._card(self.remote_layout, "Text and keyboard")
        self.remote_text = QPlainTextEdit()
        self.remote_text.setPlaceholderText("Text to type into the active PC application")
        self.remote_text.setMaximumHeight(90)
        keyboard.addWidget(self.remote_text)
        row = QHBoxLayout()
        send = button("Send text", "primary")
        send.clicked.connect(lambda: self._remote_request("keyboard_text", {"text": self.remote_text.toPlainText()}, "keyboard"))
        clear = button("Clear")
        clear.clicked.connect(self.remote_text.clear)
        row.addWidget(send)
        row.addWidget(clear)
        keyboard.addLayout(row)
        self.remote_controls.append((send, "keyboard"))
        keys = QGridLayout()
        for title, key in (("Enter", "ENTER"), ("Tab", "TAB"), ("Esc", "ESCAPE"), ("Backspace", "BACKSPACE"), ("←", "LEFT"), ("↑", "UP"), ("↓", "DOWN"), ("→", "RIGHT")):
            self._remote_button(keys, title, "keyboard_key", {"key": key}, "keyboard", columns=4)
        keyboard.addLayout(keys)
        mods = QHBoxLayout()
        for title, key in (("Ctrl", "CTRL"), ("Shift", "SHIFT"), ("Alt", "ALT"), ("Win", "WIN")):
            b = button(title)
            b.pressed.connect(lambda k=key: self._remote_request("keyboard_modifier", {"key": k, "pressed": True}, "keyboard"))
            b.released.connect(lambda k=key: self._remote_request("keyboard_modifier", {"key": k, "pressed": False}, "keyboard"))
            mods.addWidget(b)
            self.remote_controls.append((b, "keyboard"))
        keyboard.addLayout(mods)
        shortcuts = self._card(self.remote_layout, "Quick shortcuts")
        grid = QGridLayout()
        for title, key in (("Copy", "copy"), ("Paste", "paste"), ("Cut", "cut"), ("Undo", "undo"), ("Select all", "select_all"), ("Save", "save"), ("Find", "find"), ("Alt + Tab", "alt_tab"), ("Show desktop", "show_desktop")):
            self._remote_button(grid, title, "keyboard_shortcut", {"shortcut": key}, "keyboard")
        shortcuts.addLayout(grid)
        media = self._card(self.remote_layout, "Media and volume")
        grid = QGridLayout()
        for title, command in (("Vol −", "volume_down"), ("Mute", "mute"), ("Vol +", "volume_up"), ("Previous", "previous_track"), ("Play / Pause", "play_pause"), ("Next", "next_track"), ("Stop", "stop")):
            self._remote_button(grid, title, "media", {"command": command}, "media")
        media.addLayout(grid)
        clipboard = self._card(self.remote_layout, "Clipboard")
        self.clipboard_text = QPlainTextEdit()
        self.clipboard_text.setPlaceholderText("Text to send to PC, or text read from PC clipboard")
        self.clipboard_text.setMaximumHeight(85)
        clipboard.addWidget(self.clipboard_text)
        row = QHBoxLayout()
        copy = button("Copy to PC", "primary")
        copy.clicked.connect(lambda: self._remote_request("clipboard_set", {"text": self.clipboard_text.toPlainText()}, "clipboard"))
        row.addWidget(copy)
        self.remote_controls.append((copy, "clipboard"))
        self._remote_button(row, "Read PC clipboard", "clipboard_get", {}, "clipboard")
        clipboard.addLayout(row)
        apps = self._card(self.remote_layout, "Approved applications")
        grid = QGridLayout()
        for title, app in (("Browser", "browser"), ("Explorer", "explorer"), ("Calculator", "calculator"), ("Notepad", "notepad"), ("Downloads", "downloads")):
            self._remote_button(grid, title, "launch_app", {"app": app}, "app_launch")
        apps.addLayout(grid)
        presentation = self._card(self.remote_layout, "Presentation")
        grid = QGridLayout()
        for title, command in (("Previous", "previous"), ("Next", "next"), ("Start", "start"), ("End", "end"), ("Black screen", "black_screen")):
            self._remote_button(grid, title, "presentation", {"command": command}, "presentation")
        presentation.addLayout(grid)
        power = self._card(self.remote_layout, "Power actions")
        grid = QGridLayout()
        for title, command in (("Lock", "lock"), ("Sleep", "sleep"), ("Display off", "display_off"), ("Log off", "logoff"), ("Restart", "restart"), ("Shut down", "shutdown")):
            b = button(title, "danger" if command in ("logoff", "restart", "shutdown") else "normal")
            b.clicked.connect(lambda checked=False, cmd=command: self._confirm_power(cmd))
            n = grid.count()
            grid.addWidget(b, n // 3, n % 3)
            self.remote_controls.append((b, "power"))
        power.addLayout(grid)
        self.remote_result = label("Remote actions require an authenticated connection and explicit PC permissions.", "muted")
        self.remote_layout.addWidget(self.remote_result)
        self.remote_layout.addStretch(1)
        self._update_remote_controls()

    def _build_settings(self):
        identity = self._card(self.settings_layout, "Device identity")
        identity.addWidget(label("Name shown in the desktop Server page", "muted"))
        self.settings_name = QLineEdit(self.client.device_name)
        identity.addWidget(self.settings_name)
        save = button("Save device name", "primary")
        save.clicked.connect(self._save_name)
        identity.addWidget(save)
        tune = self._card(self.settings_layout, "Controller tuning")
        row = QHBoxLayout()
        std, drive = button("Standard"), button("Driving")
        std.clicked.connect(lambda: self._set_mode("standard"))
        drive.clicked.connect(lambda: self._set_mode("driving"))
        row.addWidget(std)
        row.addWidget(drive)
        tune.addLayout(row)
        self.gyro_label = label("Checking motion sensor…", "muted")
        tune.addWidget(self.gyro_label)
        row = QHBoxLayout()
        self.gyro_button = button("Enable motion steering", "violet")
        self.calibrate_button = button("Calibrate centre")
        self.gyro_button.clicked.connect(self._toggle_gyro)
        self.calibrate_button.clicked.connect(self._calibrate_gyro)
        row.addWidget(self.gyro_button)
        row.addWidget(self.calibrate_button)
        tune.addLayout(row)
        self.sensitivity_label = label(f"Steering sensitivity · {self.client.steering_sensitivity:.1f}×", "muted")
        tune.addWidget(self.sensitivity_label)
        steer_slider = QSlider(Qt.Orientation.Horizontal)
        steer_slider.setRange(5, 40)
        steer_slider.setValue(int(self.client.steering_sensitivity*10))
        steer_slider.valueChanged.connect(self._steering_sensitivity_changed)
        tune.addWidget(steer_slider)
        mouse = self._card(self.settings_layout, "Touch mouse")
        self.mouse_sensitivity_label = label(f"Pointer sensitivity · {self.client.mouse_sensitivity:.1f}×", "muted")
        mouse.addWidget(self.mouse_sensitivity_label)
        mouse_slider = QSlider(Qt.Orientation.Horizontal)
        mouse_slider.setRange(5, 40)
        mouse_slider.setValue(int(self.client.mouse_sensitivity*10))
        mouse_slider.valueChanged.connect(self._mouse_sensitivity_changed)
        mouse.addWidget(mouse_slider)
        tap = QCheckBox("Tap the trackpad to click")
        tap.setChecked(self.client.tap_to_click)
        tap.toggled.connect(self._tap_changed)
        mouse.addWidget(tap)
        security = self._card(self.settings_layout, "Security")
        security.addWidget(label("TLS certificate pinning verifies the PC before state is sent. The desktop app controls permissions for keyboard, clipboard, media, apps, presentation and power actions.", "muted"))
        self.settings_layout.addStretch(1)

    def _select_tab(self, index):
        self.stack.setCurrentIndex(index)
        for i, b in enumerate(self.nav_buttons):
            b.setProperty("selected", i == index)
            b.style().unpolish(b)
            b.style().polish(b)
        if index == 3 and self.client.connected:
            self._remote_request("pc_status", {}, "pc_status")

    def _scan_qr(self):
        scanner = PairingScanner(self)
        scanner.pairingFound.connect(self._apply_pairing)
        scanner.exec()

    def _apply_pairing(self, payload):
        self.host_input.setText(payload["host"])
        self.port_input.setText(payload["port"])
        self.pin_input.setText(payload["fingerprint"])
        self.connect_status.setText("QR read. Verifying PC certificate…")
        self.client.connect_to(payload["host"], payload["port"], self.name_input.text(), payload["fingerprint"])

    def _connect_clicked(self):
        if self.client.connected:
            self.client.disconnect()
        else:
            self.client.connect_to(self.host_input.text(), self.port_input.text(), self.name_input.text(), self.pin_input.text())

    def _connection_changed(self, connected, message):
        self.badge.setText("CONNECTED" if connected else "DISCONNECTED")
        self.badge.setProperty("role", "badgeGreen" if connected else "badgeRed")
        self.badge.style().unpolish(self.badge)
        self.badge.style().polish(self.badge)
        self.connect_status.setText(message)
        self.connect_button.setText("Disconnect" if connected else "Connect securely")
        self.connect_button.setProperty("kind", "danger" if connected else "primary")
        self.connect_button.style().unpolish(self.connect_button)
        self.connect_button.style().polish(self.connect_button)
        if not connected:
            self.client.gyro_enabled = False
            if self.sensor is not None:
                try:
                    self.sensor.stop()
                except Exception:
                    pass
            self.gyro_label.setText("Motion steering disabled while disconnected.")
            self.gyro_button.setText("Enable motion steering")
        self._update_remote_controls()

    def _connecting_changed(self, busy):
        self.connect_button.setEnabled(not busy)
        if busy:
            self.connect_button.setText("Connecting securely…")
        else:
            self.connect_button.setText("Disconnect" if self.client.connected else "Connect securely")

    def _status_message(self, message):
        if not self.client.connected:
            self.connect_status.setText(message)
        self.remote_result.setText(message)

    def _periodic_state(self):
        if self.client.connected:
            self.client.send_state()
            self.client._expire_requests()

    def _set_mode(self, mode):
        self.client.set_mode(mode)
        for b, value in ((self.standard_btn, "standard"), (self.driving_btn, "driving")):
            b.setProperty("kind", "primary" if value == mode else "normal")
            b.style().unpolish(b)
            b.style().polish(b)

    def _save_name(self):
        self.client.set_device_name(self.settings_name.text())
        self.name_input.setText(self.client.device_name)
        self.uuid_label.setText("Device ID  ·  " + self.client.device_uuid)
        self.connect_status.setText("Device name saved.")

    def _steering_sensitivity_changed(self, value):
        self.client.steering_sensitivity = value/10
        SETTINGS["steering_sensitivity"] = self.client.steering_sensitivity
        save_settings()
        self.sensitivity_label.setText(f"Steering sensitivity · {self.client.steering_sensitivity:.1f}×")

    def _mouse_sensitivity_changed(self, value):
        self.client.mouse_sensitivity = value/10
        SETTINGS["mouse_sensitivity"] = self.client.mouse_sensitivity
        save_settings()
        self.mouse_sensitivity_label.setText(f"Pointer sensitivity · {self.client.mouse_sensitivity:.1f}×")

    def _tap_changed(self, checked):
        self.client.tap_to_click = checked
        SETTINGS["tap_to_click"] = checked
        save_settings()

    def _setup_sensor(self):
        if QAccelerometer is None:
            self.gyro_label.setText("Motion steering unavailable: QtSensors is not present in this runtime.")
            self.gyro_button.setEnabled(False)
            self.calibrate_button.setEnabled(False)
            return
        try:
            self.sensor = QAccelerometer(self)
            self.sensor.setDataRate(30)
            self.sensor.readingChanged.connect(self._sensor_changed)
            self.sensor_available = True
            self.gyro_label.setText("Motion sensor found. Enable motion steering while connected.")
        except Exception as exc:
            self.gyro_label.setText(f"Motion sensor unavailable: {exc}")
            self.gyro_button.setEnabled(False)
            self.calibrate_button.setEnabled(False)

    def _toggle_gyro(self):
        if not self.sensor_available or self.sensor is None:
            return
        if not self.client.gyro_enabled:
            try:
                self.sensor.start()
                self.client.gyro_enabled = True
                self.gyro_button.setText("Disable motion steering")
                self.gyro_label.setText("Enabled. Hold the phone at neutral and calibrate centre.")
            except Exception as exc:
                self.client.gyro_enabled = False
                self.gyro_label.setText(f"Could not start sensor: {exc}")
        else:
            self.client.gyro_enabled = False
            self.client.gyro_steer = 0.0
            self.sensor.stop()
            self.gyro_button.setText("Enable motion steering")
            self.gyro_label.setText("Motion steering disabled.")
        self.client.send_state()

    def _calibrate_gyro(self):
        if not self.client.gyro_enabled or self.last_accel_x is None:
            self.gyro_label.setText("Enable motion steering and wait for a sensor reading.")
            return
        self.client.gyro_neutral = self.last_accel_x
        self.client.gyro_steer = 0.0
        self.client.joystick["left_x"] = 128
        self.client.send_state()
        self.gyro_label.setText("Steering centre calibrated.")

    def _sensor_changed(self):
        reading = self.sensor.reading() if self.sensor else None
        if reading is None:
            return
        try:
            x = float(reading.x())
        except Exception:
            return
        self.last_accel_x = x
        if not self.client.gyro_enabled or self.client.mode != "driving":
            return
        if self.client.gyro_neutral is None:
            self.client.gyro_neutral = x
        delta = x - self.client.gyro_neutral
        target = clamp(delta / (2.2 / max(self.client.steering_sensitivity, .1)), -1, 1)
        self.client.gyro_steer = self.client.gyro_steer * .78 + target * .22
        self.client.joystick["left_x"] = int(round(128 + self.client.gyro_steer * 127))
        self.client.send_state()

    def _remote_request(self, action, payload, capability):
        if not self.client.connected:
            self.remote_result.setText("Connect to the PC first.")
            return
        if capability != "pc_status" and not self.capabilities.get(capability, False):
            self.remote_result.setText(f"The PC has not enabled the {capability} permission.")
            return
        request_id = self.client.send_remote_action(action, payload)
        self.remote_result.setText(
            f"Waiting for PC confirmation: {action.replace('_', ' ')}…" if request_id
            else "Could not send the command. Check the secure link."
        )

    def _update_remote_controls(self):
        if not hasattr(self, "remote_result"):
            return
        if not self.client.connected:
            self.capabilities = {"pc_status": True, "keyboard": False, "media": False, "clipboard": False,
                                 "app_launch": False, "presentation": False, "power": False}
            self.pc_info.setText("Connect to PC and refresh its status.")
        for b, cap in self.remote_controls:
            b.setEnabled(self.client.connected and bool(self.capabilities.get(cap, False)))
        for b in self.remote_page.findChildren(QPushButton):
            if b.text() == "Refresh PC status":
                b.setEnabled(self.client.connected)

    def _remote_response(self, response):
        action = response.get("action", "remote action")
        if not response.get("ok"):
            self.remote_result.setText(f"PC rejected {action.replace('_', ' ')}: {response.get('error', 'Unknown error')}")
            return
        result = response.get("result") or {}
        if action == "pc_status":
            received = result.get("capabilities", {})
            if isinstance(received, dict):
                for cap in self.capabilities:
                    if cap in received:
                        self.capabilities[cap] = bool(received[cap])
            self.pc_info.setText(
                f"{result.get('computer_name', 'PC')} · {result.get('operating_system', 'OS unavailable')}\n"
                f"Local time: {result.get('local_time', 'Unavailable')}"
            )
            self._update_remote_controls()
            self.remote_result.setText("PC status received. Permissions reflect desktop settings.")
        elif action == "clipboard_get":
            self.clipboard_text.setPlainText(str(result.get("text", "")))
            self.remote_result.setText("PC clipboard received" + (" (truncated)" if result.get("truncated") else ""))
        else:
            self.remote_result.setText(f"PC confirmed: {action.replace('_', ' ')}")

    def _confirm_power(self, command):
        if not self.client.connected or not self.capabilities.get("power", False):
            self.remote_result.setText("Power actions are not enabled by the PC.")
            return
        if command == "lock":
            self._remote_request("power_action", {"command": command}, "power")
            return
        details = {"sleep": "Put the PC into sleep mode.", "display_off": "Turn off the PC display.",
                   "logoff": "Sign out of Windows.", "restart": "Restart Windows.",
                   "shutdown": "Shut down Windows. Unsaved work may be lost."}
        answer = QMessageBox.question(
            self, "Confirm PC action", details.get(command, "Run this system action?"),
            QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._remote_request("power_action", {"command": command}, "power")

    def closeEvent(self, event):
        if self.sensor is not None:
            try:
                self.sensor.stop()
            except Exception:
                pass
        self.client.disconnect()
        super().closeEvent(event)


STYLESHEET = f"""
QWidget {{ background: {PALETTE['bg']}; color: {PALETTE['text']}; font-size: 14px; }}
QMainWindow {{ background: {PALETTE['bg']}; }}
QFrame#header, QFrame#nav {{ background: #0d1524; border: 1px solid {PALETTE['line']}; border-radius: 16px; }}
QFrame#card {{ background: {PALETTE['surface']}; border: 1px solid {PALETTE['line']}; border-radius: 17px; }}
QLabel {{ background: transparent; }}
QLabel[role="brand"] {{ color: #dfeaff; font-size: 19px; font-weight: 800; letter-spacing: 1px; }}
QLabel[role="pageTitle"] {{ color: {PALETTE['text']}; font-size: 24px; font-weight: 750; }}
QLabel[role="cardTitle"] {{ color: #eaf1ff; font-size: 16px; font-weight: 700; }}
QLabel[role="muted"] {{ color: {PALETTE['muted']}; font-size: 13px; }}
QLabel[role="tinyMuted"] {{ color: {PALETTE['subtle']}; font-size: 11px; }}
QLabel[role="warning"] {{ color: {PALETTE['yellow']}; }}
QLabel[role="badgeGreen"] {{ color: {PALETTE['green']}; font-size: 11px; font-weight: 800; }}
QLabel[role="badgeRed"] {{ color: {PALETTE['red']}; font-size: 11px; font-weight: 800; }}
QPushButton {{ color: #eaf1ff; background: #1b2940; border: 1px solid #30435f; border-radius: 12px; padding: 9px; font-weight: 650; }}
QPushButton:pressed {{ background: #263b5a; }}
QPushButton:disabled {{ color: #52627c; background: #101927; border-color: #1c2a3e; }}
QPushButton[kind="primary"] {{ background: #2769df; border-color: #4685f6; color: white; }}
QPushButton[kind="violet"] {{ background: #563abd; border-color: #8d70ff; color: white; }}
QPushButton[kind="green"] {{ background: #176e58; border-color: #35d39a; color: white; }}
QPushButton[kind="red"], QPushButton[kind="danger"] {{ background: #7d2c42; border-color: #d54d6a; color: white; }}
QPushButton[kind="yellow"] {{ background: #705b1f; border-color: #c5a13f; color: white; }}
QPushButton[kind="nav"] {{ background: #111a2b; border: 1px solid transparent; color: #9aabc4; font-size: 11px; padding: 5px 2px; }}
QPushButton[kind="nav"][selected="true"] {{ background: #203653; border-color: #4f8cff; color: white; }}
QLineEdit, QPlainTextEdit {{ background: #0b1423; border: 1px solid #30435f; border-radius: 10px; color: {PALETTE['text']}; padding: 9px; selection-background-color: #2769df; }}
QLineEdit:focus, QPlainTextEdit:focus {{ border: 1px solid #4f8cff; }}
QCheckBox {{ spacing: 8px; color: {PALETTE['muted']}; }}
QSlider::groove:horizontal {{ height: 5px; background: #293850; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: #4f8cff; border-radius: 2px; }}
QSlider::handle:horizontal {{ width: 17px; margin: -7px 0; border-radius: 8px; background: #f4f7ff; border: 2px solid #4f8cff; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ width: 5px; background: transparent; }}
QScrollBar::handle:vertical {{ background: #35445c; border-radius: 2px; min-height: 20px; }}
QMessageBox {{ background: {PALETTE['surface']}; }}
"""


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("ArvinNotDev")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    app.setFont(QFont("Inter", 10))
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
