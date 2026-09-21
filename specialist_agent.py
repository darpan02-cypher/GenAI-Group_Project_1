"""Specialist Agent: RAG over knowledge_base/ -> grounded, sourced answer.

Owned by Pair 1. Read this file top to bottom; you shouldn't need to touch
requester_agent.py or run_tests.py to build out the RAG quality.

--- Advanced RAG technique: Context Window Enhancement (sentence-window retrieval) ---
Each knowledge_base/*.md doc is split into small chunks (~200 chars) for precise
embedding matches -- a tiny chunk like "Wi-Fi will not connect." embeds much more
precisely than a whole document. But a tiny chunk alone loses the surrounding
Troubleshooting/Resolution/Ticket Category context the LLM needs to answer well.
So retrieval matches on small chunks, then _expand() pulls in the WINDOW chunks
immediately before/after each match from the *same* document before handing
context to the LLM. This matters a lot here specifically because several docs
overlap in topic (account_access.md, password_reset.md, security.md all discuss
password/account problems) -- small chunks keep the vector match precise, while
windowed expansion keeps the generation grounded in the full procedure instead
of one isolated sentence.

--- In-process A2A (team decision) ---
Requester and Specialist run in the same Python process; submit_task()/get_status()
are called directly rather than over HTTP. The dicts they exchange are still built
exclusively through contract.py, so the message shapes are identical to what a real
HTTP+JSON transport would send -- swapping in a real server later only means putting
these two functions behind endpoints, not changing the protocol.
"""

import json
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

import contract

try:
    import faiss
except ImportError as exc:  # pragma: no cover
    raise ImportError("faiss-cpu is required: pip install -r requirements.txt") from exc

load_dotenv()

logging.basicConfig(level=logging.INFO, format="[specialist] %(message)s")
logger = logging.getLogger("specialist_agent")

KB_DIR = Path(__file__).parent / "knowledge_base"
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")

CHUNK_SIZE = 200
TOP_K = 3
WINDOW = 1  # chunks pulled in on each side of a match (context window enhancement)
SIMILARITY_THRESHOLD = 0.30  # cosine similarity below this -> "no relevant documents"

# Categories the LLM/knowledge base may surface that have no matching <option> in
# the form. Mapped to the closest valid category per the documented edge case:
# an "Email" issue is treated as a client/application problem (closest = software).
CATEGORY_FALLBACK_MAP = {
    "email": "software",
    "security": "account_access",
    "password_reset": "account_access",
}

SYSTEM_PROMPT = """You are an IT support specialist. Answer ONLY using the provided \
context from the knowledge base. Do not use outside knowledge, and do not invent \
steps that are not supported by the context.

Respond with a strict JSON object and nothing else:
{"category": "<one of: account_access, hardware, software, network>", "resolution": "<2-4 sentence resolution>"}

If the issue is about email, use "software" (the email client is the application at fault).
resolution must be concise, actionable text a support agent could hand directly to the user."""


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    idx: int
    text: str


def _load_and_chunk() -> list[Chunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=0, separators=["\n\n", "\n", ". ", " "]
    )
    chunks = []
    for path in sorted(KB_DIR.glob("*.md")):
        doc_id = path.stem
        pieces = [p for p in splitter.split_text(path.read_text()) if p.strip()]
        chunks.extend(Chunk(doc_id=doc_id, idx=i, text=piece) for i, piece in enumerate(pieces))
    return chunks


