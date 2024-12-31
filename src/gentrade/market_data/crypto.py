import os
import logging
import time
import json
import ccxt
import pandas as pd
import numpy as np

from .core import FinancialAsset, FinancialMarket
from .timeframe import TimeFrame

LOG = logging.getLogger(__name__)

BINANCE_MARKET_ID = "b13a4902-ad9d-11ef-a239-00155d3ba217"

class CryptoMarket(FinancialMarket):

    def __init__(self, name: str, market_id:str=None, cache_dir:str=None):
        super().__init__(name, FinancialMarket.MARKET_CRYPTO, market_id,
                         cache_dir)

    def get_crypto_asset(self, base, quote):
        """
        Return asset according to crypt naming rule "base/quote"
        """
        return self.get_asset("%s_%s" % (base.lower(), quote.lower()))

class CryptoAsset(FinancialAsset):

    _CRYPTO_TYPE_SPOT = "spot"
    _CRYPTO_TYPE_SWAP = "swap"
    _CRYPTO_TYPE_FUTURE = "future"

    _CRYPTO_TYPES = [ _CRYPTO_TYPE_SPOT, _CRYPTO_TYPE_SWAP, _CRYPTO_TYPE_FUTURE]

    def __init__(self, base:str, quote:str,
                 symbol:str, crypto_type:str, market:CryptoMarket):
        self._base = base.lower()
        self._quote = quote.lower()
        assert crypto_type in self._CRYPTO_TYPES
        self._crypto_type = crypto_type
        self._symbol = symbol
        super().__init__("%s_%s" %(base.lower(),
                                   quote.lower()), market)

    @property
    def base(self) -> str:
        return self._base

    @property
    def quote(self) -> str:
        return self._quote

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def crypto_type(self) -> str:
        return self._crypto_type

    @property
    def asset_type(self):
        return self.crypto_type

    def to_dict(self) -> dict:
        retval = super().to_dict()
        retval['base'] = self.base
        retval['symbol'] = self._symbol
        return retval

    def fetch_ohlcv(self, timeframe:str = '1d', since: int = -1, to: int = -1,
                    limit=-1) -> pd.DataFrame:
        """Fetch the OHLCV

        Args:
            timeframe (str, optional): Defaults to '1d'.
            since (int): the start of UTC timestamp.
            to (int, optional): Defaults to -1 for now
            limit (int, optional): the max count of returned value
        """
        df = FinancialAsset.fetch_ohlcv(self, timeframe, since, to, limit)
        LOG.info("Double check whether the dataframe is valid")

        if df is None or len(df) == 0 or \
            not self._cache.check_cache(timeframe, df.index[0], df.index[-1]):
            tfobj = TimeFrame(timeframe)
            (since_new, to_new) = tfobj.normalize(since, to, limit)
            df = self._market.fetch_ohlcv(
                                 self, timeframe, since_new,
                                 to_new)
            self._cache.save(timeframe, df)

        return df

class BinanceMarket(CryptoMarket):

    """
    Binance Market Class to provide crypto information via Binance API.
    Please set the environment variable BINANCE_API_SECRET and BINANCE_API_SECRET.
    """

    _ASSETS_LIST_PATH = "crypto_assets.json"

    def __init__(self, cache_dir:str=None):
        """
        :param cache_dir: the root directory for the cache.
        """
        if cache_dir is None:
            cache_dir = os.path.join(os.path.dirname(__file__), "../../cache")
        cache_dir = os.path.join(cache_dir, "Binance")
        super().__init__("Binance", BINANCE_MARKET_ID, cache_dir)
        assert self.api_key is not None, \
            "Please specify the Binance's API key via the environment" \
            "variable BINANCE_API_KEY"
        assert self.api_secret is not None, \
            "Please specify the Binance's API Secret via the environment" \
            "variable BINANCE_API_SECRET"

        params = {'apiKey': self.api_key, 'secret': self.api_secret}
        if 'HTTP_PROXY' in os.environ:
            params['proxies'] = {
                    'http': os.environ['HTTP_PROXY'],
                    'https': os.environ['HTTP_PROXY']
                    }

        self._ccxt_inst = ccxt.binance(params)
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

        LOG.info("Loading Crypto Market...")

        asset_list_path = os.path.join(self.cache_dir, self._ASSETS_LIST_PATH)
        if not os.path.exists(asset_list_path):
            LOG.info("Not found the asset list file, use Binance API")
            retry_num = 0
            success = False
            while retry_num < 5:
                retry_num += 1
                try:
                    self._ccxt_inst.load_markets()
                except (ccxt.RequestTimeout, ccxt.NetworkError):
                    LOG.critical("Request Timeout... retry[%d/5]", retry_num)
                    time.sleep(5)
                except Exception as e:
                    LOG.critical(e, exc_info=True)
                    LOG.error("Fail to load market... retry[%d/5]", retry_num)
                    time.sleep(5)
                else:
                    success = True
                    break

            if not success:
                return False

            all_assets = {}
            for symbol in self._ccxt_inst.symbols:
                info = self._ccxt_inst.market(symbol)
                base, quote = symbol.split("/")
                caobj = CryptoAsset(base, quote, symbol, info['type'], self)
                self.assets[caobj.name] = caobj
                all_assets[caobj.name] = caobj.to_dict()

            with open(asset_list_path, 'w', encoding='utf-8') as output:
                json.dump(all_assets, output, sort_keys = True, indent = 4,
                        ensure_ascii = False)
        else:
            LOG.info("Found the asset list file %s", asset_list_path)
            with open(asset_list_path, 'r', encoding='utf-8') as input_file:
                assets_data = json.load(input_file)
                for item in assets_data.items():
                    caobj = CryptoAsset(
                        item[1]['base'],
                        item[1]['quote'],
                        item[1]['symbol'],
                        item[1]['type'],
                        self)
                    self.assets[item[0]] = caobj
        LOG.info("Found %d crypto assets.", len(self.assets))

        self._ready = True
        return True

    def fetch_ohlcv(self, asset:CryptoAsset, timeframe: str, since: int, to:int ):
        """
        Fetch OHLCV (Open High Low Close Volume).

        :param     asset: the specific asset
        :param timeframe: 1m/1h/1W/1M etc
        :param     since: the timestamp for starting point
        :param     limit: count
        """
        LOG.info("$$ Fetch from market: timeframe=%s since=%d, to=%d",
                 timeframe, since, to)

        all_ohlcv = []

        tfobj = TimeFrame(timeframe)
        limit = tfobj.calculate_count(since, to=to)

        remaining = limit
        index = int(since * 1000)
        # Continuous to fetching until get all data
        while remaining > 0:
            LOG.info("since=%d remaining=%d", index, remaining)
            try:
                ohlcv = self._ccxt_inst.fetch_ohlcv(asset.symbol, timeframe,
                                                    index, remaining)
            except TimeoutError:
                LOG.critical("Network Timeout")
                time.sleep(1)
                continue
            all_ohlcv += ohlcv
            remaining = remaining - len(ohlcv)
            index = ohlcv[-1][0]
            time.sleep(1)

        df = pd.DataFrame(all_ohlcv, columns =
                          ['time', 'open', 'high', 'low', 'close', 'vol'])
        df.time = (df.time / 1000).astype(np.int64)
        df.set_index('time', inplace=True)
        return df

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cm = BinanceMarket(cache_dir="./binance/")
    cm.init()
    asset_btcusdt = cm.get_crypto_asset("ETH", "USDT")
    while True:
        ret = asset_btcusdt.fetch_ohlcv("1h", limit=3)
        print(ret)
        time.sleep(30)
