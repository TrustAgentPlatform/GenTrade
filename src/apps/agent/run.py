"""
Agent to call TIA datahub API to get crypto prices.

Please prepare below steps to run this script:

1. Set the PYTHONPATH for the library of tia.

For example: if the tia library is put at D:\\work\\fintech\\TrustedInvestAgent\\src
then "set PYTHONPATH=D:\\work\\fintech\\TrustedInvestAgent\\src"

2. Set environment variables:
    - TIA_BINANCE_API_KEY
    - TIA_BINANCE_API_SECRET
    - OPENAI_API_KEY
    - OPENAI_API_URL (optional)
    - OPENAI_API_MODEL (optional)

"""
import os
import logging

import backtrader as bt

from autogen import ConversableAgent
from tia.market_data.crypto import BinanceMarket
from tia.strategy.basic import StrategySma

LOG = logging.getLogger(__name__)

# pylint: disable=unexpected-keyword-arg, global-variable-not-assigned, global-statement
API_KEY  = os.environ.get("OPENAI_API_KEY", "empty")
BASE_URL = os.environ.get("OPENAI_API_URL", "https://oa.api2d.net")
MODEL    = os.environ.get("OPENAI_API_MODEL", "gpt-4o")

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

def get_crypto_price(name:str, timeframe:str="1h", limit:int=100) -> dict:
    name += "_usdt"
    bm_inst = BinanceMarket()
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
    return df_new.to_json()

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
              bitcoin or BTC, eth for Ethereum
        timeframe: the duration of time frame like 1d for 1 day, 1h for 1 hour
        limit: the count of timeframe since from today to calculate
        """
    )(get_crypto_price)
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
user_proxy.register_for_execution(name="do_bt_sma")(do_bt_sma)

# chat_result = user_proxy.initiate_chat(
#     assistant,
#     message="""
#         Please get past 400 days price for bitcoin, then use simple moving average
#         strategy for back testing, please try to use 7 for slow line, and 21 for
#         fast line
#         please terminate after call function
#         """)

chat_result = user_proxy.initiate_chat(
    assistant,
    message="""
        请获取过去300天的以太坊的价格，并使用简单平均移动策略来进行回测，在这个策略中，
        请设置慢线为9，请设置快线为26
        please terminate after call function
        """)
