import os
import pytest

import ccxt

import gentrade.market_data
import gentrade.market_data.crypto
from gentrade.market_data.crypto import BinanceMarket

CURR = os.path.dirname(__file__)

@pytest.fixture(scope="session")
def inst_binance() -> BinanceMarket:
    """
    Binance Market Instance in session scope
    """
    cache_dir = os.getenv("GENTRADE_CACHE_DIR", os.path.join(CURR, "../cache/"))
    market_inst = gentrade.market_data.crypto.BinanceMarket(cache_dir)
    assert market_inst.init(), "Fail to initiate the market instance"
    return market_inst

@pytest.fixture(scope="session")
def inst_ccxt_binance() -> ccxt.binance:
    """
    Binance instance created from CCXT
    """
    ccxt_inst = ccxt.binance({'apiKey': os.getenv("BINANCE_API_KEY"),
                              'secret': os.getenv("BINANCE_API_SECRET")})
    ccxt_inst.load_markets()
    return ccxt_inst
