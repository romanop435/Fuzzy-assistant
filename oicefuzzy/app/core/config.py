import json
from pathlib import Path
from typing import Any, Dict, List

import yaml

from app.core.utils import app_root, resource_path


class ConfigStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else app_root()
        self.config_dir = self.base_dir / "config"
        self.settings_path = self.config_dir / "settings.yaml"
        self.commands_path = self.config_dir / "commands.yaml"
        self.targets_path = self.config_dir / "targets.yaml"
        self.allowlist_path = self.config_dir / "allowlist.yaml"
        self._settings: Dict[str, Any] = {}
        self._commands: List[Dict[str, Any]] = []
        self._targets: Dict[str, str] = {}
        self._allowlist: List[Dict[str, Any]] = []
        self.reload_all()

    def reload_all(self) -> None:
        self._settings = self._load_yaml(self.settings_path) or {}
        self._commands = (self._load_yaml(self.commands_path) or {}).get("commands", [])
        self._targets = (self._load_yaml(self.targets_path) or {}).get("aliases", {})
        self._allowlist = (self._load_yaml(self.allowlist_path) or {}).get("items", [])

    def _load_yaml(self, path: Path) -> Dict[str, Any] | None:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)

    def save_settings(self) -> None:
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
        with self.settings_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(self._settings, handle, sort_keys=False, allow_unicode=False)

    @property
    def settings(self) -> Dict[str, Any]:
        return self._settings

    @property
    def commands(self) -> List[Dict[str, Any]]:
        return self._commands

    @property
    def targets(self) -> Dict[str, str]:
        return self._targets

    @property
    def allowlist(self) -> List[Dict[str, Any]]:
        return self._allowlist

    def get_setting(self, *keys: str, default: Any = None) -> Any:
        current: Any = self._settings
        for key in keys:
            if not isinstance(current, dict):
                return default
            current = current.get(key)
        if current is None:
            return default
        return current

    def set_setting(self, *keys: str, value: Any) -> None:
        current = self._settings
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def config_dir_path(self) -> str:
        return str(self.config_dir)

    def ensure_resource_path(self, relative: str) -> str:
        return resource_path(relative)

    def dump_state(self) -> str:
        return json.dumps(
            {
                "settings": self._settings,
                "commands": self._commands,
                "targets": self._targets,
                "allowlist": self._allowlist,
            },
            ensure_ascii=True,
            indent=2,
        )
