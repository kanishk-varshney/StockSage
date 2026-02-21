"""Stock symbol processing pipeline."""

from collections.abc import Generator

from src.core.config.enums import ProcessingStage, SubStage, StatusType
from src.core.config.models import LogEntry
from src.core.processing.download_pipeline import DownloadPipeline
from src.core.validation.validation import validate_symbol


class StockProcessor:
    """Orchestrates the full processing pipeline for a stock symbol.

    Pipeline stages: validate -> download -> analyze.
    Each stage yields LogEntry objects for real-time UI streaming.
    """

    def __init__(self, symbol: str):
        self.symbol = symbol.upper()

    def _log(self, stage: ProcessingStage, substage: SubStage | None = None,
             status: StatusType = StatusType.IN_PROGRESS, message: str | None = None) -> LogEntry:
        return LogEntry(stage=stage, substage=substage, status_type=status, message=message, symbol=self.symbol)

    def _validate(self) -> Generator[LogEntry, None, bool]:
        """Validate the stock symbol format and existence."""
        yield self._log(ProcessingStage.VALIDATING)
        yield self._log(ProcessingStage.VALIDATING, SubStage.VALIDATING_SYMBOL)

        result = validate_symbol(self.symbol)
        if not result.is_valid:
            yield self._log(ProcessingStage.VALIDATING, SubStage.VALIDATING_SYMBOL, StatusType.FAILED, result.error_message)
            return False

        yield self._log(ProcessingStage.VALIDATING, SubStage.VALIDATING_SYMBOL, StatusType.SUCCESS)
        return True

    def _download(self) -> Generator[LogEntry, None, bool]:
        """Download all market data for the symbol."""
        yield self._log(ProcessingStage.DOWNLOADING_DATA)

        stock_data = yield from DownloadPipeline(self.symbol).run()

        if stock_data is None or not stock_data.is_valid():
            return False

        self.stock_data = stock_data
        return True

    def _analyze(self) -> Generator[LogEntry, None, bool]:
        """Run CrewAI-powered analysis on downloaded data."""
        from src.crew.pipeline import AnalysisPipeline
        success = yield from AnalysisPipeline(self.symbol).run()
        return success

    def run(self) -> Generator[LogEntry, None, None]:
        """Execute the full pipeline: validate -> download -> analyze."""
        yield self._log(ProcessingStage.STARTING, message=f"Processing symbol: {self.symbol}")

        if not (yield from self._validate()):
            return

        if not (yield from self._download()):
            return

        if not (yield from self._analyze()):
            yield self._log(ProcessingStage.COMPLETE, status=StatusType.FAILED, message=f"Analysis failed for {self.symbol}")
            return

        yield self._log(ProcessingStage.COMPLETE, message=f"Successfully processed {self.symbol}")
