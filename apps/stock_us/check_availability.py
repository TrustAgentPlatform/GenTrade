
import requests
import json
import yfinance as yf
from datetime import datetime, timedelta
import time

#SEC_LIST="https://www.sec.gov/files/company_tickers.json"

final = {}
issue = {}

def save_file(value, filename):
    with open(filename, 'w') as fp:
        json.dump(value, fp)

with open('company_tickers.json') as f:
    origin = json.loads(f.read())
    index = 0
    for item in origin:
        print('%04d - %s' % (index, origin[item]['ticker']))
        index += 1
        asset_name = origin[item]['ticker']
        try:
            ohlcv = yf.download(
                asset_name,
                group_by="Ticker",
                start=datetime.now().replace(second=0, microsecond=0) - timedelta(days=10),
                interval='1d')
            if len(ohlcv) != 0:
                final[item] = origin[item]
                save_file(final, 'final.json')
            else:
                issue[item] = origin[item]
                save_file(issue, 'issue.json')
        except Exception as ex:
            print(f"Error: {ex}")
            time.sleep(5)
            issue[item] = origin[item]
            save_file(issue, 'issue.json')

