import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabBar,
    QStackedWidget,
    QSystemTrayIcon,
    QMenu,
    QApplication,
    QLabel,
    QPushButton,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter, QBrush, QPen, QColor, QFont

from ui.theme_manager import ThemeManager
from ui.pages.controller_emulation import ControllerEmulation
from ui.pages.controllers import ControllersPage
from ui.pages.settings import SettingsPage
from ui.pages.server import ServerPage
from ui.pages.web_remote import WebRemotePage
from ui.pages.hotkey import HotkeyPage
from ui.pages.profiles import ProfilesPage
from ui.pages.about import AboutPage
from core.settings import SettingsManager
from core.profile_manager import ProfileManager

from core.utils.hotkeys import Hotkey
from core.utils.paths import data_path, resource_path
from ui.i18n import apply_translations, tr
from core.version import APP_NAME

class MainWindow(QMainWindow):

    WINDOW_TITLE = APP_NAME
    WINDOW_WIDTH = 1100
    WINDOW_HEIGHT = 700

    # Menu indices (must match the order items are added to self.menu)
    IDX_CONTROLLER_EMULATION = 0
    IDX_REMOTE_GAMEPAD = 1
    IDX_HOTKEY = 2
    IDX_PROFILES = 3
    IDX_TEST_XINPUT = 4
    IDX_SETTINGS = 5
    IDX_ABOUT = 6
    IDX_WEB_REMOTE = 7
    IDX_QUIT = 8

    def __init__(self, app: QApplication) -> None:
        super().__init__()

        # Theme & settings
        self.theme_manager = ThemeManager(app)
        self.theme_manager.apply_theme("dark")
        self.media_functions = {
                "volume up": "volume up",
                "volume down": "volume down",
                "play/pause media": "play/pause media",
                "next track": "next track",
                "previous track": "previous track",
                "volume mute": "volume mute",
            }
        self.hotkey = Hotkey(str(data_path("hotkeys.json")))
        self.settings = SettingsManager()
        self.profile_manager = ProfileManager(self.settings)
        self.profile_manager.create_default_profile()
        self._applying_language = False

        # quitting flag
        self._is_quitting = False

        self.setWindowTitle(self.WINDOW_TITLE)
        self.resize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

        self._shown_tray_hint = False

        # Main application shell
        central = QWidget(self)
        central.setObjectName("app_root")
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(22, 18, 22, 18)
        main_layout.setSpacing(14)
        self.setCentralWidget(central)

        # Compact application header
        header = QWidget()
        header.setObjectName("app_header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(2, 0, 2, 0)
        header_layout.setSpacing(12)

        brand = QWidget()
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(12)

        self._brand_mark = QLabel("IB")
        self._brand_mark.setObjectName("brand_mark")
        self._brand_mark.setAlignment(Qt.AlignCenter)
        self._brand_mark.setFixedSize(44, 44)
        brand_layout.addWidget(self._brand_mark)

        brand_title = QLabel("InputBridge")
        brand_title.setObjectName("brand_title")
        brand_layout.addWidget(brand_title)
        header_layout.addWidget(brand)
        header_layout.addStretch(1)

        # Active profile chip (kept compact so navigation remains the focus)
        self._avatar_container = QWidget()
        self._avatar_container.setObjectName("profile_chip")
        avatar_layout = QHBoxLayout(self._avatar_container)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        avatar_layout.setSpacing(8)

        self._sidebar_avatar = _SidebarAvatar(32)
        avatar_layout.addWidget(self._sidebar_avatar, alignment=Qt.AlignVCenter)

        profile_copy = QVBoxLayout()
        profile_copy.setContentsMargins(0, 0, 0, 0)
        profile_copy.setSpacing(1)
        self._sidebar_profile_name = QLabel("")
        self._sidebar_profile_name.setObjectName("sidebar_profile_name")
        self._sidebar_profile_name.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._sidebar_profile_label = QLabel("No profile active")
        self._sidebar_profile_label.setObjectName("sidebar_profile_label")
        self._sidebar_profile_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        profile_copy.addWidget(self._sidebar_profile_name)
        profile_copy.addWidget(self._sidebar_profile_label)
        avatar_layout.addLayout(profile_copy)
        header_layout.addWidget(self._avatar_container)

        main_layout.addWidget(header)

        # Native horizontal tabs keep each label at its natural width.
        # Unlike a QListWidget flow, tabs are never forced to share the first
        # item's width, so longer names and translated labels remain readable.
        self.menu = QTabBar()
        self.menu.setObjectName("top_navigation")
        self.menu.setDocumentMode(True)
        self.menu.setDrawBase(False)
        self.menu.setExpanding(False)
        self.menu.setMovable(False)
        self.menu.setUsesScrollButtons(True)
        self.menu.setElideMode(Qt.ElideNone)
        self.menu.setShape(QTabBar.Shape.RoundedNorth)
        self.menu.addTab("Controller Emulation")                       # 0
        self.menu.addTab("Mobile Controller")                          # 1
        self.menu.addTab("Hotkeys")                                    # 2
        self.menu.addTab("Profiles")                                   # 3
        self.menu.addTab("Input Test")                                 # 4
        self.menu.addTab("Settings")                                   # 5
        self.menu.addTab("About")                                      # 6
        self.menu.addTab("Web Companion")                               # 7
        self.menu.setMinimumHeight(44)
        main_layout.addWidget(self.menu)

        # Pages
        self.pages = QStackedWidget()
        self.pages.setObjectName("content_stack")

        controllers_page = ControllersPage(self.settings)
        self.controllers_page = controllers_page
        hotkey_page = HotkeyPage(self.hotkey)
        self.hotkey_page = hotkey_page
        # The stacked page order must match menu indices 0..7.
        # 0: Controller Emulation
        self.controller_emulation_page = ControllerEmulation(
            self.settings, controllers_page, hotkey_page
        )
        self.pages.addWidget(self.controller_emulation_page)
        # 1: Remote Gamepad (server page)
        self.server_page = ServerPage(self.settings, controllers_page, hotkey_page)
        self.pages.addWidget(self.server_page)
        # 2: Hotkeys page
        self.pages.addWidget(hotkey_page)
        # 3: Profiles
        self.profiles_page = ProfilesPage(self.profile_manager, self.settings)
        self.profiles_page.profile_loaded.connect(self._on_profile_loaded)
        self.profiles_page.profile_changed.connect(self._refresh_sidebar_avatar)
        self.pages.addWidget(self.profiles_page)
        # 4: Test XInput
        self.pages.addWidget(controllers_page)
        # 5: Settings
        self.settings_page = SettingsPage(self.theme_manager, self.settings, self.profile_manager)
        self.pages.addWidget(self.settings_page)
        self.settings_page.combo_lang.currentIndexChanged.connect(
            lambda _index: self._apply_language()
        )
        self.settings_page.vibration_enabled_changed.connect(
            self.controllers_page.set_vibration_enabled
        )
        self.about_page = AboutPage()
        self.pages.addWidget(self.about_page)
        # Browser controllers share the existing mapper registration path with
        # the TLS phone client, so each paired browser appears as its own XInput
        # device alongside mobile and physical controllers.
        self.web_remote_page = WebRemotePage(
            self.settings, controllers_page, hotkey_page, self.server_page,
            status_changed=self._refresh_tray_menu,
        )
        self.pages.addWidget(self.web_remote_page)

        main_layout.addWidget(self.pages, 1)

        self.menu.currentChanged.connect(self._on_menu_index_changed)
        self.menu.setCurrentIndex(self.IDX_CONTROLLER_EMULATION)

        # Initialize sidebar avatar
        self._refresh_sidebar_avatar()
        self._apply_language()

        # Tray
        self.tray_icon: QSystemTrayIcon | None = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self._init_tray_icon()
            app.setQuitOnLastWindowClosed(False)
        app.aboutToQuit.connect(self.shutdown)

    # --------------------
    # Menu
    # --------------------

    def _on_menu_index_changed(self, index: int) -> None:
        # If Quit item selected
        if index == self.IDX_QUIT:
            self._is_quitting = True
            QApplication.quit()
            return

        # For all remaining tabs, show the matching stacked page (indices 0..7).
        if 0 <= index < self.pages.count():
            self.pages.setCurrentIndex(index)

    # --------------------
    # Tray
    # --------------------

    def _init_tray_icon(self) -> None:

        tray_icon = QSystemTrayIcon(self)

        icon = QIcon(str(resource_path("ui", "assets", "tray.png")))
        if icon.isNull():
            icon = QIcon.fromTheme("applications-system")

        tray_icon.setIcon(icon)
        tray_icon.setToolTip(self.WINDOW_TITLE)

        self.tray_icon = tray_icon
        self._create_tray_menu()

        tray_icon.activated.connect(self._on_tray_activated)
        tray_icon.show()
        self.server_page.tray_status_callback = self._refresh_tray_menu
        self.server_page.signals.client_connected.connect(
            lambda _addr: self._refresh_tray_menu()
        )
        self.server_page.signals.client_disconnected.connect(
            lambda _addr: self._refresh_tray_menu()
        )

    def _create_tray_menu(self) -> None:

        if self.tray_icon is None:
            return

        menu = QMenu(self)

        self._tray_menu = menu

        self._tray_status_action = QAction("Server: stopped", menu)
        self._tray_status_action.setEnabled(False)
        menu.addAction(self._tray_status_action)
        menu.addSeparator()

        self._tray_show_action = QAction("Show window", menu)
        self._tray_show_action.triggered.connect(self._show_from_tray)
        menu.addAction(self._tray_show_action)

        self._tray_hide_action = QAction("Hide window", menu)
        self._tray_hide_action.triggered.connect(self.hide)
        menu.addAction(self._tray_hide_action)

        self._tray_server_action = QAction("Start server", menu)
        self._tray_server_action.triggered.connect(self._toggle_server_from_tray)
        menu.addAction(self._tray_server_action)

        menu.addSeparator()
        for label, index in (
            ("Controller Emulation", self.IDX_CONTROLLER_EMULATION),
            ("Mobile Controller", self.IDX_REMOTE_GAMEPAD),
            ("Hotkeys", self.IDX_HOTKEY),
            ("Profiles", self.IDX_PROFILES),
            ("Settings", self.IDX_SETTINGS),
            ("About", self.IDX_ABOUT),
            ("Web Companion", self.IDX_WEB_REMOTE),
        ):
            action = QAction(label, menu)
            action.triggered.connect(
                lambda checked=False, target=index: self._show_page_from_tray(target)
            )
            menu.addAction(action)

        menu.addSeparator()
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self._quit_from_tray)
        menu.addAction(quit_action)
        menu.aboutToShow.connect(self._refresh_tray_menu)
        self.tray_icon.setContextMenu(menu)
        self._refresh_tray_menu()

    def _refresh_tray_menu(self) -> None:
        if self.tray_icon is None:
            return
        running = bool(getattr(self.server_page, "server_running", False))
        client_count = len(getattr(self.server_page, "clients", {}))
        web_server = getattr(getattr(self, "web_remote_page", None), "web_server", None)
        web_running = bool(getattr(web_server, "running", False))
        web_count = int(getattr(web_server, "client_count", 0)) if web_server else 0
        mapped_count = len(getattr(self.controller_emulation_page, "mappers", {}))
        self._tray_status_action.setText(
            f"Phone: {'on' if running else 'off'} · Web: {'on' if web_running else 'off'} · "
            f"Clients: {client_count}+{web_count} · Mapped: {mapped_count}"
        )
        self._tray_server_action.setText("Stop phone server" if running else "Start phone server")
        self.tray_icon.setToolTip(
            f"{self.WINDOW_TITLE} — Phone server {'running' if running else 'stopped'}, "
            f"Web Companion {'running' if web_running else 'stopped'}"
        )
        self._tray_hide_action.setEnabled(self.isVisible())

    def _toggle_server_from_tray(self) -> None:
        self.server_page.toggle_server()
        self._refresh_tray_menu()

    def _on_profile_loaded(self, profile_name: str) -> None:
        """Called when a profile is activated from the Profiles page."""
        self._refresh_sidebar_avatar()
        self.settings_page.reload_from_settings()
        # Reload theme in case it changed
        try:
            theme = self.settings.get_ui_theme()
            self.theme_manager.apply_theme(theme)
        except Exception:
            pass

    def _refresh_sidebar_avatar(self) -> None:
        """Update the sidebar avatar and profile name from the active profile."""
        name = self.profile_manager.get_active_profile_name()
        try:
            language = self.settings.get_ui_language()
        except Exception:
            language = "eng"
        if name:
            img_path = self.profile_manager.get_profile_image_path(name)
            self._sidebar_avatar.set_image(img_path)
            self._sidebar_profile_name.setText(name)
            self._sidebar_profile_label.setText(tr("Active profile", language))
        else:
            self._sidebar_avatar.set_image(None)
            self._sidebar_profile_name.setText("")
            self._sidebar_profile_label.setText(tr("No profile active", language))

    def _apply_language(self) -> None:
        """Apply the selected UI language without changing layout direction."""
        if self._applying_language:
            return
        self._applying_language = True
        try:
            language = self.settings_page.combo_lang.currentData()
            if language not in ("eng", "fa", "es"):
                language = self.settings.get_ui_language()
            self.settings.set_ui_language(language or "eng")
            self.settings.save()
        except Exception:
            language = "eng"
        try:
            apply_translations(self, language)
            self.profiles_page.refresh_list()
            self._sidebar_profile_label.setText(
                tr(
                    "Active profile"
                    if self.profile_manager.get_active_profile_name()
                    else "No profile active",
                    language,
                )
            )
        finally:
            self._applying_language = False

    def _show_page_from_tray(self, index: int) -> None:
        self.menu.setCurrentIndex(index)
        self._show_from_tray()

    def _quit_from_tray(self) -> None:
        self._is_quitting = True
        QApplication.quit()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:

        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):

            if self.isVisible() and not self.isMinimized():
                self.hide()
            else:
                self._show_from_tray()

    def _show_from_tray(self) -> None:

        self.show()

        if self.isMinimized():
            self.setWindowState(self.windowState() & ~Qt.WindowMinimized)

        self.activateWindow()
        self.raise_()
        self._refresh_tray_menu()

    def shutdown(self) -> None:
        if getattr(self, "_shutdown_complete", False):
            return
        self._shutdown_complete = True
        try:
            self.server_page.shutdown()
        except Exception as exc:
            print(f"[MainWindow] Server shutdown failed: {exc}")
        try:
            self.web_remote_page.shutdown()
        except Exception as exc:
            print(f"[MainWindow] Web Companion shutdown failed: {exc}")
        try:
            self.controller_emulation_page.shutdown()
        except Exception as exc:
            print(f"[MainWindow] HID shutdown failed: {exc}")
        try:
            self.controllers_page.refresh_timer.stop()
        except Exception:
            pass
        if self.tray_icon is not None:
            self.tray_icon.hide()

    # --------------------
    # Close behavior
    # --------------------

    def closeEvent(self, event) -> None:
        # If we are quitting explicitly (from menu or tray), exit
        if self._is_quitting:
            self.shutdown()
            event.accept()
            return

        # Otherwise, go to tray (if available)
        if self.tray_icon is not None:

            self.hide()

            if not self._shown_tray_hint:
                try:
                    self.tray_icon.showMessage(
                        self.WINDOW_TITLE,
                        "Application is still running in the tray. "
                        "Use the tray icon to restore or quit.",
                    )
                except Exception:
                    pass

                self._shown_tray_hint = True

            event.ignore()
        else:
            self.shutdown()
            super().closeEvent(event)


