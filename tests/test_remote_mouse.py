import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from core.mapper import Mouse, Phone_mapper
from ui.pages.server import ClientListItemWidget, validate_client_message


_APP = QApplication.instance() or QApplication([])


def _phone_message(mouse):
    return {
        "uuid": "phone-uuid",
        "name": "Phone",
        "buttons": {},
        "analog": {},
        "joystick": {},
        "mouse": mouse,
    }


def test_server_accepts_bounded_phone_mouse_payload():
    normalized = validate_client_message(_phone_message({
        "dx": 30,
        "dy": -12,
        "scroll": 2,
        "left": True,
        "right": 0,
        "middle": False,
    }))

    assert normalized is not None
    assert normalized["mouse"] == {
        "dx": 30,
        "dy": -12,
        "scroll": 2,
        "left": 1,
        "right": 0,
        "middle": 0,
    }


def test_server_rejects_invalid_or_unbounded_mouse_payloads():
    for mouse in (
        {"dx": 2049},
        {"dy": 1.5},
        {"scroll": 21},
        {"left": 2},
    ):
        assert validate_client_message(_phone_message(mouse)) is None


def test_client_row_constructs_and_keeps_gamepad_and_mouse_modes_exclusive():
    widget = ClientListItemWidget(("127.0.0.1", 5000), "127.0.0.1:5000")

    assert not widget.is_running()
    assert not widget.is_mouse_running()
    widget.set_running(True)
    assert widget.is_running()
    assert not widget.is_mouse_running()
    widget.set_mouse_running(True)
    assert not widget.is_running()
    assert widget.is_mouse_running()
    assert widget.btn_mouse.text() == "Stop Mouse"


def test_phone_mouse_mapper_moves_scrolls_and_releases_buttons(monkeypatch):
    calls = []
    monkeypatch.setattr(Mouse, "moveRel", lambda *args, **kwargs: calls.append(("move", args)))
    monkeypatch.setattr(Mouse, "scroll", lambda value: calls.append(("scroll", value)))
    monkeypatch.setattr(Mouse, "buttonDown", lambda value: calls.append(("down", value)))
    monkeypatch.setattr(Mouse, "buttonUp", lambda value: calls.append(("up", value)))

    mapper = Phone_mapper.__new__(Phone_mapper)
    mapper._connected = True
    mapper._mouse_buttons = {"left": False, "right": False, "middle": False}

    payload = validate_client_message(_phone_message({
        "dx": 30, "dy": -12, "scroll": 2, "left": True,
    }))
    mapper.handle_mouse_data(payload["mouse"])
    assert calls == [
        ("move", (30, -12)),
        ("scroll", 2),
        ("down", "left"),
    ]

    mapper.release_mouse_buttons()
    assert calls[-1] == ("up", "left")
    assert not mapper._mouse_buttons["left"]
