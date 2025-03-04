import os
import optparse
import logging
from datetime import datetime, timedelta

import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from talib import abstract

import zhbase
import external
import utility

FORMAT_DAY = '%Y-%m-%d'
FORMAT_TIME = '%Y-%m-%d %H:%M:%S'
CURR_DIR = os.path.dirname(__file__)
LOG = logging.getLogger(__name__)


def parse_args():
    parser = optparse.OptionParser()
    parser.add_option('-c', '--code', type=str, default='000001')
    parser.add_option('-k', '--ktype', type=int, default=1)
    parser.add_option('-s', '--start')
    parser.add_option('-e', '--end')
    opts, _ = parser.parse_args()
    start = opts.start
    if start is not None:
        start = datetime.strptime(start, FORMAT_DAY)
    return opts.code, opts.ktype, start, opts.end


def show(code, name, ktype, df):
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
    mpf.plot(df, title="%s - %s [%d]" % (code, name, ktype), type='candle',
             style=style, xrotation=90, datetime_format='%Y-%m-%d %H:%M',
             mav=(7, 14, 30, 60), volume=True,
             ylabel='价格', ylabel_lower='量',
             figratio=(10, 7), figscale=1,
             show_nontrading=False,
             addplot=panels, returnfig=True)
    mpf.show()

def start():
    code, ktype, start, end = parse_args()

    market = zhbase.ChinaMarket()
    market.load()
    name = market.get_name(code)
    if name is None:
        return
    asset = zhbase.ChinaAsset(code, name)
    df = asset.get_ohlcv(ktype, start, end)
    show(code, name, ktype, df)


if __name__ == '__main__':
    start()
