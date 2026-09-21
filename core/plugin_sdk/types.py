"""Plugin SDK versioning helpers."""

from __future__ import annotations

PLUGIN_API_VERSION = "1.0"


def parse_version(value: str) -> tuple[int, ...]:
    """Parse a dotted version into integer parts (SemVer-safe)."""
    return tuple(int(part) for part in value.split("."))


def api_compatible(plugin_api: str, app_api: str = PLUGIN_API_VERSION) -> bool:
    """Compatibility rule: same major, plugin minor <= app minor."""
    plugin = parse_version(plugin_api)
    app = parse_version(app_api)
    if not plugin or not app:
        return False
    return plugin[0] == app[0] and plugin[1] <= app[1]
