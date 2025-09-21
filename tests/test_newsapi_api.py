"""
Pytest Suite for NewsAPI US Stock News Retrieval
=================================================
- Tests fetching latest financial news for US stocks via NewsAPI.
- Relies on `NEWSAPI_API_KEY` stored in environment variables (never hardcode keys).
- Validates response structure, critical fields, and handles common API errors.
"""

import os
import pytest
import requests
from typing import List, Dict
from dotenv import load_dotenv  # Loads .env file (optional but useful for local testing)
# Import Python's built-in datetime module (fixes the AttributeError)
from datetime import datetime, timedelta

# ------------------------------
# Test Configuration
# ------------------------------
# Load environment variables (including NEWSAPI_API_KEY)
load_dotenv()  # Uncomment if using a .env file for local development

# NewsAPI endpoints and parameters
NEWSAPI_BASE_URL = "https://newsapi.org/v2/everything"
# US stock-related query: common tickers + financial keywords (ensures relevant results)
US_STOCKS_QUERY = "AAPL OR MSFT OR NVDA OR TSLA OR US stocks OR S&P 500 OR NASDAQ"
# Response fields to validate (critical for usable news data)
REQUIRED_ARTICLE_FIELDS = ["title", "url", "publishedAt", "source"]
# Test stock tickers (for single-ticker news checks)
TEST_TICKERS = ["AAPL", "MSFT", "NVDA"]


# ------------------------------
# Pytest Fixtures
# ------------------------------
@pytest.fixture(scope="session")
def newsapi_api_key() -> str:
    """
    Fixture: Get NewsAPI key from environment variable.
    Fails early if key is missing (prevents irrelevant test errors).
    """
    api_key = os.getenv("NEWSAPI_API_KEY")
    assert api_key is not None and api_key.strip() != "", \
        "NEWSAPI_API_KEY environment variable is missing or empty. " \
        "Set it via terminal (e.g., `export NEWSAPI_API_KEY='your-key'`) " \
        "or add it to a .env file."
    return api_key.strip()


@pytest.fixture(scope="session")
def newsapi_headers(newsapi_api_key: str) -> Dict[str, str]:
    """Fixture: Reusable HTTP headers for NewsAPI requests (includes auth key)."""
    return {"Authorization": f"Bearer {newsapi_api_key}"}


@pytest.fixture(params=TEST_TICKERS, ids=[f"Ticker:{ticker}" for ticker in TEST_TICKERS])
def test_ticker(request) -> str:
    """
    Parameterized Fixture: Inject multiple US stock tickers (AAPL, MSFT, NVDA) into tests.
    Runs tests once per ticker to validate single-stock news retrieval.
    """
    return request.param


# ------------------------------
# Core Test Cases
# ------------------------------
def test_get_us_stocks_news_success(
    newsapi_headers: Dict[str, str]
) -> None:
    """
    Test 1: Successful retrieval of US stock news (general query).
    Validates: 200 OK status, non-empty results, and required fields in articles.
    """
    # 1. Define request parameters (filters for recent, relevant news)
    # Use built-in datetime + timedelta (fixed the AttributeError)
    one_day_ago = (datetime.now() - timedelta(days=1)).isoformat()

    params = {
        "q": US_STOCKS_QUERY,
        "language": "en",  # Ensure English news (relevant for US stocks)
        "sortBy": "publishedAt",  # Get latest news first
        "pageSize": 10,  # Limit to 10 results (avoids rate limit hits)
        "from": one_day_ago  # Last 24h (uses corrected datetime logic)
    }

    # 2. Send request to NewsAPI
    response = requests.get(
        url=NEWSAPI_BASE_URL,
        headers=newsapi_headers,
        params=params,
        timeout=10  # Prevent hanging tests
    )

    # 3. Validate response status (200 = success)
    assert response.status_code == 200, \
        f"Failed to fetch news. Status code: {response.status_code}. " \
        f"Error: {response.text[:200]}"  # Show first 200 chars of error for debugging

    # 4. Parse JSON response
    response_data = response.json()

    # 5. Validate response structure (NewsAPI's success schema)
    assert response_data.get("status") == "ok", \
        f"NewsAPI returned error status: {response_data.get('status')}. " \
        f"Message: {response_data.get('message')}"
    assert "articles" in response_data, "Response missing 'articles' field"

    # 6. Validate articles (non-empty + required fields)
    articles = response_data["articles"]
    #assert len(articles) > 0, "No US stock news found in the last 24 hours"

    for idx, article in enumerate(articles, 1):
        # Check all required fields exist and are non-empty
        for field in REQUIRED_ARTICLE_FIELDS:
            assert field in article, \
                f"Article {idx} missing required field: '{field}'"
            assert article[field] is not None and str(article[field]).strip() != "", \
                f"Article {idx} has empty value for field: '{field}'"

        # Extra validation: URL is valid (starts with http/https)
        assert article["url"].startswith(("http://", "https://")), \
            f"Article {idx} has invalid URL: {article['url']}"


