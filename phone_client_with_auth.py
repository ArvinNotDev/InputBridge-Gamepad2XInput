# -*- coding: utf-8 -*-
"""
InputBridge - Professional multi-screen Kivy gamepad client.
Redesigned from phone_client_with_auth.py; networking/protocol logic preserved.
"""

import os
import uuid
import json
import socket
import threading
from math import sqrt, atan2, cos, sin

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

try:
    from plyer import accelerometer
except Exception:
    accelerometer = None


UUID_FILE = "gamepad_uuid.txt"
LAST_IP_FILE = "last_ip.txt"
NAME_FILE = "device_name.txt"


THEME = {
    "bg":          (0.07, 0.09, 0.12, 1),
    "surface":     (0.11, 0.14, 0.19, 1),
    "surface2":    (0.15, 0.18, 0.24, 1),
    "border":      (0.22, 0.28, 0.38, 1),
    "text":        (0.95, 0.97, 1.00, 1),
    "muted":       (0.68, 0.74, 0.84, 1),
    "subtle":      (0.48, 0.54, 0.64, 1),
    "accent":      (0.22, 0.60, 1.00, 1),
    "accent2":     (0.96, 0.62, 0.18, 1),
    "success":     (0.20, 0.74, 0.42, 1),
    "danger":      (0.92, 0.28, 0.30, 1),
    "warn":        (0.94, 0.74, 0.16, 1),
    "btn":         (0.18, 0.23, 0.32, 1),
    "btn_hover":   (0.24, 0.30, 0.42, 1),
    "panel":       (0.11, 0.14, 0.19, 1),
    "panel_alt":   (0.15, 0.18, 0.24, 1),
    "a_color":     (0.98, 0.84, 0.14, 1),
    "b_color":     (0.94, 0.26, 0.24, 1),
    "x_color":     (0.20, 0.52, 0.98, 1),
    "g_color":     (0.16, 0.80, 0.34, 1),
}


Window.clearcolor = THEME["bg"]


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def load_or_create_uuid():
    if os.path.exists(UUID_FILE):
        try:
            with open(UUID_FILE, "r", encoding="utf-8") as f:
                val = f.read().strip()
                if val:
                    return val
        except Exception:
            pass

    device_uuid = str(uuid.uuid4())

    try:
        with open(UUID_FILE, "w", encoding="utf-8") as f:
            f.write(device_uuid)
    except Exception:
        pass

    return device_uuid


def load_last_ip(default="192.168.1.100"):
    if os.path.exists(LAST_IP_FILE):
        try:
            with open(LAST_IP_FILE, "r", encoding="utf-8") as f:
                ip = f.read().strip()
                if ip:
                    return ip
        except Exception:
            pass

    return default


def save_last_ip(ip):
    try:
        with open(LAST_IP_FILE, "w", encoding="utf-8") as f:
            f.write(ip.strip())
    except Exception:
        pass


def load_name(default="KivyGamepad"):
    if os.path.exists(NAME_FILE):
        try:
            with open(NAME_FILE, "r", encoding="utf-8") as f:
                name = f.read().strip()
                if name:
                    return name
        except Exception:
            pass

    return default


def save_name(name):
    try:
        with open(NAME_FILE, "w", encoding="utf-8") as f:
            f.write(name.strip())
    except Exception:
        pass


class Card(BoxLayout):
    def __init__(self, **kwargs):
        padding = kwargs.pop(
            "padding",
            (dp(12), dp(12), dp(12), dp(12))
        )
        spacing = kwargs.pop("spacing", dp(8))
        orientation = kwargs.pop("orientation", "vertical")

        self.radius = kwargs.pop("radius", dp(18))
        self.border_width = kwargs.pop("border_width", 1.0)
        self.fill_color = kwargs.pop("fill_color", THEME["surface"])
        self.border_color = kwargs.pop("border_color", THEME["border"])

        super().__init__(
            orientation=orientation,
            padding=padding,
            spacing=spacing,
            **kwargs,
        )

        with self.canvas.before:
            Color(*self.fill_color)
            self._bg = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[self.radius],
            )

            Color(*self.border_color)
            self._line = Line(
                rounded_rectangle=(
                    self.x,
                    self.y,
                    self.width,
                    self.height,
                    self.radius,
                ),
                width=self.border_width,
            )

        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *args):
        self._bg.pos = self.pos
        self._bg.size = self.size

        self._line.rounded_rectangle = (
            self.x,
            self.y,
            self.width,
            self.height,
            self.radius,
        )


class SectionTitle(Label):
    def __init__(self, **kwargs):
        kwargs.setdefault("color", THEME["text"])
        kwargs.setdefault("bold", True)
        kwargs.setdefault("halign", "left")
        kwargs.setdefault("valign", "middle")
        kwargs.setdefault("font_size", sp(17))
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(24))

        super().__init__(**kwargs)

        self.bind(size=self._update_text_size)

    def _update_text_size(self, *args):
        self.text_size = (self.width, None)


class Pill(Label):
    def __init__(self, **kwargs):
        kwargs.setdefault("color", THEME["text"])
        kwargs.setdefault("bold", True)
        kwargs.setdefault("font_size", sp(14))
        kwargs.setdefault("halign", "center")
        kwargs.setdefault("valign", "middle")

        super().__init__(**kwargs)

        self.padding = (dp(10), dp(6))
        self.size_hint = (None, None)

        self.bind(texture_size=self._fit)

        self._bg_color = THEME["btn"]

        with self.canvas.before:
            Color(*self._bg_color)
            self._bg = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(999)],
            )

        self.bind(pos=self._redraw, size=self._redraw)

    def set_color(self, color):
        self._bg_color = color

        self.canvas.before.clear()

        with self.canvas.before:
            Color(*self._bg_color)
            self._bg = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(999)],
            )

    def _fit(self, *args):
        self.size = (
            self.texture_size[0] + dp(20),
            self.texture_size[1] + dp(12),
        )

    def _redraw(self, *args):
        self._bg.pos = self.pos
        self._bg.size = self.size


def make_text_input(text, hint, input_filter=None):
    return TextInput(
        text=text,
        hint_text=hint,
        multiline=False,
        input_filter=input_filter,
        padding=(dp(12), dp(10)),
        background_color=THEME["panel_alt"],
        foreground_color=THEME["text"],
        cursor_color=THEME["accent"],
        hint_text_color=THEME["subtle"],
        size_hint_y=None,
        height=dp(42),
    )


def make_button(
    text,
    accent=None,
    font_size=sp(14),
    bold=True,
    height=dp(42),
):
    btn = Button(
        text=text,
        background_normal="",
        background_down="",
        background_color=THEME["btn"],
        color=THEME["text"],
        font_size=font_size,
        bold=bold,
        size_hint_y=None,
        height=height,
    )

    btn._base_color = THEME["btn"]
    btn._accent_color = accent if accent else THEME["btn_hover"]

    btn.bind(
        on_press=lambda inst: setattr(
            inst,
            "background_color",
            inst._accent_color,
        )
    )

    btn.bind(
        on_release=lambda inst: setattr(
            inst,
            "background_color",
            inst._base_color,
        )
    )

    return btn


