import sys
import socket
import json
import threading
import hashlib
import secrets
import os
import tempfile
import time
from math import ceil
from pathlib import Path
from typing import Optional, Dict, Tuple
from core.settings import SettingsManager

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QHBoxLayout, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QObject, QSize, QTimer

from core.mapper import Phone_mapper
from core.utils.paths import data_path


HOST = "0.0.0.0"
PORT = 5000
TRUSTED_FILE = data_path("trusted_clients.json")
MAX_CLIENTS = 8
MAX_FRAME_BYTES = 16 * 1024
MAX_CLIENT_NAME_LENGTH = 64
MAX_CLIENT_UUID_LENGTH = 128
BUTTON_KEYS = {
    "A", "B", "X", "Y", "LB", "RB", "BACK", "START", "GUIDE", "L3", "R3",
    "DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT",
}
ANALOG_KEYS = {"L2", "R2"}
JOYSTICK_KEYS = {"left_x", "left_y", "right_x", "right_y"}


# ---------------------------------------------------------

def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
    except Exception:
        ip = "Unavailable"
    return f"{ip}:{PORT}"


def hash_uuid(uuid_str: str) -> str:
    return hashlib.sha256(uuid_str.encode("utf-8")).hexdigest()


def load_trusted() -> dict:
    if TRUSTED_FILE.exists():
        try:
            with TRUSTED_FILE.open("r", encoding="utf-8") as f:
                stored = json.load(f)
            if not isinstance(stored, dict):
                return {}

            # New format is UUID hash -> display name. Migrate the legacy
            # display name -> UUID hash format in memory without losing trust.
            trusted = {}
            for key, value in stored.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    continue
                if len(key) == 64 and all(c in "0123456789abcdefABCDEF" for c in key):
                    trusted[key.lower()] = value[:MAX_CLIENT_NAME_LENGTH]
                elif len(value) == 64 and all(c in "0123456789abcdefABCDEF" for c in value):
                    trusted[value.lower()] = key[:MAX_CLIENT_NAME_LENGTH]
            return trusted
        except Exception:
            pass
    return {}


def save_trusted(trusted_data: dict):
    TRUSTED_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=TRUSTED_FILE.parent,
            prefix=f"{TRUSTED_FILE.name}.", suffix=".tmp", delete=False,
        ) as f:
            temporary_path = Path(f.name)
            json.dump(trusted_data, f, indent=4, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary_path, TRUSTED_FILE)
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def _bounded_numeric_map(value, allowed_keys, minimum, maximum, *, allow_bool=False):
    if not isinstance(value, dict):
        return None
    normalized = {}
    for key, item in value.items():
        if key not in allowed_keys:
            continue
        if allow_bool and isinstance(item, bool):
            normalized[key] = int(item)
            continue
        if type(item) is not int or not minimum <= item <= maximum:
            return None
        normalized[key] = item
    return normalized


def validate_client_message(message):
    """Return a bounded, normalized gamepad message, or None if it is invalid."""
    if not isinstance(message, dict):
        return None

    client_uuid = message.get("uuid")
    client_name = message.get("name")
    if (
        not isinstance(client_uuid, str)
        or not client_uuid.strip()
        or len(client_uuid) > MAX_CLIENT_UUID_LENGTH
        or any(ord(char) < 32 for char in client_uuid)
        or not isinstance(client_name, str)
        or not client_name.strip()
        or len(client_name.strip()) > MAX_CLIENT_NAME_LENGTH
        or any(ord(char) < 32 for char in client_name)
    ):
        return None

    buttons = _bounded_numeric_map(
        message.get("buttons", {}), BUTTON_KEYS, 0, 1, allow_bool=True
    )
    analog = _bounded_numeric_map(message.get("analog", {}), ANALOG_KEYS, 0, 255)
    joystick = _bounded_numeric_map(
        message.get("joystick", {}), JOYSTICK_KEYS, 0, 255
    )
    if buttons is None or analog is None or joystick is None:
        return None

    auth_code = message.get("auth_code")
    if auth_code is not None and (
        not isinstance(auth_code, str) or len(auth_code) > 32
    ):
        return None

    return {
        "uuid": client_uuid.strip(),
        "name": client_name.strip(),
        "auth_code": auth_code,
        "buttons": buttons,
        "analog": analog,
        "joystick": joystick,
    }


