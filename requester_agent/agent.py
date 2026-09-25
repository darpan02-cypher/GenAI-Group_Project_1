"""Requester orchestration: submit a task and poll for its result."""

from __future__ import annotations

import time

from a2a.protocol import TaskStatus, TaskStore


class TaskTimeoutError(Exception):
    """The specialist did not finish within the configured deadline."""


class TaskFailedError(Exception):
    """The specialist reported a failed task."""


class RequesterAgent:
    def __init__(self, specialist, task_store: TaskStore, poll_interval: float = 1.0, timeout: float = 15.0) -> None:
        self.specialist = specialist
        self.task_store = task_store
        self.poll_interval = poll_interval
        self.timeout = timeout

    def handle_user_request(self, user_text: str) -> dict:
        acknowledgement = self.specialist.receive_task({"question": user_text})
        return self._poll_for_result(acknowledgement["task_id"])

    def _poll_for_result(self, task_id: str) -> dict:
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            task = self.task_store.get(task_id)
            if task.status is TaskStatus.COMPLETED and task.result:
                return task.result.to_dict()
            if task.status is TaskStatus.FAILED:
                raise TaskFailedError(task.error or "Specialist Agent reported failure.")
            time.sleep(self.poll_interval)
        raise TaskTimeoutError(f"Task {task_id} did not complete within {self.timeout}s")