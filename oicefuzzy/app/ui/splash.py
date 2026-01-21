from PySide6.QtCore import QElapsedTimer, Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QProgressBar, QVBoxLayout, QWidget


class SplashScreen(QWidget):
    finished = Signal()

    def __init__(self, icon_path: str, duration_ms: int = 3500, parent=None) -> None:
        super().__init__(parent)
        self._duration_ms = max(900, int(duration_ms))
        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._tick)
        self._elapsed = QElapsedTimer()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._root = QFrame()
        self._root.setObjectName("SplashRoot")
        self._root.setStyleSheet(
            """
            QFrame#SplashRoot {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0B111A, stop:0.6 #111827, stop:1 #0F172A);
                border-radius: 18px;
                border: 1px solid rgba(148, 163, 184, 0.25);
            }
            QLabel#SplashTitle { color: #F8FAFC; font-size: 22px; font-weight: 700; }
            QLabel#SplashSubtitle { color: #94A3B8; font-size: 12px; }
            QProgressBar {
                background: rgba(15, 23, 42, 0.6);
                border: 1px solid rgba(148, 163, 184, 0.25);
                border-radius: 8px;
                text-align: center;
                color: #CBD5E1;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #38BDF8, stop:1 #14B8A6);
                border-radius: 6px;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.addWidget(self._root)
        layout.setContentsMargins(16, 16, 16, 16)

        inner = QVBoxLayout(self._root)
        inner.setContentsMargins(24, 24, 24, 22)
        inner.setSpacing(14)

        self._icon = QLabel()
        if icon_path:
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                self._icon.setPixmap(pixmap.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self._icon.setAlignment(Qt.AlignCenter)

        title = QLabel("\u0424\u0430\u0437\u0438")
        title.setObjectName("SplashTitle")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("\u0417\u0430\u043f\u0443\u0441\u043a\u0430\u044e \u043f\u043e\u043c\u043e\u0449\u043d\u0438\u043a\u0430...")
        subtitle.setObjectName("SplashSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFixedHeight(18)

        inner.addWidget(self._icon)
        inner.addWidget(title)
        inner.addWidget(subtitle)
        inner.addWidget(self._progress)

        self.resize(360, 320)

    def set_duration_ms(self, duration_ms: int) -> None:
        self._duration_ms = max(900, int(duration_ms))

    def start(self) -> None:
        self._elapsed.start()
        self._timer.start()

    def _tick(self) -> None:
        elapsed = self._elapsed.elapsed()
        progress = int(min(100, (elapsed / self._duration_ms) * 100))
        self._progress.setValue(progress)
        if elapsed >= self._duration_ms:
            self._timer.stop()
            self.finished.emit()
