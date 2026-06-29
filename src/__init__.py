"""Top-level package exports for the AI Harness MVP.

The package exposes the default bootstrap entry point and the most commonly
used domain namespaces so callers can import from stable package surfaces
instead of deep module paths.
"""

from src.bootstrap import build_default_harness
from src.domain import enums, models

__all__ = ["build_default_harness", "enums", "models"]
