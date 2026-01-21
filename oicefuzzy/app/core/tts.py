import queue
import threading
from typing import Optional

import pyttsx3


class TtsEngine:
    def __init__(self, enabled: bool = True, volume: float = 1.0, rate: int = 180) -> None:
        self._enabled = enabled
        self._volume = volume
        self._rate = rate
        self._queue: queue.Queue[str] = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._running = True
        self._engine: Optional[pyttsx3.Engine] = None
        self._thread.start()

    def _run(self) -> None:
        self._engine = pyttsx3.init()
        self._apply_settings()
        while self._running:
            try:
                text = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if not text or not self._enabled:
                continue
            try:
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception:
                continue

    def _apply_settings(self) -> None:
        if not self._engine:
            return
        self._engine.setProperty("volume", max(0.0, min(1.0, self._volume)))
        self._engine.setProperty("rate", int(self._rate))

    def update(self, enabled: bool | None = None, volume: float | None = None, rate: int | None = None) -> None:
        if enabled is not None:
            self._enabled = enabled
        if volume is not None:
            self._volume = volume
        if rate is not None:
            self._rate = rate
        self._apply_settings()

    def speak(self, text: str) -> None:
        if not text:
            return
        self._queue.put(text)

    def stop(self) -> None:
        self._running = False
        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass
