"""Requester Agent: submits a task via A2A, polls for the result, then drives
Playwright to fill and submit the mock support ticket form.

Owned by Pair 2. You shouldn't need to touch specialist_agent.py's RAG internals --
just its two public functions, submit_task() and get_status(), which are the whole
A2A surface.

Polling: 15s total timeout, 1s between polls (team decision). If the Specialist
never reaches "completed" or "failed" within that window, request_support()
synthesizes its own failed() with error "requester_local_timeout" -- the Specialist
itself never sends a timeout message (see contract.py's docstring, point 7).
"""

import time
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

import contract
import specialist_agent

POLL_INTERVAL_SECONDS = 1
POLL_TIMEOUT_SECONDS = 15

FORM_PATH = Path(__file__).parent / "mock_support_app" / "index.html"

# Mirrors mock_support_app/script.js's CATEGORY_LABELS, used to verify the
# confirmation echoes back the category we selected.
CATEGORY_LABELS = {
    "account_access": "Account Access",
    "hardware": "Hardware",
    "software": "Software",
    "network": "Network",
}


def request_support(query: str) -> dict:
    """Runs the full A2A submit -> poll loop. Returns the final status dict,
    which is always one of contract's completed()/failed() shapes -- callers
    don't need to special-case a timeout separately from any other failure."""
    task_id = uuid.uuid4().hex[:8]
    submission = contract.task_submission(task_id, query)

    ack = specialist_agent.submit_task(submission["task_id"], submission["query"])
    if ack["status"] != contract.STATUS_SUBMITTED:
        raise RuntimeError(f"expected immediate ack, got {ack!r}")

    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    status = ack
    while time.monotonic() < deadline:
        time.sleep(POLL_INTERVAL_SECONDS)
        status = specialist_agent.get_status(contract.status_poll(task_id)["task_id"])
        if status["status"] in (contract.STATUS_COMPLETED, contract.STATUS_FAILED):
            return status

    print(f"[requester] task {task_id} timed out after {POLL_TIMEOUT_SECONDS}s "
          f"(last status: {status['status']})")
    return contract.failed(task_id, contract.ERROR_LOCAL_TIMEOUT)


def submit_ticket_via_browser(issue_text: str, status: dict) -> dict:
    """Given a completed() status dict, fills and submits the mock support form
    via Playwright, then verifies the confirmation. Returns a report dict.

    If status isn't "completed" (failed or timed out), this refuses to open the
    browser at all -- there's nothing valid to fill in, and the failure/timeout
    was already logged in request_support(). Callers should check status first.
    """
    if status["status"] != contract.STATUS_COMPLETED:
        return {"ok": False, "reason": f"specialist did not complete (status={status['status']}, "
                                        f"error={status.get('error')})"}

    category = status["result"]["category"]
    resolution = status["result"]["resolution"]

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(FORM_PATH.as_uri())
            page.fill("#issue", issue_text)
            page.select_option("#category", category)
            page.fill("#resolution", resolution)
            page.click("#submit-ticket")

            try:
                page.wait_for_selector("#confirmation:not(.hidden)", timeout=5000)
            except Exception:
                error_text = page.inner_text("#error") if page.is_visible("#error") else "unknown error"
                return {"ok": False, "reason": f"form showed #error instead of confirmation: {error_text}"}

            shown_category = page.inner_text("#ticket-category")
            shown_resolution = page.inner_text("#ticket-resolution")
            ticket_id = page.inner_text("#ticket-id")

            ok = shown_category == CATEGORY_LABELS[category] and shown_resolution == resolution
            return {
                "ok": ok,
                "ticket_id": ticket_id,
                "shown_category": shown_category,
                "shown_resolution": shown_resolution,
            }
        finally:
            browser.close()
