"""JSON configuration with shipped defaults and atomic user overrides.

Shipped defaults live in ``configs/default.json``; user changes are persisted to
``data/config.json`` and transparently merged over the defaults. Unknown keys are
ignored with a warning so a forward-created config never crashes an older build.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from core.exceptions import ConfigError

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class WindowSettings(BaseModel):
    """Persisted main-window geometry."""

    model_config = ConfigDict(extra="ignore")

    width: int = Field(default=1280, ge=400, le=7680)
    height: int = Field(default=800, ge=300, le=4320)
    x: int | None = None
    y: int | None = None
    maximized: bool = False


class LoggingSettings(BaseModel):
    """Log verbosity settings."""

    model_config = ConfigDict(extra="ignore")

    level: LogLevel = "INFO"
    console: bool = True


class TaskSettings(BaseModel):
    """Defaults applied to every background task."""

    model_config = ConfigDict(extra="ignore")

    max_workers: int = Field(default=8, ge=1, le=64)
    default_timeout: float = Field(default=30.0, gt=0.0)


class AppConfig(BaseModel):
    """Complete runtime configuration."""

    model_config = ConfigDict(extra="ignore")

    theme: Literal["dark", "light"] = "dark"
    language: str = "zh_CN"
    window: WindowSettings = Field(default_factory=WindowSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    tasks: TaskSettings = Field(default_factory=TaskSettings)
    recent_tools: list[str] = Field(default_factory=list, max_length=20)


_NESTED_SECTIONS: dict[str, type[BaseModel]] = {
    "window": WindowSettings,
    "logging": LoggingSettings,
    "tasks": TaskSettings,
}


class ConfigManager:
    """Loads, validates, merges and atomically saves JSON configuration."""

    def __init__(self, user_config: Path, *, defaults_path: Path | None = None) -> None:
        self._user_config = Path(user_config)
        self._defaults_path = Path(defaults_path) if defaults_path is not None else None
        self._logger = logging.getLogger("core.config")

    @property
    def user_config_path(self) -> Path:
        return self._user_config

    def load(self) -> AppConfig:
        """Load defaults overlaid with user overrides, creating the user file if absent."""
        defaults = self._load_defaults()
        raw = self._read_json(self._user_config)
        if raw is None:
            self.save(defaults)
            return defaults
        self._warn_unknown_keys(raw)
        try:
            return defaults.model_validate(self._merge(defaults, raw))
        except ValidationError as exc:
            raise ConfigError(
                f"invalid configuration in {self._user_config}: {exc}",
                user_message="配置文件格式错误，已使用默认设置。",
            ) from exc

    def save(self, config: AppConfig) -> Path:
        """Atomically persist the given configuration."""
        self._user_config.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(config.model_dump(mode="json"), ensure_ascii=False, indent=2)
        temporary = self._user_config.with_suffix(self._user_config.suffix + ".tmp")
        try:
            temporary.write_text(payload + "\n", encoding="utf-8")
            os.replace(temporary, self._user_config)
        except OSError as exc:
            raise ConfigError(
                f"failed to save configuration to {self._user_config}: {exc}",
                user_message="无法保存配置，请检查磁盘权限。",
            ) from exc
        return self._user_config

    def update(self, **changes: Any) -> AppConfig:
        """Apply top-level changes and persist them immediately."""
        updated = self.load().model_copy(update=changes)
        self.save(updated)
        return updated

    def _load_defaults(self) -> AppConfig:
        if self._defaults_path is None or not self._defaults_path.exists():
            return AppConfig()
        raw = self._read_json(self._defaults_path)
        if raw is None:
            return AppConfig()
        try:
            return AppConfig.model_validate(raw)
        except ValidationError as exc:
            raise ConfigError(
                f"invalid default configuration at {self._defaults_path}: {exc}",
                user_message="默认配置文件损坏，请重新安装程序。",
            ) from exc

    @staticmethod
    def _merge(defaults: AppConfig, raw: dict[str, Any]) -> dict[str, Any]:
        """Deep-merge user values over a complete copy of the defaults."""
        merged = defaults.model_dump(mode="python")
        for key, value in raw.items():
            if key in _NESTED_SECTIONS and isinstance(value, dict):
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value
        return merged

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(
                f"cannot parse configuration file {path}: {exc}",
                user_message="配置文件无法解析，已使用默认设置。",
            ) from exc
        if not isinstance(data, dict):
            raise ConfigError(
                f"configuration root of {path} must be a JSON object",
                user_message="配置文件格式错误，已使用默认设置。",
            )
        return data

    def _warn_unknown_keys(self, raw: dict[str, Any]) -> None:
        unknown = sorted(set(raw) - set(AppConfig.model_fields))
        if unknown:
            self._logger.warning("Ignoring unknown config keys: %s", ", ".join(unknown))
        for section, model in _NESTED_SECTIONS.items():
            value = raw.get(section)
            if isinstance(value, dict):
                nested_unknown = sorted(set(value) - set(model.model_fields))
                if nested_unknown:
                    self._logger.warning(
                        "Ignoring unknown config keys in '%s': %s",
                        section,
                        ", ".join(nested_unknown),
                    )
