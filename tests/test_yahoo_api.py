"""
Yahoo Finance API Interval Test Suite

This test suite verifies that stock price data can be retrieved from Yahoo Finance
using different time intervals. It uses the yfinance library as a wrapper for the
Yahoo Finance API.

Dependencies:
- pip install yfinance pytest pandas

Test coverage includes validation of:
- Successful data retrieval for different intervals
- Correct data structure and columns
- Reasonable date ranges based on interval
- Non-empty price data
"""

import pytest
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


@pytest.fixture(scope="module")
def test_ticker():
    """Fixture providing a test ticker object (Apple Inc.)"""
    return yf.Ticker("AAPL")


# Define test parameters: (interval, max_days, expected_periods)
@pytest.mark.parametrize("interval, max_history_days, min_expected_rows", [
    ("1m", 7, 10),       # 1 minute - max 7 days history
    ("1d", None, 30),    # 1 day - max unlimited (using 1 year for test)
    ("5d", None, 10),    # 5 days
])
def test_stock_price_by_interval(test_ticker, interval, max_history_days, min_expected_rows):
    """
    Test stock price retrieval for different intervals.

    Args:
        test_ticker: Ticker fixture (AAPL)
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

    # Retrieve historical data - removed progress parameter for compatibility
    hist = test_ticker.history(
        start=start_str,
        end=end_str,
        interval=interval
    )
    print(hist)
    # 1. Verify data structure
    assert isinstance(hist, pd.DataFrame), f"Expected DataFrame for {interval}, got {type(hist)}"

    # 2. Verify required columns exist
    required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in required_columns:
        assert col in hist.columns, f"Missing required column {col} for interval {interval}"

    # 3. Verify we got enough data points
    assert len(hist) >= min_expected_rows, (
        f"Insufficient data for {interval}. "
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

    print(f"Interval {interval}: Retrieved {len(hist)} rows from {first_date} to {last_date}")
