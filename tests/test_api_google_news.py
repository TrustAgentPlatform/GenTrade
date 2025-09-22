"""
Google News API Test Suite

This module contains pytest tests to verify functionality of Google's Custom Search API
for retrieving financial and stock-related news. It includes tests for:
- API credential validation
- General financial news retrieval
- Specific stock symbol news retrieval

Requirements:
- Valid Google Cloud API key with Custom Search API enabled: GOOGLE_API_KEY
- Custom Search Engine ID (CX) configured for news search: CX
- Environment variables stored in .env file
"""

import os
import requests
import pytest
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@pytest.fixture(scope="module")
def api_credentials():
    """
    Fixture to validate and provide API credentials.

    Retrieves Google API key and Custom Search Engine ID from environment variables
    and performs basic validation. Fails if any credential is missing.

    Returns:
        dict: Contains valid API credentials with keys 'api_key' and 'cx'
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    cx = os.getenv("GOOGLE_CX")

    error_messages = []
    if not api_key:
        error_messages.append(
            "GOOGLE_API_KEY not found in environment variables. "
            "Please check your .env file."
        )
    if not cx:
        error_messages.append(
            "GOOGLE_CX (Custom Search Engine ID) not found. "
            "Please check your .env file."
        )

    assert not error_messages, "\n".join(error_messages)

    return {
        "api_key": api_key,
        "cx": cx
    }


def test_api_credentials_work(api_credentials):
    """
    Test if API credentials are valid and functional.

    Performs a basic test query to verify that the provided API key and
    CX ID can successfully authenticate with the Google Custom Search API.
    Provides detailed error messages for common authentication issues.
    """
    url = "https://www.googleapis.com/customsearch/v1"
    test_params = {
        "key": api_credentials["api_key"],
        "cx": api_credentials["cx"],
        "q": "test query",
        "num": 1
    }

    response = requests.get(url, params=test_params, timeout=30)

    # Handle common authentication errors with detailed guidance
    if response.status_code == 403:
        pytest.fail(
            "403 Forbidden: Invalid credentials or insufficient permissions.\n"
            "Possible fixes:\n"
            "1. Verify your API key is correct in .env\n"
            "2. Ensure Custom Search API is enabled in Google Cloud Console\n"
            "3. Check if your API key has IP restrictions that block this request\n"
            "4. Confirm your project has billing enabled (required for production use)\n"
            f"API Response: {response.text}"
        )
    elif response.status_code == 400:
        pytest.fail(
            f"400 Bad Request: Invalid parameters. Check your CX ID.\n"
            f"API Response: {response.text}"
        )

    assert response.status_code == 200, \
        f"API request failed with status code {response.status_code}. Response: {response.text}"


def test_get_latest_financial_news(api_credentials):
    """
    Test retrieval of latest financial news from Google News.

    Queries the Custom Search API for recent financial news (past 1 week)
    and validates the structure and content of returned results.
    """
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_credentials["api_key"],
        "cx": api_credentials["cx"],
        "q": "finance stock market",
        "num": 10,
        "dateRestrict": "w1",  # Restrict results to past 1 week
        "gl": "us",            # Focus on United States results
        "lr": "lang_en",       # Restrict to English language
        "siteSearch": "news.google.com",  # Search only Google News
        "siteSearchFilter": "i"           # Include only specified sites
    }

    # Execute API request
    response = requests.get(url, params=params, timeout=30)

    # Handle specific API errors
    if response.status_code == 403:
        pytest.fail(f"403 Forbidden: Check API key and permissions. Response: {response.text}")
    if response.status_code == 429:
        pytest.fail(f"429 Too Many Requests: API quota exceeded. Response: {response.text}")

    # Verify successful response
    assert response.status_code == 200, \
        f"API request failed with status code {response.status_code}. Response: {response.text}"

    # Parse and validate response content
    results = response.json()

    assert "items" in results, f"No news items found. API response: {results}"
    assert len(results["items"]) > 0, "No articles returned from Google News"

    # Validate individual news articles
    for item in results["items"][:3]:  # Check first 3 articles
        assert "title" in item, "News item missing title"
        assert "link" in item, "News item missing URL"
        assert "snippet" in item, "News item missing snippet"


def test_get_specific_stock_news(api_credentials):
    """
    Test retrieval of news for specific stock symbols.

    Queries the Custom Search API for news related to major tech stocks
    and verifies that returned articles mention the target stock symbol.
    """
    stock_symbols = ["AAPL", "MSFT", "GOOGL"]
    url = "https://www.googleapis.com/customsearch/v1"

    for symbol in stock_symbols:
        params = {
            "key": api_credentials["api_key"],
            "cx": api_credentials["cx"],
            "q": f"{symbol} stock news",
            "num": 5,
            "dateRestrict": "w1",  # Restrict to past 1 week
            "gl": "us",
            "lr": "lang_en",
            "siteSearch": "news.google.com",
            "siteSearchFilter": "i"
        }

        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 403:
            pytest.fail(f"403 Forbidden for {symbol}: Check API key and permissions")

        assert response.status_code == 200, \
            f"Failed to get news for {symbol} (status code {response.status_code})"

        results = response.json()

        # Validate stock symbol appears in results when available
        if "items" in results and len(results["items"]) > 0:
            symbol_in_results = any(
                symbol in item["title"].upper() or symbol in item.get("snippet", "").upper()
                for item in results["items"]
            )
            assert symbol_in_results, f"No results mentioning {symbol} found"