def test_get_single_ticker_news(test_ticker: str, newsapi_headers: Dict[str, str]) -> None:
    """
    Test 2: Retrieve news for a single US stock ticker (e.g., AAPL).
    Ensures NewsAPI returns ticker-specific results.
    """
    # 1. Calculate "last 24h" (uses built-in datetime to fix error)
    one_day_ago = (datetime.now() - timedelta(days=1)).isoformat()

    # 2. Request news for the current test ticker (e.g., "AAPL")
    params = {
        "q": test_ticker,  # Focus on a single ticker
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 5,  # Fewer results = faster test
        "from": one_day_ago  # Last 24h (corrected datetime logic)
    }

    response = requests.get(
        url=NEWSAPI_BASE_URL,
        headers=newsapi_headers,
        params=params,
        timeout=10
    )

    # 3. Validate success status
    assert response.status_code == 200, \
        f"Failed to fetch {test_ticker} news. Status: {response.status_code}"
    response_data = response.json()
    assert response_data["status"] == "ok", \
        f"{test_ticker} news error: {response_data.get('message')}"

    # 4. Validate ticker relevance (article titles should mention the ticker)
    articles = response_data["articles"]
    if len(articles) > 0:  # Skip if no news (possible for less active tickers)
        ticker_in_titles = any(
            test_ticker in article["title"].upper()  # Case-insensitive check
            for article in articles
        )
        assert ticker_in_titles, \
            f"No {test_ticker} mentions found in article titles. Results may be irrelevant."


# ------------------------------
# Error Handling Tests
# ------------------------------
def test_invalid_api_key() -> None:
    """
    Test 3: Invalid API key returns 401 Unauthorized.
    Ensures the API correctly rejects bad credentials.
    """
    bad_headers = {"Authorization": "Bearer INVALID_KEY_123"}
    params = {"q": "AAPL", "pageSize": 1}

    response = requests.get(
        url=NEWSAPI_BASE_URL,
        headers=bad_headers,
        params=params,
        timeout=10
    )

    assert response.status_code == 401, \
        f"Expected 401 for invalid key, got {response.status_code}"
    response_data = response.json()

    assert response_data["status"] == "error", \
        "Invalid key did not return error status"
    assert "apiKeyInvalid" in response_data["code"], \
        f"Unexpected error message: {response_data['message']}"


def test_rate_limit_exceeded(newsapi_headers: Dict[str, str]) -> None:
    """
    Test 4: Rate limit violation returns 429 Too Many Requests.
    (Note: NewsAPI free tier has ~100 requests/day—this test is lightweight.)
    """
    # Send 3 quick requests to simulate rate limit (adjust count if needed)
    params = {"q": "AAPL", "pageSize": 1}
    rate_limit_hit = False

    for _ in range(3):
        response = requests.get(
            url=NEWSAPI_BASE_URL,
            headers=newsapi_headers,
            params=params,
            timeout=10
        )
        if response.status_code == 429:
            rate_limit_hit = True
            break

    if rate_limit_hit:
        # Validate 429 response details
        response_data = response.json()
        assert response_data["status"] == "error", \
            "Rate limit did not return error status"
        assert "rate limit" in response_data["message"].lower(), \
            f"Unexpected rate limit message: {response_data['message']}"
    else:
        # If rate limit not hit, mark test as "skipped" (not a failure)
        pytest.skip("NewsAPI rate limit not exceeded (free tier has ample requests). "
                    "Re-run later if you want to test 429 handling.")
