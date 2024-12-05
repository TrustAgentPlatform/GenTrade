"""
DataHub Core Package
"""
import os
import logging
import time
import datetime
from abc import ABC, abstractmethod
from threading import Thread
import uuid
import pandas as pd

LOG = logging.getLogger(__name__)

# The delta of TIME FRAME in seconds
TIME_FRAME = {
    '1m':                60,
    '15m':          15 * 60,
    '1h':       1 * 60 * 60,
    '4h':       4 * 60 * 60,
    '1d':      24 * 60 * 60,
    '1w':  7 * 24 * 60 * 60,
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
    @property
    def cache(self) -> FinancialAssetCache:
        return self._cache

    def fetch_ohlcv(self, timeframe:str="1h", since: int = -1,
                    limit: int = 100) -> pd.DataFrame:
        """
        Fetch the specific asset
        """
        # correct limit to ensure correct range according to since
        if since != -1:
            max_limit = int((time.time() - since) / TIME_FRAME[timeframe])
            assert max_limit > 0
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

        LOG.info("fetch_ohlcv: timeframe=%s, since=%d, limit=%d, to=%d",
                 timeframe, since, limit, to_)

        # search from cache first
        df_cached = self._cache.search(timeframe, from_, to_)
        if df_cached is None:
            df = self._market.fetch_ohlcv(self, timeframe, since, limit)
            self._cache.save(timeframe, df)
        else:
            LOG.info("cache: count=%d, index=%d, to=%d",
                     len(df_cached), df_cached.index[-1], to_)
            if df_cached.index[-1] == to_:
                # Find all data
                df = df_cached
            else:
                # Find part data, continue fetch remaining from market
                new_limit = int((to_ - df_cached.index[-1]) / tf_delta)
                new_since = df_cached.index[-1] + 1
                df_remaining = self._market.fetch_ohlcv(
                    self, timeframe, new_since, new_limit)
                df = pd.concat([df_cached, df_remaining])
                df = df[~df.index.duplicated(keep='first')]
                df.sort_index(inplace=True)
                self._cache.save(timeframe, df_remaining)
        return df

    def index_to_datetime(self, df:pd.DataFrame, unit="s"):
        df.index = pd.to_datetime(df.index, unit=unit)
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
        Property: Cache Directory
        """
        return self._cache_dir

    @property
    def market_type(self) -> str:
        """
        Property: Market Type
        """
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
    def fetch_ohlcv(self, asset:FinancialAsset, timeframe:str,
                    since: int = None, limit: int = None):
        """
        Fetch OHLCV for the specific asset
        """
        raise NotImplementedError

    @abstractmethod
    def milliseconds(self) -> int:
        """
        Current timestamp in milliseconds
        """
        raise NotImplementedError

    def seconds(self) -> int:
        """
        Current timestamp in seconds
        """
        return int(self.milliseconds() / 1000)

class FinancialAssetCache:

    def __init__(self, asset:FinancialAsset):
        self._asset = asset
        self._mem_cache:dict[str, pd.DataFrame] = {}
        self._save_in_progress = False
        self._init()

    def get_index(self, timeframe:str):
        if timeframe not in self._mem_cache:
            return -1, -1
        cache_obj = self._mem_cache[timeframe]
        return cache_obj.index[0], cache_obj.index[-1]

    def _init(self):
        cache_dir = self._asset.market.cache_dir
        if cache_dir is None or not os.path.exists(cache_dir):
            return

        for timeframe in TIME_FRAME:
            csv_name = self._get_csv_name(timeframe)
            csv_path = os.path.join(cache_dir, csv_name)
            if os.path.exists(csv_path):
                LOG.info("found: %s", csv_path)
                try:
                    self._mem_cache[timeframe] = \
                        pd.read_csv(csv_path, index_col=0)
                except pd.errors.EmptyDataError:
                    pass

    def search(self, timeframe:str, since:int, to:int):
        """
        Search from cache
        """
        LOG.info("Search cache: tf=%s, since=%d, to=%d",
                 timeframe, since, to)
        if timeframe not in self._mem_cache:
            self._mem_cache[timeframe] = pd.DataFrame()
            return None

        if since < self._mem_cache[timeframe].index[0] or \
            since > self._mem_cache[timeframe].index[-1]:
            LOG.info("No records found from cache")
            return None

        df_part = None
        # if from_ in the range of existing cache
        if to <= self._mem_cache[timeframe].index[-1] and \
            self.check_cache(timeframe, since, to):
            LOG.info("All records found from cache")
            df_part = self._mem_cache[timeframe].loc[since:to]
        else:
            if self.check_cache(timeframe, since):
                df_part = self._mem_cache[timeframe].loc[since:]
                LOG.info("Part of records found from cache: from %d -> %d",
                        df_part.index[0], df_part.index[-1])

        return df_part

    def save(self, timeframe:str, df_new:pd.DataFrame):
        """
        Save OHLCV to cache
        """
        self._mem_cache[timeframe] = pd.concat(
            [self._mem_cache[timeframe], df_new])
        self._mem_cache[timeframe] = \
            self._mem_cache[timeframe][~self._mem_cache[timeframe].\
                                       index.duplicated(keep='first')]
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

    def check_cache(self, timeframe:str, since:int, to:int=-1):
        """
        Check whether the dataframe is continuous
        """
        df_cached = self._mem_cache[timeframe]
        if to == -1:
            to = self._mem_cache[timeframe].index[-1]

        for item in [since, to]:
            if item < df_cached.index[0] or item > df_cached.index[-1]:
                return False

        df_cached = self._mem_cache[timeframe].loc[since:to]
        if len(df_cached) == 0 or df_cached.index[0] != since:
            return False

        count = int((df_cached.index[-1] - df_cached.index[0]) / \
                    TIME_FRAME[timeframe]) + 1
        if count != len(df_cached):
            LOG.error("The cache[%d->%d] is not completed: count=%d, len=%d",
                       since, to, count, len(df_cached))
            return False
        return True

class DataCollectorThread(Thread):

    def __init__(self, key:str, market_obj:FinancialMarket,
                 asset_obj:FinancialAsset, timeframe:str, since:int):
        Thread.__init__(self)
        self._key = key
        self._market_obj = market_obj
        self._since = since
        self._asset_obj = asset_obj
        self._timeframe = timeframe
        self._current = since
        self._terminate = False
        self._now = time.time()

    def run(self):
        LOG.info("Thread %s started.", self._key)
        self._current = self._since
        limit = 100
        tf_delta = TIME_FRAME[self._timeframe]
        while not self._terminate:
            LOG.info("=> %d: Collector[%s] since=%d ...",
                 self._now, datetime.datetime.fromtimestamp(self._now).\
                    strftime('%Y-%m-%d %H:%M:%S'),
                    self._current)
            to = self._current + limit * tf_delta
            if self._asset_obj.cache.check_cache(self._timeframe, self._current, to):
                # skip for existing data
                self._current = to + limit * tf_delta
                continue

            ret = self._asset_obj.fetch_ohlcv(
                self._timeframe, self._current, limit)
            if ret is not None:
                self._current = ret.index[-1] + tf_delta
                LOG.info("current:%d, now:%d", self._current, self._now)
                if self._current >= self._now - tf_delta:
                    break
            time.sleep(5)
        self._terminate = True
        LOG.info("Thread %s completed.", self._key)

    @property
    def is_completed(self):
        return self._terminate

    def terminate(self):
        self._terminate = True

    @property
    def progress(self):
        total = int((self._now - self._since) / TIME_FRAME[self._timeframe])
        now = int((self._now - self._current) / TIME_FRAME[self._timeframe])
        return now, total

    @property
    def since(self):
        return self._since
