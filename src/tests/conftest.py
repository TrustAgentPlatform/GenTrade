import os
import pytest

import ccxt

import tia
import tia.market_data
import tia.market_data.crypto
from tia.market_data.crypto import BinanceMarket


@pytest.fixture(scope="session")
def inst_binance() -> BinanceMarket:
    """
    Binance Market Instance in session scope
    """
    cache_dir = os.getenv("TIA_CACHE_DIR", None)
    market_inst = tia.market_data.crypto.BinanceMarket(cache_dir)
    assert market_inst.init(), "Fail to initiate the market instance"
    return market_inst

@pytest.fixture(scope="session")
def inst_ccxt_binance() -> ccxt.binance:
    """
    Binance instance created from CCXT
    """
    ccxt_inst = ccxt.binance({'apiKey': os.getenv("TIA_BINANCE_API_KEY"),
                              'secret': os.getenv("TIA_BINANCE_API_SECRET")})
    ccxt_inst.load_markets()
    return ccxt_inst
