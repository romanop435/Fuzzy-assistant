from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from app.core.config import ConfigStore
from app.core.stt import SpeechListener


class SettingsDialog(QDialog):
    def __init__(self, config: ConfigStore, listener: SpeechListener, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._listener = listener
        self.setWindowTitle("\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438")
        self.setModal(True)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.mic_combo = QComboBox()
        self.mic_combo.addItem("\u041f\u043e \u0443\u043c\u043e\u043b\u0447\u0430\u043d\u0438\u044e", userData=None)
        for device in SpeechListener.list_input_devices():
            self.mic_combo.addItem(device["name"], userData=device["index"])

        device_index = self._config.get_setting("stt", "device_index", default=None)
        for idx in range(self.mic_combo.count()):
            if self.mic_combo.itemData(idx) == device_index:
                self.mic_combo.setCurrentIndex(idx)
                break

        self.tts_enabled = QCheckBox()
        self.tts_enabled.setChecked(self._config.get_setting("tts", "enabled", default=True))

        self.tts_volume = QDoubleSpinBox()
        self.tts_volume.setRange(0.0, 1.0)
        self.tts_volume.setSingleStep(0.05)
        self.tts_volume.setValue(float(self._config.get_setting("tts", "volume", default=0.9)))

        self.tts_rate = QSpinBox()
        self.tts_rate.setRange(80, 260)
        self.tts_rate.setValue(int(self._config.get_setting("tts", "rate", default=180)))

        self.command_timeout = QSpinBox()
        self.command_timeout.setRange(3, 12)
        self.command_timeout.setValue(int(self._config.get_setting("stt", "command_timeout_sec", default=8)))

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Dark", userData="dark")
        self.theme_combo.addItem("Light", userData="light")
        current_theme = self._config.get_setting("ui", "theme", default="dark")
        for idx in range(self.theme_combo.count()):
            if self.theme_combo.itemData(idx) == current_theme:
                self.theme_combo.setCurrentIndex(idx)
                break

        self.overlay_enabled = QCheckBox()
        self.overlay_enabled.setChecked(self._config.get_setting("ui", "overlay_enabled", default=False))

        self.config_path_label = QLabel(self._config.config_dir_path())
        self.config_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        open_button = QPushButton("\u041e\u0442\u043a\u0440\u044b\u0442\u044c")
        open_button.clicked.connect(self._open_config_folder)
        config_row = QHBoxLayout()
        config_row.addWidget(self.config_path_label, 1)
        config_row.addWidget(open_button)

        form.addRow("\u041c\u0438\u043a\u0440\u043e\u0444\u043e\u043d", self.mic_combo)
        form.addRow("TTS \u0432\u043a\u043b\u044e\u0447\u0435\u043d", self.tts_enabled)
        form.addRow("TTS \u0433\u0440\u043e\u043c\u043a\u043e\u0441\u0442\u044c", self.tts_volume)
        form.addRow("TTS \u0441\u043a\u043e\u0440\u043e\u0441\u0442\u044c", self.tts_rate)
        form.addRow("\u0422\u0430\u0439\u043c\u0430\u0443\u0442 \u043a\u043e\u043c\u0430\u043d\u0434\u044b (\u0441)", self.command_timeout)
        form.addRow("\u0422\u0435\u043c\u0430", self.theme_combo)
        form.addRow("\u041e\u0432\u0435\u0440\u043b\u0435\u0439 \u0442\u0435\u043a\u0441\u0442\u0430", self.overlay_enabled)
        form.addRow("\u041f\u0430\u043f\u043a\u0430 \u043a\u043e\u043d\u0444\u0438\u0433\u043e\u0432", config_row)

        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _open_config_folder(self) -> None:
        from app.core.utils import expand_path
        import os

        path = expand_path(self._config.config_dir_path())
        os.startfile(path)

    def values(self) -> dict:
        return {
            "device_index": self.mic_combo.currentData(),
            "tts_enabled": self.tts_enabled.isChecked(),
            "tts_volume": float(self.tts_volume.value()),
            "tts_rate": int(self.tts_rate.value()),
            "command_timeout_sec": int(self.command_timeout.value()),
            "theme": self.theme_combo.currentData(),
            "overlay_enabled": self.overlay_enabled.isChecked(),
        }
