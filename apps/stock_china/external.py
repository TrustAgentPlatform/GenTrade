import logging
from datetime import datetime, timedelta
import pandas as pd

import baostock
import adata


LOG = logging.getLogger(__name__)
FORMAT_DAY = '%Y-%m-%d'
FORMAT_TIME = '%Y-%m-%d %H:%M:%S'


class BaoStockApi:

    def __init__(self):
        ret = baostock.login()
        assert self._check_ret(ret)

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
        assert self._check_ret(ret)
        df = ret.get_data()
        df['id'] = df['code']
        df['code'] = df['id'].str[3:]
        df['exchange'] = df['id'].str[:2]
        df.set_index('id', inplace=True)
        return df

    def get_stock_basic_info(self, id_='sh.000001') -> list:
        ret = baostock.query_stock_basic(code=id_)
        assert self._check_ret(ret)
        ret.next()
        value = ret.get_row_data()
        if len(value) != 0:
            return [value[2], value[4]]
        return None


class ADataApi:

    def _process_date(self, df) -> pd.DataFrame:
        df['date'] = pd.to_datetime(df['trade_time'])
        df.set_index('date', inplace=True)
        df.drop(columns=['trade_time',
                'trade_date'], inplace=True)
        return df

    def get_ohlcv(self, code, ktype, start: datetime, end: datetime):
        df = adata.stock.market.get_market(
            code, start.strftime(FORMAT_TIME),
            end.strftime(FORMAT_TIME), ktype)
        if len(df) == 0:
            return df
        return self._process_date(df).drop(columns=['stock_code'])

    def get_index_min(self, code='000001'):
        df = adata.stock.market.get_market_index_min(code)
        return self._process_date(df).drop(columns=['index_code'])

    def get_stock_industry(self, code='600391'):
        """Get industry information

        Args:
            code (str, optional): _description_. Defaults to '600391'.

        Returns:
            ---------
                stock_code sw_code industry_name industry_type source
            0     600391  650000          国防军工          申万一级  百度股市通
            1     600391  650200         航空装备Ⅱ          申万二级  百度股市通
            --------
        """
        df = adata.stock.info.get_industry_sw(code)
        return df

    def get_stock_concept(self, code='600391'):
        """_summary_

        Args:
            code (str, optional): _description_. Defaults to '600391'.

        Returns:
            stock_code concept_code   name source                                             reason
            0     600391       BK1140   央企改革   东方财富     公司的实际控制人为中国航空发动机集团有限公司,公司的组织形式...
            1     600391       BK0814    大飞机   东方财富      压气机叶片已经中标大飞机C919项目;为飞机提供航空发动机、燃...
            2     600391       BK0715   航母概念   东方财富     公司主营航空发动机和燃气轮机的主要零部件,坚定“做世界级航空...
            3     600391       BK0683   国企改革   东方财富     最终控股股东为国务院国资委
            4     600391       BK0590  西部大开发   东方财富    注册地址是中国(四川)自由贸易成都高新区天韵路150号1栋9楼901号。
            5     600391       BK0490     军工   东方财富      公司主营航空发动机和燃气轮机的主要零部件,坚定“做世界级航空...
        """
        df = adata.stock.info.get_concept_east(code)
        return df

    def get_stock_plate(self, code='600391'):
        """_summary_

        Args:
            code (str, optional): _description_. Defaults to '600391'.

        Returns:
            -----
            stock_code plate_code plate_name plate_type source
            0      600391     BK0480       航天航空         行业   东方财富
            1      600391     BK0169       四川板块         板块   东方财富
            2      600391     BK0707        沪股通         概念   东方财富
            3      600391     BK0596       融资融券         概念   东方财富
            4      600391     BK1140       央企改革         概念   东方财富
            5      600391     BK0814        大飞机         概念   东方财富
            6      600391     BK0715       航母概念         概念   东方财富
            7      600391     BK0683       国企改革         概念   东方财富
            8      600391     BK0590      西部大开发         概念   东方财富
            9      600391     BK0534       成渝特区         概念   东方财富
            10     600391     BK0490         军工         概念   东方财富
            -----
        """
        df = adata.stock.info.get_plate_east(code)
        return df

    def get_index_concept(self, code='600001'):
        df = adata.stock.info.get_plate_east(code)
        return df


if __name__ == "__main__":
    adata_api = ADataApi()
    retval = adata_api.get_stock_plate()
    print(retval)