def field_box(label_text, widget):
    box = BoxLayout(
        orientation="vertical",
        spacing=dp(4),
        size_hint_x=1,
    )

    if label_text:
        label = Label(
            text=label_text,
            color=THEME["subtle"],
            size_hint_y=None,
            height=dp(16),
            halign="left",
            valign="middle",
            font_size=sp(12),
        )

        label.bind(
            size=lambda inst, *_: setattr(
                inst,
                "text_size",
                inst.size,
            )
        )

        box.add_widget(label)
    else:
        box.add_widget(
            Widget(
                size_hint_y=None,
                height=dp(16),
            )
        )

    box.add_widget(widget)

    return box


def fit_label(label):
    label.bind(
        size=lambda inst, *_: setattr(
            inst,
            "text_size",
            inst.size,
        )
    )

    return label


class Joystick(Widget):
    value_x = NumericProperty(128)
    value_y = NumericProperty(128)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.knob_radius_ratio = 0.34
        self.center_x_pos = 0
        self.center_y_pos = 0
        self.base_radius = 0
        self.knob_x = 0
        self.knob_y = 0
        self._touch_id = None

        with self.canvas:
            Color(0.10, 0.12, 0.16, 1)
            self.base_circle = Ellipse()

            Color(0.32, 0.38, 0.50, 1)
            self.base_line = Line(
                circle=(0, 0, 0),
                width=1.2,
            )

            Color(0.18, 0.22, 0.30, 1)
            self.cross_x = Line(points=[], width=1)
            self.cross_y = Line(points=[], width=1)

            Color(0.22, 0.60, 1.00, 0.10)
            self.halo = Ellipse()

            Color(0.22, 0.60, 1.00, 1)
            self.knob_circle = Ellipse()

            Color(1, 1, 1, 0.18)
            self.inner_glow = Ellipse()

            Color(1, 1, 1, 0.08)
            self.glow = Ellipse()

        self.bind(
            pos=self._update_graphics,
            size=self._update_graphics,
        )

        self.bind(
            value_x=self._sync_from_values,
            value_y=self._sync_from_values,
        )

    def _update_graphics(self, *args):
        diameter = min(self.width, self.height)

        self.base_radius = diameter / 2 * 0.93

        self.center_x_pos = self.x + self.width / 2
        self.center_y_pos = self.y + self.height / 2

        self.base_circle.pos = (
            self.center_x_pos - self.base_radius,
            self.center_y_pos - self.base_radius,
        )

        self.base_circle.size = (
            self.base_radius * 2,
            self.base_radius * 2,
        )

        self.base_line.circle = (
            self.center_x_pos,
            self.center_y_pos,
            self.base_radius,
        )

        self.cross_x.points = [
            self.center_x_pos - self.base_radius * 0.62,
            self.center_y_pos,
            self.center_x_pos + self.base_radius * 0.62,
            self.center_y_pos,
        ]

        self.cross_y.points = [
            self.center_x_pos,
            self.center_y_pos - self.base_radius * 0.62,
            self.center_x_pos,
            self.center_y_pos + self.base_radius * 0.62,
        ]

        self._sync_from_values()

    def _value_to_offset(self, value):
        return clamp(
            (value - 128) / 127.0,
            -1.0,
            1.0,
        )

    def _offset_to_value(self, offset):
        return int(
            round(
                128
                + clamp(offset, -1.0, 1.0) * 127
            )
        )

    def _sync_from_values(self, *args):
        if self.base_radius <= 0:
            return

        nx = self._value_to_offset(self.value_x)
        ny = self._value_to_offset(self.value_y)

        self.knob_x = (
            self.center_x_pos
            + nx * self.base_radius
        )

        self.knob_y = (
            self.center_y_pos
            - ny * self.base_radius
        )

        knob_radius = (
            self.base_radius
            * self.knob_radius_ratio
        )

        self.knob_circle.pos = (
            self.knob_x - knob_radius,
            self.knob_y - knob_radius,
        )

        self.knob_circle.size = (
            knob_radius * 2,
            knob_radius * 2,
        )

        inner_size = knob_radius * 1.5

        self.inner_glow.pos = (
            self.knob_x - inner_size / 2,
            self.knob_y - inner_size / 2,
        )

        self.inner_glow.size = (
            inner_size,
            inner_size,
        )

        halo_size = knob_radius * 2.2

        self.halo.pos = (
            self.knob_x - halo_size / 2,
            self.knob_y - halo_size / 2,
        )

        self.halo.size = (
            halo_size,
            halo_size,
        )

        glow_size = self.base_radius * 1.55

        self.glow.pos = (
            self.center_x_pos - glow_size / 2,
            self.center_y_pos - glow_size / 2,
        )

        self.glow.size = (
            glow_size,
            glow_size,
        )

    def _set_knob(self, x, y):
        dx = x - self.center_x_pos
        dy = y - self.center_y_pos

        dist = sqrt(dx * dx + dy * dy)

        if dist > self.base_radius and dist > 0:
            angle = atan2(dy, dx)

            dx = cos(angle) * self.base_radius
            dy = sin(angle) * self.base_radius

        self.knob_x = self.center_x_pos + dx
        self.knob_y = self.center_y_pos + dy

        self.value_x = self._offset_to_value(
            dx / self.base_radius
            if self.base_radius
            else 0
        )

        self.value_y = self._offset_to_value(
            -(dy / self.base_radius
              if self.base_radius
              else 0)
        )

        self._sync_from_values()

    def set_external_values(self, value_x=None, value_y=None):
        if self._touch_id is not None:
            return

        if value_x is not None:
            self.value_x = int(
                clamp(value_x, 0, 255)
            )

        if value_y is not None:
            self.value_y = int(
                clamp(value_y, 0, 255)
            )

        self._sync_from_values()

    def reset_to_center(self):
        self._touch_id = None

        self.value_x = 128
        self.value_y = 128

        self._sync_from_values()

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False

        if self._touch_id is not None:
            return False

        self._touch_id = touch.uid

        self._set_knob(
            touch.x,
            touch.y,
        )

        return True

    def on_touch_move(self, touch):
        if self._touch_id != touch.uid:
            return False

        self._set_knob(
            touch.x,
            touch.y,
        )

        return True

    def on_touch_up(self, touch):
        if self._touch_id != touch.uid:
            return False

        self.reset_to_center()

        return True


