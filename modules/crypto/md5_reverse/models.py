"""Input and result models for the MD5 reverse analyzer."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ReverseMode = Literal["verify", "dictionary", "bruteforce"]

MODE_LABELS = {
    "verify": "单候选验证",
    "dictionary": "字典匹配",
    "bruteforce": "暴力尝试",
}


class MD5ReverseInput(BaseModel):
    """Validated tool parameters."""

    target: str = Field(min_length=1, max_length=100_000)
    mode: ReverseMode = "verify"
    candidate: str = ""
    dictionary_path: str = ""
    charset: str = "abcdefghijklmnopqrstuvwxyz"
    min_length: int = Field(default=1, ge=1, le=8)
    max_length: int = Field(default=5, ge=1, le=8)


class MD5ReverseResult(BaseModel):
    """Structured result for dictionary/brute-force runs."""

    target_hash: str
    mode: str
    matched: bool
    plaintext: str | None = None
    attempts: int = 0
    elapsed: float = 0.0
    speed: float = 0.0
    dictionary_path: str | None = None
    charset: str | None = None
    min_length: int | None = None
    max_length: int | None = None


VERIFY_DISPLAY_SPEC: dict[str, Any] = {
    "title": "MD5 候选验证结果",
    "table": {
        "columns": [
            {"field": "hash", "label": "目标Hash"},
            {"field": "candidate", "label": "候选"},
            {"field": "matched", "label": "匹配"},
        ]
    },
}


RESULT_DISPLAY_SPEC: dict[str, Any] = {
    "title": "MD5 逆向分析结果",
    "sections": [
        {
            "title": "基本信息",
            "items": [
                {"field": "target_hash", "label": "目标Hash"},
                {"field": "mode", "label": "模式", "map": MODE_LABELS},
                {"field": "matched", "label": "匹配"},
            ],
        },
        {
            "title": "结果",
            "items": [
                {"field": "plaintext", "label": "候选明文"},
                {"field": "attempts", "label": "尝试次数"},
                {"field": "elapsed", "label": "耗时(秒)"},
                {"field": "speed", "label": "速度(candidates/s)"},
            ],
        },
        {
            "title": "参数",
            "items": [
                {"field": "dictionary_path", "label": "字典文件"},
                {"field": "charset", "label": "字符集"},
                {"field": "min_length", "label": "最小长度"},
                {"field": "max_length", "label": "最大长度"},
            ],
        },
    ],
}
