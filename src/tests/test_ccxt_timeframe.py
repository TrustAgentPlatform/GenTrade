"""
Test CCXT library
"""
import time
import logging
import datetime
import pytest

from tia.market_data.timeframe import TimeFrame

# pylint: disable=unused-argument

LOG = logging.getLogger(__name__)

@pytest.mark.parametrize("tf_name",
                         [ "1m", "15m", "30m", "1h", "4h",
                           "8h", "1d", "1w", "1M" ])
def test_timeframe_limit(inst_ccxt_binance, tf_name):
    tfobj = TimeFrame(tf_name)
    limit = 40
    data = inst_ccxt_binance.fetch_ohlcv("BTC/USDT", tf_name, limit=limit)
    LOG.info("ccxt retune[ 0] - %d: %s", data[0][0]/1000,
             datetime.datetime.fromtimestamp(data[0][0]/1000))
    LOG.info("ccxt retune[-1] - %d: %s", data[-1][0]/1000,
             datetime.datetime.fromtimestamp(data[-1][0]/1000))

    last_record_ts = int(int(data[-1][0]) / 1000)
    first_record_ts = int(int(data[0][0]) / 1000)

    last_now_ts = tfobj.ts_last(time.time())
    first_now_ts = tfobj.ts_last_limit(limit, time.time())

    LOG.info("first_now - %d: %s", first_now_ts,
             datetime.datetime.fromtimestamp(first_now_ts))
    LOG.info("last_now  - %d: %s", last_now_ts,
             datetime.datetime.fromtimestamp(last_now_ts))

    assert last_now_ts == last_record_ts
    assert first_now_ts == first_record_ts

@pytest.mark.parametrize("tf_name",
                         [ "1m", "15m", "30m", "1h", "4h",
                           "8h", "1d", "1w", "1M" ])
def test_timeframe_since(inst_ccxt_binance, tf_name):
    tfobj = TimeFrame(tf_name)
    limit = 40
    since_ts = int(datetime.datetime(2023, 12, 4, 13, 30, 0).timestamp())
    LOG.info(since_ts)
    data = inst_ccxt_binance.fetch_ohlcv("BTC/USDT", tf_name,
                                         since=since_ts * 1000, limit=limit)
    LOG.info("ccxt retune[ 0] - %d: %s", data[0][0]/1000,
             datetime.datetime.fromtimestamp(data[0][0]/1000))
    LOG.info("ccxt retune[-1] - %d: %s", data[-1][0]/1000,
             datetime.datetime.fromtimestamp(data[-1][0]/1000))

    last_record_ts = int(int(data[-1][0]) / 1000)
    first_record_ts = int(int(data[0][0]) / 1000)

    next_first_ts = tfobj.ts_since(since_ts)
    next_last_ts = tfobj.ts_since_limit(since_ts, limit)


    LOG.info("since_next - %d: %s", next_first_ts,
              datetime.datetime.fromtimestamp(next_first_ts))
    LOG.info("last_now  - %d: %s", next_last_ts,
              datetime.datetime.fromtimestamp(next_last_ts))
    LOG.info("limit:%d Real count%d", limit,
             tfobj.calculate_count(since_ts, limit))

    assert first_record_ts == next_first_ts
    assert next_last_ts == last_record_ts
