"""Deterministic facts builder for stable UI metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd
from src.core.config.data_contracts import (
    CSV_CASH_FLOW,
    CSV_COMPANY_INFO,
    CSV_HISTORICAL_PRICES,
    CSV_INCOME_STATEMENT,
    CSV_INSTITUTIONAL_HOLDERS,
    CSV_MARKET_INDEX,
    CSV_NEWS,
    CSV_RECOMMENDATIONS,
    DATA_DIR,
)


def build_task_facts(symbol: str) -> dict[str, str]:
    sym = symbol.upper()
    company = _read_csv(sym, CSV_COMPANY_INFO)
    prices = _read_csv(sym, CSV_HISTORICAL_PRICES)
    market = _read_csv(sym, CSV_MARKET_INDEX)
    income = _read_csv(sym, CSV_INCOME_STATEMENT)
    cash = _read_csv(sym, CSV_CASH_FLOW)
    recs = _read_csv(sym, CSV_RECOMMENDATIONS)
    holders = _read_csv(sym, CSV_INSTITUTIONAL_HOLDERS)
    news = _read_csv(sym, CSV_NEWS)

    company_row = company.iloc[0] if company is not None and not company.empty else pd.Series(dtype=object)

    facts: dict[str, str] = {}
    facts["analyze_valuation_ratios"] = _valuation_facts(company_row, cash, sym)
    facts["analyze_price_performance"] = _performance_facts(prices, market)
    facts["analyze_financial_health"] = _financial_health_facts(company_row, income, cash)
    facts["analyze_market_sentiment"] = _sentiment_facts(recs, holders, news)
    facts["generate_investment_report"] = _company_basics_facts(company_row, sym, recs, holders, prices, market)
    return facts


def _read_csv(symbol: str, file_name: str) -> pd.DataFrame | None:
    path = DATA_DIR / symbol / file_name
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def _f(row: pd.Series, key: str, default: float | None = None) -> float | None:
    if key not in row:
        return default
    val = row.get(key)
    if pd.isna(val):
        return default
    try:
        return float(val)
    except Exception:
        return default


def _s(row: pd.Series, key: str, default: str = "") -> str:
    if key not in row:
        return default
    val = row.get(key)
    if pd.isna(val):
        return default
    return str(val).strip()


def _fmt_num(val: float | None, suffix: str = "", digits: int = 2, prefix: str = "") -> str:
    if val is None:
        return "N/A"
    return f"{prefix}{val:,.{digits}f}{suffix}"


def _fmt_large(val: float | None) -> str:
    if val is None:
        return "N/A"
    abs_v = abs(val)
    if abs_v >= 1_000_000_000_000:
        return f"${val / 1_000_000_000_000:.2f}T"
    if abs_v >= 1_000_000_000:
        return f"${val / 1_000_000_000:.2f}B"
    if abs_v >= 1_000_000:
        return f"${val / 1_000_000:.2f}M"
    return f"${val:,.0f}"


def _series_close(df: pd.DataFrame | None) -> np.ndarray:
    if df is None or df.empty or "Close" not in df.columns:
        return np.array([])
    s = pd.to_numeric(df["Close"], errors="coerce").dropna()
    return s.to_numpy(dtype=float)


def _to_usd_billions(val: float | None) -> str:
    if val is None:
        return "N/A"
    return f"${val / 1_000_000_000:.2f}B"


def _valuation_facts(row: pd.Series, cash: pd.DataFrame | None, symbol: str) -> str:
    lines = [
        "FINANCIAL SNAPSHOT",
        f"P/E (x): {_fmt_num(_f(row, 'trailingPE'), 'x')}",
        f"Forward P/E (x): {_fmt_num(_f(row, 'forwardPE'), 'x')}",
        f"P/B (x): {_fmt_num(_f(row, 'priceToBook'), 'x')}",
        f"P/S (x): {_fmt_num(_f(row, 'priceToSalesTrailing12Months'), 'x')}",
        f"ROE (%): {_fmt_num(_f(row, 'returnOnEquity', 0) * 100 if _f(row, 'returnOnEquity') is not None else None, '%')}",
        f"ROA (%): {_fmt_num(_f(row, 'returnOnAssets', 0) * 100 if _f(row, 'returnOnAssets') is not None else None, '%')}",
        f"Gross Margin (%): {_fmt_num(_f(row, 'grossMargins', 0) * 100 if _f(row, 'grossMargins') is not None else None, '%')}",
        "",
        "INSIGHT",
        "Insight: Valuation is rich; watch earnings growth to justify current multiples.",
    ]
    if cash is not None and "Free Cash Flow" in cash.iloc[:, 0].values:
        try:
            idx = cash.iloc[:, 0] == "Free Cash Flow"
            val = pd.to_numeric(cash.loc[idx].iloc[0, 1], errors="coerce")
            if not pd.isna(val):
                lines.insert(8, f"Free Cash Flow (USD B): {_to_usd_billions(float(val))}")
        except Exception:
            pass
    return "\n".join(lines)


def _performance_facts(prices: pd.DataFrame | None, market: pd.DataFrame | None) -> str:
    sp = _series_close(prices)
    mp = _series_close(market)
    if len(sp) < 3:
        return "PERFORMANCE & RISK\nInsight: Insufficient price history to compute reliable performance metrics."

    total = (sp[-1] - sp[0]) / sp[0]
    annualized = (1 + total) ** (252 / len(sp)) - 1
    sr = np.diff(sp) / sp[:-1]
    vol = float(np.std(sr, ddof=1) * np.sqrt(252)) if len(sr) > 1 else 0.0
    peak = np.maximum.accumulate(sp)
    mdd = float(np.min((sp - peak) / peak))

    beta = None
    if len(mp) >= 3:
        min_len = min(len(sp), len(mp))
        sr2 = np.diff(sp[:min_len]) / sp[: min_len - 1]
        mr2 = np.diff(mp[:min_len]) / mp[: min_len - 1]
        cov = np.cov(sr2, mr2)
        if cov[1, 1] != 0:
            beta = float(cov[0, 1] / cov[1, 1])

    lines = [
        "PERFORMANCE & RISK",
        f"Total Return (%): {_fmt_num(total * 100, '%')}",
        f"Annualized Return (%): {_fmt_num(annualized * 100, '%')}",
        f"Volatility (%): {_fmt_num(vol * 100, '%')}",
        f"Max Drawdown (%): {_fmt_num(mdd * 100, '%')}",
        f"Beta (vs market): {_fmt_num(beta, 'x')}",
        "",
        "INSIGHT",
        "Insight: Risk is acceptable for growth investors if drawdowns are tolerated.",
    ]
    return "\n".join(lines)


def _financial_health_facts(row: pd.Series, income: pd.DataFrame | None, cash: pd.DataFrame | None) -> str:
    lines = ["FINANCIAL HEALTH"]

    rev_growth = _f(row, "revenueGrowth")
    earn_growth = _f(row, "earningsGrowth")
    if rev_growth is not None:
        lines.append(f"Revenue Growth (%): {_fmt_num(rev_growth * 100, '%')}")
    if earn_growth is not None:
        lines.append(f"Earnings Growth (%): {_fmt_num(earn_growth * 100, '%')}")

    lines.extend(
        [
            f"Debt/Equity: {_fmt_num(_f(row, 'debtToEquity'))}",
            f"Current Ratio: {_fmt_num(_f(row, 'currentRatio'))}",
            f"Operating Cash Flow (USD B): {_to_usd_billions(_f(row, 'operatingCashflow'))}",
        ]
    )

    if income is not None and not income.empty and "Total Revenue" in income.iloc[:, 0].values:
        try:
            revenue_row = income[income.iloc[:, 0] == "Total Revenue"].iloc[0, 1:4]
            revenue_vals = pd.to_numeric(revenue_row, errors="coerce").dropna().to_numpy()
            if len(revenue_vals) >= 2:
                yoy = (revenue_vals[0] - revenue_vals[1]) / revenue_vals[1]
                lines.append(f"Revenue YoY (%): {_fmt_num(float(yoy) * 100, '%')}")
        except Exception:
            pass

    if cash is not None and not cash.empty and "Free Cash Flow" in cash.iloc[:, 0].values:
        try:
            fcf_row = cash[cash.iloc[:, 0] == "Free Cash Flow"].iloc[0, 1:3]
            fcf_vals = pd.to_numeric(fcf_row, errors="coerce").dropna().to_numpy()
            if len(fcf_vals) >= 2 and fcf_vals[1] != 0:
                fcf_yoy = (fcf_vals[0] - fcf_vals[1]) / fcf_vals[1]
                lines.append(f"Free Cash Flow YoY (%): {_fmt_num(float(fcf_yoy) * 100, '%')}")
        except Exception:
            pass

    lines.extend(["", "INSIGHT", "Insight: Balance sheet remains stable with healthy cash generation."])
    return "\n".join(lines)


def _sentiment_facts(recs: pd.DataFrame | None, holders: pd.DataFrame | None, news: pd.DataFrame | None) -> str:
    lines = ["SENTIMENT & ANALYST SUMMARY"]
    if recs is not None and not recs.empty:
        latest = recs.iloc[0]
        sb = int(pd.to_numeric(latest.get("strongBuy", 0), errors="coerce") or 0)
        b = int(pd.to_numeric(latest.get("buy", 0), errors="coerce") or 0)
        h = int(pd.to_numeric(latest.get("hold", 0), errors="coerce") or 0)
        s = int(pd.to_numeric(latest.get("sell", 0), errors="coerce") or 0)
        ss = int(pd.to_numeric(latest.get("strongSell", 0), errors="coerce") or 0)
        buy_count = sb + b
        sell_count = s + ss
        total = sb + b + h + s + ss
        signal = "Neutral"
        if buy_count > sell_count + h:
            signal = "Positive"
        elif sell_count > buy_count + h:
            signal = "Negative"
        lines.extend(
            [
                f"Analyst Consensus: Buy {buy_count} | Hold {h} | Sell {sell_count} ({total} analysts)",
                f"Sentiment Signal: {signal}",
            ]
        )

    lines.extend(["", "OWNERSHIP"])
    if holders is not None and not holders.empty and "Holder" in holders.columns:
        top = holders.head(3)
        holder_names = ", ".join(str(x) for x in top["Holder"].tolist())
        lines.append(f"Top Holders: {holder_names}")

    lines.extend(["", "INSIGHT", "Insight: Analyst positioning remains constructive, but monitor revision trend.", "", "RELATED NEWS"])
    if news is not None and not news.empty and "url" in news.columns:
        lines.append("News Status: Latest cached news")
        news_rows = news.head(3).fillna("")
        for _, row in news_rows.iterrows():
            title = str(row.get("title", "")).strip()
            publisher = str(row.get("publisher", "")).strip().strip("{}").replace("'", "")
            url = str(row.get("url", "")).strip()
            if title and url:
                lines.append(f"News: {title} | {publisher or 'source'} | {url}")
    else:
        lines.append("News Status: No recent news available")
    return "\n".join(lines)


def _company_basics_facts(
    row: pd.Series,
    symbol: str,
    recs: pd.DataFrame | None,
    holders: pd.DataFrame | None,
    prices: pd.DataFrame | None,
    market: pd.DataFrame | None,
) -> str:
    name = _s(row, "longName") or _s(row, "shortName") or symbol
    lines = [
        "COMPANY BASICS:",
        f"Company Name: {name}",
        f"Ticker: {symbol}",
        f"Sector: {_s(row, 'sector')}",
        f"Segment: {_s(row, 'industry')}",
        f"Price (USD): {_fmt_num(_f(row, 'currentPrice'), prefix='$')}",
        f"Market Cap: {_fmt_large(_f(row, 'marketCap'))}",
    ]

    peers: list[str] = []
    if holders is not None and not holders.empty and "Holder" in holders.columns:
        peers = [str(x) for x in holders["Holder"].dropna().head(5).tolist()]
    if not peers and recs is not None and not recs.empty:
        peers = ["Peer data not available in local files"]
    lines.append(f"Peers: {', '.join(peers) if peers else 'N/A'}")

    sp = _series_close(prices)
    mp = _series_close(market)
    stock_change = "N/A"
    market_change = "N/A"
    if len(sp) >= 2:
        stock_change = f"{((sp[-1] - sp[-2]) / sp[-2]) * 100:.2f}%"
    if len(mp) >= 2:
        market_change = f"{((mp[-1] - mp[-2]) / mp[-2]) * 100:.2f}%"

    lines.extend(
        [
            "",
            "RECOMMENDATION",
            "VERDICT: HOLD | Confidence: Medium",
            "",
            "MARKET PULSE",
            f"Mini Screener: Valuation=Watch | Momentum=Positive | Risk=Moderate | Sentiment=Constructive",
            f"Ticker Tape: {symbol} {_fmt_num(_f(row, 'currentPrice'), prefix='$')} ({stock_change}) | S&P 500 ({market_change}) [cached]",
        ]
    )
    return "\n".join(lines)

