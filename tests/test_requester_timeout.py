"""Pair 2 deliverable: exercises requester_agent.py's *local* timeout path.

Every other test (run_tests.py) only ever sees the Specialist resolve fast --
either to completed() or failed(). Nothing forces the Specialist to stay stuck
in "working" past POLL_TIMEOUT_SECONDS, so the timeout branch in
request_support() (the `while time.monotonic() < deadline` loop falling
through to `return contract.failed(task_id, contract.ERROR_LOCAL_TIMEOUT)`)
has never actually been exercised.

This test forces exactly that, without needing FAISS/sentence-transformers/Groq:
a stub specialist module is installed into sys.modules *before*
requester_agent is imported, so `import specialist_agent` inside
requester_agent.py binds to the stub instead of the real RAG pipeline. The
stub's submit_task() acks immediately (as the contract requires) and
get_status() always reports "working" -- it never resolves -- so the only way
request_support() can return is via its own timeout branch.

Run directly: python tests/test_requester_timeout.py
(No network, no API key, no Playwright browser needed.)
"""

import sys
import time
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import contract  # noqa: E402  (real contract.py -- no heavy deps)

# ---------------------------------------------------------------------------
# Build a stub specialist_agent module that never completes or fails, then
# register it in sys.modules BEFORE requester_agent is imported, so
# requester_agent's `import specialist_agent` binds to this stub.
# ---------------------------------------------------------------------------
_stub = types.ModuleType("specialist_agent")


def _submit_task(task_id: str, query: str) -> dict:
    return contract.ack(task_id)


def _get_status(task_id: str) -> dict:
    # Always "working" -- simulates a Specialist that is permanently stuck
    # (e.g. hung on a slow/unresponsive LLM call) and never reaches a
    # terminal state on its own.
    return contract.working(task_id)


_stub.submit_task = _submit_task
_stub.get_status = _get_status
sys.modules["specialist_agent"] = _stub

import requester_agent  # noqa: E402  (picks up the stub via sys.modules)

# Shrink the timeout/poll interval for a fast test run. This overrides the
# module-level constants requester_agent.request_support() reads at call
# time -- the *behavior* under test (give up locally, synthesize failed()
# with ERROR_LOCAL_TIMEOUT) is identical to the real 15s/1s team decision,
# just compressed so the test doesn't take 15 real seconds.
requester_agent.POLL_TIMEOUT_SECONDS = 2
requester_agent.POLL_INTERVAL_SECONDS = 0.2


def test_timeout_fires_and_returns_failed():
    print("=== Pair 2 bonus test: hard timeout path ===")
    start = time.monotonic()
    status = requester_agent.request_support("this will never resolve")
    elapsed = time.monotonic() - start

    assert status["status"] == contract.STATUS_FAILED, (
        f"expected status={contract.STATUS_FAILED!r}, got {status!r}"
    )
    assert status["error"] == contract.ERROR_LOCAL_TIMEOUT, (
        f"expected error={contract.ERROR_LOCAL_TIMEOUT!r}, got {status.get('error')!r}"
    )
    # Should give up at (approximately) POLL_TIMEOUT_SECONDS, not hang forever
    # and not return early.
    assert requester_agent.POLL_TIMEOUT_SECONDS <= elapsed < requester_agent.POLL_TIMEOUT_SECONDS + 1, (
        f"expected ~{requester_agent.POLL_TIMEOUT_SECONDS}s, took {elapsed:.2f}s"
    )

    print(f"  status: {status['status']} error: {status['error']}")
    print(f"  elapsed: {elapsed:.2f}s (timeout={requester_agent.POLL_TIMEOUT_SECONDS}s)")
    print("  RESULT: PASS (timeout fired correctly, no Playwright run attempted)")


def test_browser_step_refuses_on_timeout():
    # Belt-and-suspenders: confirm submit_ticket_via_browser() still refuses
    # to touch the browser for a timed-out status, same as any other failure.
    status = contract.failed("deadbeef", contract.ERROR_LOCAL_TIMEOUT)
    report = requester_agent.submit_ticket_via_browser("this will never resolve", status)
    assert report["ok"] is False
    assert "failed" in report["reason"] or contract.ERROR_LOCAL_TIMEOUT in report["reason"]
    print("  RESULT: PASS (browser step correctly refused on timed-out status)")


if __name__ == "__main__":
    test_timeout_fires_and_returns_failed()
    test_browser_step_refuses_on_timeout()
    print("\n2/2 passed")
