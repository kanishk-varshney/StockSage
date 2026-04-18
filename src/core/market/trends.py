# SPDX-License-Identifier: MIT
"""Google Trends fetching via pytrends."""

import logging

import pandas as pd
from pytrends.request import TrendReq

logger = logging.getLogger(__name__)


class TrendsFetcher:
    """Fetches Google Trends interest-over-time data for a stock."""

    def __init__(self, keyword: str, timeframe: str = "today 12-m", geo="IN"):
        self._keyword = keyword
        self._timeframe = timeframe
        self._geo = geo

    def fetch(self) -> pd.DataFrame:
        try:
            pt = TrendReq(
                hl="en-US",
                tz=330,
                timeout=(10, 25),
                retries=4,
                backoff_factor=1.0,
            )

            pt.build_payload(
                kw_list=[self._keyword],
                timeframe=self._timeframe,
                geo=self._geo,
            )

            df = pt.interest_over_time()
            if df is not None and not df.empty:
                return df.drop(columns=["isPartial"], errors="ignore")

            logger.warning("Empty trends data for %s", self._keyword)
            return pd.DataFrame()

        except Exception as e:
            logger.warning("Google Trends failed for %s: %s", self._keyword, e)
            return pd.DataFrame()
