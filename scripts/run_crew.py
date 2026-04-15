"""Standalone crew runner for manual prompt and model iteration.

Run from repository root:
    python -m scripts.run_crew
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

SYMBOL = os.getenv("STOCKSAGE_SYMBOL", "AAPL")


def _bootstrap() -> None:
    storage = Path(".crewai_storage").resolve()
    storage.mkdir(parents=True, exist_ok=True)
    os.environ["CREWAI_STORAGE_DIR"] = str(storage)
    os.environ["STOCKSAGE_ACTIVE_SYMBOL"] = SYMBOL.upper()


_task_count = 0


def _on_task_done(output: Any) -> None:
    global _task_count
    _task_count += 1
    name = getattr(output, "name", None) or f"task_{_task_count}"
    agent = getattr(output, "agent", "") or ""
    pydantic = getattr(output, "pydantic", None)
    keys = list(pydantic.model_dump().keys()) if pydantic else []

    print(f"\n  [{_task_count}] {name}  agent={agent}")
    if keys:
        print(f"      output keys: {keys}")
    else:
        raw = getattr(output, "raw", str(output))
        print(f"      raw ({len(raw)} chars): {raw[:200]}...")


def main() -> int:
    _bootstrap()

    from src.core.config.config import LLM_MODEL
    from src.crew.crew import StockAnalysisCrew

    print(f"[config] model={LLM_MODEL}  symbol={SYMBOL}")

    crew = StockAnalysisCrew().crew()
    crew.task_callback = _on_task_done

    result = crew.kickoff(inputs={"symbol": SYMBOL.upper()})

    tasks_output = getattr(result, "tasks_output", None) or []
    valid = sum(1 for task in tasks_output if getattr(task, "pydantic", None) is not None)

    print(f"\n{'=' * 70}")
    print(f"  {valid}/{len(tasks_output)} tasks returned structured output")
    print(f"{'=' * 70}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
