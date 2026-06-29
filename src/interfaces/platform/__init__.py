"""Cross-cutting platform contract exports."""

from src.interfaces.platform.configuration_manager import ConfigurationManager
from src.interfaces.platform.dependency_container import DependencyContainer
from src.interfaces.platform.models import PluginDescriptor
from src.interfaces.platform.plugin_manager import PluginManager
from src.interfaces.platform.secret_manager import SecretManager

__all__ = [
    "ConfigurationManager",
    "DependencyContainer",
    "PluginDescriptor",
    "PluginManager",
    "SecretManager",
]