class AppState:
    def __init__(self):
        self.device_uuid = load_or_create_uuid()
        self.device_name = load_name()

        self.sock = None
        self.connected = False
        self.authenticating = False

        self._send_lock = threading.Lock()
        self._rx_stop = threading.Event()
        self._rx_thread = None
        self._connection_generation = 0

        self.buttons = {
            "A": 0,
            "B": 0,
            "X": 0,
            "Y": 0,
            "LB": 0,
            "RB": 0,
            "BACK": 0,
            "START": 0,
            "GUIDE": 0,
            "L3": 0,
            "R3": 0,
            "DPAD_UP": 0,
            "DPAD_DOWN": 0,
            "DPAD_LEFT": 0,
            "DPAD_RIGHT": 0,
        }

        self.analog = {
            "L2": 0,
            "R2": 0,
        }

        self.joystick = {
            "left_x": 128,
            "left_y": 128,
            "right_x": 128,
            "right_y": 128,
        }

        self.mode = "standard"

        self.gyro_enabled = False
        self._gyro_supported = accelerometer is not None

        self._gyro_neutral = None
        self._gyro_steer = 0.0
        self._gyro_raw = 0.0
        self._gyro_last_sample = None

        self.sensitivity = 1.5

        self.connect_screen = None
        self.control_screen = None
        self.settings_screen = None

        self._periodic_send_ev = Clock.schedule_interval(
            self.periodic_send,
            0.10,
        )

        self._gyro_poll_ev = Clock.schedule_interval(
            self._poll_gyro,
            0.05,
        )

    # -------------------- Networking --------------------

    def request_connect(self, ip, port_text, name):
        if self.connected:
            self.disconnect()
            return

        if self.authenticating:
            self._ui_status("Already connecting...")
            return

        if not ip or not port_text:
            self._ui_status("IP and port are required")
            return

        try:
            port = int(port_text)
        except (TypeError, ValueError):
            self._ui_status("Invalid port")
            return

        save_last_ip(ip)
        save_name(name)

        self.device_name = name
        self.authenticating = True
        self._connection_generation += 1
        generation = self._connection_generation

        Clock.schedule_once(
            lambda dt: self._ui_authenticating(),
            0,
        )

        threading.Thread(
            target=self._connect_thread,
            args=(ip, port, generation),
            daemon=True,
        ).start()

    def _connect_thread(self, ip, port, generation):
        try:
            s = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM,
            )

            s.settimeout(5.0)

            s.connect(
                (ip, port)
            )

            if generation != self._connection_generation:
                s.close()
                return

            s.settimeout(1.0)

            self.sock = s
            self.connected = True
            self.authenticating = False

            self._rx_stop.clear()

            Clock.schedule_once(
                lambda dt: self._on_connected_ui(True),
                0,
            )

            self._rx_thread = threading.Thread(
                target=self._rx_loop,
                args=(generation,),
                daemon=True,
            )

            self._rx_thread.start()

            self.send_state()

        except Exception:
            try:
                if self.sock:
                    self.sock.close()
            except Exception:
                pass

            self.sock = None
            self.connected = False
            self.authenticating = False

            Clock.schedule_once(
                lambda dt: self._on_connected_ui(
                    False,
                    "Connection failed",
                ),
                0,
            )

    def _on_connected_ui(self, connected, message=None):
        self.connected = connected

        if self.connect_screen:
            self.connect_screen.update_ui(
                "connected" if connected else "disconnected",
                message,
            )

        if self.control_screen:
            self.control_screen.refresh_top_bar()

        if not connected:
            self._stop_gyro_for_disconnect()

    def _ui_authenticating(self):
        if self.connect_screen:
            self.connect_screen.update_ui(
                "authenticating"
            )

    def _ui_status(self, text):
        Clock.schedule_once(
            lambda dt, t=text:
                self.connect_screen.show_status(t)
                if self.connect_screen
                else None,
            0,
        )

    def _stop_gyro_for_disconnect(self):
        self.gyro_enabled = False
        self._gyro_steer = 0.0

        if self._gyro_supported:
            try:
                accelerometer.disable()
            except Exception:
                pass

        Clock.schedule_once(
            lambda dt: self._refresh_gyro_ui(),
            0,
        )

    def _rx_loop(self, generation):
        try:
            while (
                not self._rx_stop.is_set()
                and self.sock
            ):
                try:
                    data = self.sock.recv(2048)

                    if not data:
                        break

                except socket.timeout:
                    continue

                except Exception:
                    break

        finally:
            Clock.schedule_once(
                lambda dt, g=generation: self._disconnect_if_current(g),
                0,
            )

    def _disconnect_if_current(self, generation):
        if generation == self._connection_generation:
            self.disconnect()

    def on_submit_code(self, code):
        code = (code or "").strip()

        if not code:
            self._ui_pair_status(
                "Enter a code first"
            )
            return False

        payload = self.build_state_message()
        payload["auth_code"] = code

        self._send(payload)

        self._ui_pair_status("Sent")

        Clock.schedule_once(
            lambda dt: self._clear_pair_status(),
            2.0,
        )

        return True

    def _ui_pair_status(self, text):
        Clock.schedule_once(
            lambda dt, t=text:
                self.connect_screen.show_pair_status(t)
                if self.connect_screen
                else None,
            0,
        )

    def _clear_pair_status(self):
        if self.connect_screen:
            self.connect_screen.clear_pair_status()

    def disconnect(self):
        self._connection_generation += 1
        self._rx_stop.set()

        self.connected = False
        self.authenticating = False

        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass

        self.sock = None

        self._on_connected_ui(
            False,
            "Disconnected",
        )

    def _send(self, obj):
        if not self.connected or not self.sock:
            return

        try:
            data = (
                json.dumps(obj)
                + "\n"
            ).encode("utf-8")

            with self._send_lock:
                self.sock.sendall(data)

        except Exception:
            self.disconnect()

    # -------------------- State --------------------

    def build_state_message(self):
        return {
            "uuid": self.device_uuid,
            "name": self.device_name or "UnknownDevice",
            "mode": self.mode,
            "gyro_enabled": self.gyro_enabled,
            "buttons": self.buttons,
            "analog": self.analog,
            "joystick": self.joystick,
            "tilt": {
                "neutral_x": self._gyro_neutral,
                "steer": round(
                    self._gyro_steer,
                    4,
                ),
            },
        }

    def send_state(self):
        self._send(
            self.build_state_message()
        )

    def periodic_send(self, dt):
        if self.connected:
            self.send_state()

            if self.control_screen:
                self.control_screen.refresh_top_bar()

    # -------------------- Controls --------------------

    def momentary_button(self, key, value):
        key_aliases = {
            "a": "A",
            "b": "B",
            "x": "X",
            "y": "Y",
            "lb": "LB",
            "rb": "RB",
            "back": "BACK",
            "start": "START",
            "guide": "GUIDE",
            "l3": "L3",
            "r3": "R3",
            "dpad_up": "DPAD_UP",
            "dpad_down": "DPAD_DOWN",
            "dpad_left": "DPAD_LEFT",
            "dpad_right": "DPAD_RIGHT",
        }

        canonical_key = key_aliases.get(
            str(key).lower(),
            key,
        )

        if canonical_key not in self.buttons:
            return

        self.buttons[canonical_key] = (
            1 if value else 0
        )

        self.send_state()

    def set_trigger(self, which, value):
        trigger_aliases = {
            "left": "L2",
            "right": "R2",
            "l2": "L2",
            "r2": "R2",
        }

        canonical_key = trigger_aliases.get(
            str(which).lower(),
            which,
        )

        if canonical_key not in self.analog:
            return

        self.analog[canonical_key] = int(
            round(
                clamp(
                    float(value),
                    0.0,
                    1.0,
                ) * 255
            )
        )

        self.send_state()

    def set_left_stick(self, value_x, value_y):
        self.joystick["left_x"] = int(value_x)
        self.joystick["left_y"] = int(value_y)

        self.send_state()

    def set_right_stick(self, value_x, value_y):
        self.joystick["right_x"] = int(value_x)
        self.joystick["right_y"] = int(value_y)

        self.send_state()

    def set_mode(self, mode):
        if mode not in (
            "standard",
            "driving",
        ):
            return

        self.mode = mode

        self.send_state()

        Clock.schedule_once(
            lambda dt: self._refresh_mode_ui(),
            0,
        )

    def toggle_gyro(self):
        if not self._gyro_supported:
            return False

        self.gyro_enabled = not self.gyro_enabled

        try:
            if self.gyro_enabled:
                accelerometer.enable()

                if (
                    self._gyro_neutral is None
                    and self._gyro_last_sample is not None
                ):
                    self.calibrate_gyro()

            else:
                accelerometer.disable()

                self._gyro_steer = 0.0
                self._gyro_raw = 0.0

        except Exception:
            if self.gyro_enabled:
                self.gyro_enabled = False

        self.send_state()

        Clock.schedule_once(
            lambda dt: self._refresh_gyro_ui(),
            0,
        )

        return self.gyro_enabled

    def calibrate_gyro(self):
        if not self._gyro_supported:
            return False

        if self._gyro_last_sample is None:
            return False

        self._gyro_neutral = self._gyro_last_sample[0]
        self._gyro_steer = 0.0

        self.send_state()

        Clock.schedule_once(
            lambda dt: self._refresh_gyro_ui(),
            0,
        )

        return True

    def set_sensitivity(self, value):
        self.sensitivity = float(value)

    def set_device_name(self, name):
        name = (
            (name or "").strip()
            or "KivyGamepad"
        )

        self.device_name = name

        save_name(name)

        self.send_state()

    # -------------------- Gyro --------------------

    def _poll_gyro(self, dt):
        if (
            not self._gyro_supported
            or not self.gyro_enabled
            or self.mode != "driving"
        ):
            return

        try:
            sample = accelerometer.acceleration
        except Exception:
            sample = None

        if not sample or len(sample) < 3:
            return

        x, y, z = sample

        if x is None or y is None or z is None:
            return

        self._gyro_last_sample = (
            float(x),
            float(y),
            float(z),
        )

        if self._gyro_neutral is None:
            self._gyro_neutral = float(x)

        raw_delta = (
            float(x)
            - float(self._gyro_neutral)
        )

        sensitivity = float(
            self.sensitivity
        )

        steer = clamp(
            raw_delta / (2.2 / sensitivity),
            -1.0,
            1.0,
        )

        self._gyro_raw = steer

        self._gyro_steer = (
            self._gyro_steer * 0.78
            + steer * 0.22
        )

        steering_value = int(
            round(
                128
                + self._gyro_steer * 127
            )
        )

        self.joystick["left_x"] = steering_value

        if self.control_screen:
            self.control_screen.apply_gyro_steer(
                steering_value,
                self._gyro_steer,
            )

        self.send_state()

        Clock.schedule_once(
            lambda dt: self._refresh_gyro_ui(),
            0,
        )

    # -------------------- UI refresh --------------------

    def _refresh_mode_ui(self):
        if self.control_screen:
            self.control_screen.refresh_top_bar()

        if self.settings_screen:
            self.settings_screen.refresh_mode_buttons()

        if self.connect_screen:
            self.connect_screen.update_ui()

    def _refresh_gyro_ui(self):
        if self.settings_screen:
            self.settings_screen.refresh_gyro()

    def on_stop(self):
        self._rx_stop.set()

        try:
            if self._periodic_send_ev is not None:
                self._periodic_send_ev.cancel()
        except Exception:
            pass

        try:
            if self._gyro_poll_ev is not None:
                self._gyro_poll_ev.cancel()
        except Exception:
            pass

        try:
            if self._gyro_supported:
                accelerometer.disable()
        except Exception:
            pass

        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass

        self.sock = None
        self.connected = False
        self.authenticating = False


