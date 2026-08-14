import sys
import socket
import json
import threading
import hashlib
import random
import os
from typing import Optional, Dict, Tuple
from core.settings import SettingsManager

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QHBoxLayout, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QObject, QSize, QTimer

from core.mapper import Phone_mapper


HOST = "0.0.0.0"
PORT = 5000
TRUSTED_FILE = "trusted_clients.json"


# ---------------------------------------------------------

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "Unavailable"
    return f"{ip}:{PORT}"


def hash_uuid(uuid_str: str) -> str:
    return hashlib.sha256(uuid_str.encode("utf-8")).hexdigest()


def load_trusted() -> dict:
    if os.path.exists(TRUSTED_FILE):
        try:
            with open(TRUSTED_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_trusted(trusted_data: dict):
    with open(TRUSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(trusted_data, f, indent=4)


class ServerSignals(QObject):
    log_message = Signal(str)
    client_connected = Signal(tuple)            # addr
    client_disconnected = Signal(tuple)         # addr
    client_uuid_updated = Signal(tuple, str)    # addr, uuid

    # Now we send addr + code + time_left for UI per client
    show_auth_code = Signal(tuple, str, int)    # addr, code, time_left

    trusted_client_added = Signal(str)          # name
    remote_mapper_added = Signal(object)         # emulator instance


class TrustedItemWidget(QWidget):
    remove_requested = Signal(str)

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.name = name

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)

        self.lbl_name = QLabel(name)
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
        self.remove_requested.emit(self.name)


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

        # Populate trusted list
        self.refresh_trusted_ui()

        # NEW: global timer to update auth countdowns every second
        self.auth_timer = QTimer(self)
        self.auth_timer.timeout.connect(self._on_auth_timer_tick)
        self.auth_timer.start(1000)  # 1 second

    # ---------- Trusted List UI ----------

    def refresh_trusted_ui(self):
        self.trusted_list.clear()
        for name in self.trusted_data.keys():
            self._add_trusted_item_to_ui(name)

    def _add_trusted_item_to_ui(self, name: str):
        item = QListWidgetItem(self.trusted_list)
        widget = TrustedItemWidget(name)
        sh = widget.sizeHint()
        if sh.height() < 40:
            sh.setHeight(40)
        item.setSizeHint(sh)
        self.trusted_list.setItemWidget(item, widget)
        widget.remove_requested.connect(self._on_remove_trusted_requested)

    def _on_remove_trusted_requested(self, name: str):
        if name in self.trusted_data:
            del self.trusted_data[name]
            save_trusted(self.trusted_data)
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

    # ---------- Auth timer tick ----------

    def _on_auth_timer_tick(self):
        """Update auth countdowns for all clients every second."""
        to_expire = []

        for conn_key, state in list(self.auth_states.items()):
            # Skip already authenticated or already expired
            if state.get("authenticated") or state.get("expired"):
                continue

            code = state.get("code")
            time_left = state.get("time_left", 0)

            if code is None:
                continue

            if time_left > 0:
                time_left -= 1
                state["time_left"] = time_left

            # Update UI
            self.signals.show_auth_code.emit(conn_key, code, time_left)

            if time_left <= 0:
                # Expired: mark and remember to close connection
                state["expired"] = True
                to_expire.append(conn_key)

        # Close expired connections and clear UI
        for conn_key in to_expire:
            conn_tuple = self.clients.get(conn_key)
            if conn_tuple:
                try:
                    conn_tuple[0].close()
                except OSError:
                    pass
            # Clear auth UI
            self.signals.show_auth_code.emit(conn_key, "", 0)

    # ---------- Networking / Client Handling ----------

    def _handle_client(self, conn: socket.socket, addr: tuple):
        conn_key = addr
        buffer = ""
        uuid = "unknown"

        authenticated = False
        auth_code_generated: Optional[str] = None
        auth_time_left = 120  # seconds

        with self._state_lock:
            self.clients[conn_key] = (conn, addr, uuid)
            self.emulation_states.setdefault(conn_key, False)

        # Initialize auth state
        self.auth_states[conn_key] = {
            "code": None,
            "time_left": auth_time_left,
            "authenticated": False,
            "expired": False,
        }

        self.signals.client_connected.emit(addr)

        mapper: Optional[Phone_mapper] = None

        try:
            while not self.stop_event.is_set():
                # If auth expired server-side, break loop
                if self.auth_states.get(conn_key, {}).get("expired"):
                    break

                try:
                    data = conn.recv(1024)
                except ConnectionResetError:
                    break
                except OSError:
                    break

                if not data:
                    break

                buffer += data.decode("utf-8", errors="replace")

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)

                        client_uuid = msg.get("uuid", "unknown")
                        client_name = msg.get("name", "UnknownDevice")

                        if client_uuid != "unknown" and client_uuid != uuid:
                            uuid = client_uuid
                            self.clients[conn_key] = (conn, addr, uuid)
                            self.signals.client_uuid_updated.emit(addr, uuid)

                        # If auth expired, ignore any further auth attempts and break
                        if self.auth_states.get(conn_key, {}).get("expired"):
                            break

                        if not authenticated:
                            hashed_id = hash_uuid(uuid)
                            if (
                                client_name in self.trusted_data
                                and self.trusted_data[client_name] == hashed_id
                            ):
                                # Already trusted
                                authenticated = True
                                self.auth_states[conn_key]["authenticated"] = True

                                # Clear any auth code in UI
                                self.signals.show_auth_code.emit(addr, "", 0)

                                mapper = Phone_mapper(uuid, "x360", self.controllers_page, self.hotkey_page, self.settings)
                                self.signals.remote_mapper_added.emit(mapper.emulator)
                            else:
                                received_code = msg.get("auth_code")
                                if received_code:
                                    if (
                                        auth_code_generated
                                        and str(received_code) == auth_code_generated
                                    ):
                                        # Auth succeeded
                                        authenticated = True
                                        self.auth_states[conn_key]["authenticated"] = True

                                        self.trusted_data[client_name] = hashed_id
                                        save_trusted(self.trusted_data)
                                        self.signals.trusted_client_added.emit(
                                            client_name
                                        )

                                        # Auth succeeded -> clear auth code & timer in UI
                                        self.signals.show_auth_code.emit(addr, "", 0)

                                        mapper = Phone_mapper(
                                            uuid, "x360", self.controllers_page, self.hotkey_page, self.settings
                                        )
                                        self.signals.remote_mapper_added.emit(mapper.emulator)
                                    else:
                                        print(f"[{addr}] Invalid auth code: {received_code}")
                                else:
                                    # No auth_code received yet: generate once and show
                                    if not auth_code_generated:
                                        auth_code_generated = str(
                                            random.randint(1000, 9999)
                                        )
                                        auth_time_left = 120
                                        st = self.auth_states.get(conn_key, {})
                                        st["code"] = auth_code_generated
                                        st["time_left"] = auth_time_left

                                        # Initial display
                                        self.signals.show_auth_code.emit(
                                            addr,
                                            auth_code_generated,
                                            auth_time_left,
                                        )

                                # Skip HID processing until authenticated
                                continue

                        # If we reach here and expired in the meantime, stop
                        if self.auth_states.get(conn_key, {}).get("expired"):
                            break

                        if authenticated and mapper:
                            buttons = msg.get("buttons", {})
                            analog = msg.get("analog", {})
                            joystick = msg.get("joystick", {})

                            if self.emulation_states.get(conn_key, False):
                                mapper.handle_hid_data(
                                    {
                                        "buttons": buttons,
                                        "analog": analog,
                                        "joystick": joystick,
                                    }
                                )

                    except json.JSONDecodeError:
                        # Ignore malformed messages
                        continue
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
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((HOST, PORT))
        self.server_socket.listen()
        self.server_socket.settimeout(0.5)

        try:
            while not self.stop_event.is_set():
                try:
                    conn, addr = self.server_socket.accept()
                    t = threading.Thread(
                        target=self._handle_client, args=(conn, addr), daemon=True
                    )
                    with self._state_lock:
                        self.client_threads[addr] = t
                    t.start()
                except socket.timeout:
                    continue
                except OSError:
                    # socket closed while stopping
                    break
        finally:
            if self.server_socket:
                try:
                    self.server_socket.close()
                except OSError:
                    pass
                self.server_socket = None

    def toggle_server(self):
        if not self.server_running:
            self._is_shutting_down = False
            self.stop_event.clear()
            self.auth_timer.start(1000)
            self.server_thread = threading.Thread(
                target=self._server_loop, daemon=True
            )
            self.server_thread.start()
            self._set_server_button(True)

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
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                conn.close()
            except OSError:
                pass

        current = threading.current_thread()
        if server_thread and server_thread is not current:
            server_thread.join(timeout=2.0)
        for client_thread in client_threads:
            if client_thread is not current:
                client_thread.join(timeout=2.0)

        with self._state_lock:
            self.clients.clear()
            self.emulation_states.clear()
            self.auth_states.clear()
            self.client_threads.clear()

        self.server_thread = None
        self.server_socket = None
        self.clients_list.clear()
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

        if conn_key not in self.clients:
            QMessageBox.warning(
                self, "Client Disconnected", "Client is no longer connected."
            )
            if isinstance(widget, ClientListItemWidget):
                widget.set_running(False)
            return

        if isinstance(widget, ClientListItemWidget):
            self.emulation_states[conn_key] = widget.is_running()

    def _on_delete_requested(self, conn_key):
        conn_tuple = self.clients.get(conn_key)
        if conn_tuple:
            try:
                conn_tuple[0].close()
            except OSError:
                pass
        self.emulation_states.pop(conn_key, None)
        self.auth_states.pop(conn_key, None)

    # ---------- Window Closing ----------

    def closeEvent(self, event):
        self.shutdown()
        event.accept()
