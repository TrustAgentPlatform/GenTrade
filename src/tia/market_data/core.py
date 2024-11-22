"""
DataHub Core Package
"""
from abc import ABC, abstractmethod

class Instrument(ABC):
    """
    Trading instruments are all the different types of assets and contracts that
    can be traded. Trading instruments are classified into various categories,
    some more popular than others.
    """

    def __init__(self, name:str):
        self._name = name

    @property
    def name(self) -> str:
        self._name


class MarketProvider(ABC):

    """
    It could be binance, gateio or others who provide market data.
    """

    def __init__(self, name:str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name


class Market(ABC):

    """
    Trading market includes crypto, stock or golden.
    """

    def __init__(self, name:str, market_provider:MarketProvider):
        self._name = name
        self._provider = market_provider
        self._instruments:dict[str, Instrument] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def provider(self) -> MarketProvider:
        return self._provider

    def get_instrument(self, it_name) -> Instrument:
        if it_name in self._instruments:
            return self._instruments[it_name]
        return None
