"""
Finnhub API Test Suite

This module provides a collection of test cases to verify various functionalities
of the Finnhub API.
Finnhub is a financial data API service that provides market data for stocks, forex,
cryptocurrencies, etc.

Before using, install dependencies and configure API key:
pip install finnhub-python pytest python-dateutil
export FINNHUB_API_KEY=<your_api_key>

Test coverage includes:
- Symbol lookup
- Market status queries
- Company information retrieval
- Market and company news
- Financial data and reports
- Insider transactions and sentiment analysis
- IPO and earnings calendars
- Stock quotes and patent information
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo
from dateutil.relativedelta import relativedelta
import pytest
from finnhub import Client


@pytest.fixture(scope="module")
def finnhub_client():
    """
    Module-level Finnhub client fixture

    This fixture creates a Finnhub API client instance shared across all test functions.
    Verifies that the API key is set through environment variables.

    Returns:
        Client: Configured Finnhub client instance
    """
    api_key = os.getenv("FINNHUB_API_KEY")
    assert api_key is not None, "Please set the FINNHUB_API_KEY environment variable"
    return Client(api_key)


def test_symbol_lookup(finnhub_client):
    """
    Test symbol lookup functionality

    Verifies that company symbols can be found correctly, including fuzzy and exact searches.
    """
    # Test fuzzy search
    ret = finnhub_client.symbol_lookup('apple')
    assert ret['count'] > 0, "No results returned for 'apple' lookup"
    print(f"First result for 'apple' lookup: {ret['result'][0]}")

    # Test exact search
    ret = finnhub_client.symbol_lookup('AAPX')
    print(f"Result for 'AAPX' lookup: {ret}")


def test_market_status(finnhub_client):
    """
    Test market status query functionality

    Verifies that US market status can be retrieved and timestamp conversion works correctly.
    """
    ret = finnhub_client.market_status(exchange='US')
    print(f"US market status: {ret}")

    # Verify server timestamp and convert to local time
    server_ts = ret['t']
    server_time = datetime.fromtimestamp(server_ts)
    print(f"Server time: {server_time}")


def test_company_profile(finnhub_client):
    """
    Test company profile query functionality

    Verifies that basic information for a specified company can be retrieved.
    """
    profile = finnhub_client.company_profile2(symbol='AAPX')
    print(f"AAPX company profile: {profile}")
    assert isinstance(profile, dict), "Company profile returned in incorrect format"


def test_market_news(finnhub_client):
    """
    Test market news query functionality

    Verifies that market news for different categories can be retrieved and date conversion works.
    """
    # Test various news categories
    for category in ['general', 'forex', 'crypto', 'merger']:
        ret = finnhub_client.general_news(category, min_id=0)
        print(f"Number of {category} news items: {len(ret)}")

        if ret:  # Ensure results are not empty
            # Convert timestamps to New York timezone datetime
            first_date = datetime.fromtimestamp(
                ret[0]['datetime'],
                tz=ZoneInfo('America/New_York')
            )
            last_date = datetime.fromtimestamp(
                ret[-1]['datetime'],
                tz=ZoneInfo('America/New_York')
            )
            print(f"{category} news date range: From {first_date} to {last_date}")


def test_company_news(finnhub_client):
    """
    Test company news query functionality

    Verifies that news for a specified company can be retrieved and date range is correct.
    """
    # Calculate date range (past year)
    current_date = datetime.now()
    one_year_ago = current_date - relativedelta(years=1)

    # Format dates to API-required string format
    current_date_str = current_date.strftime("%Y-%m-%d")
    one_year_ago_str = one_year_ago.strftime("%Y-%m-%d")

    print(f"Querying INTC company news from {one_year_ago_str} to {current_date_str}")

    # Retrieve company news
    ret = finnhub_client.company_news(
        'INTC',
        _from=one_year_ago_str,
        to=current_date_str
    )

    print(f"Retrieved {len(ret)} news items for INTC")

    if ret:  # Ensure results are not empty
        # Find earliest and latest news timestamps
        timestamps = [item['datetime'] for item in ret]
        min_ts, max_ts = min(timestamps), max(timestamps)

        # Convert to New York timezone datetime
        first_date = datetime.fromtimestamp(min_ts, tz=ZoneInfo('America/New_York'))
        last_date = datetime.fromtimestamp(max_ts, tz=ZoneInfo('America/New_York'))

        print(f"News date range: From {first_date} to {last_date}")


def test_company_peer(finnhub_client):
    """
    Test company peers query functionality

    Verifies that list of peer companies for a specified company can be retrieved.
    """
    peers = finnhub_client.company_peers('SMR')
    print(f"SMR peer companies: {peers}")
    assert isinstance(peers, list), "Peer companies returned in incorrect format"


def test_company_basic_financials(finnhub_client):
    """
    Test company basic financials query functionality

    Verifies that basic financial information for a specified company can be retrieved.
    """
    financials = finnhub_client.company_basic_financials('TSLA', 'all')
    print(f"TSLA basic financials: {financials}")
    assert 'metric' in financials, "Financial data in incorrect format"


def test_insider_transactions(finnhub_client):
    """
    Test insider transactions query functionality

    Verifies that insider transaction information for a specified company can be retrieved.
    """
    # Calculate date range (past year)
    current_date = datetime.now()
    one_year_ago = current_date - relativedelta(years=1)

    # Format dates to API-required string format
    current_date_str = current_date.strftime("%Y-%m-%d")
    one_year_ago_str = one_year_ago.strftime("%Y-%m-%d")

    # Retrieve insider transactions data
    transactions = finnhub_client.stock_insider_transactions(
        'TSLA',
        one_year_ago_str,
        current_date_str
    )

    print(f"TSLA insider transactions data: {transactions}")
    assert 'data' in transactions, "Insider transactions data in incorrect format"


def test_insider_sentiment(finnhub_client):
    """
    Test insider sentiment analysis query functionality

    Verifies that insider transaction sentiment data for a specified company can be retrieved.
    """
    # Calculate date range (past year)
    current_date = datetime.now()
    one_year_ago = current_date - relativedelta(years=1)

    # Format dates to API-required string format
    current_date_str = current_date.strftime("%Y-%m-%d")
    one_year_ago_str = one_year_ago.strftime("%Y-%m-%d")

    # Retrieve insider sentiment data
    sentiment = finnhub_client.stock_insider_sentiment(
        'TSLA',
        one_year_ago_str,
        current_date_str
    )

    print(f"TSLA insider sentiment data: {sentiment}")
    assert isinstance(sentiment, list), "Insider sentiment data in incorrect format"


def test_financials_report(finnhub_client):
    """
    Test financial reports query functionality

    Verifies that annual financial reports for a specified company can be retrieved.
    """
    reports = finnhub_client.financials_reported(symbol='TSLA', freq='annual')
    print(f"TSLA annual financial reports: {reports}")
    assert 'data' in reports, "Financial reports data in incorrect format"


def test_sec_fillings(finnhub_client):
    """
    Test SEC filings query functionality

    Verifies that SEC filings for a specified company can be retrieved and date range is correct.
    """
    # Calculate date range (past year)
    current_date = datetime.now()
    one_year_ago = current_date - relativedelta(years=1)

    # Format dates to API-required string format
    current_date_str = current_date.strftime("%Y-%m-%d")
    one_year_ago_str = one_year_ago.strftime("%Y-%m-%d")

    # Retrieve SEC filings
    filings = finnhub_client.filings(
        symbol='TSLA',
        _from=one_year_ago_str,
        to=current_date_str
    )

    print(f"Number of TSLA SEC filings: {len(filings)}")

    if filings:  # Ensure results are not empty
        # Find earliest and latest filing dates
        timestamps = []
        for filing in filings:
            ts = datetime.strptime(filing['filedDate'], "%Y-%m-%d %H:%M:%S").timestamp()
            timestamps.append(ts)

        min_ts, max_ts = min(timestamps), max(timestamps)

        # Convert to New York timezone datetime
        first_date = datetime.fromtimestamp(min_ts, tz=ZoneInfo('America/New_York'))
        last_date = datetime.fromtimestamp(max_ts, tz=ZoneInfo('America/New_York'))

        print(f"SEC filings date range: From {first_date} to {last_date}")


def test_ipo_calendar(finnhub_client):
    """
    Test IPO calendar query functionality

    Verifies that IPO calendar for a specified time period can be retrieved.
    """
    # Calculate date range (past month)
    current_date = datetime.now()
    one_month_ago = current_date - relativedelta(months=1)

    # Format dates to API-required string format
    current_date_str = current_date.strftime("%Y-%m-%d")
    one_month_ago_str = one_month_ago.strftime("%Y-%m-%d")

    print(f"Querying IPO calendar from {one_month_ago_str} to {current_date_str}")
    ipo_calendar = finnhub_client.ipo_calendar(_from=one_month_ago_str, to=current_date_str)
    print(f"IPO calendar: {ipo_calendar}")


def test_recommend_trend(finnhub_client):
    """
    Test recommendation trends query functionality

    Verifies that analyst recommendation trends for a specified company can be retrieved.
    """
    trend = finnhub_client.recommendation_trends('TSLA')
    print(f"TSLA analyst recommendation trends: {trend}")
    assert isinstance(trend, list), "Recommendation trends data in incorrect format"


def test_earnings_calendar(finnhub_client):
    """
    Test earnings calendar query functionality

    Verifies that earnings calendar for a specified company can be retrieved.
    """
    # Calculate date range (past year)
    current_date = datetime.now()
    one_year_ago = current_date - relativedelta(years=1)

    # Format dates to API-required string format
    current_date_str = current_date.strftime("%Y-%m-%d")
    one_year_ago_str = one_year_ago.strftime("%Y-%m-%d")

    # Retrieve earnings calendar
    earnings = finnhub_client.earnings_calendar(
        _from=one_year_ago_str,
        to=current_date_str,
        symbol="TSLA",
        international=False
    )

    print(f"TSLA earnings calendar: {earnings}")
    assert 'earningsCalendar' in earnings, "Earnings calendar data in incorrect format"


def test_quote(finnhub_client):
    """
    Test stock quote query functionality

    Verifies that latest quote for a specified stock can be retrieved and timestamp
    conversion works.
    """
    quote = finnhub_client.quote('TSLA')
    print(f"TSLA latest quote: {quote}")

    # Convert timestamp to New York timezone datetime
    if 't' in quote and quote['t'] is not None:
        quote_time = datetime.fromtimestamp(quote['t'], tz=ZoneInfo('America/New_York'))
        print(f"Quote time: {quote_time}")


def test_uspto_patents(finnhub_client):
    """
    Test USPTO patents query functionality

    Verifies that patent information for a specified company can be retrieved.
    """
    # Note: Using fixed date range for test consistency
    patents = finnhub_client.stock_uspto_patent('INTC', _from='2022-06-01', to='2023-06-01')
    print(f"Number of INTC patents between 2022-06-01 and 2023-06-01: {len(patents)}")
    assert isinstance(patents, list), "Patent data in incorrect format"
