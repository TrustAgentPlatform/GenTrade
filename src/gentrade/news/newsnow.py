import json
import time
import random
from typing import List, Optional
from loguru import logger
import requests

from gentrade.news.meta import NewsProviderBase, NewsInfo

AVAILABLE_SOURCE_ID = [
    'baidu',
    'bilibili',
    'cankaoxiaoxi',
    'chongbuluo',
    'douban',
    'douyin',
    'fastbull',
    'freebuf',
    'gelonghui',
    'ghxi',
    'github',
    'hackernews',
    'hupu',
    'ifeng',
    'ithome',
    'jin10',
    'juejin',
    'kaopu',
    'kuaishou',
    'linuxdo',
    'mktnews',
    'nowcoder',
    'pcbeta',
    'producthunt',
    'smzdm',
    'solidot',
    'sputniknewscn',
    'sspai',
    'steam',
    'tencent',
    'thepaper',
    'tieba',
    'toutiao',
    'v2ex',
    'wallstreetcn',
    'weibo',
    'xueqiu',
    'zaobao',
    'zhihu'
]

class NewsNowProvider(NewsProviderBase):
    """News provider for fetching news from NewsNow service.

    Inherits from NewsProviderBase and implements the required abstract methods
    to fetch market news using the NewsNow API endpoint.
    """

    def __init__(self, source_id: str = "baidu"):
        """Initialize NewsNowProvider with optional proxy and platform ID.

        Args:
            proxy_url: Optional proxy URL for making requests.
            source_id: Platform identifier used in the API request.
        """
        self.source_id = source_id

    @property
    def market(self) -> str:
        """Override market to specify the target market for this provider."""
        return "cn"  # Default to US market, can be adjusted as needed

    def fetch_latest_market_news(
        self,
        category: str = "business",
        max_hour_interval: int = 24,
        max_count: int = 10
    ) -> List[NewsInfo]:
        """Fetch latest market news from NewsNow service.

        Args:
            category: News category filter (not used by NewsNow API).
            max_hour_interval: Maximum age (in hours) of articles to include.
            max_count: Maximum number of articles to return.

        Returns:
            List of NewsInfo objects filtered by time and count constraints.
        """
        # Fetch raw data from NewsNow API
        raw_data = self._fetch_news_data()
        if not raw_data:
            return []

        # Convert raw data to NewsInfo objects
        news_list = self._parse_news(raw_data)

        # Filter news by time interval and count
        return self.filter_news(news_list, max_hour_interval, max_count)

    def _fetch_news_data(self, max_retries: int = 2) -> Optional[dict]:
        """Fetch raw news data from NewsNow API with retry mechanism.

        Args:
            max_retries: Maximum number of retry attempts on failure.

        Returns:
            Parsed JSON data if successful, None otherwise.
        """
        url = f"https://newsnow.busiyi.world/api/s?id={self.source_id}&latest"

        retries = 0
        while retries <= max_retries:
            try:
                response = requests.get(
                    url,
                    proxies=self.proxies,
                    headers=self.http_headers,
                    timeout=10
                )
                response.raise_for_status()
                return self._validate_response(response.text)

            except Exception as e:
                retries += 1
                if retries <= max_retries:
                    wait_time = self._calculate_retry_wait(retries)
                    logger.error(
                        f"[{self.source_id}] Request failed (attempt {retries}/{max_retries}): {e}."
                        f"[{self.source_id}] Retrying in {wait_time:.2f}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed after {max_retries} retries: {e}")
                    return None

        return None

    @staticmethod
    def _validate_response(response_text: str) -> Optional[dict]:
        """Validate and parse API response.

        Args:
            response_text: Raw text response from the API.

        Returns:
            Parsed JSON data if valid, None otherwise.
        """
        try:
            data = json.loads(response_text)
            status = data.get("status", "unknown")
            if status not in ["success", "cache"]:
                logger.error(f"Invalid response status: {status}")
                return None

            status_info = "latest data" if status == "success" else "cached data"
            logger.info(f"Successfully fetched {status_info}")
            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return None

    @staticmethod
    def _calculate_retry_wait(retry_number: int, min_wait: int = 3, max_wait: int = 5) -> float:
        """Calculate exponential backoff wait time for retries.

        Args:
            retry_number: Current retry attempt number (starting at 1).
            min_wait: Minimum base wait time in seconds.
            max_wait: Maximum base wait time in seconds.

        Returns:
            Calculated wait time in seconds.
        """
        base_wait = random.uniform(min_wait, max_wait)
        additional_wait = (retry_number - 1) * random.uniform(1, 2)
        return base_wait + additional_wait

    def _parse_news(self, raw_data: dict) -> List[NewsInfo]:
        """Parse raw API response into list of NewsInfo objects.

        Args:
            raw_data: Parsed JSON data from the API.

        Returns:
            List of NewsInfo objects created from the raw data.
        """
        news_items = []
        for item in raw_data.get("items", []):
            try:
                # Extract required fields with fallbacks
                url = item.get("url", "") or item.get("mobileUrl", "")
                if not url:
                    logger.warning("Skipping item - no URL found")
                    continue

                # Convert publication time to epoch timestamp
                pub_time = item.get("pubTime", "")
                datetime_epoch = self._timestamp_to_epoch(pub_time) \
                    if pub_time else int(time.time())

                # Create NewsInfo object
                news_info = NewsInfo(
                    category=item.get("category", "general"),
                    datetime=datetime_epoch,
                    headline=item.get("title", "No headline"),
                    id=self.url_to_hash_id(url),  # Use URL hash as unique ID
                    image=item.get("image", ""),
                    related=item.get("related", []),
                    source=item.get("source", self.source_id),
                    summary=item.get("summary", ""),
                    url=url,
                    content=item.get("content", ""),
                    provider="newsnow",
                    market=self.market
                )
                news_items.append(news_info)

            except Exception as e:
                logger.error(f"Failed to parse news item: {e}")
                continue

        return news_items

if __name__ == "__main__":
    logger.info("hello")
    for source_id in AVAILABLE_SOURCE_ID:
        inst = NewsNowProvider(source_id)
        ret = inst.fetch_latest_market_news()
        logger.info(ret)
        time.sleep(5)
