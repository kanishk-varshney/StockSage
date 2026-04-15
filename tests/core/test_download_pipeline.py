"""Download pipeline failure and success branches with mocked fetchers (no network)."""

from __future__ import annotations

import pandas as pd

from src.core.config.enums import StatusType, SubStage
from src.core.market.stock_data import Financials, MarketIntel, PriceHistory
from src.core.processing import download_pipeline as dp


class FakeFetcher:
    """Minimal fetcher stub for DownloadPipeline tests."""

    def __init__(
        self,
        *,
        profile: dict | None = None,
        prices: PriceHistory | None = None,
        financials: Financials | None = None,
        intel: MarketIntel | None = None,
    ):
        self._profile = profile if profile is not None else {"longName": "ACME"}
        self._prices = prices
        self._financials = financials
        self._intel = intel if intel is not None else MarketIntel()

    def fetch_company_profile(self) -> dict:
        return self._profile

    def fetch_price_history(self) -> PriceHistory:
        return self._prices if self._prices is not None else PriceHistory()

    def fetch_financials(self) -> Financials:
        return self._financials if self._financials is not None else Financials()

    def fetch_market_intel(self) -> MarketIntel:
        return self._intel


def _bench_mock(*_a, **_k):
    class _B:
        def fetch_market_index(self):
            return pd.DataFrame(), ""

        def fetch_sector_index(self):
            return pd.DataFrame(), ""

    return _B()


def _news_mock(*_a, **_k):
    class _N:
        def fetch(self):
            return []

    return _N()


def _trends_mock(*_a, **_k):
    class _T:
        def fetch(self):
            return pd.DataFrame()

    return _T()


def test_aborts_when_no_company_profile(monkeypatch):
    monkeypatch.setattr(dp.time, "sleep", lambda *_a, **_k: None)
    p = dp.DownloadPipeline("ZAP")
    p.fetcher = FakeFetcher(profile={})
    entries = list(p.run())
    assert p.critical_ok is False
    assert any(
        e.substage == SubStage.DOWNLOADING_COMPANY_PROFILE and e.status_type == StatusType.FAILED
        for e in entries
    )


def test_aborts_when_no_price_data(monkeypatch):
    monkeypatch.setattr(dp.time, "sleep", lambda *_a, **_k: None)
    p = dp.DownloadPipeline("ZAP")
    p.fetcher = FakeFetcher(profile={"longName": "ZAP"}, prices=PriceHistory())
    list(p.run())
    assert p.critical_ok is False


def test_aborts_when_no_financials(monkeypatch):
    monkeypatch.setattr(dp.time, "sleep", lambda *_a, **_k: None)
    ph = PriceHistory()
    ph.daily = pd.DataFrame({"Close": [1.0, 2.0]})
    p = dp.DownloadPipeline("ZAP")
    p.fetcher = FakeFetcher(profile={"longName": "ZAP"}, prices=ph, financials=Financials())
    list(p.run())
    assert p.critical_ok is False


def test_critical_ok_when_full_path_succeeds(monkeypatch, tmp_path):
    monkeypatch.setattr(dp.time, "sleep", lambda *_a, **_k: None)
    monkeypatch.setattr(dp, "BenchmarkFetcher", _bench_mock)
    monkeypatch.setattr(dp, "NewsFetcher", _news_mock)
    monkeypatch.setattr(dp, "TrendsFetcher", _trends_mock)

    class OkStorage:
        def save(self, _stock_data):
            return ["a.csv"]

    monkeypatch.setattr(dp, "CSVStorage", OkStorage)

    ph = PriceHistory()
    ph.daily = pd.DataFrame({"Close": [1.0, 2.0, 3.0]})
    fin = Financials()
    fin.income_statement = pd.DataFrame({"rev": [1]})

    p = dp.DownloadPipeline("OK")
    p.fetcher = FakeFetcher(profile={"longName": "OK Corp"}, prices=ph, financials=fin)
    list(p.run())
    assert p.critical_ok is True


def test_save_failure_sets_critical_ok_false(monkeypatch):
    monkeypatch.setattr(dp.time, "sleep", lambda *_a, **_k: None)
    monkeypatch.setattr(dp, "BenchmarkFetcher", _bench_mock)
    monkeypatch.setattr(dp, "NewsFetcher", _news_mock)
    monkeypatch.setattr(dp, "TrendsFetcher", _trends_mock)

    class BoomStorage:
        def save(self, _stock_data):
            raise OSError("disk full")

    monkeypatch.setattr(dp, "CSVStorage", BoomStorage)

    ph = PriceHistory()
    ph.daily = pd.DataFrame({"Close": [1.0, 2.0]})
    fin = Financials()
    fin.income_statement = pd.DataFrame({"rev": [1]})

    p = dp.DownloadPipeline("BAD")
    p.fetcher = FakeFetcher(profile={"longName": "BAD"}, prices=ph, financials=fin)
    entries = list(p.run())
    assert p.critical_ok is False
    assert any(
        e.substage == SubStage.SAVING_DATA and e.status_type == StatusType.FAILED for e in entries
    )
