"""
DataHub Core Package
"""
import os
import logging
import time
from abc import ABC, abstractmethod
import uuid
import pandas as pd

LOG = logging.getLogger(__name__)

# The detle of TIME FRAME in seconds
TIME_FRAME = {
    '1m':                60,
    '15m':          15 * 60,
    '1h':       1 * 60 * 60,
    '4h':       4 * 60 * 60,
    '1d':      24 * 60 * 60,
    '1W':  7 * 24 * 60 * 60,
    '1M': 30 * 24 * 60 * 60
}

class FinancialMarket(ABC):
    # Forward Declaration
    pass

class FinancialAssetCache:
    # Forward Declaration
    pass

class FinancialAsset(ABC):
    """
    Trading instruments are all the different types of assets and contracts that
    can be traded. Trading instruments are classified into various categories,
    some more popular than others.
    """

    def __init__(self, name:str, market:FinancialMarket):
        self._name:str = name
        self._market:FinancialMarket = market
        self._cache:FinancialAssetCache = FinancialAssetCache(self)

    @property
    def name(self) -> str:
        """
        Property name
        """
        return self._name

    @property
    def market(self) -> FinancialMarket:
        """
        Property market which belong to
        """
        return self._market

    def fetch_ohlcv(self, timeframe:str="1h", since: int = -1,
                    limit: int = 100) -> pd.DataFrame:
        """
        Fetch the specific asset
        """
        # correct limit to ensure correct range according to since
        if since != -1:
            max_limit = int((time.time() - since) / TIME_FRAME[timeframe])
            limit = min(limit, max_limit)

        if timeframe not in TIME_FRAME:
            LOG.error("Time frame %s is invalid", timeframe)
            return None

        tf_delta = TIME_FRAME[timeframe]

        # calculate the range from_ -> to_
        if since == -1:
            to_ = int(time.time() / tf_delta - 1) * tf_delta
            from_ = to_ - (limit - 1) * tf_delta
        else:
            from_ = int(since / tf_delta) * tf_delta
            to_ = since + (limit - 1) * tf_delta

        # search from cache first
        df_cached = self._cache.search(timeframe, from_, to_)
        if df_cached is None:
            df = self._market.fetch_ohlcv(self, timeframe, since, limit)
            self._cache.save(timeframe, df)
        else:
            if df_cached.index[-1] == to_:
                # Find all data
                df = df_cached
            else:
                # Find part data, continue fetch remaining from market
                new_limit = limit - int((to_ - df_cached.index[-1]) / tf_delta)
                new_since = df_cached.index[-1]
                df_remaining = self._market.fetch_ohlcv(
                    self, timeframe, new_since, new_limit)
                df = pd.concat([df_cached, df_remaining]).drop_duplicates()
                df.sort_index(inplace=True)
                self._cache.save(timeframe, df_remaining)
        return df

    def ohlvc_to_datetime(self, df:pd.DataFrame):
        df.index = pd.to_datetime(df.index, unit="ms")
        return df

class FinancialMarket(ABC):

    MARKET_CRYPTO = 'crypto'
    MARKET_STOCK = 'stock'

    """
    Trading market includes crypto, stock or golden.
    """

    def __init__(self, name:str, market_type:str, market_id:str=None,
                 cache_dir:str=None):
        assert market_type in \
            [FinancialMarket.MARKET_CRYPTO, FinancialMarket.MARKET_STOCK]
        if market_id is None:
            self._market_id = str(uuid.uuid4())
        else:
            self._market_id = market_id
        self._name = name
        self._assets:dict[str, FinancialAsset] = {}
        self._cache_dir = cache_dir
        self._market_type = market_type


    @property
    def name(self) -> str:
        """
        Property: name
        """
        return self._name

    @property
    def assets(self) -> dict[str, FinancialAsset]:
        """
        Property: assets
        """
        return self._assets

    @property
    def cache_dir(self) -> str:
        """
        Property: cache_dir
        """
        return self._cache_dir

    @property
    def market_type(self) -> str:
        return self._market_type

    @property
    def market_id(self) -> str:
        return self._market_id

    def get_asset(self, name) -> FinancialAsset:
        """
        Get instrument object from its name
        """
        if name in self._assets:
            return self._assets[name]
        return None

    @abstractmethod
    def init(self):
        """
        Financial Market initialization
        """
        raise NotImplementedError

    @abstractmethod
    def fetch_ohlcv(self, asset:FinancialAsset, timeframe:str, since: int = None,
                    limit: int = None):
        """
        Fetch OHLV for the specific asset
        """
        raise NotImplementedError

class FinancialAssetCache:

    def __init__(self, asset:FinancialAsset):
        self._asset = asset
        self._mem_cache:dict[str, pd.DataFrame] = {}
        self._save_in_progress = False
        self._init()

    def _init(self):
        cache_dir = self._asset.market.cache_dir
        if cache_dir is None or not os.path.exists(cache_dir):
            return

        for timeframe in TIME_FRAME:
            csv_name = self._get_csv_name(timeframe)
            csv_path = os.path.join(cache_dir, csv_name)
            if os.path.exists(csv_path):
                print("found: " + csv_path)
                try:
                    self._mem_cache[timeframe] = \
                        pd.read_csv(csv_path, index_col=0)
                    print(self._mem_cache[timeframe])
                except pd.errors.EmptyDataError:
                    pass

    def search(self, timeframe:str, since:int, to:int):
        """
        Search from cache
        """
        if timeframe not in self._mem_cache:
            self._mem_cache[timeframe] = pd.DataFrame()
            return None

        if since < self._mem_cache[timeframe].index[0] or \
            since > self._mem_cache[timeframe].index[-1]:
            LOG.info("Not found records from cache")
            return None

        # if from_ in the range of existing cache
        if to <= self._mem_cache[timeframe].index[-1]:
            LOG.info("Found all records from cache")
            df_part = self._mem_cache[timeframe].loc[since:to]
        else:
            LOG.info("Found part of records from cache")
            df_part = self._mem_cache[timeframe].loc[since:]

        if self._check_whether_continuous(df_part, timeframe):
            return df_part
        return None

    def _check_whether_continuous(self, df:pd.DataFrame, timeframe):
        """
        Check whether the dataframe is continuous
        """
        count = int((df.index[-1] - df.index[0]) / TIME_FRAME[timeframe]) \
            + 1
        if count != len(df):
            LOG.error("The data frame is not continuous: count=%d, len=%d",
                      count, len(df))
            return False
        return True

    def save(self, timeframe:str, df_new:pd.DataFrame):
        """
        Save OHLCV to cache
        """
        self._mem_cache[timeframe] = pd.concat(
            [self._mem_cache[timeframe], df_new]).drop_duplicates()
        self._mem_cache[timeframe].sort_index(inplace=True)
        self._save_cache_to_file(timeframe)

    def _get_csv_name(self, timeframe):
        return self._asset.name + "-" + timeframe + ".csv"

    def _save_cache_to_file(self, timeframe):
        self._save_in_progress = True
        cache_dir = self._asset.market.cache_dir
        if cache_dir is not None:
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
            fname = os.path.join(self._asset.market.cache_dir,
                                self._get_csv_name(timeframe))
            self._mem_cache[timeframe].to_csv(fname)
        self._save_in_progress = False
