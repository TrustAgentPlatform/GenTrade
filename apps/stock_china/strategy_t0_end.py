
import logging
from datetime import datetime
import pandas as pd

import zhbase

FORMAT_DAY = '%Y-%m-%d'
FORMAT_TIME = '%Y-%m-%d %H:%M:%S'


def get_prev_info(code, prev_date: datetime):
    asset = zhbase.ChinaAsset(code)
    df = asset.get_ohlcv(ktype=15, start=prev_date, end=prev_date)
    if len(df) == 0:
        return None
    vol_total = df['volume'].sum()
    # get the records which time is between 9:30 and 14:45
    df_afternoon = df[8:15]
    print(df_afternoon)
    turnover_ratio = df_afternoon['turnover_ratio'].sum()
    change_pct = df_afternoon['change_pct'].sum()
    vol_afternoon = df_afternoon['volume'].sum()
    print("turns:%f, changes:%f volume_ratio:%f" %
          (turnover_ratio, change_pct, vol_afternoon/vol_total))
    return turnover_ratio, change_pct, vol_afternoon/vol_total


def get_next_info(code, next_date: datetime):
    asset = zhbase.ChinaAsset(code)
    df = asset.get_ohlcv(ktype=15, start=next_date, end=next_date)
    df_morning = df[0:6]
    changes = df_morning['change_pct'].sum()
    return changes


def process(code='600343'):
    days = zhbase.ChinaMarket.inst().get_trade_days(start='2025-01-01')
    days = days[days['is_trading_day'] == '1']
    df_ret = pd.DataFrame(
        columns=['date', 'code', 'name', 'turns', 'changes', 'vol', 'next'])
    asset = zhbase.ChinaAsset(code)
    for loc_index in range(len(days) - 1):
        try:
            prev_date = datetime.strptime(days.index[loc_index], FORMAT_DAY)
            next_date = datetime.strptime(
                days.index[loc_index + 1], FORMAT_DAY)
            ret = get_prev_info(code, prev_date)
            if ret is None:
                continue
            next_ = get_next_info(code, next_date)
            df_ret.loc[len(df_ret) + 1] = [prev_date, code,
                                           asset.name, ret[0], ret[1], ret[2], next_]
        except:
            continue
    return df_ret


def start():
    logging.basicConfig(level=logging.INFO)
    ret = zhbase.ChinaAsset.all()
    print(ret)
    df_ret = pd.DataFrame(
        columns=['date', 'code', 'name', 'turns', 'changes', 'vol', 'next'])
    for _, asset in ret.items():
        if asset.asset_type == zhbase.ASSET_TYPE_INDEX:
            continue
        df_ret = pd.concat([df_ret, process(asset.code)], ignore_index=True)
        df_ret.to_csv('result.csv')


if __name__ == '__main__':
    start()
