import logging
import datetime
import pytest

from gentrade.market_data.stock_us import StockUSMarket

LOG = logging.getLogger(__name__)

@pytest.mark.parametrize(
        "ticker, timeframe,limit",
        [
            ("MSFT", "1h", 10),
            ("MSFT", "1d", 100),
            ("MSFT", "1w", 20),
            ("MSFT", "1M", 10),
            ("AAPL", "1h", 10),
            ("TSLA", "1d", 100),
            ("AAPL", "1w", 20),
            ("NVDA", "1M", 10)
            ])
def test_fetch_ohlcv_msft(inst_stock_us:StockUSMarket, ticker, timeframe, limit):
    asset = inst_stock_us.get_asset(ticker)
    dt = datetime.datetime(2024, 5, 1, 13, 30)
    ret = asset.fetch_ohlcv(timeframe, since=dt.timestamp(), limit=limit)
    LOG.info(ret)

@pytest.mark.parametrize(
        "company_name",
        [
            'AAPL',
            'Apple',
            'Apple Inc',
        ])
def test_get_company_code(inst_stock_us:StockUSMarket, company_name:str):
    ret = inst_stock_us.search_ticker(company_name)
    LOG.info(ret)
    assert ret.name == 'aapl'

@pytest.mark.parametrize(
        "ticker_name",
        [
            'AAPL',
            'TSLA',
            'MSFT',
        ])
def test_get_company_name(inst_stock_us:StockUSMarket, ticker_name:str):
    ret = inst_stock_us.get_asset(ticker_name)
    LOG.info(ret)
    assert ret is not None or len(ret) != 0
