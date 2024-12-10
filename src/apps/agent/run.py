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

from autogen import ConversableAgent
from tia.market_data.crypto import BinanceMarket

LOG = logging.getLogger(__name__)

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
    return df_new.to_json()

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

# Register the tool function with the user proxy agent.
user_proxy.register_for_execution(name="get_crypto_price")(get_crypto_price)

chat_result = user_proxy.initiate_chat(
    assistant,
    message="""
        请拿到过去20天的以太坊的价格,
        please terminate after call function
        """)

chat_result = user_proxy.initiate_chat(
    assistant,
    message="""
        Please get past 30 hours price for bitcoin, please terminate
        after call function
        """
        )

chat_result = user_proxy.initiate_chat(
    assistant,
    message="""
        Please get past 40 days price for 比特币,
        please terminate after call function
        """)
