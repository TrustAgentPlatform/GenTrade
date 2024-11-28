"""
Main entry for API gateway server.

"""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .market_data.core import FinancialMarket
from .market_data.crypto import BinanceMarket

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
LOG = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DataServer:

    """
    Data Server to provide market data.

    please set `TIA_CACHE_DIR`.
    """
    def __init__(self) -> None:
        self._cache_dir = os.getenv("TIA_CACHE_DIR", None)
        LOG.info("Cache directory is %s", self._cache_dir)
        crypto_market = BinanceMarket(cache_dir=self._cache_dir)
        self._markets:dict[str, FinancialMarket] = {
            crypto_market.name: BinanceMarket(cache_dir=self._cache_dir)
        }
        for market in self._markets.values():
            if not market.init():
                pass

    @property
    def markets(self):
        return self._markets

dataserv = DataServer()

@app.get("/get_markets")
async def get_markets():
    retval = {}
    for key, market in dataserv.markets.items():
        retval[key] = {
            "name": market.name,
            "type": market.market_type,
            "id": market.market_id
        }
    return retval
