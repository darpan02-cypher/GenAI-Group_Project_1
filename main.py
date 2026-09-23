"""Composition root for the end-to-end support workflow."""

from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from a2a.protocol import TaskStore
from requester_agent.agent import RequesterAgent, TaskFailedError, TaskTimeoutError
from requester_agent.playwright_flow import submit_ticket
from specialist_agent.agent import SpecialistAgent

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")


def create_support_system() -> tuple[RequesterAgent, TaskStore]:
    store = TaskStore()
    specialist = SpecialistAgent(store, BASE_DIR / "knowledge_base")
    return RequesterAgent(specialist, store), store


def run(user_text: str, headless: bool = True) -> None:
    requester, _store = create_support_system()
    print(f"User: {user_text}")
    try:
        result = requester.handle_user_request(user_text)
    except (TaskFailedError, TaskTimeoutError) as exc:
        print(f"[FAILED] {exc}")
        return
    print(f"Specialist result: {result}")
    ticket = submit_ticket(user_text, result["category"], result["resolution"], headless=headless)
    print(f"Playwright: ticket submitted successfully -> {ticket}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("request", nargs="*", default=["I forgot my password and cannot log into my account."])
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()
    run(" ".join(args.request), headless=not args.headed)