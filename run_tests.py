"""Runs every case in test_cases.json end-to-end (Requester -> A2A -> Specialist
RAG -> Playwright) and prints a pass/fail summary.

Includes one bonus case beyond the provided 5: an out-of-scope query, to
demonstrate the "Specialist finds nothing useful" failure path in an actual
run rather than just in documentation.
"""

import json
from pathlib import Path

import contract
import requester_agent

TEST_CASES_PATH = Path(__file__).parent / "test_cases.json"

# expected_category labels in test_cases.json are human-readable; map them to
# the form's literal values for comparison. "Email" has no matching <option> in
# mock_support_app/index.html (documented edge case), so we expect the
# Specialist to route it to "software" -- see specialist_agent.CATEGORY_FALLBACK_MAP.
EXPECTED_LABEL_TO_VALUE = {
    "Account Access": "account_access",
    "Hardware": "hardware",
    "Software": "software",
    "Network": "network",
    "Email": "software",
}


def run_case(case_id, query: str, expected_label: str) -> bool:
    expected_value = EXPECTED_LABEL_TO_VALUE.get(expected_label)
    print(f"\n=== Case {case_id}: {query!r} (expected: {expected_label}) ===")

    status = requester_agent.request_support(query)

    if status["status"] != contract.STATUS_COMPLETED:
        print(f"  specialist did not complete: status={status['status']} error={status.get('error')}")
        print("  RESULT: FAIL")
        return False

    got_category = status["result"]["category"]
    report = requester_agent.submit_ticket_via_browser(query, status)

    passed = bool(report.get("ok")) and got_category == expected_value

    print(f"  category: {got_category} (expected {expected_value})")
    print(f"  sources: {status['result']['sources']}")
    print(f"  playwright: {report}")
    print(f"  RESULT: {'PASS' if passed else 'FAIL'}")
    return passed


def run_failure_demo() -> bool:
    print("\n=== Bonus case: out-of-scope query (demonstrates failure path) ===")
    status = requester_agent.request_support("What is the capital of France?")
    ok = status["status"] == contract.STATUS_FAILED
    print(f"  status: {status['status']} error: {status.get('error')}")
    print(f"  RESULT: {'PASS (correctly failed, no Playwright run)' if ok else 'FAIL (should have failed)'}")
    return ok


def main():
    cases = json.loads(TEST_CASES_PATH.read_text())
    results = [
        (case["id"], run_case(case["id"], case["request"], case["expected_category"]))
        for case in cases
    ]
    results.append(("failure-demo", run_failure_demo()))

    print("\n=== Summary ===")
    for case_id, ok in results:
        print(f"  case {case_id}: {'PASS' if ok else 'FAIL'}")
    passed = sum(1 for _, ok in results if ok)
    print(f"\n{passed}/{len(results)} passed")


if __name__ == "__main__":
    main()
