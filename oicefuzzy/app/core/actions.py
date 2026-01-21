import ctypes
import os
import random
import subprocess
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import quote_plus

from app.core.math_eval import MathEvaluator
from app.core.timer_manager import TimerManager, parse_timer_request
from app.core.utils import app_root, expand_path, normalize_text


@dataclass
class ActionResult:
    ok: bool
    log: str
    tts: str | None = None


KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_MENU = 0x12
VK_RETURN = 0x0D
VK_ESCAPE = 0x1B
VK_TAB = 0x09
VK_SNAPSHOT = 0x2C
VK_F4 = 0x73
VK_LWIN = 0x5B
VK_D = 0x44
VK_A = 0x41
VK_C = 0x43
VK_V = 0x56
VK_X = 0x58
VK_S = 0x53
VK_Z = 0x5A

VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_BRIGHTNESS_DOWN = 0xD8
VK_BRIGHTNESS_UP = 0xD9

USER32 = ctypes.WinDLL("user32", use_last_error=True)
USER32.SendInput.argtypes = (ctypes.c_uint, ctypes.c_void_p, ctypes.c_int)
USER32.SendInput.restype = ctypes.c_uint


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("_input",)
    _fields_ = [("type", ctypes.c_ulong), ("_input", _INPUT_UNION)]


def _send_vk(vk: int) -> None:
    USER32.keybd_event(vk, 0, 0, 0)
    USER32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


def _send_hotkey(*vks: int) -> None:
    for vk in vks:
        USER32.keybd_event(vk, 0, 0, 0)
    for vk in reversed(vks):
        USER32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


def _send_text(text: str) -> None:
    if not text:
        return
    for char in text:
        code = ord(char)
        inputs = (INPUT * 2)(
            INPUT(type=1, ki=KEYBDINPUT(0, code, KEYEVENTF_UNICODE, 0, None)),
            INPUT(type=1, ki=KEYBDINPUT(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, None)),
        )
        USER32.SendInput(2, ctypes.byref(inputs[0]), ctypes.sizeof(INPUT))


def _ensure_notes_path() -> Path:
    notes_path = app_root() / "config" / "notes.txt"
    notes_path.parent.mkdir(parents=True, exist_ok=True)
    return notes_path


