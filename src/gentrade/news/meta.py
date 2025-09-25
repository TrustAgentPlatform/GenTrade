"""Module for fetching, storing, and managing financial news from multiple providers.

Defines core components for news handling:
- `NewsInfo`: Dataclass representing structured news articles.
- `NewsProviderBase`: Abstract base class for news provider implementations.
- `NewsDatabase`: In-memory storage for news articles with sync tracking.

Supports fetching market-wide and stock-specific news, with filtering by time and count.
"""

import abc
import logging
import time
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass

import requests

LOG = logging.getLogger(__name__)

NEWS_MARKET = [
    'us', 'zh', 'hk', 'cypto', 'common'
]

@dataclass
class NewsInfo:
    """Dataclass representing a structured news article with core metadata."""
    category: str
    datetime: int  # Epoch timestamp in seconds
    headline: str
    id: int
    image: str
    related: str   # Related stock ticker(s) or empty string
    source: str
    summary: str
    url: str
    content: str
    provider: str  # provder like newsapi, google, finnhub, rss
    market: str    # market type like us, chn, eur, hk, crypto

    def to_dict(self) -> Dict[str, Any]:
        """Convert NewsInfo object to a dictionary.

        Returns:
            Dictionary with keys matching the dataclass fields.
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
            "url": self.url,
            "content": self.content,
            "provider": self.provider,
            "market": self.market,
        }

    def fetch_article_html(self) -> Optional[str]:
        """Fetch raw HTML content from the article's direct URL.

        Uses a browser-like user agent to avoid being blocked by servers.

        Returns:
            Raw HTML string if successful; None if request fails.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            response = requests.get(self.url, headers=headers, timeout=15)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            LOG.debug(f"Failed to fetch HTML for {self.url}: {e}")
            return None


class NewsProviderBase(metaclass=abc.ABCMeta):
    """Abstract base class defining the interface for news providers.

    All concrete news providers (e.g., NewsAPI, Finnhub) must implement these methods.
    """

    @abc.abstractmethod
    def fetch_latest_market_news(
        self,
        category: str = "business",
        max_hour_interval: int = 24,
        max_count: int = 10
    ) -> List[NewsInfo]:
        """Fetch latest general market news within a time and count constraint.

        Args:
            category: News category to filter (default: "business").
            max_hour_interval: Maximum age (in hours) of articles to include.
            max_count: Maximum number of articles to return.

        Returns:
            List of NewsInfo objects matching the criteria.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_stock_news(
        self,
        ticker: str,
        category: str = "business",
        max_hour_interval: int = 24,
        max_count: int = 10
    ) -> List[NewsInfo]:
        """Fetch news specific to a stock ticker within a time and count constraint.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL") to fetch news for.
            category: News category to filter (default: "business").
            max_hour_interval: Maximum age (in hours) of articles to include.
            max_count: Maximum number of articles to return.

        Returns:
            List of NewsInfo objects related to the specified ticker.
        """
        raise NotImplementedError

    def _timestamp_to_epoch(self, timestamp: str) -> int:
        """Convert ISO 8601 timestamp to epoch seconds.

        Args:
            timestamp: ISO format string (e.g., "2023-01-01T12:00:00Z").

        Returns:
            Epoch timestamp in seconds. Uses current time if conversion fails.
        """
        try:
            # Handle 'Z' suffix for UTC by replacing with +00:00
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return int(dt.timestamp())
        except ValueError:
            return int(time.time())

    def _filter_news(
        self,
        news_list: List[NewsInfo],
        max_hour_interval: int,
        max_count: int
    ) -> List[NewsInfo]:
        """Filter news articles by recency and limit results to max_count.

        Args:
            news_list: List of NewsInfo objects to filter.
            max_hour_interval: Maximum age (in hours) for inclusion.
            max_count: Maximum number of articles to return.

        Returns:
            Filtered list sorted by recency (implicit via original order).
        """
        current_time = int(time.time())
        time_threshold = current_time - (max_hour_interval * 3600)

        # Include only articles newer than the threshold
        filtered_news = [news for news in news_list if news.datetime >= time_threshold]

        # Limit to max_count results
        return filtered_news[:max_count]

    def url_to_hash_id(self, url: str) -> int:
        """Convert URL string to hash int value"""
        return int(hashlib.sha256(url.encode()).hexdigest(), 16)

class NewsDatabase:
    """In-memory database for storing news articles with sync tracking.

    Uses article URLs as unique keys to avoid duplicates. Tracks last sync time
    to prevent excessive fetching.
    """

    def __init__(self):
        """Initialize an empty database with last sync time set to 0."""
        self.news_dict: Dict[str, NewsInfo] = {}  # Key: article URL
        self.last_sync: float = 0.0  # Epoch time of last successful sync

    def add_news(self, news_list: List[NewsInfo]) -> None:
        """Add news articles to the database, skipping duplicates.

        Args:
            news_list: List of NewsInfo objects to store.
        """
        for news in news_list:
            # Use URL as unique identifier to avoid duplicates
            if news.url and news.url not in self.news_dict:
                self.news_dict[news.url] = news

    def get_all_news(self) -> List[NewsInfo]:
        """Retrieve all stored news articles.

        Returns:
            List of all NewsInfo objects in the database.
        """
        return list(self.news_dict.values())

    def get_market_news(self, market='us') -> List[NewsInfo]:
        """Retrieve stored news articles for given market.

        Args:
            market: Market name, by default is US.

        Returns:
            List of all NewsInfo objects in the database.
        """
        assert market in NEWS_MARKET
        market_news = []
        for item in self.news_dict.values():
            if item.market == market:
                market_news.append(item)
        return market_news
