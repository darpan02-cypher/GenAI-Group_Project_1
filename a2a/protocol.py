"""Typed, thread-safe task protocol shared by both agents."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class TaskResult:
    category: str
    resolution: str
    sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Task:
    task_id: str
    query: str
    status: TaskStatus = TaskStatus.SUBMITTED
    result: TaskResult | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "query": self.query,
            "result": self.result.to_dict() if self.result else None,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class TaskStore:
    """Thread-safe in-memory implementation of the A2A task boundary."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._lock = threading.Lock()

    def submit(self, query: str, task_id: str | None = None) -> Task:
        task = Task(task_id=task_id or uuid.uuid4().hex[:8], query=query)
        with self._lock:
            self._tasks[task.task_id] = task
        return task

    def update(
        self,
        task_id: str,
        status: TaskStatus,
        result: TaskResult | None = None,
        error: str | None = None,
    ) -> Task:
        with self._lock:
            task = self._tasks[task_id]
            task.status = status
            task.result = result
            task.error = error
            task.updated_at = time.time()
            return task

    def get(self, task_id: str) -> Task:
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError(f"Unknown task_id: {task_id}")
            task = self._tasks[task_id]
            return Task(
                task_id=task.task_id,
                query=task.query,
                status=task.status,
                result=task.result,
                error=task.error,
                created_at=task.created_at,
                updated_at=task.updated_at,
            )