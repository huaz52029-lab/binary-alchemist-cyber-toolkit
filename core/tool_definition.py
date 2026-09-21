"""Tool metadata and the uniform base interface every tool implements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from enum import StrEnum
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.result import ToolResult
from core.task import ExecutionContext


class ToolCategory(StrEnum):
    """First-class tool categories shown as navigation groups."""

    NETWORK = "network"
    WEB = "web"
    ENCODING = "encoding"
    CRYPTO = "crypto"
    FILE_ANALYSIS = "file_analysis"
    SYSTEM = "system"
    CTF = "ctf"

    @property
    def display_name(self) -> str:
        """Localized label used by navigation and the dashboard."""
        return _CATEGORY_LABELS[self]


class ToolParameterKind(StrEnum):
    """Widget-neutral parameter kinds the UI can render generically."""

    TEXT = "text"
    INTEGER = "integer"
    CHOICE = "choice"


class ToolParameter(BaseModel):
    """Declarative description of one tool input field."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(pattern=r"^[a-z_][a-z0-9_]*$")
    label: str = Field(min_length=1, max_length=100)
    kind: ToolParameterKind = ToolParameterKind.TEXT
    default: str | int | None = None
    placeholder: str = ""
    minimum: int | None = None
    maximum: int | None = None
    choices: list[str] = Field(default_factory=list)


_CATEGORY_LABELS = {
    ToolCategory.NETWORK: "网络安全",
    ToolCategory.WEB: "Web 安全",
    ToolCategory.ENCODING: "编码转换",
    ToolCategory.CRYPTO: "密码学",
    ToolCategory.FILE_ANALYSIS: "文件分析",
    ToolCategory.SYSTEM: "系统安全",
    ToolCategory.CTF: "CTF 工具",
}


class ToolDefinition(BaseModel):
    """Immutable metadata that drives registry, navigation and tool pages."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[a-z0-9_]+(\.[a-z0-9_]+)+$")
    name: str = Field(min_length=1, max_length=100)
    category: ToolCategory
    description: str = ""
    version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    author: str = ""
    icon: str = ""
    tags: list[str] = Field(default_factory=list)
    advanced: bool = False
    enabled: bool = True
    parameters: list[ToolParameter] = Field(default_factory=list)

    @model_validator(mode="after")
    def _id_matches_category(self) -> ToolDefinition:
        if not self.id.startswith(f"{self.category.value}."):
            raise ValueError(f"tool id '{self.id}' must start with '{self.category.value}.'")
        return self


ToolParameters = Mapping[str, Any]


class BaseTool(ABC):
    """Uniform contract for every security tool in the platform.

    Subclasses declare a :class:`ToolDefinition` and implement :meth:`run`. The run
    method receives parameters and an :class:`ExecutionContext`; it returns exactly
    one :class:`ToolResult`. Cancellation, progress and logging all flow through the
    context - tools never touch the UI or the task manager directly.
    """

    definition: ClassVar[ToolDefinition]

    @property
    def id(self) -> str:
        return self.definition.id

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def category(self) -> ToolCategory:
        return self.definition.category

    @abstractmethod
    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        """Execute the tool with the given parameters.

        Implementations must:

        * validate parameters and raise :class:`ToolInputError` with a user message;
        * check :meth:`ExecutionContext.raise_if_cancelled` between long steps;
        * report progress through the context;
        * return a :class:`ToolResult`, preferring ``context.make_result(...)``.
        """
