"""Unit tests for FinancialCalculatorTool and its metric handlers."""

import math

import pytest

from src.crew.tools.calculator import (
    FinancialCalculatorTool,
    _parse_number,
    _parse_prices,
    _safe_div,
)


@pytest.fixture
def calc():
    return FinancialCalculatorTool()


# ---------------------------------------------------------------------------
# _parse_number helpers
# ---------------------------------------------------------------------------


def test_parse_number_plain():
    assert _parse_number("42.5") == 42.5


def test_parse_number_percent():
    assert _parse_number("12.5%") == 12.5


def test_parse_number_dollar():
    assert _parse_number("$150.00") == 150.0


def test_parse_number_comma():
    assert _parse_number("1,000") == 1000.0


def test_parse_number_whitespace():
    assert _parse_number("  99 ") == 99.0


# ---------------------------------------------------------------------------
# _parse_prices helpers
# ---------------------------------------------------------------------------


def test_parse_prices_string():
    arr = _parse_prices("100, 110, 120")
    assert list(arr) == [100.0, 110.0, 120.0]


def test_parse_prices_list():
    arr = _parse_prices([10.0, 20.0, 30.0])
    assert list(arr) == [10.0, 20.0, 30.0]


def test_parse_prices_tuple():
    arr = _parse_prices((5.0, 10.0))
    assert list(arr) == [5.0, 10.0]


def test_parse_prices_invalid_type():
    with pytest.raises(ValueError, match="Prices must be"):
        _parse_prices(12345)


# ---------------------------------------------------------------------------
# _safe_div
# ---------------------------------------------------------------------------


def test_safe_div_normal():
    assert _safe_div(10.0, 4.0) == 2.5


def test_safe_div_zero_divisor():
    with pytest.raises(ZeroDivisionError):
        _safe_div(10.0, 0.0, "test")


# ---------------------------------------------------------------------------
# Valuation ratios
# ---------------------------------------------------------------------------


def test_pe_ratio(calc):
    result = calc._run(metric="pe_ratio", price=150.0, earnings_per_share=10.0)
    assert "pe_ratio = 15.0" in result


def test_pb_ratio(calc):
    result = calc._run(metric="pb_ratio", price=200.0, book_value_per_share=50.0)
    assert "pb_ratio = 4.0" in result


def test_ps_ratio(calc):
    result = calc._run(metric="ps_ratio", price=100.0, revenue_per_share=20.0)
    assert "ps_ratio = 5.0" in result


def test_ev_ebitda(calc):
    result = calc._run(metric="ev_ebitda", enterprise_value=500.0, ebitda=50.0)
    assert "ev_ebitda = 10.0" in result


def test_peg_ratio(calc):
    result = calc._run(metric="peg_ratio", pe_ratio=20.0, earnings_growth_rate=10.0)
    assert "peg_ratio = 2.0" in result


# ---------------------------------------------------------------------------
# Profitability ratios — return percentage strings
# ---------------------------------------------------------------------------


def test_roe(calc):
    result = calc._run(metric="roe", net_income=200.0, shareholders_equity=1000.0)
    assert "20.00%" in result


def test_roa(calc):
    result = calc._run(metric="roa", net_income=100.0, total_assets=2000.0)
    assert "5.00%" in result


def test_gross_margin(calc):
    result = calc._run(metric="gross_margin", revenue=1000.0, cost_of_goods_sold=400.0)
    assert "60.0%" in result


def test_net_margin(calc):
    result = calc._run(metric="net_margin", net_income=150.0, revenue=1000.0)
    assert "15.00%" in result


def test_operating_margin(calc):
    result = calc._run(metric="operating_margin", operating_income=250.0, revenue=1000.0)
    assert "25.00%" in result


# ---------------------------------------------------------------------------
# Leverage / liquidity
# ---------------------------------------------------------------------------


def test_debt_to_equity(calc):
    result = calc._run(metric="debt_to_equity", total_debt=400.0, shareholders_equity=1000.0)
    assert "debt_to_equity = 0.4" in result


def test_current_ratio(calc):
    result = calc._run(metric="current_ratio", current_assets=600.0, current_liabilities=300.0)
    assert "current_ratio = 2.0" in result


# ---------------------------------------------------------------------------
# Price-based metrics
# ---------------------------------------------------------------------------


PRICES_UP = "100, 105, 110, 115, 120"
PRICES_FLAT = "100, 100, 100"


def test_returns_positive(calc):
    result = calc._run(metric="returns", prices=PRICES_UP)
    assert "Total:" in result
    assert "Annualized:" in result
    assert "20.00%" in result  # (120-100)/100 = 20%


def test_returns_needs_two_prices(calc):
    result = calc._run(metric="returns", prices="100")
    assert "Error" in result


