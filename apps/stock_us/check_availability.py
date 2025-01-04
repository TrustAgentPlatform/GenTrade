import argparse
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
        json.dump(value, fp, indent=4)

def check_file(origin_fname):
    with open(origin_fname) as f:
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
                    start=datetime.now().replace(second=0, microsecond=0) - timedelta(days=20),
                    interval='1d')

                if len(ohlcv) != 0:
                    final[item] = origin[item]
                    save_file(final, 'final.json')
                else:
                    issue[item] = origin[item]
                    save_file(issue, 'issue.json')

            except Exception as ex:
                print(f"Error: {ex}")
                time.sleep(100)
                issue[item] = origin[item]
                save_file(issue, 'issue.json')

def check_ticker(ticker):
    try:
        ohlcv = yf.download(
            ticker,
            group_by="Ticker",
            start=datetime.now().replace(second=0, microsecond=0) - timedelta(days=10),
            interval='5d',
            period='5d')
        print(ohlcv)
        print(len(ohlcv))
    except Exception as ex:
        print('1213123123')
        print(f"Error: {ex}")

def start():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--filename')
    parser.add_argument('-t', '--ticker')
    ret = parser.parse_args()
    if ret.filename is None and ret.ticker is None:
        parser.print_help()
        print("please provide either file name or a ticker")
    if ret.ticker is not None:
        check_ticker(ret.ticker)
    elif ret.filename is not None:
        check_file(ret.filename)

if __name__ == "__main__":
    start()
