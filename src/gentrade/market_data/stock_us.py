import os
import logging
import time
import datetime
import ssl
import json
import requests
import yfinance as yf
import pandas as pd

from .core import FinancialAsset, FinancialMarket

LOG = logging.getLogger(__name__)

STOCK_US_MARKET_ID = "5784f1f5-d8f6-401d-8d24-f685a3812f2d"

class StockUSMarket(FinancialMarket):
    pass

class StockUSAsset(FinancialAsset):

    TYPE_STOCK  = "stock"
    TYPE_ETF    = "etf"
    TYPE_FUTURE = "future"

    def __init__(self, ticker_name:str, market:StockUSMarket,
                 ticker_type=TYPE_STOCK, ticker_cik:int=-1,
                 ticker_title:str=None):
        """
        Constructor

        :param ticker_name  : the name of ticker
        :param market       : the market instance
        :param ticker_type  : the type in stock, etf, future
        :param ticker_cik   : the Central Index Key (CIK)
        """
        super().__init__(ticker_name, market)
        self._ticker_type = ticker_type
        self._ticker_cik = ticker_cik
        self._ticker_title = ticker_title

    @property
    def ticker_type(self):
        return self._ticker_type

    @property
    def ticker_cik(self):
        return self._ticker_cik

    @property
    def ticker_title(self):
        return self._ticker_title

class StockUSMarket(FinancialMarket):

    TICKER_LIST_FILE = "stock_us_ticker.json"

    """
    US Stock Market by using Yahoo Financial API
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
        self._tickers = None

    def milliseconds(self) -> int:
        return round(time.time() * 1000)

    def init(self):
        """
        Initiate the market instance.

        :return: success or not
        """
        if self._ready:
            return False

        ticker_list_path = os.path.join(self.cache_dir, self.TICKER_LIST_FILE)
        if not os.path.exists(ticker_list_path):
            url = "https://www.sec.gov/files/company_tickers.json"
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

            try:
                response = requests.get(url=url,
                                        headers={'User-Agent': user_agent},
                                        timeout=10)
            except requests.exceptions.Timeout:
                LOG.error("request timeout")
                return False

            response.raise_for_status()
            data = response.json()

            # pylint: disable=unspecified-encoding
            with open(ticker_list_path, 'w') as out_file:
                json.dump(data, out_file, sort_keys = True, indent = 4,
                        ensure_ascii = False)

        # pylint: disable=unspecified-encoding
        with open(ticker_list_path, 'r') as input_file:
            ticker_data = json.load(input_file)
            for item in ticker_data.items():
                sa_obj = StockUSAsset(
                    item[1]['ticker'].lower(), self,
                    ticker_cik=item[1]['cik_str'],
                    ticker_title=item[1]['title']
                    )
                self.assets[item[1]['ticker'].lower()] = sa_obj

        LOG.info("Found %d assets for US stock market", len(self.assets))

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

    def _split_ranges(self, since, to, interval):
        ranges = []
        if to == -1:
            to = time.time()
        index = since
        while index + interval < to:
            ranges.append((index, index + interval))
            index += interval
        ranges.append((index, to))
        LOG.info(ranges)
        return ranges

    def _is_valid_range(self, timeframe, since, to):
        if timeframe == '1m':
            return (to - since) < 8 * 24 * 3600
        if timeframe == '1h':
            return (to - since) < 300 * 24 * 3600
        return True

    def fetch_ohlcv(self, asset:StockUSAsset, timeframe: str, since: int, to: int=-1):
        """
        Fetch OHLCV (Open High Low Close Volume).

        :param     asset: the specific asset
        :param timeframe: 1m/1h/1W/1M etc
        :param     since: the timestamp for starting point
        :param     limit: count
        """
        LOG.info("$$ Fetch from market: timeframe=%s since=%d, to=%d",
                 timeframe, since, to)

        if not self._is_valid_range(timeframe, since, to):
            LOG.error("invalid range")
            return None

        ohlcv = pd.DataFrame()
        try:
            if to != -1:
                ohlcv = yf.download(
                    asset.name,
                    group_by="Ticker",
                    start=datetime.datetime.fromtimestamp(since, tz=datetime.UTC),
                    end=datetime.datetime.fromtimestamp(to, tz=datetime.UTC),
                    interval=self._to_interval(timeframe))
            else:
                ohlcv = yf.download(
                    asset.name,
                    group_by="Ticker",
                    start=datetime.datetime.fromtimestamp(since, tz=datetime.UTC),
                    interval=self._to_interval(timeframe))
            if ohlcv is None or len(ohlcv) == 0:
                return None
        except yf.exceptions.YFPricesMissingError:
            LOG.error("No data for date %s",
                        datetime.datetime.fromtimestamp(since))
            return None
        except ssl.SSLEOFError:
            time.sleep(1)
        except requests.exceptions.SSLError:
            time.sleep(1)

        ohlcv = ohlcv.stack(level=0).rename_axis(
            ['time', 'Ticker']).reset_index(level=1)
        ohlcv = ohlcv[["Open", "High", "Low", "Close", "Volume"]]
        ohlcv.index = pd.to_datetime(ohlcv.index)
        ohlcv.index = ohlcv.index.astype('int64')
        ohlcv.index = ohlcv.index.to_series().div(10**9).astype('int64')
        ohlcv.rename(columns={
            "Open":"open", "High":"high", "Low":"low",
            "Close":"close", "Volume":"vol"}, inplace=True)
        return ohlcv

    def search_ticker(self, company_name:str) -> str:
        """
        Search ticker according to company's name
        """
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        params = {"q": company_name, "quotes_count": 1,
                  "country": "United States"}

        try:
            res = requests.get(url=url, params=params,
                            headers={'User-Agent': user_agent},
                            timeout=10)
        except requests.exceptions.Timeout:
            LOG.error("request timeout")
            return None

        data = res.json()

        if 'quotes' not in data or len(data['quotes']) == 0:
            return None

        search_ticker = data['quotes'][0]['symbol']
        asset = self.get_asset(search_ticker)
        if asset is None:
            LOG.error("Could not find the searching ticker %s", search_ticker)
            return None
        return asset