def test_volatility_string_output(calc):
    result = calc._run(metric="volatility", prices=PRICES_UP)
    assert "annualized" in result


def test_volatility_flat_prices(calc):
    # Flat prices → zero volatility (std=0)
    result = calc._run(metric="volatility", prices=PRICES_FLAT)
    assert "0.00% annualized" in result


def test_sharpe_ratio_returns_number(calc):
    result = calc._run(metric="sharpe_ratio", prices=PRICES_UP, risk_free_rate=0.04)
    assert "sharpe_ratio =" in result


def test_sharpe_ratio_default_rfr(calc):
    result = calc._run(metric="sharpe_ratio", prices=PRICES_UP)
    assert "sharpe_ratio =" in result


def test_max_drawdown_no_drawdown(calc):
    # Monotonically increasing → 0% drawdown
    result = calc._run(metric="max_drawdown", prices=PRICES_UP)
    assert "0.00%" in result


def test_max_drawdown_with_drop(calc):
    result = calc._run(metric="max_drawdown", prices="100, 80, 90")
    assert "-20.00%" in result


def test_beta_correlated(calc):
    # Identical price series → beta = 1.0
    prices = "100, 105, 110, 115, 120"
    result = calc._run(metric="beta", stock_prices=prices, market_prices=prices)
    assert "beta = 1.0" in result


def test_beta_needs_three_points(calc):
    result = calc._run(metric="beta", stock_prices="100, 110", market_prices="100, 110")
    assert "Error" in result


# ---------------------------------------------------------------------------
# Intrinsic value models
# ---------------------------------------------------------------------------


def test_dcf_basic(calc):
    result = calc._run(
        metric="dcf",
        free_cash_flow=1_000_000,
        growth_rate=0.05,
        discount_rate=0.10,
        shares_outstanding=100_000,
    )
    assert "Intrinsic Value:" in result
    assert "/share" in result


def test_dcf_discount_rate_must_exceed_terminal(calc):
    result = calc._run(
        metric="dcf",
        free_cash_flow=1_000_000,
        growth_rate=0.05,
        discount_rate=0.02,  # less than default terminal_growth_rate=0.03
        shares_outstanding=100_000,
    )
    assert "Error" in result


def test_dcf_zero_shares_error(calc):
    result = calc._run(
        metric="dcf",
        free_cash_flow=1_000_000,
        growth_rate=0.05,
        discount_rate=0.10,
        shares_outstanding=0,
    )
    assert "Error" in result


def test_ddm_basic(calc):
    result = calc._run(
        metric="ddm",
        dividend_per_share=2.0,
        dividend_growth_rate=0.03,
        required_return=0.08,
    )
    assert "Intrinsic Value (DDM):" in result
    assert "/share" in result


def test_ddm_no_dividend(calc):
    result = calc._run(
        metric="ddm",
        dividend_per_share=0.0,
        dividend_growth_rate=0.03,
        required_return=0.08,
    )
    assert "not applicable" in result


def test_ddm_required_return_must_exceed_growth(calc):
    result = calc._run(
        metric="ddm",
        dividend_per_share=2.0,
        dividend_growth_rate=0.10,
        required_return=0.05,
    )
    assert "Error" in result


def test_graham_number_basic(calc):
    result = calc._run(metric="graham_number", earnings_per_share=5.0, book_value_per_share=20.0)
    assert "Graham Number:" in result
    expected = math.sqrt(22.5 * 5.0 * 20.0)
    assert f"${expected:,.2f}" in result


def test_graham_number_negative_eps(calc):
    result = calc._run(metric="graham_number", earnings_per_share=-1.0, book_value_per_share=20.0)
    assert "not applicable" in result


def test_graham_number_negative_bvps(calc):
    result = calc._run(metric="graham_number", earnings_per_share=5.0, book_value_per_share=-10.0)
    assert "not applicable" in result


def test_relative_valuation_basic(calc):
    result = calc._run(
        metric="relative_valuation",
        earnings_per_share=10.0,
        sector_pe=20.0,
        market_pe=18.0,
    )
    assert "Sector-based Fair Value:" in result
    assert "Blended Estimate:" in result


def test_relative_valuation_negative_eps(calc):
    result = calc._run(
        metric="relative_valuation",
        earnings_per_share=-2.0,
        sector_pe=20.0,
        market_pe=18.0,
    )
    assert "not applicable" in result


# ---------------------------------------------------------------------------
# FinancialCalculatorTool._run — unknown metric and zero-division
# ---------------------------------------------------------------------------


def test_unknown_metric(calc):
    result = calc._run(metric="unicorn_ratio")
    assert "Unknown metric" in result
    assert "unicorn_ratio" in result


def test_pe_ratio_zero_eps_error(calc):
    result = calc._run(metric="pe_ratio", price=150.0, earnings_per_share=0.0)
    assert "Error" in result
