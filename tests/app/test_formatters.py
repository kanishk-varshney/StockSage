from src.app.utils.formatters import format_log_entry
from src.core.config.enums import ProcessingStage, StatusType, SubStage
from src.core.config.models import LogEntry


def test_format_log_entry_renders_report_card_with_gauge():
    entry = LogEntry(
        stage=ProcessingStage.ANALYZING,
        substage=SubStage.GENERATING_INVESTMENT_REPORT,
        status_type=StatusType.SUCCESS,
        symbol="AAPL",
        message=(
            "COMPANY BASICS:\n"
            "Company Name: Apple Inc.\n"
            "Ticker: AAPL\n"
            "Sector: Technology\n"
            "RECOMMENDATION\n"
            "VERDICT: BUY | Confidence: High\n"
        ),
    )

    html = format_log_entry(entry)

    assert "log-analysis" in html
    assert "Company Profile" in html
    assert "gauge-container" in html
    assert "BUY" in html
