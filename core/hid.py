from PySide6.QtCore import QObject, QThread, Signal
from .hid_manager import HIDWorker
import hid
from core.controller import Controller

class HIDManager(QObject):
    """Manages multiple HID controllers with polling in QThreads."""
    device_error = Signal(object, str)  # device_path, message

    def __init__(self, poll_interval=0.008):
        super().__init__()
        self.poll_interval = poll_interval
        self.devices = []
        self._workers = {}  # device_path -> (thread, worker, controller)

    def scan_devices(self):
        """Scan all connected HID devices."""
        self.devices = hid.enumerate()
        return self.devices

    def start_polling(self, vendor_id, product_id, path, name=None, on_data=None, on_error=None):
        """Start polling a single controller."""
        if path in self._workers:
            print(f"[HIDManager] Already polling device at path: {path}")
            return self._workers[path][2]  # return the controller

        controller = Controller(vendor_id, product_id, path, name)

        thread = QThread()
        worker = HIDWorker(controller, self.poll_interval)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        worker.error.connect(
            lambda message, device_path=path: self._on_worker_error(
                device_path, message
            )
        )

        if on_data:
            worker.data_received.connect(on_data)
        # Errors are routed through the manager so UI-owned cleanup happens in
        # the Qt/UI thread instead of from the HID polling thread.
        if on_error:
            self.device_error.connect(
                lambda device_path, message, expected_path=path: (
                    on_error(message) if device_path == expected_path else None
                )
            )

        self._workers[path] = (thread, worker, controller)
        thread.start()
        return controller

    def _on_worker_error(self, device_path, message: str) -> None:
        self.device_error.emit(device_path, message)

    def stop_polling(self, device_path):
        if device_path not in self._workers:
            return

        thread, worker, controller = self._workers.pop(device_path)

        worker.stop()

        thread.quit()
        thread.wait()


    def stop_all(self):
        for device_path, (thread, worker, controller) in list(self._workers.items()):
            worker.stop()
            thread.quit()
            thread.wait()
            self._workers.pop(device_path, None)


hid_manager = HIDManager()
