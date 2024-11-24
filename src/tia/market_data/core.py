"""
DataHub Core Package
"""
import logging
import pandas as pd
import time
from abc import ABC, abstractmethod

LOG = logging.getLogger(__name__)

# Forward Declaration
class FinancialMarket(ABC):
    pass

class FinancialAsset(ABC):
    """
    Trading instruments are all the different types of assets and contracts that
    can be traded. Trading instruments are classified into various categories,
    some more popular than others.
    """

    # The detle of TIME FRAME in seconds
    TIME_FRAME = {
        '15m':          15 * 60,
        '1h':       1 * 60 * 60,
        '4h':       4 * 60 * 60,
        '1d':      24 * 60 * 60,
        '1W':  7 * 24 * 60 * 60,
        '1M': 30 * 24 * 60 * 60
    }

    def __init__(self, name:str, market:FinancialMarket):
        self._name:str = name
        self._market:FinancialMarket = market
        self._cache:dict[str, pd.DataFrame] = {}

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
            max_limit = int((time.time() - since) / self.TIME_FRAME[timeframe])
            if limit > max_limit:
                limit = max_limit

        # try to get data from cache firstly
        df_cached, since_new, limit_new = \
            self._fetch_ohlcv_from_cache(timeframe, since, limit)
        if df_cached is None:
            LOG.info("Fetch ohlcv from market: timeframe:%s since:%s, limit:%d",
                     timeframe, since, limit)
            df = self._market.fetch_ohlcv(self, timeframe, since, limit)
            self._save_ohlcv_to_cache(timeframe, df)
            return df
        else:
            if limit_new == 0:
                # already find all data from cache, return directly
                return df_cached
            else:
                # find part of data from cache, need continue to get others
                df_part = self._market.fetch_ohlcv(
                    self, timeframe, since_new, limit_new)
                self._save_ohlcv_to_cache(timeframe, df_part)
                return self._merge_df(df_cached, df_part)

    def _merge_olhcv(self, df1:pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
        """
        Merge two OLHCV data frame
        """
        df_merged = pd.concat([df1, df2]).drop_duplicates()
        df_merged.sort_index(inplace=True)
        return df_merged

    def _fetch_ohlcv_from_cache(self, timeframe, since, limit) -> pd.DataFrame:
        """
        Fetch OHLCV from cache
        """
        LOG.info("featch_ohlcv_from_cache: since=%d, limit=%d now=%d" % \
                 (since, limit, time.time()))
        if timeframe not in self.TIME_FRAME:
            LOG.error("Time frame %s is invalid" % timeframe)
            return None, since, limit

        # if the cache for specific time frame has not been created, then create
        if timeframe not in self._cache:
            self._cache[timeframe] = pd.DataFrame()
            return None, since, limit

        tf_delta = self.TIME_FRAME[timeframe]
        # calculate the range from_ -> to_
        if since == -1:
            to_ = int(time.time() / tf_delta - 1) * tf_delta
            from_ = to_ - (limit - 1) * tf_delta
        else:
            from_ = int(since / tf_delta) * tf_delta
            to_ = since + (limit - 1) * tf_delta

        LOG.info("from=%d->to=%d first=%d->last=%d" % (
            from_, to_, self._cache[timeframe].index[0],
            self._cache[timeframe].index[-1]))

        # if from_ is too small or too big, then fetch from remote directly.
        if from_ < self._cache[timeframe].index[0] or \
            from_ > self._cache[timeframe].index[-1]:
            LOG.info("Not found records from cache")
            return None, since, limit

        # if from_ in the range of existing cache
        if to_ <= self._cache[timeframe].index[-1]:
            LOG.info("Found all records from cache")
            df_part = self._cache[timeframe].loc[from_:to_]
            if self._check_whether_continuous(df_part, timeframe):
                return df_part, since, 0

        else:
            LOG.info("Found part of records from cache")
            df_part = self._cache[timeframe].loc[from_:]
            if self._check_whether_continuous(df_part, timeframe):
                new_limit = limit - \
                    int((to_ - self._cache[timeframe].index[-1]) / tf_delta)
                new_since = self._cache[timeframe].index[-1]
                return df_part, new_since, new_limit

        return None, since, limit

    def _check_whether_continuous(self, df:pd.DataFrame, timeframe):
        """
        Check whether the dataframe is continuous
        """
        count = int((df.index[-1] - df.index[0]) / self.TIME_FRAME[timeframe]) \
            + 1
        if count != len(df):
            LOG.error("The data frame is not continuous: count=%d, len=%d" %
                      (count, len(df)))
            return False
        return True

    def _save_ohlcv_to_cache(self, timeframe:str, df_new:pd.DataFrame):
        """
        Save OHLCV to cache
        """
        self._cache[timeframe] = self._merge_olhcv(
            self._cache[timeframe], df_new)
        return self._cache[timeframe]

    def ohlvc_to_datetime(self, df:pd.DataFrame):
        df.index = pd.to_datetime(df.index, unit="ms")
        return df

class FinancialMarket(ABC):

    MARKET_CRYPTO = 'crypto'
    MARKET_STOCK = 'stock'

    """
    Trading market includes crypto, stock or golden.
    """

    def __init__(self, name:str, market_type:str):
        assert market_type in \
            [FinancialMarket.MARKET_CRYPTO, FinancialMarket.MARKET_STOCK]
        self._name = name
        self._assets:dict[str, FinancialAsset] = {}

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
