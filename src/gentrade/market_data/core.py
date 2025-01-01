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

from .timeframe import TimeFrame

LOG = logging.getLogger(__name__)

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
    @abstractmethod
    def quote(self) -> str:
        """Quote name, it will be usd for US stock market, cny for chinese stock
        market and usdt for crypto market
        """

    @property
    def market(self) -> FinancialMarket:
        """
        Property market which belong to
        """
        return self._market

    @property
    def cache(self) -> FinancialAssetCache:
        return self._cache

    @property
    @abstractmethod
    def asset_type(self):
        pass

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'type': self.asset_type,
            'market': self.market.market_id,
            'quote': self.quote
        }

    def fetch_ohlcv(self, timeframe:str = '1d', since: int = -1, to: int = -1,
                    limit=-1) -> pd.DataFrame:
        """Fetch the OHLCV

        Args:
            timeframe (str, optional): Defaults to '1d'.
            since (int): the start of UTC timestamp.
            to (int, optional): Defaults to -1 for now
            limit (int, optional): the max count of returned value
        """
        LOG.info("fetch_ohlcv: since:%d, to:%d, limit:%d tf:%s", since, to,
                 limit, timeframe)
        tfobj = TimeFrame(timeframe)

        # Normalize the since and to, so improve hit ratio in cache
        (since_new, to_new) = tfobj.normalize(since, to, limit)
        LOG.info("Normalize: [%d<->%d] => [%d<->%d]", since, to, since_new,
                 to_new)
        if since_new >= to_new:
            return pd.DataFrame()

        # Case 1: no any data in cache
        cache_start, cache_end = self._cache.get_index(timeframe)
        LOG.info('cache start=%d, end=%d', cache_start, cache_end)
        if cache_start == -1 or cache_end == -1:
            LOG.info("case 1")
            self._cache.save(timeframe, self._market.fetch_ohlcv(
                self, timeframe, since_new, to_new))
        else:
            # Case 2: since < cache_start
            if since_new < cache_start:
                LOG.info("case 2")
                if cache_start > to_new:
                    LOG.warning("The cache will not be continuous after this fetch")
                self._cache.save(timeframe,
                                self._market.fetch_ohlcv(
                                    self, timeframe, since_new,
                                    min(cache_start, to_new)))

            # Case 3: to > cache_end
            if to_new > cache_end:
                LOG.info("case 3")
                if since_new > cache_end:
                    LOG.warning("The cache will not be continuous after this fetch")
                self._cache.save(timeframe,
                                self._market.fetch_ohlcv(
                                    self, timeframe, max(cache_end, since_new),
                                    to_new))

        return self._cache.get_part(timeframe, since_new, to_new)

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
        if name.lower() in self._assets:
            return self._assets[name.lower()]
        return None

    @abstractmethod
    def init(self):
        """
        Financial Market initialization
        """
        raise NotImplementedError

    @abstractmethod
    def fetch_ohlcv(self, asset:FinancialAsset, timeframe:str, since:int, to:int):
        """Fetch OHLCV value for specific asset via Market API

        Args:
            asset (FinancialAsset): _description_
            timeframe (str): _description_
            since (int): _description_
            to (int): _description_

        Raises:
            NotImplementedError: _description_
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
            self._mem_cache[timeframe] = pd.DataFrame()
            return -1, -1
        cache_obj = self._mem_cache[timeframe]
        if len(cache_obj) == 0:
            return -1, -1
        return cache_obj.index[0], cache_obj.index[-1]

    def get_part(self, timeframe:str, since:int, to:int) -> pd.DataFrame:
        return self._mem_cache[timeframe].loc[since:to]

    def _init(self):
        cache_dir = self._asset.market.cache_dir
        if cache_dir is None or not os.path.exists(cache_dir):
            return

        for name, _ in TimeFrame.SUPPORTED.items():
            csv_name = self._get_csv_name(name)
            csv_path = os.path.join(cache_dir, csv_name)
            if os.path.exists(csv_path):
                LOG.info("found: %s", csv_path)
                try:
                    self._mem_cache[name] = \
                        pd.read_csv(csv_path, index_col=0)
                except pd.errors.EmptyDataError:
                    LOG.info("Found blank file %s", csv_path)

    def search(self, timeframe:str, since:int, to:int):
        """
        Search from cache
        """
        LOG.info("Search cache: tf=%s, since=%d, to=%d",
                 timeframe, since, to)
        if timeframe not in self._mem_cache:
            self._mem_cache[timeframe] = pd.DataFrame()
            return None

        if len(self._mem_cache[timeframe]) == 0:
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
        if df_new is None or len(df_new) == 0:
            LOG.warning("Invalid dataframe for save")
            return
        self._mem_cache[timeframe] = pd.concat(
            [self._mem_cache[timeframe], df_new])
        self._mem_cache[timeframe] = \
            self._mem_cache[timeframe][~self._mem_cache[timeframe].\
                                       index.duplicated(keep='first')]
        self._mem_cache[timeframe].sort_index(inplace=True)
        self._save_cache_to_file(timeframe)

    def _get_csv_name(self, timeframe):
        return self._asset.name + "-" + TimeFrame.SUPPORTED[timeframe] + ".csv"

    def _save_cache_to_file(self, timeframe):
        self._save_in_progress = True
        cache_dir = self._asset.market.cache_dir
        if cache_dir is not None:
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
            fname = os.path.join(self._asset.market.cache_dir,
                                self._get_csv_name(timeframe))
            self._mem_cache[timeframe].to_csv(fname)
            LOG.info("save to file: %s", fname)
        self._save_in_progress = False

    def check_cache(self, timeframe:str, since:int, to:int=-1):
        """
        Check whether the dataframe is continuous
        """
        if timeframe not in self._mem_cache:
            self._mem_cache[timeframe] = pd.DataFrame()
            return False

        df_cached = self._mem_cache[timeframe]
        if len(df_cached) == 0:
            return False

        if to == -1:
            to = self._mem_cache[timeframe].index[-1]

        for item in [since, to]:
            if item < df_cached.index[0] or item > df_cached.index[-1]:
                return False

        df_cached = self._mem_cache[timeframe].loc[since:to]
        if len(df_cached) == 0 or df_cached.index[0] != since:
            return False

        tfobj = TimeFrame(timeframe)
        count = tfobj.calculate_count(
            since=df_cached.index[0], to=df_cached.index[-1])
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
        limit = -1
        tfobj = TimeFrame(self._timeframe)

        while not self._terminate:
            LOG.info("=> %d: Collector[%s] since=%d ...",
                 self._now, datetime.datetime.fromtimestamp(self._now).\
                    strftime('%Y-%m-%d %H:%M:%S'),
                    self._current)
            if tfobj.is_same_frame(self._current, self._now):
                break

            to = tfobj.ts_since_limit(self._current, limit)
            if self._asset_obj.cache.check_cache(
                self._timeframe, self._current, to):
                # skip for existing data
                LOG.info("Skip the range [%d->%d] since already in cache.",
                         self._current, to)
                self._current = tfobj.ts_since_limit(to + 1, limit)
                continue

            ret = self._asset_obj.fetch_ohlcv(
                self._timeframe, self._current, limit=limit)
            if ret is not None:
                if len(ret) <= 1:
                    break
                self._current = tfobj.ts_since_limit(ret.index[-1] + 1, 1)
                LOG.info("current:%d, now:%d", self._current, self._now)
                if tfobj.is_same_frame(self._current, self._now):
                    break
            else:
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
        tfobj = TimeFrame(self._timeframe)
        total = tfobj.calculate_count(since=self._since, to=self._now)
        now = tfobj.calculate_count(since=self._current, to=self._now)
        return now, total

    @property
    def since(self):
        return self._since
