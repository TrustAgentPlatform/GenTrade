import os
import logging
import pytest

import ccxt

import gentrade.market_data
import gentrade.market_data.crypto
from gentrade.market_data.crypto import BinanceMarket
from gentrade.market_data.stock_us import StockUSMarket

CURR = os.path.dirname(__file__)

LOG = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def inst_binance() -> BinanceMarket:
    """
    Binance Market Instance in session scope
    """
    cache_dir = os.getenv("GENTRADE_CACHE_DIR", os.path.join(CURR, "../cache/"))
    LOG.info("Cache Directory: %s", cache_dir)
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

@pytest.fixture(scope="session")
def inst_stock_us() -> StockUSMarket:
    """
    Stock US market instance
    """
    cache_dir = os.getenv("GENTRADE_CACHE_DIR", os.path.join(CURR, "../cache/"))
    market_inst = gentrade.market_data.stock_us.StockUSMarket(cache_dir)
    assert market_inst.init(), "Fail to initiate the market instance"
    return market_inst
