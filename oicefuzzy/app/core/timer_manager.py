import re
import time
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, QTimer, Signal

from app.core.utils import normalize_text, format_duration


@dataclass
class TimerItem:
    id: str
    name: str | None
    duration_sec: int
    remaining_sec: int
    status: str
    end_time: float | None


class TimerManager(QObject):
    timers_updated = Signal(list)
    timer_finished = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._timers: Dict[str, TimerItem] = {}
        self._ticker = QTimer(self)
        self._ticker.setInterval(1000)
        self._ticker.timeout.connect(self._tick)
        self._ticker.start()

    def add_timer(self, duration_sec: int, name: Optional[str] = None) -> TimerItem:
        duration_sec = max(1, int(duration_sec))
        timer_id = uuid.uuid4().hex
        end_time = time.monotonic() + duration_sec
        timer = TimerItem(
            id=timer_id,
            name=name,
            duration_sec=duration_sec,
            remaining_sec=duration_sec,
            status="running",
            end_time=end_time,
        )
        self._timers[timer_id] = timer
        self._emit_update()
        return timer

    def cancel_timer(self, timer_id: str) -> bool:
        if timer_id in self._timers:
            del self._timers[timer_id]
            self._emit_update()
            return True
        return False

    def cancel_by_name(self, name: str) -> bool:
        normalized = normalize_text(name)
        for timer_id, timer in list(self._timers.items()):
            if normalize_text(timer.name or "") == normalized:
                del self._timers[timer_id]
                self._emit_update()
                return True
        return False

    def pause_timer(self, timer_id: str) -> bool:
        timer = self._timers.get(timer_id)
        if not timer or timer.status != "running":
            return False
        timer.remaining_sec = max(0, int((timer.end_time or time.monotonic()) - time.monotonic()))
        timer.end_time = None
        timer.status = "paused"
        self._emit_update()
        return True

    def resume_timer(self, timer_id: str) -> bool:
        timer = self._timers.get(timer_id)
        if not timer or timer.status != "paused":
            return False
        timer.end_time = time.monotonic() + timer.remaining_sec
        timer.status = "running"
        self._emit_update()
        return True

    def list_timers(self) -> List[TimerItem]:
        return list(self._timers.values())

    def describe_status(self) -> str:
        if not self._timers:
            return "\u041d\u0435\u0442 \u0430\u043a\u0442\u0438\u0432\u043d\u044b\u0445 \u0442\u0430\u0439\u043c\u0435\u0440\u043e\u0432"
        items = sorted(self._timers.values(), key=lambda t: t.remaining_sec)
        next_timer = items[0]
        name = next_timer.name or "\u0442\u0430\u0439\u043c\u0435\u0440"
        remaining = format_duration(next_timer.remaining_sec)
        return f"\u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c {remaining} \u0434\u043e {name}"

    def _tick(self) -> None:
        if not self._timers:
            return
        now = time.monotonic()
        finished: List[TimerItem] = []
        for timer in list(self._timers.values()):
            if timer.status == "running" and timer.end_time is not None:
                remaining = int(timer.end_time - now)
                timer.remaining_sec = max(0, remaining)
                if timer.remaining_sec <= 0:
                    timer.status = "finished"
                    finished.append(timer)
        for timer in finished:
            self._timers.pop(timer.id, None)
            self.timer_finished.emit(timer)
        if finished or self._timers:
            self._emit_update()

    def _emit_update(self) -> None:
        timers = sorted(self._timers.values(), key=lambda t: t.remaining_sec)
        self.timers_updated.emit(timers)


def parse_timer_request(text: str) -> Tuple[int | None, str | None]:
    if not text:
        return None, None
    raw = text.strip()
    name = None
    match = re.search(r'"([^"]+)"', raw)
    if match:
        name = match.group(1).strip()
        raw = raw.replace(match.group(0), " ")
    else:
        parts = raw.split("\u043d\u0430", 1)
        if len(parts) == 2 and not raw.strip().startswith("\u043d\u0430"):
            possible_name = parts[0].strip()
            if possible_name and not re.search(r"\d", possible_name):
                possible_norm = normalize_text(possible_name)
                if not re.search(
                    r"\b(\u0442\u0430\u0439\u043c\u0435\u0440|\u043f\u043e\u0441\u0442\u0430\u0432\u044c|\u043f\u043e\u0441\u0442\u0430\u0432\u0438\u0442\u044c|\u0437\u0430\u0441\u0435\u043a\u0438|\u043d\u0430\u043f\u043e\u043c\u043d\u0438|\u043d\u0430\u043f\u043e\u043c\u043d\u0438\u0442\u044c)\b",
                    possible_norm,
                ):
                    name = possible_name
                    raw = "\u043d\u0430" + parts[1]
    cleaned = normalize_text(raw)
    if not cleaned:
        return None, name
    cleaned = cleaned.replace("\u0447\u0435\u0440\u0435\u0437", " ")
    cleaned = _replace_number_words(cleaned)
    total_seconds = 0
    matches = re.findall(
        r"(\d+(?:[\.,]\d+)?)\s*(\u0447\u0430\u0441(?:\u0430|\u043e\u0432)?|\u043c\u0438\u043d\u0443\u0442(?:\u0430|\u044b)?|\u0441\u0435\u043a\u0443\u043d\u0434(?:\u0430|\u044b)?)",
        cleaned,
    )
    for value, unit in matches:
        number = float(value.replace(",", "."))
        if unit.startswith("\u0447\u0430\u0441"):
            total_seconds += int(number * 3600)
        elif unit.startswith("\u043c\u0438\u043d"):
            total_seconds += int(number * 60)
        elif unit.startswith("\u0441\u0435\u043a"):
            total_seconds += int(number)
    if total_seconds == 0:
        fallback = re.search(r"\d+(?:[\.,]\d+)?", cleaned)
        if fallback:
            total_seconds = int(float(fallback.group(0).replace(",", ".")) * 60)
    if total_seconds > 0 and not name:
        name_guess = re.sub(
            r"\d+(?:[\.,]\d+)?\s*(\u0447\u0430\u0441(?:\u0430|\u043e\u0432)?|\u043c\u0438\u043d\u0443\u0442(?:\u0430|\u044b)?|\u0441\u0435\u043a\u0443\u043d\u0434(?:\u0430|\u044b)?)",
            " ",
            cleaned,
        )
        name_guess = re.sub(
            r"\b(\u043d\u0430|\u0447\u0435\u0440\u0435\u0437|\u0442\u0430\u0439\u043c\u0435\u0440|\u043f\u043e\u0441\u0442\u0430\u0432\u044c|\u043f\u043e\u0441\u0442\u0430\u0432\u0438\u0442\u044c|\u0437\u0430\u0441\u0435\u043a\u0438|\u043d\u0430\u043f\u043e\u043c\u043d\u0438|\u043d\u0430\u043f\u043e\u043c\u043d\u0438\u0442\u044c)\b",
            " ",
            name_guess,
        )
        name_guess = normalize_text(name_guess)
        if name_guess:
            name = name_guess
    if total_seconds <= 0:
        return None, name
    return total_seconds, name


