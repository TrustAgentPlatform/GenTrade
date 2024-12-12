"""
Main entry for API gateway server.

"""
import os
import sys
import logging
import signal
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from gentrade.market_data.core import FinancialMarket, DataCollectorThread
from gentrade.market_data.crypto import BinanceMarket, BINANCE_MARKET_ID
from gentrade.market_data.timeframe import TimeFrame

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
LOG = logging.getLogger(__name__)
CURR_DIR = os.path.dirname(os.path.realpath(__file__))

class DataServer:

    """
    Data Server to provide market data.

    please set `GENTRADE_CACHE_DIR`.
    """

    _inst = None

    def __init__(self) -> None:
        self._cache_dir = os.getenv("GENTRADE_CACHE_DIR",
                                    os.path.join(CURR_DIR, "../../cache"))
        LOG.info("Cache directory is %s", self._cache_dir)
        self._markets:dict[str, FinancialMarket] = {}
        self._collect_threads:dict[str, DataCollectorThread] = {}

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

    def cleanup(self):
        LOG.info("Shutting Down ...")
        for _, t in self._collect_threads.items():
            t.terminate()

    def collect(self, market_id:str, asset:str, timeframe:str, since:int) -> int:
        if market_id not in self._markets:
            return False
        if timeframe not in TimeFrame.SUPPORTED:
            return False

        new_thread_key = "%s|%s" % (market_id, asset)

        market_obj = self._markets[market_id]
        asset_obj = market_obj.get_asset(asset.lower())

        now = time.time()
        if asset_obj.cache.check_cache(timeframe, since, now):
            LOG.info("All data already cached.")
            return -1

        if new_thread_key in self._collect_threads:
            if not self._collect_threads[new_thread_key].is_completed:
                progress_now, progress_total = \
                    self._collect_threads[new_thread_key].progress
                LOG.info("[%s] progress: %d/%d",
                        new_thread_key, progress_now, progress_total)
                return 100 - int((progress_now / progress_total) * 100)

        self._collect_threads[new_thread_key] = DataCollectorThread(
              new_thread_key, market_obj, asset_obj, timeframe, since)
        self._collect_threads[new_thread_key].start()
        return 0

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
    data_server.cleanup()
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

@app.get("/markets/")
async def get_markets():
    retval = {}
    for key, market in data_server.markets.items():
        retval[key] = {
            "name": market.name,
            "type": market.market_type,
        }
    return retval

@app.get("/assets/")
async def get_asserts(market_id:str, start:int=0, max_count:int=1000):
    if market_id is None or market_id not in data_server.markets:
        return None
    market_obj = data_server.markets[market_id]
    assets = list(market_obj.assets.keys())
    ret_count = min(max_count, len(assets) - start)
    return {
        "market": market_id,
        "count": len(assets),
        "assets": assets[start:start + ret_count]
    }

@app.get("/asset/get_ohlcv")
async def get_ohlcv(market_id:str, asset:str="BTC_USDT",
                    timeframe:str="1h", since:int=-1, limit:int=10):
    if market_id not in data_server.markets:
        return None

    asset_obj = data_server.markets[market_id].get_asset(asset.lower())
    ret = asset_obj.fetch_ohlcv(timeframe, since, limit)
    return ret.to_json(orient="records")

@app.post("/asset/start_collect")
async def start_collect(market_id:str=BINANCE_MARKET_ID,
                        asset:str="BTC_USDT",
                        timeframe:str="1h", since:int=-1):
    ret = data_server.collect(market_id, asset, timeframe, since)
    return { "ret": ret }

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)
