"""JSON message adapters kept for compatibility with the assignment contract."""

from typing import Any

from .protocol import TaskResult, TaskStatus

VALID_CATEGORIES = {"account_access", "hardware", "software", "network"}
ERROR_NO_RELEVANT_DOCS = "no_relevant_documents_found"
ERROR_SPECIALIST_EXCEPTION = "specialist_internal_error"
ERROR_LOCAL_TIMEOUT = "requester_local_timeout"
ERROR_UNKNOWN_TASK = "unknown_task_id"


def task_submission(task_id: str, query: str) -> dict[str, Any]:
    return {"task_id": task_id, "query": query}


def ack(task_id: str) -> dict[str, Any]:
    return {"task_id": task_id, "status": TaskStatus.SUBMITTED.value}


def status_poll(task_id: str) -> dict[str, Any]:
    return {"task_id": task_id}


def working(task_id: str) -> dict[str, Any]:
    return {"task_id": task_id, "status": TaskStatus.WORKING.value}


def completed(task_id: str, result: TaskResult) -> dict[str, Any]:
    if result.category not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category: {result.category!r}")
    return {"task_id": task_id, "status": TaskStatus.COMPLETED.value, "result": result.to_dict()}


def failed(task_id: str, error: str) -> dict[str, Any]:
    return {"task_id": task_id, "status": TaskStatus.FAILED.value, "error": error}