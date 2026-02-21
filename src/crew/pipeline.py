"""Analysis pipeline that bridges CrewAI execution with the LogEntry streaming system."""

from collections.abc import Generator

from src.core.config.config import ENABLE_OUTPUT_CLEANUP_FALLBACK
from src.core.config.enums import ProcessingStage, StatusType, SubStage
from src.core.config.models import LogEntry
from src.crew.facts import build_task_facts
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
            result = crew_instance.crew().kickoff(inputs={"symbol": self.symbol})
            deterministic_facts = build_task_facts(self.symbol)

            if hasattr(result, "tasks_output") and result.tasks_output:
                for task_output in result.tasks_output:
                    task_name = task_output.name if hasattr(task_output, "name") else None
                    substage = _TASK_SUBSTAGE_MAP.get(task_name)
                    output_text = sanitize_output(str(task_output))
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
