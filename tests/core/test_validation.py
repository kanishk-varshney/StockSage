import pandas as pd

from src.core.validation import validation


def test_validate_symbol_accepts_us_symbol_with_market_check(monkeypatch):
    class FakeTicker:
        def history(self, period: str):
            return pd.DataFrame({"Close": [100.0]})

    monkeypatch.setattr(validation.yf, "Ticker", lambda symbol: FakeTicker())
    result = validation.validate_symbol("aapl")

    assert result.is_valid is True
    assert result.market == "US"


def test_validate_symbol_rejects_invalid_format_without_market_call():
    result = validation.validate_symbol("AAPL1234")

    assert result.is_valid is False
    assert result.error_code == validation.ValidationErrorCode.INVALID_FORMAT.value
