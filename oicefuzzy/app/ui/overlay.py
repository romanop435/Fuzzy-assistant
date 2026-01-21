from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout


class OverlayWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._label = QLabel("")
        self._label.setStyleSheet(
            "QLabel { background: rgba(10, 10, 10, 180); color: white; padding: 8px 12px; border-radius: 8px; }"
        )
        layout = QVBoxLayout()
        layout.addWidget(self._label)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self._hide_timer = QTimer(self)
        self._hide_timer.setInterval(2500)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    def show_text(self, text: str, opacity: float = 0.9) -> None:
        if not text:
            return
        self.setWindowOpacity(opacity)
        self._label.setText(text)
        self.adjustSize()
        self._move_to_corner()
        self.show()
        self._hide_timer.start()

    def _move_to_corner(self) -> None:
        screen = self.screen().availableGeometry()
        self.move(screen.right() - self.width() - 20, screen.top() + 40)