class ActionDispatcher:
    def __init__(self, targets: Dict[str, str], allowlist: list[Dict[str, Any]], timer_manager: TimerManager) -> None:
        self._targets = targets
        self._allowlist = allowlist
        self._timer_manager = timer_manager
        self._math = MathEvaluator()

    def dispatch(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        action_type = action.get("type", "")
        handler = getattr(self, f"_handle_{action_type}", None)
        if not handler:
            return ActionResult(False, self._text("\u041a\u043e\u043c\u0430\u043d\u0434\u0430 \u043d\u0435 \u0440\u0430\u0441\u043f\u043e\u0437\u043d\u0430\u043d\u0430"))
        return handler(action, params, raw_text)

    def _handle_open_browser(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        ok = webbrowser.open("about:blank")
        if not ok:
            webbrowser.open("https://www.google.com")
        tts = self._format_tts(action, params)
        return ActionResult(True, self._text("\u041e\u0442\u043a\u0440\u044b\u0432\u0430\u044e \u0431\u0440\u0430\u0443\u0437\u0435\u0440"), tts)

    def _handle_open_url(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        url = action.get("url")
        if not url:
            return ActionResult(False, self._text("\u041d\u0435\u0442 URL \u0434\u043b\u044f \u043e\u0442\u043a\u0440\u044b\u0442\u0438\u044f"))
        webbrowser.open(url)
        tts = self._format_tts(action, params)
        log = tts or self._text("\u041e\u0442\u043a\u0440\u044b\u0432\u0430\u044e \u0441\u0430\u0439\u0442")
        return ActionResult(True, log, tts)

    def _handle_open_site(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        site = params.get(action.get("param", ""), "").strip()
        if not site:
            return ActionResult(False, self._text("\u041d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d \u0441\u0430\u0439\u0442"))
        targets_norm = {normalize_text(k): v for k, v in self._targets.items()}
        url = targets_norm.get(normalize_text(site))
        if not url:
            url = site
        if not url.startswith("http"):
            if "." not in url:
                return ActionResult(False, self._text("\u0421\u0430\u0439\u0442 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d"))
            url = f"https://{url}"
        webbrowser.open(url)
        tts = self._format_tts(action, {"site": site})
        return ActionResult(True, self._text(f"\u041e\u0442\u043a\u0440\u044b\u0432\u0430\u044e {site}"), tts)

    def _handle_google_search(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        query = params.get(action.get("param", ""), "").strip()
        if not query:
            return ActionResult(False, self._text("\u041d\u0435\u0442 \u0437\u0430\u043f\u0440\u043e\u0441\u0430 \u0434\u043b\u044f \u043f\u043e\u0438\u0441\u043a\u0430"))
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        webbrowser.open(url)
        tts = self._format_tts(action, {"query": query})
        return ActionResult(True, self._text(f"\u041f\u043e\u0438\u0441\u043a: {query}"), tts)

    def _handle_run_allowlist(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        name = params.get(action.get("param", ""), "").strip()
        if not name:
            name = str(action.get("name", "")).strip()
        if not name:
            return ActionResult(False, self._text("\u041d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u043e \u0447\u0442\u043e \u043e\u0442\u043a\u0440\u044b\u0442\u044c"))
        item = self._find_allow_item(name)
        if not item:
            return ActionResult(False, self._text("\u041d\u0435\u0442 \u0432 allowlist"))
        path = expand_path(item.get("path", ""))
        if not path or not os.path.exists(path):
            return ActionResult(False, self._text("\u041f\u0443\u0442\u044c \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d"))
        item_type = item.get("type", "file")
        executable = bool(item.get("executable", False))
        if item_type == "app" or path.lower().endswith(".exe"):
            if not executable:
                return ActionResult(False, self._text("\u0417\u0430\u043f\u0443\u0441\u043a \u0437\u0430\u043f\u0440\u0435\u0449\u0435\u043d"))
        os.startfile(path)
        return ActionResult(True, self._text(f"\u041e\u0442\u043a\u0440\u044b\u0432\u0430\u044e {name}"), None)

    def _handle_say(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        tts = self._format_tts(action, params) or action.get("text", "")
        log = action.get("log") or tts or self._text("\u041e\u043a")
        return ActionResult(True, log, tts)

    def _handle_joke(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        jokes = [
            "\u0410\u043d\u0435\u043a\u0434\u043e\u0442: \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0438\u0441\u0442\u044b \u043d\u0435 \u043f\u0430\u0434\u0430\u044e\u0442 \u0441 \u043f\u0430\u0440\u0430\u0448\u044e\u0442\u043e\u043c, \u043e\u043d\u0438 \u0434\u0435\u043b\u0430\u044e\u0442 \u0440\u0435\u0437\u0435\u0440\u0432\u043d\u0443\u044e \u043a\u043e\u043f\u0438\u044e.",
            "\u0410\u043d\u0435\u043a\u0434\u043e\u0442: \u0438\u043d\u043e\u0433\u0434\u0430 \u043b\u0443\u0447\u0448\u0435 \u043e\u0442\u043a\u043b\u044e\u0447\u0438\u0442\u044c \u0438 \u0432\u043a\u043b\u044e\u0447\u0438\u0442\u044c \u0441\u043d\u043e\u0432\u0430.",
            "\u0410\u043d\u0435\u043a\u0434\u043e\u0442: \u043c\u043e\u0439 \u043a\u043e\u0442 \u043d\u0435 \u0431\u043e\u0438\u0442\u0441\u044f \u0431\u0430\u0433\u043e\u0432, \u043e\u043d \u0438\u0445 \u043b\u044e\u0431\u0438\u0442.",
        ]
        text = random.choice(jokes)
        return ActionResult(True, text, text)

    def _handle_time_now(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        now = datetime.now()
        text = f"\u0421\u0435\u0439\u0447\u0430\u0441 {now:%H:%M}"
        return ActionResult(True, text, text)

    def _handle_date_today(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        now = datetime.now()
        weekdays = [
            "\u043f\u043e\u043d\u0435\u0434\u0435\u043b\u044c\u043d\u0438\u043a",
            "\u0432\u0442\u043e\u0440\u043d\u0438\u043a",
            "\u0441\u0440\u0435\u0434\u0430",
            "\u0447\u0435\u0442\u0432\u0435\u0440\u0433",
            "\u043f\u044f\u0442\u043d\u0438\u0446\u0430",
            "\u0441\u0443\u0431\u0431\u043e\u0442\u0430",
            "\u0432\u043e\u0441\u043a\u0440\u0435\u0441\u0435\u043d\u044c\u0435",
        ]
        months = [
            "\u044f\u043d\u0432\u0430\u0440\u044f",
            "\u0444\u0435\u0432\u0440\u0430\u043b\u044f",
            "\u043c\u0430\u0440\u0442\u0430",
            "\u0430\u043f\u0440\u0435\u043b\u044f",
            "\u043c\u0430\u044f",
            "\u0438\u044e\u043d\u044f",
            "\u0438\u044e\u043b\u044f",
            "\u0430\u0432\u0433\u0443\u0441\u0442\u0430",
            "\u0441\u0435\u043d\u0442\u044f\u0431\u0440\u044f",
            "\u043e\u043a\u0442\u044f\u0431\u0440\u044f",
            "\u043d\u043e\u044f\u0431\u0440\u044f",
            "\u0434\u0435\u043a\u0430\u0431\u0440\u044f",
        ]
        weekday = weekdays[now.weekday()]
        month = months[now.month - 1]
        text = f"\u0421\u0435\u0433\u043e\u0434\u043d\u044f {weekday}, {now.day} {month}"
        return ActionResult(True, text, text)

    def _handle_volume_up(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        _send_vk(VK_VOLUME_UP)
        return ActionResult(True, "\u0423\u0432\u0435\u043b\u0438\u0447\u0438\u0432\u0430\u044e \u0433\u0440\u043e\u043c\u043a\u043e\u0441\u0442\u044c", "\u0423\u0432\u0435\u043b\u0438\u0447\u0438\u0432\u0430\u044e \u0433\u0440\u043e\u043c\u043a\u043e\u0441\u0442\u044c")

    def _handle_volume_down(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        _send_vk(VK_VOLUME_DOWN)
        return ActionResult(True, "\u0423\u043c\u0435\u043d\u044c\u0448\u0430\u044e \u0433\u0440\u043e\u043c\u043a\u043e\u0441\u0442\u044c", "\u0423\u043c\u0435\u043d\u044c\u0448\u0430\u044e \u0433\u0440\u043e\u043c\u043a\u043e\u0441\u0442\u044c")

    def _handle_volume_max(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        for _ in range(20):
            _send_vk(VK_VOLUME_UP)
        return ActionResult(True, "\u0413\u0440\u043e\u043c\u043a\u043e\u0441\u0442\u044c \u043d\u0430 \u043c\u0430\u043a\u0441\u0438\u043c\u0443\u043c", "\u0413\u0440\u043e\u043c\u043a\u043e\u0441\u0442\u044c \u043d\u0430 \u043c\u0430\u043a\u0441\u0438\u043c\u0443\u043c")

    def _handle_volume_mute(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        _send_vk(VK_VOLUME_MUTE)
        return ActionResult(True, "\u0412\u044b\u043a\u043b\u044e\u0447\u0430\u044e \u0437\u0432\u0443\u043a", "\u0412\u044b\u043a\u043b\u044e\u0447\u0430\u044e \u0437\u0432\u0443\u043a")

    def _handle_volume_unmute(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        _send_vk(VK_VOLUME_UP)
        return ActionResult(True, "\u0412\u043a\u043b\u044e\u0447\u0430\u044e \u0437\u0432\u0443\u043a", "\u0412\u043a\u043b\u044e\u0447\u0430\u044e \u0437\u0432\u0443\u043a")

    def _handle_brightness_up(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        _send_vk(VK_BRIGHTNESS_UP)
        return ActionResult(True, "\u042f\u0440\u0447\u0435", "\u042f\u0440\u0447\u0435")

    def _handle_brightness_down(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        _send_vk(VK_BRIGHTNESS_DOWN)
        return ActionResult(True, "\u0422\u0435\u043c\u043d\u0435\u0435", "\u0422\u0435\u043c\u043d\u0435\u0435")

    def _handle_media_play_pause(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        _send_vk(VK_MEDIA_PLAY_PAUSE)
        return ActionResult(True, "\u041f\u0435\u0440\u0435\u043a\u043b\u044e\u0447\u0430\u044e \u0432\u043e\u0441\u043f\u0440\u043e\u0438\u0437\u0432\u0435\u0434\u0435\u043d\u0438\u0435", "\u041f\u0435\u0440\u0435\u043a\u043b\u044e\u0447\u0430\u044e \u0432\u043e\u0441\u043f\u0440\u043e\u0438\u0437\u0432\u0435\u0434\u0435\u043d\u0438\u0435")

    def _handle_media_next(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        _send_vk(VK_MEDIA_NEXT_TRACK)
        return ActionResult(True, "\u0421\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u0439 \u0442\u0440\u0435\u043a", "\u0421\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u0439 \u0442\u0440\u0435\u043a")

    def _handle_media_prev(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        _send_vk(VK_MEDIA_PREV_TRACK)
        return ActionResult(True, "\u041f\u0440\u0435\u0434\u044b\u0434\u0443\u0449\u0438\u0439 \u0442\u0440\u0435\u043a", "\u041f\u0440\u0435\u0434\u044b\u0434\u0443\u0449\u0438\u0439 \u0442\u0440\u0435\u043a")

    def _handle_show_desktop(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        _send_hotkey(VK_LWIN, VK_D)
        return ActionResult(True, "\u041f\u043e\u043a\u0430\u0437\u044b\u0432\u0430\u044e \u0440\u0430\u0431\u043e\u0447\u0438\u0439 \u0441\u0442\u043e\u043b", "\u041f\u043e\u043a\u0430\u0437\u044b\u0432\u0430\u044e \u0440\u0430\u0431\u043e\u0447\u0438\u0439 \u0441\u0442\u043e\u043b")

    def _handle_close_window(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        _send_hotkey(VK_MENU, VK_F4)
        return ActionResult(True, "\u0417\u0430\u043a\u0440\u044b\u0432\u0430\u044e \u043e\u043a\u043d\u043e", "\u0417\u0430\u043a\u0440\u044b\u0432\u0430\u044e \u043e\u043a\u043d\u043e")

    def _handle_switch_window(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        _send_hotkey(VK_MENU, VK_TAB)
        return ActionResult(True, "\u041f\u0435\u0440\u0435\u043a\u043b\u044e\u0447\u0430\u044e \u043e\u043a\u043d\u043e", "\u041f\u0435\u0440\u0435\u043a\u043b\u044e\u0447\u0430\u044e \u043e\u043a\u043d\u043e")

    def _handle_screenshot(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        _send_hotkey(VK_LWIN, VK_SNAPSHOT)
        return ActionResult(True, "\u0421\u043a\u0440\u0438\u043d\u0448\u043e\u0442 \u0441\u0434\u0435\u043b\u0430\u043d", "\u0421\u043a\u0440\u0438\u043d\u0448\u043e\u0442 \u0441\u0434\u0435\u043b\u0430\u043d")

    def _handle_type_text(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        text = params.get(action.get("param", ""), "").strip()
        if not text:
            return ActionResult(False, "\u041d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d \u0442\u0435\u043a\u0441\u0442")
        delay_ms = int(action.get("delay_ms", 120))
        time.sleep(max(0, delay_ms) / 1000.0)
        _send_text(text)
        return ActionResult(True, "\u041d\u0430\u0431\u0438\u0440\u0430\u044e \u0442\u0435\u043a\u0441\u0442", "\u041d\u0430\u0431\u0438\u0440\u0430\u044e \u0442\u0435\u043a\u0441\u0442")

    def _handle_hotkey(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        keys = action.get("keys", [])
        vk_map = {
            "ctrl": VK_CONTROL,
            "shift": VK_SHIFT,
            "alt": VK_MENU,
            "win": VK_LWIN,
            "a": VK_A,
            "c": VK_C,
            "v": VK_V,
            "x": VK_X,
            "s": VK_S,
            "z": VK_Z,
            "enter": VK_RETURN,
            "esc": VK_ESCAPE,
            "tab": VK_TAB,
        }
        vks = [vk_map[k] for k in keys if k in vk_map]
        if not vks:
            return ActionResult(False, "\u041d\u0435\u0442 \u043a\u043b\u0430\u0432\u0438\u0448")
        _send_hotkey(*vks)
        return ActionResult(True, "\u0412\u044b\u043f\u043e\u043b\u043d\u0435\u043d\u043e", "\u0412\u044b\u043f\u043e\u043b\u043d\u0435\u043d\u043e")

    def _handle_note_add(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        text = params.get(action.get("param", ""), "").strip()
        if not text:
            return ActionResult(False, "\u041d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d \u0442\u0435\u043a\u0441\u0442 \u0437\u0430\u043c\u0435\u0442\u043a\u0438")
        notes_path = _ensure_notes_path()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        with notes_path.open("a", encoding="utf-8") as handle:
            handle.write(f"[{timestamp}] {text}\n")
        return ActionResult(True, "\u0417\u0430\u043c\u0435\u0442\u043a\u0430 \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0430", "\u0417\u0430\u043c\u0435\u0442\u043a\u0430 \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0430")

    def _handle_note_list(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        notes_path = _ensure_notes_path()
        if not notes_path.exists():
            return ActionResult(True, "\u041d\u0435\u0442 \u0437\u0430\u043c\u0435\u0442\u043e\u043a", "\u041d\u0435\u0442 \u0437\u0430\u043c\u0435\u0442\u043e\u043a")
        lines = [line.strip() for line in notes_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            return ActionResult(True, "\u041d\u0435\u0442 \u0437\u0430\u043c\u0435\u0442\u043e\u043a", "\u041d\u0435\u0442 \u0437\u0430\u043c\u0435\u0442\u043e\u043a")
        latest = lines[-5:]
        text = "\u0412\u043e\u0442 \u0432\u0430\u0448\u0438 \u0437\u0430\u043c\u0435\u0442\u043a\u0438: " + "; ".join(latest)
        return ActionResult(True, text, text)

    def _handle_system_shutdown(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        subprocess.Popen(["shutdown", "/s", "/t", "0"], shell=False)
        text = "\u0412\u044b\u043a\u043b\u044e\u0447\u0430\u044e \u043a\u043e\u043c\u043f\u044c\u044e\u0442\u0435\u0440"
        return ActionResult(True, text, text)

    def _handle_system_restart(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        subprocess.Popen(["shutdown", "/r", "/t", "0"], shell=False)
        text = "\u041f\u0435\u0440\u0435\u0437\u0430\u0433\u0440\u0443\u0436\u0430\u044e \u043a\u043e\u043c\u043f\u044c\u044e\u0442\u0435\u0440"
        return ActionResult(True, text, text)

    def _handle_system_sleep(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], shell=False)
        text = "\u041f\u0435\u0440\u0435\u0432\u043e\u0436\u0443 \u0432 \u0441\u043f\u044f\u0449\u0438\u0439 \u0440\u0435\u0436\u0438\u043c"
        return ActionResult(True, text, text)

    def _handle_system_lock(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        USER32.LockWorkStation()
        text = "\u0411\u043b\u043e\u043a\u0438\u0440\u0443\u044e \u043a\u043e\u043c\u043f\u044c\u044e\u0442\u0435\u0440"
        return ActionResult(True, text, text)

    def _handle_battery_status(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        class SYSTEM_POWER_STATUS(ctypes.Structure):
            _fields_ = [
                ("ACLineStatus", ctypes.c_byte),
                ("BatteryFlag", ctypes.c_byte),
                ("BatteryLifePercent", ctypes.c_byte),
                ("SystemStatusFlag", ctypes.c_byte),
                ("BatteryLifeTime", ctypes.c_ulong),
                ("BatteryFullLifeTime", ctypes.c_ulong),
            ]

        status = SYSTEM_POWER_STATUS()
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        ok = kernel32.GetSystemPowerStatus(ctypes.byref(status))
        if not ok:
            text = "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043f\u043e\u043b\u0443\u0447\u0438\u0442\u044c \u0434\u0430\u043d\u043d\u044b\u0435 \u043e \u0431\u0430\u0442\u0430\u0440\u0435\u0435"
            return ActionResult(False, text, text)
        percent = int(status.BatteryLifePercent)
        if percent < 0 or percent > 100:
            text = "\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u044b\u0439 \u0443\u0440\u043e\u0432\u0435\u043d\u044c \u0437\u0430\u0440\u044f\u0434\u0430"
            return ActionResult(True, text, text)
        text = f"\u0417\u0430\u0440\u044f\u0434 \u0431\u0430\u0442\u0430\u0440\u0435\u0438 {percent}%"
        return ActionResult(True, text, text)

    def _handle_wiki_search(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        topic = params.get(action.get("param", ""), "").strip()
        if not topic:
            return ActionResult(False, "\u041d\u0435\u0442 \u0442\u0435\u043c\u044b \u0434\u043b\u044f \u043f\u043e\u0438\u0441\u043a\u0430")
        url = f"https://ru.wikipedia.org/wiki/Special:Search?search={quote_plus(topic)}"
        webbrowser.open(url)
        tts = f"\u0418\u0449\u0443 \u0432 Wikipedia: {topic}"
        return ActionResult(True, tts, tts)

    def _handle_translate(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        text = params.get(action.get("param", ""), "").strip()
        if not text:
            return ActionResult(False, "\u041d\u0435\u0442 \u0442\u0435\u043a\u0441\u0442\u0430 \u0434\u043b\u044f \u043f\u0435\u0440\u0435\u0432\u043e\u0434\u0430")
        url = f"https://translate.google.com/?sl=auto&tl=ru&text={quote_plus(text)}&op=translate"
        webbrowser.open(url)
        tts = f"\u041f\u0435\u0440\u0435\u0432\u043e\u0436\u0443: {text}"
        return ActionResult(True, tts, tts)

    def _handle_weather_search(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        place = params.get(action.get("param", ""), "").strip()
        if place:
            query = f"\u043f\u043e\u0433\u043e\u0434\u0430 {place}"
        else:
            query = "\u043f\u043e\u0433\u043e\u0434\u0430"
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        webbrowser.open(url)
        tts = (
            f"\u041f\u043e\u043a\u0430\u0437\u044b\u0432\u0430\u044e \u043f\u043e\u0433\u043e\u0434\u0443 {place}"
            if place
            else "\u041f\u043e\u043a\u0430\u0437\u044b\u0432\u0430\u044e \u043f\u043e\u0433\u043e\u0434\u0443"
        )
        return ActionResult(True, tts, tts)

    def _handle_timer_set(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        payload = params.get(action.get("param", ""), raw_text)
        seconds, name = parse_timer_request(payload)
        if not seconds:
            return ActionResult(False, self._text("\u041d\u0435 \u0441\u043c\u043e\u0433 \u0440\u0430\u0437\u043e\u0431\u0440\u0430\u0442\u044c \u0432\u0440\u0435\u043c\u044f"))
        self._timer_manager.add_timer(seconds, name)
        label = name or "\u0442\u0430\u0439\u043c\u0435\u0440"
        human = self._format_duration(seconds)
        tts = f"\u0422\u0430\u0439\u043c\u0435\u0440 {label} \u043d\u0430 {human}"
        return ActionResult(True, self._text(f"\u0422\u0430\u0439\u043c\u0435\u0440 {label} \u0437\u0430\u043f\u0443\u0449\u0435\u043d"), tts)

    def _handle_timer_status(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        status = self._timer_manager.describe_status()
        return ActionResult(True, status, status)

    def _handle_timer_cancel(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        name = params.get(action.get("param", ""), "").strip()
        if name:
            if self._timer_manager.cancel_by_name(name):
                text = f"\u0422\u0430\u0439\u043c\u0435\u0440 {name} \u043e\u0442\u043c\u0435\u043d\u0435\u043d"
                return ActionResult(True, text, text)
            return ActionResult(False, self._text("\u0422\u0430\u0439\u043c\u0435\u0440 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d"))
        timers = self._timer_manager.list_timers()
        if len(timers) == 1:
            timer = timers[0]
            self._timer_manager.cancel_timer(timer.id)
            text = "\u0422\u0430\u0439\u043c\u0435\u0440 \u043e\u0442\u043c\u0435\u043d\u0435\u043d"
            return ActionResult(True, text, text)
        if not timers:
            return ActionResult(False, self._text("\u041d\u0435\u0442 \u0430\u043a\u0442\u0438\u0432\u043d\u044b\u0445 \u0442\u0430\u0439\u043c\u0435\u0440\u043e\u0432"))
        return ActionResult(False, self._text("\u0423\u0442\u043e\u0447\u043d\u0438\u0442\u0435, \u043a\u0430\u043a\u043e\u0439 \u0442\u0430\u0439\u043c\u0435\u0440 \u043e\u0442\u043c\u0435\u043d\u0438\u0442\u044c"))

    def _handle_math_eval(self, action: Dict[str, Any], params: Dict[str, str], raw_text: str) -> ActionResult:
        expr = params.get(action.get("param", ""), raw_text)
        result = self._math.evaluate(expr)
        if not result.ok or result.value is None:
            return ActionResult(False, self._text("\u041d\u0435 \u0441\u043c\u043e\u0433 \u043f\u043e\u0441\u0447\u0438\u0442\u0430\u0442\u044c"))
        formatted = self._math.format_value(result.value)
        log = f"\u041e\u0442\u0432\u0435\u0442: {formatted}"
        return ActionResult(True, log, log)

    def _format_tts(self, action: Dict[str, Any], params: Dict[str, str]) -> str | None:
        template = action.get("tts")
        if not template:
            return None
        try:
            return template.format(**params)
        except Exception:
            return template

    def _find_allow_item(self, name: str) -> Optional[Dict[str, Any]]:
        wanted = normalize_text(name)
        for item in self._allowlist:
            if normalize_text(item.get("name", "")) == wanted:
                return item
        return None

    @staticmethod
    def _format_duration(seconds: int) -> str:
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        parts = []
        if hours:
            parts.append(f"{hours} \u0447\u0430\u0441")
        if minutes:
            parts.append(f"{minutes} \u043c\u0438\u043d\u0443\u0442")
        if secs:
            parts.append(f"{secs} \u0441\u0435\u043a\u0443\u043d\u0434")
        if not parts:
            parts.append(f"{secs} \u0441\u0435\u043a\u0443\u043d\u0434")
        return " ".join(parts)

    @staticmethod
    def _text(text: str) -> str:
        return text