class TabBar(BoxLayout):
    def __init__(self, app_ref=None, **kwargs):
        kwargs.setdefault(
            "size_hint_y",
            None,
        )
        kwargs.setdefault(
            "height",
            dp(56),
        )

        super().__init__(**kwargs)

        self.app_ref = app_ref
        self.tabs = {}

        with self.canvas.before:
            Color(*THEME["surface"])

            self._bg = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[0],
            )

            Color(*THEME["border"])

            self._topline = Line(
                points=[],
                width=1,
            )

        self.bind(
            pos=self._redraw,
            size=self._redraw,
        )

        for name, icon, label in (
            (
                "control",
                "\U0001F3AE",
                "Controller",
            ),
            (
                "connect",
                "\U0001F4E1",
                "Connect",
            ),
            (
                "settings",
                "\u2699\ufe0f",
                "Settings",
            ),
        ):
            tab = self._make_tab(
                name,
                icon,
                label,
            )

            self.tabs[name] = tab
            self.add_widget(tab)

    def _make_tab(self, name, icon, label):
        tab = Button(
            text=icon + "\n" + label,
            markup=True,
            background_normal="",
            background_down="",
            background_color=THEME["surface"],
            color=THEME["muted"],
            font_size=sp(13),
            size_hint_x=1,
        )

        tab._name = name
        tab._underline_color = THEME["border"]
        tab._underline_width = 1.0

        with tab.canvas.after:
            Color(*tab._underline_color)

            tab._underline = Line(
                points=[],
                width=tab._underline_width,
            )

        # FIX:
        # _draw_underline is a TabBar method, not a Button method.
        tab.bind(
            pos=self._draw_underline,
            size=self._draw_underline,
        )

        tab.bind(
            on_press=lambda inst, n=name:
                self._on_tab(n)
        )

        return tab

    def _draw_underline(self, widget, *args):
        widget.canvas.after.clear()

        with widget.canvas.after:
            Color(*widget._underline_color)

            widget._underline = Line(
                points=[
                    widget.x,
                    widget.y + dp(1),
                    widget.x + widget.width,
                    widget.y + dp(1),
                ],
                width=widget._underline_width,
            )

    def _on_tab(self, name):
        if self.app_ref:
            self.app_ref.switch_screen(name)

    def set_active(self, name):
        for key, tab in self.tabs.items():
            if key == name:
                tab.color = THEME["accent"]
                tab._underline_color = THEME["accent"]
                tab._underline_width = 3.0
            else:
                tab.color = THEME["muted"]
                tab._underline_color = THEME["border"]
                tab._underline_width = 1.0

            # FIX:
            # _draw_underline belongs to TabBar.
            self._draw_underline(tab)

    def _redraw(self, *args):
        self._bg.pos = self.pos
        self._bg.size = self.size

        self._topline.points = [
            self.x,
            self.y + self.height,
            self.x + self.width,
            self.y + self.height,
        ]


# ============================================================
# Screens
# ============================================================


