import time
import logging
import pytest
import pandas as pd

from tia.market_data.core import TIME_FRAME
from tia.market_data.crypto import BinanceMarket

LOG = logging.getLogger(__name__)

def check_delta_count(timeframe:str, limit:int, df:pd.DataFrame, since=-1):
    tf_delta = TIME_FRAME[timeframe]
    now_index = int(time.time() / tf_delta) - 1
    if since == -1:
        assert df.index[-1] == now_index * tf_delta
        assert df.index[0] == (now_index - limit + 1) * tf_delta

@pytest.mark.parametrize("timeframe", ["1m", "1h", "1d", "4h", "15m"])
def test_fetch_ohlcv_btc(inst_binance:BinanceMarket, timeframe):
    asset = inst_binance.get_asset("btc_usdt")
    ret = asset.fetch_ohlcv(timeframe, limit=10)
    LOG.info(ret)
    check_delta_count(timeframe, 10, ret)


@pytest.mark.parametrize("timeframe", ["1m", "1h", "1d", "4h", "15m"])
def test_fetch_ohlcv_eth(inst_binance:BinanceMarket, timeframe):
    asset = inst_binance.get_asset("eth_usdt")
    ret = asset.fetch_ohlcv(timeframe, limit=10)
    LOG.info(ret)
    check_delta_count(timeframe, 10, ret)

def test_market_time(inst_binance:BinanceMarket):
    LOG.debug(inst_binance.seconds())
    LOG.debug(time.time())
    assert abs(inst_binance.seconds() - time.time()) < 10
