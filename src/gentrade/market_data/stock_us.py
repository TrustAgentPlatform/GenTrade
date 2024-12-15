import os
import logging
import time
import datetime
import ssl
import requests
import yfinance as yf
import pandas as pd

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
        return round(time.time() * 1000)

    def init(self):
        """
        Initiate the market instance.

        :return: success or not
        """
        if self._ready:
            return False

        for ticket_name in ["MSFT", "AAPL", "TSLA"]:
            caobj = StockUSAsset(ticket_name.lower(), self)
            self.assets[caobj.name] = caobj

        self._ready = True
        return True

    def _to_interval(self, timeframe):
        if timeframe in ["1h", "1m", "1d"]:
            return timeframe

        if timeframe == "1M":
            return "1mo"

        if timeframe == "1w":
            return "1wk"

        return None

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

        tfobj = TimeFrame(timeframe)

        # calculate the range from_ -> to_
        if since == -1:
            since = tfobj.ts_last_limit(limit)
        else:
            # Calibrate the limit value according to the duration between
            # since and now
            limit = tfobj.calculate_count(since, limit)

        download_ok = False
        while not download_ok:
            try:
                ohlcv = yf.download(
                    asset.name,
                    group_by="Ticker",
                    start=datetime.datetime.fromtimestamp(since),
                    interval=self._to_interval(timeframe))
                download_ok = True
            except yf.exceptions.YFPricesMissingError:
                LOG.error("No data for date %s",
                            datetime.datetime.fromtimestamp(since))
                return None
            except ssl.SSLEOFError:
                time.sleep(1)
            except requests.exceptions.SSLError:
                time.sleep(1)
        ohlcv = ohlcv.stack(level=0).rename_axis(['time', 'Ticker']).reset_index(level=1)
        ohlcv = ohlcv[["Open", "High", "Low", "Close", "Volume"]]
        ohlcv.index = pd.to_datetime(ohlcv.index)
        ohlcv.index = ohlcv.index.astype('int64')
        ohlcv.index = ohlcv.index.to_series().div(10**9).astype('int64')
        ohlcv.rename(columns={
            "Open":"open", "High":"high", "Low":"low",
            "Close":"close", "Volume":"vol"}, inplace=True)
        LOG.info(ohlcv)
        return ohlcv
