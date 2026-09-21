"""Plugin manifest model and lifecycle status."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class PluginStatus(StrEnum):
    DISCOVERED = "DISCOVERED"
    VALIDATING = "VALIDATING"
    LOADING = "LOADING"
    LOADED = "LOADED"
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    FAILED = "FAILED"
    UNLOADING = "UNLOADING"
    UNLOADED = "UNLOADED"


class PluginDefinition(BaseModel):
    """Validated ``plugin.json`` metadata."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(pattern=r"^[a-z0-9]+(\.[a-z0-9]+)+$")
    name: str = Field(min_length=1, max_length=100)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    api_version: str = Field(pattern=r"^\d+\.\d+$")
    author: str = ""
    description: str = ""
    entry_point: str = Field(default="plugin.py", pattern=r"^[A-Za-z0-9_-]+\.py$")
    enabled: bool = True
    permissions: list[str] = Field(default_factory=list)
    dependencies: dict[str, str] = Field(default_factory=dict)
    icon: str = ""
    homepage: str = ""
    license: str = ""
    signature: str | None = None
