
# Group Project 1: 2 Agent AI System

## Setup

1. Create and activate your virtual environment.
2. Install dependencies:

   pip install -r requirements.txt

3. Install Playwright browsers:

   playwright install

4. Copy `.env.example` to `.env`.
5. Add your API key.

## Run the Mock Application

Open:

`mock_support_app/index.html`

in your browser.

## Run the Agents

```
playwright install chromium   # one-time
python run_tests.py
```

This drives all 5 cases in `test_cases.json` plus one bonus out-of-scope query
(to exercise the failure path), through the full loop: Requester submits a task
via the A2A contract in `contract.py`, Specialist runs RAG over `knowledge_base/`
and returns a grounded, sourced answer, Requester uses that answer to fill and
submit the mock form via Playwright, then verifies the confirmation.

To watch the browser fill/submit the form live instead of running headless (e.g. for a demo):

```
PLAYWRIGHT_HEADED=1 python run_tests.py
```

File map:
- `contract.py` — shared A2A JSON shapes both agents import (read this first).
- `specialist_agent.py` — RAG pipeline (FAISS + sentence-transformers + Groq) and
  the in-memory task store. Advanced RAG technique: context window enhancement
  (see module docstring for why).
- `requester_agent.py` — A2A polling loop + Playwright driver for the mock form.
- `run_tests.py` — wires both agents against `test_cases.json`.

## Project Requirements

See the project instructions on Canvas for the complete requirements.
