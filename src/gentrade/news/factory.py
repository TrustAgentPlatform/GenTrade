"""News aggregation module for fetching, processing, and storing news articles from multiple
   providers.

This module includes a factory for creating news provider instances and an aggregator for
synchronizing news from these providers to a database, with functionality to extract and clean
article content.
"""

import os
import logging
import time
import threading
import random
from typing import List, Optional, Set
from urllib.parse import urlparse  # Add this to extract domain from URL

import requests
from gentrade.scraper.extractor import ArticleContentExtractor
from newspaper import Article
from bs4 import BeautifulSoup

from gentrade.news.meta import NewsInfo, NewsProviderBase, NewsDatabase
from gentrade.news.googlenews import GoogleNewsProvider
from gentrade.news.newsapi import NewsApiProvider
from gentrade.news.rss import RssProvider
from gentrade.news.finnhub import FinnhubNewsProvider

LOG = logging.getLogger(__name__)


class NewsFactory:
    """Factory class for creating news provider instances based on provider type.

    Provides a static method to instantiate the appropriate news provider (e.g., NewsAPI,
    Finnhub) using the specified type and required configuration parameters.
    """

    @staticmethod
    def create_provider(provider_type: str, **kwargs) -> NewsProviderBase:
        """Create a news provider instance based on the specified provider type.

        Args:
            provider_type: Type of news provider. Supported values: "newsapi", "finnhub",
                "google", "rss".
           ** kwargs: Additional keyword arguments for provider initialization (e.g., feed_url
                for RSS providers).

        Returns:
            Instance of the specified news provider, subclassed from NewsProviderBase.

        Raises:
            ValueError: If the provider type is unknown or required environment variables
                for initialization are missing.
        """
        provider_type_lower = provider_type.lower()
        providers = {
            "newsapi": NewsApiProvider,
            "finnhub": FinnhubNewsProvider,
            "google": GoogleNewsProvider,
            "rss": RssProvider
        }

        provider_class = providers.get(provider_type_lower)
        if not provider_class:
            raise ValueError(f"Unknown provider type: {provider_type}")

        if provider_type_lower == "newsapi":
            api_key = os.getenv("NEWSAPI_API_KEY")
            if not api_key:
                raise ValueError("NEWSAPI_API_KEY environment variable not set")
            return provider_class(api_key=api_key)

        if provider_type_lower == "finnhub":
            api_key = os.getenv("FINNHUB_API_KEY")
            if not api_key:
                raise ValueError("FINNHUB_API_KEY environment variable not set")
            return provider_class(api_key=api_key)

        if provider_type_lower == "google":
            api_key = os.getenv("GOOGLE_CLOUD_API_KEY")
            cse_id = os.getenv("GOOGLE_CSE_ID")
            if not api_key or not cse_id:
                raise ValueError(
                    "GOOGLE_CLOUD_API_KEY or GOOGLE_CSE_ID environment variable not set"
                )
            return provider_class(api_key=api_key, cse_id=cse_id)

        if provider_type_lower == "rss":
            feed_url = kwargs.get("feed_url", os.getenv("RSS_FEED_URL"))
            return provider_class(feed_url=feed_url)

        return provider_class(**kwargs)


