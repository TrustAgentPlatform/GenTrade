#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gentrade - NewsNow News Provider Module

Project: gentrade
Module: news.providers.newsnow
Description:
    Implementation of the NewsNow news provider for fetching real-time market news
    from the NewsNow API endpoint. This module inherits from NewsProviderBase and
    implements core methods for news retrieval, parsing, and filtering across
    multiple supported sources (e.g., baidu, zhihu, weibo).

Key Features:
    - Source-specific news fetching from 38+ supported platforms
    - Automatic news parsing into standardized NewsInfo objects
    - Time-based and count-based news filtering
    - Jittered exponential backoff for retry logic
    - Robust error handling and logging
    - Compatibility with China (cn) market news by default
"""

import time
import random
from typing import List
from loguru import logger

from gentrade.news.meta import NewsProviderBase, NewsInfo
from gentrade.utils.download import HttpDownloader

# Supported news sources for NewsNow provider (38+ platforms)
AVAILABLE_SOURCE = [
    'baidu', 'bilibili', 'cankaoxiaoxi', 'chongbuluo', 'douban', 'douyin',
    'fastbull', 'freebuf', 'gelonghui', 'ghxi', 'github', 'hackernews',
    'hupu', 'ifeng', 'ithome', 'jin10', 'juejin', 'kaopu', 'kuaishou',
    'linuxdo', 'mktnews', 'nowcoder', 'pcbeta', 'producthunt', 'smzdm',
    'solidot', 'sputniknewscn', 'sspai', 'steam', 'tencent', 'thepaper',
    'tieba', 'toutiao', 'v2ex', 'wallstreetcn', 'weibo', 'xueqiu', 'zaobao',
    'zhihu'
]


class NewsNowProvider(NewsProviderBase):
    """News provider for fetching real-time market news from NewsNow service.

    Inherits from NewsProviderBase and implements abstract methods to fetch
    categorized market news using the NewsNow API endpoint with source-specific
    configurations.
    """

    def __init__(self, source: str = "baidu"):
        """Initialize NewsNowProvider with specified news source.

        Args:
            source: Platform identifier (from AVAILABLE_SOURCE) used in API request
        """
        self.source = source
        self.url = f"https://newsnow.busiyi.world/api/s?id={self.source}&latest"

    @property
    def market(self) -> str:
        """Override market property to specify target market (China)."""
        return "cn"  # Target market: China (adjustable for other regions)

    def fetch_latest_market_news(
        self,
        category: str = "business",
        max_hour_interval: int = 24,
        max_count: int = 10
    ) -> List[NewsInfo]:
        """Fetch and filter latest market news from NewsNow service.

        Args:
            category: News category filter (unused by NewsNow API, kept for compat)
            max_hour_interval: Max age (hours) of articles to include
            max_count: Maximum number of articles to return

        Returns:
            List of NewsInfo objects filtered by time and count constraints
        """
        # Fetch raw JSON data from NewsNow API endpoint
        response = HttpDownloader.inst().get(self.url)
        if not response:
            logger.warning(f"Empty response from NewsNow API (source: {self.source})")
            return []

        # Parse raw response to NewsInfo objects and apply filters
        news_list = self._parse_news(response.json())
        filtered_news = self.filter_news(news_list, max_hour_interval, max_count)

        logger.info(f"Fetched {len(filtered_news)} news items (source: {self.source})")
        return filtered_news

    @staticmethod
    def _calculate_retry_wait(
        retry_number: int,
        min_wait: int = 3,
        max_wait: int = 5
    ) -> float:
        """Calculate exponential backoff wait time for request retries.

        Implements jittered exponential backoff to avoid thundering herd effect.

        Args:
            retry_number: Current retry attempt number (starting at 1)
            min_wait: Minimum base wait time in seconds
            max_wait: Maximum base wait time in seconds

        Returns:
            Calculated wait time in seconds (with random jitter)
        """
        base_wait = random.uniform(min_wait, max_wait)
        additional_wait = (retry_number - 1) * random.uniform(1, 2)
        return base_wait + additional_wait

    def _parse_news(self, raw_data: dict) -> List[NewsInfo]:
        """Parse raw NewsNow API JSON response into NewsInfo objects.

        Extracts and normalizes news fields with fallbacks for missing values,
        handles time conversion, and generates unique IDs from URLs.

        Args:
            raw_data: Parsed JSON dictionary from NewsNow API response

        Returns:
            List of valid NewsInfo objects (skipped invalid/corrupted items)
        """
        news_items = []
        for item in raw_data.get("items", []):
            try:
                # Extract URL with mobile fallback (critical field)
                url = item.get("url", "") or item.get("mobileUrl", "")
                if not url:
                    logger.warning("Skipping news item - no URL found")
                    continue

                # Convert publication time to epoch timestamp (fallback: current time)
                pub_time = item.get("pubTime", "")
                datetime_epoch = (
                    self._timestamp_to_epoch(pub_time) if pub_time else int(time.time())
                )

                # Create normalized NewsInfo object with default values
                news_info = NewsInfo(
                    category=item.get("category", "general"),
                    datetime=datetime_epoch,
                    headline=item.get("title", "No headline"),
                    id=self.url_to_hash_id(url),  # Unique ID from URL hash
                    image=item.get("image", ""),
                    related=item.get("related", []),
                    source=item.get("source", self.source),
                    summary=item.get("summary", ""),
                    url=url,
                    content=item.get("content", ""),
                    provider="newsnow",
                    market=self.market
                )
                news_items.append(news_info)

            except Exception as e:
                logger.error(f"Failed to parse news item (source: {self.source}): {str(e)}")
                continue

        return news_items


if __name__ == "__main__":
    logger.info("Starting NewsNowProvider test for all available sources...")

    for source in AVAILABLE_SOURCE:
        try:
            provider = NewsNowProvider(source)
            news_items = provider.fetch_latest_market_news()
            logger.info(f"Source {source}: Found {len(news_items)} news items")
            time.sleep(1)  # Rate limiting for test execution
        except Exception as e:
            logger.error(f"Test failed for source {source}: {str(e)}")

    logger.info("NewsNowProvider test completed")
