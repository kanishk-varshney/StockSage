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
    assert 'data-section="company-header"' in html
    assert "Apple Inc." in html
    assert "Overall Verdict" in html
    assert "BUY" in html


def test_formatter_golden_snippet_for_report_card():
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
            "Structured Summary: Durable cash generation and strong margins.\n"
            "RECOMMENDATION\n"
            "VERDICT: BUY | Confidence: High\n"
        ),
    )
    html = format_log_entry(entry)

    assert '<span class="w-3 h-3 rounded-full' in html
    assert "Overall Verdict" in html
