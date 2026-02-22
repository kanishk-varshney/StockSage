"""CSV reader tool for loading stock data from the .market_data/ directory."""

from typing import Any

import pandas as pd
from crewai.tools import BaseTool

from src.core.config.data_contracts import (
    CSV_BALANCE_SHEET,
    CSV_CASH_FLOW,
    CSV_COMPANY_INFO,
    CSV_DAILY_PRICES,
    CSV_DIVIDENDS,
    CSV_EARNINGS_DATES,
    CSV_HISTORICAL_PRICES,
    CSV_INCOME_STATEMENT,
    CSV_INSIDER_TRANSACTIONS,
    CSV_INSTITUTIONAL_HOLDERS,
    CSV_MAJOR_HOLDERS,
    CSV_MARKET_INDEX,
    CSV_NEWS,
    CSV_QUARTERLY_BALANCE_SHEET,
    CSV_QUARTERLY_CASH_FLOW,
    CSV_QUARTERLY_INCOME_STATEMENT,
    CSV_RECOMMENDATIONS,
    CSV_SECTOR_INDEX,
    CSV_SPLITS,
    DATA_DIR,
)


class CSVReaderTool(BaseTool):
    """Reads a CSV file for a given stock symbol from the data directory."""

    name: str = "csv_reader"
    description: str = (
        "Reads a CSV data file for a stock symbol. "
        f"Parameters: symbol (e.g. 'AAPL'), file_name (e.g. '{CSV_INCOME_STATEMENT}'). "
        f"Available files: {CSV_COMPANY_INFO}, {CSV_HISTORICAL_PRICES}, {CSV_DAILY_PRICES}, "
        f"{CSV_INCOME_STATEMENT}, {CSV_QUARTERLY_INCOME_STATEMENT}, "
        f"{CSV_BALANCE_SHEET}, {CSV_QUARTERLY_BALANCE_SHEET}, "
        f"{CSV_CASH_FLOW}, {CSV_QUARTERLY_CASH_FLOW}, "
        f"{CSV_RECOMMENDATIONS}, {CSV_INSIDER_TRANSACTIONS}, "
        f"{CSV_INSTITUTIONAL_HOLDERS}, {CSV_MAJOR_HOLDERS}, "
        f"{CSV_DIVIDENDS}, {CSV_SPLITS}, {CSV_EARNINGS_DATES}, "
        f"{CSV_NEWS}, {CSV_MARKET_INDEX}, {CSV_SECTOR_INDEX}"
    )

    def _run(self, symbol: str, file_name: str) -> str:
        csv_path = DATA_DIR / symbol.upper() / file_name
        if not csv_path.exists():
            return f"Error: File not found — {csv_path}"

        try:
            df = pd.read_csv(csv_path)
            if df.empty:
                return f"File {file_name} for {symbol} is empty."

            # company_info is a single-row wide table — transpose for readability
            if file_name == "company_info.csv" and len(df) <= 2:
                info_lines = []
                for col in df.columns:
                    val = df[col].iloc[0]
                    if pd.notna(val) and str(val).strip():
                        info_lines.append(f"{col}: {val}")
                return "\n".join(info_lines)

            return df.to_string(max_rows=60, max_cols=20)
        except Exception as e:
            return f"Error reading {file_name}: {e}"
