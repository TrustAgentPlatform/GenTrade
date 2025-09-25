"""
Baidu Search Scraper with Article Extraction

This module provides tools for:
1. Persistent storage of blocked domains and dummy content patterns.
2. Cleaning and extracting article content while filtering irrelevant material.
3. Scraping Baidu search results and enriching them with extracted article content.
"""

import json
import logging
import os
import random
import re
import time

from typing import Dict, List
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Comment
from newspaper import Article
from newspaper.article import ArticleException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ScraperStorage:
    """Manages persistent storage for scraper data such as blocklists and dummy patterns."""

    def __init__(self, storage_dir: str = "scraper_data"):
        self.storage_dir = storage_dir
        self.blocklist_path = os.path.join(storage_dir, "blocked_domains.json")
        self.dummy_patterns_path = os.path.join(
            storage_dir, "dummy_content_patterns.json"
        )

        os.makedirs(storage_dir, exist_ok=True)
        self._initialize_file(self.blocklist_path, {})
        self._initialize_file(self.dummy_patterns_path, [])

    def _initialize_file(self, file_path: str, default_content):
        """Create a new storage file with default content if it doesn't exist."""
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(default_content, f, ensure_ascii=False, indent=2)

    def load_blocked_domains(self) -> Dict[str, float]:
        """Load list of blocked domains with their block timestamps."""
        try:
            with open(self.blocklist_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load blocked domains: %s", str(e))
            return {}

    def save_blocked_domains(self, blocked_domains: Dict[str, float]):
        """Save updated blocked domains list to storage."""
        try:
            with open(self.blocklist_path, "w", encoding="utf-8") as f:
                json.dump(blocked_domains, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Failed to save blocked domains: %s", str(e))

    def load_dummy_patterns(self) -> List[str]:
        """Load previously identified dummy content patterns."""
        try:
            with open(self.dummy_patterns_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load dummy patterns: %s", str(e))
            return []

    def save_dummy_patterns(self, dummy_patterns: List[str]):
        """Save new dummy content patterns to storage, ensuring uniqueness."""
        try:
            unique_patterns = []
            for pattern in dummy_patterns:
                if pattern not in unique_patterns:
                    unique_patterns.append(pattern)

            with open(self.dummy_patterns_path, "w", encoding="utf-8") as f:
                json.dump(unique_patterns, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Failed to save dummy patterns: %s", str(e))


class ArticleContentExtractor:
    """Handles article content extraction with dummy content filtering."""

    def __init__(self, storage: ScraperStorage):
        self.ignored_extensions = (
            ".pdf", ".doc", ".docx", ".xls", ".xlsx",
            ".zip", ".rar", ".jpg", ".png", ".jpeg", ".gif"
        )
        self.dummy_keywords = {
            "we use cookies", "cookie policy", "analyze website traffic",
            "accept cookies", "reject cookies", "by continuing to use",
            "this website uses cookies", "improve user experience",
            "ads by", "sponsored content", "subscribe to access"
        }

        self.storage = storage
        self.blocked_domains = self.storage.load_blocked_domains()
        self.dummy_patterns = self.storage.load_dummy_patterns()

        self.user_agents = [
            ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
             "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"),
            ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15"),
            ("Mozilla/5.0 (X11; Linux x86_64) "
             "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"),
        ]

    def _get_random_headers(self) -> Dict[str, str]:
        """Generate random browser-like headers."""
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
                       "image/avif,image/webp,*/*;q=0.8"),
            "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def _clean_html(self, html: str) -> str:
        """Clean raw HTML by removing non-content elements and ads."""
        if not html:
            return ""

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(
            ["script", "style", "noscript", "iframe", "aside", "nav", "footer"]
        ):
            tag.decompose()

        for comment in soup.find_all(text=lambda t: isinstance(t, Comment)):
            comment.extract()

        ad_selectors = [
            "div[class*='ad']", "div[id*='ad']",
            "div[class*='advert']", "div[id*='advert']",
            "div[class*='推广']", "div[id*='推广']",
        ]
        for selector in ad_selectors:
            for tag in soup.select(selector):
                tag.decompose()

        text = soup.get_text()
        return re.sub(r"\s+", " ", text).strip()

    def _is_dummy_content(self, content: str) -> bool:
        """Check if content contains dummy patterns or keywords."""
        if not content:
            return False

        content_lower = content.lower()

        if any(keyword in content_lower for keyword in self.dummy_keywords):
            return True

        for pattern in self.dummy_patterns:
            if pattern.lower() in content_lower and len(pattern) > 10:
                return True

        return False

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL (without port)."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.split(":")[0]
        except Exception:
            return url

    def _is_domain_blocked(self, url: str) -> bool:
        """Check if domain is in blocked list (7-day expiration)."""
        domain = self._get_domain(url)
        if domain in self.blocked_domains:
            if time.time() - self.blocked_domains[domain] < 604800:
                logger.info("Domain %s is blocked - skipping extraction", domain)
                return True
            del self.blocked_domains[domain]
            self.storage.save_blocked_domains(self.blocked_domains)
        return False

    def _block_domain(self, url: str):
        """Add domain to blocked list with current timestamp."""
        domain = self._get_domain(url)
        if domain not in self.blocked_domains:
            self.blocked_domains[domain] = time.time()
            self.storage.save_blocked_domains(self.blocked_domains)
            logger.info("Added domain %s to blocked list", domain)

    def _add_dummy_content_pattern(self, content: str):
        """Extract and save new dummy content patterns from detected content."""
        fragments = re.split(r"[.!?;]", content)
        for fragment in fragments:
            fragment = fragment.strip()
            if 20 < len(fragment) < 200:
                self.dummy_patterns.append(fragment)

        self.storage.save_dummy_patterns(self.dummy_patterns)

    def extract_content(self, url: str) -> str:
        """Extract article content with dummy filtering and blocklisting."""
        if self._is_domain_blocked(url):
            logger.warning("Content source blocked: %s", url)
            return "Content source blocked: Previously detected irrelevant content"

        parsed_url = urlparse(url)
        if parsed_url.path.lower().endswith(self.ignored_extensions):
            logger.warning("Skipping non-HTML file: %s", url)
            return "Unsupported file type (non-HTML)"

        try:
            article = Article(url, language="zh")
            article.download()
            article.parse()
            content = article.text.strip()
        except ArticleException as e:
            logger.warning(
                "newspaper3k extraction failed: %s - falling back to HTML cleaning",
                str(e)
            )
            try:
                headers = self._get_random_headers()
                response = requests.get(
                    url, headers=headers, timeout=10, allow_redirects=True
                )
                response.encoding = response.apparent_encoding

                if response.status_code != 200:
                    logger.warning("Failed to retrieve article (status %s): %s",
                                   response.status_code, url)
                    return "Failed to retrieve content (HTTP error)"

                content = self._clean_html(response.text)
            except requests.exceptions.RequestException as e:
                logger.error("Request error for %s: %s", url, str(e))
                return "Failed to retrieve content (network error)"

        if self._is_dummy_content(content):
            logger.warning("Dummy content detected at: %s", url)
            self._block_domain(url)
            self._add_dummy_content_pattern(content)
            return "Content blocked: Contains cookie notices or irrelevant material"

        return content
