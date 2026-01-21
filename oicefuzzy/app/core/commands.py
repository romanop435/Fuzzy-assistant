import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.core.actions import ActionDispatcher, ActionResult
from app.core.utils import normalize_text


@dataclass
class MatchResult:
    command_id: str
    action: Dict[str, Any]
    params: Dict[str, str]


class CommandMatcher:
    def __init__(self, commands: List[Dict[str, Any]]) -> None:
        self._compiled = []
        for command in commands:
            command_id = command.get("id", "")
            action = command.get("action", {})
            for pattern in command.get("patterns", []):
                regex, loose = self._compile_pattern(pattern)
                self._compiled.append((command_id, regex, loose, action))

    def match(self, text: str) -> Optional[MatchResult]:
        normalized = normalize_text(text)
        for command_id, regex, loose, action in self._compiled:
            match = regex.match(normalized)
            if match:
                params = {k: v.strip() for k, v in match.groupdict().items() if v}
                return MatchResult(command_id, action, params)
        for command_id, regex, loose, action in self._compiled:
            if not loose:
                continue
            match = loose.search(normalized)
            if match:
                params = {k: v.strip() for k, v in match.groupdict().items() if v}
                return MatchResult(command_id, action, params)
        return None

    def _compile_pattern(self, pattern: str) -> tuple[re.Pattern, re.Pattern | None]:
        if pattern.startswith("regex:"):
            raw = pattern[6:].strip()
            exact = re.compile(raw, re.IGNORECASE)
            loose = None
            if raw.startswith("^") and raw.endswith("$") and len(raw) > 2:
                loose = re.compile(raw[1:-1], re.IGNORECASE)
            return exact, loose
        escaped = re.escape(pattern)
        escaped = re.sub(r"\\\{(\w+)\\\}", r"(?P<\1>.+)", escaped)
        exact_pattern = escaped.replace("\\ ", r"\s+")
        exact = re.compile(rf"^{exact_pattern}$", re.IGNORECASE)
        loose_pattern = exact_pattern.replace(r"\s+", r"\s+.*?")
        loose_pattern = re.sub(r"\(\?P<(\w+)>\.\+\)", r"(?P<\1>.+?)", loose_pattern)
        loose = re.compile(loose_pattern, re.IGNORECASE)
        return exact, loose


class CommandProcessor:
    def __init__(self, dispatcher: ActionDispatcher, wake_word: str) -> None:
        self._dispatcher = dispatcher
        self._wake_words = self._split_wake_words(wake_word)

    def handle(self, text: str, matcher: CommandMatcher) -> ActionResult:
        if not text:
            return ActionResult(False, "\u041a\u043e\u043c\u0430\u043d\u0434\u0430 \u043d\u0435 \u0440\u0430\u0441\u043f\u043e\u0437\u043d\u0430\u043d\u0430")
        cleaned = normalize_text(text)
        for word in self._wake_words:
            if cleaned.startswith(word):
                cleaned = cleaned[len(word) :].strip()
                break
        if not cleaned:
            return ActionResult(False, "\u041a\u043e\u043c\u0430\u043d\u0434\u0430 \u043d\u0435 \u0440\u0430\u0441\u043f\u043e\u0437\u043d\u0430\u043d\u0430")
        match = matcher.match(cleaned)
        if match:
            return self._dispatcher.dispatch(match.action, match.params, text)
        if "\u0442\u0430\u0439\u043c\u0435\u0440" in cleaned:
            return self._dispatcher.dispatch({"type": "timer_set"}, {"payload": cleaned}, text)
        if re.search(r"\d", cleaned):
            return self._dispatcher.dispatch({"type": "math_eval"}, {"expr": cleaned}, text)
        return ActionResult(False, "\u041a\u043e\u043c\u0430\u043d\u0434\u0430 \u043d\u0435 \u0440\u0430\u0441\u043f\u043e\u0437\u043d\u0430\u043d\u0430")

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
