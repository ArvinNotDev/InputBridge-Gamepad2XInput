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


def test_flask_serves_mobile_focus_and_touch_gesture_styles():
    from core.web_remote import WebRemoteServer

    client = WebRemoteServer(object(), object(), object()).app.test_client()
    css = client.get("/static/app.css")

    assert css.status_code == 200
    assert b"orientation:portrait" in css.data
    assert b"orientation:landscape" in css.data
    assert b"body.focus-mode" in css.data
    assert b"overflow-x:auto" in css.data
    assert b"overscroll-behavior-y:auto" in css.data
    assert b"touch-action:none" in css.data


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


def test_disconnect_releases_the_browser_controller_session():
    import time
    from core.web_remote import WebRemoteServer

    class Mapper:
        def __init__(self):
            self.calls = []

        def reset_gamepad(self):
            self.calls.append("reset_gamepad")

        def release_mouse_buttons(self):
            self.calls.append("release_mouse_buttons")

        def shutdown(self):
            self.calls.append("shutdown")

    class Remote:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    server = WebRemoteServer(object(), object(), object())
    mapper, remote, token = Mapper(), Remote(), "test-browser-token"
    with server._lock:
        server._sessions[token] = {
            "uuid": "web-test", "name": "Test browser", "mapper": mapper,
            "remote": remote, "last_seen": time.monotonic(), "mode": "gamepad",
        }

    response = server.app.test_client().post(
        "/api/disconnect", headers={"Authorization": f"Bearer {token}"}, json={}
    )

    assert response.status_code == 200
    assert response.get_json()["ok"] is True
    assert token not in server._sessions
    assert mapper.calls == ["reset_gamepad", "release_mouse_buttons", "shutdown"]
    assert remote.closed is True


def test_web_tls_certificate_covers_advertised_lan_ip_and_reuses_matching_identity(tmp_path):
    import ssl
    from cryptography import x509
    from core.remote_security import create_web_server_ssl_context

    certificate_path = tmp_path / "web_server.crt"
    key_path = tmp_path / "web_server.key"
    context, fingerprint = create_web_server_ssl_context(
        ["192.168.77.21"], certificate_path, key_path
    )
    certificate = x509.load_pem_x509_certificate(certificate_path.read_bytes())
    sans = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    ip_names = {str(value) for value in sans.get_values_for_type(x509.IPAddress)}
    assert "192.168.77.21" in ip_names
    assert "127.0.0.1" in ip_names
    assert context.minimum_version == ssl.TLSVersion.TLSv1_2
    assert len(fingerprint.replace(":", "")) == 64

    _context_again, fingerprint_again = create_web_server_ssl_context(
        ["192.168.77.21"], certificate_path, key_path
    )
    assert fingerprint_again == fingerprint

    _new_context, fingerprint_new_host = create_web_server_ssl_context(
        ["192.168.77.22"], certificate_path, key_path
    )
    assert fingerprint_new_host != fingerprint
    new_cert = x509.load_pem_x509_certificate(certificate_path.read_bytes())
    new_sans = new_cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert "192.168.77.22" in {str(value) for value in new_sans.get_values_for_type(x509.IPAddress)}
