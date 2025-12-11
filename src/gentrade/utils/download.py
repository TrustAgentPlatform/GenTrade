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

import os
import random
import time
from typing import Dict
import requests
from loguru import logger

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

    def __init__(self, max_retries: int = 3, timeout: int = 10):
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

    def get(self, url: str, params: Dict = None) -> Dict:
        """Send HTTP GET request with automatic retry mechanism

        Args:
            url: Target URL to retrieve content from

        Returns:
            Response text if successful, None if all retries fail
        """
        retry_count = 0  # Current retry attempt counter

        logger.debug(f"Http download {url} ...")
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
                    verify=True  # Enable SSL certificate verification
                )
                # Raise exception for HTTP error status codes (4xx/5xx)
                response.raise_for_status()
                return response.json()  # Return successful response content

            except Exception as e:
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
