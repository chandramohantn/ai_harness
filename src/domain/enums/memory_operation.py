from enum import StrEnum


class MemoryOperation(StrEnum):
    READ = "READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    LIST = "LIST"
    CLEAR = "CLEAR"

