"""Module for fetching and storing financial news from multiple providers.

This module defines a `NewsInfo` dataclass for news articles, an abstract `NewsAPIProvider`
for fetching news, specific provider implementations (NewsAPI.org, Finnhub, Google Custom Search),
a factory for creating providers, an in-memory database, and an aggregator for periodic news
syncing.
"""

import abc
import logging
import os
import time
from typing import Dict, List, Any

from datetime import datetime
from dataclasses import dataclass
import requests

LOG = logging.getLogger(__name__)


@dataclass
class NewsInfo:
    """Represents a news article with structured fields."""
    category: str
    datetime: int
    headline: str
    id: int
    image: str
    related: str
    source: str
    summary: str
    url: str

    def to_dict(self) -> Dict[str, Any]:
        """Converts the NewsInfo object to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of the news article.
        """
        return {
            "category": self.category,
            "datetime": self.datetime,
            "headline": self.headline,
            "id": self.id,
            "image": self.image,
            "related": self.related,
            "source": self.source,
            "summary": self.summary,
            "url": self.url
        }


class NewsAPIProvider(metaclass=abc.ABCMeta):
    """Abstract base class for news provider implementations."""

    @abc.abstractmethod
    def fetch_latest_market_news(self, category: str = "business") -> List[NewsInfo]:
        """Fetches latest financial market news.

        Args:
            category (str): News category (default: "business").

        Returns:
            List[NewsInfo]: List of news articles.
        """
        #pylint: disable=unnecessary-pass
        pass

    @abc.abstractmethod
    def fetch_stock_news(self, ticker: str, category: str = "business") -> List[NewsInfo]:
        """Fetches news for a specific stock by ticker.

        Args:
            ticker (str): Stock ticker symbol.
            category (str): News category (default: "business").

        Returns:
            List[NewsInfo]: List of news articles related to the stock.
        """
        #pylint: disable=unnecessary-pass
        pass

    def _timestamp_to_epoch(self, timestamp: str) -> int:
        """Converts ISO timestamp to epoch time.

        Args:
            timestamp (str): ISO format timestamp (e.g., "2023-01-01T12:00:00Z").

        Returns:
            int: Epoch timestamp in seconds, or current time if conversion fails.
        """
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return int(dt.timestamp())
        except ValueError:
            return int(time.time())


class NewsApiAdapter(NewsAPIProvider):
    """NewsAPI.org provider implementation."""

    def __init__(self, api_key: str):
        """Initializes NewsAPI.org provider.

        Args:
            api_key (str): API key for NewsAPI.org.
        """
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2/everything"

    def fetch_latest_market_news(self, category: str = "business") -> List[NewsInfo]:
        """Fetches latest financial market news from NewsAPI.org."""
        params = {
            "q": "financial market OR stock market",
            "apiKey": self.api_key,
            "language": "en",
            "sortBy": "publishedAt"
        }
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            articles = response.json().get("articles", [])
            return [
                NewsInfo(
                    category=category,
                    datetime=self._timestamp_to_epoch(article.get("publishedAt", "")),
                    headline=article.get("title", ""),
                    id=hash(article.get("url", "")),
                    image=article.get("urlToImage", ""),
                    related="",
                    source=article.get("source", {}).get("name", ""),
                    summary=article.get("description", ""),
                    url=article.get("url", "")
                ) for article in articles
            ]
        except requests.RequestException as e:
            LOG.debug(f"Error fetching market news from NewsAPI: {e}")
            return []

    def fetch_stock_news(self, ticker: str, category: str = "business") -> List[NewsInfo]:
        """Fetches stock-specific news from NewsAPI.org."""
        params = {
            "q": ticker,
            "apiKey": self.api_key,
            "language": "en",
            "sortBy": "publishedAt"
        }
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            articles = response.json().get("articles", [])
            return [
                NewsInfo(
                    category=category,
                    datetime=self._timestamp_to_epoch(article.get("publishedAt", "")),
                    headline=article.get("title", ""),
                    id=hash(article.get("url", "")),
                    image=article.get("urlToImage", ""),
                    related=ticker,
                    source=article.get("source", {}).get("name", ""),
                    summary=article.get("description", ""),
                    url=article.get("url", "")
                ) for article in articles
            ]
        except requests.RequestException as e:
            LOG.debug(f"Error fetching stock news from NewsAPI: {e}")
            return []


