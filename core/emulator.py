import vgamepad as vg
import time
import threading
from core.utils.controller_monitor import controllerMonitor
from core.utils.hotkeys import Hotkey
from core.utils.hotkey_commander import HotkeyCommander


media_functions = {
                    "volume up": "volume up",
                    "volume down": "volume down",
                    "play/pause media": "play/pause media",
                    "next track": "next track",
                    "previous track": "previous track",
                    "volume mute": "volume mute",
                  }
custom_commands = {}

class ListOfAllControllers:
    controllers_path = []
    controllers_name = []
    lock = threading.RLock()

class EmulateX360:
    def __init__(self, device_path, controller_name, hotkey):
        self.device_path = device_path
        self.controller_name = controller_name
        self.hotkey = hotkey
        self.hotkey_commander = HotkeyCommander(media_functions, custom_commands)
        with ListOfAllControllers.lock:
            ListOfAllControllers.controllers_path.append(device_path)
            ListOfAllControllers.controllers_name.append(controller_name)
        self.is_monitoring = False
        self.could_instantiate = False

        # debounce state for hotkeys
        self._last_hotkey_func = None
        self._last_hotkey_time = 0.0
        self._hotkey_interval = 0.1  # 200 ms

        while self.could_instantiate is False:
            self.instantiate_vg()
            time.sleep(0.2)

    def instantiate_vg(self):
        try:
            self.v_x360 = vg.VX360Gamepad()
            self.could_instantiate = True
        except AssertionError as A:
            print(A)

    def _maybe_do_hotkey(self, ok, func):
        """
        Debounce / repeat logic:
        - Execute immediately on first detection of a hotkey.
        - If held (same func), re-execute every _hotkey_interval seconds.
        """
        if not ok or func is None:
            # reset if no valid hotkey
            self._last_hotkey_func = None
            return

        now = time.time()

        # new hotkey -> execute immediately and reset timer
        if func != self._last_hotkey_func:
            self._last_hotkey_func = func
            self._last_hotkey_time = now
            if func in media_functions.keys():
                self.hotkey_commander.do(func, False)
            return

        # same hotkey as last time -> check debounce timer
        if now - self._last_hotkey_time >= self._hotkey_interval:
            self._last_hotkey_time = now
            if func in media_functions.keys():
                self.hotkey_commander.do(func, False)

    def update(self, ljx, ljy, rjx, rjy, a=False, x=False, b=False, y=False,
               rb=False, rt=0, lb=False, lt=0, dpu=False, dpd=False, dpr=False, dpl=False,
               back=False, start=False, l3=False, r3=False):
        
        if self.is_monitoring:
            data = controllerMonitor.monitor(
                a, b, y, x,
                start, back,
                r3, l3,
                dpu, dpd, dpr, dpl,
                rb, lb,
                rt, lt,
                ljx, ljy,
                rjx, rjy
            )
            self._last_monitor = data
            return data
        
        binary, rt, lt, jlx, jly, jrx, jry = controllerMonitor.monitor(
            a, b, y, x,
            start, back,
            r3, l3,
            dpu, dpd, dpr, dpl,
            rb, lb,
            rt, lt,
            ljx, ljy,
            rjx, rjy
        )

        ok, func, msg = self.hotkey.get_hotkey(binary)

        # debounced hotkey execution
        self._maybe_do_hotkey(ok, func)

        # Joysticks
        self.v_x360.left_joystick(x_value=int(ljx), y_value=int(ljy))
        self.v_x360.right_joystick(x_value=int(rjx), y_value=int(rjy))

        # Triggers
        self.v_x360.left_trigger(value=int(lt))
        self.v_x360.right_trigger(value=int(rt))

        # Face Buttons
        self._press_release(a, vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
        self._press_release(b, vg.XUSB_BUTTON.XUSB_GAMEPAD_B)
        self._press_release(x, vg.XUSB_BUTTON.XUSB_GAMEPAD_X)
        self._press_release(y, vg.XUSB_BUTTON.XUSB_GAMEPAD_Y)
        
        # Shoulders
        self._press_release(lb, vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER)
        self._press_release(rb, vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER)

        # Menu / Stick Clicks
        self._press_release(back, vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK)
        self._press_release(start, vg.XUSB_BUTTON.XUSB_GAMEPAD_START)
        self._press_release(l3, vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB)
        self._press_release(r3, vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB)

        # DPad simulation
        self._set_dpad(dpu, dpd, dpl, dpr)

        self.v_x360.update()

    def _press_release(self, pressed, button):
        if pressed:
            self.v_x360.press_button(button=button)
        else:
            self.v_x360.release_button(button=button)

    def _set_dpad(self, up, down, left, right):
        # Reset all D-pad buttons first
        self.v_x360.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
        self.v_x360.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
        self.v_x360.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)
        self.v_x360.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)

        # Press based on state (allowing diagonals)
        if up:
            self.v_x360.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
        if down:
            self.v_x360.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
        if left:
            self.v_x360.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)
        if right:
            self.v_x360.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)

    def shutdown(self):
        try:
            self.v_x360.reset()
            self.v_x360.update()
        except Exception as e:
            print(f"[EmulateX360] Error on shutdown: {e}")

        # Remove from tracking lists
        try:
            with ListOfAllControllers.lock:
                idx = ListOfAllControllers.controllers_path.index(self.device_path)
                ListOfAllControllers.controllers_path.pop(idx)
                ListOfAllControllers.controllers_name.pop(idx)
        except ValueError:
            pass
        
class EmulateKeyboard:
    pass
