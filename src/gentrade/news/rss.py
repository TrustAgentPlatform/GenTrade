"""RSS/ATOM feed news provider implementation for financial news retrieval.

This module implements the NewsProviderBase abstract class to fetch news from RSS/ATOM feeds.
It supports general market news via a configured feed URL and limited stock-specific news
(by filtering headlines/summaries for tickers). Uses fallback URLs and robust error handling
for feed fetching/parsing.
"""

import os
import logging
from typing import List

import requests
import feedparser

from gentrade.news.meta import NewsInfo, NewsProviderBase

LOG = logging.getLogger(__name__)


class RssProvider(NewsProviderBase):
    """News provider that fetches news from RSS/ATOM feeds.

    Retrieves general market news via a specified RSS feed URL (with environment variable
    fallback). For stock-specific news, filters general feed results by ticker in headlines
    or summaries (since most RSS feeds lack ticker-specific endpoints).
    """

    def __init__(self, feed_url: str = None):
        """Initialize the RssProvider with an optional feed URL.

        Args:
            feed_url: URL of the RSS/ATOM feed to use. If not provided, uses the
                `RSS_FEED_URL` environment variable or defaults to China Daily's finance feed.
        """
        # Priority: explicit feed_url > env var > default China Daily finance feed
        self.feed_url = (
            feed_url
            or os.getenv("RSS_FEED_URL")
            or "https://plink.anyfeeder.com/chinadaily/caijing"
        )

    def fetch_latest_market_news(
        self,
        category: str = "business",
        max_hour_interval: int = 24,
        max_count: int = 10
    ) -> List[NewsInfo]:
        """Fetch latest general market news from the configured RSS feed.

        Retrieves articles from the RSS feed, filters by recency (max_hour_interval), and
        limits results to max_count. Uses feedparser for parsing and includes media content
        (e.g., images) where available.

        Args:
            category: Category label to assign to fetched news (default: "business").
            max_hour_interval: Maximum age (in hours) of articles to include (default: 24).
            max_count: Maximum number of articles to return (default: 10).

        Returns:
            List of NewsInfo objects with formatted market news; empty list if feed fetching,
            parsing fails, or no valid articles exist.
        """
        if not self.feed_url:
            LOG.error("RSS feed URL is missing (no explicit URL, env var, or default).")
            return []

        # Headers to mimic browser (avoid feed server blocking) and accept RSS/XML
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml"
        }

        try:
            # Fetch raw feed content
            response = requests.get(self.feed_url, headers=headers, timeout=10)
            response.raise_for_status()  # Raise error for HTTP 4xx/5xx

            # Parse feed with feedparser
            feed = feedparser.parse(response.text)
            if not feed.entries:
                LOG.warning(f"No articles found in RSS feed: {self.feed_url}")
                return []

            # Convert feed entries to standardized NewsInfo objects
            # Fetch 2x max_count initially to allow post-filtering by time
            news_list = [
                NewsInfo(
                    category=category,
                    datetime=self._timestamp_to_epoch(entry.get("published", "")),
                    headline=entry.get("title", ""),
                    id=hash(entry.get("link", "")),  # Unique ID from article URL
                    # Extract image URL (handles missing media_content gracefully)
                    image=entry.get("media_content", [{}])[0].get("url", "")
                    if entry.get("media_content") else "",
                    related="",  # No ticker for general market news
                    source=feed.feed.get("title", "Unknown RSS Feed"),  # Feed source name
                    summary=entry.get("summary", ""),  # Short article preview
                    url=entry.get("link", ""),  # Direct article URL
                    content=""  # Content extracted later by aggregator
                )
                for entry in feed.entries[:max_count * 2]
                if entry.get("link")  # Skip entries without a valid URL
            ]

            # Filter by recency and limit to max_count
            return self._filter_news(news_list, max_hour_interval, max_count)

        except requests.HTTPError as e:
            LOG.error(
                f"HTTP error fetching RSS feed {self.feed_url}: "
                f"Status {e.response.status_code} - {str(e)}"
            )
            return []
        except requests.RequestException as e:
            LOG.error(f"Network error fetching RSS feed {self.feed_url}: {str(e)}")
            return []
        except Exception as e:
            LOG.error(f"Unexpected error parsing RSS feed {self.feed_url}: {str(e)}")
            return []

    def fetch_stock_news(
        self,
        ticker: str,
        category: str = "business",
        max_hour_interval: int = 24,
        max_count: int = 10
    ) -> List[NewsInfo]:
        """Fetch stock-specific news by filtering RSS feed results for the target ticker.

        Note: Most RSS feeds don't support native ticker filtering. This method fetches
        general market news first, then filters entries where the ticker appears in the
        headline or summary (case-insensitive).

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL") to filter for.
            category: Category label to assign to fetched news (default: "business").
            max_hour_interval: Maximum age (in hours) of articles to include (default: 24).
            max_count: Maximum number of articles to return (default: 10).

        Returns:
            List of NewsInfo objects with ticker-matching news; empty list if no matches
            or feed fetching fails.
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
            news.related = ticker

        # Limit to max_count results
        return ticker_news[:max_count]
