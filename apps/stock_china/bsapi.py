import baostock
import logging
import pandas
from datetime import datetime, timedelta

LOG = logging.getLogger(__name__)
FORMAT_DAY = '%Y-%m-%d'

class BaoStockApi:

    def __init__(self):
        retobj = baostock.login()
        assert(self._check_ret(retobj))

    def _check_ret(self, retobj):
        """Check the error code

        Args:
            retobj (any): return object from BaoStock

        Returns:
            bool: success for error code 0
        """
        if retobj.error_code == '0':
            return True

        LOG.error("Return error [%s]: %s",
                    retobj.error_code, retobj.error_msg)
        return False

    def get_last_trade_day(self) -> datetime:
        """Get last the trade day from now

        Returns:
            datetime: the last trade day
        """
        end = datetime.today()
        start = end - timedelta(days=7)
        ret_arr = baostock.query_trade_dates(start_date=start, end_date=end)
        last = None
        while (ret_arr.error_code == '0') & ret_arr.next():
            ret_row = ret_arr.get_row_data()
            if ret_row[1] == '1':
                last = ret_row[0]
        assert last is not None
        return datetime.strptime(last, FORMAT_DAY)

    def get_tickers(self):
        """Get all today's tickers information

        Returns:
            DataFrame: Tickers table
        """
        last = self.get_last_trade_day()
        ret_arr = baostock.query_all_stock(day=last.strftime(FORMAT_DAY))
        tickers_list = []
        count = 0
        while (ret_arr.error_code == '0') & ret_arr.next():
            count += 1
            [ code, status, name ] = ret_arr.get_row_data()
            ticker_info = self.get_ticker_info(code)
            if ticker_info is not None:
                [ ipo_date, type_ ] = ticker_info
            else:
                [ ipo_date, type_ ] = ['', '']
            print('[%d] %s - %s' % (count, code, name))
            tickers_list.append([code, name, type_, status, ipo_date])
        return pandas.DataFrame(tickers_list, columns=['code', 'name', 'type', 'status', 'ipo_data'])

    def get_ticker_info(self, ticker='sh.000001'):
        """Get detail informatino for a given ticker

        Args:
            ticker (str, optional): _description_. Defaults to 'sh.000001'.

        Returns:
            []: ipo date and type
        """
        rs = baostock.query_stock_basic(code=ticker)
        while (rs.error_code == '0') & rs.next():
            row_data = rs.get_row_data()
            return row_data[2], row_data[4]
        return None


    def get_ohlcv(self, code, start, end):
        k_rs = baostock.query_history_k_data_plus(code, "date,code,open,high,low,close,volume,amount,turn", start, end)
        #data_df = pandas.concat([data_df, k_rs.get_data()], ignore_index=True)
        #print(k_rs.get_data())
        return k_rs.get_data()
