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

    _inst = None

    def __init__(self) -> None:
        self._cache_dir = os.getenv("TIA_CACHE_DIR", None)
        LOG.info("Cache directory is %s", self._cache_dir)
        crypto_market = BinanceMarket(cache_dir=self._cache_dir)
        self._markets:dict[str, FinancialMarket] = {
            crypto_market.market_id: BinanceMarket(cache_dir=self._cache_dir)
        }
        for market in self._markets.values():
            if not market.init():
                pass

    @property
    def markets(self):
        return self._markets


    @staticmethod
    def inst():
        if DataServer._inst is None:
            DataServer._inst = DataServer()
        return DataServer._inst

data_server = DataServer.inst()

@app.get("/get_markets")
async def get_markets():
    retval = {}
    for key, market in data_server.markets.items():
        retval[key] = {
            "name": market.name,
            "type": market.market_type,
        }
    return retval

@app.get("/get_ohlcv")
async def get_ohlcv(market_id:str, asset:str="BTC_USDT",
                    timeframe:str="1m", since:int=-1, limit:int=10):
    if market_id not in data_server.markets:
        return None
    market_obj = data_server.markets[market_id]

    for key, _ in market_obj.assets.items():
        print(key)
    asset_obj = market_obj.get_asset(asset.lower())
    ret = asset_obj.fetch_ohlcv(timeframe, since, limit)
    return ret.to_json(orient="records")

