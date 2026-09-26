import threading
from configparser import ConfigParser

from core.controller import stable_controller_id
from core.dualsense_lightbar import (
    CHARGING_LIGHTBAR_COLOR,
    DualSenseLightbar,
    build_bt_lightbar_report,
    build_usb_lightbar_report,
    dualsense_bt_crc,
    resolve_lightbar_color,
)
from core.dualsense_output import next_dualsense_bt_sequence
from core.mapper import Mapper
from core.settings import SettingsManager


def test_usb_lightbar_report_has_dualsense_fields_and_rgb():
    report = build_usb_lightbar_report((0x12, 0x34, 0x56))

    assert len(report) == 63
    assert report[0] == 0x02
    assert report[2] == 0x04
    assert report[39] == 0x02
    assert report[42] == 0x01
    assert report[45:48] == bytes((0x12, 0x34, 0x56))
    assert report[1] == 0


def test_bluetooth_lightbar_report_has_sequence_rgb_and_crc():
    report = build_bt_lightbar_report(15, (0x12, 0x34, 0x56))

    assert len(report) == 78
    assert report[0] == 0x31
    assert report[1] == 0xF0
    assert report[2] == 0x10
    assert report[4] == 0x04
    assert report[41] == 0x02
    assert report[44] == 0x01
    assert report[47:50] == bytes((0x12, 0x34, 0x56))
    assert int.from_bytes(report[74:78], "little") == dualsense_bt_crc(
        bytes(report[:-4])
    )


def test_lightbar_off_sends_black_and_bluetooth_sequence_is_per_controller():
    report = build_bt_lightbar_report(0, (10, 20, 30), enabled=False)
    assert report[47:50] == b"\x00\x00\x00"

    controller_a = "test-lightbar-controller-a"
    controller_b = "test-lightbar-controller-b"
    assert next_dualsense_bt_sequence(controller_a) == 0
    assert next_dualsense_bt_sequence(controller_a) == 1
    assert next_dualsense_bt_sequence(controller_b) == 0
    assert [next_dualsense_bt_sequence(controller_a) for _ in range(14)] == list(
        range(2, 16)
    )
    assert next_dualsense_bt_sequence(controller_a) == 0


def test_lightbar_writer_deduplicates_same_state():
    writes = []
    first_write = threading.Event()

    class FakeDevice:
        def open_path(self, path):
            self.path = path

        def write(self, report):
            writes.append(bytes(report))
            first_write.set()
            return len(report)

        def close(self):
            pass

    import core.dualsense_lightbar as lightbar_module

    original_device = lightbar_module.hid.device
    lightbar_module.hid.device = lambda: FakeDevice()
    output = DualSenseLightbar(b"test-usb-lightbar", transport="USB")
    try:
        output.set_color((1, 2, 3))
        assert first_write.wait(timeout=1)
        output.set_color((1, 2, 3))
    finally:
        output.stop()
        lightbar_module.hid.device = original_device

    assert len(writes) == 1
    assert writes[0][45:48] == b"\x01\x02\x03"


def test_lightbar_writer_applies_latest_color_after_in_flight_write():
    writes = []
    first_color_sent = threading.Event()
    second_color_started = threading.Event()
    release_second_color = threading.Event()

    class FakeDevice:
        def open_path(self, path):
            self.path = path

        def write(self, report):
            report = bytes(report)
            writes.append(report)
            color = report[45:48]
            if color == b"\x04\x05\x06":
                first_color_sent.set()
            elif color == b"\x07\x08\x09":
                second_color_started.set()
                assert release_second_color.wait(timeout=1)
            return len(report)

        def close(self):
            pass

    import core.dualsense_lightbar as lightbar_module

    original_device = lightbar_module.hid.device
    lightbar_module.hid.device = lambda: FakeDevice()
    output = DualSenseLightbar(b"test-usb-lightbar-coalesce", transport="USB")
    try:
        output.set_color((4, 5, 6))
        assert first_color_sent.wait(timeout=1)
        output.set_color((7, 8, 9))
        assert second_color_started.wait(timeout=1)
        output.set_color((4, 5, 6))
        release_second_color.set()
    finally:
        release_second_color.set()
        output.stop()
        lightbar_module.hid.device = original_device

    assert [report[45:48] for report in writes] == [
        b"\x04\x05\x06",
        b"\x07\x08\x09",
        b"\x04\x05\x06",
    ]


def test_per_controller_lightbar_settings_save_and_load_independently(tmp_path):
    config_path = tmp_path / "settings.conf"
    manager = SettingsManager.__new__(SettingsManager)
    manager.path = config_path
    manager.config = ConfigParser()

    manager.set_controller_lightbar_settings(
        "sony:controller-a",
        {
            "enabled": True,
            "color": "#FF0000",
            "battery_mode": False,
            "charging_indication": True,
        },
    )
    manager.set_controller_lightbar_settings(
        "sony:controller-b",
        {
            "enabled": True,
            "color": "#0088FF",
            "battery_mode": True,
            "charging_indication": False,
        },
    )
    manager.save()

    loaded = SettingsManager(path=config_path)
    assert loaded.get_controller_lightbar_settings("sony:controller-a") == {
        "enabled": True,
        "color": "#FF0000",
        "battery_mode": False,
        "charging_indication": True,
    }
    assert loaded.get_controller_lightbar_settings("sony:controller-b") == {
        "enabled": True,
        "color": "#0088FF",
        "battery_mode": True,
        "charging_indication": False,
    }


def test_battery_colors_are_temporary_and_charging_returns_to_saved_color():
    settings = {
        "enabled": True,
        "color": "#8B5CF6",
        "battery_mode": True,
        "charging_indication": True,
    }

    assert resolve_lightbar_color(settings, (85, False))[0] == (34, 197, 94)
    assert resolve_lightbar_color(settings, (50, False))[0] == (234, 179, 8)
    assert resolve_lightbar_color(settings, (25, False))[0] == (249, 115, 22)
    assert resolve_lightbar_color(settings, (10, False))[0] == (239, 68, 68)
    assert resolve_lightbar_color(settings, (10, True))[0] == CHARGING_LIGHTBAR_COLOR

    settings["battery_mode"] = False
    assert resolve_lightbar_color(settings, (10, False))[0] == tuple(
        bytes.fromhex("8B5CF6")
    )
    assert resolve_lightbar_color(settings, (10, True))[0] == CHARGING_LIGHTBAR_COLOR
    assert settings["color"] == "#8B5CF6"


def test_dualsense_battery_status_and_transport_offsets():
    mapper = object.__new__(Mapper)
    mapper.controller_type = "Dualsense"

    assert mapper._interpret_battery(0x15) == (55, True)
    assert mapper._interpret_battery(0x25) == (100, False)
    mapper.controller = type("Device", (), {"transport": 1})()
    assert mapper._battery_report_index(54) == 53
    mapper.controller.transport = 2
    assert mapper._battery_report_index(54) == 54


def test_stable_controller_id_prefers_serial_over_connection_path():
    first = stable_controller_id(0x054C, 0x0CE6, "bt-path-a", "S0NY-123")
    reconnected = stable_controller_id(0x054C, 0x0CE6, "bt-path-b", "S0NY-123")
    second = stable_controller_id(0x054C, 0x0CE6, "bt-path-c", "S0NY-456")

    assert first == reconnected
    assert first != second
