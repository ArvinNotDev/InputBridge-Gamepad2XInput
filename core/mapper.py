import json
import time
from typing import Tuple

from core.emulator import EmulateX360, EmulateKeyboard
from core.emulator import media_functions, custom_commands
from core.mouse import Mouse
from core.utils.controller_monitor import controllerMonitor
from core.utils.hotkey_commander import HotkeyCommander


class Mapper:
    """
    Maps input from a physical HID controller to an emulator (X360 or keyboard).
    """

    def __init__(
        self,
        controller,
        controller_type,
        emulate_to,
        settings,
        controllers_page,
        hotkey_page,
        debug: bool = False,
    ):
        self.controller = controller
        self.controller_type = controller_type
        self._connected = False
        self.debug = debug
        self.settings = settings
        self.controllers_page = controllers_page

        self.mouse_mode = True
        self.mouse_mode_hotkey = False

        self._prev_back = False
        self._prev_r3 = False
        self._prev_a = False
        self._prev_b = False
        self._last_battery = None

        if emulate_to == "x360":
            self.emulator = EmulateX360(
                controller.device_path,
                controller.name,
                hotkey_page.hotkey,
            )
            controllers_page.add_x360_instance(self.emulator)
            hotkey_page.add_x360_instance(self.emulator)
        elif emulate_to == "keyboard":
            self.emulator = EmulateKeyboard()
        else:
            raise ValueError(f"Invalid emulate_to target: {emulate_to}")

        self.controller_config = self._load_json(f"{controller_type}.json")

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def _load_json(self, filename: str) -> dict:
        """
        Load controller profile from the profiles directory.
        """
        try:
            with open(f"profiles/{filename}", "r") as config:
                return json.load(config)
        except FileNotFoundError:
            print(f"Warning: Profile '{filename}' not found.")
            return {}
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in profile '{filename}'.")
            return {}

    def start(self) -> None:
        """
        Begin processing HID reports for this controller.
        """
        if not self._connected:
            self._connected = True
            print(f"[Mapper] Started mapping for {self.controller.name}")

    def stop(self) -> None:
        """
        Stop processing HID reports and shut down the emulator if supported.
        """
        if self._connected:
            print(f"[Mapper] Stopped mapping for {self.controller.name}")
        self._connected = False

        clear_battery = getattr(self.controllers_page, "clear_battery", None)
        if clear_battery is not None:
            try:
                clear_battery(self.controller.device_path)
            except Exception:
                pass

        if hasattr(self.emulator, "shutdown"):
            try:
                self.emulator.shutdown()
            except Exception as e:
                print(f"[Mapper] Failed to shutdown emulator: {e}")

    # -------------------------------------------------------------------------
    # HID entry points
    # -------------------------------------------------------------------------

    def handle_hid_data(self, data: bytes) -> None:
        """
        Dispatch raw HID report to the appropriate handler.
        """
        if not self._connected:
            return

        if isinstance(self.emulator, EmulateX360):
            self._handle_x360_input(data)
        else:
            self._handle_keyboard_input(data)

    def handle_error(self, msg: str) -> None:
        """
        Handle device-level errors.
        """
        print(f"[Mapper] Error from device {self.controller.name}: {msg}")
        self.stop()

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _clamp(v: int, lo: int, hi: int) -> int:
        return max(lo, min(hi, v))

    @staticmethod
    def _scale_stick_0_255_to_x360(val: int, invert_y: bool) -> int:
        """
        Convert 0–255 axis value to XInput signed 16‑bit range.
        """
        centered = float(val) - 128.0
        normalized = -centered / 127.0 if invert_y else centered / 127.0
        scaled = int(round(normalized * 32767.0))
        return int(Mapper._clamp(scaled, -32768, 32767))

    def _read_byte_safe(self, report: list[int], idx: int | None) -> int:
        """
        Safely read a byte from a HID report by index.
        """
        if idx is None or idx < 0 or idx >= len(report):
            return 0
        return report[idx]

    def _get_button_from_cfg(self, report: list[int], cfg: dict | None) -> bool:
        """
        Decode a digital button state from the report using a mapping entry.
        """
        if cfg is None:
            return False

        byte_idx = cfg.get("index", cfg.get("byte"))
        val = self._read_byte_safe(report, byte_idx)

        mask = cfg.get("mask")
        if mask is not None:
            mask_int = int(mask, 16) if isinstance(mask, str) else int(mask)
            val &= mask_int

        if "value" in cfg:
            return val == cfg["value"]
        return val != 0

    def _get_dpad_from_hat(self, report: list[int], cfg: dict | None) -> Tuple[bool, bool, bool, bool]:
        """
        Decode a hat‑switch style D‑Pad into individual directions.
        """
        if cfg is None:
            return False, False, False, False

        byte_idx = cfg.get("byte")
        raw_val = self._read_byte_safe(report, byte_idx)

        mask = cfg.get("mask", 0x0F)
        if isinstance(mask, str):
            mask = int(mask, 16)

        hat_val = raw_val & mask

        up = hat_val in (0, 1, 7)
        down = hat_val in (3, 4, 5)
        right = hat_val in (1, 2, 3)
        left = hat_val in (5, 6, 7)

        return up, down, left, right

    def _apply_deadzone(
        self,
        raw_x: int,
        raw_y: int,
        deadzone: float,
        invertion: Tuple[bool, bool],
    ) -> Tuple[int, int]:
        """
        Apply radial deadzone and axis inversion, then scale to XInput space.
        """
        invert_x, invert_y = invertion

        cx = raw_x - 128
        cy = raw_y - 128

        if abs(cx) < deadzone * 127:
            cx = 0
        if abs(cy) < deadzone * 127:
            cy = 0

        x_scaled = self._scale_stick_0_255_to_x360(cx + 128, invert_x)
        y_scaled = self._scale_stick_0_255_to_x360(cy + 128, invert_y)

        return x_scaled, y_scaled

    def _apply_button_invertion(self, button: bool, invert: bool) -> bool:
        """
        Optionally invert a digital button state.
        """
        return not button if invert else button

    # -------------------------------------------------------------------------
    # X360 mapping (physical HID)
    # -------------------------------------------------------------------------
    def _interpret_battery(self, battery_byte):
        battery_level = battery_byte & 0x0F  # Lower 4 bits
        charging_state = (battery_byte >> 4) & 0x0F  # Upper 4 bits

        is_charging = (charging_state == 0x02)

        if battery_level == 0x0A:
            percent = 100
        elif battery_level <= 0x09:
            percent = battery_level * 10
        else:
            percent = 100

        # If charging and level shows 9, might actually be full
        if is_charging and battery_level == 0x09:
            percent = 100

        return percent, is_charging

    def _handle_x360_input(self, data: bytes) -> None:
        """
        Decode a HID report and forward it to the X360 emulator.
        """
        report = list(data)
        if len(report) < 10:
            return

        axes_cfg = self.controller_config.get("axes", {})
        buttons_cfg = self.controller_config.get("buttons", {})
        dpad_cfg = self.controller_config.get("dpad_hat", {})
        battery_cfg = self.controller_config.get("battery_status", {})

        raw_ljx = self._read_byte_safe(report, axes_cfg.get("left_stick_x", {}).get("byte"))
        raw_ljy = self._read_byte_safe(report, axes_cfg.get("left_stick_y", {}).get("byte"))
        raw_rjx = self._read_byte_safe(report, axes_cfg.get("right_stick_x", {}).get("byte"))
        raw_rjy = self._read_byte_safe(report, axes_cfg.get("right_stick_y", {}).get("byte"))
        raw_lt = self._read_byte_safe(report, axes_cfg.get("left_trigger", {}).get("byte"))
        raw_rt = self._read_byte_safe(report, axes_cfg.get("right_trigger", {}).get("byte"))
        battery_percent = None
        is_charging = False
        battery_percent_cfg = battery_cfg.get("percent", {})
        if battery_percent_cfg.get("byte") is not None:
            raw_battery = self._read_byte_safe(
                report, battery_percent_cfg.get("byte")
            )
            battery_percent, is_charging = self._interpret_battery(raw_battery)
            self._publish_battery(battery_percent, is_charging)


        left_deadzone, right_deadzone = self.settings.get_deadzones()
        left_inv, right_inv = self.settings.get_joystick_invertion()
        button_inv = self.settings.get_button_invertion()

        ljx, ljy = self._apply_deadzone(raw_ljx, raw_ljy, left_deadzone, left_inv)
        rjx, rjy = self._apply_deadzone(raw_rjx, raw_rjy, right_deadzone, right_inv)

        lt = int(raw_lt)
        rt = int(raw_rt)

        a = self._get_button_from_cfg(report, buttons_cfg.get("cross"))
        b = self._get_button_from_cfg(report, buttons_cfg.get("circle"))
        x_ = self._get_button_from_cfg(report, buttons_cfg.get("square"))
        y_ = self._get_button_from_cfg(report, buttons_cfg.get("triangle"))
        lb = self._get_button_from_cfg(report, buttons_cfg.get("l1"))
        rb = self._get_button_from_cfg(report, buttons_cfg.get("r1"))
        back = self._get_button_from_cfg(report, buttons_cfg.get("share"))
        start = self._get_button_from_cfg(report, buttons_cfg.get("option"))
        l3 = self._get_button_from_cfg(report, buttons_cfg.get("l3"))
        r3 = self._get_button_from_cfg(report, buttons_cfg.get("r3"))

        dpu, dpd, dpl, dpr = self._get_dpad_from_hat(report, dpad_cfg)

        a = self._apply_button_invertion(a, button_inv)
        b = self._apply_button_invertion(b, button_inv)
        x_ = self._apply_button_invertion(x_, button_inv)
        y_ = self._apply_button_invertion(y_, button_inv)
        lb = self._apply_button_invertion(lb, button_inv)
        rb = self._apply_button_invertion(rb, button_inv)
        back = self._apply_button_invertion(back, button_inv)
        start = self._apply_button_invertion(start, button_inv)
        l3 = self._apply_button_invertion(l3, button_inv)
        r3 = self._apply_button_invertion(r3, button_inv)

        if back and r3 and not (self._prev_back and self._prev_r3):
            self.mouse_mode_hotkey = not self.mouse_mode_hotkey

        self.mouse_mode = self.settings.get_mouse_mode()

        if self.mouse_mode or self.mouse_mode_hotkey:
            if not hasattr(self, "_mx"):
                self._mx = 0.0
                self._my = 0.0

            sensitivity = self.settings.get_mouse_sensitivity()
            nx = ljx / 32768.0
            ny = ljy / 32768.0

            speed = 35.0 * sensitivity
            target_dx = nx * speed
            target_dy = -ny * speed

            alpha = 0.25
            self._mx = self._mx * (1.0 - alpha) + target_dx * alpha
            self._my = self._my * (1.0 - alpha) + target_dy * alpha

            try:
                Mouse.moveRel(self._mx, self._my, duration=0)
                if a and not self._prev_a:
                    Mouse.leftClick()
                if b and not self._prev_b:
                    Mouse.rightClick()
            except Exception:
                pass

            self._prev_a = a
            self._prev_b = b
        else:
            self.emulator.update(
                ljx, ljy, rjx, rjy,
                a, x_, b, y_,
                rb, rt, lb, lt,
                dpu, dpd, dpr, dpl,
                back, start, l3, r3,
            )

        self._prev_back = back
        self._prev_r3 = r3

    def _publish_battery(self, percent: int, is_charging: bool) -> None:
        """Publish battery changes without touching Qt widgets from HID threads."""
        state = (int(percent), bool(is_charging))
        if state == self._last_battery:
            return
        self._last_battery = state
        publisher = getattr(self.controllers_page, "battery_updated", None)
        if publisher is not None:
            try:
                publisher.emit(self.controller.device_path, *state)
            except Exception:
                pass

    def _handle_keyboard_input(self, data: bytes) -> None:
        """
        Placeholder for keyboard emulation mapping.
        """
        pass


