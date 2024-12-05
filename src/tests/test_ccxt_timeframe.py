"""
Test CCXT library
"""
import time
import logging
import datetime
import pytest


LOG = logging.getLogger(__name__)

@pytest.mark.parametrize("tf_name,tf_delta",
                         [
                             ("1m", 60),
                             ("1h", 60 * 60),
                             ("1d", 24 * 60 * 60)
                        ])
def test_timeframe_limit(inst_ccxt_binance, tf_name, tf_delta):
    data = inst_ccxt_binance.fetch_ohlcv("BTC/USDT", tf_name, limit=10)
    LOG.info("ccxt retune[ 0] - %d: %s", data[0][0]/1000,
             datetime.datetime.fromtimestamp(data[0][0]/1000))
    LOG.info("ccxt retune[-1] - %d: %s", data[-1][0]/1000,
             datetime.datetime.fromtimestamp(data[-1][0]/1000))

    last_record_ts = int(int(data[-1][0]) / 1000)
    first_record_ts = int(int(data[0][0]) / 1000)

    last_now_ts = int(time.time() / tf_delta) * tf_delta
    first_now_ts = int(time.time() / tf_delta) * tf_delta - (10 - 1) * tf_delta

    LOG.info("first_now - %d: %s", first_now_ts,
             datetime.datetime.fromtimestamp(first_now_ts))
    LOG.info("last_now  - %d: %s", last_now_ts,
             datetime.datetime.fromtimestamp(last_now_ts))


    assert last_now_ts == last_record_ts
    assert first_now_ts == first_record_ts

def test_timeframe_week_limit(inst_ccxt_binance):
    limit = 3
    data = inst_ccxt_binance.fetch_ohlcv("BTC/USDT", "1w", limit=limit)
    LOG.info("ccxt retune[ 0] - %d: %s", data[0][0]/1000,
             datetime.datetime.fromtimestamp(data[0][0]/1000))
    LOG.info("ccxt retune[-1] - %d: %s", data[-1][0]/1000,
             datetime.datetime.fromtimestamp(data[-1][0]/1000))

    tf_delta = 7 * 24 * 3600
    last_record_ts = int(int(data[-1][0]) / 1000)
    first_record_ts = int(int(data[0][0]) / 1000)

    today = datetime.datetime.now()
    LOG.info(today.weekday())
    last_week = datetime.datetime(
        today.year, today.month, today.day - today.weekday())
    last_week_ts = last_week.replace(
        tzinfo=datetime.timezone.utc).timestamp()
    first_week_ts = last_week_ts - (limit - 1) * tf_delta

    LOG.info("first_now - %d: %s", first_week_ts,
             datetime.datetime.fromtimestamp(first_week_ts))
    LOG.info("last_now  - %d: %s", last_week_ts,
             datetime.datetime.fromtimestamp(last_week_ts))

    assert last_week_ts == last_record_ts
    assert first_week_ts == first_record_ts

def test_timeframe_month_limit(inst_ccxt_binance):
    limit = 3
    data = inst_ccxt_binance.fetch_ohlcv("BTC/USDT", "1M", limit=limit)
    LOG.info("ccxt retune[ 0] - %d: %s", data[0][0]/1000,
             datetime.datetime.fromtimestamp(data[0][0]/1000))
    LOG.info("ccxt retune[-1] - %d: %s", data[-1][0]/1000,
             datetime.datetime.fromtimestamp(data[-1][0]/1000))
    last_record_ts = int(int(data[-1][0]) / 1000)
    first_record_ts = int(int(data[0][0]) / 1000)

    today = datetime.datetime.now()
    last_month = today.month - limit
    last_month = datetime.datetime(today.year, today.month, 1)
    last_month_ts = last_month.replace(
        tzinfo=datetime.timezone.utc).timestamp()

    first_month_index = last_month.month - (limit - 1)
    first_year_index = last_month.year
    if first_month_index < 0:
        first_month_index += 12
        first_year_index -= 1
    first_month = datetime.datetime(first_year_index, first_month_index, 1)
    first_month_ts = first_month.replace(
        tzinfo=datetime.timezone.utc).timestamp()

    LOG.info("first_now - %d: %s", first_month_ts,
             datetime.datetime.fromtimestamp(first_month_ts))
    LOG.info("last_now  - %d: %s", last_month_ts,
             datetime.datetime.fromtimestamp(last_month_ts))
    assert first_month_ts == first_record_ts
    assert last_month_ts == last_record_ts
