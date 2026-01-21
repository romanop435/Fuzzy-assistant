import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QDialog

from app.core.actions import ActionDispatcher
from app.core.commands import CommandMatcher, CommandProcessor
from app.core.config import ConfigStore
from app.core.stt import SpeechListener
from app.core.timer_manager import TimerManager
from app.core.tts import TtsEngine
from app.core.utils import app_root
from app.ui.main_window import MainWindow
from app.ui.settings_dialog import SettingsDialog
from app.ui.splash import SplashScreen
from app.ui.styles import theme_styles
from app.ui.tray import TrayManager


def resolve_model_path(config: ConfigStore) -> str:
    model_path = config.get_setting("stt", "model_path", default="")
    if not model_path:
        return ""
    return resolve_asset_path(model_path)


def resolve_asset_path(value: str) -> str:
    if not value:
        return ""
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str(app_root() / value)


def show_splash(app: QApplication, config: ConfigStore):
    if not config.get_setting("ui", "splash_enabled", default=False):
        return None, None
    icon_path = resolve_asset_path(config.get_setting("ui", "splash_icon", default=""))
    sound_path = resolve_asset_path(config.get_setting("ui", "splash_sound", default=""))
    duration_ms = int(config.get_setting("ui", "splash_duration_ms", default=3500))

    splash = SplashScreen(icon_path, duration_ms=duration_ms)
    splash.show()
    splash.start()
    app.processEvents()
    screen = app.primaryScreen()
    if screen:
        geo = screen.availableGeometry()
        splash.move(geo.center() - splash.rect().center())

    player = None
    if sound_path and Path(sound_path).exists():
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

            player = QMediaPlayer()
            audio = QAudioOutput()
            volume = float(config.get_setting("ui", "splash_volume", default=0.7))
            audio.setVolume(max(0.0, min(1.0, volume)))
            player.setAudioOutput(audio)
            player.setSource(QUrl.fromLocalFile(sound_path))
            player.durationChanged.connect(
                lambda ms, base=duration_ms: splash.set_duration_ms(max(base, int(ms))) if ms else None
            )
            player.play()
            player._audio = audio
        except Exception:
            player = None
    return splash, player


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    config = ConfigStore()
    theme = config.get_setting("ui", "theme", default="dark")
    app.setStyleSheet(theme_styles(theme))

    icon_path = resolve_asset_path(
        config.get_setting("ui", "app_icon", default=config.get_setting("ui", "splash_icon", default=""))
    )
    app_icon = QIcon(icon_path) if icon_path and Path(icon_path).exists() else QIcon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    splash, splash_player = show_splash(app, config)

    tts = TtsEngine(
        enabled=config.get_setting("tts", "enabled", default=True),
        volume=float(config.get_setting("tts", "volume", default=0.9)),
        rate=int(config.get_setting("tts", "rate", default=180)),
    )
    timer_manager = TimerManager()
    dispatcher = ActionDispatcher(config.targets, config.allowlist, timer_manager)
    matcher = CommandMatcher(config.commands)
    processor = CommandProcessor(dispatcher, config.get_setting("stt", "wake_word", default=""))

    window = MainWindow(config, matcher, processor, timer_manager, tts)
    if not app_icon.isNull():
        window.setWindowIcon(app_icon)
    tray = TrayManager(window, icon=app_icon if not app_icon.isNull() else None)
    window.set_notifier(tray.show_message)

    model_path = resolve_model_path(config)
    listener = SpeechListener(
        model_path=model_path,
        wake_word=config.get_setting("stt", "wake_word", default=""),
        sample_rate=int(config.get_setting("stt", "sample_rate", default=16000)),
    )
    listener.configure(
        command_timeout_sec=int(config.get_setting("stt", "command_timeout_sec", default=8)),
        silence_timeout_ms=int(config.get_setting("stt", "silence_timeout_ms", default=1200)),
        device_index=config.get_setting("stt", "device_index", default=None),
        debug_console=config.get_setting("stt", "debug_console", default=False),
    )
    window.set_listener(listener)
    window.listening_changed.connect(tray.update_state)
    window.direct_mode_changed.connect(tray.update_direct_mode)

    def open_settings() -> None:
        dialog = SettingsDialog(config, listener, window)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.values()
            was_listening = window.is_listening()
            config.set_setting("stt", "device_index", value=values["device_index"])
            config.set_setting("stt", "command_timeout_sec", value=values["command_timeout_sec"])
            config.set_setting("tts", "enabled", value=values["tts_enabled"])
            config.set_setting("tts", "volume", value=values["tts_volume"])
            config.set_setting("tts", "rate", value=values["tts_rate"])
            config.set_setting("ui", "theme", value=values["theme"])
            config.set_setting("ui", "overlay_enabled", value=values["overlay_enabled"])
            config.save_settings()
            tts.update(values["tts_enabled"], values["tts_volume"], values["tts_rate"])
            listener.configure(
                command_timeout_sec=values["command_timeout_sec"],
                silence_timeout_ms=int(config.get_setting("stt", "silence_timeout_ms", default=1200)),
                device_index=values["device_index"],
                debug_console=config.get_setting("stt", "debug_console", default=False),
            )
            app.setStyleSheet(theme_styles(values["theme"]))
            if was_listening:
                listener.stop()
                listener.start()

    window.settings_button_clicked(open_settings)

    def show_main() -> None:
        window.show()
        window.start_listening()

    if splash:
        splash.finished.connect(lambda: (splash.close(), show_main()))
    else:
        show_main()
    def shutdown() -> None:
        listener.stop()
        tts.stop()
    app.aboutToQuit.connect(shutdown)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