# ------------------------------------------------------------------
# Sidebar avatar widget
# ------------------------------------------------------------------

class _SidebarAvatar(QLabel):
    """Circular avatar displayed at the top of the sidebar."""

    def __init__(self, size: int = 64, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.setStyleSheet("background: transparent;")
        self._pixmap: QPixmap | None = None

    def set_image(self, path: str | None) -> None:
        if path and Path(path).is_file():
            self._pixmap = QPixmap(path)
        else:
            self._pixmap = None
        self.update()

    def paintEvent(self, event) -> None:
        s = self._size
        if self._pixmap is None or self._pixmap.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QBrush(QColor("#3a3a5a")))
            painter.setPen(QPen(QColor("#555577"), 2))
            painter.drawEllipse(1, 1, s - 2, s - 2)
            # Draw a controller icon placeholder
            painter.setPen(QColor("#8888aa"))
            font = QFont()
            font.setPixelSize(s // 3)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, "🎮")
            painter.end()
            return

        scaled = self._pixmap.scaled(
            s, s, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
        )
        x = (scaled.width() - s) // 2
        y = (scaled.height() - s) // 2
        cropped = scaled.copy(x, y, s, s)

        mask = QPixmap(s, s)
        mask.fill(QColor(0, 0, 0, 0))
        m = QPainter(mask)
        m.setRenderHint(QPainter.Antialiasing)
        m.setBrush(QBrush(QColor(0, 0, 0)))
        m.setPen(Qt.NoPen)
        m.drawEllipse(0, 0, s, s)
        m.end()
        cropped.setMask(mask.mask())

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawPixmap(0, 0, cropped)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#5a5af0"), 2))
        painter.drawEllipse(1, 1, s - 2, s - 2)
        painter.end()