class ServerSignals(QObject):
    log_message = Signal(str)
    client_connected = Signal(tuple)            # addr
    client_disconnected = Signal(tuple)         # addr
    client_uuid_updated = Signal(tuple, str)    # addr, uuid

    # Now we send addr + code + time_left for UI per client
    show_auth_code = Signal(tuple, str, int)    # addr, code, time_left

    trusted_client_added = Signal(str)          # name
    remote_mapper_added = Signal(object)         # emulator instance
    server_started = Signal()
    server_failed = Signal(str)


class TrustedItemWidget(QWidget):
    remove_requested = Signal(str)

    def __init__(self, identity: str, name: str, parent=None):
        super().__init__(parent)
        self.identity = identity
        self.name = name

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)

        self.lbl_name = QLabel(name)
        self.lbl_name.setTextFormat(Qt.PlainText)
        self.lbl_name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.lbl_name)

        self.btn_remove = QPushButton("Remove")
        self.btn_remove.setFixedWidth(80)
        self.btn_remove.setStyleSheet(
            "background-color: #ef4444; color: white; border-radius: 4px; padding: 4px;"
        )
        self.btn_remove.clicked.connect(self._on_remove_clicked)
        layout.addWidget(self.btn_remove)

    def _on_remove_clicked(self):
        self.remove_requested.emit(self.identity)


class ClientListItemWidget(QWidget):
    emulate_requested = Signal(object)
    delete_requested = Signal(object)

    def __init__(self, conn_key, addr_str: str, uuid: str = "unknown", parent=None):
        super().__init__(parent)
        self.conn_key = conn_key
        self.addr_str = addr_str
        self.uuid = uuid
        self._running = False

        # --- NEW: auth code + timer UI state ---
        self.auth_code: Optional[str] = None
        self.auth_time_left: int = 0  # seconds

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)

        self.lbl_text = QLabel(self._build_label_text())
        self.lbl_text.setTextFormat(Qt.PlainText)
        self.lbl_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.lbl_text)

        # NEW: Auth label
        self.lbl_auth = QLabel("")
        self.lbl_auth.setStyleSheet("color: #dc2626; font-weight: 500;")
        self.lbl_auth.setMinimumWidth(150)
        layout.addWidget(self.lbl_auth)

        self.btn_emulate = QPushButton("Emulate")
        self.btn_emulate.setFixedWidth(90)
        self.btn_emulate.clicked.connect(self._on_emulate_clicked)
        layout.addWidget(self.btn_emulate)

        self.btn_delete = QPushButton("Disconnect")
        self.btn_delete.setFixedWidth(90)
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        layout.addWidget(self.btn_delete)

        self.status = QLabel()
        self.status.setFixedSize(14, 14)
        self._update_status_style(False)
        layout.addWidget(self.status, alignment=Qt.AlignRight | Qt.AlignVCenter)

    def _build_label_text(self) -> str:
        return f"{self.addr_str}  (uuid: {self.uuid})"

    def _update_status_style(self, running: bool):
        color = "#2ecc71" if running else "#9aa0a6"
        self.status.setStyleSheet(
            f"border-radius: 7px; background-color: {color};"
        )

    def set_running(self, running: bool):
        self._running = bool(running)
        self._update_status_style(self._running)
        self.btn_emulate.setText("Stop" if self._running else "Emulate")

    def is_running(self) -> bool:
        return self._running

    def update_uuid(self, uuid: str):
        self.uuid = uuid
        self.lbl_text.setText(self._build_label_text())

    # ---------- Auth/timer helpers ----------

    def set_auth_info(self, code: str, time_left: int):
        """Set or update auth code and remaining time."""
        # If code is empty, we treat this as clear
        if not code:
            self.clear_auth_info()
            return
        self.auth_code = code
        self.auth_time_left = max(0, time_left)
        self._refresh_auth_label()

    def decrement_auth_timer(self):
        """Decrease timer by one second and refresh label."""
        if self.auth_code is None:
            return
        if self.auth_time_left > 0:
            self.auth_time_left -= 1
        self._refresh_auth_label()

    def clear_auth_info(self):
        """Clear auth code and hide label."""
        self.auth_code = None
        self.auth_time_left = 0
        self.lbl_auth.setText("")

    def _refresh_auth_label(self):
        if self.auth_code is None:
            self.lbl_auth.setText("")
        else:
            self.lbl_auth.setText(
                f"Auth: {self.auth_code}  ({self.auth_time_left}s)"
            )

    # ---------- Button handlers ----------

    def _on_emulate_clicked(self):
        # Toggle locally first so UI is responsive
        self.set_running(not self._running) if False else self.set_running(not self._running)
        self.emulate_requested.emit(self.conn_key)

    def _on_delete_clicked(self):
        self.delete_requested.emit(self.conn_key)


