import logging

import hid
from PySide6.QtCore import QObject, QThread

from core.controller import Controller
from .hid_manager import HIDWorker, MIN_POLL_INTERVAL


LOGGER = logging.getLogger(__name__)
THREAD_STOP_TIMEOUT_MS = 2000


class HIDManager(QObject):
    """Manages multiple HID controllers with polling in QThreads."""
    def __init__(self, poll_interval=0.008):
        super().__init__()
        self.poll_interval = max(float(poll_interval), MIN_POLL_INTERVAL)
        self.devices = []
        self._workers = {}  # device_path -> (thread, worker, controller)

    def scan_devices(self):
        """Scan all connected HID devices."""
        try:
            self.devices = hid.enumerate()
        except Exception as exc:
            LOGGER.exception("Failed to enumerate HID devices: %s", exc)
            self.devices = []
        return self.devices

    def start_polling(self, vendor_id, product_id, path, name=None, on_data=None, on_error=None):
        """Start polling a single controller."""
        if not path:
            raise ValueError("Cannot start HID polling without a device path.")

        if path in self._workers:
            LOGGER.debug("Already polling HID device at path: %s", path)
            return self._workers[path][2]  # return the controller

        controller = Controller(vendor_id, product_id, path, name)

        thread = QThread()
        worker = HIDWorker(controller, self.poll_interval)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        if on_data:
            worker.data_received.connect(on_data)
        if on_error:
            worker.error.connect(on_error)

        thread.start()
        self._workers[path] = (thread, worker, controller)
        return controller

    def stop_polling(self, device_path):
        if device_path not in self._workers:
            return

        thread, worker, controller = self._workers.pop(device_path)

        worker.stop()

        thread.quit()
        if not thread.wait(THREAD_STOP_TIMEOUT_MS):
            LOGGER.warning("Timed out stopping HID polling thread for %s", controller)
            thread.terminate()
            thread.wait(500)

    def stop_all(self):
        for device_path, (thread, worker, controller) in list(self._workers.items()):
            worker.stop()
            thread.quit()
            if not thread.wait(THREAD_STOP_TIMEOUT_MS):
                LOGGER.warning("Timed out stopping HID polling thread for %s", controller)
                thread.terminate()
                thread.wait(500)
            self._workers.pop(device_path, None)


hid_manager = HIDManager()
