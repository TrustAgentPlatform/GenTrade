import logging
from datetime import datetime, timedelta
from bsapi import BaoStockApi, FORMAT_DAY
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from talib import abstract

#zhfont1 = matplotlib.font_manager.FontProperties(fname="SourceHanSansSC-Bold.otf")
#plt.rcParams['font.family'] = 'Heiti TC'
plt.rcParams['font.sans-serif'] = ['SimHei']


def DEMA(df, period):
    return abstract.DEMA(df, timeperiod=period)

def EMA(df, period):
    return abstract.EMA(df, timeperiod=period)

def SMA(df, period):
    return abstract.SMA(df, timeperiod=period)

def RSI(df, period):
    return abstract.RSI(df, timeperiod=period)

#Generating Colors For Histogram
def gen_macd_color(df):
    macd_color = []
    macd_color.clear()
    for i in range (0,len(df["MACDh_12_26_9"])):
        if df["MACDh_12_26_9"][i] >= 0 and df["MACDh_12_26_9"][i-1] < df["MACDh_12_26_9"][i]:
            macd_color.append('#26A69A')
            #print(i,'green')
        elif df["MACDh_12_26_9"][i] >= 0 and df["MACDh_12_26_9"][i-1] > df["MACDh_12_26_9"][i]:
            macd_color.append('#B2DFDB')
            #print(i,'faint green')
        elif df["MACDh_12_26_9"][i] < 0 and df["MACDh_12_26_9"][i-1] > df["MACDh_12_26_9"][i] :
            #print(i,'red')
            macd_color.append('#FF5252')
        elif df["MACDh_12_26_9"][i] < 0 and df["MACDh_12_26_9"][i-1] < df["MACDh_12_26_9"][i] :
            #print(i,'faint red')
            macd_color.append('#FFCDD2')
        else:
            macd_color.append('#000000')
            #print(i,'no')
    return macd_color

def MACD(df, fast=12, slow=26, period=9):
    exp12     = df['close'].ewm(span=fast, adjust=False).mean()
    exp26     = df['close'].ewm(span=slow, adjust=False).mean()
    macd      = exp12 - exp26
    signal    = macd.ewm(span=period, adjust=False).mean()
    histogram = macd - signal

    df['MACD_12_26_9'] = df.index.map(macd)
    df['MACDh_12_26_9'] = df.index.map(histogram)
    df['MACDs_12_26_9'] = df.index.map(signal)

    macd_color = gen_macd_color(df)


    # fb_green = dict(y1=macd.values,y2=signal.values,where=signal<macd,color="#93c47d",alpha=0.6,interpolate=True)
    # fb_red   = dict(y1=macd.values,y2=signal.values,where=signal>macd,color="#e06666",alpha=0.6,interpolate=True)
    # fb_green['panel'] = 1
    # fb_red['panel'] = 1
    # fb       = [fb_green,fb_red]

    # apds = [mpf.make_addplot(exp12,color='lime'),
    #         mpf.make_addplot(exp26,color='c'),
    #         mpf.make_addplot(histogram,type='bar',width=0.7,panel=1,
    #                         color='dimgray',alpha=1,secondary_y=True),
    #         mpf.make_addplot(macd,panel=1,color='fuchsia',secondary_y=False),
    #         mpf.make_addplot(signal,panel=1,color='b',secondary_y=False)#,fill_between=fb),
    #     ]
    apds = [
        mpf.make_addplot(df[['MACD_12_26_9']],color='#2962FF', panel=1),
        mpf.make_addplot(df[['MACDs_12_26_9']],color='#FF6D00', panel=1),
        mpf.make_addplot(df[['MACDh_12_26_9']],type='bar',width=0.7,panel=1, ylabel='MACD', color=macd_color,alpha=1,secondary_y=True),
    ]
    return apds

logging.basicConfig(level=logging.DEBUG)
bsa = BaoStockApi()
end_day = datetime.today()
start_day = end_day - timedelta(200)

data = bsa.get_ohlcv(code='sh.600622', start=start_day.strftime(FORMAT_DAY), end=end_day.strftime(FORMAT_DAY))
data.reset_index(drop=True, inplace=True)
data['date'] = pd.to_datetime(data['date'])
data['open'] = data['open'].astype('float')
data['high'] = data['high'].astype('float')
data['low'] = data['low'].astype('float')
data['close'] = data['close'].astype('float')
data['volume'] = data['volume'].astype('float')
data['turn'] = data['turn'].astype('float')
data.set_index('date', inplace=True)

index  = mpf.make_addplot(DEMA(data, 10), panel=2)
index2  = mpf.make_addplot(EMA(data, 40))
#mpf.plot(data, title='sz.300105', type='candle',mav=(3,6,9),volume=True, addplot = [index])
#print(index)
turns_index = data[['turn']]
index3 = mpf.make_addplot(turns_index, panel=3, ylabel = '换手率', color = 'lime')
print(MACD(data))
#index_macd = mpf.make_addplot(MACD(data),panel=3,color='fuchsia',secondary_y=True),
#print(turns_index)
index_rsi = mpf.make_addplot(RSI(data, 15),panel=4,color='fuchsia', ylabel='RSI', secondary_y=True)

plots = MACD(data)
plots.append(index3)
plots.append(index_rsi)

s = mpf.make_mpf_style(base_mpf_style='starsandstripes', rc={
    'font.family': 'SimHei', 'axes.unicode_minus': 'False'})
mpf.plot(data, title='光大嘉宝', type='candle', style=s, volume=True, \
    mav=(7,14,30,60), scale_width_adjustment=dict(ohlc=2.0,lines=0.65,volume=0.4), \
    addplot = plots, ylabel='价格', ylabel_lower='量', volume_panel=2, \
    figscale=1, returnfig=True, \
        xrotation=90)
mpf.show()