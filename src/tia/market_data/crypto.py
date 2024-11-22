
from .core import Instrument, Market, MarketProvider


class CryptoMarket(Market):

    def __init__(self):
        Market.__init__(self, "crypto")


class CryptoAsses(Instrument):

    pass