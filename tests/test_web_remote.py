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


def test_flask_serves_responsive_ui_and_security_headers():
    from core.web_remote import WebRemoteServer

    server = WebRemoteServer(object(), object(), object())
    client = server.app.test_client()
    page = client.get("/")
    assert page.status_code == 200
    assert b"Gamepad" in page.data and b"PC Remote" in page.data
    assert page.headers["Cache-Control"] == "no-store"
    assert "default-src 'self'" in page.headers["Content-Security-Policy"]
    assert page.headers["X-Frame-Options"] == "DENY"


def test_public_server_info_reports_the_tls_fingerprint_and_https_scheme():
    from core.web_remote import WebRemoteServer

    server = WebRemoteServer(object(), object(), object())
    server.fingerprint = "AA:" * 31 + "AA"
    response = server.app.test_client().get("/api/info", base_url="https://localhost")
    assert response.status_code == 200
    assert response.get_json()["fingerprint"] == server.fingerprint
    assert response.get_json()["secure"] is True


def test_pairing_and_state_endpoints_reject_bad_or_missing_credentials():
    from core.web_remote import WebRemoteServer

    client = WebRemoteServer(object(), object(), object()).app.test_client()
    bad_code = client.post("/api/pair", json={"code": "123", "name": "Test"})
    assert bad_code.status_code == 400
    no_token = client.post("/api/state", json={"mode": "gamepad"})
    assert no_token.status_code == 401
