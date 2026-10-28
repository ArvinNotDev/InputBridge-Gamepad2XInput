from core.web_remote import validate_web_controller_state


def test_browser_state_is_normalized_with_neutral_defaults():
    result = validate_web_controller_state({"mode": "gamepad", "buttons": {"A": True}, "joystick": {"left_x": 255}})
    assert result is not None
    assert result["buttons"]["A"] == 1 and result["buttons"]["B"] == 0
    assert result["analog"] == {"L2": 0, "R2": 0}
    assert result["joystick"] == {"left_x": 255, "left_y": 128, "right_x": 128, "right_y": 128}


def test_invalid_browser_input_is_rejected():
    values = [
        {"mode": "shell"}, {"buttons": {"SHELL": 1}}, {"buttons": {"A": 3}},
        {"joystick": {"left_x": 256}}, {"mode": "mouse", "mouse": {"dx": 2049}},
        {"mode": "mouse", "mouse": {"scroll": 21}}, {"mode": "mouse", "mouse": {"left": "yes"}},
        {"unexpected": True},
    ]
    for value in values:
        assert validate_web_controller_state(value) is None


def test_bounded_touch_mouse_state_accepts_boolean_button_values():
    result = validate_web_controller_state({"mode": "mouse", "mouse": {"dx": -2048, "dy": 2048, "scroll": -20, "left": True}})
    assert result is not None
    assert result["mouse"] == {"dx": -2048, "dy": 2048, "scroll": -20, "left": 1, "right": 0, "middle": 0}
