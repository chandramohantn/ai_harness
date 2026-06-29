from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.domain.models._serialization import utcnow


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)


class ValidationRule(ABC):
    @abstractmethod
    def validate(self, raw_input: dict[str, Any]) -> list[str]:
        raise NotImplementedError


@dataclass
class Session:
    session_id: str
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    is_active: bool = True

