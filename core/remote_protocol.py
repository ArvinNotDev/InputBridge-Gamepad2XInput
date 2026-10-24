"""Versioned, bounded JSON-line protocol for authenticated remote actions."""
from __future__ import annotations
import json
import re
from typing import Any

PROTOCOL_VERSION = 1
MAX_FRAME_BYTES = 16 * 1024
MAX_REMOTE_TEXT_CHARS = 4096
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

KEY_NAMES = {
    "ENTER": "enter", "TAB": "tab", "ESCAPE": "esc", "BACKSPACE": "backspace",
    "DELETE": "delete", "SPACE": "space", "UP": "up", "DOWN": "down", "LEFT": "left",
    "RIGHT": "right", "HOME": "home", "END": "end", "PAGE_UP": "page up",
    "PAGE_DOWN": "page down", "INSERT": "insert",
    "F1": "f1", "F2": "f2", "F3": "f3", "F4": "f4", "F5": "f5", "F6": "f6",
    "F7": "f7", "F8": "f8", "F9": "f9", "F10": "f10", "F11": "f11", "F12": "f12",
}
MODIFIER_KEYS = {"CTRL": "ctrl", "SHIFT": "shift", "ALT": "alt", "WIN": "windows"}
SHORTCUTS = {
    "copy": "ctrl+c", "paste": "ctrl+v", "cut": "ctrl+x", "undo": "ctrl+z",
    "redo": "ctrl+y", "select_all": "ctrl+a", "save": "ctrl+s", "find": "ctrl+f",
    "alt_tab": "alt+tab", "show_desktop": "windows+d",
}
MEDIA_ACTIONS = {"volume_up", "volume_down", "mute", "play_pause", "previous_track", "next_track", "stop"}
APP_SHORTCUTS = {"browser", "explorer", "calculator", "notepad", "downloads"}
PRESENTATION_ACTIONS = {"next", "previous", "start", "end", "black_screen"}
POWER_ACTIONS = {"lock", "sleep", "logoff", "restart", "shutdown", "display_off"}
ACTION_PERMISSION = {
    "keyboard_text": "keyboard", "keyboard_key": "keyboard",
    "keyboard_shortcut": "keyboard", "keyboard_modifier": "keyboard",
    "clipboard_set": "clipboard", "clipboard_get": "clipboard",
    "media": "media", "pc_status": "status", "launch_app": "app_launch",
    "presentation": "presentation", "power_action": "power",
}


def _is_text(value: Any, *, max_length: int = MAX_REMOTE_TEXT_CHARS) -> bool:
    if not isinstance(value, str) or len(value) > max_length:
        return False
    return not any((ord(char) < 32 and char not in "\n\r\t") or ord(char) == 127 for char in value)


def validate_remote_request(candidate: Any) -> dict[str, Any] | None:
    """Validate and normalize one action request. Return None if any field is invalid."""
    if not isinstance(candidate, dict) or set(candidate) - {"request_id", "action", "payload", "protocol_version"}:
        return None
    request_id = candidate.get("request_id")
    action = candidate.get("action")
    payload = candidate.get("payload", {})
    version = candidate.get("protocol_version", PROTOCOL_VERSION)
    if (
        not isinstance(request_id, str) or not _REQUEST_ID_RE.fullmatch(request_id)
        or type(version) is not int or version != PROTOCOL_VERSION
        or not isinstance(action, str) or action not in ACTION_PERMISSION
        or not isinstance(payload, dict)
    ):
        return None
    normalized = {}
    if action in {"keyboard_text", "clipboard_set"}:
        if set(payload) != {"text"} or not _is_text(payload["text"]):
            return None
        normalized["text"] = payload["text"]
    elif action == "keyboard_key":
        if set(payload) != {"key"} or payload.get("key") not in KEY_NAMES:
            return None
        normalized["key"] = payload["key"]
    elif action == "keyboard_modifier":
        if set(payload) != {"key", "pressed"} or payload.get("key") not in MODIFIER_KEYS or type(payload.get("pressed")) is not bool:
            return None
        normalized.update(key=payload["key"], pressed=payload["pressed"])
    elif action == "keyboard_shortcut":
        if set(payload) != {"shortcut"} or payload.get("shortcut") not in SHORTCUTS:
            return None
        normalized["shortcut"] = payload["shortcut"]
    elif action == "media":
        if set(payload) != {"command"} or payload.get("command") not in MEDIA_ACTIONS:
            return None
        normalized["command"] = payload["command"]
    elif action == "launch_app":
        if set(payload) != {"app"} or payload.get("app") not in APP_SHORTCUTS:
            return None
        normalized["app"] = payload["app"]
    elif action == "presentation":
        if set(payload) != {"command"} or payload.get("command") not in PRESENTATION_ACTIONS:
            return None
        normalized["command"] = payload["command"]
    elif action == "power_action":
        if set(payload) != {"command"} or payload.get("command") not in POWER_ACTIONS:
            return None
        normalized["command"] = payload["command"]
    elif action in {"clipboard_get", "pc_status"} and payload:
        return None
    return {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "action": action,
        "payload": normalized,
    }


def make_remote_response(request_id: str, action: str, *, ok: bool, result: Any = None, error: str | None = None) -> dict[str, Any]:
    """Build a matching, bounded response for a single request."""
    response = {
        "protocol_version": PROTOCOL_VERSION,
        "message_type": "remote_response",
        "request_id": request_id,
        "action": action,
        "ok": bool(ok),
    }
    if ok:
        response["result"] = result if result is not None else {}
    else:
        response["error"] = str(error or "Remote action failed")[:240]
    encoded = json.dumps(response, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) + 1 > MAX_FRAME_BYTES:
        response = {
            "protocol_version": PROTOCOL_VERSION, "message_type": "remote_response",
            "request_id": request_id, "action": action, "ok": False,
            "error": "Response exceeds the protocol size limit",
        }
    return response


def encode_json_line(message: dict[str, Any]) -> bytes:
    """Encode one bounded UTF-8 JSON frame using newline framing."""
    encoded = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if not encoded or len(encoded) + 1 > MAX_FRAME_BYTES:
        raise ValueError("Protocol frame exceeds the size limit")
    return encoded + b"\n"
