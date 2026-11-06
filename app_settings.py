from pathlib import Path

from PySide6.QtCore import QSettings

try:
    import winreg
except ImportError:
    winreg = None

ORGANIZATION = "Winamp-Py"
LEGACY_ORGANIZATION = "MyMusicPlayer"
LEGACY_GROUPS = (("VLCPlayer", ""), ("GeissVisualization", "GeissVisualization"))


def open_settings(group=""):
    settings = QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, ORGANIZATION, "settings")
    if not Path(settings.fileName()).exists():
        import_legacy_settings(settings)
    if group:
        settings.beginGroup(group)
    return settings


def legacy_key_exists(application):
    if winreg is None:
        return False
    try:
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\{LEGACY_ORGANIZATION}\\{application}"))
    except OSError:
        return False
    return True


def import_legacy_settings(settings):
    for application, group in LEGACY_GROUPS:
        if not legacy_key_exists(application):
            continue
        legacy = QSettings(QSettings.Format.NativeFormat, QSettings.Scope.UserScope, LEGACY_ORGANIZATION, application)
        for key in legacy.allKeys():
            settings.setValue(f"{group}/{key}" if group else key, legacy.value(key))
    settings.sync()
