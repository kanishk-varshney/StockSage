"""CSV reader tool for loading stock data from the .market_data/ directory."""

from pathlib import Path
from typing import Any

import pandas as pd
from crewai.tools import BaseTool


DATA_DIR = Path(__file__).resolve().parents[3] / ".market_data"


class CSVReaderTool(BaseTool):
    """Reads a CSV file for a given stock symbol from the data directory."""

    name: str = "csv_reader"
    description: str = (
        "Reads a CSV data file for a stock symbol. "
        "Parameters: symbol (e.g. 'AAPL'), file_name (e.g. 'income_statement.csv'). "
        "Available files: company_info.csv, historical_prices.csv, daily.csv, "
        "income_statement.csv, quarterly_income_statement.csv, "
        "balance_sheet.csv, quarterly_balance_sheet.csv, "
        "cash_flow.csv, quarterly_cash_flow.csv, "
        "recommendations.csv, insider_transactions.csv, "
        "institutional_holders.csv, major_holders.csv, "
        "dividends.csv, splits.csv, earnings_dates.csv, "
        "news.csv, market_index.csv, sector_index.csv"
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
