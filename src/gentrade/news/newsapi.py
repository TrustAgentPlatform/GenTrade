"""NewsAPI.org provider implementation for fetching financial and stock-specific news.

This module implements the NewsProviderBase abstract class to retrieve general market news
and stock-specific news via the NewsAPI.org API. It supports filtering by time interval,
article count, and language, while formatting results into standardized NewsInfo objects.
"""

from typing import List
from datetime import datetime, timedelta
import requests
from loguru import logger

from gentrade.news.meta import NewsInfo, NewsProviderBase

class NewsApiProvider(NewsProviderBase):
    """News provider that uses NewsAPI.org to fetch financial and stock-specific news.

    Authenticates with a NewsAPI.org API key, then retrieves news articles via the
    "everything" endpoint. Supports both market-wide news (using financial queries)
    and stock-specific news (using ticker symbols).
    """

    def __init__(self, api_key: str):
        """Initialize the NewsApiProvider with a NewsAPI.org API key.

        Args:
            api_key: API key for authenticating requests to NewsAPI.org.
        """
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2/everything"  # Core endpoint for news retrieval

    def fetch_latest_market_news(
        self,
        category: str = "business",
        max_hour_interval: int = 24,
        max_count: int = 10
    ) -> List[NewsInfo]:
        """Fetch latest general market news from NewsAPI.org.

        Retrieves financial market news from the last `max_hour_interval` hours, limited to
        `max_count` articles, and assigns the specified category. Results are sorted by
        publication time (newest first) and restricted to English.

        Args:
            category: Category label to assign to fetched news (default: "business").
            max_hour_interval: Maximum age (in hours) of articles to retrieve (default: 24).
            max_count: Maximum number of articles to return (default: 10).

        Returns:
            List of NewsInfo objects with formatted market news; empty list if fetch fails
            or no results exist.
        """
        # Calculate start time for news retrieval (current time minus max_hour_interval)
        start_time = (datetime.now() - timedelta(hours=max_hour_interval)).isoformat()

        params = {
            "q": "financial market OR stock market",  # Query for financial market news
            "apiKey": self.api_key,
            "language": "en",  # Restrict to English-language articles
            "sortBy": "publishedAt",  # Sort by newest first
            "from": start_time
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()  # Raise error for HTTP status codes ≥400
            articles = response.json().get("articles", [])  # Extract articles from response

            # Convert API response to standardized NewsInfo objects
            news_list = [
                NewsInfo(
                    category=category,
                    datetime=self._timestamp_to_epoch(article.get("publishedAt", "")),
                    headline=article.get("title", ""),
                    id=self.url_to_hash_id(article.get("url", "")),
                    image=article.get("urlToImage", ""),  # Article thumbnail (if available)
                    related="",  # No stock ticker for general market news
                    source=article.get("source", {}).get("name", ""),  # News source name
                    summary=article.get("description", ""),  # Short article preview
                    url=article.get("url", ""),  # Direct article URL
                    content="",  # Content extracted later by aggregator
                    provider='newsapi',
                    market='us'
                )
                for article in articles
            ]

            return self._filter_news(news_list, max_hour_interval, max_count)

        except requests.RequestException as e:
            logger.debug(f"Failed to fetch market news from NewsAPI.org: {e}")
            return []
        except Exception as e:
            logger.debug(f"Unexpected error: {e}")
            return []

    def fetch_stock_news(
        self,
        ticker: str,
        category: str = "business",
        max_hour_interval: int = 24,
        max_count: int = 10
    ) -> List[NewsInfo]:
        """Fetch stock-specific news for a given ticker from NewsAPI.org.

        Retrieves news related to the specified stock ticker from the last `max_hour_interval`
        hours, limited to `max_count` articles, and assigns the specified category. Results
        are sorted by publication time (newest first) and restricted to English.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL") to fetch news for.
            category: Category label to assign to fetched news (default: "business").
            max_hour_interval: Maximum age (in hours) of articles to retrieve (default: 24).
            max_count: Maximum number of articles to return (default: 10).

        Returns:
            List of NewsInfo objects with formatted stock news; empty list if fetch fails
            or no results exist.
        """
        # Calculate start time for news retrieval
        start_time = (datetime.now() - timedelta(hours=max_hour_interval)).isoformat()

        params = {
            "q": ticker,  # Ticker-specific query to target stock-related news
            "apiKey": self.api_key,
            "language": "en",
            "sortBy": "publishedAt",
            "from": start_time
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            articles = response.json().get("articles", [])

            # Convert API response to standardized NewsInfo objects
            news_list = [
                NewsInfo(
                    category=category,
                    datetime=self._timestamp_to_epoch(article.get("publishedAt", "")),
                    headline=article.get("title", ""),
                    id=hash(article.get("url", "")),
                    image=article.get("urlToImage", ""),
                    related=ticker,  # Associate with target stock ticker
                    source=article.get("source", {}).get("name", ""),
                    summary=article.get("description", ""),
                    url=article.get("url", ""),
                    content="",
                    provider='newsapi',
                    market='us'
                )
                for article in articles
            ]

            return self._filter_news(news_list, max_hour_interval, max_count)

        except requests.RequestException as e:
            logger.debug(f"Failed to fetch {ticker} stock news from NewsAPI.org: {e}")
            return []
