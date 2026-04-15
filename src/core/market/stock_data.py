"""Data models for stock market data, grouped by category."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd


def _format_market_cap(value: Optional[float]) -> str:
    if not value:
        return "N/A"
    if value >= 1e12:
        return f"${value / 1e12:.1f}T"
    if value >= 1e9:
        return f"${value / 1e9:.1f}B"
    if value >= 1e6:
        return f"${value / 1e6:.1f}M"
    return f"${value:,.0f}"


def _df_len(df: pd.DataFrame) -> int:
    return len(df) if df is not None and not df.empty else 0


def _df_cols(df: pd.DataFrame) -> int:
    return len(df.columns) if df is not None and not df.empty else 0


@dataclass
class PriceHistory:
    """OHLCV, dividends, and splits data."""

    daily: pd.DataFrame = field(default_factory=pd.DataFrame)
    dividends: pd.DataFrame = field(default_factory=pd.DataFrame)
    splits: pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def summary(self) -> str:
        parts = [f"{_df_len(self.daily)} trading days"]
        if _df_len(self.dividends):
            parts.append(f"{_df_len(self.dividends)} dividends")
        if _df_len(self.splits):
            parts.append(f"{_df_len(self.splits)} splits")
        return ", ".join(parts)

    def is_valid(self) -> bool:
        return not self.daily.empty


@dataclass
class Financials:
    """Income statement, balance sheet, and cash flow (annual + quarterly)."""

    income_statement: pd.DataFrame = field(default_factory=pd.DataFrame)
    quarterly_income_statement: pd.DataFrame = field(default_factory=pd.DataFrame)
    balance_sheet: pd.DataFrame = field(default_factory=pd.DataFrame)
    quarterly_balance_sheet: pd.DataFrame = field(default_factory=pd.DataFrame)
    cash_flow: pd.DataFrame = field(default_factory=pd.DataFrame)
    quarterly_cash_flow: pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def summary(self) -> str:
        annual = _df_cols(self.income_statement)
        quarterly = _df_cols(self.quarterly_income_statement)
        parts = []
        if annual:
            parts.append(f"{annual}yr annual")
        if quarterly:
            parts.append(f"{quarterly}Q quarterly")
        return " + ".join(parts) if parts else "No financial data"

    def has_any(self) -> bool:
        return any(
            not df.empty
            for df in [
                self.income_statement,
                self.balance_sheet,
                self.cash_flow,
            ]
        )


@dataclass
class MarketIntel:
    """Earnings, holders, insider trades, news, trends, and recommendations."""

    earnings_dates: pd.DataFrame = field(default_factory=pd.DataFrame)
    institutional_holders: pd.DataFrame = field(default_factory=pd.DataFrame)
    insider_transactions: pd.DataFrame = field(default_factory=pd.DataFrame)
    major_holders: pd.DataFrame = field(default_factory=pd.DataFrame)
    recommendations: pd.DataFrame = field(default_factory=pd.DataFrame)
    news: List[Dict[str, Any]] = field(default_factory=list)
    google_trends: pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def summary(self) -> str:
        parts = []
        if _df_len(self.earnings_dates):
            parts.append(f"{_df_len(self.earnings_dates)} earnings dates")
        if _df_len(self.institutional_holders):
            parts.append(f"{_df_len(self.institutional_holders)} institutions")
        if _df_len(self.insider_transactions):
            parts.append(f"{_df_len(self.insider_transactions)} insider trades")
        if self.news:
            parts.append(f"{len(self.news)} news articles")
        if _df_len(self.recommendations):
            parts.append(f"{_df_len(self.recommendations)} analyst recs")
        if _df_len(self.google_trends):
            parts.append(f"{_df_len(self.google_trends)} trend points")
        return ", ".join(parts) if parts else "No supplementary data"


@dataclass
class BenchmarkData:
    """Market index and sector benchmark price data for relative analysis."""

    market_index: pd.DataFrame = field(default_factory=pd.DataFrame)
    market_index_name: str = ""
    sector_index: pd.DataFrame = field(default_factory=pd.DataFrame)
    sector_index_name: str = ""

    @property
    def summary(self) -> str:
        parts = []
        if _df_len(self.market_index):
            parts.append(f"{self.market_index_name} ({_df_len(self.market_index)} days)")
        if _df_len(self.sector_index):
            parts.append(f"{self.sector_index_name} ({_df_len(self.sector_index)} days)")
        return ", ".join(parts) if parts else "No benchmark data"


@dataclass
class StockData:
    """Complete bundle of all fetched data for a stock symbol."""

    symbol: str
    company_info: Dict[str, Any] = field(default_factory=dict)
    prices: PriceHistory = field(default_factory=PriceHistory)
    financials: Financials = field(default_factory=Financials)
    market_intel: MarketIntel = field(default_factory=MarketIntel)
    benchmarks: BenchmarkData = field(default_factory=BenchmarkData)

    @property
    def company_summary(self) -> str:
        name = (
            self.company_info.get("longName") or self.company_info.get("shortName") or self.symbol
        )
        sector = self.company_info.get("sector", "N/A")
        market_cap = _format_market_cap(self.company_info.get("marketCap"))
        return f"{self.symbol}: {name} | {sector} | Market Cap: {market_cap}"

    def is_valid(self) -> bool:
        return self.prices.is_valid()
