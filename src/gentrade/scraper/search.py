"""
Baidu Search Scraper Module

This module provides a class `BaiduSearchScraper` that scrapes Baidu search
results and extracts structured information including title, summary,
source, timestamp, and optionally full article content.
"""

import json
import logging
import random
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

from gentrade.scraper.extractor import ScraperStorage, ArticleContentExtractor


# pylint: disable=too-many-locals,too-many-statements,too-many-branches,possibly-used-before-assignment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BaiduSearchScraper:
    """Scrapes Baidu search results and extracts structured article data."""

    def __init__(self) -> None:
        """Initialize scraper with user agents, storage, and regex patterns."""
        self.base_url = "https://www.baidu.com/s"
        self.user_agents = [
            ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
             "AppleWebKit/537.36 (KHTML, like Gecko) "
             "Chrome/114.0.0.0 Safari/537.36"),
            ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) "
             "Version/16.5 Safari/605.1.15"),
            ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36")
        ]

        self.storage = ScraperStorage()
        self.content_extractor = ArticleContentExtractor(self.storage)

        self.time_patterns = {
            "minute": re.compile(r"(\d+)\s*分钟前"),
            "hour": re.compile(r"(\d+)\s*小时前"),
            "day": re.compile(r"(\d+)\s*天前"),
            "week": re.compile(r"(\d+)\s*周前"),
            "month": re.compile(r"(\d+)\s*月前"),
            "year": re.compile(r"(\d+)\s*年前"),
            "date": re.compile(r"(\d{4})[^\d]?(\d{1,2})[^\d]?(\d{1,2})"),
            "datetime": re.compile(
                r"(\d{4})[^\d]?(\d{1,2})[^\d]?(\d{1,2})\s+"
                r"(\d{1,2})[:：](\d{1,2})"
            ),
        }

    def _get_random_headers(self) -> Dict[str, str]:
        """Generate random HTTP headers for requests."""
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": ("text/html,application/xhtml+xml,application/xml;"
                       "q=0.9,image/avif,image/webp,*/*;q=0.8"),
            "Accept-Language": (
                "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,"
                "en-US;q=0.3,en;q=0.2"
            ),
            "Connection": "keep-alive",
            "Referer": "https://www.baidu.com/",
            "Upgrade-Insecure-Requests": "1",
        }

    def _parse_time_to_timestamp(self, time_text: str) -> int:
        """Convert a time string into a Unix timestamp."""
        if not time_text:
            return int(time.time())

        now = datetime.now()

        # Handle relative times
        for unit, pattern in self.time_patterns.items():
            match = pattern.search(time_text)
            if match:
                try:
                    num = int(match.group(1))
                    if unit == "minute":
                        dt = now - timedelta(minutes=num)
                    elif unit == "hour":
                        dt = now - timedelta(hours=num)
                    elif unit == "day":
                        dt = now - timedelta(days=num)
                    elif unit == "week":
                        dt = now - timedelta(weeks=num)
                    elif unit == "month":
                        dt = now - timedelta(days=num * 30)
                    elif unit == "year":
                        dt = now - timedelta(days=num * 365)
                    return int(dt.timestamp())
                except Exception:
                    continue

        # Handle absolute datetime
        dt_match = self.time_patterns["datetime"].search(time_text)
        if dt_match:
            try:
                year, month, day, hour, minute = map(int, dt_match.groups())
                return int(datetime(year, month, day, hour, minute).timestamp())
            except Exception:
                pass

        # Handle absolute date
        date_match = self.time_patterns["date"].search(time_text)
        if date_match:
            try:
                year, month, day = map(int, date_match.groups())
                return int(datetime(year, month, day).timestamp())
            except Exception:
                pass

        logger.warning("Unrecognized time format: %s", time_text)
        return int(time.time())

    def search(
        self,
        query: str,
        limit: int = 10,
        page: int = 1,
        fetch_content: bool = True
    ) -> List[Dict[str, str]]:
        """
        Perform a Baidu search and return structured results.

        Args:
            query: Search query string.
            limit: Maximum number of results to return.
            page: Starting page number.
            fetch_content: Whether to fetch full article content.

        Returns:
            A list of dictionaries containing search result data.
        """
        results = []
        current_page = page

        while len(results) < limit:
            pn = (current_page - 1) * 10
            params = {"wd": query, "pn": pn, "ie": "utf-8",
                      "oe": "utf-8", "tn": "baidu"}

            try:
                headers = self._get_random_headers()
                response = requests.get(
                    self.base_url,
                    params=params,
                    headers=headers,
                    timeout=10,
                    allow_redirects=False,
                )

                if response.status_code != 200:
                    logger.warning(
                        "Search request failed (status %s)", response.status_code
                    )
                    break

                soup = BeautifulSoup(response.text, "html.parser")
                search_results = soup.select("div.result.c-container.xpath-log")

                if not search_results:
                    logger.info("No more search results found")
                    break

                for item in search_results:
                    if len(results) >= limit:
                        break

                    try:
                        title_tag = item.select_one("h3.t a")
                        title = (title_tag.get_text(strip=True)
                                 if title_tag else "No title")
                        url = (title_tag["href"]
                               if (title_tag and "href" in title_tag.attrs) else "")

                        abstract_tag = item.select_one("div.c-abstract")
                        summary = (abstract_tag.get_text(strip=True)
                                   if abstract_tag else "No summary")

                        source_time_tag = item.select_one("div.c-source")
                        source_time_text = (
                            source_time_tag.get_text(strip=True)
                            if source_time_tag else "Unknown source"
                        )

                        source = source_time_text
                        time_text = ""
                        time_pattern = re.compile(
                            r"(\d+[分钟小时天周月年]前|\d{4}[^\d]?\d{1,2}[^\d]?"
                            r"\d{1,2}.*)"
                        )
                        time_match = time_pattern.search(source_time_text)

                        if time_match:
                            time_text = time_match.group(1)
                            source = (
                                source_time_text.replace(time_text, "").strip()
                                or "Unknown source"
                            )

                        timestamp = self._parse_time_to_timestamp(time_text)

                        content = ""
                        if fetch_content and url:
                            content = self.content_extractor.extract_content(url)
                            time.sleep(random.uniform(0.5, 1.5))

                        results.append({
                            "title": title,
                            "url": url,
                            "summary": summary,
                            "source": source,
                            "timestamp": timestamp,
                            "content": content,
                        })

                    except Exception as e:
                        logger.error("Error parsing result: %s", str(e))
                        continue

                logger.info("Fetched page %d - total results: %d",
                            current_page, len(results))

                next_page = soup.select_one("a.n")
                if not next_page:
                    logger.info("Reached last page of results")
                    break

                current_page += 1
                time.sleep(random.uniform(1.5, 3.5))

            except requests.exceptions.RequestException as e:
                logger.error("Search request failed: %s", str(e))
                break
            except Exception as e:
                logger.error("Error processing search page: %s", str(e))
                break

        return results[:limit]


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    scraper = BaiduSearchScraper()
    news = scraper.search(
        query="最近24小时关于TESLA的财经新闻",
        limit=10,
        page=1,
        fetch_content=True,
    )


    print(json.dumps(news, ensure_ascii=False, indent=2))
