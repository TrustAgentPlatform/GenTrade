"""Finnhub news provider implementation for fetching financial market and stock-specific news.

This module provides a concrete implementation of the NewsProviderBase abstract class,
utilizing the Finnhub.io API to retrieve news articles. It supports both general market news
and news specific to individual stock tickers, with filtering by time interval and article count.
"""

import time
from typing import List
from datetime import datetime, timedelta
import requests
from loguru import logger

from gentrade.news.meta import NewsInfo, NewsProviderBase

class FinnhubNewsProvider(NewsProviderBase):
    """News provider implementation for fetching news via the Finnhub.io API.

    Retrieves both general financial market news and stock-specific news articles using
    the Finnhub API. Implements methods to fetch, parse, and filter news based on time
    intervals and maximum article count.
    """

    def __init__(self, api_key: str):
        """Initialize the FinnhubNewsProvider with the required API key.

        Args:
            api_key: API key for authenticating requests to Finnhub.io.
        """
        self.api_key = api_key
        self.base_url = "https://finnhub.io/api/v1"

    @property
    def market(self):
        return 'us'

    def fetch_latest_market_news(
        self,
        category: str = "business",
        max_hour_interval: int = 24,
        max_count: int = 10
    ) -> List[NewsInfo]:
        """Fetch the latest general market news from Finnhub.io.

        Retrieves news articles from the specified time interval (up to max_hour_interval hours ago)
        and returns up to max_count articles, filtered and formatted as NewsInfo objects.

        Args:
            category: Category to assign to the fetched news (default: "business").
            max_hour_interval: Maximum age (in hours) of articles to fetch (default: 24).
            max_count: Maximum number of articles to return (default: 10).

        Returns:
            List of NewsInfo objects containing the fetched and filtered news articles.
        """
        params = {
            "category": "general",
            "token": self.api_key,
            "from": (datetime.now() - timedelta(hours=max_hour_interval)).strftime("%Y-%m-%d")
        }

        try:
            response = requests.get(
                f"{self.base_url}/news",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            articles = response.json()

            news_list = [
                NewsInfo(
                    category=category,
                    datetime=article.get("datetime", int(time.time())),
                    headline=article.get("headline", ""),
                    id=self.url_to_hash_id(article.get("url", "")),
                    image=article.get("image", ""),
                    related=article.get("related", []),
                    source=article.get("source", ""),
                    summary=article.get("summary", ""),
                    url=article.get("url", ""),
                    content="",
                    provider='finnhub',
                    market='us'
                ) for article in articles
            ]

            return self.filter_news(news_list, max_hour_interval, max_count)

        except requests.RequestException as e:
            logger.debug(f"Error fetching market news from Finnhub: {e}")
            return []

    def fetch_stock_news(
        self,
        ticker: str,
        category: str = "business",
        max_hour_interval: int = 24,
        max_count: int = 10
    ) -> List[NewsInfo]:
        """Fetch stock-specific news for a given ticker from Finnhub.io.

        Retrieves news articles related to the specified stock ticker from the last
        max_hour_interval hours, returning up to max_count articles formatted as NewsInfo objects.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL") to fetch news for.
            category: Category to assign to the fetched news (default: "business").
            max_hour_interval: Maximum age (in hours) of articles to fetch (default: 24).
            max_count: Maximum number of articles to return (default: 10).

        Returns:
            List of NewsInfo objects containing the fetched and filtered stock-specific news.
        """
        params = {
            "symbol": ticker,
            "token": self.api_key,
            "from": (datetime.now() - timedelta(hours=max_hour_interval)).strftime("%Y-%m-%d")
        }

        try:
            response = requests.get(
                f"{self.base_url}/company-news",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            articles = response.json()

            news_list = [
                NewsInfo(
                    category=category,
                    datetime=article.get("datetime", int(time.time())),
                    headline=article.get("headline", ""),
                    id=article.get("id", hash(article.get("url", ""))),
                    image=article.get("image", ""),
                    related=[ticker,],
                    source=article.get("source", ""),
                    summary=article.get("summary", ""),
                    url=article.get("url", ""),
                    content="",
                    provider='finnhub',
                    market='us'
                ) for article in articles
            ]

            return self.filter_news(news_list, max_hour_interval, max_count)

        except requests.RequestException as e:
            logger.debug(f"Error fetching stock news from Finnhub: {e}")
            return []
