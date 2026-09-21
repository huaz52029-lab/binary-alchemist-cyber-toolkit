"""PluginDefinition validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.plugin_sdk import PLUGIN_API_VERSION, PluginDefinition, api_compatible


def test_valid_definition() -> None:
    definition = PluginDefinition.model_validate(
        {
            "id": "binaryalchemist.example",
            "name": "Example",
            "version": "1.0.0",
            "api_version": "1.0",
            "permissions": ["filesystem.read"],
            "unknown_field": "ignored",
        }
    )
    assert definition.id == "binaryalchemist.example"
    assert definition.permissions == ["filesystem.read"]
    assert not hasattr(definition, "unknown_field")


@pytest.mark.parametrize(
    "payload",
    [
        {"id": "badid", "name": "x", "version": "1.0.0", "api_version": "1.0"},
        {"id": "a.b", "name": "x", "version": "v1", "api_version": "1.0"},
        {"id": "a.b", "name": "x", "version": "1.0.0", "api_version": "2.0.0"},
        {"name": "x", "version": "1.0.0", "api_version": "1.0"},
    ],
)
def test_invalid_definitions(payload: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        PluginDefinition.model_validate(payload)


def test_api_compatibility() -> None:
    assert api_compatible("1.0", PLUGIN_API_VERSION)
    assert not api_compatible("2.0", PLUGIN_API_VERSION)
    assert not api_compatible("1.5", PLUGIN_API_VERSION)
