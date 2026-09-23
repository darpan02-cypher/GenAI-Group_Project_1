"""Playwright adapter for the mock support form."""

from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

FORM_PATH = Path(__file__).parents[1] / "mock_support_app" / "index.html"
CATEGORY_LABELS = {
    "account_access": "Account Access",
    "hardware": "Hardware",
    "software": "Software",
    "network": "Network",
}


class FormFieldUnavailableError(Exception):
    """The specialist result cannot be represented by the form."""


def submit_ticket(issue_text: str, category: str, resolution: str, app_path: Path = FORM_PATH, headless: bool = True) -> dict:
    if category not in CATEGORY_LABELS:
        raise FormFieldUnavailableError(f"The ticket form has no category option for '{category}'.")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=headless,
            slow_mo=800 if os.environ.get("PLAYWRIGHT_HEADED") == "1" else 0,
        )
        page = browser.new_page()
        try:
            page.goto(app_path.as_uri())
            page.fill("#issue", issue_text)
            page.select_option("#category", category)
            page.fill("#resolution", resolution)
            page.click("#submit-ticket")
            page.wait_for_selector("#confirmation:not(.hidden)", timeout=5000)
            return {
                "ticket_id": page.inner_text("#ticket-id"),
                "shown_category": page.inner_text("#ticket-category"),
                "shown_resolution": page.inner_text("#ticket-resolution"),
            }
        finally:
            browser.close()


def submit_ticket_via_browser(issue_text: str, status: dict) -> dict:
    """Compatibility wrapper for the original requester API."""
    if status.get("status") != "completed":
        return {"ok": False, "reason": f"specialist did not complete: {status.get('error')}"}
    category = status["result"]["category"]
    result = submit_ticket(
        issue_text,
        category,
        status["result"]["resolution"],
        headless=os.environ.get("PLAYWRIGHT_HEADED") != "1",
    )
    result["ok"] = (
        result["shown_category"] == CATEGORY_LABELS[category]
        and result["shown_resolution"] == status["result"]["resolution"]
    )
    return result