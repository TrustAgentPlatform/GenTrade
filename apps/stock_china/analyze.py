import os
import optparse
import logging
from datetime import datetime

import pandas as pd
import mplfinance as mpf

import zhbase
import utility
from matplotlib import ticker

FORMAT_DAY = '%Y-%m-%d'
FORMAT_TIME = '%Y-%m-%d %H:%M:%S'
CURR_DIR = os.path.dirname(__file__)
LOG = logging.getLogger(__name__)


def parse_args():
    parser = optparse.OptionParser()
    parser.add_option('-c', '--code', type=str, default='000001')
    parser.add_option('-k', '--ktype', type=int, default=5)
    parser.add_option('-s', '--start')
    parser.add_option('-e', '--end')
    opts, _ = parser.parse_args()
    start_ = opts.start
    if start_ is not None:
        start_ = datetime.strptime(start_, FORMAT_DAY)
    return opts.code, opts.ktype, start_, opts.end


def show(asset, ktype, df):
    panels = []
    panel_index = 2  # panel 0 is OHLCV, panel 1 is volume

    # show turns_ratio
    turns_col = df[['turnover_ratio']]
    turns_plot = mpf.make_addplot(turns_col, panel=panel_index,
                                  ylabel='换手率', color='lime')
    panels.append(turns_plot)
    panel_index += 1

    # show increase percent
    pct_col = df[['change_pct']]
    pct_plot = mpf.make_addplot(pct_col, panel=panel_index,
                                ylabel='涨幅', color='red')
    panels.append(pct_plot)
    panel_index += 1

    # show MACD
    panels += utility.macd_plots(df, panel_index)

    style = mpf.make_mpf_style(
        base_mpf_style='starsandstripes', rc={
            'font.family': 'SimHei', 'axes.unicode_minus': 'False'})
    _, axlist = mpf.plot(df, title="%s - %s [%s]" % (
                            asset.code, asset.name,
                            utility.get_ktype_name(int(ktype))),
                         type='candle',
                         style=style, xrotation=90, datetime_format='%Y-%m-%d %H:%M',
                         mav=(7, 14, 30, 60), volume=True,
                         ylabel='价格', ylabel_lower='量',
                         figratio=(10, 7), figscale=1,
                         show_nontrading=False,
                         addplot=panels, returnfig=True)
    axlist[0].xaxis.set_major_locator(ticker.MultipleLocator(5))

    # also show sh.000001 上证
    sh000001 = zhbase.ChinaAsset('000001', zhbase.ASSET_TYPE_INDEX)
    df_000001 = sh000001.get_min()
    df_000001 = df_000001.groupby(pd.Grouper(level='date', axis=0,
                                             freq='5Min')).mean()
    df_000001['Open'] = df_000001['avg_price']
    df_000001['Close'] = df_000001['avg_price']
    df_000001['High'] = df_000001['avg_price']
    df_000001['Low'] = df_000001['avg_price']
    df_000001['Volume'] = df_000001['volume']
    _, axlist = mpf.plot(df_000001, title=sh000001.name + " 5分钟", type='line',
                           style=style, xrotation=90, datetime_format='%Y-%m-%d %H:%M',
                           volume=True,
                           ylabel='价格', ylabel_lower='量',
                           figratio=(10, 7), figscale=1,
                           show_nontrading=False,
                           returnfig=True)
    axlist[0].xaxis.set_major_locator(ticker.MultipleLocator(5))
    mpf.show()


def run():
    code, ktype, start, end = parse_args()

    asset = zhbase.ChinaAsset(code, zhbase.ASSET_TYPE_STOCK)
    df = asset.get_ohlcv(ktype, start, end)
    show(asset, ktype, df)

if __name__ == '__main__':
    run()