class FinnhubNewsProvider(NewsAPIProvider):
    """Finnhub.io provider implementation."""

    def __init__(self, api_key: str):
        """Initializes Finnhub.io provider.

        Args:
            api_key (str): API key for Finnhub.io.
        """
        self.api_key = api_key
        self.base_url = "https://finnhub.io/api/v1"

    def fetch_latest_market_news(self, category: str = "business") -> List[NewsInfo]:
        """Fetches latest financial market news from Finnhub.io."""
        params = {"category": "general", "token": self.api_key}
        try:
            response = requests.get(f"{self.base_url}/news", params=params, timeout=10)
            response.raise_for_status()
            articles = response.json()
            return [
                NewsInfo(
                    category=category,
                    datetime=article.get("datetime", int(time.time())),
                    headline=article.get("headline", ""),
                    id=article.get("id", hash(article.get("url", ""))),
                    image=article.get("image", ""),
                    related=article.get("related", ""),
                    source=article.get("source", ""),
                    summary=article.get("summary", ""),
                    url=article.get("url", "")
                ) for article in articles
            ]
        except requests.RequestException as e:
            LOG.debug(f"Error fetching market news from Finnhub: {e}")
            return []

    def fetch_stock_news(self, ticker: str, category: str = "business") -> List[NewsInfo]:
        """Fetches stock-specific news from Finnhub.io."""
        params = {"symbol": ticker, "token": self.api_key}
        try:
            response = requests.get(f"{self.base_url}/company-news", params=params, timeout=10)
            response.raise_for_status()
            articles = response.json()
            return [
                NewsInfo(
                    category=category,
                    datetime=article.get("datetime", int(time.time())),
                    headline=article.get("headline", ""),
                    id=article.get("id", hash(article.get("url", ""))),
                    image=article.get("image", ""),
                    related=ticker,
                    source=article.get("source", ""),
                    summary=article.get("summary", ""),
                    url=article.get("url", "")
                ) for article in articles
            ]
        except requests.RequestException as e:
            LOG.debug(f"Error fetching stock news from Finnhub: {e}")
            return []


class GoogleNewsProvider(NewsAPIProvider):
    """Google Custom Search provider implementation."""

    def __init__(self, api_key: str, cse_id: str):
        """Initializes Google Custom Search provider.

        Args:
            api_key (str): API key for Google Cloud.
            cse_id (str): Custom Search Engine ID.
        """
        self.api_key = api_key
        self.cse_id = cse_id
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    def fetch_latest_market_news(self, category: str = "business") -> List[NewsInfo]:
        """Fetches latest financial market news from Google Custom Search."""
        params = {"key": self.api_key, "cx": self.cse_id, "q": "financial market news",
            "sort": "date"}
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            items = response.json().get("items", [])
            return [
                NewsInfo(
                    category=category,
                    datetime=int(time.time()),
                    headline=item.get("title", ""),
                    id=hash(item.get("link", "")),
                    image=item.get("pagemap", {}).get("cse_image", [{}])[0].get("src", ""),
                    related="",
                    source=item.get("displayLink", ""),
                    summary=item.get("snippet", ""),
                    url=item.get("link", "")
                ) for item in items
            ]
        except requests.RequestException as e:
            LOG.debug(f"Error fetching market news from Google: {e}")
            return []

    def fetch_stock_news(self, ticker: str, category: str = "business") -> List[NewsInfo]:
        """Fetches stock-specific news from Google Custom Search."""
        params = {"key": self.api_key, "cx": self.cse_id, "q": f"{ticker} stock news",
            "sort": "date"}
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            items = response.json().get("items", [])
            return [
                NewsInfo(
                    category=category,
                    datetime=int(time.time()),
                    headline=item.get("title", ""),
                    id=hash(item.get("link", "")),
                    image=item.get("pagemap", {}).get("cse_image", [{}])[0].get("src", ""),
                    related=ticker,
                    source=item.get("displayLink", ""),
                    summary=item.get("snippet", ""),
                    url=item.get("link", "")
                ) for item in items
            ]
        except requests.RequestException as e:
            LOG.debug(f"Error fetching stock news from Google: {e}")
            return []


