"""Knowledge-base loading, chunking, embedding, and FAISS search."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

try:
    import faiss
except ImportError as exc:  # pragma: no cover
    raise ImportError("faiss-cpu is required: pip install -r requirements.txt") from exc


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    index: int
    text: str


class KnowledgeIndex:
    def __init__(
        self,
        knowledge_base: Path,
        model_name: str = "all-MiniLM-L6-v2",
        chunk_size: int = 200,
    ) -> None:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=0, separators=["\n\n", "\n", ". ", " "]
        )
        self.chunks = [
            Chunk(path.stem, index, text)
            for path in sorted(knowledge_base.glob("*.md"))
            for index, text in enumerate(splitter.split_text(path.read_text(encoding="utf-8")))
            if text.strip()
        ]
        if not self.chunks:
            raise RuntimeError(f"No documents found in {knowledge_base}")
        self.model = SentenceTransformer(model_name)
        embeddings = self.model.encode(
            [chunk.text for chunk in self.chunks], normalize_embeddings=True
        )
        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(np.asarray(embeddings, dtype="float32"))
        self.by_doc: dict[str, dict[int, Chunk]] = {}
        for chunk in self.chunks:
            self.by_doc.setdefault(chunk.doc_id, {})[chunk.index] = chunk

    def search(self, query: str, limit: int = 3) -> list[tuple[Chunk, float]]:
        embedding = self.model.encode([query], normalize_embeddings=True).astype("float32")
        scores, indices = self.index.search(embedding, limit)
        return [
            (self.chunks[index], float(score))
            for index, score in zip(indices[0], scores[0])
            if index != -1
        ]

    def expand(self, chunk: Chunk, window: int = 1) -> str:
        document = self.by_doc[chunk.doc_id]
        return " ".join(
            document[index].text
            for index in range(chunk.index - window, chunk.index + window + 1)
            if index in document
        )