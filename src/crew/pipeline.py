"""Analysis pipeline that bridges CrewAI execution with the LogEntry streaming system."""

from collections.abc import Generator
import time

from src.core.config.config import ENABLE_OUTPUT_CLEANUP_FALLBACK
from src.core.config.enums import ProcessingStage, StatusType, SubStage
from src.core.config.models import LogEntry
from src.crew.facts import build_task_facts
from src.crew.structured_output import (
    STRUCTURED_OUTPUT_POLICY,
    has_structured_schema,
    serialize_structured_output,
    should_retry_structured_error,
    validate_task_output,
)
from src.crew.utils import fallback_cleanup, sanitize_output, should_apply_fallback_cleanup

_TASK_SUBSTAGE_MAP = {
    "analyze_valuation_ratios": SubStage.ANALYZING_VALUATION_RATIOS,
    "analyze_price_performance": SubStage.ANALYZING_PRICE_PERFORMANCE,
    "analyze_financial_health": SubStage.ANALYZING_FINANCIAL_HEALTH,
    "analyze_market_sentiment": SubStage.ANALYZING_MARKET_SENTIMENT,
    "review_analysis": SubStage.REVIEWING_ANALYSIS,
    "generate_investment_report": SubStage.GENERATING_INVESTMENT_REPORT,
}


class AnalysisPipeline:
    """Runs the CrewAI stock analysis crew and yields LogEntry objects for UI streaming.

    Returns True on success, False on failure — so the caller knows whether
    to show "Successfully processed" or not.
    """

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.stage = ProcessingStage.ANALYZING

    def _log(self, substage: SubStage | None, status: StatusType, message: str | None = None) -> LogEntry:
        return LogEntry(
            stage=self.stage,
            substage=substage,
            status_type=status,
            message=message,
            symbol=self.symbol,
        )

    def run(self) -> Generator[LogEntry, None, bool]:
        """Execute the analysis crew. Returns True on success, False on failure."""
        yield self._log(None, StatusType.IN_PROGRESS, "Starting AI-powered analysis...")

        try:
            from src.crew.crew import StockAnalysisCrew

            crew_instance = StockAnalysisCrew()
            result = None
            max_attempts = max(1, STRUCTURED_OUTPUT_POLICY.max_retry_attempts + 1)
            for attempt in range(1, max_attempts + 1):
                try:
                    result = crew_instance.crew().kickoff(inputs={"symbol": self.symbol})
                    break
                except Exception as exc:
                    if attempt < max_attempts and should_retry_structured_error(exc):
                        yield self._log(
                            None,
                            StatusType.IN_PROGRESS,
                            f"Structured output parse issue. Retrying analysis ({attempt}/{max_attempts - 1})...",
                        )
                        time.sleep(STRUCTURED_OUTPUT_POLICY.retry_backoff_seconds * attempt)
                        continue
                    raise

            if result is None:
                raise RuntimeError("Crew returned no result")
            deterministic_facts = build_task_facts(self.symbol)

            if hasattr(result, "tasks_output") and result.tasks_output:
                for task_output in result.tasks_output:
                    task_name = task_output.name if hasattr(task_output, "name") else None
                    substage = _TASK_SUBSTAGE_MAP.get(task_name)
                    structured_model = validate_task_output(task_name, task_output)
                    if structured_model is None and has_structured_schema(task_name) and STRUCTURED_OUTPUT_POLICY.strict_validation:
                        raise ValueError(f"Structured output validation failed for task: {task_name}")

                    structured_text = serialize_structured_output(task_name, structured_model) if structured_model else ""
                    output_text = sanitize_output(structured_text or str(task_output))
                    facts_text = deterministic_facts.get(task_name or "", "")
                    if ENABLE_OUTPUT_CLEANUP_FALLBACK and should_apply_fallback_cleanup(output_text):
                        output_text = sanitize_output(fallback_cleanup(output_text))
                    if facts_text:
                        output_text = f"{facts_text}\n\n{output_text}" if output_text else facts_text

                    if not output_text:
                        continue

                    if substage:
                        yield self._log(substage, StatusType.IN_PROGRESS)
                        yield self._log(substage, StatusType.SUCCESS, output_text)
                    else:
                        yield self._log(None, StatusType.SUCCESS, output_text)
            else:
                report_facts = deterministic_facts.get("generate_investment_report", "")
                report_output = (
                    sanitize_output(fallback_cleanup(str(result)))
                    if ENABLE_OUTPUT_CLEANUP_FALLBACK and should_apply_fallback_cleanup(str(result))
                    else sanitize_output(str(result))
                )
                output_text = f"{report_facts}\n\n{report_output}" if report_facts else report_output
                yield self._log(
                    SubStage.GENERATING_INVESTMENT_REPORT,
                    StatusType.SUCCESS,
                    output_text,
                )

            return True

        except Exception as exc:
            yield self._log(None, StatusType.FAILED, f"Analysis failed: {exc}")
            return False
