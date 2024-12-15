import time
import logging
import pytest
import pandas as pd

from gentrade.market_data.stock_us import StockUSMarket
from gentrade.market_data.timeframe import TimeFrame

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
            ("1w", 20),
            ("1M", 10)
            ])
def test_fetch_ohlcv_msft(inst_stock_us:StockUSMarket, timeframe, limit):
    asset = inst_stock_us.get_asset("MSFT")
    ret = asset.fetch_ohlcv(timeframe, limit=limit)
    LOG.info(ret)
    check_delta_count(timeframe, limit, ret)
