import os
import logging
import pandas as pd
from datetime import datetime, timedelta
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
        self._df = None

    def load(self, market_file=None):
        if market_file is None:
            market_file = os.path.join(CURR_DIR, 'china_market.csv')
        if not os.path.exists(market_file):
            self.download(market_file)
        else:
            df = pd.read_csv(market_file, dtype=str, index_col=0)
        self._df = df
        return self._df

    def download(self, fpath):
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
        df_stocks.to_csv(fpath, encoding='utf8')

    def get_name(self, code:str, asset_type:str=ASSET_TYPE_STOCK):
        df = self._df.loc[(self._df['code'] == code) & (
            self._df['type'] == asset_type)]
        if len(df) == 0:
            LOG.error("Could not find the specific code %s" % code)
            return None
        return df.iloc[0]['code_name']

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

    @property
    def code(self):
        return self._code

    @property
    def asset_type(self):
        return self._type

    @property
    def name(self):
        return self._name

    def get_ohlcv(self, ktype=1, start:datetime=None, end:datetime=None):
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

    def _calculate_start(self, ktype:int, end:datetime) -> datetime:
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
        elif ktype == 3 or ktype == 4:
            start = end - timedelta(weeks=240)
        elif ktype == 5:
            start = end - timedelta(days=3)
        elif ktype == 15:
            start = end - timedelta(days=7)
        elif ktype in [30, 60]:
            start = end - timedelta(days=14)
        return start

    def get_min(self):
        if self._type == ASSET_TYPE_INDEX:
            return self._adata_api.get_index_min(self.code)
        return None

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    ca = ChinaAsset('000001')
    df = ca.get_ohlcv()
    print(df)
