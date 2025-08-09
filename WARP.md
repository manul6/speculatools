# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

- Environment: Windows 10, PowerShell 7, Python 3.11 (system), local virtualenv
- Scope: Local development only (no packaging/CI yet)

Quickstart (pwsh)
- Create and activate a local venv:
  - py -3.11 -m venv .venv
  - .\.venv\Scripts\Activate.ps1
- Upgrade pip and install local dev dependencies:
  - python -m pip install -U pip
  - pip install langchain-core langchain ruff pyright pytest

Common commands
- Activate env for this session:
  - .\.venv\Scripts\Activate.ps1
- Lint (ruff):
  - ruff check .
  - ruff check . --fix
  - ruff format .
- Type-check (pyright):
  - pyright
- Tests (pytest):
  - Run all tests (once tests/ is added):
    - pytest -q
  - Run a single test file::test (pattern examples):
    - pytest tests/test_core.py::test_call_tool -q
    - pytest -k call_tool -q
- Run the inline demo/test that exists today:
  - python -c "from speculatools_langchain.core import test_call_tool; test_call_tool()"

Build
- No package build is defined yet (no pyproject.toml/setup.cfg). When packaging is added, build with:
  - python -m build

Architecture overview
- Purpose: Provide speculative streaming around slow tool calls so users see immediate, provisional output that is corrected when the tool finishes.
- Core flow (speculatools_langchain/core.py):
  - call_tool(chain: Runnable, tool: Tool, tool_input: dict) -> async generator of str
  - Starts tool.arun(tool_input) concurrently (asyncio.create_task).
  - While the tool runs, streams from chain.stream({"result": {"status": "success"}}) to optimistically emit a “success” path.
  - When the tool finishes, if result["status"] != "success": it emits the token "<MISPREDICT>" and then re-streams with the true result: chain.stream({"result": result}).
- Contracts and expectations:
  - The Tool must be an async-capable LangChain Tool whose arun returns a mapping including a "status" key with values like "success" or "error".
  - The Runnable provided as chain must implement an async stream(input) yielding string chunks. In the test harness, it formats a template with the provided result.
  - Consumers should treat "<MISPREDICT>" as a segmentation marker that separates the optimistic stream from the corrected stream.
- Extending:
  - To adapt to other tools, ensure their async call returns a dict with a "status" (or adjust the predicate used to detect success vs. error).
  - To change speculative behavior, alter the optimistic input fed into chain.stream (e.g., provide richer placeholders than {"status": "success"}).
  - The misprediction token can be changed but should be treated consistently by downstream renderers.

Repository notes
- Python source currently lives in speculatools_langchain/core.py with an inline test harness (test_call_tool). A tests/ directory and pytest-based tests are expected to be added later.
- README is intentionally minimal; this file is the primary guide for day-to-day commands until packaging and CI are introduced.

