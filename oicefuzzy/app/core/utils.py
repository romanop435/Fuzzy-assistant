import os
import re
import sys
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def resource_path(relative: str) -> str:
    if not relative:
        return ""
    path = Path(relative)
    if path.is_absolute():
        return str(path)
    if getattr(sys, "frozen", False):
        exe_base = Path(sys.executable).resolve().parent
        candidate = exe_base / relative
        if candidate.exists():
            return str(candidate)
    base = getattr(sys, "_MEIPASS", None)
    if base:
        candidate = Path(base) / relative
        if candidate.exists():
            return str(candidate)
    return str(app_root() / relative)


def normalize_text(text: str) -> str:
    if not text:
        return ""
    cleaned = text.strip().lower()
    cleaned = cleaned.replace("\u0451", "\u0435")
    cleaned = re.sub(r"[^\w\s\.,:/\-()]+", " ", cleaned, flags=re.UNICODE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def expand_path(path: str) -> str:
    if not path:
        return ""
    return os.path.expandvars(path)
