"""Backward-compatible public A2A message contract."""

from a2a.messages import (
    ERROR_LOCAL_TIMEOUT,
    ERROR_NO_RELEVANT_DOCS,
    ERROR_SPECIALIST_EXCEPTION,
    ERROR_UNKNOWN_TASK,
    VALID_CATEGORIES,
    ack,
    completed as _completed,
    failed,
    status_poll,
    task_submission,
    working,
)
from a2a.protocol import TaskResult, TaskStatus

STATUS_SUBMITTED = TaskStatus.SUBMITTED.value
STATUS_WORKING = TaskStatus.WORKING.value
STATUS_COMPLETED = TaskStatus.COMPLETED.value
STATUS_FAILED = TaskStatus.FAILED.value
VALID_STATUSES = {status.value for status in TaskStatus}


def completed(task_id: str, category: str, resolution: str, sources: list[str]) -> dict:
    return _completed(task_id, TaskResult(category, resolution, sources))
