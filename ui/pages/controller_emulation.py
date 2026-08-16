from typing import Optional, Tuple

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QListWidget, QPushButton,
    QDialog, QListWidgetItem, QSizePolicy, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread, QObject, QUrl
from PySide6.QtGui import QDesktopServices

from ui.pages.modal.add_controller import AddControllerDialog
from core.mapper import Mapper
from core.settings import SettingsManager
from core.hid import HIDManager
from core import hid

from core.hidhide import HIDHIDE_RELEASES_URL, HidHideError, HidHideManager


class HidHideWorker(QObject):
    finished = Signal(object)

    def __init__(self, manager: HidHideManager, action: str, devices: list[dict]):
        super().__init__()
        self.manager = manager
        self.action = action
        self.devices = devices

    def run(self):
        try:
            if self.action == "detect":
                result = ("detect", self.manager.detect())
            elif self.action == "enable":
                added = self.manager.hide_hid_devices(self.devices)
                result = ("enable", {"added": added})
            else:
                result = ("error", "Unknown HidHide operation.")
        except HidHideError as exc:
            result = ("error", str(exc))
        except Exception as exc:
            result = ("error", f"Unexpected HidHide error: {exc}")
        self.finished.emit(result)


class HidHideCard(QFrame):
    """Self-contained HidHide control card with asynchronous detection."""

    def __init__(self, parent: "ControllerEmulation"):
        super().__init__(parent)
        self.page = parent
        self.manager = HidHideManager()
        self._thread: QThread | None = None
        self._worker: HidHideWorker | None = None
        self._loader_timer = QTimer(self)
        self._loader_timer.setInterval(180)
        self._loader_timer.timeout.connect(self._animate_loader)
        self._loader_index = 0
        self._busy = False

        self.setObjectName("hidhideCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumHeight(118)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(10)

        title = QLabel("HidHide")
        title.setObjectName("hidhideTitle")
        header.addWidget(title)

        self.status = QLabel("Click HidHide to detect the driver.")
        self.status.setObjectName("hidhideStatus")
        self.status.setWordWrap(True)
        header.addWidget(self.status, 1)
        root.addLayout(header)

        self.detail = QLabel(
            "Hide supported physical controllers from other applications while InputBridge remains allowed to read them."
        )
        self.detail.setObjectName("hidhideDetail")
        self.detail.setWordWrap(True)
        root.addWidget(self.detail)

        actions = QHBoxLayout()
        actions.setSpacing(8)

        self.detect_button = QPushButton("HidHide")
        self.detect_button.setObjectName("hidhidePrimary")
        self.detect_button.setMinimumHeight(36)
        self.detect_button.clicked.connect(self.start_detection)
        actions.addWidget(self.detect_button)

        self.open_link_button = QPushButton("Open Link")
        self.open_link_button.setObjectName("hidhideSecondary")
        self.open_link_button.setMinimumHeight(36)
        self.open_link_button.setVisible(False)
        self.open_link_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(HIDHIDE_RELEASES_URL))
        )
        actions.addWidget(self.open_link_button)
        actions.addStretch(1)
        root.addLayout(actions)

        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet(
            """
            QFrame#hidhideCard {
                background: rgba(255, 255, 255, 12%);
                border: 1px solid rgba(255, 255, 255, 20%);
                border-radius: 12px;
            }
            QLabel#hidhideTitle {
                font-size: 15px;
                font-weight: 700;
            }
            QLabel#hidhideStatus {
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#hidhideDetail {
                font-size: 11px;
            }
            QPushButton#hidhidePrimary {
                background: #5390ff;
                color: white;
                border: 0;
                border-radius: 8px;
                padding: 7px 18px;
                font-weight: 700;
            }
            QPushButton#hidhidePrimary:hover {
                background: #6aa0ff;
            }
            QPushButton#hidhidePrimary:pressed {
                background: #3d7ce6;
            }
            QPushButton#hidhidePrimary:disabled {
                background: #666a73;
                color: #d5d7dc;
            }
            QPushButton#hidhideSecondary {
                background: transparent;
                color: #85c1ff;
                border: 1px solid rgba(133, 193, 255, 55%);
                border-radius: 8px;
                padding: 7px 16px;
                font-weight: 600;
            }
            QPushButton#hidhideSecondary:hover {
                background: rgba(133, 193, 255, 10%);
            }
            """
        )

    def _set_status(self, text: str):
        self.status.setText(text)

    def _animate_loader(self):
        spinner = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        glyph = spinner[self._loader_index % len(spinner)]
        self.detect_button.setText(f"Detecting HidHide {glyph}")
        self._loader_index += 1

    def _start_worker(self, action: str, devices: list[dict]):
        if self._busy:
            return
        self._busy = True
        self.open_link_button.setVisible(False)
        self.detect_button.setEnabled(False)
        self._loader_index = 0
        self._loader_timer.start()

        self._thread = QThread(self)
        self._worker = HidHideWorker(self.manager, action, devices)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        thread = self._thread
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(lambda t=thread: self._clear_thread_refs(t))
        self._thread.start()

    def _clear_thread_refs(self, thread):
        if self._thread is thread:
            self._worker = None
            self._thread = None

    def _finish_busy(self):
        self._busy = False
        self._loader_timer.stop()
        self.detect_button.setEnabled(True)

    def _run_enable(self, devices: list[dict]):
        if self._busy:
            return
        self._busy = True
        self.detect_button.setEnabled(False)
        self._loader_index = 0
        self._loader_timer.start()
        self._thread = QThread(self)
        self._worker = HidHideWorker(self.manager, "enable", devices)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        thread = self._thread
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(lambda t=thread: self._clear_thread_refs(t))
        self._thread.start()

    def _on_worker_finished(self, result):
        self._finish_busy()
        action, payload = result

        if action == "detect":
            detection = payload
            if not detection.installed:
                self._set_status("HidHide not found on this PC.")
                self.detail.setText(
                    "Install HidHide from the official Nefarius releases. After installation, click HidHide again to detect it."
                )
                self.open_link_button.setVisible(True)
                self.detect_button.setText("HidHide")
                return

            self.open_link_button.setVisible(False)
            if detection.message and detection.message != "HidHide detected.":
                self._set_status("HidHide detected, but the configuration interface is unavailable.")
                self.detail.setText(detection.message)
                self.detect_button.setText("HidHide")
                return
            version = f" • {detection.version}" if detection.version else ""
            self._set_status(f"HidHide detected{version}.")
            self.detail.setText(
                "Preparing the controller firewall. InputBridge will be added to HidHide's application whitelist before cloaking."
            )

            devices = self.page._get_hidhide_devices()
            if not devices:
                self._set_status("HidHide detected, but no supported controller is connected.")
                self.detail.setText(
                    "Connect a DualShock 4, DualSense, or UnoJoy controller and click HidHide again."
                )
                self.detect_button.setText("HidHide")
                return

            self._run_enable(devices)
            return

        if action == "enable":
            added = payload.get("added", []) if isinstance(payload, dict) else []
            hidden_count = len(added)
            if hidden_count:
                self._set_status(
                    f"HidHide active • {hidden_count} controller interface(s) hidden."
                )
                self.detail.setText(
                    "The physical controller is hidden from non-whitelisted applications. InputBridge remains whitelisted."
                )
            else:
                self._set_status("HidHide is already active for the detected controller.")
                self.detail.setText(
                    "The current HidHide blacklist already contains the controller; no duplicate rule was added."
                )
            self.detect_button.setText("HidHide • Active")
            return

        self._set_status("HidHide configuration failed.")
        self.detail.setText(str(payload))
        self.detect_button.setText("HidHide")

    def start_detection(self):
        if self._busy:
            return
        self._set_status("Detecting HidHide…")
        self.detail.setText(
            "Checking the official HidHide installation and configuration interface."
        )
        self._start_worker("detect", [])


