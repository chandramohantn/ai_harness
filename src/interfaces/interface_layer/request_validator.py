from __future__ import annotations

from abc import ABC, abstractmethod

from src.interfaces.interface_layer.models import ValidationResult, ValidationRule


class RequestValidator(ABC):
    @abstractmethod
    def validate_request(self, raw_input: dict[str, object]) -> ValidationResult:
        raise NotImplementedError

    @abstractmethod
    def register_rule(self, rule: ValidationRule) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_rules(self) -> list[ValidationRule]:
        raise NotImplementedError
