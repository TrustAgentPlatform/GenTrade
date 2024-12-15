import os
import logging
import time
import datetime
import yfinance as yf
import pandas as pd
import numpy as np
from .core import FinancialAsset, FinancialMarket
from .timeframe import TimeFrame

LOG = logging.getLogger(__name__)

STOCK_US_MARKET_ID = "5784f1f5-d8f6-401d-8d24-f685a3812f2d"

class StockUSMarket(FinancialMarket):
    pass

class StockUSAsset(FinancialAsset):

    TYPE_STOCK  = "stock"
    TYPE_ETF    = "etf"
    TYPE_FUTURE = "future"

    def __init__(self, ticker_name:str, market:StockUSMarket, tiker_type=TYPE_STOCK):
        super().__init__(ticker_name, market)
        self._ticker_type = tiker_type

    @property
    def ticket_type(self):
        return self._ticker_type


class StockUSMarket(FinancialMarket):

    """
    Binance Market Class to provide crypto information via Binance API.

    Please set the environment variable BINANCE_API_SECRET and BINANCE_API_SECRET.

    """
    def __init__(self, cache_dir:str=None):
        """
        :param cache_dir: the root directory for the cache.
        """
        if cache_dir is None:
            cache_dir = os.path.join(os.path.dirname(__file__), "../../cache")
        cache_dir = os.path.join(cache_dir, "StockUS")
        super().__init__("StockUS", "stock", STOCK_US_MARKET_ID, cache_dir)
        self._ready = False

    @property
    def api_key(self):
        return os.getenv("BINANCE_API_KEY")

    @property
    def api_secret(self):
        return os.getenv("BINANCE_API_SECRET")

    def milliseconds(self) -> int:
        return self._ccxt_inst.milliseconds()

    def init(self):
        """
        Initiate the market instance.

        :return: success or not
        """
        if self._ready:
            return False

        for ticket_name in ["MSFT", "AAPL", "TELA"]:
            caobj = StockUSAsset(ticket_name, self)
            self.assets[caobj.name] = caobj

        self._ready = True
        return True

    def _to_interval(self, timeframe):
        if timeframe in ["1h", "1m", "1d"]:
            return timeframe

        if timeframe == "1mo":
            return "1M"

        if timeframe == "1wk":
            return "1w"

    def fetch_ohlcv(self, asset:StockUSAsset, timeframe: str, since: int = -1,
                    limit: int = 500):
        """
        Fetch OHLCV (Open High Low Close Volume).

        :param     asset: the specific asset
        :param timeframe: 1m/1h/1W/1M etc
        :param     since: the timestamp for starting point
        :param     limit: count
        """
        LOG.info("$$ Fetch from market: timeframe=%s since=%d, limit=%d",
                 timeframe, since, limit)
        remaining = limit
        all_ohlcv = []

        tfobj = TimeFrame(timeframe)

        # calculate the range from_ -> to_
        if since == -1:
            since = tfobj.ts_last_limit(limit)
        else:
            # Calibrate the limit value according to the duration between
            # since and now
            limit = tfobj.calculate_count(since, limit)

        # Continuous to fetching until get all data
        while remaining > 0:
            #ohlcv = self._ccxt_inst.fetch_ohlcv(asset.symbol, timeframe,
            #                                    int(since * 1000), limit)

            ohlcv = yf.download(
                asset.name,
                start=datetime.datetime.fromtimestamp(since),
                interval=self._to_interval(timeframe))
            LOG.info(ohlcv)
            all_ohlcv += ohlcv
            remaining = remaining - len(ohlcv)
            count = tfobj.calculate_count(since, limit)
            if count == 1:
                break
            since = tfobj.ts_since_limit(since, limit)

            LOG.info("len=%d, remaining=%d, since=%d count=%d",
                     len(ohlcv), remaining, since, count)
            time.sleep(0.1)

        df = pd.DataFrame(all_ohlcv, columns =
                          ['time', 'open', 'high', 'low', 'close', 'vol'])
        df.time = (df.time / 1000).astype(np.int64)
        df.set_index('time', inplace=True)
        return df