class _KnowledgeIndex:
    def __init__(self):
        self.chunks = _load_and_chunk()
        if not self.chunks:
            raise RuntimeError(f"No documents found in {KB_DIR}")
        self.model = SentenceTransformer(EMBED_MODEL_NAME)
        embeddings = self.model.encode([c.text for c in self.chunks], normalize_embeddings=True)
        self.embeddings = np.asarray(embeddings, dtype="float32")
        self.index = faiss.IndexFlatIP(self.embeddings.shape[1])
        self.index.add(self.embeddings)
        self.by_doc: dict[str, dict[int, Chunk]] = {}
        for c in self.chunks:
            self.by_doc.setdefault(c.doc_id, {})[c.idx] = c

    def search(self, query: str, k: int = TOP_K) -> list[tuple[Chunk, float]]:
        q_emb = self.model.encode([query], normalize_embeddings=True).astype("float32")
        scores, idxs = self.index.search(q_emb, k)
        return [
            (self.chunks[i], float(s))
            for i, s in zip(idxs[0], scores[0])
            if i != -1
        ]

    def expand(self, chunk: Chunk, window: int = WINDOW) -> str:
        """Context window enhancement: stitch in neighboring chunks from the same
        doc so the LLM sees full section context, not one isolated sentence."""
        doc_chunks = self.by_doc[chunk.doc_id]
        lo, hi = chunk.idx - window, chunk.idx + window
        return " ".join(doc_chunks[i].text for i in range(lo, hi + 1) if i in doc_chunks)


_index = _KnowledgeIndex()  # built once at import time


def _retrieve_context(query: str) -> tuple[str, list[str]] | None:
    hits = _index.search(query)
    if not hits or hits[0][1] < SIMILARITY_THRESHOLD:
        return None

    seen_docs: dict[str, str] = {}
    for chunk, _score in hits:
        seen_docs.setdefault(chunk.doc_id, _index.expand(chunk))

    sources = [f"{doc_id}.md" for doc_id in seen_docs]
    context = "\n\n---\n\n".join(f"[{doc_id}]\n{text}" for doc_id, text in seen_docs.items())
    return context, sources


def _groq_client():
    from groq import Groq

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set. Copy .env.example to .env and add your key.")
    return Groq(api_key=api_key)


def _ask_llm(query: str, context: str) -> tuple[str, str]:
    client = _groq_client()
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nUser issue: {query}"},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content)
    category = str(data.get("category", "")).strip().lower()
    resolution = str(data.get("resolution", "")).strip()
    return category, resolution


def _resolve_category(task_id: str, category: str, sources: list[str]) -> str:
    if category in contract.VALID_CATEGORIES:
        return category

    mapped = CATEGORY_FALLBACK_MAP.get(category)
    if mapped is None:
        raise ValueError(f"LLM returned unmappable category: {category!r}")

    if "email.md" in sources:
        logger.info(
            "task %s: 'Email' has no matching form option; routed to %r per documented edge case",
            task_id, mapped,
        )
    else:
        logger.info("task %s: mapped LLM category %r -> %r", task_id, category, mapped)
    return mapped


# ---- In-memory task store -------------------------------------------------

_tasks: dict[str, dict] = {}
_lock = threading.Lock()


def submit_task(task_id: str, query: str) -> dict:
    """Requester -> Specialist submission. Returns the immediate ack (contract.ack)
    and kicks off RAG retrieval + generation on a background thread so the ack
    returns without waiting on FAISS/Groq."""
    ack = contract.ack(task_id)
    with _lock:
        _tasks[task_id] = ack
    threading.Thread(target=_process_task, args=(task_id, query), daemon=True).start()
    return dict(ack)


def get_status(task_id: str) -> dict:
    """Requester -> Specialist status poll. Returns whatever contract shape
    matches the task's current state (working / completed / failed)."""
    with _lock:
        return dict(_tasks.get(task_id, contract.failed(task_id, contract.ERROR_UNKNOWN_TASK)))


def _process_task(task_id: str, query: str) -> None:
    with _lock:
        _tasks[task_id] = contract.working(task_id)

    try:
        retrieval = _retrieve_context(query)
        if retrieval is None:
            logger.info("task %s: no relevant documents for query=%r", task_id, query)
            result = contract.failed(task_id, contract.ERROR_NO_RELEVANT_DOCS)
        else:
            context, sources = retrieval
            category, resolution = _ask_llm(query, context)
            category = _resolve_category(task_id, category, sources)
            result = contract.completed(task_id, category, resolution, sources)
    except Exception:
        logger.exception("task %s: specialist internal error", task_id)
        result = contract.failed(task_id, contract.ERROR_SPECIALIST_EXCEPTION)

    with _lock:
        _tasks[task_id] = result
