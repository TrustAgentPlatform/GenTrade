"""
HTTP Downloader Utility

Description:
    A robust HTTP downloader implementation with singleton pattern, automatic retry mechanism,
    randomized User-Agent spoofing, and proxy support from environment variables.

    Key Features:
    - Singleton pattern for consistent configuration across application
    - Configurable retry attempts and request timeout
    - Random User-Agent rotation to mimic different browsers
    - Proxy configuration loaded from standard environment variables
    - Comprehensive error logging with backoff timing
    - SSL certificate verification for secure requests

Usage Example:
    >>> downloader = HttpDownloader.inst()
    >>> content = downloader.get("https://example.com")
    >>> if content:
    >>>     print("Content downloaded successfully")

Dependencies:
    - requests >= 2.25.1
    - loguru >= 0.7.0
    - Python >= 3.8
"""
import re
import os
import random
import time
import json
from typing import Dict, List
from urllib.parse import urlparse

import requests
from loguru import logger

from bs4 import BeautifulSoup, Comment
from newspaper import Article
from newspaper.article import ArticleException

class HttpDownloader:
    """HTTP Downloader with retry mechanism, random User-Agent, and proxy support

    Implements singleton pattern for consistent HTTP GET requests with:
    - Automatic retry on failure (configurable max retries)
    - Randomized User-Agent to mimic different browsers
    - Proxy configuration loaded from environment variables
    - Timeout control for request safety
    """
    # Singleton instance storage
    _INSTANCE = None

    def __init__(self, max_retries: int = 3, timeout: int = 5):
        """Initialize downloader configuration

        Args:
            max_retries: Maximum retry attempts on failure (default: 3)
            timeout: Request timeout in seconds (default: 10)
        """
        self.max_retries = max_retries  # Max retry attempts for failed requests
        self.timeout = timeout          # Request timeout threshold (seconds)

    @property
    def http_headers(self) -> Dict:
        """Generate randomized HTTP request headers

        Returns:
            Dictionary of HTTP headers with random User-Agent
        """
        # List of common browser User-Agents for request spoofing
        user_agents = [
            (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
            ),
            (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15"
            ),
            (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
            ),
        ]

        # Construct headers with random User-Agent selection
        return {
            "User-Agent": random.choice(user_agents),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    @property
    def proxies(self) -> Dict:
        """Load proxy configuration from environment variables

        Supported environment variables (case-insensitive):
        - http_proxy / HTTP_PROXY
        - https_proxy / HTTPS_PROXY
        - no_proxy / NO_PROXY

        Returns:
            Dictionary of proxy configurations (empty if no proxies set)
        """
        proxy_config = {}
        # Check all standard proxy environment variables
        proxy_env_keys = [
            'http_proxy', 'https_proxy', 'no_proxy',
            'HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY'
        ]

        for key in proxy_env_keys:
            env_value = os.environ.get(key)
            if env_value:
                proxy_config[key] = env_value

        return proxy_config

    def get(self, url: str, verify: bool = True, params: Dict = None) -> requests.Response:
        """Send HTTP GET request with automatic retry mechanism

        Args:
            url: Target URL to retrieve content from

        Returns:
            Response text if successful, None if all retries fail
        """
        retry_count = 0  # Current retry attempt counter

        logger.debug(f"Http download {url} {verify} {params} ")
        # Retry loop until max retries or successful response
        while retry_count <= self.max_retries:
            try:
                # Send GET request with configured headers/proxies/timeout
                response = requests.get(
                    url,
                    proxies=self.proxies,
                    headers=self.http_headers,
                    timeout=self.timeout,
                    params=params,
                    verify=verify  # Enable SSL certificate verification
                )

                # Raise exception for HTTP error status codes (4xx/5xx)
                response.raise_for_status()
                return response
            except Exception as e:
                logger.error(e)
                retry_count += 1  # Increment retry counter on failure

                # Final retry failed - log error and return None
                if retry_count > self.max_retries:
                    logger.error(
                        f"Failed to download URL after {self.max_retries} retries: {e} | URL: {url}"
                    )
                    return None

                # Calculate random backoff time (0.5-2.0s) to avoid rate limiting
                backoff_time = random.uniform(0.5, 2.0)
                logger.error(
                    f"Request failed (attempt {retry_count}/{self.max_retries}): {e}. "
                    f"Retrying in {backoff_time:.2f} seconds..."
                )
                time.sleep(backoff_time)  # Wait before next retry attempt

        return None

    def clean_html(self, html: str) -> str:
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

    @staticmethod
    def inst() -> "HttpDownloader":
        """Get singleton instance of HttpDownloader

        Implements lazy initialization - creates instance only on first call

        Returns:
            Singleton HttpDownloader instance
        """
        if HttpDownloader._INSTANCE is None:
            HttpDownloader._INSTANCE = HttpDownloader()
        return HttpDownloader._INSTANCE


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


class ArticleDownloader(HttpDownloader):
    """Handles article content extraction with dummy content filtering."""

    _INSTANCE = None

    def __init__(self, storage: ScraperStorage=None):
        super().__init__()
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

        if storage is None:
            storage = ScraperStorage()
        self.storage = storage

        self.blocked_domains = self.storage.load_blocked_domains()
        self.dummy_patterns = self.storage.load_dummy_patterns()

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

    def get_content(self, url: str, verify: bool=True, params: Dict = None) -> str:
        """Get article content with dummy filtering and blocklisting."""
        if self._is_domain_blocked(url):
            logger.warning("Content source blocked: %s", url)
            return "Content source blocked: Previously detected irrelevant content"

        parsed_url = urlparse(url)
        if parsed_url.path.lower().endswith(self.ignored_extensions):
            logger.warning("Skipping non-HTML file: %s", url)
            return "Unsupported file type (non-HTML)"

        resp = super().get(url, verify, params)
        if not resp:
            return None

        try:
            article = Article(url, language='zh')
            article.set_html(resp.text)
            article.parse()
            content = article.text
        except ArticleException as e:
            logger.warning(
                "newspaper3k extraction failed: %s - falling back to HTML cleaning",
                str(e)
            )
            content = self.clean_html(resp.text)

        if self._is_dummy_content(content):
            logger.warning("Dummy content detected at: %s", url)
            self._block_domain(url)
            self._add_dummy_content_pattern(content)
            return None

        return content

    @staticmethod
    def inst(storage: ScraperStorage=None):
        if ArticleDownloader._INSTANCE is None:
            ArticleDownloader._INSTANCE = ArticleDownloader(storage)
        return ArticleDownloader._INSTANCE
