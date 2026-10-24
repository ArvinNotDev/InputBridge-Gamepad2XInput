import json
from core.remote_protocol import MAX_FRAME_BYTES, PROTOCOL_VERSION, encode_json_line, make_remote_response, validate_remote_request


def _request(action, payload=None, request_id="req_01"):
    return {"protocol_version": PROTOCOL_VERSION, "request_id": request_id, "action": action, "payload": payload or {}}


def test_protocol_validates_and_preserves_unicode_text():
    assert validate_remote_request(_request("keyboard_text", {"text": "Hello\n世界"}))["payload"]["text"] == "Hello\n世界"


def test_protocol_rejects_unknown_actions_extra_fields_and_invalid_ids():
    assert validate_remote_request(_request("shell", {"command": "whoami"})) is None
    assert validate_remote_request({**_request("pc_status"), "extra": "no"}) is None
    assert validate_remote_request(_request("pc_status", request_id="bad id")) is None
    assert validate_remote_request(_request("pc_status", request_id="x" * 65)) is None


def test_protocol_rejects_invalid_keys_modifiers_and_oversized_text():
    assert validate_remote_request(_request("keyboard_key", {"key": "NOT_A_KEY"})) is None
    assert validate_remote_request(_request("keyboard_modifier", {"key": "CTRL", "pressed": 1})) is None
    assert validate_remote_request(_request("keyboard_text", {"text": "x" * 4097})) is None
    assert validate_remote_request(_request("keyboard_text", {"text": "bad\u0001"})) is None


def test_protocol_rejects_untrusted_app_and_power_action_arguments():
    assert validate_remote_request(_request("launch_app", {"app": "powershell"})) is None
    assert validate_remote_request(_request("power_action", {"command": "run arbitrary"})) is None
    assert validate_remote_request(_request("launch_app", {"app": "browser", "path": "C:/"})) is None


def test_json_line_frames_are_bounded_and_parseable():
    encoded = encode_json_line({"message_type": "test", "text": "line\nbreak"})
    assert encoded.endswith(b"\n")
    assert json.loads(encoded.decode("utf-8"))["text"] == "line\nbreak"
    try:
        encode_json_line({"text": "x" * MAX_FRAME_BYTES})
    except ValueError:
        pass
    else:
        raise AssertionError("Oversized frame was not rejected")


def test_remote_response_contains_matching_request_id_and_explicit_status():
    success = make_remote_response("req_01", "pc_status", ok=True, result={"computer_name": "PC"})
    failure = make_remote_response("req_02", "media", ok=False, error="Denied")
    assert success["request_id"] == "req_01" and success["ok"] is True
    assert failure["request_id"] == "req_02" and failure["ok"] is False
    assert failure["error"] == "Denied"
