import pandas as pd
import mplfinance as mpf

def gen_macd_color(df):
    macd_color = []
    macd_color.clear()
    for i in range(0, len(df["MACDh_12_26_9"])):
        if df["MACDh_12_26_9"].iloc[i] >= 0 and \
            df["MACDh_12_26_9"].iloc[i-1] < df["MACDh_12_26_9"].iloc[i]:
            macd_color.append('#26A69A')
        elif df["MACDh_12_26_9"].iloc[i] >= 0 and \
            df["MACDh_12_26_9"].iloc[i-1] > df["MACDh_12_26_9"].iloc[i]:
            macd_color.append('#B2DFDB')
        elif df["MACDh_12_26_9"].iloc[i] < 0 and \
            df["MACDh_12_26_9"].iloc[i-1] > df["MACDh_12_26_9"].iloc[i]:
            macd_color.append('#FF5252')
        elif df["MACDh_12_26_9"].iloc[i] < 0 and \
            df["MACDh_12_26_9"].iloc[i-1] < df["MACDh_12_26_9"].iloc[i]:
            macd_color.append('#FFCDD2')
        else:
            macd_color.append('#000000')
    return macd_color

def macd_plots(df: pd.DataFrame, panel: int, fast=12, slow=26, period=9):
    exp12 = df['close'].ewm(span=fast, adjust=False).mean()
    exp26 = df['close'].ewm(span=slow, adjust=False).mean()
    macd = exp12 - exp26
    signal = macd.ewm(span=period, adjust=False).mean()
    histogram = macd - signal

    df['MACD_12_26_9'] = df.index.map(macd)
    df['MACDh_12_26_9'] = df.index.map(histogram)
    df['MACDs_12_26_9'] = df.index.map(signal)

    macd_color = gen_macd_color(df)

    plots = [
        mpf.make_addplot(
            df[['MACD_12_26_9']], color='#2962FF', panel=panel),
        mpf.make_addplot(
            df[['MACDs_12_26_9']], color='#FF6D00', panel=panel),
        mpf.make_addplot(
            df[['MACDh_12_26_9']], type='bar', width=0.7, panel=panel,
            ylabel='MACD', color=macd_color, alpha=1, secondary_y=True)
    ]
    return plots

def get_ktype_name(ktype:int=1):
    if ktype == 1:
        return '1天'
    elif ktype == 2:
        return '1周'
    elif ktype == 3:
        return '1月'
    elif ktype == 4:
        return '1季度'
    elif ktype == 5:
        return '5分钟'
    elif ktype == 15:
        return '15分钟'
    elif ktype == 30:
        return '30分钟'
    elif ktype == 60:
        return '60分钟'
    return None