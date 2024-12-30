
import os
import logging

import backtrader as bt

from autogen import ConversableAgent
from gentrade.market_data.crypto import BinanceMarket
from gentrade.strategy.basic import StrategySma, StrategyWma, StrategyBb, StrategyMacd, StrategyRsi

LOG = logging.getLogger(__name__)

# pylint: disable=unexpected-keyword-arg, global-variable-not-assigned, global-statement
API_KEY  = os.environ.get("OPENAI_API_KEY", "empty")
BASE_URL = os.environ.get("OPENAI_API_URL", "https://api.openai.com/v1")
MODEL    = os.environ.get("OPENAI_API_MODEL", "gpt-3.5-turbo")
CURR     = os.path.dirname(__file__)
config_list= [
    {
        'base_url': BASE_URL,
        'model': MODEL,
        'api_key' : API_KEY
    }
]

llm_config = {
    "config_list": config_list,
}

crypto_data = None

def get_crypto_price(name:str, timeframe:str="1h", limit:int=100) -> bool:
    name += "_usdt"
    cache_dir = os.getenv("GENTRADE_CACHE_DIR", os.path.join(CURR, "../../cache/"))
    LOG.info("Cache Directory: %s", cache_dir)
    bm_inst = BinanceMarket(cache_dir)
    if not bm_inst.init():
        LOG.error("Fail to create Binance instance")
        return None

    asset_inst = bm_inst.get_asset(name)
    if asset_inst is None:
        LOG.error("Fail to get asset %s", name)
        return None

    df = asset_inst.fetch_ohlcv(timeframe=timeframe, limit=limit)
    df = asset_inst.index_to_datetime(df)
    df_new = df.copy()
    df_new['openinterest'] = 0
    df_new.index.name="datetime"
    global crypto_data
    crypto_data = df_new
    return True

def do_strategy(name:str) -> int:
    kwargs = { 'timeframe':bt.TimeFrame.Minutes }

    pandas_data = bt.feeds.PandasData(dataname=crypto_data, **kwargs)
    cerebro = bt.Cerebro()

    if name == "sma":
        cerebro.addstrategy(StrategySma)
    elif name == "wma":
        cerebro.addstrategy(StrategyWma)
    elif name == "macd":
        cerebro.addstrategy(StrategyMacd)
    elif name == "bb":
        cerebro.addstrategy(StrategyBb)
    elif name == "rsi":
        cerebro.addstrategy(StrategyRsi)

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

    cerebro.plot(volume=False)
    return portfolio_end

def do_bt_sma(slow:int=9, fast:int=26) -> None:
    global crypto_data
    kwargs = { 'timeframe':bt.TimeFrame.Minutes }
    pandas_data = bt.feeds.PandasData(dataname=crypto_data, **kwargs)

    cerebro = bt.Cerebro()
    cerebro.addstrategy(StrategySma, fast=fast, slow=slow)
    cerebro.adddata(pandas_data)

    cerebro.broker.setcash(10000000.0)
    cerebro.broker.setcommission(commission=0.0004)

    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name="AnnualReturn")
    cerebro.addanalyzer(bt.analyzers.Calmar, _name="Calmar")
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name = 'SharpeRatio')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='DrawDown')
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')

    portfolio_start = cerebro.broker.getvalue()
    LOG.info('Starting Portfolio Value: %.2f', portfolio_start)
    cerebro.run()
    portfolio_end = cerebro.broker.getvalue()
    earn_percent = (portfolio_end - portfolio_start) * 100 / portfolio_start
    if earn_percent > 0:
        earn_value = "+%.2f" % earn_percent + "%"
    else:
        earn_value = "%.2f" % earn_percent + "%"
    LOG.info("earn value: %s", earn_value)
    cerebro.plot(volume=False)

# Let's first define the assistant agent that suggests tool calls.
assistant = ConversableAgent(
    name="Assistant",
    system_message="You are a helpful AI assistant. "
    "You can help with the tool of get_crypto_price. "
    "Return 'TERMINATE' when the task is done.",
    llm_config=llm_config,
)

# The user proxy agent is used for interacting with the assistant agent
# and executes tool calls.
user_proxy = ConversableAgent(
    name="User",
    llm_config=False,
    is_termination_msg=lambda msg: msg.get("content") is not None and \
        "TERMINATE" in msg["content"],
    human_input_mode="NEVER",
)

# Register the tool signature with the assistant agent.
assistant.register_for_llm(
    name="get_crypto_price",
    description="""
        The tool of get_crypto_price, the params are
        name: the abbreviate name for crypto currency, for example it is btc for
              bitcoin or BTC, eth for Ethereum, please make sure lower case.
        timeframe: the duration of time frame like 1d for 1 day, 1h for 1 hour
        limit: the count of timeframe since from today to calculate
        """
    )(get_crypto_price)
assistant.register_for_llm(
    name="do_strategy",
    description="""
        The tool of do_strategy can do different strategy including sma, wma, macd, rsi, bb
        for back testing, and return the final portfolio money value. It accept following
        params:

        name: the short name of strategy, it can be sma, wma, macd, rsi, bb
        """
    )(do_strategy)
assistant.register_for_llm(
    name="do_bt_sma",
    description="""
        The tool of do_bt_sma is using simple moving average strategy for back
        testing, the params are:

        slow: the slow line value
        fast: the fast line value
        """
    )(do_bt_sma)

# Register the tool function with the user proxy agent.
user_proxy.register_for_execution(name="get_crypto_price")(get_crypto_price)
user_proxy.register_for_execution(name="do_strategy")(do_strategy)
user_proxy.register_for_execution(name="do_bt_sma")(do_bt_sma)

#logging.basicConfig(level=logging.INFO)

while True:
    print("\n\n")
    message = input("Please input your question(请提问):")
    chat_result = user_proxy.initiate_chat(
        assistant,
        message=message + ".\nplease terminate after call function")
