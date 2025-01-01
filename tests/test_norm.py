import logging
import datetime
import pandas as pd

from gentrade.market_data.crypto import BinanceMarket
from gentrade.market_data.timeframe import TimeFrame

LOG = logging.getLogger(__name__)

def check_delta_count(timeframe:str, limit:int, df:pd.DataFrame):
    tfobj = TimeFrame(timeframe)

    ts_to = tfobj.ts_last()
    ts_from = tfobj.ts_last_limit(limit)

    assert df.index[-1] == ts_to
    assert df.index[0] == ts_from

def test_fetch_ohlcv_btc(inst_binance:BinanceMarket):
    asset = inst_binance.get_asset("btc_usdt")

    since = datetime.datetime(2024, 11, 12, 4, 10, 12)
    to = datetime.datetime(2024, 11, 12, 4, 10, 15)
    ret = asset.fetch_ohlcv("1m", since=since.timestamp(), to=to.timestamp())
    assert len(ret) == 0

    since = datetime.datetime(2024, 11, 12, 4, 10, 12)
    to = datetime.datetime(2024, 11, 12, 14, 10, 15)
    ret = asset.fetch_ohlcv("1d", since=since.timestamp(), to=to.timestamp())
    assert len(ret) == 0

    since = datetime.datetime(2024, 11, 12, 4, 10, 12)
    to = datetime.datetime(2024, 11, 13, 14, 10, 15)
    ret = asset.fetch_ohlcv("1w", since=since.timestamp(), to=to.timestamp())
    assert len(ret) == 0

    since = datetime.datetime(2024, 11, 12, 4, 10, 12)
    to = datetime.datetime(2024, 11, 20, 14, 10, 15)
    ret = asset.fetch_ohlcv("1M", since=since.timestamp(), to=to.timestamp())
    assert len(ret) == 0
