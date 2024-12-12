"""
Run with matplot to draw diagram
"""
import os
import logging
import argparse
import mplfinance as mpf

from gentrade.market_data.crypto import BinanceMarket

LOG = logging.getLogger(__name__)

# pylint: disable=unexpected-keyword-arg, too-many-function-args

def parse_args():
    cache_dir = os.path.join(os.path.dirname(__file__), "../../../", "cache")

    parser = argparse.ArgumentParser(prog='tia_sma')
    parser.add_argument("-a", "--asset", default="btc",
                        help="Crypto Asset name btc/eth/doge, it will"
                             "append _usdt automatically")
    parser.add_argument("-t", "--timeframe", help="Timeframe string",
                        default="1h", type=str)
    parser.add_argument("-l", "--limit", default=50, type=int,
                        help="The limit count of kline, default is 50")
    parser.add_argument("-c", "--cache", default=cache_dir, type=str,
                        help="Data cache for Binance market, default is ../../cache")
    return parser.parse_args()

def get_data(cache_dir:str, asset_name:str, timeframe:str, limit:int):
    asset_name += "_usdt"
    bm_inst = BinanceMarket(cache_dir)
    if not bm_inst.init():
        LOG.error("Fail to create Binance instance")
        return None

    asset_inst = bm_inst.get_asset(asset_name)
    if asset_inst is None:
        LOG.error("Fail to get asset %s", asset_name)
        return None

    df = asset_inst.fetch_ohlcv(timeframe=timeframe, limit=limit)
    df = asset_inst.index_to_datetime(df)
    df.index.name="date"
    df.columns = [ "open", "high", "low", "close", "volume"]
    return df

def start():
    args = parse_args()
    df = get_data(args.cache, args.asset, args.timeframe, args.limit)
    mpf.plot(df, type='candle', mav=(3,6,9), volume=True)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start()
