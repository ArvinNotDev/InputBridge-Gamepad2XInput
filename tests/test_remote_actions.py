import pytest
from core.remote_actions import DEFAULT_REMOTE_PERMISSIONS, RemoteActionSession, remote_capabilities


def _request(action, payload=None, request_id="req_01"):
    return {"protocol_version": 1, "request_id": request_id, "action": action, "payload": payload or {}}


def test_remote_permissions_are_disabled_by_default():
    assert all(value is False for value in DEFAULT_REMOTE_PERMISSIONS.values())
    assert all(value is False for name, value in remote_capabilities().items() if name != "pc_status")
    assert remote_capabilities()["pc_status"] is True


def test_status_is_available_and_reports_real_machine_values():
    result = RemoteActionSession().execute(_request("pc_status"), DEFAULT_REMOTE_PERMISSIONS)
    assert result["computer_name"]
    assert result["operating_system"]
    assert result["capabilities"]["pc_status"] is True
    assert "volume_level" not in result


def test_permission_denied_before_adapter_runs():
    called = []
    with pytest.raises(PermissionError):
        RemoteActionSession().execute(
            _request("clipboard_set", {"text": "do not copy"}),
            dict(DEFAULT_REMOTE_PERMISSIONS, clipboard=False),
            adapters={"clipboard_set": lambda payload: called.append(payload)},
        )
    assert called == []


def test_allowlisted_action_uses_adapter_for_testability():
    seen = []
    result = RemoteActionSession().execute(
        _request("media", {"command": "mute"}),
        dict(DEFAULT_REMOTE_PERMISSIONS, media=True),
        adapters={"media": lambda payload: seen.append(payload["command"]) or {"done": True}},
    )
    assert result == {"done": True}
    assert seen == ["mute"]


def test_invalid_request_fails_before_adapter_runs():
    with pytest.raises(ValueError):
        RemoteActionSession().execute(
            _request("launch_app", {"app": "powershell"}),
            DEFAULT_REMOTE_PERMISSIONS,
            adapters={"launch_app": lambda payload: {"launched": True}},
        )


def test_permissions_persist_atomically_and_invalid_values_use_defaults(tmp_path):
    from core.remote_actions import load_remote_permissions, save_remote_permissions
    path = tmp_path / "remote_permissions.json"
    save_remote_permissions({"power": True, "clipboard": "yes"}, path)
    restored = load_remote_permissions(path)
    assert restored["power"] is True
    assert restored["clipboard"] is False
    assert restored["keyboard"] is False
