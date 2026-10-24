"""InputBridge entry point: desktop controller app on PC, Kivy client on Android."""
import os
import sys


def _is_android_runtime() -> bool:
    # python-for-android sets ANDROID_ARGUMENT/ANDROID_PRIVATE; the explicit
    # platform check also supports runtimes which expose it directly.
    return (
        sys.platform == "android"
        or bool(os.environ.get("ANDROID_ARGUMENT"))
        or bool(os.environ.get("ANDROID_PRIVATE"))
    )


def main():
    if _is_android_runtime():
        from phone_client_with_auth import InputBridgeApp

        InputBridgeApp().run()
        return

    from PySide6.QtWidgets import QApplication
    from ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("InputBridge-Gamepad2XInput")
    window = MainWindow(app)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
