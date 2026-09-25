"""Grounded Groq generation and response validation."""

from __future__ import annotations

import json
import os
from typing import Any

SYSTEM_PROMPT = """You are an IT support specialist. Answer ONLY using the provided context.
Do not use outside knowledge or invent steps. Return only JSON:
{\"category\": \"account_access|hardware|software|network\", \"resolution\": \"2-4 actionable sentences\"}
Email issues should use software because the form treats email as an application problem."""


class GroqGenerator:
    def __init__(self, model: str | None = None, client: Any = None) -> None:
        self.model = model or os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
        self._client_instance = client

    def _client(self) -> Any:
        if self._client_instance is None:
            from groq import Groq

            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                raise RuntimeError("GROQ_API_KEY is not set. Copy .env.example to .env and add your key.")
            self._client_instance = Groq(api_key=api_key)
        return self._client_instance

    def generate(self, query: str, context: str) -> dict[str, str]:
        response = self._client().chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n{context}\n\nUser issue: {query}"},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
        category = str(data.get("category", "")).strip().lower()
        resolution = str(data.get("resolution", "")).strip()
        if not category or not resolution:
            raise ValueError("Generator returned an incomplete support result")
        return {"category": category, "resolution": resolution}