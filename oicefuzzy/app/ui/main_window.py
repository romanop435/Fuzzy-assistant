import threading
from datetime import datetime
from typing import Callable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.actions import ActionResult
from app.core.commands import CommandMatcher, CommandProcessor
from app.core.config import ConfigStore
from app.core.stt import SpeechListener
from app.core.timer_manager import TimerItem, TimerManager
from app.core.tts import TtsEngine
from PySide6.QtGui import QPixmap

from app.core.utils import format_duration
from app.ui.overlay import OverlayWindow


class MainWindow(QMainWindow):
    listening_changed = Signal(bool)
    direct_mode_changed = Signal(bool)
    def __init__(
        self,
        config: ConfigStore,
        matcher: CommandMatcher,
        processor: CommandProcessor,
        timer_manager: TimerManager,
        tts: TtsEngine,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._matcher = matcher
        self._processor = processor
        self._timer_manager = timer_manager
        self._tts = tts
        self._listener: Optional[SpeechListener] = None
        self._listening = False
        self._direct_mode = False
        self._notifier: Optional[Callable[[str, str], None]] = None
        self._overlay = OverlayWindow()
        self._force_close = False
        self._close_notice_shown = False
        self._build_ui()
        self._timer_manager.timers_updated.connect(self._update_timers)
        self._timer_manager.timer_finished.connect(self._on_timer_finished)

    def set_listener(self, listener: SpeechListener) -> None:
        self._listener = listener
        listener.status_changed.connect(self._on_status)
        listener.partial_text.connect(self._on_partial)
        listener.command_ready.connect(self._on_command)
        listener.error.connect(self._on_error)
        listener.wake_detected.connect(self._on_wake)

    def set_notifier(self, notifier: Callable[[str, str], None]) -> None:
        self._notifier = notifier

    def _build_ui(self) -> None:
        self.setWindowTitle("\u0424\u0430\u0437\u0438")
        self.setMinimumSize(980, 620)
        root = QWidget()
        self.setCentralWidget(root)

        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        left_panel = QVBoxLayout()
        left_panel.setSpacing(12)

        status_card = self._card()
        status_layout = QHBoxLayout(status_card)
        status_layout.setContentsMargins(16, 16, 16, 16)
        icon_label = QLabel()
        icon_label.setObjectName("Avatar")
        icon_path = self._config.get_setting("ui", "app_icon", default=self._config.get_setting("ui", "splash_icon", default=""))
        if icon_path:
            pixmap = QPixmap(self._config.ensure_resource_path(icon_path))
            if not pixmap.isNull():
                icon_label.setPixmap(pixmap.scaled(46, 46, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        status_layout.addWidget(icon_label)

        title = QLabel("\u0424\u0430\u0437\u0438")
        title.setObjectName("Title")
        status_layout.addWidget(title)
        status_layout.addStretch(1)
        self.status_dot = QLabel()
        self.status_dot.setObjectName("StatusDot")
        self.status_dot.setProperty("status", "idle")
        self.status_text = QLabel("\u041e\u0436\u0438\u0434\u0430\u043d\u0438\u0435")
        self.status_text.setObjectName("StatusText")
        status_layout.addWidget(self.status_dot)
        status_layout.addWidget(self.status_text)
        left_panel.addWidget(status_card)

        control_card = self._card()
        controls = QVBoxLayout(control_card)
        controls.setContentsMargins(16, 16, 16, 16)
        self.listen_button = QPushButton("\u0421\u0442\u0430\u0440\u0442 \u043f\u0440\u043e\u0441\u043b\u0443\u0448\u0438\u0432\u0430\u043d\u0438\u044f")
        self.listen_button.setObjectName("PrimaryButton")
        self.listen_button.clicked.connect(self._toggle_listening)
        self.direct_button = QPushButton("\u041a\u043e\u043c\u0430\u043d\u0434\u044b \u0431\u0435\u0437 \"\u0424\u0430\u0437\u0438\": \u0432\u044b\u043a\u043b")
        self.direct_button.setObjectName("GhostButton")
        self.direct_button.clicked.connect(self._toggle_direct_mode)
        self.test_button = QPushButton("\u0422\u0435\u0441\u0442 \u043c\u0438\u043a\u0440\u043e\u0444\u043e\u043d\u0430")
        self.test_button.clicked.connect(self._test_microphone)
        self.settings_button = QPushButton("\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438")
        self.exit_button = QPushButton("\u0412\u044b\u0445\u043e\u0434")
        self.exit_button.clicked.connect(self.request_exit)
        controls.addWidget(self.listen_button)
        controls.addWidget(self.direct_button)
        controls.addWidget(self.test_button)
        controls.addWidget(self.settings_button)
        controls.addWidget(self.exit_button)
        controls.addStretch(1)
        left_panel.addWidget(control_card)
        left_panel.addStretch(1)

        right_panel = QVBoxLayout()
        right_panel.setSpacing(12)

        history_group = QGroupBox("\u0418\u0441\u0442\u043e\u0440\u0438\u044f \u043a\u043e\u043c\u0430\u043d\u0434")
        history_layout = QVBoxLayout(history_group)
        self.history_list = QListWidget()
        history_layout.addWidget(self.history_list)
        right_panel.addWidget(history_group, 2)

        timer_group = QGroupBox("\u0422\u0430\u0439\u043c\u0435\u0440\u044b")
        timer_layout = QVBoxLayout(timer_group)
        self.timer_table = QTableWidget(0, 4)
        self.timer_table.setHorizontalHeaderLabels([
            "\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435",
            "\u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c",
            "\u0421\u0442\u0430\u0442\u0443\u0441",
            "\u0414\u0435\u0439\u0441\u0442\u0432\u0438\u044f",
        ])
        self.timer_table.horizontalHeader().setStretchLastSection(True)
        self.timer_table.verticalHeader().setVisible(False)
        self.timer_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.timer_table.setSelectionMode(QTableWidget.NoSelection)
        timer_layout.addWidget(self.timer_table)
        right_panel.addWidget(timer_group, 1)

        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 2)

    def _card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        return card

    def _toggle_listening(self) -> None:
        if not self._listener:
            return
        if self._listening:
            self.stop_listening()
        else:
            self.start_listening()

    def toggle_listening(self) -> None:
        self._toggle_listening()

    def is_listening(self) -> bool:
        return self._listening

    def start_listening(self) -> None:
        if not self._listener or self._listening:
            return
        self._listener.start()
        self._listening = True
        self.listen_button.setText("\u0421\u0442\u043e\u043f \u043f\u0440\u043e\u0441\u043b\u0443\u0448\u0438\u0432\u0430\u043d\u0438\u044f")
        self.listening_changed.emit(True)
        self._listener.set_direct_mode(self._direct_mode)

    def stop_listening(self) -> None:
        if not self._listener or not self._listening:
            return
        self._listener.stop()
        self._listening = False
        self.listen_button.setText("\u0421\u0442\u0430\u0440\u0442 \u043f\u0440\u043e\u0441\u043b\u0443\u0448\u0438\u0432\u0430\u043d\u0438\u044f")
        self.listening_changed.emit(False)

    def _toggle_direct_mode(self) -> None:
        self.set_direct_mode(not self._direct_mode)

    def set_direct_mode(self, enabled: bool) -> None:
        self._direct_mode = bool(enabled)
        if self._direct_mode and not self._listening:
            self.start_listening()
        if self._listener:
            self._listener.set_direct_mode(self._direct_mode)
        label = "\u0432\u043a\u043b" if self._direct_mode else "\u0432\u044b\u043a\u043b"
        self.direct_button.setText(f"\u041a\u043e\u043c\u0430\u043d\u0434\u044b \u0431\u0435\u0437 \"\u0424\u0430\u0437\u0438\": {label}")
        self.direct_mode_changed.emit(self._direct_mode)
        status_text = "\u0420\u0435\u0436\u0438\u043c \u0431\u0435\u0437 \u0424\u0430\u0437\u0438 \u0432\u043a\u043b\u044e\u0447\u0435\u043d" if self._direct_mode else "\u0420\u0435\u0436\u0438\u043c \u0431\u0435\u0437 \u0424\u0430\u0437\u0438 \u0432\u044b\u043a\u043b\u044e\u0447\u0435\u043d"
        self._append_history(status_text)

    def toggle_direct_mode(self) -> None:
        self._toggle_direct_mode()

    def is_direct_mode(self) -> bool:
        return self._direct_mode

    def _test_microphone(self) -> None:
        if self._listening:
            QMessageBox.information(self, "\u0424\u0430\u0437\u0438", "\u041e\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u0435 \u043f\u0440\u043e\u0441\u043b\u0443\u0448\u0438\u0432\u0430\u043d\u0438\u0435 \u0434\u043b\u044f \u0442\u0435\u0441\u0442\u0430")
            return
        threading.Thread(target=self._mic_test_worker, daemon=True).start()

    def _mic_test_worker(self) -> None:
        try:
            import sounddevice as sd
            import time

            sample_rate = 16000
            duration = 1.0
            device_index = self._config.get_setting("stt", "device_index", default=None)
            rms = 0.0
            samples = 0
            with sd.RawInputStream(
                samplerate=sample_rate,
                blocksize=4000,
                dtype="int16",
                channels=1,
                device=device_index,
            ) as stream:
                start = time.monotonic()
                while time.monotonic() - start < duration:
                    data, _ = stream.read(4000)
                    if not data:
                        continue
                    total = 0
                    for i in range(0, len(data), 2):
                        sample = int.from_bytes(data[i : i + 2], byteorder="little", signed=True)
                        total += sample * sample
                    count = len(data) // 2
                    if count:
                        rms += (total / count) ** 0.5
                        samples += 1
            if samples:
                rms = rms / samples
            if rms > 300:
                text = "\u041c\u0438\u043a\u0440\u043e\u0444\u043e\u043d \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442"
            else:
                text = "\u0421\u0438\u0433\u043d\u0430\u043b \u0441\u043b\u0430\u0431\u044b\u0439, \u043f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 \u0443\u0440\u043e\u0432\u0435\u043d\u044c"
            self._append_history(text)
        except Exception as exc:
            self._append_history(f"\u041e\u0448\u0438\u0431\u043a\u0430 \u0442\u0435\u0441\u0442\u0430: {exc}")

    def _on_status(self, status: str) -> None:
        labels = {
            "idle": "\u041e\u0436\u0438\u0434\u0430\u043d\u0438\u0435",
            "listening": "\u0421\u043b\u0443\u0448\u0430\u044e",
            "executing": "\u0412\u044b\u043f\u043e\u043b\u043d\u044f\u044e",
        }
        self.status_text.setText(labels.get(status, status))
        self.status_dot.setProperty("status", status)
        self.status_dot.style().unpolish(self.status_dot)
        self.status_dot.style().polish(self.status_dot)

    def _on_partial(self, text: str) -> None:
        if self._config.get_setting("ui", "overlay_enabled", default=False):
            opacity = float(self._config.get_setting("ui", "overlay_opacity", default=0.9))
            self._overlay.show_text(text, opacity)

    def _on_wake(self) -> None:
        try:
            import winsound

            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass
        self._append_history("\u0410\u043a\u0442\u0438\u0432\u0430\u0446\u0438\u044f: \u0424\u0430\u0437\u0438")

    def _on_command(self, text: str) -> None:
        if not text:
            self._append_history("\u041a\u043e\u043c\u0430\u043d\u0434\u0430 \u043d\u0435 \u0440\u0430\u0441\u043f\u043e\u0437\u043d\u0430\u043d\u0430")
            self._tts.speak("\u041a\u043e\u043c\u0430\u043d\u0434\u0430 \u043d\u0435 \u0440\u0430\u0441\u043f\u043e\u0437\u043d\u0430\u043d\u0430")
            return
        self._append_history(f"\u0420\u0430\u0441\u043f\u043e\u0437\u043d\u0430\u043d\u043e: {text}")
        self._on_status("executing")
        result = self._processor.handle(text, self._matcher)
        self._handle_result(result)
        self._on_status("listening" if self._listening else "idle")

    def _handle_result(self, result: ActionResult) -> None:
        self._append_history(result.log)
        if result.tts:
            self._tts.speak(result.tts)
        elif not result.ok:
            self._tts.speak(result.log)

    def _on_error(self, error: str) -> None:
        self._append_history(f"\u041e\u0448\u0438\u0431\u043a\u0430 STT: {error}")

    def _update_timers(self, timers: list[TimerItem]) -> None:
        self.timer_table.setRowCount(len(timers))
        for row, timer in enumerate(timers):
            name = timer.name or "\u2014"
            remaining = format_duration(timer.remaining_sec)
            status = "\u041f\u0430\u0443\u0437\u0430" if timer.status == "paused" else "\u0410\u043a\u0442\u0438\u0432\u043d\u044b\u0439"
            self.timer_table.setItem(row, 0, QTableWidgetItem(name))
            self.timer_table.setItem(row, 1, QTableWidgetItem(remaining))
            self.timer_table.setItem(row, 2, QTableWidgetItem(status))
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)
            pause_button = QPushButton("\u041f\u0430\u0443\u0437\u0430" if timer.status == "running" else "\u041f\u0440\u043e\u0434\u043e\u043b\u0436\u0438\u0442\u044c")
            pause_button.clicked.connect(lambda tid=timer.id, st=timer.status: self._toggle_timer(tid, st))
            cancel_button = QPushButton("\u041e\u0442\u043c\u0435\u043d\u0438\u0442\u044c")
            cancel_button.clicked.connect(lambda tid=timer.id: self._timer_manager.cancel_timer(tid))
            action_layout.addWidget(pause_button)
            action_layout.addWidget(cancel_button)
            self.timer_table.setCellWidget(row, 3, action_widget)

    def _toggle_timer(self, timer_id: str, status: str) -> None:
        if status == "running":
            self._timer_manager.pause_timer(timer_id)
        else:
            self._timer_manager.resume_timer(timer_id)

    def _on_timer_finished(self, timer: TimerItem) -> None:
        label = timer.name or "\u0442\u0430\u0439\u043c\u0435\u0440"
        message = f"\u0422\u0430\u0439\u043c\u0435\u0440 {label} \u0437\u0430\u043a\u043e\u043d\u0447\u0438\u043b\u0441\u044f"
        self._append_history(message)
        try:
            import winsound

            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass
        self._tts.speak("\u0412\u0440\u0435\u043c\u044f \u0432\u044b\u0448\u043b\u043e")
        if self._notifier:
            self._notifier("\u0424\u0430\u0437\u0438", message)

    def _append_history(self, text: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        item = QListWidgetItem(f"[{timestamp}] {text}")
        self.history_list.addItem(item)
        max_entries = int(self._config.get_setting("ui", "log_max_entries", default=200))
        if self.history_list.count() > max_entries:
            self.history_list.takeItem(0)
        self.history_list.scrollToBottom()

    def add_history(self, text: str) -> None:
        self._append_history(text)

    def timer_manager(self) -> TimerManager:
        return self._timer_manager

    def request_exit(self) -> None:
        self._force_close = True
        self.close()

    def closeEvent(self, event) -> None:
        if self._force_close:
            event.accept()
            return
        self.hide()
        event.ignore()
        if not self._close_notice_shown and self._notifier:
            self._notifier("\u0424\u0430\u0437\u0438", "\u041f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0435 \u0441\u0432\u0435\u0440\u043d\u0443\u0442\u043e \u0432 \u0442\u0440\u0435\u0439")
            self._close_notice_shown = True

    def bind_settings_action(self, action: QAction) -> None:
        action.triggered.connect(self.settings_button.click)

    def settings_button_clicked(self, handler) -> None:
        self.settings_button.clicked.connect(handler)
