import logging
from datetime import datetime, timedelta
from bsapi import BaoStockApi, FORMAT_DAY

logging.basicConfig(level=logging.DEBUG)
bsa = BaoStockApi()
ret = bsa.get_tickers()
fname = 'stock_china_tickers_' + datetime.today().strftime(FORMAT_DAY) + '.csv'
ret.to_csv(fname, encoding="utf-8", index=False)
