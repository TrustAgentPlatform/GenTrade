import os
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
import pytest
import requests
from gentrade.news.factory import NewsFactory
from gentrade.news.meta import NewsProviderBase
from gentrade.news.newsapi import NewsApiProvider
from gentrade.news.finnhub import FinnhubNewsProvider
from gentrade.news.rss import RssProvider


# ------------------------------ NewsFactory Tests ------------------------------
class TestNewsFactory:
    """Tests for NewsFactory provider creation logic"""

    @patch.dict(os.environ, {"NEWSAPI_API_KEY": "test_newsapi_key"})
    def test_create_newsapi_provider(self):
        """Test NewsAPI provider creation with valid env var"""
        provider = NewsFactory.create_provider("newsapi")
        assert isinstance(provider, NewsApiProvider)
        assert provider.api_key == "test_newsapi_key"

    def test_create_newsapi_missing_key(self):
        """Test NewsAPI creation fails with missing API key"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as excinfo:
                NewsFactory.create_provider("newsapi")
            assert "NEWSAPI_API_KEY" in str(excinfo.value)

    @patch.dict(os.environ, {"FINNHUB_API_KEY": "test_finnhub_key"})
    def test_create_finnhub_provider(self):
        """Test Finnhub provider creation with valid env var"""
        provider = NewsFactory.create_provider("finnhub")
        assert isinstance(provider, FinnhubNewsProvider)
        assert provider.api_key == "test_finnhub_key"

    def test_create_finnhub_missing_key(self):
        """Test Finnhub creation fails with missing API key"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as excinfo:
                NewsFactory.create_provider("finnhub")
            assert "FINNHUB_API_KEY" in str(excinfo.value)

    def test_create_rss_provider_with_feed_url(self):
        """Test RSS provider creation with explicit feed URL"""
        feed_url = "https://test-feed.com/rss"
        provider = NewsFactory.create_provider("rss", feed_url=feed_url)
        assert isinstance(provider, RssProvider)
        assert provider.feed_url == feed_url

    @patch.dict(os.environ, {"RSS_FEED_URL": "https://env-feed.com/rss"})
    def test_create_rss_provider_from_env(self):
        """Test RSS provider uses env var when no URL is provided"""
        provider = NewsFactory.create_provider("rss")
        assert provider.feed_url == "https://env-feed.com/rss"

    def test_create_rss_provider_default_url(self):
        """Test RSS provider uses default URL when no env var/URL provided"""
        with patch.dict(os.environ, {}, clear=True):
            provider = NewsFactory.create_provider("rss")
            assert provider.feed_url == "https://plink.anyfeeder.com/chinadaily/caijing"

    def test_create_unknown_provider(self):
        """Test factory raises error for unknown provider types"""
        with pytest.raises(ValueError) as excinfo:
            NewsFactory.create_provider("unknown")
        assert "Unknown provider type: unknown" in str(excinfo.value)


# ------------------------------ News Provider Common Tests ------------------------------
class TestNewsProvidersCommon:
    """Parametrized tests for common provider functionality"""

    @pytest.fixture(params=[
        ("newsapi", NewsApiProvider, {"NEWSAPI_API_KEY": "test_key"}),
        ("finnhub", FinnhubNewsProvider, {"FINNHUB_API_KEY": "test_key"}),
        ("rss", RssProvider, {})
    ])
    def provider_setup(self, request):
        """Fixture providing provider type, class, and required env vars"""
        provider_type, provider_class, env_vars = request.param
        with patch.dict(os.environ, env_vars):
            if provider_type == "rss":
                provider = NewsFactory.create_provider(provider_type,
                    feed_url="https://test.com/rss")
            else:
                provider = NewsFactory.create_provider(provider_type)
        return provider_type, provider_class, provider

    def test_provider_base_class(self, provider_setup):
        """Test all providers inherit from NewsProviderBase"""
        _, _, provider = provider_setup
        assert isinstance(provider, NewsProviderBase)

    def test_fetch_market_news_returns_list(self, provider_setup):
        """Test market news fetch returns list (empty or with items)"""
        _, _, provider = provider_setup
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200

            # Provider-specific mock responses
            if provider_setup[0] == "newsapi":
                mock_response.json.return_value = {"articles": []}
            elif provider_setup[0] == "finnhub":
                mock_response.json.return_value = []
            elif provider_setup[0] == "rss":
                pass  # Handled in RSS specific tests

            mock_get.return_value = mock_response

            result = provider.fetch_stock_news(ticker="AAPL")
            assert isinstance(result, list)

    def test_fetch_stock_news_returns_list(self, provider_setup):
        """Test stock news fetch returns list (empty or with items)"""
        provider_type, _, provider = provider_setup
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200

            # Match mock responses to actual provider return formats
            if provider_type == "newsapi":
                # NewsAPI returns {"articles": [...]}
                mock_response.json.return_value = {"articles": []}
            elif provider_type == "finnhub":
                # Finnhub returns list directly
                mock_response.json.return_value = []
            elif provider_type == "rss":
                # RSS uses feedparser, handled separately
                pass

            mock_get.return_value = mock_response

            result = provider.fetch_stock_news(ticker="AAPL")
            assert isinstance(result, list)

