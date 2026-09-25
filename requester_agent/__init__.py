"""Requester coordination and browser adapter."""

from .agent import RequesterAgent, TaskFailedError, TaskTimeoutError

__all__ = ["RequesterAgent", "TaskFailedError", "TaskTimeoutError"]