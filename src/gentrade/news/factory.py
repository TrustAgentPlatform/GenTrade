"""News aggregation module for fetching, processing, and storing news articles from multiple
   providers.

This module includes a factory for creating news provider instances and an aggregator for
synchronizing news from these providers to a database, with functionality to extract and clean
article content.
"""

import os
import logging
import time
from typing import List, Optional

import requests
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
        for provider in self.providers:
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
                    f"Fetched {len(news)} market news articles from {provider.__class__.__name__}"
                )

            self.process_news(news)
            self.db.add_news(news)

        self.db.last_sync = current_time
        LOG.info("News sync completed.")

    def process_news(self, news: List[NewsInfo]) -> None:
        """Process a list of NewsInfo objects by extracting content from their URLs.

        Args:
            news: List of NewsInfo objects to process.
        """
        for article in news:
            LOG.info(f"Processing news: {article.headline}")
            content = self._extract_news_text(article.url)
            article.content = content
            LOG.info(f"Extracted content: {content}")
            time.sleep(1)  # Throttle requests to avoid rate limits

    def _extract_news_text(self, url: str) -> str:
        """Extract text content from a news article URL using newspaper3k.

        Falls back to HTML scraping with BeautifulSoup if newspaper3k fails.

        Args:
            url: URL of the news article to extract text from.

        Returns:
            Cleaned text content of the article, or empty string if extraction fails.
        """
        try:
            article = Article(url)
            article.download()
            article.parse()
            if article.text:
                return article.text

            # Fallback to HTML scraping if newspaper3k returns empty text
            html = self._fetch_original_html(url)
            return self._clean_html(html)

        except Exception as e:
            LOG.error(f"Failed to extract text with newspaper3k ({url}): {e}")
            html = self._fetch_original_html(url)
            return self._clean_html(html)

    def _fetch_original_html(self, url: str, timeout: int = 10) -> Optional[str]:
        """Fetch raw HTML content from a URL with retries.

        Args:
            url: URL to fetch HTML from.
            timeout: Request timeout in seconds (default: 10).

        Returns:
            Raw HTML content as a string, or None if fetch fails.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        retries = 3

        for attempt in range(retries):
            try:
                response = requests.get(
                    url, headers=headers, timeout=timeout, verify=False
                )
                response.raise_for_status()
                return response.text
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(1)
                    continue
                LOG.error(f"Failed to fetch HTML after {retries} retries ({url}): {e}")
                return None

        return None

    def _clean_html(self, html_content: Optional[str]) -> str:
        """Clean HTML content to extract readable text.

        Removes scripts, styles, and other non-content elements, then normalizes whitespace.

        Args:
            html_content: Raw HTML content to clean.

        Returns:
            Cleaned text string, or empty string if input is None/empty.
        """
        if not html_content:
            return ""

        soup = BeautifulSoup(html_content, "html.parser")

        # Remove non-content elements
        for element in soup(["script", "style", "iframe", "nav", "aside", "footer"]):
            element.decompose()

        # Extract and normalize text
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        return "\n".join(chunk for chunk in chunks if chunk)


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
