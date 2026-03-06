"""Analysis pipeline that bridges CrewAI execution with the LogEntry streaming system."""

import asyncio
from collections.abc import AsyncGenerator
import random
import re
from typing import Any

from src.core.config.enums import ProcessingStage, StatusType, SubStage
from src.core.config.models import LogEntry
from src.crew.facts import build_task_facts
from src.crew.structured_output import (
    serialize_structured_output,
    validate_task_output,
)

_TASK_SUBSTAGE_MAP = {
    "validate_data_sanity": SubStage.VALIDATING_DATA_SANITY,
    "analyze_valuation_ratios": SubStage.ANALYZING_VALUATION_RATIOS,
    "analyze_price_performance": SubStage.ANALYZING_PRICE_PERFORMANCE,
    "analyze_financial_health": SubStage.ANALYZING_FINANCIAL_HEALTH,
    "analyze_market_sentiment": SubStage.ANALYZING_MARKET_SENTIMENT,
    "review_analysis": SubStage.REVIEWING_ANALYSIS,
    "generate_investment_report": SubStage.GENERATING_INVESTMENT_REPORT,
}
_RATE_LIMIT_WAIT_RE = re.compile(r"Please try again in ([0-9]+(?:\.[0-9]+)?)s", re.IGNORECASE)
_MAX_RATE_LIMIT_RETRIES = 3
_RATE_LIMIT_JITTER_SECONDS = (0.2, 0.8)


def _extract_retry_wait(error: Exception) -> float:
    match = _RATE_LIMIT_WAIT_RE.search(str(error))
    return float(match.group(1)) if match else 2.0


def _is_rate_limit_error(error: Exception) -> bool:
    msg = str(error).lower()
    return "rate_limit_exceeded" in msg or "rate limit reached" in msg


def _raw_text(task_output: Any) -> str:
    raw = getattr(task_output, "raw", None)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return str(task_output).strip()


class AnalysisPipeline:
    """Runs the CrewAI stock analysis crew and yields LogEntry objects for UI streaming."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.success: bool = False

    def _log(self, substage: SubStage | None, status: StatusType, message: str | None = None) -> LogEntry:
        return LogEntry(
            stage=ProcessingStage.ANALYZING,
            substage=substage,
            status_type=status,
            message=message,
            symbol=self.symbol,
        )

    async def run(self) -> AsyncGenerator[LogEntry, None]:
        """Execute the analysis crew, yielding progress entries. Sets self.success."""
        yield self._log(None, StatusType.IN_PROGRESS, "Starting AI-powered analysis...")

        try:
            from src.crew.crew import StockAnalysisCrew

            crew = StockAnalysisCrew().crew()
            task_names = [getattr(t, "name", None) or f"task_{i}" for i, t in enumerate(crew.tasks, 1)]
            total = len(task_names)
            completed = 0
            loop = asyncio.get_running_loop()
            progress_q: asyncio.Queue[tuple[str, int]] = asyncio.Queue()

            def on_task_done(_output: Any) -> None:
                nonlocal completed
                completed += 1
                if completed < total:
                    loop.call_soon_threadsafe(progress_q.put_nowait, (task_names[completed], completed + 1))

            crew.task_callback = on_task_done

            result = None
            rate_limit_retries = 0
            started_substages: set[SubStage] = set()

            while True:
                try:
                    if task_names:
                        await progress_q.put((task_names[0], 1))

                    kickoff_task = asyncio.create_task(
                        crew.kickoff_async(inputs={"symbol": self.symbol})
                    )

                    while not kickoff_task.done() or not progress_q.empty():
                        try:
                            task_name, index = await asyncio.wait_for(progress_q.get(), timeout=0.2)
                        except asyncio.TimeoutError:
                            continue

                        substage = _TASK_SUBSTAGE_MAP.get(task_name)
                        if not substage or substage in started_substages:
                            continue

                        started_substages.add(substage)
                        yield self._log(
                            substage,
                            StatusType.IN_PROGRESS,
                            f"{substage.display_name}...",
                        )

                    result = await kickoff_task
                    break

                except Exception as exc:
                    if _is_rate_limit_error(exc) and rate_limit_retries < _MAX_RATE_LIMIT_RETRIES:
                        wait = _extract_retry_wait(exc) + random.uniform(*_RATE_LIMIT_JITTER_SECONDS)
                        rate_limit_retries += 1
                        yield self._log(
                            None, StatusType.IN_PROGRESS,
                            f"Rate limit hit. Retrying in {wait:.1f}s ({rate_limit_retries}/{_MAX_RATE_LIMIT_RETRIES})...",
                        )
                        await asyncio.sleep(wait)
                        continue
                    raise

            if result is None:
                raise RuntimeError("Crew returned no result")

            deterministic_facts = build_task_facts(self.symbol)

            for task_output in getattr(result, "tasks_output", None) or []:
                task_name = getattr(task_output, "name", None)
                substage = _TASK_SUBSTAGE_MAP.get(task_name)

                structured_model = validate_task_output(task_name, task_output)
                output_text = (
                    serialize_structured_output(task_name, structured_model)
                    if structured_model
                    else _raw_text(task_output)
                )

                facts_text = deterministic_facts.get(task_name or "", "")
                if facts_text:
                    output_text = f"{facts_text}\n\n{output_text}" if output_text else facts_text

                if not output_text:
                    continue

                if substage:
                    if substage not in started_substages:
                        yield self._log(substage, StatusType.IN_PROGRESS)
                    yield self._log(substage, StatusType.SUCCESS, output_text)
                else:
                    yield self._log(None, StatusType.SUCCESS, output_text)

            if not getattr(result, "tasks_output", None):
                report_facts = deterministic_facts.get("generate_investment_report", "")
                raw_output = str(result).strip()
                output_text = f"{report_facts}\n\n{raw_output}" if report_facts else raw_output
                yield self._log(SubStage.GENERATING_INVESTMENT_REPORT, StatusType.SUCCESS, output_text)

            self.success = True

        except Exception as exc:
            yield self._log(None, StatusType.FAILED, f"Analysis failed: {exc}")
            self.success = False