class ServerPage(QWidget):
    def __init__(self, settings, controllers_page, hotkey_page):
        super().__init__()
        self.setWindowTitle("Server Control")
        self.setMinimumSize(700, 600)

        self.server_socket: Optional[socket.socket] = None
        self.server_thread: Optional[threading.Thread] = None
        self.server_running = False
        self.stop_event = threading.Event()
        self.client_threads: Dict[tuple, threading.Thread] = {}
        self._state_lock = threading.RLock()
        self.tray_status_callback = None
        self._is_shutting_down = False
        self.signals = ServerSignals()
        self.settings = settings
        self.controllers_page = controllers_page
        self.hotkey_page = hotkey_page

        # conn_key -> (conn, addr, uuid)
        self.clients: Dict[tuple, Tuple[socket.socket, tuple, str]] = {}
        # conn_key -> bool
        self.emulation_states: Dict[tuple, bool] = {}

        # conn_key -> {"code": str, "time_left": int, "authenticated": bool, "expired": bool}
        self.auth_states: Dict[tuple, Dict[str, object]] = {}

        self.trusted_data = load_trusted()

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(40, 20, 40, 20)

        self.ip_label = QLabel(f"Local IP: {get_local_ip()}")
        self.ip_label.setAlignment(Qt.AlignCenter)
        self.ip_label.setObjectName("ipLabel")

        self.clients_label = QLabel("Connected Clients")
        self.clients_label.setAlignment(Qt.AlignCenter)
        self.clients_label.setObjectName("sectionLabel")

        self.clients_list = QListWidget()
        self.clients_list.setFixedHeight(220)

        self.trusted_label = QLabel("Trusted Platforms")
        self.trusted_label.setAlignment(Qt.AlignCenter)
        self.trusted_label.setObjectName("sectionLabel")

        self.trusted_list = QListWidget()
        self.trusted_list.setFixedHeight(220)

        self.button = QPushButton("Start Server")
        self.button.setCursor(Qt.PointingHandCursor)
        self.button.setFixedHeight(45)
        self.button.clicked.connect(self.toggle_server)
        self.button.setObjectName("serverButton")
        self.button.setProperty("running", False)  # initial state


        layout.addWidget(self.ip_label)
        layout.addWidget(self.clients_label)
        layout.addWidget(self.clients_list)
        layout.addWidget(self.trusted_label)
        layout.addWidget(self.trusted_list)
        layout.addWidget(self.button)

        self.setLayout(layout)

        self.setStyleSheet(
            """
        #ipLabel {
            font-size: 22px;
            font-weight: 600;
            color: #38bdf8;
        }

        #infoLabel {
            font-size: 14px;
            color: #94a3b8;
        }

        #serverButton {
            background-color: #2563eb;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            color: white;
        }

        #serverButton:hover {
            background-color: #3b82f6;
        }

        #serverButton:pressed {
            background-color: #1d4ed8;
        }

        /* Running (red) variant, we’ll set this inline at runtime */
        #serverButton[running="true"] {
            background-color: #dc2626;
        }
        #serverButton[running="true"]:hover {
            background-color: #ef4444;
        }
        #serverButton[running="true"]:pressed {
            background-color: #b91c1c;
        }

        #sectionLabel {
            font-size: 14px;
            font-weight: 600;
            margin-top: 8px;
            margin-bottom: 4px;
        }
        QListWidget {
            border: 1px solid #d1d5db;
            border-radius: 6px;
            color: #000000;
            padding: 10px;
        }
        QLabel {
            font-weight: normal;
        }
        QListWidget::item {
                padding: 0px;
                color: #000000;
                background-color: transparent;
        }
        """
        )


        # Connect signals
        self.signals.client_connected.connect(self._on_client_connected_ui)
        self.signals.client_disconnected.connect(self._on_client_disconnected_ui)
        self.signals.client_uuid_updated.connect(self._on_client_uuid_updated_ui)
        self.signals.show_auth_code.connect(self._on_show_auth_code_ui)
        self.signals.trusted_client_added.connect(self._on_trusted_client_added_ui)
        self.signals.remote_mapper_added.connect(self._on_remote_mapper_added_ui)
        self.signals.server_started.connect(self._on_server_started)
        self.signals.server_failed.connect(self._on_server_failed)

        # Populate trusted list
        self.refresh_trusted_ui()

        # NEW: global timer to update auth countdowns every second
        self.auth_timer = QTimer(self)
        self.auth_timer.timeout.connect(self._on_auth_timer_tick)
        self.auth_timer.start(1000)  # 1 second

    # ---------- Trusted List UI ----------

    def refresh_trusted_ui(self):
        self.trusted_list.clear()
        with self._state_lock:
            trusted_clients = list(self.trusted_data.items())
        for identity, name in trusted_clients:
            self._add_trusted_item_to_ui(identity, name)

    def _add_trusted_item_to_ui(self, identity: str, name: str):
        item = QListWidgetItem(self.trusted_list)
        widget = TrustedItemWidget(identity, name)
        sh = widget.sizeHint()
        if sh.height() < 40:
            sh.setHeight(40)
        item.setSizeHint(sh)
        self.trusted_list.setItemWidget(item, widget)
        widget.remove_requested.connect(self._on_remove_trusted_requested)

    def _on_remove_trusted_requested(self, identity: str):
        with self._state_lock:
            if identity not in self.trusted_data:
                return
            trusted_snapshot = dict(self.trusted_data)
            del trusted_snapshot[identity]
            try:
                save_trusted(trusted_snapshot)
            except OSError as exc:
                QMessageBox.warning(self, "Storage Error", str(exc))
                return
            self.trusted_data = trusted_snapshot
        self.refresh_trusted_ui()

    def _on_show_auth_code_ui(self, addr: tuple, code: str, time_left: int):
        """Show/refresh auth code+timer on the client row instead of QMessageBox."""
        item = self._find_item_by_conn_key(addr)
        if not item:
            return
        widget = self.clients_list.itemWidget(item)
        if isinstance(widget, ClientListItemWidget):
            widget.set_auth_info(code, time_left)

    def _on_trusted_client_added_ui(self, name: str):
        self.refresh_trusted_ui()

    def _on_remote_mapper_added_ui(self, instance) -> None:
        if self._is_shutting_down:
            return
        self.controllers_page.add_x360_instance(instance)
        self.hotkey_page.add_x360_instance(instance)

    def _on_server_started(self) -> None:
        if self.stop_event.is_set():
            return
        self.button.setEnabled(True)
        self._set_server_button(True)
        self.auth_timer.start(1000)

    def _on_server_failed(self, message: str) -> None:
        self.button.setEnabled(True)
        self._set_server_button(False)
        self.auth_timer.stop()
        if not self._is_shutting_down:
            QMessageBox.warning(self, "Server Error", message)

    # ---------- Auth timer tick ----------

    def _on_auth_timer_tick(self):
        """Update auth countdowns for all clients every second."""
        to_expire = []
        expired_keys = []
        now = time.monotonic()
        with self._state_lock:
            for conn_key, state in list(self.auth_states.items()):
                if state.get("authenticated") or state.get("expired"):
                    continue
                code = state.get("code")
                deadline = state.get("deadline")
                if code is None or deadline is None:
                    continue
                time_left = max(0, ceil(deadline - now))
                state["time_left"] = time_left
                self.signals.show_auth_code.emit(conn_key, code, time_left)
                if time_left <= 0:
                    state["expired"] = True
                    expired_keys.append(conn_key)
                    conn_tuple = self.clients.get(conn_key)
                    if conn_tuple:
                        to_expire.append(conn_tuple[0])

        for conn in to_expire:
            self._close_connection(conn)
        for conn_key in expired_keys:
            self.signals.show_auth_code.emit(conn_key, "", 0)

    @staticmethod
    def _close_connection(conn: socket.socket) -> None:
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            conn.close()
        except OSError:
            pass

    # ---------- Networking / Client Handling ----------

    def _handle_client(self, conn: socket.socket, addr: tuple):
        conn_key = addr
        buffer = bytearray()
        uuid = "unknown"
        client_name_identity = None

        authenticated = False
        auth_code_generated: Optional[str] = None
        auth_time_left = 120  # seconds

        conn.settimeout(0.5)
        with self._state_lock:
            self.clients[conn_key] = (conn, addr, uuid)
            self.emulation_states.setdefault(conn_key, False)
            self.auth_states[conn_key] = {
                "code": None,
                "time_left": auth_time_left,
                "deadline": None,
                "authenticated": False,
                "expired": False,
            }

        self.signals.client_connected.emit(addr)

        mapper: Optional[Phone_mapper] = None
        auth_failures = 0

        try:
            while not self.stop_event.is_set():
                # If auth expired server-side, break loop
                with self._state_lock:
                    auth_state = self.auth_states.get(conn_key)
                    is_expired = auth_state is None or auth_state.get("expired")
                if is_expired:
                    break

                try:
                    data = conn.recv(4096)
                except socket.timeout:
                    continue
                except ConnectionResetError:
                    break
                except OSError:
                    break

                if not data:
                    break

                buffer.extend(data)
                while b"\n" in buffer:
                    newline = buffer.find(b"\n")
                    if newline > MAX_FRAME_BYTES:
                        return
                    raw_line = bytes(buffer[:newline]).strip()
                    del buffer[:newline + 1]
                    if not raw_line:
                        continue
                    try:
                        msg = validate_client_message(
                            json.loads(raw_line.decode("utf-8"))
                        )
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                    if msg is None:
                        continue

                    client_uuid = msg["uuid"]
                    client_name = msg["name"]
                    if uuid == "unknown":
                        uuid = client_uuid
                        client_name_identity = client_name
                        with self._state_lock:
                            if conn_key in self.clients:
                                self.clients[conn_key] = (conn, addr, uuid)
                        self.signals.client_uuid_updated.emit(addr, uuid)
                    elif client_uuid != uuid or client_name != client_name_identity:
                        # A connection cannot switch identity after pairing starts.
                        continue

                    with self._state_lock:
                        auth_state = self.auth_states.get(conn_key)
                        is_expired = auth_state is None or auth_state.get("expired")
                    if is_expired:
                        return

                    if not authenticated:
                        hashed_id = hash_uuid(uuid)
                        with self._state_lock:
                            trusted_name = self.trusted_data.get(hashed_id)
                        if trusted_name is not None:
                            authenticated = True
                            with self._state_lock:
                                auth_state = self.auth_states.get(conn_key)
                                if auth_state is not None:
                                    auth_state["authenticated"] = True
                            self.signals.show_auth_code.emit(addr, "", 0)
                            mapper = Phone_mapper(
                                uuid, "x360", self.controllers_page,
                                self.hotkey_page, self.settings,
                            )
                            self.signals.remote_mapper_added.emit(mapper.emulator)
                        else:
                            received_code = msg["auth_code"]
                            if received_code is not None:
                                if auth_code_generated and secrets.compare_digest(
                                    received_code, auth_code_generated
                                ):
                                    with self._state_lock:
                                        trusted_snapshot = dict(self.trusted_data)
                                        trusted_snapshot[hashed_id] = client_name
                                        try:
                                            save_trusted(trusted_snapshot)
                                        except OSError as exc:
                                            trusted_saved = False
                                            print(
                                                f"[Server] Could not save trusted phone: {exc}"
                                            )
                                        else:
                                            trusted_saved = True
                                            self.trusted_data = trusted_snapshot
                                            auth_state = self.auth_states.get(conn_key)
                                            if auth_state is not None:
                                                auth_state["authenticated"] = True
                                    if not trusted_saved:
                                        return
                                    authenticated = True
                                    self.signals.trusted_client_added.emit(client_name)
                                    self.signals.show_auth_code.emit(addr, "", 0)
                                    mapper = Phone_mapper(
                                        uuid, "x360", self.controllers_page,
                                        self.hotkey_page, self.settings,
                                    )
                                    self.signals.remote_mapper_added.emit(mapper.emulator)
                                else:
                                    auth_failures += 1
                                    if auth_failures >= 5:
                                        with self._state_lock:
                                            auth_state = self.auth_states.get(conn_key)
                                            if auth_state is not None:
                                                auth_state["expired"] = True
                                        return
                            elif auth_code_generated is None:
                                auth_code_generated = str(secrets.randbelow(9000) + 1000)
                                deadline = time.monotonic() + auth_time_left
                                with self._state_lock:
                                    auth_state = self.auth_states.get(conn_key)
                                    if auth_state is not None:
                                        auth_state["code"] = auth_code_generated
                                        auth_state["deadline"] = deadline
                                        auth_state["time_left"] = auth_time_left
                                self.signals.show_auth_code.emit(
                                    addr, auth_code_generated, auth_time_left
                                )
                            if not authenticated:
                                continue

                    with self._state_lock:
                        emulation_enabled = self.emulation_states.get(conn_key, False)
                    if authenticated and mapper and emulation_enabled:
                        mapper.handle_hid_data({
                            "buttons": msg["buttons"],
                            "analog": msg["analog"],
                            "joystick": msg["joystick"],
                        })

                if len(buffer) > MAX_FRAME_BYTES:
                    return
        finally:
            if mapper is not None:
                try:
                    mapper.shutdown()
                except Exception as exc:
                    print(f"[Server] Failed to shutdown phone mapper: {exc}")
            try:
                conn.close()
            except OSError:
                pass

            with self._state_lock:
                self.clients.pop(conn_key, None)
                self.emulation_states.pop(conn_key, None)
                self.auth_states.pop(conn_key, None)
                self.client_threads.pop(conn_key, None)

            self.signals.client_disconnected.emit(addr)

    def _server_loop(self):
        listener = None
        try:
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((HOST, PORT))
            listener.listen()
            listener.settimeout(0.5)
            with self._state_lock:
                if self.stop_event.is_set():
                    return
                self.server_socket = listener
            self.signals.server_started.emit()

            while not self.stop_event.is_set():
                try:
                    conn, addr = listener.accept()
                    with self._state_lock:
                        if len(self.client_threads) >= MAX_CLIENTS:
                            client_thread = None
                        else:
                            client_thread = threading.Thread(
                                target=self._handle_client,
                                args=(conn, addr),
                                daemon=True,
                            )
                            self.client_threads[addr] = client_thread
                    if client_thread is None:
                        self._close_connection(conn)
                        continue
                    client_thread.start()
                except socket.timeout:
                    continue
                except OSError as exc:
                    if not self.stop_event.is_set():
                        self._fail_server(str(exc))
                    break
        except OSError as exc:
            if not self.stop_event.is_set():
                self._fail_server(str(exc))
        finally:
            if listener is not None:
                with self._state_lock:
                    if self.server_socket is listener:
                        self.server_socket = None
                try:
                    listener.close()
                except OSError:
                    pass

    def _fail_server(self, message: str) -> None:
        self.stop_event.set()
        with self._state_lock:
            connections = [entry[0] for entry in self.clients.values()]
        for conn in connections:
            self._close_connection(conn)
        self.signals.server_failed.emit(message)

    def toggle_server(self):
        if not self.server_running:
            self._is_shutting_down = False
            self.stop_event.clear()
            self.button.setEnabled(False)
            self.button.setText("Starting...")
            self.server_thread = threading.Thread(
                target=self._server_loop, daemon=True
            )
            self.server_thread.start()
        else:
            self.shutdown()

    def _set_server_button(self, running: bool) -> None:
        self.server_running = bool(running)
        self.button.setText("Stop Server" if running else "Start Server")
        self.button.setProperty("running", bool(running))
        self.button.style().unpolish(self.button)
        self.button.style().polish(self.button)
        if self.tray_status_callback:
            try:
                self.tray_status_callback()
            except Exception:
                pass

    def shutdown(self) -> None:
        """Stop the listener and wait briefly for every client worker."""
        self._is_shutting_down = True
        self.stop_event.set()

        server_socket = self.server_socket
        if server_socket is not None:
            try:
                server_socket.close()
            except OSError:
                pass

        with self._state_lock:
            connections = list(self.clients.values())
            server_thread = self.server_thread
            client_threads = list(self.client_threads.values())

        for conn, _, _ in connections:
            self._close_connection(conn)

        current = threading.current_thread()
        join_deadline = time.monotonic() + 2.0
        if server_thread and server_thread is not current:
            server_thread.join(timeout=max(0.0, join_deadline - time.monotonic()))
        for client_thread in client_threads:
            if client_thread is not current:
                client_thread.join(timeout=max(0.0, join_deadline - time.monotonic()))

        with self._state_lock:
            self.clients.clear()
            self.emulation_states.clear()
            self.auth_states.clear()
            self.client_threads.clear()

        self.server_thread = None
        self.server_socket = None
        self.clients_list.clear()
        self.button.setEnabled(True)
        self._set_server_button(False)
        self.auth_timer.stop()

    # ---------- Client List UI Helpers ----------

    def _find_item_by_conn_key(self, conn_key) -> Optional[QListWidgetItem]:
        for i in range(self.clients_list.count()):
            it = self.clients_list.item(i)
            widget = self.clients_list.itemWidget(it)
            if isinstance(widget, ClientListItemWidget) and widget.conn_key == conn_key:
                return it
        return None

    def _on_client_connected_ui(self, addr: tuple):
        conn_key = addr
        item = QListWidgetItem(self.clients_list)
        widget = ClientListItemWidget(conn_key, f"{addr[0]}:{addr[1]}")
        sh = widget.sizeHint()
        if sh.height() < 40:
            sh.setHeight(40)
        item.setSizeHint(sh)
        self.clients_list.setItemWidget(item, widget)

        widget.emulate_requested.connect(self._on_emulate_requested)
        widget.delete_requested.connect(self._on_delete_requested)

    def _on_client_disconnected_ui(self, addr: tuple):
        item = self._find_item_by_conn_key(addr)
        if item:
            row = self.clients_list.row(item)
            if row != -1:
                self.clients_list.takeItem(row)

    def _on_client_uuid_updated_ui(self, addr: tuple, uuid: str):
        item = self._find_item_by_conn_key(addr)
        if item:
            widget = self.clients_list.itemWidget(item)
            if isinstance(widget, ClientListItemWidget):
                widget.update_uuid(uuid)
                sh = widget.sizeHint()
                if sh.height() < 40:
                    sh.setHeight(40)
                item.setSizeHint(sh)

    def _on_emulate_requested(self, conn_key):
        item = self._find_item_by_conn_key(conn_key)
        if not item:
            return
        widget = self.clients_list.itemWidget(item)

        with self._state_lock:
            is_connected = conn_key in self.clients
        if not is_connected:
            QMessageBox.warning(
                self, "Client Disconnected", "Client is no longer connected."
            )
            if isinstance(widget, ClientListItemWidget):
                widget.set_running(False)
            return

        if isinstance(widget, ClientListItemWidget):
            with self._state_lock:
                if conn_key in self.clients:
                    self.emulation_states[conn_key] = widget.is_running()

    def _on_delete_requested(self, conn_key):
        with self._state_lock:
            conn_tuple = self.clients.get(conn_key)
        if conn_tuple:
            self._close_connection(conn_tuple[0])

    # ---------- Window Closing ----------

    def closeEvent(self, event):
        self.shutdown()
        event.accept()