class NewsAggregator:
    """Aggregates news articles from multiple providers and synchronizes them to a database.

    Fetches news from configured providers, processes article content (extracts text from URLs),
    and stores results in a database. Includes logic to avoid frequent syncs.
    """

    def __init__(self, providers: List[NewsProviderBase], db: NewsDatabase):
        """Initialize the NewsAggregator with a list of providers and a database.

        Args:
            providers: List of news provider instances (subclasses of NewsProviderBase).
            db: Database instance for storing news articles (subclass of NewsDatabase).
        """
        self.providers = providers
        self.db = db
        self.db_lock = threading.Lock()

        # 1. Add blocklist (stores blocked domain names, e.g., "example.com")
        self.blocklist: Set[str] = set()

        # 2. Add dummy content keywords (expand this list based on your needs)
        self.dummy_keywords = {
            "we use cookies", "cookie policy", "analyze website traffic",
            "accept cookies", "reject cookies", "by continuing to use",
            "this website uses cookies", "improve user experience",
            "ads by", "sponsored content", "subscribe to access"
        }
        #self.blocklist = self._load_blocklist()

    def _load_blocklist(self) -> Set[str]:
        try:
            with open("news_blocklist.txt", "r", encoding="utf-8") as f:
                return set(line.strip() for line in f if line.strip())
        except FileNotFoundError:
            return set()

    def _save_blocklist(self) -> None:
        with open("news_blocklist.txt", "w", encoding="utf-8") as f:
            for domain in self.blocklist:
                f.write(f"{domain}\n")

    def _fetch_thread(self, provider, aggregator, ticker, category,
        max_hour_interval, max_count, is_process=False):
        if ticker:
            news = provider.fetch_stock_news(
                ticker, category, max_hour_interval, max_count
            )
            LOG.info(
                f"Fetched {len(news)} stock news articles for {ticker} from "
                f"{provider.__class__.__name__}"
            )
        else:
            news = provider.fetch_latest_market_news(
                category, max_hour_interval, max_count
            )
            LOG.info(
                f"Fetched {len(news)} market news articles from "
                f"{provider.__class__.__name__}"
            )

        ace = ArticleContentExtractor.inst()
        for item in news:
            item.summary = ace.clean_html(item.summary)
            if is_process:
                item.content = ace.extract_content(item.url)
                LOG.info(item.content)

        with aggregator.db_lock:
            aggregator.db.add_news(news)

    def sync_news(
        self,
        ticker: Optional[str] = None,
        category: str = "business",
        max_hour_interval: int = 24,
        max_count: int = 10
    ) -> None:
        """Synchronize news from providers, skipping if last sync was within 1 hour.

        Fetches either stock-specific news (if ticker is provided) or general market news,
        processes the articles, and stores them in the database.

        Args:
            ticker: Optional stock ticker symbol for fetching stock-specific news.
            category: News category to filter by (default: "business").
            max_hour_interval: Maximum age (in hours) of news articles to fetch (default: 24).
            max_count: Maximum number of articles to fetch per provider (default: 10).
        """
        current_time = time.time()
        if current_time < self.db.last_sync + 3600:
            LOG.info("Skipping sync: Last sync was less than 1 hour ago.")
            return

        LOG.info("Starting news sync...")

        threads = []
        for provider in self.providers:
            thread = threading.Thread(
                target=self._fetch_thread,
                args=(provider, self, ticker, category, max_hour_interval, max_count)
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        self.db.last_sync = current_time
        LOG.info("News sync completed.")

    def _is_blocked(self, url: str) -> bool:
        """Check if the website of the URL is in the blocklist"""
        domain = self._extract_domain(url)
        if domain in self.blocklist:
            LOG.info(f"Skipping blocked website: {domain} (URL: {url})")
            return True
        return False

    def _extract_domain(self, url: str) -> str:
        """Extract the main domain from a URL
        (e.g., "https://www.example.com/news" → "example.com")
        """
        try:
            parsed = urlparse(url)
            # Split subdomains (e.g., "www.example.co.uk" → "example.co.uk" for common TLDs)
            domain_parts = parsed.netloc.split(".")
            # Handle cases like "co.uk" (adjust based on your target regions)
            if len(domain_parts) >= 3 and domain_parts[-2] in ["co", "com", "org", "net"]:
                return ".".join(domain_parts[-3:])
            return ".".join(domain_parts[-2:])
        except Exception as e:
            LOG.error(f"Failed to extract domain from {url}: {e}")
            return url  # Fallback to full URL if parsing fails


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db = NewsDatabase()

    try:
        # Initialize providers using the factory
        newsapi_provider = NewsFactory.create_provider("newsapi")
        finnhub_provider = NewsFactory.create_provider("finnhub")
        google_provider = NewsFactory.create_provider("google")
        rss_provider = NewsFactory.create_provider("rss")

        # Create aggregator with selected providers
        aggregator = NewsAggregator(providers=[newsapi_provider], db=db)

        # Sync market news and stock-specific news
        aggregator.sync_news(category="business", max_hour_interval=64, max_count=10)
        aggregator.sync_news(
            ticker="AAPL",
            category="business",
            max_hour_interval=240,
            max_count=10
        )

        # Log results
        all_news = db.get_all_news()
        LOG.info(f"Total articles in database: {len(all_news)}")

        if all_news:
            LOG.info("Example article:")
            LOG.info(all_news[0].to_dict())

            for news_item in all_news:
                LOG.info("--------------------------------")
                print(news_item.headline)
                print(news_item.url)
                print(news_item.content)
                LOG.info("--------------------------------")

    except ValueError as e:
        LOG.error(f"Error during news aggregation: {e}")
