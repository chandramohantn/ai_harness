"""Concrete platform services for configuration, plugins, DI, and secrets."""

from __future__ import annotations

import importlib
import importlib.util
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from src.interfaces.platform import (
    ConfigurationManager,
    DependencyContainer,
    PluginDescriptor,
    PluginManager,
    SecretManager,
)


class InMemoryConfigurationManager(ConfigurationManager):
    """Store configuration values in process memory."""

    def __init__(self) -> None:
        self._values: dict[str, Any] = {}
        self._sources: list[str] = []

    def get(self, key: str, default: Any = None) -> Any:
        return self._values.get(key, default)

    def get_required(self, key: str) -> Any:
        if key not in self._values:
            raise KeyError(f"Missing required configuration key: {key}")
        return self._values[key]

    def set(self, key: str, value: Any) -> None:
        self._values[key] = value

    def has(self, key: str) -> bool:
        return key in self._values

    def get_section(self, prefix: str) -> dict[str, Any]:
        return {
            key: value
            for key, value in self._values.items()
            if key == prefix or key.startswith(f"{prefix}.")
        }

    def load(self, source: str) -> None:
        path = Path(source)
        self._sources.append(source)
        if path.suffix == ".json":
            self._values.update(json.loads(path.read_text()))
            return
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            self._values[key.strip()] = value.strip()

    def reload(self) -> None:
        sources = list(self._sources)
        self._values.clear()
        self._sources.clear()
        for source in sources:
            self.load(source)


class DefaultPluginManager(PluginManager):
    """Discover and load lightweight Python-based plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, Any] = {}
        self._descriptors: dict[str, PluginDescriptor] = {}

    def discover(self, path: str) -> list[PluginDescriptor]:
        descriptors: list[PluginDescriptor] = []
        root = Path(path)
        for file in root.rglob("*.py"):
            if file.name == "__init__.py":
                continue
            descriptor = PluginDescriptor(
                name=file.stem,
                version="0.1.0",
                plugin_type="python_module",
                entry_point=file.stem,
                metadata={"path": str(file)},
            )
            descriptors.append(descriptor)
            self._descriptors[descriptor.name] = descriptor
        return descriptors

    def load(self, descriptor: PluginDescriptor) -> Any:
        path = descriptor.metadata.get("path")
        if isinstance(path, str):
            spec = importlib.util.spec_from_file_location(descriptor.name, path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load plugin from path: {path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            plugin = module
        elif ":" in descriptor.entry_point:
            module_name, attr = descriptor.entry_point.split(":", 1)
            plugin = getattr(importlib.import_module(module_name), attr)
        else:
            plugin = importlib.import_module(descriptor.entry_point)
        self._plugins[descriptor.name] = plugin
        self._descriptors[descriptor.name] = descriptor
        return plugin

    def register(self, name: str, plugin: Any) -> None:
        self._plugins[name] = plugin
        self._descriptors.setdefault(
            name,
            PluginDescriptor(
                name=name,
                version="manual",
                plugin_type="registered",
                entry_point=name,
            ),
        )

    def get(self, name: str) -> Any | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[PluginDescriptor]:
        return list(self._descriptors.values())

    def unload(self, name: str) -> None:
        self._plugins.pop(name, None)
        self._descriptors.pop(name, None)


class SimpleDependencyContainer(DependencyContainer):
    """Resolve registered implementations and factories."""

    def __init__(self) -> None:
        self._registrations: dict[type, tuple[Any, bool, bool]] = {}
        self._instances: dict[type, Any] = {}

    def register(self, interface: type, implementation: Any, singleton: bool = True) -> None:
        self._registrations[interface] = (implementation, singleton, False)

    def resolve(self, interface: type) -> Any:
        if interface not in self._registrations:
            raise KeyError(f"No registration for {interface!r}")
        implementation, singleton, is_factory = self._registrations[interface]
        if singleton and interface in self._instances:
            return self._instances[interface]
        if is_factory:
            instance = implementation()
        elif isinstance(implementation, type):
            instance = implementation()
        else:
            instance = implementation
        if singleton:
            self._instances[interface] = instance
        return instance

    def has(self, interface: type) -> bool:
        return interface in self._registrations

    def reset(self) -> None:
        self._registrations.clear()
        self._instances.clear()

    def register_factory(
        self, interface: type, factory: Callable[[], Any], singleton: bool = True
    ) -> None:
        self._registrations[interface] = (factory, singleton, True)


class InMemorySecretManager(SecretManager):
    """Store development secrets in process memory."""

    def __init__(self) -> None:
        self._secrets: dict[str, str] = {}

    def get_secret(self, key: str) -> str | None:
        return self._secrets.get(key)

    def has_secret(self, key: str) -> bool:
        return key in self._secrets

    def set_secret(self, key: str, value: str) -> None:
        self._secrets[key] = value

    def delete_secret(self, key: str) -> None:
        self._secrets.pop(key, None)

    def list_keys(self) -> list[str]:
        return sorted(self._secrets.keys())
