from PySide6.QtCore import QObject
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QInputDialog, QMenu, QStyle, QSystemTrayIcon

from app.core.timer_manager import parse_timer_request


class TrayManager(QObject):
    def __init__(self, window, icon: QIcon | None = None) -> None:
        super().__init__(window)
        self._window = window
        tray_icon = icon if icon and not icon.isNull() else window.windowIcon()
        if tray_icon.isNull():
            tray_icon = window.style().standardIcon(QStyle.SP_ComputerIcon)
        self._tray = QSystemTrayIcon(tray_icon, window)
        self._menu = QMenu()
        self._toggle_action = QAction("\u0412\u043a\u043b\u044e\u0447\u0438\u0442\u044c \u043f\u0440\u043e\u0441\u043b\u0443\u0448\u0438\u0432\u0430\u043d\u0438\u0435", window)
        self._toggle_action.triggered.connect(self._toggle_listening)
        self._direct_action = QAction("\u041a\u043e\u043c\u0430\u043d\u0434\u044b \u0431\u0435\u0437 \"\u0424\u0430\u0437\u0438\": \u0432\u044b\u043a\u043b", window)
        self._direct_action.triggered.connect(self._toggle_direct_mode)
        self._open_action = QAction("\u041e\u0442\u043a\u0440\u044b\u0442\u044c \u043e\u043a\u043d\u043e", window)
        self._open_action.triggered.connect(self._open_window)
        self._timer_action = QAction("\u0411\u044b\u0441\u0442\u0440\u044b\u0439 \u0442\u0430\u0439\u043c\u0435\u0440...", window)
        self._timer_action.triggered.connect(self._quick_timer)
        self._exit_action = QAction("\u0412\u044b\u0445\u043e\u0434", window)
        self._exit_action.triggered.connect(self._window.request_exit)

        self._menu.addAction(self._toggle_action)
        self._menu.addAction(self._direct_action)
        self._menu.addAction(self._open_action)
        self._menu.addAction(self._timer_action)
        self._menu.addSeparator()
        self._menu.addAction(self._exit_action)
        self._tray.setContextMenu(self._menu)
        self._tray.setToolTip("\u0424\u0430\u0437\u0438")
        self._tray.activated.connect(self._on_activate)
        self._tray.show()

    def _toggle_listening(self) -> None:
        self._window.toggle_listening()
        self.update_state(self._window.is_listening())

    def _toggle_direct_mode(self) -> None:
        self._window.toggle_direct_mode()
        self.update_direct_mode(self._window.is_direct_mode())

    def update_state(self, listening: bool) -> None:
        if listening:
            self._toggle_action.setText("\u0412\u044b\u043a\u043b\u044e\u0447\u0438\u0442\u044c \u043f\u0440\u043e\u0441\u043b\u0443\u0448\u0438\u0432\u0430\u043d\u0438\u0435")
        else:
            self._toggle_action.setText("\u0412\u043a\u043b\u044e\u0447\u0438\u0442\u044c \u043f\u0440\u043e\u0441\u043b\u0443\u0448\u0438\u0432\u0430\u043d\u0438\u0435")

    def update_direct_mode(self, enabled: bool) -> None:
        label = "\u0432\u043a\u043b" if enabled else "\u0432\u044b\u043a\u043b"
        self._direct_action.setText(f"\u041a\u043e\u043c\u0430\u043d\u0434\u044b \u0431\u0435\u0437 \"\u0424\u0430\u0437\u0438\": {label}")

    def show_message(self, title: str, message: str) -> None:
        self._tray.showMessage(title, message)

    def _open_window(self) -> None:
        self._window.showNormal()
        self._window.raise_()
        self._window.activateWindow()

    def _quick_timer(self) -> None:
        prompt = "\u0424\u0440\u0430\u0437\u0430 \u0442\u0430\u0439\u043c\u0435\u0440\u0430 (\u043d\u0430 5 \u043c\u0438\u043d\u0443\u0442)"
        text, ok = QInputDialog.getText(self._window, "\u0422\u0430\u0439\u043c\u0435\u0440", prompt)
        if not ok or not text:
            return
        seconds, name = parse_timer_request(text)
        if not seconds:
            self._window.add_history("\u041d\u0435 \u0441\u043c\u043e\u0433 \u0440\u0430\u0437\u043e\u0431\u0440\u0430\u0442\u044c \u0432\u0440\u0435\u043c\u044f")
            return
        self._window.timer_manager().add_timer(seconds, name)
        label = name or "\u0442\u0430\u0439\u043c\u0435\u0440"
        self._window.add_history(f"\u0422\u0430\u0439\u043c\u0435\u0440 {label} \u0437\u0430\u043f\u0443\u0449\u0435\u043d")

    def _on_activate(self, reason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self._open_window()