class NewsFactory:
    """Factory for creating news provider instances."""

    @staticmethod
    def create_provider(provider_type: str, **kwargs) -> NewsAPIProvider:
        """Creates a news provider instance based on the provider type.

        Args:
            provider_type (str): Type of provider ("newsapi", "finnhub", or "google").
            **kwargs: Additional arguments for provider initialization.

        Returns:
            NewsAPIProvider: Instance of the specified news provider.

        Raises:
            ValueError: If provider type is unknown or required environment variables are not set.
        """
        providers = {
            "newsapi": NewsApiAdapter,
            "finnhub": FinnhubNewsProvider,
            "google": GoogleNewsProvider
        }
        provider_class = providers.get(provider_type.lower())
        if not provider_class:
            raise ValueError(f"Unknown provider type: {provider_type}")

        if provider_type.lower() == "newsapi":
            api_key = os.getenv("NEWSAPI_API_KEY")
            if not api_key:
                raise ValueError("NEWSAPI_API_KEY environment variable not set")
            return provider_class(api_key=api_key)
        if provider_type.lower() == "finnhub":
            api_key = os.getenv("FINNHUB_API_KEY")
            if not api_key:
                raise ValueError("FINNHUB_API_KEY environment variable not set")
            return provider_class(api_key=api_key)
        if provider_type.lower() == "google":
            api_key = os.getenv("GOOGLE_CLOUD_API_KEY")
            cse_id = os.getenv("GOOGLE_CSE_ID")
            if not api_key or not cse_id:
                raise ValueError(
                    "GOOGLE_CLOUD_API_KEY or GOOGLE_CSE_ID environment variable not set")
            return provider_class(api_key=api_key, cse_id=cse_id)
        return provider_class(**kwargs)


class NewsDatabase:
    """In-memory database for storing news articles."""

    def __init__(self):
        """Initializes the news database."""
        self.news_dict: Dict[str, NewsInfo] = {}  # Key: URL, Value: NewsInfo
        self.last_sync: float = 0.0

    def add_news(self, news_list: List[NewsInfo]):
        """Adds news articles to the database if not already present.

        Args:
            news_list (List[NewsInfo]): List of news articles to add.
        """
        for news in news_list:
            if news.url and news.url not in self.news_dict:
                self.news_dict[news.url] = news

    def get_all_news(self) -> List[NewsInfo]:
        """Retrieves all stored news articles.

        Returns:
            List[NewsInfo]: List of all news articles in the database.
        """
        return list(self.news_dict.values())


class NewsAggregator:
    """Aggregates news from multiple providers and syncs to database."""

    def __init__(self, providers: List[NewsAPIProvider], db: NewsDatabase):
        """Initializes the news aggregator.

        Args:
            providers (List[NewsAPIProvider]): List of news providers.
            db (NewsDatabase): Database to store news articles.
        """
        self.providers = providers
        self.db = db

    def sync_news(self, ticker: str = None, category: str = "business"):
        """Syncs news from providers if last sync was more than 1 hour ago.

        Args:
            ticker (str, optional): Stock ticker for stock-specific news. Defaults to None.
            category (str): News category (default: "business").
        """
        current_time = time.time()
        if current_time < self.db.last_sync + 3600:
            LOG.info("Skipping sync: Last sync was less than 1 hour ago.")
            return

        LOG.info("Starting sync...")
        for provider in self.providers:
            if ticker:
                news = provider.fetch_stock_news(ticker, category)
                LOG.info(f"Fetched {len(news)} stock news articles for {ticker} from \
                    {provider.__class__.__name__}")
            else:
                news = provider.fetch_latest_market_news(category)
                LOG.info(f"Fetched {len(news)} market news articles from \
                    {provider.__class__.__name__}")
            self.db.add_news(news)

        self.db.last_sync = current_time
        LOG.info("Sync completed.")


if __name__ == "__main__":
    db = NewsDatabase()
    try:
        newsapi_provider = NewsFactory.create_provider("newsapi")
        finnhub_provider = NewsFactory.create_provider("finnhub")
        google_provider = NewsFactory.create_provider("google")
        aggregator = NewsAggregator(
            providers=[newsapi_provider, finnhub_provider, google_provider],
            db=db
        )
        aggregator.sync_news(category="business")
        aggregator.sync_news(ticker="AAPL", category="business")
        all_news = db.get_all_news()
        LOG.info(f"Total articles in database: {len(all_news)}")
        if all_news:
            LOG.info("Example article:")
            LOG.info(all_news[0].to_dict())
        aggregator.sync_news(category="business")
    except ValueError as e:
        LOG.debug(f"Error: {e}")
