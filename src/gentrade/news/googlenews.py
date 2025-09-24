"""Google Custom Search (GCS) news provider for financial news retrieval.

Implements the NewsProviderBase abstract class to fetch general market news and stock-specific
news via Google's Custom Search API. Supports filtering by time interval, article count,
region, and language, while formatting results into standardized NewsInfo objects.
"""

import logging
import time
from typing import List

import requests

from gentrade.news.meta import NewsInfo, NewsProviderBase

LOG = logging.getLogger(__name__)


class GoogleNewsProvider(NewsProviderBase):
    """News provider using Google Custom Search API to retrieve financial news.

    Authenticates with Google Cloud API key and Custom Search Engine (CSE) ID. Fetches
    market-wide or stock-specific news, with built-in filtering for recency and result count.
    """

    def __init__(self, api_key: str, cse_id: str):
        """Initialize GoogleNewsProvider with required authentication credentials.

        Args:
            api_key: Google Cloud API key for Custom Search request authentication.
            cse_id: Google Custom Search Engine (CSE) ID configured for news retrieval.
        """
        self.api_key = api_key
        self.cse_id = cse_id
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    def fetch_latest_market_news(
        self,
        category: str = "business",
        max_hour_interval: int = 24,
        max_count: int = 10
    ) -> List[NewsInfo]:
        """Fetch latest general market news via Google Custom Search.

        Retrieves financial market news from the last `max_hour_interval` hours, limited to
        `max_count` articles, and assigns the specified category.

        Args:
            category: Category label for fetched news (default: "business").
            max_hour_interval: Maximum age (in hours) of articles to retrieve (default: 24).
            max_count: Maximum number of articles to return (default: 10).

        Returns:
            List of NewsInfo objects with formatted market news; empty list if fetch fails
            or no results exist.
        """
        params = {
            "key": self.api_key,
            "cx": self.cse_id,
            "q": "finance stock market",  # Core query for market news
            "num": max_count,
            "dateRestrict": f"h{max_hour_interval}",  # Filter by recent hours
            "gl": "us",  # Focus on US region results
            "lr": "lang_en",  # Restrict to English language
            "siteSearch": "news.google.com",  # Limit to Google News sources
            "siteSearchFilter": "i"  # Exclude duplicate results
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()  # Raise error for HTTP status codes ≥400
            items = response.json().get("items", [])  # Extract articles from response

            # Convert API response to standardized NewsInfo objects
            news_list = [
                NewsInfo(
                    category=category,
                    datetime=int(time.time()),  # Google CSE lacks article timestamp
                    headline=item.get("title", ""),
                    id=hash(item.get("link", "")),  # Unique ID from article URL
                    image=item.get("pagemap", {}).get("cse_image", [{}])[0].get("src", ""),
                    related="",  # No stock ticker for general market news
                    source=item.get("displayLink", ""),  # Source domain (e.g., "bloomberg.com")
                    summary=item.get("snippet", ""),  # Short article preview
                    url=item.get("link", ""),  # Direct article URL
                    content="",  # Content extracted later by aggregator
                    provider='google',
                    market='us'
                )
                for item in items
            ]

            return self._filter_news(news_list, max_hour_interval, max_count)

        except requests.RequestException as e:
            LOG.debug(f"Failed to fetch market news from Google Custom Search: {e}")
            return []

    def fetch_stock_news(
        self,
        ticker: str,
        category: str = "business",
        max_hour_interval: int = 24,
        max_count: int = 10
    ) -> List[NewsInfo]:
        """Fetch stock-specific news for a given ticker via Google Custom Search.

        Retrieves news related to the specified stock ticker from the last `max_hour_interval`
        hours, limited to `max_count` articles, and assigns the specified category.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL") to fetch news for.
            category: Category label for fetched news (default: "business").
            max_hour_interval: Maximum age (in hours) of articles to retrieve (default: 24).
            max_count: Maximum number of articles to return (default: 10).

        Returns:
            List of NewsInfo objects with formatted stock news; empty list if fetch fails
            or no results exist.
        """
        params = {
            "key": self.api_key,
            "cx": self.cse_id,
            "q": f"{ticker} stock news",  # Ticker-specific query
            "num": max_count,
            "dateRestrict": f"h{max_hour_interval}",  # Filter by recent hours
            "sort": "date"  # Sort results by most recent first
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            items = response.json().get("items", [])

            # Convert API response to standardized NewsInfo objects
            news_list = [
                NewsInfo(
                    category=category,
                    datetime=int(time.time()),  # Google CSE lacks article timestamp
                    headline=item.get("title", ""),
                    id=hash(item.get("link", "")),  # Unique ID from URL
                    image=item.get("pagemap", {}).get("cse_image", [{}])[0].get("src", ""),
                    related=ticker,  # Associate with target stock ticker
                    source=item.get("displayLink", ""),
                    summary=item.get("snippet", ""),
                    url=item.get("link", ""),
                    content="",  # Content extracted later
                    provider='google',
                    market='us'
                )
                for item in items
            ]

            return self._filter_news(news_list, max_hour_interval, max_count)

        except requests.RequestException as e:
            LOG.debug(f"Failed to fetch {ticker} stock news from Google Custom Search: {e}")
            return []
