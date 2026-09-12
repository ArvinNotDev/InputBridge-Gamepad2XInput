import threading
from unittest import mock

from core.dualsense_rumble import (
    DualSenseRumble,
    build_bt_report,
    build_usb_report,
    dualsense_bt_crc,
    xinput_to_dualsense_intensity,
)


def test_xinput_intensity_scaling_preserves_full_range():
    assert xinput_to_dualsense_intensity(0) == 0
    assert xinput_to_dualsense_intensity(65535) == 255
    assert xinput_to_dualsense_intensity(32768) == 128
    assert xinput_to_dualsense_intensity(-1) == 0
    assert xinput_to_dualsense_intensity(99999) == 255


def test_classic_rumble_reports_keep_left_and_right_independent():
    usb = build_usb_report(left_motor=19, right_motor=201)
    assert usb[0] == 0x02
    assert usb[1] == 0x03
    assert usb[3] == 201
    assert usb[4] == 19

    bluetooth = build_bt_report(sequence=6, left_motor=19, right_motor=201)
    assert bluetooth[0] == 0x31
    assert bluetooth[1] == 0x60
    assert bluetooth[3] == 0x03
    assert bluetooth[5] == 201
    assert bluetooth[6] == 19
    assert int.from_bytes(bluetooth[-4:], "little") == dualsense_bt_crc(bluetooth[:-4])


def test_rumble_writer_uses_background_hid_write_and_stops_both_motors():
    writes = []
    write_started = threading.Event()

    class FakeDevice:
        def open_path(self, path):
            self.path = path

        def write(self, report):
            writes.append(bytes(report))
            write_started.set()
            return len(report)

        def close(self):
            pass

    with mock.patch("core.dualsense_rumble.hid.device", return_value=FakeDevice()):
        rumble = DualSenseRumble(b"test-path", transport="Bluetooth")
        rumble.set_xinput_vibration(0x4000, 0xC000)

        assert write_started.wait(timeout=1.0)
        rumble.stop()

    assert len(writes) >= 2
    first = writes[0]
    assert first[5] == xinput_to_dualsense_intensity(0xC000)
    assert first[6] == xinput_to_dualsense_intensity(0x4000)

    final = writes[-1]
    assert final[5] == 0
    assert final[6] == 0


def test_xinput_vibration_callback_keeps_motor_channels_separate():
    from core.emulator import EmulateX360

    received = []
    instance = object.__new__(EmulateX360)
    instance.rumble = object()
    instance.set_xinput_vibration = lambda left, right: received.append((left, right))

    instance._on_xinput_vibration(None, None, 20, 180, None, None)
    assert received == [(20 * 257, 180 * 257)]
