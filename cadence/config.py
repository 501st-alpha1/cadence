"""
Config loading for cadence.

Looks for config in (in order of precedence):
  1. $CADENCE_CONFIG env var
  2. ~/.config/cadence/config.toml
  3. Built-in defaults (cadence/default_config.toml)
"""

from __future__ import annotations

import os
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]  # backport for Python 3.10
from pathlib import Path
from typing import Any


_DEFAULT_CONFIG_PATH = Path(__file__).parent / "default_config.toml"
_USER_CONFIG_PATH = Path.home() / ".config" / "cadence" / "config.toml"


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, returning a new dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _expand(value: Any) -> Any:
    """Expand ~ and env vars in string values."""
    if isinstance(value, str):
        return os.path.expandvars(os.path.expanduser(value))
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    return value


class Config:
    def __init__(self, data: dict) -> None:
        self._data = data

    def get(self, *keys: str, default: Any = None) -> Any:
        node = self._data
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return _expand(node)

    @property
    def public_repo(self) -> Path:
        path = self.get("repos", "public")
        if not path:
            raise RuntimeError(
                "Public repo path not configured. "
                "Set [repos] public in ~/.config/cadence/config.toml"
            )
        return Path(path)

    @property
    def private_repo(self) -> Path:
        path = self.get("repos", "private")
        if not path:
            raise RuntimeError(
                "Private repo path not configured. "
                "Set [repos] private in ~/.config/cadence/config.toml"
            )
        return Path(path)

    @property
    def thresholds(self) -> dict:
        return self._data.get("thresholds", {})


def load_config() -> Config:
    with open(_DEFAULT_CONFIG_PATH, "rb") as f:
        data = tomllib.load(f)

    # Check env var override first
    env_path = os.environ.get("CADENCE_CONFIG")
    user_path = Path(env_path) if env_path else _USER_CONFIG_PATH

    if user_path.exists():
        with open(user_path, "rb") as f:
            user_data = tomllib.load(f)
        data = _deep_merge(data, user_data)

    return Config(data)


def ensure_user_config() -> Path:
    """Create a default user config file if none exists. Returns the path."""
    _USER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _USER_CONFIG_PATH.exists():
        import shutil
        shutil.copy(_DEFAULT_CONFIG_PATH, _USER_CONFIG_PATH)
    return _USER_CONFIG_PATH
