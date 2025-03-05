import logging
from datetime import datetime, timedelta
from bsapi import BaoStockApi, FORMAT_DAY

logging.basicConfig(level=logging.DEBUG)
bsa = BaoStockApi()
df = bsa.get_ohlcv_hourly('sz.002882')
print(df)