class EmuListItemWidget(QWidget):
    emulate_requested = Signal(str, str, object)
    delete_requested = Signal(object)

    def __init__(self, hid: str, emu: str, parent=None):
        super().__init__(parent)
        self.hid = hid
        self.emu = emu
        self._running = False
        self._battery = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        self.lbl_text = QLabel(f"{hid} → {emu}")
        self.lbl_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.lbl_text)

        self.lbl_battery = QLabel("Battery: --")
        self.lbl_battery.setMinimumWidth(115)
        self.lbl_battery.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_battery)

        self.btn_emulate = QPushButton("Emulate")
        self.btn_emulate.setToolTip("Start/stop emulation for this mapping")
        self.btn_emulate.clicked.connect(self._on_emulate_clicked)
        layout.addWidget(self.btn_emulate)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setToolTip("Remove this mapping")
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        layout.addWidget(self.btn_delete)

        self.status = QLabel()
        self.status.setFixedSize(12, 12)
        self.status.setToolTip("Running status")
        self._update_status_style(False)
        layout.addWidget(self.status, alignment=Qt.AlignRight)

    def _update_status_style(self, running: bool):
        if running:
            color = "#2ecc71"
        else:
            color = "#9aa0a6"
        self.status.setStyleSheet(
            f"border-radius: 6px; background-color: {color};"
        )

    def set_running(self, running: bool):
        self._running = bool(running)
        self._update_status_style(self._running)
        self.btn_emulate.setText("Stop" if self._running else "Emulate")

    def set_battery(self, percent: int | None, charging: bool = False):
        if percent is None:
            self._battery = None
            self.lbl_battery.setText("Battery: --")
            return
        self._battery = (int(percent), bool(charging))
        suffix = " ⚡" if charging else ""
        self.lbl_battery.setText(f"Battery: {int(percent)}%{suffix}")

    def set_connection_state(self, connected: bool):
        if connected:
            self._update_status_style(self._running)
            return
        self.status.setStyleSheet(
            "border-radius: 6px; background-color: #f59e0b;"
        )
        self.lbl_battery.setText("Waiting for reconnect…")

    def is_running(self) -> bool:
        return self._running

    def _on_emulate_clicked(self):
        self.set_running(not self._running)
        self.emulate_requested.emit(self.hid, self.emu, self)

    def _on_delete_clicked(self):
        self.delete_requested.emit(self)


