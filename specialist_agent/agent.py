"""Specialist orchestration: task lifecycle around the RAG components."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from a2a.messages import ERROR_NO_RELEVANT_DOCS, ERROR_SPECIALIST_EXCEPTION, ack
from a2a.protocol import TaskResult, TaskStatus, TaskStore

logger = logging.getLogger(__name__)


class SpecialistAgent:
    def __init__(self, task_store: TaskStore, knowledge_base: Path) -> None:
        from rag.generator import GroqGenerator
        from rag.index import KnowledgeIndex

        self.task_store = task_store
        self.index = KnowledgeIndex(knowledge_base)
        self.generator = GroqGenerator()

    def receive_task(self, payload: dict[str, str]) -> dict[str, str]:
        task = self.task_store.submit(payload.get("question", ""))
        threading.Thread(target=self._process, args=(task.task_id,), daemon=True).start()
        return ack(task.task_id)

    def _process(self, task_id: str) -> None:
        from rag.retriever import retrieve_context

        self.task_store.update(task_id, TaskStatus.WORKING)
        task = self.task_store.get(task_id)
        try:
            retrieval = retrieve_context(self.index, task.query)
            if retrieval is None:
                self.task_store.update(task_id, TaskStatus.FAILED, error=ERROR_NO_RELEVANT_DOCS)
                return
            context, sources = retrieval
            answer = self.generator.generate(task.query, context)
            category = self._resolve_category(answer["category"], task_id, sources)
            result = TaskResult(category, answer["resolution"], sources)
            self.task_store.update(task_id, TaskStatus.COMPLETED, result=result)
        except Exception:
            logger.exception("task %s failed", task_id)
            self.task_store.update(task_id, TaskStatus.FAILED, error=ERROR_SPECIALIST_EXCEPTION)

    @staticmethod
    def _resolve_category(category: str, task_id: str, sources: list[str]) -> str:
        from rag.categories import resolve_category

        return resolve_category(category, task_id=task_id, sources=sources)