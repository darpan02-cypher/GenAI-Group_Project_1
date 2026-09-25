"""Category normalization between the knowledge base, model, and form."""

import logging

from a2a.messages import VALID_CATEGORIES

logger = logging.getLogger(__name__)
FALLBACKS = {"email": "software", "security": "account_access", "password_reset": "account_access"}


def resolve_category(category: str, task_id: str = "", sources: list[str] | None = None) -> str:
    normalized = category.strip().lower()
    if normalized in VALID_CATEGORIES:
        return normalized
    mapped = FALLBACKS.get(normalized)
    if mapped is None:
        raise ValueError(f"LLM returned unmappable category: {category!r}")
    logger.info("task %s: mapped category %r -> %r from %s", task_id, normalized, mapped, sources or [])
    return mapped