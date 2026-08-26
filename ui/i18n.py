"""Small runtime translation layer for the desktop UI."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractButton,
    QComboBox,
    QGroupBox,
    QLabel,
    QListWidget,
    QWidget,
)


LANGUAGE_NAMES = {
    "eng": "English",
    "fa": "فارسی",
    "es": "Español",
}

_TRANSLATIONS = {
    "fa": {
        "Controller Emulation": "🎮 شبیه‌سازی دسته",
        "Remote Gamepad": "📱 دستهٔ راه دور",
        "Hotkeys": "⌨️ میانبرها",
        "Profiles": "🗂️ پروفایل‌ها",
        "Test XInput": "🧪 تست XInput",
        "Settings": "⚙️ تنظیمات",
        "About": "ℹ️ دربارهٔ برنامه",
        "About": "ℹ️ دربارهٔ برنامه",
        "Quit": "🚪 خروج",
        "No profile active": "پروفایل فعالی وجود ندارد",
        "Active profile": "پروفایل فعال",
        "active": "فعال",
        "Open ArvinNotDev on GitHub": "باز کردن صفحهٔ ArvinNotDev در گیت‌هاب",
        "Device": "دستگاه",
        "UI": "رابط کاربری",
        "Developer": "توسعه‌دهنده",
        "Device Settings": "تنظیمات دستگاه",
        "UI Settings": "تنظیمات رابط کاربری",
        "Developer Settings": "تنظیمات توسعه‌دهنده",
        "Polling rate (Hz)": "نرخ نمونه‌برداری (هرتز)",
        "Auto reconnect": "اتصال مجدد خودکار",
        "D-Pad as mouse": "تبدیل D-Pad به ماوس",
        "Mouse mode": "حالت ماوس",
        "Mouse sensitivity": "حساسیت ماوس",
        "Left joystick deadzone": "ناحیهٔ مردهٔ جوی‌استیک چپ",
        "Right joystick deadzone": "ناحیهٔ مردهٔ جوی‌استیک راست",
        "Axis inversion": "معکوس‌سازی محورها",
        "Left": "چپ",
        "Right": "راست",
        "Invert X joystick": "معکوس‌سازی محور X",
        "Invert Y joystick": "معکوس‌سازی محور Y",
        "Invert buttons": "معکوس‌سازی دکمه‌ها",
        "Language": "زبان",
        "Theme": "پوسته",
        "Debug": "اشکال‌زدایی",
        "Raw HID debug": "اشکال‌زدایی HID خام",
        "Log to file": "ثبت گزارش در فایل",
        "Log file path": "مسیر فایل گزارش",
        "Reset": "بازنشانی",
        "Apply Now": "اعمال فوری",
        "Auto-save is on": "ذخیرهٔ خودکار فعال است",
        "✓ Auto-saved": "✓ ذخیرهٔ خودکار انجام شد",
        "Save Settings to Profile": "ذخیرهٔ تنظیمات در پروفایل",
        "Profiles Not Available": "پروفایل‌ها در دسترس نیستند",
        "Profile manager is not initialized.": "مدیر پروفایل آماده نشده است.",
        "New Profile": "پروفایل جدید",
        "Profile name:": "نام پروفایل:",
        "Overwrite Profile?": "بازنویسی پروفایل؟",
        "Profile Saved": "پروفایل ذخیره شد",
        "Profile Updated": "پروفایل به‌روزرسانی شد",
        "Profiles": "پروفایل‌ها",
        "Manage your application settings profiles": "پروفایل‌های تنظیمات برنامه را مدیریت کنید",
        "Select a profile": "یک پروفایل انتخاب کنید",
        "Description": "توضیحات",
        "Add a description for this profile…": "برای این پروفایل توضیحی بنویسید…",
        "Save Description": "ذخیرهٔ توضیحات",
        "Metadata": "اطلاعات",
        "Created: —": "ساخته‌شده: —",
        "Modified: —": "آخرین تغییر: —",
        "Created": "ساخته‌شده",
        "Modified": "آخرین تغییر",
        "Settings Summary": "خلاصهٔ تنظیمات",
        "Built with care for gamers 🎮": "با عشق برای گیمرها ساخته شده 🎮",
        "Activate Profile": "فعال‌سازی پروفایل",
        "✓ Active": "✓ فعال",
        "＋ New": "＋ جدید",
        "⧉ Copy": "⧉ کپی",
        "✎ Rename": "✎ تغییر نام",
        "🗑 Delete": "🗑 حذف",
        "Delete": "حذف",
        "Add Controller": "➕ افزودن دسته",
        "📷 Set Image": "📷 انتخاب تصویر",
        "⬇ Import": "⬇ درون‌ریزی",
        "⬆ Export": "⬆ برون‌بری",
        "Remove profile image": "حذف تصویر پروفایل",
        "Save as new profile…": "ذخیره به‌عنوان پروفایل جدید…",
        "Overwrite": "بازنویسی",
        "Emulated Devices": "دستگاه‌های شبیه‌سازی‌شده",
        "Battery": "باتری",
        "Connected Clients": "کلاینت‌های متصل",
        "Trusted Platforms": "دستگاه‌های مورد اعتماد",
        "Start Server": "شروع سرور",
        "Stop Server": "توقف سرور",
        "Remove": "حذف",
        "Disconnect": "قطع اتصال",
        "Emulate": "شبیه‌سازی",
        "Stop": "توقف",
        "Choose a controller to define hotkeys on.\n(Hotkeys will be applied to all controllers.)":
            "دسته‌ای را برای تعریف میانبر انتخاب کنید.\n(میانبرها روی همهٔ دسته‌ها اعمال می‌شوند.)",
        "Add Hotkey": "افزودن میانبر",
        "Delete Hotkey": "حذف میانبر",
        "Redo": "دوباره",
        "Apply": "اعمال",
        "Current Hotkeys": "میانبرهای فعلی",
        "Hotkey Settings": "تنظیمات میانبر",
        "Xbox 360 Controller Monitor": "مانیتور دستهٔ Xbox 360",
        "Buttons": "دکمه‌ها",
        "No buttons pressed": "هیچ دکمه‌ای فشرده نشده است",
        "Controller": "دسته",
        "HidHide": "HidHide",
        "Unhide All": "نمایش همه",
        "Open Link": "باز کردن لینک",
        "Hide": "مخفی کردن",
        "Unhide": "نمایش",
        "Hidden": "مخفی",
        "Visible": "قابل مشاهده",
        "Unknown": "ناشناخته",
        "✨  INPUTBRIDGE": "✨  INPUTBRIDGE",
        "Built with care for gamers 🎮": "با عشق برای گیمرها ساخته شده 🎮",
        "Developer: آروین جعفری": "توسعه‌دهنده: آروین جعفری",
        "🐙 GitHub Profile": "🐙 پروفایل گیت‌هاب",
        "📦 Project Repository": "📦 مخزن پروژه",
        "💡 Tip: Create a profile for each game and switch between them in seconds.":
            "💡 نکته: برای هر بازی یک پروفایل بسازید و در چند ثانیه جابه‌جا شوید.",
        "A modern bridge between your controllers, XInput, keyboard, and mouse.":
            "پل مدرن بین دسته‌ها، XInput، صفحه‌کلید و ماوس شما.",
        "InputBridge-Gamepad2XInput helps you connect physical HID controllers to virtual Xbox 360 devices with flexible profiles, hotkeys, mouse mode, remote gamepad support, and HidHide integration.":
            "InputBridge-Gamepad2XInput دسته‌های HID فیزیکی را با پروفایل‌های "
            "انعطاف‌پذیر، میانبرها، حالت ماوس، دستهٔ راه دور و HidHide به دستگاه‌های "
            "مجازی Xbox 360 متصل می‌کند.",
        "English": "انگلیسی",
        "فارسی": "فارسی",
        "Español": "اسپانیایی",
    },
    "es": {
        "Controller Emulation": "🎮 Emulación de mandos",
        "Remote Gamepad": "📱 Gamepad remoto",
        "Hotkeys": "⌨️ Atajos",
        "Profiles": "🗂️ Perfiles",
        "Test XInput": "🧪 Probar XInput",
        "Settings": "⚙️ Ajustes",
        "About": "ℹ️ Acerca de",
        "About": "ℹ️ Acerca de",
        "Quit": "🚪 Salir",
        "No profile active": "No hay perfil activo",
        "Active profile": "Perfil activo",
        "active": "activo",
        "Device": "Dispositivo",
        "UI": "Interfaz",
        "Developer": "Desarrollador",
        "Device Settings": "Ajustes del dispositivo",
        "UI Settings": "Ajustes de la interfaz",
        "Developer Settings": "Ajustes del desarrollador",
        "Auto reconnect": "Reconexión automática",
        "D-Pad as mouse": "D-Pad como ratón",
        "Mouse mode": "Modo ratón",
        "Mouse sensitivity": "Sensibilidad del ratón",
        "Axis inversion": "Inversión de ejes",
        "Language": "Idioma",
        "Theme": "Tema",
        "Reset": "Restablecer",
        "Apply Now": "Aplicar ahora",
        "Auto-save is on": "Guardado automático activo",
        "Save Settings to Profile": "Guardar ajustes en el perfil",
        "Profiles": "Perfiles",
        "Manage your application settings profiles": "Gestiona tus perfiles de configuración",
        "Select a profile": "Selecciona un perfil",
        "Description": "Descripción",
        "Save Description": "Guardar descripción",
        "Metadata": "Metadatos",
        "Settings Summary": "Resumen de ajustes",
        "Created": "Creado",
        "Modified": "Modificado",
        "Activate Profile": "Activar perfil",
        "＋ New": "＋ Nuevo",
        "⧉ Copy": "⧉ Copiar",
        "✎ Rename": "✎ Renombrar",
        "🗑 Delete": "🗑 Eliminar",
        "Delete": "Eliminar",
        "Add Controller": "➕ Añadir mando",
        "📷 Set Image": "📷 Elegir imagen",
        "⬇ Import": "⬇ Importar",
        "⬆ Export": "⬆ Exportar",
        "Emulated Devices": "Dispositivos emulados",
        "Connected Clients": "Clientes conectados",
        "Trusted Platforms": "Plataformas de confianza",
        "Start Server": "Iniciar servidor",
        "Stop Server": "Detener servidor",
        "Remove": "Eliminar",
        "Disconnect": "Desconectar",
        "Emulate": "Emular",
        "Stop": "Detener",
        "Redo": "Rehacer",
        "Apply": "Aplicar",
        "Current Hotkeys": "Atajos actuales",
        "HidHide": "HidHide",
        "Unhide All": "Mostrar todos",
        "Open Link": "Abrir enlace",
        "Hide": "Ocultar",
        "Unhide": "Mostrar",
        "Hidden": "Oculto",
        "Visible": "Visible",
        "Unknown": "Desconocido",
        "✨  INPUTBRIDGE": "✨  INPUTBRIDGE",
        "Built with care for gamers 🎮": "Creado con cariño para gamers 🎮",
        "Developer: آروین جعفری": "Desarrollador: آروین جعفری",
        "🐙 GitHub Profile": "🐙 Perfil de GitHub",
        "📦 Project Repository": "📦 Repositorio del proyecto",
        "💡 Tip: Create a profile for each game and switch between them in seconds.":
            "💡 Consejo: crea un perfil para cada juego y cambia entre ellos en segundos.",
        "A modern bridge between your controllers, XInput, keyboard, and mouse.":
            "Un puente moderno entre tus mandos, XInput, teclado y ratón.",
        "InputBridge-Gamepad2XInput helps you connect physical HID controllers to virtual Xbox 360 devices with flexible profiles, hotkeys, mouse mode, remote gamepad support, and HidHide integration.":
            "InputBridge-Gamepad2XInput conecta mandos HID físicos con dispositivos "
            "Xbox 360 virtuales mediante perfiles flexibles, atajos, modo ratón, "
            "gamepad remoto e integración con HidHide.",
        "English": "Inglés",
        "فارسی": "Persa",
        "Español": "Español",
    },
}


def tr(text: str, language: str = "eng") -> str:
    """Translate a source string, leaving unknown/dynamic text untouched."""
    if not text or language == "eng":
        return text
    return _TRANSLATIONS.get(language, {}).get(text, text)


def _translate_widget(widget: QWidget, language: str) -> None:
    if widget.property("_i18n_dynamic"):
        return
    source = widget.property("_i18n_source")
    if source is None:
        if isinstance(widget, QGroupBox):
            source = widget.title()
        elif isinstance(widget, QAbstractButton):
            source = widget.text()
        elif isinstance(widget, QLabel):
            source = widget.text()
        else:
            source = widget.windowTitle()
        widget.setProperty("_i18n_source", source)

    if isinstance(widget, QGroupBox):
        widget.setTitle(tr(source, language))
    elif isinstance(widget, QAbstractButton):
        widget.setText(tr(source, language))
    elif isinstance(widget, QLabel):
        widget.setText(tr(source, language))
    elif source:
        widget.setWindowTitle(tr(source, language))

    if isinstance(widget, QComboBox):
        for index in range(widget.count()):
            item_source = widget.itemData(index, Qt.UserRole + 1000)
            if item_source is None:
                item_source = widget.itemText(index)
                widget.setItemData(index, item_source, Qt.UserRole + 1000)
            widget.setItemText(index, tr(item_source, language))

    if isinstance(widget, QListWidget):
        for index in range(widget.count()):
            item = widget.item(index)
            item_source = item.data(Qt.UserRole + 1000)
            if item_source is None:
                item_source = item.text()
                item.setData(Qt.UserRole + 1000, item_source)
            item.setText(tr(item_source, language))


def apply_translations(root: QWidget, language: str) -> None:
    """Translate all static widgets below ``root`` without changing layout."""
    for widget in [root, *root.findChildren(QWidget)]:
        _translate_widget(widget, language)
    for action in root.findChildren(QAction):
        source = action.property("_i18n_source")
        if source is None:
            source = action.text()
            action.setProperty("_i18n_source", source)
        action.setText(tr(source, language))
