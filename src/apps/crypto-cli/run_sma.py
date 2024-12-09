"""
SMA strategy by using the backtrader library
"""
import os
import logging
import argparse

import backtrader as bt

from tia.strategy.basic import StrategySma
from tia.market_data.crypto import BinanceMarket

LOG = logging.getLogger(__name__)

# pylint: disable=unexpected-keyword-arg, too-many-function-args

def parse_args():
    cache_dir = os.path.join(os.path.dirname(__file__), "../../", "cache")

    parser = argparse.ArgumentParser(prog='tia_sma')
    parser.add_argument("-a", "--asset", default="btc",
                        help="Crypto Asset name btc/eth/doge, it will"
                             "append _usdt automatically")
    parser.add_argument("-s", "--slow", default=21, type=int,
                        help="The number of slow SMA, default is 21")
    parser.add_argument("-f", "--fast", help="The number of fast SMA, default is 9",
                        default=9, type=int)
    parser.add_argument("-t", "--timeframe", help="Timeframe string",
                        default="1h", type=str)
    parser.add_argument("-l", "--limit", default=100, type=int,
                        help="The limit count of kline, default is 100")
    parser.add_argument("-g", "--graphic", help="Draw graphic or not",
                        default=False, action="store_true")
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
    df_new = df.copy()
    df_new['openinterest'] = 0
    df_new.index.name="datetime"
    return df_new

def start():
    args = parse_args()

    df = get_data(args.cache, args.asset, args.timeframe, args.limit)
    kwargs = { 'timeframe':bt.TimeFrame.Minutes }

    pandas_data = bt.feeds.PandasData(dataname=df, **kwargs)
    cerebro = bt.Cerebro()
    cerebro.addstrategy(StrategySma, fast=args.fast, slow=args.slow)
    cerebro.adddata(pandas_data)

    cerebro.broker.setcash(10000000.0)
    cerebro.broker.setcommission(commission=0.0004)

    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name="AnnualReturn")
    cerebro.addanalyzer(bt.analyzers.Calmar, _name="Calmar")
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name = 'SharpeRatio')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='DrawDown')
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')

    portfolio_start = cerebro.broker.getvalue()
    print('Starting Portfolio Value: %.2f' % portfolio_start)
    results = cerebro.run()
    strat = results[0]
    portfolio_end = cerebro.broker.getvalue()
    earn_percent = (portfolio_end - portfolio_start) * 100 / portfolio_start
    if earn_percent > 0:
        earn_value = "+%.2f" % earn_percent + "%"
    else:
        earn_value = "%.2f" % earn_percent + "%"

    print("\n\n=====================================")
    print('Portfolio Money Change : %.2f -> %.2f %s' % (
        portfolio_start, portfolio_end, earn_value))
    sharp_ratio = strat.analyzers.SharpeRatio.get_analysis()['sharperatio']
    if sharp_ratio is not None:
        print('SharpeRatio            : %.2f' % sharp_ratio )
    else:
        print('SharpeRatio            : None')

    print('Max Draw Down          : %.2f' % \
          strat.analyzers.DrawDown.get_analysis()['max']['drawdown'] + '%')
    print('Max Money Down         : %.2f' % \
          strat.analyzers.DrawDown.get_analysis()['max']['moneydown'])
    print("=====================================\n\n")
    if args.graphic:
        cerebro.plot(volume=False)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start()
