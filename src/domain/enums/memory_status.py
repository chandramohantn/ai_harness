from enum import StrEnum


class MemoryStatus(StrEnum):
    SUCCESS = "SUCCESS"
    NOT_FOUND = "NOT_FOUND"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"

