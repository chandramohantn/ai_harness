from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.interfaces.observability.models import PromptRecord


class PromptTracer(ABC):
    @abstractmethod
    def record_prompt(
        self, task_id: str, prompt: str, metadata: dict[str, Any] | None = None
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def record_response(
        self,
        prompt_record_id: str,
        response: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_prompt_history(self, task_id: str) -> list[PromptRecord]:
        raise NotImplementedError
