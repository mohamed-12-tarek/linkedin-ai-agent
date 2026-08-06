from enum import StrEnum


class ModelRole(StrEnum):
    WRITER = "writer"
    REVIEWER = "reviewer"
    JUDGE = "judge"
    TRANSLATOR = "translation"
    IMAGE = "image"


class NodeStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
