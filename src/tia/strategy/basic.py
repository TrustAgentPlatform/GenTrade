"""
The collections of basic strategies
"""
import logging

import backtrader as bt
import backtrader.indicators as btind

LOG = logging.getLogger(__name__)

# pylint: disable=no-member, too-many-function-args, unexpected-keyword-arg

class StrategyBase(bt.Strategy):

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        LOG.info('%s %s', dt.strftime("%Y-%m-%d %H:%M:%S"), txt)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
        # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, %.2f' % order.executed.price)
            elif order.issell():
                self.log('SELL EXECUTED, %.2f' % order.executed.price)
            self.bar_executed = len(self)
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' % (
            trade.pnl, trade.pnlcomm))

class StrategyRsi(StrategyBase):
    params=(
        ('min_RSI', 35),
        ('max_RSI', 65),
        ('max_position', 10),
        ('look_back_period', 14)
        )

    def __init__(self):
        super().__init__()
        # RSI indicator
        self.RSI = btind.RSI_SMA(self.data.close, period=self.params.look_back_period)

    def next(self):
        # Buy if over sold
        if self.RSI < self.params.min_RSI:
            self.buy()
        # Sell if over buyed
        if self.RSI > self.params.max_RSI:
            self.close()

class StrategySma(StrategyBase):

    """
    SMA, SimpleMovingAverage
    Non-weighted average of the last n periods

    Formula:
        movav = Sum(data, period) / period

    See also:
        http://en.wikipedia.org/wiki/Moving_average#Simple_moving_average
    """

    params = (
        ('fast', 9),
        ('slow', 21),
    )

    def __init__(self):
        super().__init__()
        sma_fast = btind.SMA(period=self.p.fast)
        sma_slow = btind.SMA(period=self.p.slow)
        self.buysig = btind.CrossOver(sma_fast, sma_slow)

    def next(self):
        if self.position.size:
            if self.buysig < 0:
                self.sell()
        elif self.buysig > 0:
            self.buy()

class StrategyMacd(StrategyBase):
    params=(
        ('fast_LBP',12),
        ('slow_LBP',26),
        ('max_position',1),
        ('signal_LBP',9)
        )

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        super().__init__()
        self.fast_EMA = btind.EMA(self.data, period=self.params.fast_LBP)
        self.slow_EMA = btind.EMA(self.data, period=self.params.slow_LBP)

        self.MACD=self.fast_EMA-self.slow_EMA
        self.Signal = btind.EMA(self.MACD, period=self.params.signal_LBP)
        self.Crossing = btind.CrossOver(
            self.MACD,
            self.Signal,
            plotname='Buy_Sell_Line')
        self.Hist = self.MACD - self.Signal

    def next(self):

        # If MACD is above Signal line
        if self.Crossing > 0:
            if self.position.size < self.params.max_position:
                self.buy()

        # If MACD is below Signal line
        elif self.Crossing < 0:
            if self.position.size > 0:
                self.close()

class StrategyWma(StrategyBase):

    """
    Alias:

        WMA, MovingAverageWeighted
        A Moving Average which gives an arithmetic weighting to values with the
        newest having the more weight

    Formula:

        weights = range(1, period + 1)
        coef = 2 / (period * (period + 1))
        movav = coef * Sum(weight[i] * data[period - i] for i in range(period))

    See also:

        http://en.wikipedia.org/wiki/Moving_average#Weighted_moving_average
    """

    params = (
        ('maperiod', 30),
    )

    def __init__(self):
        super().__init__()
        self.dataclose = self.datas[0].close

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
        self.buycomm = None

        #Adding SMA indicator
        self.sma = btind.WeightedMovingAverage(
            self.datas[0], period = self.params.maperiod
        )

    def next(self):
        self.log('Close, %.2f' % self.dataclose[0])

        if self.order:
            return

        #check if we are in market
        if not self.position:
            if self.dataclose[0] > self.sma[0]:
                self.log('BUY CREATE, %.2f' % self.dataclose[0])
                self.order = self.buy()
        else:
            if self.dataclose[0] < self.sma[0]:
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                self.order = self.sell()


class StrategyBb(StrategyBase):

    """
    BollingerBands

    Defined by John Bollinger in the 80s. It measures volatility by defining
    upper and lower bands at distance x standard deviations

    Formula:
        midband = SimpleMovingAverage(close, period)
        topband = midband + devfactor * StandardDeviation(data, period)
        botband = midband - devfactor * StandardDeviation(data, period)

    See: <http://en.wikipedia.org/wiki/Bollinger_Bands>
    """
    params = (
        ('maperiod', 30 ),
    )

    def __init__(self):
        super().__init__()
        self.dataclose = self.datas[0].close

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
        self.buycomm = None

        #Adding SMA indicator
        self.bbands = btind.BBands(self.datas[0])

    def next(self):
        self.log('Close, %.2f' % self.dataclose[0])

        if self.order:
            return

        #check if we are in market
        if not self.position:
            if self.bbands[0] < self.dataclose[0]:
                self.log('BUY CREATE, %.2f' % self.dataclose[0])
                self.order = self.buy()
        else:
            if self.bbands[0] > self.dataclose[0]:
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                self.order = self.sell()
