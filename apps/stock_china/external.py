import baostock
import logging
import pandas as pd
import adata
from datetime import datetime, timedelta

LOG = logging.getLogger(__name__)
FORMAT_DAY = '%Y-%m-%d'
FORMAT_TIME = '%Y-%m-%d %H:%M:%S'

class BaoStockApi:

    def __init__(self):
        ret = baostock.login()
        assert(self._check_ret(ret))

    def _check_ret(self, ret):
        """Check the error code

        Args:
            retobj (any): return object from BaoStock

        Returns:
            bool: success for error code 0
        """
        if ret.error_code == '0':
            return True
        LOG.error("Return error [%s]: %s",
                    ret.error_code, ret.error_msg)
        return False

    def get_trade_days(self, start, end) -> pd.DataFrame:
        """Get last the trade day from now

        Returns:
            ------------------------------------
            calendar_date        is_trading_day
            ------------------------------------
            2025-01-01                 0
            2025-01-02                 1
            2025-01-03                 1
            ------------------------------------
        """
        ret = baostock.query_trade_dates(start_date=start, end_date=end)
        if ret.error_code == '0':
            return ret.get_data().set_index('calendar_date')
        return None

    def get_last_trading_day(self) -> datetime:
        """
        Get the last trading day
        """
        end = datetime.today()
        df_date = self.get_trade_days(
            datetime.today() - timedelta(days=7), datetime.today())
        df_valid = df_date.loc[df_date['is_trading_day'] == '1']
        if len(df_valid) == 0:
            return None
        return datetime.strptime(df_valid.tail(1).index[0], FORMAT_DAY)

    def get_all_stocks(self, day=None) -> pd.DataFrame:
        """_summary_

        Args:
            day (_type_, optional): _description_. Defaults to None.

        Returns:
            -----------------------------------------------------------
            id          code      tradeStatus   code_name      exchange
            -----------------------------------------------------------
            sh.000001  000001           1      上证综合指数        sh
            sh.000002  000002           1      上证A股指数         sh
            sh.000003  000003           1      上证B股指数         sh
            sh.000004  000004           1     上证工业类指数       sh
            -----------------------------------------------------------
        """
        if day is None:
            day = self.get_last_trading_day()
        ret = baostock.query_all_stock(day=day.strftime(FORMAT_DAY))
        assert(self._check_ret(ret))
        df = ret.get_data()
        df['id'] = df['code']
        df['code'] = df['id'].str[3:]
        df['exchange'] = df['id'].str[:2]
        df.set_index('id', inplace=True)
        return df

    def get_stock_basic_info(self, id='sh.000001') -> list:
        ret = baostock.query_stock_basic(code=id)
        assert(self._check_ret(ret))
        ret.next()
        value = ret.get_row_data()
        if len(value) != 0:
            return [ value[2], value[4] ]
        return None


class ADataApi:

    def _process_date(self, df) -> pd.DataFrame:
        df['date'] = pd.to_datetime(df['trade_time'])
        df.set_index('date', inplace=True)
        df.drop(columns=['trade_time',
                'trade_date'], inplace=True)
        return df

    def get_ohlcv(self, code, ktype, start:datetime, end:datetime):
        df = adata.stock.market.get_market(
            code, start.strftime(FORMAT_TIME),
            end.strftime(FORMAT_TIME), ktype)
        return self._process_date(df).drop(columns=['stock_code'])

    def get_index_min(self, code='000001'):
        df = adata.stock.market.get_market_index_min(code)
        return self._process_date(df).drop(columns=['index_code'])
