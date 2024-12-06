import time
import logging
import pytest
import pandas as pd

from tia.market_data.crypto import BinanceMarket
from tia.market_data.timeframe import TimeFrame

LOG = logging.getLogger(__name__)

def check_delta_count(timeframe:str, limit:int, df:pd.DataFrame):
    tfobj = TimeFrame(timeframe)

    ts_to = tfobj.ts_last()
    ts_from = tfobj.ts_last_limit(limit)

    assert df.index[-1] == ts_to
    assert df.index[0] == ts_from

@pytest.mark.parametrize(
        "timeframe,limit",
        [
            ("1m", 10),
            ("1h", 10),
            ("1d", 100),
            ("4h", 30),
            ("15m", 10),
            ("1w", 20),
            ("1M", 10)
            ])
def test_fetch_ohlcv_btc(inst_binance:BinanceMarket, timeframe, limit):
    asset = inst_binance.get_asset("btc_usdt")
    ret = asset.fetch_ohlcv(timeframe, limit=limit)
    LOG.info(ret)
    check_delta_count(timeframe, limit, ret)

@pytest.mark.parametrize(
        "timeframe,limit",
        [
            ("1m", 10),
            ("1h", 10),
            ("1d", 100),
            ("4h", 30),
            ("15m", 10),
            ("1M", 10)
        ])
def test_fetch_ohlcv_eth(inst_binance:BinanceMarket, timeframe, limit):
    asset = inst_binance.get_asset("eth_usdt")
    ret = asset.fetch_ohlcv(timeframe, limit=limit)
    LOG.info(ret)
    check_delta_count(timeframe, limit, ret)

def test_market_time(inst_binance:BinanceMarket):
    LOG.debug(inst_binance.seconds())
    LOG.debug(time.time())
    assert abs(inst_binance.seconds() - time.time()) < 10
