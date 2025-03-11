import os
import logging
from datetime import datetime, timedelta

import pandas as pd

import external

FORMAT_DAY = '%Y-%m-%d'
FORMAT_TIME = '%Y-%m-%d %H:%M:%S'
CURR_DIR = os.path.dirname(__file__)
LOG = logging.getLogger(__name__)

ASSET_TYPE_STOCK = '1'
ASSET_TYPE_INDEX = '2'


class ChinaMarket:

    _inst = None

    def __init__(self):
        self._bsapi = external.BaoStockApi()
        self._adata_api = external.ADataApi()
        self._df = None

    def load(self, market_file=None):
        if market_file is None:
            market_file = os.path.join(CURR_DIR, 'china_market.csv')
        if not os.path.exists(market_file):
            self._df = self.download_base()
            self.save(market_file)
        else:
            self._df = pd.read_csv(market_file, dtype=str, index_col=0)
        return self._df

    def save(self, market_file=None):
        self._df.to_csv(market_file, encoding='utf8')

    def download_base(self):
        """Download the asset list including stock and index

        Args:
            fpath (_type_): _description_
        """
        df_stocks = self._bsapi.get_all_stocks()
        df_stocks['type'] = '0'
        df_stocks['date'] = ''
        count = 0
        for item in df_stocks.index:
            values = self._bsapi.get_stock_basic_info(item)
            if values is not None:
                df_stocks.loc[item, 'date'] = values[0]
                df_stocks.loc[item, 'type'] = values[1]
                LOG.info("-> [%04d][%s] type:%s name:%s ", count, item,
                         df_stocks.loc[item, 'type'],
                         df_stocks.loc[item, 'code_name'])
                count += 1
        return df_stocks

    def get_name(self, code: str, asset_type: str = ASSET_TYPE_STOCK):
        df = self._df.loc[(self._df['code'] == code) & (
            self._df['type'] == asset_type)]
        if len(df) == 0:
            LOG.error("Could not find the specific code %s", code)
            return None
        return df.iloc[0]['code_name']

    def get_id(self, code: str, asset_type: str = ASSET_TYPE_STOCK):
        df = self._df.loc[(self._df['code'] == code) & (
            self._df['type'] == asset_type)]
        if len(df) == 0:
            LOG.error("Could not find the specific code %s", code)
            return None
        return df.index[0]

    def get_trade_days(self, start, end=None) -> pd.DataFrame:
        return self._bsapi.get_trade_days(start, end)

    def download_industry_info(self):
        count = 0
        if "industry1_code" not in self._df.columns:
            self._df["industry1_code"] = ""
        if "industry1_name" not in self._df.columns:
            self._df["industry1_name"] = ""
        if "industry2_code" not in self._df.columns:
            self._df["industry2_code"] = ""
        if "industry2_name" not in self._df.columns:
            self._df["industry2_name"] = ""
        for index in self._df.index:
            if self._df.at[index, 'type'] == ASSET_TYPE_INDEX:
                continue
            ret = self._adata_api.get_stock_industry(
                self._df.at[index, 'code'])
            if ret is not None and len(ret) == 2:
                self._df.at[index, 'industry1_code'] = ret.at[0, 'sw_code']
                self._df.at[index, 'industry1_name'] = ret.at[0,
                                                              'industry_name']
                self._df.at[index, 'industry2_code'] = ret.at[1, 'sw_code']
                self._df.at[index, 'industry2_name'] = ret.at[1,
                                                              'industry_name']
            LOG.info("[%04d] %s", count, self._df.loc[[index]])
            count += 1
            self.save('china_market_2.csv')

    @staticmethod
    def inst():
        if ChinaMarket._inst is None:
            ChinaMarket._inst = ChinaMarket()
            ChinaMarket._inst.load()
        return ChinaMarket._inst


class ChinaAsset:

    def __init__(self, code: str, asset_type=ASSET_TYPE_STOCK):
        self._adata_api = external.ADataApi()
        self._code = code
        self._type = asset_type
        self._name = ChinaMarket.inst().get_name(code, asset_type)
        self._id = ChinaMarket.inst().get_id(code, asset_type)

    @property
    def code(self):
        return self._code

    @property
    def asset_type(self):
        return self._type

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    def __str__(self):
        return '[%s] %s' % (self._id, self._name)

    def get_ohlcv(self, ktype=1, start: datetime = None, end: datetime = None):
        """Get OHLCV

        Args:
            ktype (int, optional):  1:day 2:week 3:month 4:quart 5:5min
                                    15: 15min 30:30min 60:60min
            start (datetime, optional): _description_. Defaults to None.
            end (datetime, optional): _description_. Defaults to None.
        """
        if end is None:
            end = datetime.now()
        if start is None:
            start = self._calculate_start(ktype, end)

        LOG.info('Get OHLCV[%s][%s] => ktype=%d start=%s, end=%s',
                 self._code, self._name, ktype,
                 start.strftime(FORMAT_TIME), end.strftime(FORMAT_TIME))
        df = self._adata_api.get_ohlcv(self._code, ktype, start, end)
        return df

    def _calculate_start(self, ktype: int, end: datetime) -> datetime:
        """Calculate the start date according to end date and ktype

        Args:
            ktype (_type_): ktype
            end (_type_): end date

        Returns:
            _type_: _description_
        """
        if ktype == 1:
            start = end - timedelta(days=200)
        elif ktype == 2:
            start = end - timedelta(weeks=100)
        elif ktype in (3, 4):
            start = end - timedelta(weeks=240)
        elif ktype == 5:
            start = end - timedelta(days=3)
        elif ktype == 15:
            start = end - timedelta(days=7)
        elif ktype in [30, 60]:
            start = end - timedelta(days=14)
        else:
            LOG.error("invalid ktype: %d", ktype)
            return None
        return start

    def get_min(self):
        if self._type == ASSET_TYPE_INDEX:
            return self._adata_api.get_index_min(self.code)
        return None

    @staticmethod
    def all(asset_type=ASSET_TYPE_STOCK):
        ret_dict = {}
        df = ChinaMarket.inst().load()
        print(df)
        for index in df.index:
            if df.loc[index]['type'] == ASSET_TYPE_STOCK:
                asset = ChinaAsset(df.loc[index]['code'], asset_type)
                ret_dict[asset.id] = asset
        return ret_dict


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    cm = ChinaMarket()
    cm.load()
    cm.download_industry_info()
