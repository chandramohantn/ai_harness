from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PluginDescriptor:
    name: str
    version: str
    plugin_type: str
    entry_point: str
    metadata: dict[str, Any] = field(default_factory=dict)