class ControlScreen(Screen):
    """Live gamepad controller screen: D-Pad, sticks, triggers, ABXY, steering meter."""

    def __init__(self, state, **kwargs):
        self.state = state

        super().__init__(**kwargs)

        root = BoxLayout(
            orientation="vertical",
            spacing=dp(6),
            padding=(
                dp(8),
                dp(6),
                dp(8),
                dp(6),
            ),
        )

        # ---- Top bar ----

        top_bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(48),
            spacing=dp(8),
        )

        self.mode_pill = Pill(
            text="Standard"
        )

        self.mode_pill.set_color(
            THEME["accent"]
        )

        left_wrap = BoxLayout(
            orientation="horizontal",
            size_hint_x=0.32,
        )

        left_wrap.add_widget(Widget())
        left_wrap.add_widget(self.mode_pill)
        left_wrap.add_widget(Widget())

        top_bar.add_widget(left_wrap)

        center_wrap = BoxLayout(
            orientation="horizontal",
            size_hint_x=0.36,
            spacing=dp(6),
        )

        center_wrap.add_widget(Widget())

        self.conn_dot = Label(
            text="\u25CF",
            color=THEME["danger"],
            bold=True,
            font_size=sp(14),
            size_hint_x=None,
            width=dp(18),
        )

        center_wrap.add_widget(
            self.conn_dot
        )

        self.conn_text = fit_label(
            Label(
                text="Disconnected",
                color=THEME["muted"],
                halign="left",
                valign="middle",
                font_size=sp(13),
            )
        )

        center_wrap.add_widget(
            self.conn_text
        )

        center_wrap.add_widget(Widget())

        top_bar.add_widget(center_wrap)

        right_wrap = BoxLayout(
            orientation="horizontal",
            size_hint_x=0.32,
        )

        self.gyro_icon = fit_label(
            Label(
                text="\U0001F9ED OFF",
                color=THEME["muted"],
                halign="right",
                valign="middle",
                font_size=sp(13),
            )
        )

        right_wrap.add_widget(Widget())
        right_wrap.add_widget(self.gyro_icon)

        top_bar.add_widget(right_wrap)

        root.add_widget(top_bar)

        # ---- Main area ----

        main = BoxLayout(
            orientation="horizontal",
            spacing=dp(8),
        )

        # ----- LEFT column -----

        left = BoxLayout(
            orientation="vertical",
            spacing=dp(6),
            size_hint_x=0.32,
        )

        dpad_grid = GridLayout(
            cols=3,
            rows=3,
            spacing=dp(4),
            size_hint_y=0.34,
        )

        def dpad_btn(arrow, key):
            btn = make_button(
                arrow,
                accent=THEME["btn_hover"],
                font_size=sp(16),
                height=dp(1),
            )

            btn.size_hint_y = 1

            btn.bind(
                on_press=lambda inst, k=key:
                    self.state.momentary_button(
                        k,
                        True,
                    ),
                on_release=lambda inst, k=key:
                    self.state.momentary_button(
                        k,
                        False,
                    ),
            )

            return btn

        dpad_grid.add_widget(Widget())
        dpad_grid.add_widget(
            dpad_btn("\u25b2", "DPAD_UP")
        )
        dpad_grid.add_widget(Widget())

        dpad_grid.add_widget(
            dpad_btn("\u25c0", "DPAD_LEFT")
        )
        dpad_grid.add_widget(Widget())

        dpad_grid.add_widget(
            dpad_btn("\u25b6", "DPAD_RIGHT")
        )
        dpad_grid.add_widget(Widget())

        dpad_grid.add_widget(
            dpad_btn("\u25bc", "DPAD_DOWN")
        )
        dpad_grid.add_widget(Widget())

        left.add_widget(dpad_grid)

        self.left_stick = Joystick(
            size_hint_y=0.48
        )

        self.left_stick.bind(
            value_x=lambda inst, val:
                self.state.set_left_stick(
                    inst.value_x,
                    inst.value_y,
                ),
            value_y=lambda inst, val:
                self.state.set_left_stick(
                    inst.value_x,
                    inst.value_y,
                ),
        )

        left.add_widget(self.left_stick)

        l3 = make_button(
            "L3",
            accent=THEME["btn_hover"],
            height=dp(40),
        )

        l3.bind(
            on_press=lambda *_:
                self.state.momentary_button(
                    "L3",
                    True,
                ),
            on_release=lambda *_:
                self.state.momentary_button(
                    "L3",
                    False,
                ),
        )

        left.add_widget(l3)

        main.add_widget(left)

        # ----- CENTER column -----

        center = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            size_hint_x=0.36,
        )

        shoulder_row = BoxLayout(
            orientation="horizontal",
            spacing=dp(6),
            size_hint_y=None,
            height=dp(120),
        )

        lb = make_button(
            "LB",
            accent=THEME["btn_hover"],
            height=dp(1),
        )

        lb.size_hint_y = 1

        lb.bind(
            on_press=lambda *_:
                self.state.momentary_button(
                    "LB",
                    True,
                ),
            on_release=lambda *_:
                self.state.momentary_button(
                    "LB",
                    False,
                ),
        )

        shoulder_row.add_widget(lb)

        def trigger_slider(which):
            s = Slider(
                min=0,
                max=1,
                value=0,
                orientation="vertical",
                step=0.01,
            )

            s.bind(
                value=lambda inst, val:
                    self.state.set_trigger(
                        which,
                        val,
                    )
            )

            s.bind(
                on_touch_up=lambda inst, touch: (
                    setattr(inst, "value", 0)
                    if inst.collide_point(
                        *touch.pos
                    )
                    else None
                )
            )

            return s

        lt_box = BoxLayout(
            orientation="vertical",
            spacing=dp(2),
        )

        lt_label = fit_label(
            Label(
                text="LT",
                color=THEME["muted"],
                size_hint_y=None,
                height=dp(16),
                halign="center",
                valign="middle",
                font_size=sp(12),
            )
        )

        lt_box.add_widget(lt_label)
        lt_box.add_widget(
            trigger_slider("L2")
        )

        shoulder_row.add_widget(lt_box)

        rt_box = BoxLayout(
            orientation="vertical",
            spacing=dp(2),
        )

        rt_label = fit_label(
            Label(
                text="RT",
                color=THEME["muted"],
                size_hint_y=None,
                height=dp(16),
                halign="center",
                valign="middle",
                font_size=sp(12),
            )
        )

        rt_box.add_widget(rt_label)
        rt_box.add_widget(
            trigger_slider("R2")
        )

        shoulder_row.add_widget(rt_box)

        rb = make_button(
            "RB",
            accent=THEME["btn_hover"],
            height=dp(1),
        )

        rb.size_hint_y = 1

        rb.bind(
            on_press=lambda *_:
                self.state.momentary_button(
                    "RB",
                    True,
                ),
            on_release=lambda *_:
                self.state.momentary_button(
                    "RB",
                    False,
                ),
        )

        shoulder_row.add_widget(rb)

        center.add_widget(shoulder_row)

        sys_row = BoxLayout(
            orientation="horizontal",
            spacing=dp(6),
            size_hint_y=None,
            height=dp(42),
        )

        for label, key, accent in (
            (
                "BACK",
                "BACK",
                THEME["btn_hover"],
            ),
            (
                "GUIDE",
                "GUIDE",
                THEME["warn"],
            ),
            (
                "START",
                "START",
                THEME["btn_hover"],
            ),
        ):
            b = make_button(
                label,
                accent=accent,
                font_size=sp(12),
                height=dp(1),
            )

            b.size_hint_y = 1

            b.bind(
                on_press=lambda inst, k=key:
                    self.state.momentary_button(
                        k,
                        True,
                    ),
                on_release=lambda inst, k=key:
                    self.state.momentary_button(
                        k,
                        False,
                    ),
            )

            sys_row.add_widget(b)

        center.add_widget(sys_row)

        steer_box = BoxLayout(
            orientation="vertical",
            spacing=dp(2),
            size_hint_y=None,
            height=dp(44),
        )

        steer_label = fit_label(
            Label(
                text="Steering",
                color=THEME["muted"],
                size_hint_y=None,
                height=dp(16),
                halign="center",
                valign="middle",
                font_size=sp(12),
            )
        )

        steer_box.add_widget(
            steer_label
        )

        self.steer_meter = Slider(
            min=-1,
            max=1,
            value=0,
            disabled=True,
            opacity=0.9,
        )

        steer_box.add_widget(
            self.steer_meter
        )

        center.add_widget(steer_box)

        center.add_widget(Widget())

        main.add_widget(center)

        # ----- RIGHT column -----

        right = BoxLayout(
            orientation="vertical",
            spacing=dp(6),
            size_hint_x=0.32,
        )

        abxy_grid = GridLayout(
            cols=3,
            rows=3,
            spacing=dp(4),
            size_hint_y=0.46,
        )

        abxy_grid.add_widget(Widget())

        def face_button(label, key, accent):
            btn = make_button(
                label,
                accent=accent,
                font_size=sp(16),
                height=dp(1),
            )

            btn.size_hint_y = 1

            btn.bind(
                on_press=lambda inst, k=key:
                    self.state.momentary_button(
                        k,
                        True,
                    ),
                on_release=lambda inst, k=key:
                    self.state.momentary_button(
                        k,
                        False,
                    ),
            )

            return btn

        self.btn_y = face_button(
            "Y",
            "Y",
            THEME["a_color"],
        )

        abxy_grid.add_widget(
            self.btn_y
        )

        abxy_grid.add_widget(Widget())

        abxy_grid.add_widget(
            face_button(
                "X",
                "X",
                THEME["x_color"],
            )
        )

        abxy_grid.add_widget(Widget())

        abxy_grid.add_widget(
            face_button(
                "B",
                "B",
                THEME["b_color"],
            )
        )

        abxy_grid.add_widget(Widget())

        abxy_grid.add_widget(
            face_button(
                "A",
                "A",
                THEME["g_color"],
            )
        )

        abxy_grid.add_widget(Widget())

        right.add_widget(abxy_grid)

        self.right_stick = Joystick(
            size_hint_y=0.38
        )

        self.right_stick.bind(
            value_x=lambda inst, val:
                self.state.set_right_stick(
                    inst.value_x,
                    inst.value_y,
                ),
            value_y=lambda inst, val:
                self.state.set_right_stick(
                    inst.value_x,
                    inst.value_y,
                ),
        )

        right.add_widget(self.right_stick)

        r3 = make_button(
            "R3",
            accent=THEME["btn_hover"],
            height=dp(40),
        )

        r3.bind(
            on_press=lambda *_:
                self.state.momentary_button(
                    "R3",
                    True,
                ),
            on_release=lambda *_:
                self.state.momentary_button(
                    "R3",
                    False,
                ),
        )

        right.add_widget(r3)

        main.add_widget(right)

        root.add_widget(main)

        self.add_widget(root)

        self.refresh_top_bar()

    def _pad_button(self, key, arrow):
        btn = make_button(
            arrow,
            accent=THEME["btn_hover"],
            font_size=sp(16),
            height=dp(1),
        )

        btn.size_hint_y = 1

        btn.bind(
            on_press=lambda inst, k=key:
                self.state.momentary_button(
                    k,
                    True,
                ),
            on_release=lambda inst, k=key:
                self.state.momentary_button(
                    k,
                    False,
                ),
        )

        return btn

    def refresh_top_bar(self):
        if self.state.mode == "driving":
            self.mode_pill.text = "Driving"
            self.mode_pill.set_color(
                THEME["accent2"]
            )
        else:
            self.mode_pill.text = "Standard"
            self.mode_pill.set_color(
                THEME["accent"]
            )

        if self.state.connected:
            self.conn_dot.color = THEME["success"]
            self.conn_text.text = "Connected"
            self.conn_text.color = THEME["success"]
        else:
            self.conn_dot.color = THEME["danger"]
            self.conn_text.text = "Disconnected"
            self.conn_text.color = THEME["muted"]

        if self.state.gyro_enabled:
            self.gyro_icon.text = (
                "\U0001F9ED ON"
            )
            self.gyro_icon.color = (
                THEME["success"]
            )
        else:
            self.gyro_icon.text = (
                "\U0001F9ED OFF"
            )
            self.gyro_icon.color = (
                THEME["muted"]
            )

    def apply_gyro_steer(
        self,
        steering_value,
        steer,
    ):
        if not hasattr(
            self,
            "steer_meter",
        ):
            return

        self.steer_meter.value = clamp(
            steer,
            -1,
            1,
        )

        self.left_stick.set_external_values(
            value_x=int(
                clamp(
                    steering_value,
                    0,
                    255,
                )
            )
        )


