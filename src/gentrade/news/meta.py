"""Module for fetching, storing, and managing financial news from multiple providers.

Defines core components for news handling:
- `NewsInfo`: Dataclass representing structured news articles.
- `NewsProviderBase`: Abstract base class for news provider implementations.
- `NewsDatabase`: In-memory storage for news articles with sync tracking.

Supports fetching market-wide and stock-specific news, with filtering by time and count.
"""
import os
import json
import abc
import time
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from loguru import logger
import requests

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
    related: list[str]   # Related stock ticker(s) or empty list
    source: str
    summary: str
    url: str
    content: str
    provider: str  # provder like newsapi, finnhub, rss
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
            logger.debug(f"Failed to fetch HTML for {self.url}: {e}")
            return None

class NewsProviderBase(metaclass=abc.ABCMeta):
    """Abstract base class defining the interface for news providers.

    All concrete news providers (e.g., NewsAPI, Finnhub) must implement these methods.
    """

    @property
    def market(self) -> str:
        """Get the market identifier this provider is associated with.

        Defaults to 'common' for providers that cover general markets.
        Concrete providers may override this to specify a specific market (e.g., 'us', 'cn').

        Returns:
            str: Market identifier string.
        """
        return 'common'

    @property
    def is_available(self) -> bool:
        """Check if the news provider is currently available/operational.

        Defaults to True. Concrete providers may override this to implement
        availability checks (e.g., API status, rate limits, connectivity).

        Returns:
            bool: True if provider is available, False otherwise.
        """
        return True

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
        # Fetch 2x max_count general news to allow ticker filtering
        general_news = self.fetch_latest_market_news(
            category=category,
            max_hour_interval=max_hour_interval,
            max_count=max_count * 2
        )

        # Filter articles where ticker is in headline or summary (case-insensitive)
        ticker_lower = ticker.lower()
        ticker_news = [
            news for news in general_news
            if ticker_lower in news.headline.lower()
            or ticker_lower in news.summary.lower()
        ]

        # Update "related" field to link articles to the target ticker
        for news in ticker_news:
            news.related.append(ticker)

        # Limit to max_count results
        return ticker_news[:max_count]

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

    def filter_news(
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
        self.news_list: List[NewsInfo] = []
        self.last_sync = 0

    def add_news(self, news_list: List[NewsInfo]) -> None:
        """Add news articles to the database, skipping duplicates.

        Args:
            news_list: List of NewsInfo objects to store.
        """
        news_hash_cache_list = [item.id for item in self.news_list]
        for news in news_list:
            if news.id in news_hash_cache_list:
                logger.error("news %s already in the cache list" % news.id)
                continue
            self.news_list.append(news)

    def get_all_news(self) -> List[NewsInfo]:
        """Retrieve all stored news articles.

        Returns:
            List of all NewsInfo objects in the database.
        """
        return self.news_list

    def get_market_news(self, market='us') -> List[NewsInfo]:
        """Retrieve stored news articles for given market.

        Args:
            market: Market name, by default is US.

        Returns:
            List of all NewsInfo objects in the database.
        """
        assert market in NEWS_MARKET
        market_news = []
        for item in self.news_list:
            if item.market == market:
                market_news.append(item)
        return market_news


class NewsFileDatabase(NewsDatabase):

    def __init__(self, filepath):
        super().__init__()
        self._filepath = filepath
        if os.path.exists(self._filepath):
            self.load()

    def save(self):
        news_dicts = [news.to_dict() for news in self.news_list]
        content = {
            "last_sync": self.last_sync,
            "news_list": news_dicts
        }
        with open(self._filepath, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=4)  # indent for readability

    def load(self):
        with open(self._filepath, 'r', encoding='utf-8') as f:
            content = json.load(f)  # Directly loads JSON content into a Python list/dict
        self.last_sync = content['last_sync']
        self.news_list = [NewsInfo(**item_dict) for item_dict in content['news_list']]
        logger.info(self.news_list)
