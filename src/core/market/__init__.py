# SPDX-License-Identifier: MIT
"""Data operations for stock data."""

from src.core.market.benchmark import BenchmarkFetcher
from src.core.market.fetcher import StockDataFetcher
from src.core.market.news import NewsFetcher
from src.core.market.stock_data import (
    BenchmarkData,
    Financials,
    MarketIntel,
    PriceHistory,
    StockData,
)
from src.core.market.storage import CSVStorage
from src.core.market.trends import TrendsFetcher

__all__ = [
    "BenchmarkFetcher",
    "StockDataFetcher",
    "NewsFetcher",
    "TrendsFetcher",
    "CSVStorage",
    "StockData",
    "BenchmarkData",
    "PriceHistory",
    "Financials",
    "MarketIntel",
]
