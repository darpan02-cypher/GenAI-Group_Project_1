"""Shared A2A JSON contract between requester_agent.py and specialist_agent.py.

Both agents build/read messages exclusively through these helpers so the two
sides of the protocol can't drift out of sync. Shapes match the assignment
spec verbatim:

    1. task_submission(task_id, query)                -> Requester -> Specialist
    2. ack(task_id)                                    -> Specialist -> Requester (immediate)
    3. status_poll(task_id)                            -> Requester -> Specialist
    4. working(task_id)                                -> Specialist -> Requester (while running)
    5. completed(task_id, category, resolution, sources) -> Specialist -> Requester
    6. failed(task_id, error)                          -> Specialist -> Requester
    7. Timeout is never sent by the Specialist -- the Requester gives up locally
       after POLL_TIMEOUT_SECONDS and synthesizes its own failed() with error
       "requester_local_timeout" (see requester_agent.py).
"""

STATUS_SUBMITTED = "submitted"
STATUS_WORKING = "working"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

VALID_STATUSES = {STATUS_SUBMITTED, STATUS_WORKING, STATUS_COMPLETED, STATUS_FAILED}

# The 4 categories mock_support_app/index.html's <select id="category"> actually
# accepts. The Specialist must map whatever the RAG/LLM concludes onto one of these.
VALID_CATEGORIES = {"account_access", "hardware", "software", "network"}

# Known "error" values for a failed() response.
ERROR_NO_RELEVANT_DOCS = "no_relevant_documents_found"
ERROR_SPECIALIST_EXCEPTION = "specialist_internal_error"
ERROR_LOCAL_TIMEOUT = "requester_local_timeout"
ERROR_UNKNOWN_TASK = "unknown_task_id"


def task_submission(task_id: str, query: str) -> dict:
    return {"task_id": task_id, "query": query}


def ack(task_id: str) -> dict:
    return {"task_id": task_id, "status": STATUS_SUBMITTED}


def status_poll(task_id: str) -> dict:
    return {"task_id": task_id}


def working(task_id: str) -> dict:
    return {"task_id": task_id, "status": STATUS_WORKING}


def completed(task_id: str, category: str, resolution: str, sources: list) -> dict:
    if category not in VALID_CATEGORIES:
        raise ValueError(f"category must be one of {sorted(VALID_CATEGORIES)}, got {category!r}")
    return {
        "task_id": task_id,
        "status": STATUS_COMPLETED,
        "result": {"category": category, "resolution": resolution, "sources": sources},
    }


def failed(task_id: str, error: str) -> dict:
    return {"task_id": task_id, "status": STATUS_FAILED, "error": error}