def _replace_number_words(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"\b\u043f\u043e\u043b\s*\u0447\u0430\u0441\u0430?\b", "30 \u043c\u0438\u043d\u0443\u0442", text)
    text = re.sub(r"\b\u043f\u043e\u043b\u0447\u0430\u0441\u0430\b", "30 \u043c\u0438\u043d\u0443\u0442", text)
    text = re.sub(r"\b\u043f\u043e\u043b\u0442\u043e\u0440\u0430\s*\u0447\u0430\u0441\u0430?\b", "90 \u043c\u0438\u043d\u0443\u0442", text)
    text = re.sub(r"\b\u043f\u043e\u043b\u0442\u043e\u0440\u044b\s*\u0447\u0430\u0441\u0430?\b", "90 \u043c\u0438\u043d\u0443\u0442", text)
    ones = {
        "\u043d\u043e\u043b\u044c": 0,
        "\u043e\u0434\u0438\u043d": 1,
        "\u043e\u0434\u043d\u0430": 1,
        "\u043e\u0434\u043d\u043e": 1,
        "\u0434\u0432\u0430": 2,
        "\u0434\u0432\u0435": 2,
        "\u0442\u0440\u0438": 3,
        "\u0447\u0435\u0442\u044b\u0440\u0435": 4,
        "\u043f\u044f\u0442\u044c": 5,
        "\u0448\u0435\u0441\u0442\u044c": 6,
        "\u0441\u0435\u043c\u044c": 7,
        "\u0432\u043e\u0441\u0435\u043c\u044c": 8,
        "\u0434\u0435\u0432\u044f\u0442\u044c": 9,
        "\u0434\u0435\u0441\u044f\u0442\u044c": 10,
        "\u043e\u0434\u0438\u043d\u043d\u0430\u0434\u0446\u0430\u0442\u044c": 11,
        "\u0434\u0432\u0435\u043d\u0430\u0434\u0446\u0430\u0442\u044c": 12,
        "\u0442\u0440\u0438\u043d\u0430\u0434\u0446\u0430\u0442\u044c": 13,
        "\u0447\u0435\u0442\u044b\u0440\u043d\u0430\u0434\u0446\u0430\u0442\u044c": 14,
        "\u043f\u044f\u0442\u043d\u0430\u0434\u0446\u0430\u0442\u044c": 15,
        "\u0448\u0435\u0441\u0442\u043d\u0430\u0434\u0446\u0430\u0442\u044c": 16,
        "\u0441\u0435\u043c\u043d\u0430\u0434\u0446\u0430\u0442\u044c": 17,
        "\u0432\u043e\u0441\u0435\u043c\u043d\u0430\u0434\u0446\u0430\u0442\u044c": 18,
        "\u0434\u0435\u0432\u044f\u0442\u043d\u0430\u0434\u0446\u0430\u0442\u044c": 19,
    }
    tens = {
        "\u0434\u0432\u0430\u0434\u0446\u0430\u0442\u044c": 20,
        "\u0442\u0440\u0438\u0434\u0446\u0430\u0442\u044c": 30,
        "\u0441\u043e\u0440\u043e\u043a": 40,
        "\u043f\u044f\u0442\u044c\u0434\u0435\u0441\u044f\u0442": 50,
        "\u0448\u0435\u0441\u0442\u044c\u0434\u0435\u0441\u044f\u0442": 60,
        "\u0441\u0435\u043c\u044c\u0434\u0435\u0441\u044f\u0442": 70,
        "\u0432\u043e\u0441\u0435\u043c\u044c\u0434\u0435\u0441\u044f\u0442": 80,
        "\u0434\u0435\u0432\u044f\u043d\u043e\u0441\u0442\u043e": 90,
    }
    tokens = text.split()
    output = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in tens:
            value = tens[token]
            consumed = 1
            if i + 1 < len(tokens) and tokens[i + 1] in ones:
                value += ones[tokens[i + 1]]
                consumed = 2
            output.append(str(value))
            i += consumed
            continue
        if token in ones:
            output.append(str(ones[token]))
            i += 1
            continue
        output.append(token)
        i += 1
    return " ".join(output)