class ConnectScreen(Screen):
    """Connection, authentication and device identity screen."""

    def __init__(self, state, **kwargs):
        self.state = state

        super().__init__(**kwargs)

        scroll = ScrollView(
            bar_width=0,
            do_scroll_x=False,
            do_scroll_y=True,
        )

        content = BoxLayout(
            orientation="vertical",
            spacing=dp(10),
            size_hint_y=None,
            padding=(
                dp(10),
                dp(10),
                dp(10),
                dp(10),
            ),
        )

        content.bind(
            minimum_height=content.setter(
                "height"
            )
        )

        scroll.add_widget(content)

        # ---- Header card ----

        header = Card(
            size_hint_y=None,
            height=dp(96),
            spacing=dp(4),
            padding=(
                dp(16),
                dp(12),
                dp(16),
                dp(12),
            ),
        )

        title_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(32),
        )

        title = fit_label(
            Label(
                text="[b]InputBridge[/b]",
                markup=True,
                color=THEME["text"],
                halign="left",
                valign="middle",
                font_size=sp(26),
            )
        )

        self.badge = Pill(
            text="Disconnected"
        )

        self.badge.set_color(
            THEME["danger"]
        )

        title_row.add_widget(title)

        tr_spacer = BoxLayout()
        tr_spacer.add_widget(Widget())
        tr_spacer.add_widget(self.badge)

        title_row.add_widget(tr_spacer)

        subtitle = fit_label(
            Label(
                text="Gamepad Controller",
                color=THEME["muted"],
                halign="left",
                valign="middle",
                font_size=sp(14),
            )
        )

        header.add_widget(title_row)
        header.add_widget(subtitle)

        content.add_widget(header)

        # ---- Server card ----

        server_card = Card(
            size_hint_y=None,
            height=dp(214),
            spacing=dp(8),
        )

        server_card.add_widget(
            SectionTitle(text="Server")
        )

        name_row = BoxLayout(
            orientation="horizontal",
            spacing=dp(8),
            size_hint_y=None,
            height=dp(66),
        )

        self.name_input = make_text_input(
            load_name(),
            "Device name",
        )

        self.ip_input = make_text_input(
            load_last_ip(),
            "Server IP",
        )

        name_row.add_widget(
            field_box(
                "Device Name",
                self.name_input,
            )
        )

        name_row.add_widget(
            field_box(
                "Server IP",
                self.ip_input,
            )
        )

        server_card.add_widget(name_row)

        port_row = BoxLayout(
            orientation="horizontal",
            spacing=dp(8),
            size_hint_y=None,
            height=dp(66),
        )

        self.port_input = make_text_input(
            "5000",
            "Port",
            input_filter="int",
        )

        port_row.add_widget(
            field_box(
                "Port",
                self.port_input,
            )
        )

        port_row.add_widget(Widget())

        server_card.add_widget(port_row)

        self.connect_btn = make_button(
            "Connect",
            accent=THEME["accent"],
            height=dp(46),
        )

        self.connect_btn.bind(
            on_release=self._on_connect
        )

        server_card.add_widget(
            self.connect_btn
        )

        self.status_label = fit_label(
            Label(
                text="Ready",
                color=THEME["muted"],
                halign="left",
                valign="middle",
                font_size=sp(13),
                size_hint_y=None,
                height=dp(20),
            )
        )

        server_card.add_widget(
            self.status_label
        )

        content.add_widget(server_card)

        # ---- Authentication card ----

        auth_card = Card(
            size_hint_y=None,
            height=dp(118),
            spacing=dp(8),
        )

        auth_card.add_widget(
            SectionTitle(text="Authentication")
        )

        auth_row = BoxLayout(
            orientation="horizontal",
            spacing=dp(8),
            size_hint_y=None,
            height=dp(52),
        )

        self.code_input = make_text_input(
            "",
            "Auth code",
            input_filter="int",
        )

        submit_btn = make_button(
            "Submit Code",
            accent=THEME["warn"],
            height=dp(46),
        )

        submit_btn.bind(
            on_release=self._on_submit_code
        )

        auth_row.add_widget(
            field_box(
                "Code",
                self.code_input,
            )
        )

        auth_row.add_widget(
            field_box(
                "",
                submit_btn,
            )
        )

        auth_card.add_widget(auth_row)

        self.pair_status_label = fit_label(
            Label(
                text="",
                color=THEME["subtle"],
                halign="left",
                valign="middle",
                font_size=sp(13),
                size_hint_y=None,
                height=dp(18),
            )
        )

        auth_card.add_widget(
            self.pair_status_label
        )

        content.add_widget(auth_card)

        # ---- Connection info card ----

        info_card = Card(
            size_hint_y=None,
            height=dp(104),
            spacing=dp(6),
        )

        info_card.add_widget(
            SectionTitle(text="Connection Info")
        )

        try:
            mono = "RobotoMono-Regular"

            from kivy.core.text import LabelBase

            LabelBase.register(
                name=mono,
                fn_regular=mono + ".ttf",
            )

            uuid_font = mono

        except Exception:
            uuid_font = None

        uuid_kwargs = {
            "text": "UUID: " + self.state.device_uuid,
            "color": THEME["muted"],
            "font_size": sp(11),
            "halign": "left",
            "valign": "middle",
        }

        if uuid_font:
            uuid_kwargs["font_name"] = uuid_font

        self.uuid_label = fit_label(
            Label(**uuid_kwargs)
        )

        self.uuid_label.size_hint_y = None
        self.uuid_label.height = dp(20)

        info_card.add_widget(
            self.uuid_label
        )

        self.last_ip_label = fit_label(
            Label(
                text=(
                    "Last connected: "
                    + load_last_ip()
                ),
                color=THEME["muted"],
                halign="left",
                valign="middle",
                font_size=sp(12),
            )
        )

        self.last_ip_label.size_hint_y = None
        self.last_ip_label.height = dp(18)

        info_card.add_widget(
            self.last_ip_label
        )

        content.add_widget(info_card)

        content.add_widget(Widget())

        self.add_widget(scroll)

        self.update_ui()

    # ---------- actions ----------

    def _on_connect(self, *_):
        if self.state.connected:
            self.state.disconnect()
        else:
            self.state.request_connect(
                self.ip_input.text.strip(),
                self.port_input.text.strip(),
                self.name_input.text.strip()
                or load_name(),
            )

    def _on_submit_code(self, *_):
        self.state.on_submit_code(
            self.code_input.text
        )

    # ---------- public UI API ----------

    def show_status(self, text):
        self.status_label.text = str(text)

    def show_pair_status(self, text):
        self.pair_status_label.text = str(text)

    def clear_pair_status(self):
        self.pair_status_label.text = ""

    def update_ui(
        self,
        status=None,
        message=None,
    ):
        connected = self.state.connected

        if connected:
            self.badge.text = "Connected"

            self.badge.set_color(
                THEME["success"]
            )

            self.connect_btn.text = "Disconnect"

            self.connect_btn._accent_color = (
                THEME["danger"]
            )

            self.connect_btn.background_color = (
                THEME["danger"]
            )

            self.connect_btn._base_color = (
                THEME["danger"]
            )

            self.name_input.disabled = True
            self.ip_input.disabled = True
            self.port_input.disabled = True

        elif status == "authenticating":
            self.badge.text = "Connecting"

            self.badge.set_color(
                THEME["warn"]
            )

            self.connect_btn.text = "Connecting..."
            self.connect_btn.disabled = True

        else:
            self.badge.text = "Disconnected"

            self.badge.set_color(
                THEME["danger"]
            )

            self.connect_btn.text = "Connect"

            self.connect_btn._accent_color = (
                THEME["accent"]
            )

            self.connect_btn._base_color = (
                THEME["btn"]
            )

            self.connect_btn.background_color = (
                THEME["btn"]
            )

            self.connect_btn.disabled = False

            self.name_input.disabled = False
            self.ip_input.disabled = False
            self.port_input.disabled = False

        if message:
            self.show_status(message)


