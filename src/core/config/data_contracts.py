# SPDX-License-Identifier: MIT
"""Shared filesystem/data contract constants for stock CSV artifacts."""

from src.core.config.config import OUTPUT_DIR_PATH

# Single source of truth for persisted CSV names used across writers/readers/tasks.
CSV_COMPANY_INFO = "company_info.csv"
CSV_DAILY_PRICES = "daily.csv"
CSV_HISTORICAL_PRICES = "historical_prices.csv"
CSV_DIVIDENDS = "dividends.csv"
CSV_SPLITS = "splits.csv"
CSV_INCOME_STATEMENT = "income_statement.csv"
CSV_QUARTERLY_INCOME_STATEMENT = "quarterly_income_statement.csv"
CSV_BALANCE_SHEET = "balance_sheet.csv"
CSV_QUARTERLY_BALANCE_SHEET = "quarterly_balance_sheet.csv"
CSV_CASH_FLOW = "cash_flow.csv"
CSV_QUARTERLY_CASH_FLOW = "quarterly_cash_flow.csv"
CSV_EARNINGS_DATES = "earnings_dates.csv"
CSV_INSTITUTIONAL_HOLDERS = "institutional_holders.csv"
CSV_INSIDER_TRANSACTIONS = "insider_transactions.csv"
CSV_MAJOR_HOLDERS = "major_holders.csv"
CSV_RECOMMENDATIONS = "recommendations.csv"
CSV_NEWS = "news.csv"
CSV_GOOGLE_TRENDS = "google_trends.csv"
CSV_MARKET_INDEX = "market_index.csv"
CSV_SECTOR_INDEX = "sector_index.csv"

# Dataclass field-name -> persisted filename mapping used by CSVStorage.
CSV_FILE_BY_FIELD = {
    "daily": CSV_DAILY_PRICES,
    "dividends": CSV_DIVIDENDS,
    "splits": CSV_SPLITS,
    "income_statement": CSV_INCOME_STATEMENT,
    "quarterly_income_statement": CSV_QUARTERLY_INCOME_STATEMENT,
    "balance_sheet": CSV_BALANCE_SHEET,
    "quarterly_balance_sheet": CSV_QUARTERLY_BALANCE_SHEET,
    "cash_flow": CSV_CASH_FLOW,
    "quarterly_cash_flow": CSV_QUARTERLY_CASH_FLOW,
    "earnings_dates": CSV_EARNINGS_DATES,
    "institutional_holders": CSV_INSTITUTIONAL_HOLDERS,
    "insider_transactions": CSV_INSIDER_TRANSACTIONS,
    "major_holders": CSV_MAJOR_HOLDERS,
    "recommendations": CSV_RECOMMENDATIONS,
    "news": CSV_NEWS,
    "google_trends": CSV_GOOGLE_TRENDS,
    "market_index": CSV_MARKET_INDEX,
    "sector_index": CSV_SECTOR_INDEX,
}

# Compatibility aliases written alongside canonical files.
CSV_ALIASES_BY_FIELD = {
    "daily": (CSV_HISTORICAL_PRICES,),
}

# Canonical absolute data directory used by both writers and readers.
DATA_DIR = OUTPUT_DIR_PATH