# ------------------------------ Provider-Specific Tests ------------------------------
class TestNewsApiProvider:
    """NewsAPI-specific test cases"""

    @pytest.fixture
    def newsapi_provider(self):
        with patch.dict(os.environ, {"NEWSAPI_API_KEY": "test_key"}):
            return NewsFactory.create_provider("newsapi")

    @patch("gentrade.news.newsapi.requests.get")
    def test_fetch_market_news_params(self, mock_get, newsapi_provider):
        """Test NewsAPI market news uses correct parameters"""
        mock_get.return_value = Mock(status_code=200, json=lambda: {"articles": []})
        newsapi_provider.fetch_latest_market_news(
            category="finance",
            max_hour_interval=12,
            max_count=5
        )

        _, kwargs = mock_get.call_args
        params = kwargs["params"]
        assert params["q"] == "financial market OR stock market"
        assert params["language"] == "en"
        assert "from" in params


class TestRssProvider:
    """RSS Provider-specific test cases"""

    @pytest.fixture
    def rss_provider(self):
        return NewsFactory.create_provider("rss", feed_url="https://test.com/rss")

    @patch("feedparser.parse")
    def test_rss_feed_parsing(self, mock_parse):
        # Calculate a timestamp within the default 24-hour window
        recent_time = (datetime.now() - timedelta(hours=1)).isoformat() + "Z"  # 1 hour ago

        # Mock a valid RSS feed response with recent timestamp
        mock_parse.return_value = {
            "entries": [
                {
                    "title": "Test Article",
                    "link": "https://example.com/news",
                    "published": recent_time,  # Use time within 24 hours
                    "summary": "Test summary content",
                    "media_content": [{"url": "https://example.com/image.jpg"}]
                }
            ],
            "feed": {"title": "Test Feed"}
        }

        provider = RssProvider()
        news = provider.fetch_latest_market_news(max_count=1)
        assert len(news) == 1
        assert news[0].headline == "Test Article"
        assert news[0].url == "https://example.com/news"


class TestFinnhubProviderAdditional:
    """Additional Finnhub-specific tests"""

    @pytest.fixture
    def finnhub_provider(self):
        with patch.dict(os.environ, {"FINNHUB_API_KEY": "test_key"}):
            return NewsFactory.create_provider("finnhub")

    @patch("gentrade.news.finnhub.requests.get")
    def test_company_news_endpoint(self, mock_get, finnhub_provider):
        """Test Finnhub uses correct endpoint for company news"""
        mock_get.return_value = Mock(status_code=200, json=lambda: [])
        finnhub_provider.fetch_stock_news(ticker="AAPL")

        args, _ = mock_get.call_args
        assert "company-news" in args[0]


# ------------------------------ Error Handling Tests ------------------------------
class TestProviderErrorHandling:
    """Tests for provider error handling"""

    @pytest.fixture(params=["newsapi", "finnhub"])
    def api_provider(self, request):
        """Fixture for API-based providers (non-RSS)"""
        provider_type = request.param
        env_vars = {
            "newsapi": {"NEWSAPI_API_KEY": "test"},
            "finnhub": {"FINNHUB_API_KEY": "test"}
        }[provider_type]

        with patch.dict(os.environ, env_vars):
            return NewsFactory.create_provider(provider_type)

    @patch("requests.get")
    def test_provider_handles_http_errors(self, mock_get, api_provider):
        """Test providers return empty list on HTTP errors"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Forbidden")
        mock_get.return_value = mock_response

        market_news = api_provider.fetch_latest_market_news()
        stock_news = api_provider.fetch_stock_news(ticker="AAPL")

        assert market_news == []
        assert stock_news == []

    @patch("requests.get")
    def test_provider_handles_connection_errors(self, mock_get, api_provider):
        """Test providers return empty list on connection errors"""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        market_news = api_provider.fetch_latest_market_news()
        stock_news = api_provider.fetch_stock_news(ticker="AAPL")

        assert market_news == []
        assert stock_news == []
