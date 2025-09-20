"""
Baostock API Test Suite

This test suite verifies the functionality of Baostock API for retrieving Chinese stock market data.
Baostock provides free financial data for A-shares, indices, and other financial instruments,
with no API key required.

Dependencies:
- pip install pytest baostock pandas

Test coverage includes:
- API connection and initialization
- Retrieval of historical stock quotes (OHLCV)
- Verification of data for different time periods (daily, weekly, monthly)
- Index data retrieval
- Error handling for exceptional cases
"""
from datetime import datetime, timedelta
import pytest
import baostock as bs
import pandas as pd


# Global variables defining test stock and index codes
TEST_STOCK_CODE = "sh.600000"  # Shanghai Pudong Development Bank
TEST_INDEX_CODE = "sh.000001"  # Shanghai Composite Index
TEST_START_DATE = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")  # Past year
TEST_END_DATE = datetime.now().strftime("%Y-%m-%d")

# pylint: disable=unused-argument

@pytest.fixture(scope="module")
def baostock_connection():
    """
    Module-level Baostock connection fixture

    Initializes Baostock connection and properly closes it after tests complete
    """
    # Login to Baostock
    login_result = bs.login()
    assert login_result.error_code == '0', f"Login failed: {login_result.error_msg}"

    yield  # Provide connection to test cases

    # Logout after tests
    bs.logout()


def test_baostock_login_logout():
    """Test Baostock login and logout functionality"""
    # Test login
    login_result = bs.login()
    assert login_result.error_code == '0', f"Login failed: {login_result.error_msg}"

    # Test logout
    logout_result = bs.logout()
    assert logout_result.error_code == '0', f"Logout failed: {logout_result.error_msg}"


def test_get_stock_daily_data(baostock_connection):
    """Test retrieval of daily stock data"""
    # Get daily data
    rs = bs.query_history_k_data_plus(
        TEST_STOCK_CODE,
        "date,code,open,high,low,close,volume,amount",
        start_date=TEST_START_DATE,
        end_date=TEST_END_DATE,
        frequency="d",
        adjustflag="3"  # 3 = no adjustment, 2 = post-adjustment, 1 = pre-adjustment
    )

    assert rs.error_code == '0', f"Failed to get daily data: {rs.error_msg}"

    # Parse data
    data_list = []
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data())

    # Create DataFrame
    df = pd.DataFrame(
        data_list,
        columns=rs.fields
    )

    # Validate data
    assert not df.empty, "Daily data is empty"
    assert len(df) > 200, f"Insufficient daily data, only {len(df)} records retrieved"

    # Verify required fields exist
    required_columns = ["date", "code", "open", "high", "low", "close", "volume", "amount"]
    for col in required_columns:
        assert col in df.columns, f"Missing required field: {col}"

    # Verify data types
    numeric_columns = ["open", "high", "low", "close", "volume", "amount"]
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        assert not df[col].isna().all(), f"Field {col} contains all invalid values"
        assert (df[col] >= 0).all(), f"Field {col} contains negative values"

    print(f"Stock daily data test passed, retrieved {len(df)} daily records for {TEST_STOCK_CODE}")


@pytest.mark.parametrize("frequency, min_expected_rows", [
    ("d", 200),   # Daily, expect at least 200 records
    ("w", 40),    # Weekly, expect at least 40 records
    ("m", 10)     # Monthly, expect at least 10 records
])
def test_get_stock_kline_data(baostock_connection, frequency, min_expected_rows):
    """Test retrieval of stock K-line data for different periods"""
    rs = bs.query_history_k_data_plus(
        TEST_STOCK_CODE,
        "date,code,open,high,low,close,volume",
        start_date=TEST_START_DATE,
        end_date=TEST_END_DATE,
        frequency=frequency,
        adjustflag="2"  # Post-adjustment
    )

    assert rs.error_code == '0', f"Failed to get {frequency} data: {rs.error_msg}"

    # Parse data
    data_list = []
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data())

    df = pd.DataFrame(data_list, columns=rs.fields)
    print(df)
    # Validate data
    assert not df.empty, f"{frequency} data is empty"
    assert len(df) >= min_expected_rows, \
        f"Insufficient {frequency} data, only {len(df)} records retrieved"

    print(f"{frequency} data test passed, retrieved {len(df)} records")


def test_get_index_data(baostock_connection):
    """Test retrieval of index data"""
    rs = bs.query_history_k_data_plus(
        TEST_INDEX_CODE,
        "date,code,open,high,low,close,volume",
        start_date=TEST_START_DATE,
        end_date=TEST_END_DATE,
        frequency="d"
    )

    assert rs.error_code == '0', f"Failed to get index data: {rs.error_msg}"

    # Parse data
    data_list = []
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data())

    df = pd.DataFrame(data_list, columns=rs.fields)

    # Validate data
    assert not df.empty, "Index data is empty"
    assert len(df) > 200, f"Insufficient index data, only {len(df)} records retrieved"

    print(f"Index data test passed, retrieved {len(df)} daily records for {TEST_INDEX_CODE}")


def test_invalid_stock_code(baostock_connection):
    """Test error handling for invalid stock codes"""
    rs = bs.query_history_k_data_plus(
        "invalid.code",  # Invalid code
        "date,code,open,close",
        start_date=TEST_START_DATE,
        end_date=TEST_END_DATE,
        frequency="d"
    )

    # Invalid code should return error
    assert rs.error_code != '0', "Invalid stock code did not return error"
    print(f"Invalid stock code test passed, error message: {rs.error_msg}")


def test_invalid_date_range(baostock_connection):
    """Test error handling for invalid date ranges"""
    # Start date after end date
    rs = bs.query_history_k_data_plus(
        TEST_STOCK_CODE,
        "date,code,open,close",
        start_date=TEST_END_DATE,
        end_date=TEST_START_DATE,
        frequency="d"
    )

    assert rs.error_code != '0', "Invalid date range did not return error"
    print(f"Invalid date range test passed, error message: {rs.error_msg}")


def test_get_stock_basic_info(baostock_connection):
    """Test retrieval of basic stock information"""
    rs = bs.query_stock_basic(code=TEST_STOCK_CODE)

    assert rs.error_code == '0', f"Failed to get basic stock info: {rs.error_msg}"

    # Parse data
    data_list = []
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data())

    df = pd.DataFrame(data_list, columns=rs.fields)

    assert not df.empty, "Stock basic information is empty"
    assert df.iloc[0]['code'] == TEST_STOCK_CODE, "Stock code does not match"

    print(f"Stock basic info test passed, stock name: {df.iloc[0]['code_name']}")
