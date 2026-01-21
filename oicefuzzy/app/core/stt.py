import json
import re
import queue
import threading
import time
from typing import Optional

import sounddevice as sd
from PySide6.QtCore import QObject, Signal
from vosk import KaldiRecognizer, Model

from app.core.utils import normalize_text


class SpeechListener(QObject):
    status_changed = Signal(str)
    partial_text = Signal(str)
    command_ready = Signal(str)
    error = Signal(str)
    wake_detected = Signal()

    def __init__(self, model_path: str, wake_word: str, sample_rate: int = 16000) -> None:
        super().__init__()
        self._model_path = model_path
        self._wake_words = self._split_wake_words(wake_word)
        self._sample_rate = sample_rate
        self._command_timeout_sec = 8
        self._silence_timeout_ms = 1200
        self._device_index: Optional[int] = None
        self._debug_console = False
        self._direct_mode = False
        self._model: Optional[Model] = None
        self._recognizer: Optional[KaldiRecognizer] = None
        self._audio_queue: queue.Queue[bytes] = queue.Queue()
        self._running = False
        self._worker: Optional[threading.Thread] = None
        self._stream: Optional[sd.RawInputStream] = None
        self._mode = "idle"
        self._command_deadline = 0.0
        self._last_voice_time = 0.0
        self._heard_speech = False
        self._command_parts: list[str] = []
        self._last_partial = ""
        self._rms_threshold = 500

    def configure(
        self,
        command_timeout_sec: int,
        silence_timeout_ms: int,
        device_index: Optional[int],
        debug_console: Optional[bool] = None,
    ) -> None:
        self._command_timeout_sec = command_timeout_sec
        self._silence_timeout_ms = silence_timeout_ms
        self._device_index = device_index
        if debug_console is not None:
            self._debug_console = bool(debug_console)

    def set_direct_mode(self, enabled: bool) -> None:
        self._direct_mode = bool(enabled)
        if not self._running:
            return
        if self._direct_mode:
            self._enter_command_mode(emit_wake=False)
        else:
            self._mode = "idle"
            self._status("listening")

    def start(self) -> None:
        if self._running:
            return
        try:
            if not self._model:
                self._model = Model(self._model_path)
            self._recognizer = KaldiRecognizer(self._model, self._sample_rate)
        except Exception as exc:
            self.error.emit(str(exc))
            return
        self._running = True
        self._mode = "idle"
        self._status("listening")
        if self._direct_mode:
            self._enter_command_mode(emit_wake=False)
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def stop(self) -> None:
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
        self._stream = None
        self._status("idle")

    def _run(self) -> None:
        def callback(indata, frames, time_info, status):
            if status:
                pass
            self._audio_queue.put(bytes(indata))

        try:
            self._stream = sd.RawInputStream(
                samplerate=self._sample_rate,
                blocksize=8000,
                dtype="int16",
                channels=1,
                callback=callback,
                device=self._device_index,
            )
            self._stream.start()
        except Exception as exc:
            self.error.emit(str(exc))
            self._running = False
            return

        while self._running:
            try:
                data = self._audio_queue.get(timeout=0.2)
            except queue.Empty:
                self._check_command_timeout()
                continue
            self._process_audio(data)
            self._check_command_timeout()

    def _process_audio(self, data: bytes) -> None:
        if not self._recognizer:
            return
        rms = self._calculate_rms(data)
        now = time.monotonic()
        if rms > self._rms_threshold:
            self._last_voice_time = now
            if not self._heard_speech:
                self._command_deadline = now + self._command_timeout_sec
            self._heard_speech = True
        if self._recognizer.AcceptWaveform(data):
            result = json.loads(self._recognizer.Result())
            text = result.get("text", "")
            if self._debug_console and text:
                print(f"[final:{self._mode}] {text}", flush=True)
            self._handle_text(text, is_final=True)
        else:
            partial = json.loads(self._recognizer.PartialResult()).get("partial", "")
            if self._debug_console and partial:
                print(f"[partial:{self._mode}] {partial}", flush=True)
            self._handle_text(partial, is_final=False)

    def _handle_text(self, text: str, is_final: bool) -> None:
        cleaned = normalize_text(text)
        if not cleaned:
            return
        if self._mode == "idle":
            if self._wake_words and any(word in cleaned for word in self._wake_words):
                self._enter_command_mode(emit_wake=True)
        elif self._mode == "command":
            self._last_partial = cleaned
            self.partial_text.emit(cleaned)
            if is_final:
                self._command_parts.append(cleaned)

    def _enter_command_mode(self, emit_wake: bool) -> None:
        self._mode = "command"
        self._command_parts = []
        self._last_partial = ""
        self._heard_speech = False
        now = time.monotonic()
        self._command_deadline = now + self._command_timeout_sec
        self._last_voice_time = now
        if self._recognizer:
            try:
                self._recognizer.Reset()
            except Exception:
                pass
        if emit_wake:
            self.wake_detected.emit()
        self._status("listening")

    def _finalize_command(self) -> None:
        if self._mode != "command":
            return
        command_text = " ".join(self._command_parts).strip()
        if not command_text and self._last_partial:
            command_text = self._last_partial
        if self._direct_mode and self._running:
            self._enter_command_mode(emit_wake=False)
        else:
            self._mode = "idle"
            if self._running:
                self._status("listening")
            else:
                self._status("idle")
        self._command_parts = []
        self._last_partial = ""
        if command_text:
            self.command_ready.emit(command_text)
        else:
            self.command_ready.emit("")

    def _check_command_timeout(self) -> None:
        if self._mode != "command":
            return
        now = time.monotonic()
        if self._direct_mode and not self._heard_speech:
            return
        if now >= self._command_deadline:
            self._finalize_command()
            return
        if self._heard_speech and (now - self._last_voice_time) * 1000 > self._silence_timeout_ms:
            self._finalize_command()

    def _status(self, value: str) -> None:
        self.status_changed.emit(value)

    def _calculate_rms(self, data: bytes) -> float:
        if not data:
            return 0.0
        count = len(data) // 2
        if count == 0:
            return 0.0
        total = 0
        for i in range(0, len(data), 2):
            sample = int.from_bytes(data[i : i + 2], byteorder="little", signed=True)
            total += sample * sample
        return (total / count) ** 0.5

    @staticmethod
    def list_input_devices() -> list[dict]:
        devices = []
        for idx, device in enumerate(sd.query_devices()):
            if device.get("max_input_channels", 0) > 0:
                devices.append({"index": idx, "name": device.get("name", "")})
        return devices

    @staticmethod
    def _split_wake_words(wake_word: str) -> list[str]:
        if not wake_word:
            return []
        parts = re.split(r"[|,;]+", wake_word)
        words = []
        for part in parts:
            normalized = normalize_text(part)
            if normalized:
                words.append(normalized)
        return words
