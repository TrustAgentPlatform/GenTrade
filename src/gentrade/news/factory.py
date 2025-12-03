"""News aggregation module for fetching, processing, and storing news articles from multiple
   providers.

This module includes a factory for creating news provider instances and an aggregator for
synchronizing news from these providers to a database, with functionality to extract and clean
article content.
"""

import os
import time
import threading
from typing import List, Optional
from loguru import logger

from gentrade.scraper.extractor import ArticleContentExtractor

from gentrade.news.meta import NewsProviderBase, NewsDatabase
from gentrade.news.newsapi import NewsApiProvider
from gentrade.news.rss import RssProvider
from gentrade.news.finnhub import FinnhubNewsProvider


class NewsFactory:
    """Factory class for creating news provider instances based on provider type.

    Provides a static method to instantiate the appropriate news provider (e.g., NewsAPI,
    Finnhub) using the specified type and required configuration parameters.
    """

    @staticmethod
    def create_provider(provider_type: str, **kwargs) -> NewsProviderBase:
        """Create a news provider instance based on the specified provider type.

        Args:
            provider_type: Type of news provider. Supported values: "newsapi", "finnhub", "rss".
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

    def _fetch_thread(self, provider, aggregator, ticker, category,
        max_hour_interval, max_count, is_process=False):
        if ticker:
            news = provider.fetch_stock_news(
                ticker, category, max_hour_interval, max_count
            )
            logger.info(
                f"Fetched {len(news)} stock news articles for {ticker} from "
                f"{provider.__class__.__name__}"
            )
        else:
            news = provider.fetch_latest_market_news(
                category, max_hour_interval, max_count
            )
            logger.info(
                f"Fetched {len(news)} market news articles from "
                f"{provider.__class__.__name__}"
            )

        ace = ArticleContentExtractor.inst()
        for item in news:
            item.summary = ace.clean_html(item.summary)
            if is_process:
                item.content = ace.extract_content(item.url)

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
            logger.info("Skipping sync: Last sync was less than 1 hour ago.")
            return

        logger.info("Starting news sync...")

        threads = []
        for provider in self.providers:
            if not provider.is_available:
                continue

            thread = threading.Thread(
                target=self._fetch_thread,
                args=(provider, self, ticker, category, max_hour_interval, max_count)
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        self.db.last_sync = current_time
        logger.info("News sync completed.")

if __name__ == "__main__":
    db = NewsDatabase()

    try:
        # Initialize providers using the factory
        newsapi_provider = NewsFactory.create_provider("newsapi")
        finnhub_provider = NewsFactory.create_provider("finnhub")
        rss_provider = NewsFactory.create_provider("rss")

        # Create aggregator with selected providers
        aggregator = NewsAggregator(providers=[rss_provider], db=db)

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
        logger.info(f"Total articles in database: {len(all_news)}")

        if all_news:

            for news_item in all_news:
                logger.info("[%s...]: %s..." % (str(news_item.id)[:10], news_item.headline[:15]))

    except ValueError as e:
        logger.error(f"Error during news aggregation: {e}")
