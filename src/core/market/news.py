# SPDX-License-Identifier: MIT
"""News fetching via Google News (gnews)."""

import logging
from typing import Any, Dict, List

from gnews import GNews

logger = logging.getLogger(__name__)

DEFAULT_NEWS_PERIOD = "30d"
DEFAULT_MAX_RESULTS = 20


class NewsFetcher:
    """Fetches recent news articles for a stock symbol via Google News."""

    def __init__(self, symbol: str, company_name: str = ""):
        self._query = f"{company_name or symbol} stock"

    def fetch(self, max_results: int = DEFAULT_MAX_RESULTS) -> List[Dict[str, Any]]:
        """Fetch news articles. Returns list of article dicts (title, url, published date, publisher)."""
        try:
            gn = GNews(language="en", max_results=max_results, period=DEFAULT_NEWS_PERIOD)
            articles = gn.get_news(self._query)
            return articles if isinstance(articles, list) else []
        except Exception as e:
            logger.warning("Failed to fetch news for '%s': %s", self._query, e)
            return []
