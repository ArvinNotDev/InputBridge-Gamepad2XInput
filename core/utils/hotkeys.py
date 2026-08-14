from __future__ import annotations

import json
import os
import time
from typing import Iterable, Union, Dict, List, Tuple, Any


BinaryLike = Union[
    bytes,
    bytearray,
    str,
    Iterable[int],
]


class Hotkey:
    """
    Manages controller hotkey mappings stored in a JSON file.

    Mapping format in JSON:
        {
            "<binary_pattern>": "<function_name>"
        }

    Example:
        {
            "10001000000000": "volume up",
            "00000000000011": "next track"
        }

    Each binary pattern represents the pressed state of the controller buttons
    defined in `buttons_layout`.
    """

    def __init__(self, keys_file_name: str):
        """
        Initialize the hotkey manager and load existing mappings.

        :param keys_file_name: Path to the JSON file used for persistence.
        """
        self.keys_file_name = keys_file_name

        # Controller button order (must match UI / controller monitor mapping)
        self.buttons_layout = [
            "a", "b", "y", "x",
            "start", "back",
            "r3", "l3",
            "up", "down", "right", "left",
            "rb", "lb",
        ]

        # Allowed actions for hotkeys
        self.function_choices = [
            "volume up",
            "volume down",
            "play/pause media",
            "next track",
            "previous track",
            "volume mute",
        ]

        # { "<binary_pattern>": "<function_name>" }
        self.keys: Dict[str, str] = {}
        self._keys_mtime_ns: int | None = None
        self._last_refresh_check = 0.0
        self._refresh_check_interval = 0.5

        self.update_hotkeys(force=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_hotkey(self, binary_input: BinaryLike, function: str) -> Tuple[bool, str]:
        """
        Register a new hotkey mapping.

        :param binary_input: Button state representation.
        :param function: Action name to bind.
        :return: (success, message)
        """
        if function not in self.function_choices:
            return False, f"Unknown function '{function}'. Allowed: {self.function_choices}"

        normalized = self._normalize_binary_input(binary_input)

        if len(normalized) != len(self.buttons_layout):
            return (
                False,
                f"Binary input length must be {len(self.buttons_layout)} "
                f"(got {len(normalized)}).",
            )

        pattern = "".join("1" if v else "0" for v in normalized)

        self.keys[pattern] = function
        self._save_hotkeys()

        pressed = self._translate_binary_to_key(normalized)
        return True, f"{pattern} => {function} ({pressed})"

    def get_hotkey(self, binary_input: BinaryLike) -> Tuple[bool, str, str]:
        """
        Resolve a binary button pattern to its assigned function.

        :param binary_input: Button state representation.
        :return: (success, function_name, message)
        """
        self.update_hotkeys()

        normalized = self._normalize_binary_input(binary_input)

        if len(normalized) != len(self.buttons_layout):
            return (
                False,
                "",
                f"Binary input length must be {len(self.buttons_layout)} "
                f"(got {len(normalized)}).",
            )

        pattern = "".join("1" if v else "0" for v in normalized)

        function = self.keys.get(pattern)
        if not function:
            return False, "", f"No hotkey assigned for pattern '{pattern}'."

        pressed = self._translate_binary_to_key(normalized)

        return True, function, f"{pattern} => {function} ({pressed})"

    def clear_hotkey(self, binary_input: BinaryLike) -> Tuple[bool, str]:
        """
        Remove a hotkey mapping.

        :param binary_input: Button pattern to remove.
        :return: (success, message)
        """
        self.update_hotkeys()

        normalized = self._normalize_binary_input(binary_input)

        if len(normalized) != len(self.buttons_layout):
            return (
                False,
                f"Binary input length must be {len(self.buttons_layout)} "
                f"(got {len(normalized)}).",
            )

        pattern = "".join("1" if v else "0" for v in normalized)

        if pattern in self.keys:
            del self.keys[pattern]
            self._save_hotkeys()
            return True, f"Cleared mapping for pattern '{pattern}'."

        return False, f"No mapping stored for pattern '{pattern}'."

    def list_hotkeys(self) -> Dict[str, Dict[str, Any]]:
        """
        Return all registered hotkeys with decoded button names.

        Output format:
        {
            "<pattern>": {
                "function": "<function_name>",
                "pressed": ["button1", "button2"]
            }
        }
        """
        self.update_hotkeys()

        result: Dict[str, Dict[str, Any]] = {}

        for pattern, function in self.keys.items():
            try:
                normalized = self._normalize_binary_input(pattern)
            except ValueError:
                continue

            if len(normalized) != len(self.buttons_layout):
                continue

            pressed = self._translate_binary_to_key(normalized)

            result[pattern] = {
                "function": function,
                "pressed": pressed,
            }

        return result

    # ------------------------------------------------------------------
    # Binary Translation / Validation
    # ------------------------------------------------------------------

    def _translate_binary_to_key(self, normalized_bits: List[bool]) -> List[str]:
        """
        Convert a binary button state to human-readable button names.

        :param normalized_bits: Boolean button state list.
        :return: List of pressed button names.
        """
        pressed: List[str] = []

        for index, is_pressed in enumerate(normalized_bits):
            if is_pressed:
                pressed.append(self.buttons_layout[index])

        return pressed

    def _normalize_binary_input(self, binary_input: BinaryLike) -> List[bool]:
        """
        Normalize various binary representations into a boolean list.

        Accepted formats:
            - bytes / bytearray
            - binary string ("010010...")
            - iterable of ints (0/1 or ASCII 48/49)

        :return: List[bool] where True indicates a pressed button.
        """
        if isinstance(binary_input, (bytes, bytearray)):
            try:
                return self._normalize_binary_input(binary_input.decode("ascii"))
            except UnicodeDecodeError:
                return [bool(b) for b in binary_input]

        if isinstance(binary_input, str):
            s = binary_input.strip().replace(" ", "")

            if any(ch not in "01" for ch in s):
                raise ValueError(
                    f"Binary string must contain only '0' or '1' (got {binary_input!r})"
                )

            return [ch == "1" for ch in s]

        bits: List[bool] = []

        for value in binary_input:
            if value in (0, 1):
                bits.append(bool(value))
            elif value in (48, 49):  # ASCII '0' / '1'
                bits.append(value == 49)
            else:
                raise ValueError(f"Invalid bit value: {value!r}. Expected 0/1 or 48/49.")

        return bits

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def update_hotkeys(self, force: bool = False) -> None:
        """
        Load hotkeys from the JSON file.

        If the file is missing or corrupted, an empty mapping is created.
        """
        now = time.monotonic()
        if (
            not force
            and now - self._last_refresh_check < self._refresh_check_interval
        ):
            return
        self._last_refresh_check = now

        if not os.path.exists(self.keys_file_name):
            self.keys = {}
            if force:
                self._save_hotkeys()
            return

        try:
            mtime_ns = os.stat(self.keys_file_name).st_mtime_ns
            if not force and mtime_ns == self._keys_mtime_ns:
                return

            with open(self.keys_file_name, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                self.keys = {}
            else:
                self.keys = {str(k): str(v) for k, v in data.items()}
            self._keys_mtime_ns = mtime_ns

        except (json.JSONDecodeError, OSError):
            self.keys = {}
            self._keys_mtime_ns = None
            if force:
                self._save_hotkeys()

    def _save_hotkeys(self) -> None:
        """
        Persist hotkey mappings to the JSON file.
        """
        os.makedirs(os.path.dirname(self.keys_file_name) or ".", exist_ok=True)

        with open(self.keys_file_name, "w", encoding="utf-8") as f:
            json.dump(self.keys, f, indent=2, ensure_ascii=False)
        try:
            self._keys_mtime_ns = os.stat(self.keys_file_name).st_mtime_ns
        except OSError:
            self._keys_mtime_ns = None