class SettingsScreen(Screen):
    """Control mode, gyro steering and device settings."""

    def __init__(self, state, **kwargs):
        self.state = state

        super().__init__(**kwargs)

        scroll = ScrollView(
            bar_width=0,
            do_scroll_x=False,
            do_scroll_y=True,
        )

        content = BoxLayout(
            orientation="vertical",
            spacing=dp(10),
            size_hint_y=None,
            padding=(
                dp(10),
                dp(10),
                dp(10),
                dp(10),
            ),
        )

        content.bind(
            minimum_height=content.setter(
                "height"
            )
        )

        scroll.add_widget(content)

        # ---- Control Mode ----

        mode_card = Card(
            size_hint_y=None,
            height=dp(94),
            spacing=dp(8),
        )

        mode_card.add_widget(
            SectionTitle(
                text="Control Mode"
            )
        )

        mode_row = BoxLayout(
            orientation="horizontal",
            spacing=dp(8),
            size_hint_y=None,
            height=dp(46),
        )

        self.standard_btn = make_button(
            "Standard Mode",
            accent=THEME["accent"],
        )

        self.standard_btn.bind(
            on_release=lambda *_:
                self.state.set_mode(
                    "standard"
                )
        )

        self.driving_btn = make_button(
            "Driving Mode",
            accent=THEME["accent2"],
        )

        self.driving_btn.bind(
            on_release=lambda *_:
                self.state.set_mode(
                    "driving"
                )
        )

        mode_row.add_widget(
            self.standard_btn
        )

        mode_row.add_widget(
            self.driving_btn
        )

        mode_card.add_widget(mode_row)

        content.add_widget(mode_card)

        # ---- Gyro Steering ----

        gyro_card = Card(
            size_hint_y=None,
            height=dp(232),
            spacing=dp(8),
        )

        gyro_card.add_widget(
            SectionTitle(
                text="Gyro Steering"
            )
        )

        gyro_row = BoxLayout(
            orientation="horizontal",
            spacing=dp(8),
            size_hint_y=None,
            height=dp(46),
        )

        self.gyro_btn = make_button(
            "Enable Gyro",
            accent=THEME["success"],
        )

        self.gyro_btn.bind(
            on_release=lambda *_:
                self.state.toggle_gyro()
        )

        self.calibrate_btn = make_button(
            "Calibrate Tilt",
            accent=THEME["warn"],
        )

        self.calibrate_btn.bind(
            on_release=lambda *_:
                self.state.calibrate_gyro()
        )

        gyro_row.add_widget(
            self.gyro_btn
        )

        gyro_row.add_widget(
            self.calibrate_btn
        )

        gyro_card.add_widget(gyro_row)

        self.gyro_state_label = fit_label(
            Label(
                text="Gyro: off",
                color=THEME["muted"],
                halign="left",
                valign="middle",
                font_size=sp(13),
                size_hint_y=None,
                height=dp(20),
            )
        )

        gyro_card.add_widget(
            self.gyro_state_label
        )

        self.sensitivity_label = fit_label(
            Label(
                text="Sensitivity: 1.50\u00d7",
                color=THEME["muted"],
                halign="left",
                valign="middle",
                font_size=sp(13),
                size_hint_y=None,
                height=dp(20),
            )
        )

        gyro_card.add_widget(
            self.sensitivity_label
        )

        self.sensitivity_slider = Slider(
            min=0.5,
            max=3.0,
            value=1.5,
            step=0.05,
        )

        self.sensitivity_slider.bind(
            value=self._on_sensitivity
        )

        gyro_card.add_widget(
            self.sensitivity_slider
        )

        steer_row = BoxLayout(
            orientation="horizontal",
            spacing=dp(8),
            size_hint_y=None,
            height=dp(34),
        )

        steer_text = fit_label(
            Label(
                text="Steering",
                color=THEME["muted"],
                size_hint_x=0.22,
                halign="left",
                valign="middle",
                font_size=sp(13),
            )
        )

        self.steer_meter = Slider(
            min=-1,
            max=1,
            value=0,
            disabled=True,
            opacity=0.9,
        )

        steer_row.add_widget(
            steer_text
        )

        steer_row.add_widget(
            self.steer_meter
        )

        gyro_card.add_widget(
            steer_row
        )

        content.add_widget(gyro_card)

        # ---- Device ----

        device_card = Card(
            size_hint_y=None,
            height=dp(138),
            spacing=dp(8),
        )

        device_card.add_widget(
            SectionTitle(text="Device")
        )

        name_row = BoxLayout(
            orientation="horizontal",
            spacing=dp(8),
            size_hint_y=None,
            height=dp(52),
        )

        self.name_input = make_text_input(
            load_name(),
            "Device name",
        )

        save_btn = make_button(
            "Save",
            accent=THEME["accent"],
            height=dp(46),
        )

        save_btn.bind(
            on_release=self._on_save_name
        )

        name_row.add_widget(
            field_box(
                "Name",
                self.name_input,
            )
        )

        name_row.add_widget(
            field_box(
                "",
                save_btn,
            )
        )

        device_card.add_widget(name_row)

        self.uuid_label = fit_label(
            Label(
                text=(
                    "UUID: "
                    + self.state.device_uuid
                ),
                color=THEME["muted"],
                font_size=sp(11),
                halign="left",
                valign="middle",
                size_hint_y=None,
                height=dp(18),
            )
        )

        device_card.add_widget(
            self.uuid_label
        )

        content.add_widget(device_card)

        content.add_widget(Widget())

        self.add_widget(scroll)

        self.refresh_mode_buttons()
        self.refresh_gyro()

    def _on_sensitivity(self, instance, value):
        self.sensitivity_label.text = (
            f"Sensitivity: {value:.2f}\u00d7"
        )

        self.state.set_sensitivity(value)

    def _on_save_name(self, *_):
        self.state.set_device_name(
            self.name_input.text
        )

        self.show_saved()

    def show_saved(self):
        self.uuid_label.text = (
            "UUID: "
            + self.state.device_uuid
        )

    def refresh_mode_buttons(self):
        if self.state.mode == "driving":
            self.driving_btn.background_color = (
                self.driving_btn._accent_color
            )

            self.standard_btn.background_color = (
                self.standard_btn._base_color
            )

        else:
            self.standard_btn.background_color = (
                self.standard_btn._accent_color
            )

            self.driving_btn.background_color = (
                self.driving_btn._base_color
            )

    def refresh_gyro(self):
        if not self.state._gyro_supported:
            self.gyro_btn.text = "Gyro Unavailable"
            self.gyro_btn.disabled = True

            self.gyro_btn.background_color = (
                THEME["btn"]
            )

            self.calibrate_btn.disabled = True

            self.gyro_state_label.text = (
                "Gyro unavailable (plyer not installed)"
            )

            self.gyro_state_label.color = (
                THEME["subtle"]
            )

            self.steer_meter.value = 0

            return

        self.gyro_btn.disabled = False
        self.calibrate_btn.disabled = False

        if self.state.gyro_enabled:
            self.gyro_btn.text = "Disable Gyro"

            self.gyro_btn.background_color = (
                self.gyro_btn._accent_color
            )

            self.gyro_state_label.text = (
                "Gyro: on"
            )

            self.gyro_state_label.color = (
                THEME["success"]
            )

        else:
            self.gyro_btn.text = "Enable Gyro"

            self.gyro_btn.background_color = (
                self.gyro_btn._base_color
            )

            self.gyro_state_label.text = (
                "Gyro: off"
            )

            self.gyro_state_label.color = (
                THEME["muted"]
            )

        self.steer_meter.value = clamp(
            self.state._gyro_steer,
            -1,
            1,
        )


