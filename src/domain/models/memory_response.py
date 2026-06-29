from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.domain.enums import MemoryOperation, MemoryStatus
from src.domain.models._serialization import serialize_value


@dataclass(frozen=True)
class MemoryResponse:
    request_id: str
    operation: MemoryOperation
    status: MemoryStatus
    value: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_success(self) -> bool:
        return self.status == MemoryStatus.SUCCESS

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "operation": self.operation.value,
            "status": self.status.value,
            "value": serialize_value(self.value),
            "error": self.error,
            "metadata": serialize_value(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryResponse":
        return cls(
            request_id=data["request_id"],
            operation=MemoryOperation(data["operation"]),
            status=MemoryStatus(data["status"]),
            value=data.get("value"),
            error=data.get("error"),
            metadata=dict(data.get("metadata", {})),
        )

