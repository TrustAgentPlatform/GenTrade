"""
Main entry for API gateway server.

"""
import os
import sys
import logging
import signal
import time
import datetime
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .market_data.core import FinancialMarket
from .market_data.crypto import BinanceMarket

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
LOG = logging.getLogger(__name__)
CURR_DIR = os.path.dirname(os.path.realpath(__file__))

class DataServer:

    """
    Data Server to provide market data.

    please set `TIA_CACHE_DIR`.
    """

    _inst = None

    def __init__(self) -> None:
        self._cache_dir = os.getenv("TIA_CACHE_DIR",
                                    os.path.join(CURR_DIR, "cache"))
        LOG.info("Cache directory is %s", self._cache_dir)
        self._markets:dict[str, FinancialMarket] = {}

    @property
    def markets(self):
        return self._markets

    def _add_markets(self):
        crypto_market = BinanceMarket(cache_dir=self._cache_dir)
        self._markets:dict[str, FinancialMarket] = {
            crypto_market.market_id: BinanceMarket(cache_dir=self._cache_dir)
        }

    def _init_markets(self):
        for market in self._markets.values():
            if not market.init():
                pass

    def init(self):
        self._add_markets()
        self._init_markets()
        #asyncio.create_task(self._task_collect_crypto())

    def cleanup(self):
        LOG.info("Shutting Down ...")

    async def _task_collect_crypto(self):
        now = time.time()
        LOG.info("=> On Sched - %d %s:",
                 now, datetime.datetime.fromtimestamp(now).\
                    strftime('%Y-%m-%d %H:%M:%S'))
        while True:
            crypto_market = self.markets[BinanceMarket.MARKET_ID]
            if not crypto_market.init():
                continue
            assets = ["btc_usdt", "eth_usdt", "doge_usdt"]
            if crypto_market is not None:
                for asset in assets:
                    asset_obj = crypto_market.get_asset(asset.lower())
                    if asset_obj is not None:
                        for tf in ["1m", "15m", "1h", "4h"]:
                            asset_obj.fetch_ohlcv(tf, limit=50)
            await asyncio.sleep(60)

    @staticmethod
    def inst():
        if DataServer._inst is None:
            DataServer._inst = DataServer()
        return DataServer._inst

data_server = DataServer.inst()

def receive_signal(signalNumber, _):
    """
    Quit on Control + C
    """
    LOG.info('Received Signal: %d', signalNumber)
    sys.exit()

@asynccontextmanager
async def lifespan(_:FastAPI):
    LOG.info("Starting Up...")
    signal.signal(signal.SIGINT, receive_signal)
    data_server.init()
    yield
    data_server.cleanup()

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

    asset_obj = data_server.markets[market_id].get_asset(asset.lower())
    ret = asset_obj.fetch_ohlcv(timeframe, since, limit)
    return ret.to_json(orient="records")

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)