class Phone_mapper:
    """
    Maps input from a network client (phone) to an emulator (X360 or keyboard).
    """

    def __init__(
        self,
        uuid: str,
        emulate_to: str,
        controllers_page,
        hotkey_page,
        settings,
        debug: bool = False,
    ):
        self.uuid = uuid
        self.settings = settings
        self.debug = debug
        self._connected = True
        self.controllers_page = controllers_page
        self.hotkey = hotkey_page.hotkey
        self.hotkey_commander = HotkeyCommander(media_functions, custom_commands)
        self._last_hotkey_func = None
        self._last_hotkey_time = 0.0
        self._hotkey_interval = 0.1

        if emulate_to == "x360":
            self.emulator = EmulateX360(self.uuid, self.uuid, hotkey_page.hotkey)
        elif emulate_to == "keyboard":
            self.emulator = EmulateKeyboard()
        else:
            raise ValueError(f"Invalid emulate_to target: {emulate_to}")

    # -------------------------------------------------------------------------
    # HID entry points
    # -------------------------------------------------------------------------

    def handle_hid_data(self, data: dict) -> None:
        """
        Dispatch JSON gamepad state from phone to the appropriate handler.
        """
        if not self._connected:
            return

        if isinstance(self.emulator, EmulateX360):
            self._handle_x360_input(data)
        else:
            self._handle_keyboard_input(data)

    def _handle_keyboard_input(self, data: dict) -> None:
        """
        Placeholder for keyboard emulation mapping from phone input.
        """
        pass

    # -------------------------------------------------------------------------
    # Helpers (kept separate from Mapper for loose coupling)
    # -------------------------------------------------------------------------

    @staticmethod
    def _clamp(v: int, lo: int, hi: int) -> int:
        return max(lo, min(hi, v))

    @staticmethod
    def _scale_stick_0_255_to_x360(val: int, invert_y: bool) -> int:
        centered = float(val) - 128.0
        normalized = -centered / 127.0 if invert_y else centered / 127.0
        scaled = int(round(normalized * 32767.0))
        return int(Phone_mapper._clamp(scaled, -32768, 32767))

    def _apply_deadzone(
        self,
        raw_x: int,
        raw_y: int,
        deadzone: float,
        invertion: Tuple[bool, bool],
    ) -> Tuple[int, int]:
        """
        Apply deadzone and inversion for phone joystick input (0–255).
        """
        invert_x, invert_y = invertion

        cx = raw_x - 128
        cy = raw_y - 128

        if abs(cx) < deadzone * 127:
            cx = 0
        if abs(cy) < deadzone * 127:
            cy = 0

        x_scaled = self._scale_stick_0_255_to_x360(cx + 128, invert_x)
        y_scaled = self._scale_stick_0_255_to_x360(cy + 128, invert_y)

        return x_scaled, y_scaled

    def _apply_button_invertion(self, button: bool, invert: bool) -> bool:
        """
        Optionally invert a digital button state.
        """
        return not button if invert else button

    def _maybe_do_hotkey(self, ok: bool, func: str | None) -> None:
        if not ok or func is None:
            self._last_hotkey_func = None
            return

        now = time.monotonic()
        if func != self._last_hotkey_func:
            self._last_hotkey_func = func
            self._last_hotkey_time = now
            self.hotkey_commander.do(func, False)
            return

        if now - self._last_hotkey_time >= self._hotkey_interval:
            self._last_hotkey_time = now
            self.hotkey_commander.do(func, False)

    # -------------------------------------------------------------------------
    # X360 mapping (phone JSON)
    # -------------------------------------------------------------------------

    def _handle_x360_input(self, data: dict) -> None:
        """
        Decode JSON controller state from phone and forward it to the X360 emulator.
        """
        buttons = data.get("buttons", {})
        analog = data.get("analog", {})
        joystick = data.get("joystick", {})

        left_deadzone, right_deadzone = self.settings.get_deadzones()
        left_inv, right_inv = self.settings.get_joystick_invertion()
        button_inv = self.settings.get_button_invertion()

        lx_val = joystick.get("left_x", 128)
        ly_val = joystick.get("left_y", 128)
        rx_val = joystick.get("right_x", 128)
        ry_val = joystick.get("right_y", 128)

        ljx, ljy = self._apply_deadzone(lx_val, ly_val, left_deadzone, left_inv)
        rjx, rjy = self._apply_deadzone(rx_val, ry_val, right_deadzone, right_inv)

        a = buttons.get("A", False)
        b = buttons.get("B", False)
        x_ = buttons.get("X", False)
        y_ = buttons.get("Y", False)
        lb = buttons.get("LB", False)
        rb = buttons.get("RB", False)
        back = buttons.get("BACK", False)
        start = buttons.get("START", False)
        l3 = buttons.get("L3", False)
        r3 = buttons.get("R3", False)
        dpu = buttons.get("DPAD_UP", False)
        dpd = buttons.get("DPAD_DOWN", False)
        dpr = buttons.get("DPAD_RIGHT", False)
        dpl = buttons.get("DPAD_LEFT", False)

        rt = analog.get("R2", 0)
        lt = analog.get("L2", 0)

        a = self._apply_button_invertion(a, button_inv)
        b = self._apply_button_invertion(b, button_inv)
        x_ = self._apply_button_invertion(x_, button_inv)
        y_ = self._apply_button_invertion(y_, button_inv)
        lb = self._apply_button_invertion(lb, button_inv)
        rb = self._apply_button_invertion(rb, button_inv)
        back = self._apply_button_invertion(back, button_inv)
        start = self._apply_button_invertion(start, button_inv)
        l3 = self._apply_button_invertion(l3, button_inv)
        r3 = self._apply_button_invertion(r3, button_inv)

        binary, _, _, _, _, _, _ = controllerMonitor.monitor(
            a, b, y_, x_, start, back,
            r3, l3, dpu, dpd, dpr, dpl, rb, lb,
            rt, lt, ljx, ljy, rjx, rjy,
        )
        ok, func, _ = self.hotkey.get_hotkey(binary)
        self._maybe_do_hotkey(ok, func)

        self.emulator.update(
            ljx, ljy, rjx, rjy,
            a, x_, b, y_,
            rb, rt, lb, lt,
            dpu, dpd, dpr, dpl,
            back, start, l3, r3,
        )

    def shutdown(self) -> None:
        self._connected = False
        if hasattr(self.emulator, "shutdown"):
            try:
                self.emulator.shutdown()
            except Exception as exc:
                print(f"[Phone_mapper] Failed to shutdown emulator: {exc}")