class ControllerEmulation(QWidget):
    def __init__(self, settings, controllers_page, hotkey_page):
        super().__init__()
        layout_dashboard = QVBoxLayout(self)
        self.controllers_page = controllers_page
        hid.hid_manager = HIDManager(settings.get_polling_rate() / 1000)
        self.hotkey_page = hotkey_page
        self.mappers: dict = {}
        self._mapping_records: dict[int, dict] = {}
        self._path_records: dict[object, int] = {}
        self.settings = settings
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setInterval(1000)
        self._reconnect_timer.timeout.connect(self._try_reconnect)
        self._reconnect_timer_active = False
        self.controllers_page.battery_updated.connect(self._on_battery_updated)
        hid.hid_manager.device_error.connect(self._on_device_error)
        lbl_dashboard = QLabel("Controller Emulation Page\nPress {Share/Select/⚙️ + R3} to switch between mouse mode and controller mode")
        lbl_dashboard.setAlignment(Qt.AlignCenter)

        emu_label = QLabel("List of Emulated Devices")
        emu_label.setAlignment(Qt.AlignCenter)

        self.emu_list = QListWidget()
        self.emu_list.setStyleSheet("""
            QListWidget::item {
                padding: 0px;
                color: #000000;
                background-color: transparent;
        }
                                    """)

        self.hidhide_card = HidHideCard(self)

        add_btn = QPushButton("Add Controller")
        add_btn.clicked.connect(self.open_add_controller_dialog)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #5390ff;
                color: #000000;
                border: 2px solid #000000;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;  /* same as normal to remove hover effect */
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """)


        layout_dashboard.addWidget(lbl_dashboard)
        layout_dashboard.addWidget(emu_label)
        layout_dashboard.addWidget(self.emu_list)
        layout_dashboard.addWidget(self.hidhide_card)
        layout_dashboard.addWidget(add_btn)

    def _get_hidhide_devices(self) -> list[dict]:
        """Return supported connected HID devices for HidHide integration."""
        devices = hid.hid_manager.scan_devices() or []
        supported = []
        seen_paths = set()

        for device in devices:
            vid = self._device_id(device.get("vendor_id"))
            pid = self._device_id(device.get("product_id"))
            is_supported = (
                (vid == 0x054C and pid in (0x05C4, 0x09CC, 0x0CE6))
                or (vid == 0x10C4 and pid == 0x82C0)
            )
            if not is_supported:
                continue
            path = str(device.get("path") or "")
            if path and path not in seen_paths:
                seen_paths.add(path)
                supported.append(device)

        return supported

    def open_add_controller_dialog(self):
        dialog = AddControllerDialog(self)

        hid_list_display = []
        hid_path_list = []

        devices = hid.hid_manager.scan_devices() or []

        name_counts = {}
        for dev in devices:
            vid = dev.get("vendor_id")
            pid = dev.get("product_id")

            try:
                vid_int = int(vid) if isinstance(vid, (int,)) else int(str(vid), 0)
            except Exception:
                try:
                    vid_int = int(vid)
                except Exception:
                    vid_int = None
            try:
                pid_int = int(pid) if isinstance(pid, (int,)) else int(str(pid), 0)
            except Exception:
                try:
                    pid_int = int(pid)
                except Exception:
                    pid_int = None

            if vid_int == 0x054C and pid_int in (0x05C4, 0x09CC):
                name = "Dualshock4 (PS4 Controller)"
            elif vid_int == 0x054C and pid_int == 0x0CE6:
                name = "Dualsense (PS5 Controller)"
            elif vid_int == 0x10C4 and pid_int == 0x82C0:
                name = "UnoJoy Controller (Arduino)"
            else:
                name = "Not Supported"
            
            # --- Skip unsupported devices entirely ---
            if name == "Not Supported":
                continue
            
            count = name_counts.get(name, 0)
            name_counts[name] = count + 1
            display = name if count == 0 else f"{name} ({count})"
            
            hid_list_display.append(display)
            hid_path_list.append(dev)

        hid_list_display.reverse()
        hid_path_list.reverse()
        dialog.hid_list.addItems(hid_list_display)
        dialog.emu_list.addItems(["Emulate Xbox"])

        if dialog.exec_() != QDialog.Accepted:
            return

        hid_choice, emu_choice = dialog.get_selections()
        if not (hid_choice and emu_choice):
            return

        selected_index = dialog.hid_list.currentRow()
        if selected_index is None or selected_index < 0:
            try:
                selected_index = hid_list_display.index(hid_choice)
            except ValueError:
                selected_index = -1

        device = None
        if 0 <= selected_index < len(hid_path_list):
            device = hid_path_list[selected_index]

        added = self.add_emulated_mapping(hid_choice, emu_choice, device)
        if not added:
            return

        if not device:
            print("[Controller Emulation] Warning: selected HID could not be mapped to a device entry.")

    def add_emulated_mapping(self, hid_choice: str, emu: str, device: Optional[dict] = None) -> bool:
        new_path = device.get("path") if device else None

        for i in range(self.emu_list.count()):
            existing_item = self.emu_list.item(i)
            existing_data: Tuple[Optional[dict], Optional[str], Optional[str]] = existing_item.data(Qt.UserRole) or (None, None, None)
            existing_device = existing_data[0]
            existing_display = existing_data[1]

            if new_path and existing_device and existing_device.get("path") == new_path:
                self.emu_list.setCurrentItem(existing_item)
                existing_widget = self.emu_list.itemWidget(existing_item)
                if existing_widget:
                    existing_widget.setFocus()
                QMessageBox.information(self, "Already added",
                                        f"Device '{hid_choice}' is already in the emulated devices list.")
                return False

            if not new_path and existing_display == hid_choice:
                self.emu_list.setCurrentItem(existing_item)
                QMessageBox.information(self, "Already added",
                                        f"HID '{hid_choice}' is already in the emulated devices list.")
                return False

        item = QListWidgetItem()
        widget = EmuListItemWidget(hid_choice, emu)

        item.setSizeHint(widget.sizeHint())
        item.setData(Qt.UserRole, (device, hid_choice, emu))

        self.emu_list.addItem(item)
        self.emu_list.setItemWidget(item, widget)

        widget.emulate_requested.connect(self._on_emulate_requested)
        widget.delete_requested.connect(lambda w=widget, i=item: self._on_delete_requested(w, i))

        return True

    def _find_item_by_widget(self, widget: EmuListItemWidget) -> Optional[QListWidgetItem]:
        for i in range(self.emu_list.count()):
            it = self.emu_list.item(i)
            if self.emu_list.itemWidget(it) is widget:
                return it
        return None

    def _find_device_by_display_name(self, display_name: str) -> Optional[dict]:
        devices = getattr(hid.hid_manager, "devices", None) or hid.hid_manager.scan_devices() or []
        base_name = display_name.split(" (")[0]
        for dev in devices:
            name = dev.get("product_string") or f"VID_{dev.get('vendor_id')}_PID_{dev.get('product_id')}"
            if base_name == name:
                return dev
        return None

    @staticmethod
    def _device_id(value) -> Optional[int]:
        try:
            return int(value) if isinstance(value, int) else int(str(value), 0)
        except (TypeError, ValueError):
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

    def _controller_type(self, device: dict) -> str:
        vid = self._device_id(device.get("vendor_id"))
        pid = self._device_id(device.get("product_id"))
        if vid == 0x054C and pid in (0x05C4, 0x09CC):
            return "Dualshock4"
        if vid == 0x054C and pid == 0x0CE6:
            return "Dualsense"
        if vid == 0x10C4 and pid == 0x82C0:
            return "Unojoy"
        return "Generic"

    def _auto_reconnect_enabled(self) -> bool:
        try:
            return bool(self.settings.get_auto_reconnect())
        except Exception:
            return True

    def _start_mapping(
        self,
        item: QListWidgetItem,
        widget: EmuListItemWidget,
        device: dict,
        record: Optional[dict] = None,
    ) -> bool:
        path = device.get("path")
        if not path or path in self.mappers:
            return False

        try:
            controller = hid.hid_manager.start_polling(
                device.get("vendor_id"), device.get("product_id"), path
            )
            mapper = Mapper(
                controller,
                self._controller_type(device),
                "x360",
                self.settings,
                self.controllers_page,
                self.hotkey_page,
            )
        except Exception as exc:
            print(f"[Controller Emulation] Failed to start mapping: {exc}")
            try:
                hid.hid_manager.stop_polling(path)
            except Exception:
                pass
            return False

        key = id(item)
        record = record or {
            "item": item,
            "widget": widget,
            "hid_choice": item.data(Qt.UserRole)[1],
            "emu": item.data(Qt.UserRole)[2],
            "last_device": device,
            "path": path,
            "waiting": False,
        }
        record["last_device"] = device
        record["path"] = path
        record["waiting"] = False
        self._mapping_records[key] = record
        self._path_records[path] = key
        self.mappers[path] = mapper
        item.setData(
            Qt.UserRole,
            (device, record["hid_choice"], record["emu"]),
        )

        wtuple = getattr(hid.hid_manager, "_workers", {}).get(path)
        if wtuple:
            _, worker, _ = wtuple
            try:
                worker.data_received.connect(mapper.handle_hid_data)
            except RuntimeError:
                print(f"[Warning] Worker for {path} was deleted before connecting signals")

        mapper.start()
        widget.set_connection_state(True)
        widget.set_battery(None)
        return True

    def _stop_mapping(self, path: str) -> None:
        mapper = self.mappers.pop(path, None)
        self._path_records.pop(path, None)
        if mapper is not None:
            try:
                mapper.stop()
            except Exception:
                pass
        try:
            hid.hid_manager.stop_polling(path)
        except Exception:
            pass

    def _on_emulate_requested(self, hid_choice: str, emu: str, widget: EmuListItemWidget):
        item = self._find_item_by_widget(widget)
        if item is None:
            print("[Controller Emulation] Could not locate QListWidgetItem for widget")
            widget.set_running(False)
            return
        stored = item.data(Qt.UserRole) or (None, None, None)
        device = stored[0]
        display_name = stored[1] or hid_choice

        if not device:
            device = self._find_device_by_display_name(display_name)
            if not device:
                print("[Controller Emulation] Could not match HID to device")
                widget.set_running(False)
                return

        path = device.get("path")
        running = widget.is_running()
        key = id(item)

        if running:
            if key in self._mapping_records and self._mapping_records[key].get("waiting"):
                self._ensure_reconnect_timer()
                return
            if path in self.mappers:
                return
            if self._start_mapping(item, widget, device):
                self._ensure_reconnect_timer()

        else:
            record = self._mapping_records.pop(key, None)
            actual_path = record.get("path") if record else path
            if actual_path:
                self._stop_mapping(actual_path)
            widget.set_battery(None)
            widget.set_connection_state(True)
            self._maybe_stop_reconnect_timer()

    def _on_battery_updated(self, path, percent: int, charging: bool) -> None:
        key = self._path_records.get(path)
        if key is None:
            return
        record = self._mapping_records.get(key)
        if record:
            record["widget"].set_battery(percent, charging)

    def _on_device_error(self, path: str, message: str) -> None:
        key = self._path_records.get(path)
        if key is None:
            return

        record = self._mapping_records.get(key)
        if not record:
            return

        print(f"[Controller Emulation] Device lost at {path}: {message}")
        self._stop_mapping(path)
        record["waiting"] = True
        record["path"] = None
        record["widget"].set_connection_state(False)
        record["widget"].set_battery(None)
        if self._auto_reconnect_enabled():
            self._ensure_reconnect_timer()

    def _ensure_reconnect_timer(self) -> None:
        if not self._reconnect_timer_active:
            self._reconnect_timer.start()
            self._reconnect_timer_active = True

    def _maybe_stop_reconnect_timer(self) -> None:
        if any(record.get("waiting") for record in self._mapping_records.values()):
            return
        if self._reconnect_timer_active:
            self._reconnect_timer.stop()
            self._reconnect_timer_active = False

    def _is_matching_device(self, expected: dict, candidate: dict) -> bool:
        if self._device_id(expected.get("vendor_id")) != self._device_id(candidate.get("vendor_id")):
            return False
        if self._device_id(expected.get("product_id")) != self._device_id(candidate.get("product_id")):
            return False

        serial = expected.get("serial_number")
        candidate_serial = candidate.get("serial_number")
        return not serial or not candidate_serial or serial == candidate_serial

    def _try_reconnect(self) -> None:
        waiting = [
            record for record in self._mapping_records.values()
            if record.get("waiting") and record["widget"].is_running()
        ]
        if not waiting:
            self._maybe_stop_reconnect_timer()
            return

        try:
            devices = hid.hid_manager.scan_devices() or []
        except Exception as exc:
            print(f"[Controller Emulation] Reconnect scan failed: {exc}")
            return

        occupied_paths = set(self.mappers)
        for record in waiting:
            expected = record.get("last_device") or {}
            candidate = next(
                (
                    dev for dev in devices
                    if dev.get("path") not in occupied_paths
                    and self._is_matching_device(expected, dev)
                ),
                None,
            )
            if candidate is None:
                continue

            if self._start_mapping(
                record["item"], record["widget"], candidate, record=record
            ):
                occupied_paths.add(candidate.get("path"))

        self._maybe_stop_reconnect_timer()

    def _on_delete_requested(self, widget: EmuListItemWidget, item: QListWidgetItem):
        key = id(item)
        record = self._mapping_records.pop(key, None)
        stored = item.data(Qt.UserRole) or (None, None, None)
        device = stored[0] or (record or {}).get("last_device")
        path = (record or {}).get("path") or (device or {}).get("path")
        if path:
            self._stop_mapping(path)

        for i in range(self.emu_list.count()):
            if self.emu_list.item(i) is item:
                self.emu_list.takeItem(i)
                break
        self._maybe_stop_reconnect_timer()

    def shutdown(self) -> None:
        for path in list(self.mappers):
            self._stop_mapping(path)
        self._mapping_records.clear()
        self._path_records.clear()
        self._reconnect_timer.stop()
        self._reconnect_timer_active = False
        try:
            hid.hid_manager.stop_all()
        except Exception:
            pass

    def closeEvent(self, event):
        self.shutdown()
        super().closeEvent(event)