class InputBridgeApp(App):
    title = "InputBridge"

    def build(self):
        self.state = AppState()

        self.sm = ScreenManager()

        self.state.control_screen = ControlScreen(
            self.state,
            name="control",
        )

        self.state.connect_screen = ConnectScreen(
            self.state,
            name="connect",
        )

        self.state.settings_screen = SettingsScreen(
            self.state,
            name="settings",
        )

        self.sm.add_widget(
            self.state.connect_screen
        )

        self.sm.add_widget(
            self.state.control_screen
        )

        self.sm.add_widget(
            self.state.settings_screen
        )

        # Clock events are already scheduled inside AppState.__init__
        # periodic_send @ 0.10
        # _poll_gyro @ 0.05
        # Do not double-schedule.

        tabbar = TabBar(
            app_ref=self
        )

        root = BoxLayout(
            orientation="vertical"
        )

        root.add_widget(self.sm)
        root.add_widget(tabbar)

        self.tabbar = tabbar

        self.sm.current = "connect"

        tabbar.set_active("connect")

        return root

    def switch_screen(self, name):
        self.sm.current = name

        if self.tabbar:
            self.tabbar.set_active(name)

        screen = self.sm.get_screen(name)

        refresh = getattr(
            screen,
            "refresh_top_bar",
            None,
        )

        if refresh:
            refresh()

        refresh_mode = getattr(
            screen,
            "refresh_mode_buttons",
            None,
        )

        if refresh_mode:
            refresh_mode()

        refresh_gyro = getattr(
            screen,
            "refresh_gyro",
            None,
        )

        if refresh_gyro:
            refresh_gyro()

        update_ui = getattr(
            screen,
            "update_ui",
            None,
        )

        if update_ui:
            update_ui()

    def on_stop(self):
        if hasattr(self, "state"):
            self.state.on_stop()


if __name__ == "__main__":
    InputBridgeApp().run()
