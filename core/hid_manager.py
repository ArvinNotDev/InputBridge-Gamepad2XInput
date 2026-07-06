import logging
import time

from PySide6.QtCore import QObject, Signal
import hid


LOGGER = logging.getLogger(__name__)
READ_SIZE = 65
READ_TIMEOUT_MS = 1
MIN_POLL_INTERVAL = 0.001


class HIDWorker(QObject):
    data_received = Signal(bytes)
    error = Signal(str)
    finished = Signal()

    def __init__(self, controller, poll_interval=0.008):
        super().__init__()
        self.controller = controller
        self.poll_interval = max(float(poll_interval), MIN_POLL_INTERVAL)
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        ds = hid.device()
        try:
            ds.open_path(self.controller.device_path)
        except Exception as e:
            self.error.emit(f"Failed to open {self.controller}: {e}")
            self.finished.emit()
            return

        try:
            ds.get_feature_report(0x05, READ_SIZE)
        except Exception as exc:
            LOGGER.debug("Controller %s did not accept feature report 0x05: %s", self.controller, exc)

        try:
            while self._running:
                try:
                    try:
                        report = ds.read(READ_SIZE, timeout_ms=READ_TIMEOUT_MS)
                    except TypeError:
                        report = ds.read(READ_SIZE, timeout=READ_TIMEOUT_MS)

                    if report:
                        self.data_received.emit(bytes(report))

                    time.sleep(self.poll_interval)

                except Exception as e:
                    self.error.emit(str(e))
                    break

        finally:
            try:
                ds.close()
            except Exception as exc:
                LOGGER.debug("Failed to close HID device %s: %s", self.controller, exc)
            self.finished.emit()
