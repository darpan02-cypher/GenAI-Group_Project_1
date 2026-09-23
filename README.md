
# Group Project 1: 2 Agent AI System

## Setup

1. Create and activate your virtual environment.
2. Install dependencies:

   pip install -r requirements.txt

3. Install Playwright browsers:

   python -m playwright install chromium

4. Copy `.env.example` to `.env`.
5. Add your API key.

## Run the Mock Application

Open:

`mock_support_app/index.html`

in your browser.

## Run the Agents

```
python -m playwright install chromium   # one-time
python run_tests.py
```

This drives all 5 cases in `test_cases.json` plus one bonus out-of-scope query
(to exercise the failure path), through the full loop: Requester submits a task
via the A2A contract in `contract.py`, Specialist runs RAG over `knowledge_base/`
and returns a grounded, sourced answer, Requester uses that answer to fill and
submit the mock form via Playwright, then verifies the confirmation.

To watch the browser fill/submit the form live instead of running headless (e.g. for a demo):

```
# PowerShell
$env:PLAYWRIGHT_HEADED = "1"; python run_tests.py

# Command Prompt
set PLAYWRIGHT_HEADED=1 && python run_tests.py
```

Run one request through the composition root:

```text
python main.py "My laptop won't connect to Wi-Fi."
python main.py --headed "My laptop won't connect to Wi-Fi."
```

Run the dependency-light unit tests:

```text
python -m unittest discover -s tests -v
```

File map:
- `a2a/protocol.py` — typed task state and thread-safe in-process protocol.
- `a2a/messages.py` and `contract.py` — JSON message adapters and compatibility API.
- `rag/index.py` — knowledge-base chunking, embeddings, and FAISS search.
- `rag/retriever.py` — similarity filtering and context-window expansion.
- `rag/generator.py` — grounded Groq generation and response validation.
- `specialist_agent/agent.py` — specialist orchestration and task lifecycle.
- `requester_agent/agent.py` — A2A polling and timeout handling.
- `requester_agent/playwright_flow.py` — browser form automation and verification.
- `main.py` — composition root that wires the application together.
- `run_tests.py` — end-to-end cases; `tests/` contains focused unit tests.

## Project Requirements

See the project instructions on Canvas for the complete requirements.
