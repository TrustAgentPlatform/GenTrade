"""
Yahoo Finance API Test Suite

This test suite verifies that both stock price data and financial news can be retrieved
from Yahoo Finance using the yfinance library as a wrapper for the Yahoo Finance API.

Dependencies:
- pip install yfinance pytest pandas

Test coverage includes validation of:
- Successful price data retrieval for different intervals
- Correct price data structure and columns
- Reasonable date ranges based on interval
- Non-empty price data
- Successful news retrieval for major US stocks
- News item structure and required fields
- News relevance and timeliness
"""
from datetime import datetime, timedelta
import pytest
import yfinance as yf
import pandas as pd


# ------------------------------
# Shared Fixtures
# ------------------------------
@pytest.fixture(params=["AAPL", "MSFT", "NVDA", "TSLA"],
                ids=[f"Ticker:{ticker}" for ticker in ["AAPL", "MSFT", "NVDA", "TSLA"]])
def ticker_symbol(request):
    """Parameterized fixture providing multiple test ticker symbols"""
    return request.param


@pytest.fixture
def ticker_object(ticker_symbol):
    """Fixture providing a yfinance Ticker object for the given symbol"""
    return yf.Ticker(ticker_symbol)


# ------------------------------
# Stock Price Interval Tests
# ------------------------------
@pytest.mark.prices
@pytest.mark.parametrize("interval, max_history_days, min_expected_rows", [
    ("1m", 7, 10),       # 1 minute - max 7 days history
    ("1d", None, 30),    # 1 day - using 1 year for test
    ("5d", None, 10),    # 5 days
])
def test_stock_price_by_interval(ticker_object, interval, max_history_days, min_expected_rows):
    """
    Test stock price retrieval for different intervals.

    Args:
        ticker_object: Ticker fixture
        interval: Time interval for data (e.g., "30m", "1h", "1d")
        max_history_days: Maximum days of history available for this interval
        min_expected_rows: Minimum number of rows expected in response
    """
    # Calculate date range based on interval limitations
    end_date = datetime.now()
    if max_history_days:
        start_date = end_date - timedelta(days=max_history_days)
    else:
        # For intervals with no max (daily+), use 1 year of data
        start_date = end_date - timedelta(days=365)

    # Convert to string format (YYYY-MM-DD)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    # Retrieve historical data
    hist = ticker_object.history(
        start=start_str,
        end=end_str,
        interval=interval
    )

    # 1. Verify data structure
    assert isinstance(hist, pd.DataFrame), f"Expected DataFrame for {interval}, got {type(hist)}"

    # 2. Verify required columns exist
    required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in required_columns:
        assert col in hist.columns, f"Missing required column {col} for interval {interval}"

    # 3. Verify we got enough data points
    assert len(hist) >= min_expected_rows, (
        f"Insufficient data for {ticker_object.ticker} {interval}. "
        f"Got {len(hist)} rows, expected at least {min_expected_rows}"
    )

    # 4. Verify date range is within requested range
    first_date = hist.index[0].date()
    last_date = hist.index[-1].date()

    assert first_date >= start_date.date(), (
        f"First data point {first_date} earlier than requested start {start_date.date()}"
    )
    assert last_date <= end_date.date(), (
        f"Last data point {last_date} later than requested end {end_date.date()}"
    )

    # 5. Verify price data is not all zero/NaN
    assert not hist['Close'].isna().all(), f"All Close prices are NaN for {interval}"
    assert not (hist['Close'] == 0).all(), f"All Close prices are zero for {interval}"

    print(f"{ticker_object.ticker} {interval}: Retrieved {len(hist)} rows from {first_date} \
            to {last_date}")


# ------------------------------
# Financial News Tests - Updated for current Yahoo Finance API format
# ------------------------------
@pytest.mark.news
def test_news_retrieval_success(ticker_object):
    """Test successful retrieval of news for a given stock ticker"""
    news = ticker_object.news

    # Basic validation: News should be a non-empty list
    assert isinstance(news, list), f"News for {ticker_object.ticker} is not a list"
    assert len(news) > 0, f"No news found for {ticker_object.ticker}"


@pytest.mark.news
def test_news_contains_required_fields(ticker_object):
    """Test that each news item contains all required fields (updated for current API)"""
    news = ticker_object.news
    # Updated field names based on current Yahoo Finance API response
    required_fields = ["title", "provider", "pubDate"]

    for idx, item in enumerate(news, 1):
        print('---------------------------------')
        print(item.keys())
        print('---------------------------------')
        item_content = item['content']
        print(item_content)
        # Check all required fields exist
        for field in required_fields:
            assert field in item_content, (
                f"{ticker_object.ticker} news item {idx} missing required field: '{field}'"
            )

            # Check fields have non-empty values
            assert item_content[field] is not None, (
                f"{ticker_object.ticker} news item {idx} has None value for '{field}'"
            )

            if field != "pubDate":  # Skip timestamp for string check
                assert str(item_content[field]).strip() != "", (
                    f"{ticker_object.ticker} news item {idx} has empty value for '{field}'"
                )


@pytest.mark.news
def test_news_timeliness(ticker_object):
    """Test that news items are relatively recent (within 7 days)"""
    news = ticker_object.news
    max_age_days = 7
    now = datetime.now()
    max_age_timestamp = (now - timedelta(days=max_age_days)).timestamp()

    for idx, item in enumerate(news, 1):
        # Use updated timestamp field name "pubTime" (Yahoo's current field)
        print(item['content'])
        # Convert Yahoo's timestamp (seconds, not milliseconds)
        publish_time = datetime.strptime(
            item['content']["pubDate"], "%Y-%m-%dT%H:%M:%SZ").timestamp()

        assert publish_time >= max_age_timestamp, (
            f"{ticker_object.ticker} news item {idx} is too old. "
            f"Published {datetime.fromtimestamp(publish_time).strftime('%Y-%m-%d')}, "
            f"which is more than {max_age_days} days ago"
        )


@pytest.mark.news
def test_news_relevance(ticker_object):
    """Test that news items are relevant to the stock"""
    news = ticker_object.news
    ticker = ticker_object.ticker

    # Get company name for relevance check
    info = ticker_object.info
    company_name = info.get("longName", "").lower()
    ticker_lower = ticker.lower()

    # Track if we found at least one relevant article
    has_relevant_news = False

    for item in news:
        # Use updated title field name
        title = item['content']["title"].lower()
        # Check if title contains ticker or company name
        if ticker_lower in title or (company_name and company_name in title):
            has_relevant_news = True
            break

    assert has_relevant_news, (
        f"No relevant news found for {ticker} ({company_name}). "
        "News titles don't mention the ticker or company name"
    )
